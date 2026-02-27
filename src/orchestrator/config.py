"""[配置管理模块]"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# [加载环境变量]
load_dotenv()


@dataclass
class LLMConfig:
    """LLM [配置]"""
    model: str = "GLM-4.7"
    api_key: str = ""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class RequirementConfig:
    """[需求分析配置]"""
    max_clarify_rounds: int = 3
    default_quantity: int = 1000
    default_time_range: str = "[近一年]"


@dataclass
class SiteDiscoveryConfig:
    """[候选站挖掘配置]"""
    min_sites: int = 10
    max_sites: int = 30
    default_priority: int = 5
    priority_threshold: int = 5


@dataclass
class SchedulerConfig:
    """[调度器配置]"""
    mode: str = "serial"  # "serial" 或 "concurrent"
    max_concurrency: int = 3  # 并发模式下的最大并发数
    agent_timeout_min: int = 30
    max_retries: int = 2
    retry_delay_sec: int = 5


@dataclass
class MonitorConfig:
    """[监控配置]"""
    progress_update_interval: int = 5
    enable_realtime_push: bool = True
    heartbeat_interval: int = 10
    log_level: str = "INFO"


@dataclass
class RedisConfig:
    """Redis [配置]"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    ssl: bool = False
    socket_timeout: int = 30
    socket_connect_timeout: int = 5
    url: str = "redis://localhost:6379/0"
    connection_pool_size: int = 10


@dataclass
class PostgresConfig:
    """PostgreSQL [配置]"""
    host: str = "localhost"
    port: int = 5432
    database: str = "crawler"
    user: str = "crawler"
    password: str = "crawler"
    min_pool_size: int = 5
    max_pool_size: int = 20
    command_timeout: int = 60
    dsn: str = "postgresql://user:pass@localhost:5432/crawler"
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: int = 30


@dataclass
class StorageConfig:
    """[存储配置]"""
    redis: RedisConfig = field(default_factory=RedisConfig)
    postgres: PostgresConfig = field(default_factory=PostgresConfig)


@dataclass
class AgentConfig:
    """Agent [配置]"""
    path: str = "../full-self-crawl-agent"
    module: str = "full_self_crawl_agent"
    timeout_sec: int = 1800
    python_executable: str = "python"


@dataclass
class LoggingConfig:
    """[日志配置]"""
    level: str = "INFO"
    format: str = "structured"
    output: str = "stdout"
    file_path: str = "logs/orchestrator.log"
    rotation: str = "1 day"
    retention: str = "30 days"


@dataclass
class OrchestratorConfig:
    """Orchestrator [全局配置]"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    requirement: RequirementConfig = field(default_factory=RequirementConfig)
    site_discovery: SiteDiscoveryConfig = field(default_factory=SiteDiscoveryConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorConfig":
        """[从字典创建配置]"""
        return cls(
            llm=LLMConfig(**data.get("llm", {})),
            requirement=RequirementConfig(**data.get("requirement", {})),
            site_discovery=SiteDiscoveryConfig(**data.get("site_discovery", {})),
            scheduler=SchedulerConfig(**data.get("scheduler", {})),
            monitor=MonitorConfig(**data.get("monitor", {})),
            storage=StorageConfig(
                redis=RedisConfig(**data.get("storage", {}).get("redis", {})),
                postgres=PostgresConfig(**data.get("storage", {}).get("postgres", {})),
            ),
            agent=AgentConfig(**data.get("agent", {})),
            logging=LoggingConfig(**data.get("logging", {})),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "OrchestratorConfig":
        """[从] YAML [文件加载配置]"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # [展开环境变量]
        data = _expand_env_vars(data)

        return cls.from_dict(data.get("orchestrator", {}))


def _expand_env_vars(obj: Any) -> Any:
    """[递归展开对象中的环境变量]"""
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # [支持] ${VAR} [和] ${VAR:-default} [语法]
        import re

        def replace_env_var(match: Any) -> str:
            var_expr = match.group(1)
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
                return os.getenv(var_name, default)
            return os.getenv(var_expr, "")

        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_env_var, obj)
    return obj


# [全局配置实例]
_config: Optional[OrchestratorConfig] = None


def get_config(config_path: Optional[str] = None) -> OrchestratorConfig:
    """[获取全局配置实例]"""
    global _config

    if _config is None:
        if config_path is None:
            # [默认配置文件路径]
            config_path = os.getenv(
                "ORCHESTRATOR_CONFIG",
                str(Path(__file__).parent.parent.parent / "config" / "orchestrator.yaml")
            )

        if Path(config_path).exists():
            _config = OrchestratorConfig.from_yaml(config_path)
        else:
            # [使用默认配置]
            _config = OrchestratorConfig()

    return _config


def set_config(config: OrchestratorConfig) -> None:
    """[设置全局配置实例]"""
    global _config
    _config = config
