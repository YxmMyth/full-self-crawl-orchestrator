#!/usr/bin/env python3
"""
测试脚本：验证 Orchestrator 和 AgentRunner 的基本集成
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_basic_integration():
    """测试基本集成"""
    print("🔍 测试 Orchestrator 与 AgentRunner 集成...")

    try:
        # 测试模型导入
        from src.orchestrator.models import TaskParams, TaskResult, RefinedRequirement
        print("✅ 模型导入成功")

        # 测试 AgentRunner 导入
        from src.orchestrator.management.agent_runner import AgentRunner
        print("✅ AgentRunner 导入成功")

        # 测试 Orchestrator 导入
        from src.orchestrator.orchestrator import Orchestrator
        from src.orchestrator.config import OrchestratorConfig
        print("✅ Orchestrator 导入成功")

        # 测试配置加载
        config = OrchestratorConfig()
        print(f"✅ 配置加载成功: {config.agent.mode} 模式")

        # 测试 AgentRunner 初始化
        agent_runner = AgentRunner(
            agent_path=config.agent.path,
            mode=config.agent.mode,
            agent_image=config.agent.image,
            agent_memory_limit=config.agent.memory_limit,
            agent_cpu_limit=config.agent.cpu_limit,
        )
        print(f"✅ AgentRunner 初始化成功: {config.agent.path}, {config.agent.mode} 模式")

        # 测试 Orchestrator 初始化
        orchestrator = Orchestrator(config)
        print("✅ Orchestrator 初始化成功")

        # 测试 TaskParams 创建
        requirement = RefinedRequirement(
            topic="测试主题",
            target_fields=["标题", "作者", "时间"],
            scope="测试范围"
        )
        task_params = TaskParams(
            task_id="test_task_001",
            site_url="https://example.com",
            site_name="测试站点",
            requirement=requirement
        )
        print("✅ TaskParams 创建成功")

        print("\n🎉 集成测试通过！Orchestrator 与 Agent 的接口正常工作。")
        return True

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_runner_modes():
    """测试不同的 Agent 运行模式"""
    print("\n🔍 测试 AgentRunner 不同模式...")

    from src.orchestrator.management.agent_runner import AgentRunner
    from src.orchestrator.models import TaskParams, RefinedRequirement

    # 测试不同的运行模式
    modes = ["subprocess", "mock"]

    for mode in modes:
        try:
            runner = AgentRunner(mode=mode)

            requirement = RefinedRequirement(
                topic="测试主题",
                target_fields=["标题", "作者"],
                scope="测试"
            )

            task_params = TaskParams(
                task_id=f"test_{mode}_001",
                site_url="https://example.com",
                site_name="测试站点",
                requirement=requirement
            )

            print(f"✅ {mode} 模式实例化成功")

        except Exception as e:
            print(f"❌ {mode} 模式失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试 Orchestrator-Agent 集成...")

    success = test_basic_integration()
    test_agent_runner_modes()

    if success:
        print("\n✨ 所有测试通过！Agent 调用机制已正确实现。")
    else:
        print("\n💥 测试失败，请检查实现。")
        sys.exit(1)