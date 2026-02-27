# 数据源调研平台 - Orchestrator

基于 DeepSeek LLM 的数据源调研调度器，支持需求分析、候选站点挖掘和实时进度展示。

## 特性

- 🤖 **DeepSeek LLM 驱动**：使用 deepseek-reasoner 模型进行需求分析和站点挖掘
- 🌐 **Web 界面**：内嵌前端，支持实时进度条和日志展示
- 📊 **结果排行榜**：按质量分排序的数据源排行榜
- 🔌 **HTTP API**：FastAPI 提供的 RESTful API 接口
- ⚙️ **Mock Agent**：本地测试模式，无需真实 Agent 执行器

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

编辑 `.env` 文件：

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

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 前端界面 |
| `/api/research` | POST | 启动调研任务 |
| `/api/research/{task_id}/status` | GET | 获取任务状态 |
| `/api/research/{task_id}/result` | GET | 获取任务结果 |
| `/api/research/{task_id}/progress` | GET | 实时进度流 (SSE) |
| `/health` | GET | 健康检查 |

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

## 开发

### 运行测试

```bash
# 单元测试
python -m pytest tests/unit/ -v

# 集成测试
python test_orchestrator.py
```

### 项目结构

```
.
├── config/
│   └── orchestrator.yaml      # 配置文件
├── src/
│   └── orchestrator/
│       ├── __init__.py
│       ├── api.py              # FastAPI 服务
│       ├── config.py           # 配置管理
│       ├── models.py           # 数据模型
│       ├── orchestrator.py     # 主调度器
│       ├── utils.py            # 工具函数
│       ├── execution/          # 执行层
│       ├── management/         # 管理层
│       ├── strategic/          # 战略层
│       └── storage/            # 存储层
├── tests/
│   ├── unit/
│   └── integration/
├── run_local.py                # 本地启动脚本
└── README.md
```

## License

MIT
