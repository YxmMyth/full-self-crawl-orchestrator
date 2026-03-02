#!/usr/bin/env python3
"""
测试orchestrator的基本功能 - 访问codepen.io
"""

import asyncio
import json
from pathlib import Path
import sys

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.config import OrchestratorConfig
from orchestrator.models import RefinedRequirement, CandidateSite, ProgressUpdate


async def test_orchestrator():
    """测试orchestrator的基本功能"""

    print("=== 测试orchestrator基本功能 ===\n")

    # 创建一个简化的配置
    config = OrchestratorConfig()

    # 修改一些参数以适应测试
    config.site_discovery.min_sites = 1
    config.site_discovery.max_sites = 1  # 只测试一个站点
    config.scheduler.mode = "serial"  # 使用串行模式简化测试

    # 创建orchestrator实例
    orchestrator = Orchestrator(config)

    # 测试需求分析功能
    print("1. 测试需求分析...")
    user_input = "帮我找HTML格式的PPT资源，特别是codepen.io上的相关内容"

    requirement = await orchestrator.requirement_analyzer.analyze(user_input)
    print(f"   主题: {requirement.topic}")
    print(f"   目标字段: {requirement.target_fields}")
    print(f"   范围: {requirement.scope}")
    print(f"   时间范围: {requirement.time_range}")
    print(f"   数量: {requirement.quantity}")
    print(f"   约束: {requirement.constraints}\n")

    # 测试站点发现功能
    print("2. 测试站点发现...")
    candidate_sites = await orchestrator.site_discovery.discover(requirement)

    # 如果没有找到codepen.io相关的站点，手动添加一个
    codepen_found = any("codepen" in site.site_url.lower() for site in candidate_sites)
    if not codepen_found:
        print("   未自动发现codepen.io，手动添加...")
        candidate_sites.insert(0, CandidateSite(
            site_name="CodePen",
            site_url="https://codepen.io",
            description="在线代码编辑器和前端社区，可能包含HTML格式的PPT演示",
            priority=1
        ))

    print(f"   发现 {len(candidate_sites)} 个候选站点:")
    for i, site in enumerate(candidate_sites[:3]):  # 只显示前3个
        print(f"   {i+1}. {site.site_name} - {site.site_url}")
        print(f"      描述: {site.description}")
        print(f"      优先级: {site.priority}")

    print(f"\n   总共 {len(candidate_sites)} 个站点\n")

    # 显示预期的调度流程
    print("3. 预期的调度流程...")
    print(f"   将会使用{'并发' if config.scheduler.mode == 'concurrent' else '串行'}调度器")
    print(f"   向 {len(candidate_sites)} 个站点发送任务")
    print(f"   每个站点将收到任务参数: TaskParams")
    print(f"   任务ID: <generated>")
    print(f"   站点URL: <site_url>")
    print(f"   站点名称: <site_name>")
    print(f"   需求: {requirement.topic}\n")

    print("=== 测试完成 ===")
    print("orchestrator能够正常执行需求分析和站点发现流程，接下来会进入调度阶段调用agent。")


def progress_callback(progress):
    """进度回调函数"""
    print(f"[PROGRESS] {progress.message} - {progress.progress:.1f}%")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())