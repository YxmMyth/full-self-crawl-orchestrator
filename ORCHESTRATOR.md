# 数据源调研平台 - System Architecture

**Version**: v3.0.0
**Date**: 2026-02-24
**Scope**: 数据源调研平台的整体架构与编排

---

## Core Objective (核心目标)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        三层架构流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    战略层 (Strategic Layer)                   │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │  │
│  │  │ 需求分析    │──▶│ 候选站挖掘   │──▶│ 结果整合    │        │  │
│  │  │ (LLM决策)  │   │ (LLM生成)   │   │ (汇总排序)  │        │  │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘        │  │
│  └───────────────────────────────────────────────┼───────────────┘  │
│                                                  │                  │
│                                                  ▼                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   管理层 (Management Layer)                  │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │  │
│  │  │ 串行调度器   │◀─▶│ Agent交互   │◀─▶│ 状态监控    │        │  │
│  │  │ (任务分发)  │   │ (通信协议)  │   │ (进度跟踪)  │        │  │
│  │  └──────┬──────┘   └─────────────┘   └─────────────┘        │  │
│  └─────────┼────────────────────────────────────────────────────┘  │
│            │                                                       │
│            ▼                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   执行层 (Execution Layer)                   │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │  │
│  │  │ Agent 1 │   │ Agent 2 │   │ Agent 3 │   │  ...   │      │  │
│  │  │ (站点A) │   │ (站点B) │   │ (站点C) │   │         │      │  │
│  │  └────┬────┘   └────┬────┘   └────┬────┘   └─────────┘      │  │
│  └───────┼────────────┼────────────┼────────────────────────────┘  │
│          │            │            │                               │
│          └────────────┴────────────┴───────────▶ 结果上报          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**层级职责**：
- **战略层**：高层决策 - 需求分析、候选站生成、结果整合
- **管理层**：执行管理 - 任务调度、Agent通信、状态监控
- **执行层**：实际工作 - Agent自主爬取、质量评估、数据采集

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [战略层 (Strategic Layer)](#2-战略层-strategic-layer)
   * [2.1 需求分析模块](#21-需求分析模块)
   * [2.2 候选站挖掘模块](#22-候选站挖掘模块)
   * [2.3 结果整合模块](#23-结果整合模块)
3. [管理层 (Management Layer)](#3-管理层-management-layer)
   * [3.1 串行调度器](#31-串行调度器)
   * [3.2 Orchestrator-Agent 交互](#32-orchestrator-agent-交互)
   * [3.3 状态监控](#33-状态监控)
4. [执行层 (Execution Layer)](#4-执行层-execution-layer)
   * [4.1 Agent 探测](#41-agent-探测)
5. [Data Storage](#5-data-storage)
6. [Configuration](#6-configuration)

---

## 1. System Architecture

### 1.1 三层架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                       数据源调研平台架构                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ╔═════════════════════════════════════════════════════════════════╗│
│  ║                    战略层 (Strategic)                          ║│
│  ║  ┌───────────┐  ┌───────────┐  ┌───────────┐                  ║│
│  ║  │需求分析   │─▶│候选站挖掘 │─▶│结果整合   │                  ║│
│  ║  │LLM 决策   │  │LLM 生成   │  │汇总排序   │                  ║│
│  ║  └───────────┘  └───────────┘  └─────┬─────┘                  ║│
│  ╚══════════════════════════════════════┼═════════════════════════╝│
│                                         │                         │
│                                         ▼                         │
│  ╔═════════════════════════════════════════════════════════════════╗│
│  ║                   管理层 (Management)                          ║│
│  ║  ┌───────────┐  ┌───────────┐  ┌───────────┐                  ║│
│  ║  │串行调度器 │◀─▶│Agent交互  │◀─▶│状态监控   │                  ║│
│  ║  │任务分发   │  │通信协议   │  │进度跟踪   │                  ║│
│  ║  └─────┬─────┘  └───────────┘  └───────────┘                  ║│
│  ╚══════┼═════════════════════════════════════════════════════════╝│
│         │                                                          │
│         ▼                                                          │
│  ╔═════════════════════════════════════════════════════════════════╗│
│  ║                   执行层 (Execution)                           ║│
│  ║  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             ║│
│  ║  │ Agent 1 │ │ Agent 2 │ │ Agent 3 │ │  ...   │             ║│
│  ║  │ 站点A   │ │ 站点B   │ │ 站点C   │ │         │             ║│
│  ║  └────┬────┘ └────┬────┘ └────┬────┘ └─────────┘             ║│
│  ╠══════╪═══════════╪═════════╪═════════╪═════════════════════════╣│
│  ║      │           │           │           │                     ║│
│  ╚══════┴───────────┴───────────┴───────────┴─────────────────────╝│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 层级职责矩阵

| 层级 | 职责 | 关键决策 | 执行方式 |
|------|------|----------|----------|
| **战略层** | 高层决策 | 做什么、做多少、怎么做 | LLM 推理 |
| **管理层** | 执行管理 | 谁来做、何时做、如何协调 | 调度算法 |
| **执行层** | 实际工作 | 具体实现、细节处理 | Agent 自主 |

### 1.3 模块关系图

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator                          │
│                                                         │
│  ╔═════════════════════════════════════════════════════╗│
│  ║              战略层 (Strategic)                     ║│
│  ║  ┌─────────┐   ┌─────────┐   ┌─────────┐          ║│
│  ║  │需求分析 │──▶│候选站挖掘│──▶│结果整合 │          ║│
│  ║  └─────────┘   └─────────┘   └────┬────┘          ║│
│  ╚══════════════════════════════════┼═════════════════╝│
│                                   │                     │
│                                   ▼                     │
│  ╔═════════════════════════════════════════════════════╗│
│  ║             管理层 (Management)                     ║│
│  ║  ┌─────────┐   ┌─────────┐   ┌─────────┐          ║│
│  ║  │调度器   │◀─▶│交互协议 │◀─▶│状态监控 │          ║│
│  ║  └────┬────┘   └─────────┘   └─────────┘          ║│
│  ╚══════┼═════════════════════════════════════════════╝│
│         │                                               │
│         ▼                                               │
│  ╔═════════════════════════════════════════════════════╗│
│  ║             执行层 (Execution)                      ║│
│  ║              Agent Pool (多个Agent)                  ║│
│  ╚═════════════════════════════════════════════════════╝│
└─────────────────────────────────────────────────────────┘
```

---

## 2. 战略层 (Strategic Layer)

> **职责定位**：负责高层决策，决定"做什么"、"做多少"、"怎么做"。

### 2.1 需求分析模块

#### 2.1.1 功能描述

通过 Chatbox 与用户交互，理解用户调研意图，精确化需求规格。

#### 2.1.2 交互流程

```
┌─────────────────────────────────────────────────────────────┐
│                     Chatbox 交互流程                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   用户                        系统                          │
│    │                          │                             │
│    │  "我想找科技媒体数据源"    │                             │
│    ├─────────────────────────▶│                             │
│    │                          │  1. LLM 解析需求            │
│    │                          │  2. 抽取字段、范围          │
│    │                          ▼                             │
│    │  "我理解你想要:           │                             │
│    │   - 主题: 科技媒体         │                             │
│    │   - 字段: 标题、作者、时间  │                             │
│    │   - 范围: 国内             │                             │
│    │   确认吗？(Y/N/修改)"      │                             │
│    │◀─────────────────────────┤                             │
│    │  "Y"                     │                             │
│    ├─────────────────────────▶│                             │
│    │                          │  需求确认，传递给候选站挖掘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.1.3 消息格式

**用户输入**:
```yaml
user_message:
  type: "user_input"
  content: str                 # 自然语言文本
  timestamp: str
```

**系统回复 (需求确认)**:
```yaml
system_message:
  type: "requirement_confirm"
  content:
    parsed:
      topic: str
      target_fields: List[str]
      scope: str
      time_range: str
      quantity: int
      constraints: Dict
    prompt: "确认吗？(Y/N/修改)"
  timestamp: str
```

#### 2.1.4 输出规格

```yaml
refined_requirement:
  topic: str                    # 调研主题
  target_fields: List[str]      # 目标字段
  scope: str                    # 范围限制
  time_range: str               # 时间范围
  quantity: int                 # 期望数量
  constraints: Dict             # 其他约束
```

---

### 2.2 候选站挖掘模块

#### 2.2.1 功能描述

基于精确化后的需求，使用 LLM 生成真实候选站点列表。

#### 2.2.2 输入输出

**输入**:
```yaml
refined_requirement: Dict  # 来自需求分析模块
```

**输出**:
```yaml
candidate_sites:
  - site_name: str
    site_url: str
    description: str
    priority: int  # 优先级
```

#### 2.2.3 示例

```yaml
输入:
  topic: 科技媒体
  scope: 国内

输出:
  - site_name: 36氪
    site_url: https://36kr.com
    description: 创投科技媒体
    priority: 1
  - site_name: 虎嗅
    site_url: https://www.huxiu.com
    description: 商业科技媒体
    priority: 2
  - site_name: 钛媒体
    site_url: https://www.tmtpost.com
    description: 科技财经媒体
    priority: 3
  ... (共 10-20+ 个站点)
```

---

### 2.3 结果整合模块

#### 2.3.1 功能描述

汇总所有 Agent 的探测结果，排序展示，支持样例数据查看。

#### 2.3.2 整合输出

```yaml
research_result:
  query: str                    # 用户原始需求
  total_sites: int              # 总探测站点数
  successful_sites: int         # 成功站点数

  # 站点排行榜 (按质量分数排序)
  rankings:
    - rank: 1
      site_name: 36kr.com
      quality_score: 92
      total_records: 15000+
      samples: [...]            # 样例数据
    - rank: 2
      site_name: ifanr.com
      quality_score: 88
      total_records: 8000+
      samples: [...]
    ...

  # 失败站点
  failed_sites:
    - site_url: xxx.com
      reason: blocked
```

#### 2.3.3 展示界面

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 数据源调研平台                                [已完成]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📋 需求: 科技媒体数据源                                         │
│  📊 探测结果: 成功 8/10 站点                                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    站点排行榜                            │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ 🥇 36kr.com                                              │  │
│  │    质量分: 92/100  │  数据量: 15000+  │  难度: 简单     │  │
│  │    [查看样例] [立即接入]                                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ 🥈 ifanr.com                                             │  │
│  │    质量分: 88/100  │  数据量: 8000+   │  难度: 简单     │  │
│  │    [查看样例] [立即接入]                                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ 🥉 huxiu.com                                             │  │
│  │    质量分: 85/100  │  数据量: 12000+  │  难度: 中等     │  │
│  │    [查看样例] [立即接入]                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ⚠️  失败站点:                                                  │
│  - xxx.com (被阻止)                                             │
│  - yyy.com (结构变化)                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.4 样例数据展示

点击"查看样例"后：

```
┌─────────────────────────────────────────────────────────────────┐
│  样例数据 - 36kr.com                              [共 5 条]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 标题: AI大模型新一轮融资热潮开启                              │
│     作者: 张三                                                  │
│     时间: 2026-02-23                                           │
│     URL: https://36kr.com/p/xxxxx                              │
│     正文: ... (预览前200字)                                     │
│                                                                 │
│  2. 标题: 新能源汽车销量创新高                                   │
│     作者: 李四                                                  │
│     时间: 2026-02-22                                           │
│     ...                                                         │
│                                                                 │
│  [导出全部] [返回列表]                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 管理层 (Management Layer)

> **职责定位**：负责具体执行，决定"谁来做"、"何时做"、"如何协调"。

### 3.1 串行调度器

#### 3.1.1 功能描述

将候选站点按顺序分派给 Agent，一个一个执行。

#### 3.1.2 调度流程

```
候选站点列表
     │
     ▼
┌─────────────────┐
│   任务队列      │
│   (FIFO)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   串行执行      │
│   一个一个来    │
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │  Agent  │ ◀───┐
    │ (站点A) │     │
    └────┬────┘     │
         │          │
         │ 完成     │
         ▼          │
    ┌─────────┐     │
    │  Agent  │ ◀───┘
    │ (站点B) │
    └────┬────┘
         │
         ▼
       ... 以此类推
```

#### 3.1.3 配置

```yaml
scheduler:
  mode: "serial"               # 串行模式
  agent_timeout_min: 30        # Agent 超时时间
```

---

### 3.2 Orchestrator-Agent 交互

#### 3.2.1 交互架构

```
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator - Agent 交互流程                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                  ┌──────────────┐        │
│  │Orchestrator  │                  │    Agent     │        │
│  └──────┬───────┘                  └──────┬───────┘        │
│         │                                  │                │
│         │  1. 启动任务                     │                │
│         │  - site_url                     │                │
│         │  - requirement                  │                │
│         ├─────────────────────────────────▶│                │
│         │                                  │                │
│         │                                  │  SOOAL 循环    │
│         │                                  │  (自主探测)    │
│         │                                  │                │
│         │  2. 进度上报 (Agent主动)          │                │
│         │◀─────────────────────────────────┤                │
│         │  - current_url                   │                │
│         │  - progress %                    │                │
│         │  - collected_count               │                │
│         │                                  │                │
│         │  3. 最终返回                      │                │
│         │◀─────────────────────────────────┤                │
│         │  - quality_score                 │                │
│         │  - total_records                 │                │
│         │  - samples                       │                │
│         │                                  │                │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.2 启动任务

**Orchestrator → Agent**:
```yaml
task_params:
  task_id: str
  site_url: str
  requirement:
    topic: str
    target_fields: List[str]    # [标题, 作者, 发布时间, ...]
    scope: str
    time_range: str
    constraints: Dict
```

#### 3.2.3 进度上报

**Agent → Orchestrator** (Agent 主动上报):
```yaml
progress_update:
  task_id: str
  agent_id: str
  status: "running"
  current_url: str              # 当前正在处理的 URL
  progress: float               # 0.0 - 1.0
  collected_count: int          # 已采集数量
  timestamp: str
```

#### 3.2.4 最终返回

**Agent → Orchestrator**:
```yaml
task_result:
  task_id: str
  agent_id: str
  site_url: str
  site_name: str

  # Agent 自主评估
  quality_score: float          # 质量评分 (0-100)
  total_pages: int
  total_records: int

  # 样例数据
  samples: List[Dict]

  # 探测元信息
  duration_sec: int
  strategy_used: str
  difficulty: str
  anti_bot: List[str]

  status: "success" | "failed"
  error_message: str            # 失败时填写
```

#### 3.2.5 超时处理

| 场景 | 处理方式 |
|------|----------|
| Agent 超时无响应 | 取消任务，记录日志，继续下一个 |
| Agent 返回失败 | 记录日志，继续下一个 |
| Agent 主动上报进度 | 更新进度，不做额外处理 |

---

### 3.3 状态监控

#### 3.3.1 功能描述

实时监控任务执行状态，提供进度反馈，支持用户查看和干预。

#### 3.3.2 监控指标

```yaml
monitor_metrics:
  task_id: str
  total_sites: int
  completed_sites: int
  failed_sites: int
  current_agent: str
  current_site: str
  estimated_completion: str
  progress_percentage: float
```

#### 3.3.3 进度推送

**系统回复 (进度更新)**:
```yaml
system_message:
  type: "progress_update"
  content:
    task_id: str
    completed: int
    total: int
    current_site: str
  timestamp: str
```

**系统回复 (任务完成)**:
```yaml
system_message:
  type: "task_completed"
  content:
    task_id: str
    rankings: List[Dict]       # 站点排行榜
    failed_sites: List[Dict]   # 失败站点
  timestamp: str
```

**系统回复 (任务取消)**:
```yaml
system_message:
  type: "task_cancelled"
  content:
    task_id: str
    reason: str
  timestamp: str
```

**系统回复 (错误通知)**:
```yaml
system_message:
  type: "error_message"
  content:
    task_id: str
    error: str
    can_retry: bool
  timestamp: str
```

#### 3.3.4 交互示例

```
你: 我想找科技媒体的数据源，主要看文章标题、作者、发布时间

系统: 我理解你想要:
       - 主题: 科技媒体
       - 字段: 标题、作者、发布时间、正文、标签
       - 范围: 国内
       - 时间范围: 近一年
       - 期望数量: 1000+
       确认吗？(Y/N/修改)

你: Y

系统: 已开始探测 15 个站点，预计 5 分钟完成

[进度推送] ████████████░░░░ 60% (9/15 完成)

[进度推送] ██████████████░░░ 80% (12/15 完成)

[完成] 探测完成！成功 12/15 站点

=== 站点排行榜 ===
🥇 36kr.com - 质量分 92，数据量 15000+
🥈 ifanr.com - 质量分 88，数据量 8000+
🥉 huxiu.com - 质量分 85，数据量 12000+
...
```

---

## 4. 执行层 (Execution Layer)

> **职责定位**：负责实际工作，具体实现、细节处理由 Agent 自主完成。

### 4.1 Agent 探测

> **说明**：执行层详细设计将在 AGENT.md 中单独描述。本节仅概述 Agent 与管理层的接口。

#### 4.1.1 Agent 职责

每个 Agent 独立负责一个站点的探测工作：
- 访问目标站点
- 分析站点结构
- 采集样例数据
- 自主评估质量
- 返回探测结果

#### 4.1.2 Agent 工作流程 (SOOAL)

```
┌─────────────────────────────────────────────────────────────┐
│                    SOOAL 自主探测循环                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │
│  │  Observe│──▶│  Orient │──▶│  Decide │──▶│  Act   │    │
│  │  观察   │   │  定向   │   │  决策   │   │  行动  │    │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘    │
│       └────────────┴────────────┴────────────┴────────┘    │
│                           │                                 │
│                           ▼                                 │
│                    ┌─────────────┐                          │
│                    │  Learn      │                          │
│                    │  学习优化    │                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│                           └──────────────┐                   │
│                                          │                   │
│                             达成目标 或 达到上限               │
│                                          │                   │
│                                          ▼                   │
│                                    ┌─────────────┐            │
│                                    │  返回结果   │            │
│                                    └─────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.1.3 Agent 接口 (与管理层对接)

**接收** (来自管理层):
```yaml
task_params:
  task_id: str
  site_url: str
  requirement: Dict
```

**主动上报** (发给管理层):
```yaml
progress_update:
  task_id: str
  agent_id: str
  status: str
  current_url: str
  progress: float
  collected_count: int
```

**最终返回** (发给管理层):
```yaml
task_result:
  task_id: str
  agent_id: str
  site_url: str
  site_name: str
  quality_score: float
  total_records: int
  samples: List[Dict]
  status: str
```

---

## 5. Data Storage

### 5.1 存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   Agent     │────▶│   Redis     │────▶│ PostgreSQL  │  │
│  │             │     │  (Hot Data) │     │ (Cold Data) │  │
│  └─────────────┘     └─────────────┘     └─────────────┘  │
│                             │                   │         │
│                             ▼                   ▼         │
│                        ┌──────────┐        ┌──────────┐    │
│                        │ 任务队列  │        │ 调研记录  │    │
│                        │ Agent状态 │        │ 样本数据  │    │
│                        │ 进度同步  │        │ 站点知识  │    │
│                        └──────────┘        └──────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Redis 队列

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `task:queue` | List | 待处理站点任务 | - |
| `task:running` | Hash | 运行中任务状态 | 1h |
| `agent:{id}:state` | Hash | Agent 实时状态 | 1h |
| `agent:{id}:progress` | Hash | Agent 进度 | 1h |
| `result:cache` | String | 结果缓存 | 24h |

### 5.3 PostgreSQL 表

```sql
-- 调研任务记录
CREATE TABLE research_tasks (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    user_query TEXT NOT NULL,
    refined_requirement JSONB DEFAULT '{}',

    candidate_sites JSONB DEFAULT '[]',
    total_sites INTEGER DEFAULT 0,
    successful_sites INTEGER DEFAULT 0,

    status TEXT NOT NULL,  -- pending/running/completed/failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 站点探测结果
CREATE TABLE site_results (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL,
    site_url TEXT NOT NULL,
    site_name TEXT,

    quality_score FLOAT,
    total_records INTEGER,
    sample_records JSONB DEFAULT '[]',

    duration_sec INTEGER,
    strategy_used TEXT,
    difficulty TEXT,

    status TEXT,  -- success/failed
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- 样本数据存储
CREATE TABLE sample_records (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL,
    site_url TEXT NOT NULL,
    record_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_site_results_task ON site_results(task_id);
CREATE INDEX idx_site_results_score ON site_results(quality_score);
CREATE INDEX idx_samples_task ON sample_records(task_id);
```

---

## 6. Configuration

### 6.1 全局配置

```yaml
# config/orchestrator.yaml
orchestrator:
  # LLM 配置
  llm:
    model: "GLM-4.7"
    api_key: "${LLM_API_KEY}"
    temperature: 0.7

  # 需求分析配置 (战略层)
  requirement:
    max_clarify_rounds: 3    # 最大澄清轮次

  # 候选站挖掘配置 (战略层)
  site_discovery:
    min_sites: 10            # 最少站点数
    max_sites: 30            # 最多站点数

  # 调度器配置 (管理层)
  scheduler:
    mode: "serial"               # 串行模式 (LLM 资源受限)
    agent_timeout_min: 30        # Agent 超时时间

  # 监控配置 (管理层)
  monitor:
    progress_update_interval: 5  # 进度更新间隔(秒)
    enable_realtime_push: true   # 实时推送

  # 存储配置
  storage:
    redis_url: "redis://localhost:6379"
    postgres_dsn: "postgres://user:pass@localhost/crawler"
```

---

**Document Version**: 3.0.0
**Last Updated**: 2026-02-24
