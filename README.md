# 数据源调研平台 - Orchestrator

基于 DeepSeek LLM 的数据源调研调度器，支持需求分析、候选站点挖掘和实时进度展示。

## 特性

- **DeepSeek LLM 驱动**：使用 deepseek-reasoner 模型进行需求分析和站点挖掘
- **Web 界面**：内嵌前端，支持实时进度条和日志展示
- **结果排行榜**：按质量分排序的数据源排行榜
- **HTTP API**：FastAPI 提供的 RESTful API 接口
- **Mock Agent**：本地测试模式，无需真实 Agent 执行器

---

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -e .
pip install fastapi uvicorn
```

### 2. 配置 API Key

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-reasoner
```

### 3. 启动服务

```bash
python run_local.py
```

访问 http://localhost:8000

---

## 使用示例

### Web 界面

1. 打开浏览器访问 http://localhost:8000
2. 在输入框输入需求，例如：`找科技媒体的数据源`
3. 点击"开始调研"
4. 观察实时进度条和日志
5. 查看最终的站点排行榜

### API 调用

**启动调研任务**：

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "找科技媒体的数据源"}'
```

响应：
```json
{
  "task_id": "task_20260227_123456_abc123",
  "status": "started",
  "message": "调研任务已启动"
}
```

**获取任务状态**：

```bash
curl http://localhost:8000/api/research/task_20260227_123456_abc123/status
```

**获取任务结果**：

```bash
curl http://localhost:8027_123456_abc123/result
```

---

## API 接口文档

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 前端界面 |
| `/api/research` | POST | 启动调研任务 |
| `/api/research/{task_id}/status` | GET | 获取任务状态 |
| `/api/research/{task_id}/result` | GET | 获取任务结果 |
| `/api/research/{task_id}/progress` | GET | 实时进度流 (SSE) |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |

### 详细 API 说明

#### POST /api/research

启动新的调研任务。

**请求体**：
```json
{
  "query": "找人工智能新闻网站"
}
```

**响应**：
```json
{
  "task_id": "task_20260227_123456_abc123",
  "status": "started",
  "message": "调研任务已启动"
}
```

#### GET /api/research/{task_id}/status

获取任务当前状态。

**响应**：
```json
{
  "task_id": "task_20260227_123456_abc123",
  "status": "running",
  "progress": 0.6,
  "current_site": "https://36kr.com",
  "message": "正在处理: https://36kr.com"
}
```

#### GET /api/research/{task_id}/result

获取任务完成后的结果。

**响应**：
```json
{
  "task_id": "task_20260227_123456_abc123",
  "status": "completed",
  "result": {
    "query": "找人工智能新闻网站",
    "total_sites": 10,
    "successful_sites": 8,
    "failed_sites_count": 2,
    "rankings": [
      {
        "rank": 1,
        "site_name": "机器之心",
        "site_url": "https://www.jiqizhixin.com",
        "quality_score": 92.5,
        "total_records": 15000,
        "difficulty": "easy"
      }
    ]
  }
}
```

---

## 架构

```
Orchestrator（调度器）
├── 战略层
│   ├── requirement_analyzer.py  # 需求分析
│   ├── site_discovery.py        # 候选站挖掘
│   └── result_aggregator.py     # 结果整合
├── 管理层
│   ├── scheduler.py             # 串行调度器
│   ├── agent_runner.py          # Agent 调用 (Mock)
│   ├── state_manager.py         # 状态管理
│   └── monitor.py               # 进度监控
└── 执行层
    ├── chatbox.py               # 用户交互
    ├── presenter.py             # 结果展示
    └── api.py                   # HTTP API
```

更多架构细节见 [ORCHESTRATOR.md](ORCHESTRATOR.md)

---

## 配置

编辑 `config/orchestrator.yaml`：

```yaml
orchestrator:
  llm:
    model: "deepseek-reasoner"
    timeout: 60

  site_discovery:
    min_sites: 10
    max_sites: 30

  scheduler:
    mode: "serial"
    agent_timeout_min: 30
```

---

## 开发

### 运行测试

```bash
# 单元测试
python -m pytest tests/unit/ -v

# 测试 LLM 连接
python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from orchestrator.utils import get_llm_client

async def test():
    client = get_llm_client()
    response = await client.complete(
        system='You are a helpful assistant',
        user='Say: DeepSeek is working',
        temperature=0.7
    )
    print(response)
    await client.close()

asyncio.run(test())
"
```

### 项目结构

```
.
├── config/
│   └── orchestrator.yaml      # 配置文件
├── src/
│   └── orchestrator/
│       ├── api.py              # FastAPI 服务
│       ├── models.py           # 数据模型
│       ├── orchestrator.py     # 主调度器
│       ├── utils.py            # 工具函数
│       ├── execution/          # 执行层
│       ├── management/         # 管理层
│       ├── strategic/          # 战略层
│       └── storage/            # 存储层
├── tests/
│   ├── unit/                   # 单元测试
│   └── integration/            # 集成测试
├── run_local.py                # 本地启动脚本
└── README.md
```

---

## 故障排除

### 问题：服务启动时报编码错误

**原因**：Windows 控制台默认使用 GBK 编码

**解决**：已修复，所有 emoji 已替换为 ASCII 字符

### 问题：DeepSeek API 调用失败

**检查**：
1. 确认 `.env` 文件中 `DEEPSEEK_API_KEY` 已设置
2. 运行测试验证连接：
   ```bash
   python -c "import os; print(os.getenv('DEEPSEEK_API_KEY')[:10])"
   ```
3. 检查网络是否能访问 `api.deepseek.com`

### 问题：前端页面无法访问

**检查**：
1. 确认服务已启动：`python run_local.py`
2. 检查端口 8000 是否被占用
3. 访问 http://localhost:8000/health 查看健康状态

### 问题：任务一直显示运行中但没有结果

**原因**：可能是 LLM 调用超时或返回格式异常

**解决**：
1. 查看控制台日志输出
2. 检查 `task_progress` 是否有更新
3. 重启服务后重试

---

## 后续计划

- [ ] 接入真实 Agent 执行器
- [ ] 添加 PostgreSQL 持久化存储
- [ ] 支持更多数据源类型（电商、金融等）
- [ ] 添加 GitHub Actions CI 自动测试
- [ ] 支持并发调度模式

---

## License

MIT
