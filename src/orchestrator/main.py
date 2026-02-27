"""[主入口模块]"""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog

# [添加项目根目录到路径]
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.config import get_config
from orchestrator.execution.chatbox import Chatbox

logger = structlog.get_logger()


def setup_logging(log_level: str = "INFO", format_type: str = "structured") -> None:
    """[设置日志]"""
    import logging

    if format_type == "structured":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


async def interactive_mode() -> None:
    """[交互模式]"""
    config = get_config()
    chatbox = Chatbox(config)

    try:
        await chatbox.start_conversation()
    except KeyboardInterrupt:
        print("\n\n[用户取消操作，退出中]...")
    except Exception as e:
        logger.error("[运行时错误]", error=str(e))
        raise


def main() -> int:
    """[主函数]"""
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="[数据源调研平台] - Orchestrator [调度器]",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="[配置文件路径]",
    )

    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="[日志级别]",
    )

    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="[测试模式]",
    )

    args = parser.parse_args()

    # [加载配置]
    if args.config:
        config = get_config(args.config)
    else:
        config = get_config()

    # [设置日志]
    setup_logging(args.log_level, config.logging.format)

    logger.info(
        "Orchestrator [启动]",
        version="3.0.0",
        log_level=args.log_level,
    )

    if args.test_mode:
        # [测试模式]
        return run_test_mode()

    # [运行交互模式]
    try:
        asyncio.run(interactive_mode())
        return 0
    except Exception as e:
        logger.error("[程序异常退出]", error=str(e))
        return 1


def run_test_mode() -> int:
    """[测试模式]"""
    print("=" * 60)
    print("Orchestrator [测试模式]")
    print("=" * 60)

    # [测试配置加载]
    config = get_config()
    print(f"\n[✓] [配置加载成功]")
    print(f"  - LLM [模型]: {config.llm.model}")
    print(f"  - [调度模式]: {config.scheduler.mode}")
    print(f"  - Agent [超时]: {config.scheduler.agent_timeout_min} [分钟]")

    # [测试模型导入]
    print(f"\n[✓] [模型导入成功]")
    from orchestrator.models import RefinedRequirement, CandidateSite, TaskParams

    req = RefinedRequirement(topic="[科技媒体]", target_fields=["[标题]", "[作者]"])
    site = CandidateSite(site_name="36[氪]", site_url="https://36kr.com", priority=1)
    print(f"  - RefinedRequirement: {req.topic}")
    print(f"  - CandidateSite: {site.site_name}")

    print("\n" + "=" * 60)
    print("[所有测试通过]!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
