"""FastAPI HTTP API [服务]"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from orchestrator import Orchestrator, get_config
from orchestrator.models import ProgressUpdate, ResearchResult
from orchestrator.storage.postgres_store import PostgresStore

# [全局状态]
orchestrator: Optional[Orchestrator] = None
active_tasks: Dict[str, ResearchResult] = {}
task_progress: Dict[str, list] = {}
postgres_store: Optional[PostgresStore] = None


class ResearchRequest(BaseModel):
    """[调研请求]"""
    query: str


class ResearchResponse(BaseModel):
    """[调研响应]"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """[任务状态响应]"""
    task_id: str
    status: str
    progress: float
    current_site: Optional[str]
    message: str


class TaskResultResponse(BaseModel):
    """[任务结果响应]"""
    task_id: str
    status: str
    result: Optional[dict]


class TaskHistoryItem(BaseModel):
    """[任务历史记录项]"""
    task_id: str
    user_query: str
    status: str
    created_at: str
    completed_at: Optional[str]
    total_sites: int
    successful_sites: int


class TaskHistoryResponse(BaseModel):
    """[任务历史响应]"""
    tasks: List[TaskHistoryItem]
    total: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """[应用生命周期管理]"""
    global orchestrator, postgres_store

    # [启动时初始化]
    config = get_config()
    orchestrator = Orchestrator(config)

    # [初始化 PostgreSQL 存储]
    try:
        postgres_store = PostgresStore(
            host=config.storage.postgres.host,
            port=config.storage.postgres.port,
            database=config.storage.postgres.database,
            user=config.storage.postgres.user,
            password=config.storage.postgres.password
        )
        await postgres_store.connect()
        print("[INIT] PostgreSQL [存储已连接]")
    except Exception as e:
        print(f"[WARN] PostgreSQL [连接失败]: {e}")
        postgres_store = None

    print("[INIT] Orchestrator [初始化完成]")

    yield

    # [关闭时清理]
    if orchestrator:
        print("[SHUTDOWN] [关闭] Orchestrator")
    if postgres_store:
        await postgres_store.disconnect()
        print("[SHUTDOWN] PostgreSQL [已断开]")


app = FastAPI(
    title="[数据源调研平台] API",
    description="[基于] DeepSeek LLM [的数据源调研] Orchestrator",
    version="3.0.0",
    lifespan=lifespan
)

# CORS [配置]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def progress_callback(task_id: str, progress: ProgressUpdate):
    """[进度回调函数]"""
    if task_id not in task_progress:
        task_progress[task_id] = []
    task_progress[task_id].append(progress.model_dump())
    print(f"[{task_id}] {progress.progress*100:.1f}% - {progress.message}")


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    """
    [启动新的调研任务]

    Args:
        request: [包含用户查询请求]

    Returns:
        [任务]ID[和状态]
    """
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    task_id = None

    try:
        # [生成任务]ID
        from orchestrator.utils import generate_task_id
        task_id = generate_task_id()

        # [创建异步任务运行调研]
        async def run_research_task(tid=task_id):
            result = await orchestrator.run_research(
                user_input=request.query,
                progress_callback=lambda p: progress_callback(tid, p)
            )
            active_tasks[tid] = result

        # [启动后台任务]
        asyncio.create_task(run_research_task())

        return ResearchResponse(
            task_id=task_id,
            status="started",
            message=f"[调研任务已启动，共需探测多个站点]"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[启动调研失败]: {str(e)}")


@app.get("/api/research/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    [获取任务状态和进度]

    Args:
        task_id: [任务]ID

    Returns:
        [任务状态信息]
    """
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        status_info = await orchestrator.get_task_status(task_id)

        if not status_info:
            # [检查是否正在运行但还没有状态]
            progress_list = task_progress.get(task_id, [])
            if progress_list:
                latest = progress_list[-1]
                return TaskStatusResponse(
                    task_id=task_id,
                    status=latest.get("status", "running"),
                    progress=latest.get("progress", 0),
                    current_site=latest.get("current_url"),
                    message=latest.get("message", "[处理中]...")
                )
            raise HTTPException(status_code=404, detail="[任务不存在]")

        return TaskStatusResponse(
            task_id=task_id,
            status=status_info.get("status", "unknown"),
            progress=status_info.get("progress", 0),
            current_site=status_info.get("current_site"),
            message=f"[正在处理]: {status_info.get('current_site', '...')}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[获取状态失败]: {str(e)}")


