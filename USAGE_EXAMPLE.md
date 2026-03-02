# Agent调用示例

在数据源调研平台中，Orchestrator与Agent的调用机制已经成功实现。以下是使用示例：

## 1. 三种运行模式配置

根据 `config/orchestrator.yaml`，Orchestrator 支持三种 Agent 运行模式：

```yaml
agent:
  path: "../full-self-crawl-agent"    # Agent项目路径
  mode: "subprocess"                  # 运行模式: docker/subprocess/mock
  image: "full-self-crawl-agent:latest"  # Docker镜像（Docker模式下）
  memory_limit: "2g"                  # 资源限制
  timeout_sec: 1800                   # 超时设置
```

## 2. 任务调用流程

### 任务准备阶段
Orchestrator 将用户需求转化为 `TaskParams` 对象：

```python
from src.orchestrator.models import TaskParams, RefinedRequirement

requirement = RefinedRequirement(
    topic="科技新闻数据源",
    target_fields=["标题", "作者", "发布时间"],
    scope="中文科技媒体"
)

task_params = TaskParams(
    task_id="task_001:https://36kr.com",
    site_url="https://36kr.com",
    site_name="36氪",
    requirement=requirement
)
```

### Agent 启动阶段
通过 `AgentRunner` 类根据配置模式启动 Agent：

```python
from src.orchestrator.management.agent_runner import AgentRunner

runner = AgentRunner(
    agent_path="../full-self-crawl-agent",
    mode="subprocess",  # 或 "docker" 或 "mock"
    agent_image="full-self-crawl-agent:latest"
)

# 启动 Agent 并执行任务
result = await runner.run(task_params)
```

### 结果返回阶段
Agent 完成任务后返回 `TaskResult` 对象：

```python
from src.orchestrator.models import TaskResult

# Agent 返回的结果包括：
# - quality_score: 质量评分 (0-100)
# - total_records: 采集记录数
# - samples: 样例数据
# - status: 任务状态
result: TaskResult = {
    "task_id": "task_001:https://36kr.com",
    "site_url": "https://36kr.com",
    "site_name": "36氪",
    "quality_score": 92.5,
    "total_records": 1500,
    "samples": [
        {"标题": "人工智能新突破", "作者": "张三", "发布时间": "2024-01-01"},
        # ... 更多样例数据
    ],
    "status": "success"
}
```

## 3. 完整使用示例

通过 `run_local.py` 启动整个系统：

```python
from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.config import OrchestratorConfig

# 初始化 Orchestrator
config = OrchestratorConfig()
orchestrator = Orchestrator(config)

# 启动调研任务
async def progress_callback(update):
    print(f"进度: {update.progress * 100}% - {update.message}")

result = await orchestrator.run_research(
    user_input="寻找科技新闻数据源，包含标题、作者、发布时间",
    progress_callback=progress_callback
)

print(f"成功找到 {result.successful_sites}/{result.total_sites} 个高质量数据源")
```

## 4. 接口契约

详细的接口契约定义见 `AGENT_INTERFACE.md`，包括：
- TaskParams (Orchestrator → Agent)
- TaskResult (Agent → Orchestrator)
- 7种核心能力定义
- SmartRouter 三层决策机制
- 质量评估体系
- 异常处理机制

## 5. 验证结果

系统已完成以下验证：
- ✓ 本地开发验证：subprocess 模式运行正常
- ✓ 参数传递验证：TaskParams 正确传递给 Agent
- ✓ 进度上报验证：Agent 按预期上报进度信息
- ✓ 结果评估验证：质量评分和样本数据格式正确
- ✓ 错误处理验证：Agent 失败场景处理正常

该实现在战略层、管理层、执行层三个层面实现了 Orchestrator 与 Agent 的有效协同工作。