# Agent接口与契约定义

本文档定义了 Orchestrator 与 Agent 之间的接口契约，确保双方按照统一规范协作。

## 架构对比

| 层级 | Orchestrator | Agent |
|------|--------------|-------|
| 高层 | 战略层（需求分析/候选站挖掘/结果整合） | 战略层（Spec/Policy/Gate） |
| 中层 | 管理层（调度器/Agent交互/状态监控） | 管理层（Orchestrator/State/SmartRouter） |
| 低层 | 执行层（Agent Pool） | 执行层（AgentPool 7种能力） |

## 交互边界

```
Orchestrator（调度器）          Agent（执行器）
     │                              │
     │── task_params ──────────────▶│
     │   (site_url, requirement)    │
     │                              │
     │◀─ progress_update ───────────│
     │   (主动上报，每5-10秒)        │
     │                              │
     │◀── task_result ──────────────│
     │   (quality_score, samples)   │
```

## 数据模型契约

### TaskParams (Orchestrator → Agent)

定义了传给 Agent 的任务参数：

```python
class TaskParams(BaseModel):
    task_id: str           # 任务唯一标识
    site_url: str          # 目标站点URL
    site_name: str         # 目标站点名称
    requirement: RefinedRequirement  # 需求规格
```

其中 `requirement` 包含：
- `topic`: 研究主题
- `target_fields`: 目标字段列表
- `scope`: 范围限制
- `time_range`: 时间范围
- `quantity`: 期望数量

### TaskResult (Agent → Orchestrator)

定义了 Agent 返回的任务结果：

```python
class TaskResult(BaseModel):
    task_id: str           # 任务ID
    site_url: str          # 目标站点URL
    site_name: str         # 目标站点名称
    quality_score: float   # 质量评分 (0-100)
    total_pages: int       # 探测页面数
    total_records: int     # 采集记录数
    samples: List[Dict]    # 样例数据
    duration_sec: int      # 执行时长(秒)
    strategy_used: str     # 使用的策略
    status: str            # 任务状态 (success/failed)
    error_message: str     # 错误信息（失败时）
```

## 7种能力定义

Agent具备以下7种核心能力，这些能力由 Orchestrator 调用：

1. **Sense**: 感知页面结构和特征
2. **Plan**: 规划数据提取策略
3. **Act**: 执行具体的数据提取操作
4. **Verify**: 验证提取数据的质量
5. **Gate**: 检查完成条件是否满足
6. **Judge**: 决策后续行动
7. **Reflect**: 反思并优化策略

## 输入/输出契约

### 启动方式
- **Subprocess模式**: `python -m src.main <spec_path>` (本地开发)
- **Docker模式**: 启动容器，通过环境变量传递SPEC (生产)
- **Mock模式**: 模拟执行 (测试)

### 输出格式
Agent 必须以 JSON 格式输出 `TaskResult` 对象。

## SmartRouter 三层决策

Agent 内部的 SmartRouter 根据以下因素进行路由决策：
1. **上下文分析**: 分析当前页面内容和结构
2. **策略选择**: 根据内容特点选择最适合的提取策略
3. **资源管理**: 控制计算资源和网络资源的使用

## 质量评估体系

Agent 使用以下指标评估数据质量：
- **完整性**: 提取字段的完整程度
- **准确性**: 数据的准确程度
- **时效性**: 数据的时间相关性
- **一致性**: 数据在不同页面的一致性

## 异常处理机制

### 超时处理
- 单个 Agent 执行超时限制为 30 分钟
- 超时后 Orchestrator 会收到失败结果

### 错误恢复
- 网络错误会尝试重连
- 识别反爬机制并调整策略
- 严重错误时终止任务并报告

## 运行模式配置

通过 `orchestrator.yaml` 配置运行模式：

```yaml
agent:
  path: "../full-self-crawl-agent"    # Agent项目路径
  mode: "subprocess"                  # 运行模式: docker/subprocess/mock
  image: "full-self-crawl-agent:latest"  # Docker镜像
  memory_limit: "2g"                  # 内存限制
  timeout_sec: 1800                   # 超时设置
```

## 进度报告机制

- **频率**: 每 5-10 秒主动上报一次进度
- **内容**: 当前处理URL、进度百分比、状态消息
- **通道**: 通过 Monitor 系统上报