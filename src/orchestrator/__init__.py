"""
Orchestrator - [数据源调研平台调度器]

[提供三层架构实现：]
- [战略层：需求分析、候选站挖掘、结果整合]
- [管理层：串行调度、]Agent[交互、状态监控]
- [执行层：]Chatbox[交互、结果展示]
"""

__version__ = "3.0.0"
__author__ = "Orchestrator Team"

from orchestrator.config import OrchestratorConfig, get_config
from orchestrator.models import (
    CandidateSite,
    ProgressUpdate,
    RefinedRequirement,
    ResearchResult,
    SiteRanking,
    FailedSite,
    TaskParams,
    TaskResult,
)
from orchestrator.orchestrator import Orchestrator
from orchestrator.strategic.requirement_analyzer import RequirementAnalyzer
from orchestrator.strategic.site_discovery import SiteDiscovery
from orchestrator.strategic.result_aggregator import ResultAggregator
from orchestrator.management.scheduler import SerialScheduler
from orchestrator.management.agent_runner import AgentRunner
from orchestrator.management.state_manager import StateManager
from orchestrator.management.monitor import Monitor

__all__ = [
    # [版本]
    "__version__",
    # [主类]
    "Orchestrator",
    # Config
    "OrchestratorConfig",
    "get_config",
    # Strategic Layer
    "RequirementAnalyzer",
    "RefinedRequirement",
    "SiteDiscovery",
    "CandidateSite",
    "ResultAggregator",
    "ResearchResult",
    "SiteRanking",
    "FailedSite",
    # Management Layer
    "SerialScheduler",
    "AgentRunner",
    "TaskParams",
    "TaskResult",
    "StateManager",
    "Monitor",
    "ProgressUpdate",
]