@app.get("/api/research/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """
    [获取任务结果]

    Args:
        task_id: [任务]ID

    Returns:
        [任务结果]
    """
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="[任务不存在或尚未完成]")

    result = active_tasks[task_id]
    return TaskResultResponse(
        task_id=task_id,
        status="completed",
        result=result.model_dump()
    )


@app.get("/api/research/{task_id}/progress")
async def get_task_progress_stream(task_id: str):
    """
    [获取任务进度历史（]SSE [流）]

    Args:
        task_id: [任务]ID

    Returns:
        SSE [事件流]
    """
    from fastapi.responses import StreamingResponse
    import json

    async def event_stream():
        last_index = 0
        while True:
            progress_list = task_progress.get(task_id, [])

            # [发送新的进度]
            while last_index < len(progress_list):
                data = json.dumps(progress_list[last_index], ensure_ascii=False)
                yield f"data: {data}\n\n"
                last_index += 1

            # [检查任务是否完成]
            if task_id in active_tasks:
                yield f"data: {json.dumps({'status': 'completed'})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.get("/api/research/history", response_model=TaskHistoryResponse)
async def get_task_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None)
):
    """
    [获取任务历史列表]

    Args:
        limit: [返回数量限制]
        offset: [偏移量]
        status: [状态筛选]

    Returns:
        [任务历史列表]
    """
    if postgres_store:
        try:
            tasks = await postgres_store.list_tasks(status=status, limit=limit, offset=offset)
            total = len(tasks)  # [简化处理，实际应该查询总数]

            history_items = []
            for task in tasks:
                history_items.append(TaskHistoryItem(
                    task_id=task.get("task_id", ""),
                    user_query=task.get("user_query", ""),
                    status=task.get("status", "unknown"),
                    created_at=task.get("created_at", "").isoformat() if task.get("created_at") else "",
                    completed_at=task.get("completed_at", "").isoformat() if task.get("completed_at") else None,
                    total_sites=len(task.get("candidate_sites", [])),
                    successful_sites=task.get("successful_sites", 0)
                ))

            return TaskHistoryResponse(tasks=history_items, total=total)
        except Exception as e:
            print(f"[WARN] [查询任务历史失败]: {e}")

    # [如果没有 PostgreSQL，返回内存中的任务]
    tasks = []
    for tid, result in active_tasks.items():
        tasks.append(TaskHistoryItem(
            task_id=tid,
            user_query=result.query,
            status="completed",
            created_at=result.created_at,
            completed_at=result.completed_at,
            total_sites=result.total_sites,
            successful_sites=result.successful_sites
        ))

    return TaskHistoryResponse(tasks=tasks, total=len(tasks))


@app.get("/api/research/{task_id}/details")
async def get_task_details(task_id: str):
    """
    [获取任务详情]

    Args:
        task_id: [任务]ID

    Returns:
        [任务详细信息]
    """
    if postgres_store:
        try:
            task = await postgres_store.get_task(task_id)
            if task:
                site_results = await postgres_store.get_site_results(task_id)
                return {
                    "task_id": task_id,
                    "user_query": task.get("user_query"),
                    "status": task.get("status"),
                    "refined_requirement": task.get("refined_requirement"),
                    "candidate_sites": task.get("candidate_sites", []),
                    "successful_sites": task.get("successful_sites", 0),
                    "created_at": task.get("created_at", "").isoformat() if task.get("created_at") else "",
                    "completed_at": task.get("completed_at", "").isoformat() if task.get("completed_at") else None,
                    "site_results": site_results
                }
        except Exception as e:
            print(f"[WARN] [查询任务详情失败]: {e}")

    # [检查内存中的任务]
    if task_id in active_tasks:
        result = active_tasks[task_id]
        return {
            "task_id": task_id,
            "user_query": result.query,
            "status": "completed",
            "result": result.model_dump()
        }

    raise HTTPException(status_code=404, detail="[任务不存在]")


@app.get("/task/{task_id}")
async def task_detail_page(task_id: str):
    """[返回任务详情页面]"""
    return HTMLResponse(content=TASK_DETAIL_HTML_PAGE.replace("{{TASK_ID}}", task_id))


@app.get("/")
async def root():
    """[根路径返回前端页面]"""
    return HTMLResponse(content=HTML_PAGE)


@app.get("/health")
async def health_check():
    """[健康检查]"""
    return {"status": "ok", "orchestrator": orchestrator is not None}


# [前端] HTML [页面（内嵌）]
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[数据源调研平台]</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .progress-container {
            display: none;
            margin: 20px 0;
        }
        .progress-container.active {
            display: block;
        }
        .progress-bar {
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            min-width: 50px;
        }
        .progress-text {
            text-align: center;
            margin-top: 10px;
            color: #666;
        }
        .status-log {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            margin-top: 15px;
        }
        .status-log .log-entry {
            padding: 3px 0;
            border-bottom: 1px solid #eee;
        }
        .status-log .log-entry:last-child {
            border-bottom: none;
        }
        .results-container {
            display: none;
        }
        .results-container.active {
            display: block;
        }
        .ranking-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        .ranking-item:hover {
            background: #f8f9fa;
        }
        .rank {
            font-size: 24px;
            font-weight: bold;
            width: 40px;
            text-align: center;
        }
        .rank.gold { color: #FFD700; }
        .rank.silver { color: #C0C0C0; }
        .rank.bronze { color: #CD7F32; }
        .site-info {
            flex: 1;
            margin-left: 15px;
        }
        .site-name {
            font-weight: 600;
            font-size: 16px;
            color: #333;
        }
        .site-meta {
            font-size: 13px;
            color: #666;
            margin-top: 4px;
        }
        .score {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .stat-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
            flex: 1;
            min-width: 120px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .error {
            color: #e74c3c;
            background: #fdf2f2;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }
        .loading-dots {
            display: inline-block;
        }
        .loading-dots::after {
            content: '';
            animation: dots 1.5s infinite;
        }
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
        .nav-link {
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            text-decoration: none;
            font-size: 14px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/history" class="nav-link">[📋] [任务历史]</a>
        <h1>[🔍] [数据源调研平台]</h1>

        <div class="card">
            <div class="input-group">
                <input type="text" id="queryInput" placeholder="[输入您的数据调研需求，例如：找科技媒体的数据源]"
                    onkeypress="if(event.key==='Enter')startResearch()">
                <button id="startBtn" onclick="startResearch()">[开始调研]</button>
            </div>

            <div id="progressContainer" class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%">0%</div>
                </div>
                <div class="progress-text" id="progressText">[准备中]...</div>
                <div class="status-log" id="statusLog"></div>
            </div>

            <div id="errorContainer" class="error" style="display: none;"></div>
        </div>

        <div id="resultsContainer" class="card results-container">
            <h2 style="margin-bottom: 20px;">[📊] [调研结果]</h2>

            <div class="stats" id="statsContainer"></div>

            <div id="rankingsList"></div>
        </div>
    </div>

    <script>
        let currentTaskId = null;
        let eventSource = null;

        async function startResearch() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) {
                alert('[请输入调研需求]');
                return;
            }

            // [重置]UI
            document.getElementById('progressContainer').classList.add('active');
            document.getElementById('resultsContainer').classList.remove('active');
            document.getElementById('errorContainer').style.display = 'none';
            document.getElementById('statusLog').innerHTML = '';
            updateProgress(0, '[启动中]...');

            // [禁用按钮]
            document.getElementById('startBtn').disabled = true;
            document.getElementById('startBtn').textContent = '[调研中]...';

            try {
                // [启动调研]
                const response = await fetch('/api/research', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                currentTaskId = data.task_id;

                // [连接] SSE [获取实时进度]
                connectEventSource(currentTaskId);

                // [轮询检查结果]
                pollForResult(currentTaskId);

            } catch (error) {
                showError('[启动调研失败]: ' + error.message);
                resetUI();
            }
        }

        function connectEventSource(taskId) {
            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource(`/api/research/${taskId}/progress`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.status === 'completed') {
                    eventSource.close();
                    return;
                }

                if (data.progress !== undefined) {
                    updateProgress(data.progress * 100, data.message || '[处理中]...');
                }

                if (data.message) {
                    addLogEntry(data.message);
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
            };
        }

        async function pollForResult(taskId) {
            const checkInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/research/${taskId}/result`);

                    if (response.ok) {
                        clearInterval(checkInterval);
                        const data = await response.json();
                        showResults(data.result);
                        resetUI();
                    }
                } catch (error) {
                    console.error('[轮询结果失败]:', error);
                }
            }, 2000);

            // 5[分钟后停止轮询]
            setTimeout(() => clearInterval(checkInterval), 300000);
        }

        function updateProgress(percentage, message) {
            const fill = document.getElementById('progressFill');
            const text = document.getElementById('progressText');

            fill.style.width = percentage + '%';
            fill.textContent = Math.round(percentage) + '%';
            text.textContent = message;
        }

        function addLogEntry(message) {
            const log = document.getElementById('statusLog');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }

        function showResults(result) {
            const container = document.getElementById('resultsContainer');
            const statsContainer = document.getElementById('statsContainer');
            const rankingsList = document.getElementById('rankingsList');

            // [显示统计]
            statsContainer.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${result.total_sites}</div>
                    <div class="stat-label">[总站点数]</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${result.successful_sites}</div>
                    <div class="stat-label">[成功站点]</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${result.failed_sites_count}</div>
                    <div class="stat-label">[失败站点]</div>
                </div>
            `;

            // [显示排行榜]
            let rankingsHTML = '';
            if (result.rankings && result.rankings.length > 0) {
                rankingsHTML = result.rankings.map((item, index) => {
                    const rankClass = index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : '';
                    return `
                        <div class="ranking-item">
                            <div class="rank ${rankClass}">${item.rank}</div>
                            <div class="site-info">
                                <div class="site-name">${item.site_name}</div>
                                <div class="site-meta">
                                    [数据量]: ${item.total_records || '[未知]'} |
                                    [难度]: ${item.difficulty || '[未知]'} |
                                    <a href="${item.site_url}" target="_blank">${item.site_url}</a>
                                </div>
                            </div>
                            <div class="score">${item.quality_score.toFixed(1)}</div>
                        </div>
                    `;
                }).join('');
            } else {
                rankingsHTML = '<p style="text-align: center; color: #999;">[暂无排名数据]</p>';
            }

            rankingsList.innerHTML = rankingsHTML;
            container.classList.add('active');
        }

        function showError(message) {
            const errorContainer = document.getElementById('errorContainer');
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
        }

        function resetUI() {
            document.getElementById('startBtn').disabled = false;
            document.getElementById('startBtn').textContent = '[开始调研]';
        }
    </script>
</body>
</html>
"""

# [任务历史页面]
HISTORY_HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[任务历史] - [数据源调研平台]</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .nav-link {
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            text-decoration: none;
            font-size: 14px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.3);
        }
        h1 {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .filters {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 16px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .filter-btn:hover, .filter-btn.active {
            background: #667eea;
            color: white;
        }
        .task-list {
            list-style: none;
        }
        .task-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
            cursor: pointer;
        }
        .task-item:hover {
            background: #f8f9fa;
        }
        .task-item:last-child {
            border-bottom: none;
        }
        .task-status {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 15px;
        }
        .status-completed { background: #28a745; }
        .status-running { background: #ffc107; animation: pulse 1.5s infinite; }
        .status-pending { background: #6c757d; }
        .status-failed { background: #dc3545; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .task-info {
            flex: 1;
        }
        .task-query {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .task-meta {
            font-size: 13px;
            color: #666;
        }
        .task-stats {
            text-align: right;
            margin-right: 15px;
        }
        .task-stat {
            font-size: 13px;
            color: #666;
        }
        .view-btn {
            padding: 6px 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
        }
        .view-btn:hover {
            background: #5a6fd6;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .error {
            color: #e74c3c;
            background: #fdf2f2;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        .page-btn {
            padding: 8px 16px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            cursor: pointer;
        }
        .page-btn:hover:not(:disabled) {
            background: #f0f0f0;
        }
        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="nav-link">← [返回首页]</a>
        <h1>[📋] [任务历史]</h1>

        <div class="card">
            <div class="filters">
                <button class="filter-btn active" data-status="">[全部]</button>
                <button class="filter-btn" data-status="completed">[已完成]</button>
                <button class="filter-btn" data-status="running">[运行中]</button>
                <button class="filter-btn" data-status="pending">[待处理]</button>
                <button class="filter-btn" data-status="failed">[失败]</button>
            </div>

            <div id="taskList">
                <div class="loading">[加载中...]</div>
            </div>

            <div class="pagination" id="pagination" style="display: none;">
                <button class="page-btn" id="prevBtn" onclick="changePage(-1)">[上一页]</button>
                <span id="pageInfo"></span>
                <button class="page-btn" id="nextBtn" onclick="changePage(1)">[下一页]</button>
            </div>
        </div>
    </div>

    <script>
        let currentPage = 0;
        const pageSize = 20;
        let currentFilter = '';

        async function loadTasks() {
            const taskList = document.getElementById('taskList');
            taskList.innerHTML = '<div class="loading">[加载中...]</div>';

            try {
                const response = await fetch(`/api/research/history?limit=${pageSize}&offset=${currentPage * pageSize}&status=${currentFilter}`);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                renderTasks(data.tasks);
                renderPagination(data.total);
            } catch (error) {
                taskList.innerHTML = `<div class="error">[加载失败]: ${error.message}</div>`;
            }
        }

        function renderTasks(tasks) {
            const taskList = document.getElementById('taskList');

            if (tasks.length === 0) {
                taskList.innerHTML = `
                    <div class="empty-state">
                        <p>[暂无任务记录]</p>
                        <p style="margin-top: 10px; font-size: 14px;">[前往首页开始新的调研任务]</p>
                    </div>
                `;
                return;
            }

            taskList.innerHTML = `
                <ul class="task-list">
                    ${tasks.map(task => `
                        <li class="task-item" onclick="viewTask('${task.task_id}')">
                            <div class="task-status status-${task.status}"></div>
                            <div class="task-info">
                                <div class="task-query">${escapeHtml(task.user_query)}</div>
                                <div class="task-meta">
                                    [任务ID]: ${task.task_id} |
                                    [创建时间]: ${formatDate(task.created_at)}
                                </div>
                            </div>
                            <div class="task-stats">
                                <div class="task-stat">[站点]: ${task.successful_sites}/${task.total_sites}</div>
                                ${task.completed_at ? `<div class="task-stat">[完成]: ${formatDate(task.completed_at)}</div>` : ''}
                            </div>
                            <button class="view-btn">[查看]</button>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        function renderPagination(total) {
            const pagination = document.getElementById('pagination');
            const totalPages = Math.ceil(total / pageSize);

            if (totalPages <= 1) {
                pagination.style.display = 'none';
                return;
            }

            pagination.style.display = 'flex';
            document.getElementById('pageInfo').textContent = `[第] ${currentPage + 1} / ${totalPages} [页]`;
            document.getElementById('prevBtn').disabled = currentPage === 0;
            document.getElementById('nextBtn').disabled = currentPage >= totalPages - 1;
        }

        function changePage(delta) {
            currentPage += delta;
            loadTasks();
        }

        function viewTask(taskId) {
            window.location.href = `/task/${taskId}`;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatDate(dateStr) {
            if (!dateStr) return '[未知]';
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN');
        }

        // [筛选按钮事件]
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.status;
                currentPage = 0;
                loadTasks();
            });
        });

        // [页面加载时获取任务列表]
        loadTasks();
    </script>
</body>
</html>
"""

# [任务详情页面]
TASK_DETAIL_HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[任务详情] - [数据源调研平台]</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .nav-link {
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            text-decoration: none;
            font-size: 14px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.3);
        }
        h1 {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .task-header {
            margin-bottom: 20px;
        }
        .task-query {
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .task-meta {
            color: #666;
            font-size: 14px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .stat-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
            flex: 1;
            min-width: 120px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }
        .ranking-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        .ranking-item:hover {
            background: #f8f9fa;
        }
        .rank {
            font-size: 24px;
            font-weight: bold;
            width: 40px;
            text-align: center;
        }
        .rank.gold { color: #FFD700; }
        .rank.silver { color: #C0C0C0; }
        .rank.bronze { color: #CD7F32; }
        .site-info {
            flex: 1;
            margin-left: 15px;
        }
        .site-name {
            font-weight: 600;
            font-size: 16px;
            color: #333;
        }
        .site-meta {
            font-size: 13px;
            color: #666;
            margin-top: 4px;
        }
        .score {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .error {
            color: #e74c3c;
            background: #fdf2f2;
            padding: 15px;
            border-radius: 10px;
        }
        .back-btn {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        .back-btn:hover {
            background: #5a6fd6;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/history" class="nav-link">← [返回历史]</a>
        <h1>[📊] [任务详情]</h1>

        <div id="content">
            <div class="card">
                <div class="loading">[加载中...]</div>
            </div>
        </div>
    </div>

    <script>
        const taskId = '{{TASK_ID}}';

        async function loadTaskDetails() {
            const content = document.getElementById('content');

            try {
                const response = await fetch(`/api/research/${taskId}/details`);

                if (!response.ok) {
                    if (response.status === 404) {
                        content.innerHTML = `
                            <div class="card">
                                <div class="error">[任务不存在]</div>
                                <a href="/history" class="back-btn">[返回任务历史]</a>
                            </div>
                        `;
                        return;
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                renderTaskDetails(data);
            } catch (error) {
                content.innerHTML = `
                    <div class="card">
                        <div class="error">[加载失败]: ${error.message}</div>
                        <a href="/history" class="back-btn">[返回任务历史]</a>
                    </div>
                `;
            }
        }

        function renderTaskDetails(data) {
            const content = document.getElementById('content');
            const result = data.result || {};
            const rankings = result.rankings || [];

            content.innerHTML = `
                <div class="card">
                    <div class="task-header">
                        <div class="task-query">${escapeHtml(data.user_query || result.query || '[未知任务]')}</div>
                        <div class="task-meta">
                            [任务ID]: ${data.task_id} |
                            [状态]: ${getStatusText(data.status)} |
                            [创建时间]: ${formatDate(data.created_at || result.created_at)}
                        </div>
                    </div>

                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-value">${result.total_sites || 0}</div>
                            <div class="stat-label">[总站点数]</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${result.successful_sites || 0}</div>
                            <div class="stat-label">[成功站点]</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${result.failed_sites_count || 0}</div>
                            <div class="stat-label">[失败站点]</div>
                        </div>
                    </div>
                </div>

                ${rankings.length > 0 ? `
                <div class="card">
                    <h2 class="section-title">[🏆] [站点排行榜]</h2>
                    <div class="rankings">
                        ${rankings.map((item, index) => {
                            const rankClass = index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : '';
                            return `
                                <div class="ranking-item">
                                    <div class="rank ${rankClass}">${item.rank}</div>
                                    <div class="site-info">
                                        <div class="site-name">${escapeHtml(item.site_name)}</div>
                                        <div class="site-meta">
                                            [数据量]: ${item.total_records || '[未知]'} |
                                            [难度]: ${item.difficulty || '[未知]'} |
                                            <a href="${item.site_url}" target="_blank">${item.site_url}</a>
                                        </div>
                                    </div>
                                    <div class="score">${item.quality_score.toFixed(1)}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                ` : ''}

                <div class="card">
                    <a href="/history" class="back-btn">← [返回任务历史]</a>
                </div>
            `;
        }

        function getStatusText(status) {
            const statusMap = {
                'completed': '[已完成]',
                'running': '[运行中]',
                'pending': '[待处理]',
                'failed': '[失败]'
            };
            return statusMap[status] || status;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function formatDate(dateStr) {
            if (!dateStr) return '[未知]';
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN');
        }

        loadTaskDetails();
    </script>
</body>
</html>
"""


@app.get("/history")
async def history_page():
    """[返回任务历史页面]"""
    return HTMLResponse(content=HISTORY_HTML_PAGE)


@app.get("/task/{task_id}")
async def task_detail_page(task_id: str):
    """[返回任务详情页面]"""
    return HTMLResponse(content=TASK_DETAIL_HTML_PAGE.replace("{{TASK_ID}}", task_id))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
