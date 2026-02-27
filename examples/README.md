# API 请求示例

本文档提供了使用数据源调研平台 API 的示例代码。

## 快速开始

确保 Orchestrator 服务正在运行：

```bash
python run_local.py
# 或使用 uvicorn
uvicorn orchestrator.api:app --reload --host 0.0.0.0 --port 8000
```

## 可用示例

### 1. cURL 示例 (`curl_examples.sh`)

适用于命令行快速测试。

```bash
# 使脚本可执行
chmod +x curl_examples.sh

# 运行示例
./curl_examples.sh
```

主要展示：
- 健康检查
- 启动调研任务
- 获取任务状态
- 获取任务结果
- SSE 进度流

### 2. Python 客户端 (`python_client.py`)

适用于集成到 Python 应用程序。

```bash
# 安装依赖
pip install httpx

# 运行示例
python python_client.py
```

主要功能：
- 完整的客户端类封装
- 异步 API 调用
- 自动轮询等待结果
- SSE 流式进度接收

## API 端点说明

### 健康检查
```
GET /health
```

### 启动调研任务
```
POST /api/research
Content-Type: application/json

{
  "query": "找科技媒体的数据源"
}
```

### 获取任务状态
```
GET /api/research/{task_id}/status
```

### 获取任务结果
```
GET /api/research/{task_id}/result
```

### SSE 进度流
```
GET /api/research/{task_id}/progress
Accept: text/event-stream
```

## 响应格式

### 任务启动响应
```json
{
  "task_id": "task_20260227_123456_abc12345",
  "status": "started",
  "message": "调研任务已启动，共需探测多个站点"
}
```

### 任务状态响应
```json
{
  "task_id": "task_20260227_123456_abc12345",
  "status": "running",
  "progress": 0.5,
  "current_site": "https://36kr.com",
  "message": "正在探测: 36氪"
}
```

### 任务结果响应
```json
{
  "task_id": "task_20260227_123456_abc12345",
  "status": "completed",
  "result": {
    "query": "找科技媒体的数据源",
    "task_id": "task_20260227_123456_abc12345",
    "total_sites": 10,
    "successful_sites": 8,
    "failed_sites_count": 2,
    "rankings": [
      {
        "rank": 1,
        "site_name": "36氪",
        "site_url": "https://36kr.com",
        "quality_score": 92.5,
        "total_records": 1000,
        "difficulty": "easy",
        "samples": []
      }
    ],
    "failed_sites": [],
    "total_duration_sec": 1800
  }
}
```

## 使用场景

### 场景 1: 简单调研
```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/research",
    json={"query": "找新闻网站数据源"}
)
task_id = response.json()["task_id"]
print(f"任务已启动: {task_id}")
```

### 场景 2: 实时进度监控
```python
import httpx

# 使用 SSE 接收实时进度
with httpx.stream(
    "GET",
    f"http://localhost:8000/api/research/{task_id}/progress",
    headers={"Accept": "text/event-stream"}
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            print(f"进度: {data.get('progress', 0)*100}%")
```

### 场景 3: 轮询获取结果
```python
import time
import httpx

while True:
    response = httpx.get(
        f"http://localhost:8000/api/research/{task_id}/result"
    )
    if response.status_code == 200:
        result = response.json()
        print("任务完成!")
        print(result)
        break
    time.sleep(2)
```

## 错误处理

常见的 HTTP 状态码：

- `200 OK` - 请求成功
- `404 Not Found` - 任务不存在或尚未完成
- `500 Internal Server Error` - 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```
