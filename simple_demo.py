#!/usr/bin/env python3
"""
运行orchestrator演示：访问CodePen网站，寻找HTML格式的PPT
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


async def progress_callback(progress: ProgressUpdate):
    """进度回调函数"""
    print(f"[PROGRESS] {progress.message} - {progress.progress:.1f}%")


async def run_demo():
    """运行演示"""

    print("开始运行orchestrator演示：访问CodePen寻找HTML格式PPT")
    print("="*60)

    # 创建配置
    config = OrchestratorConfig()

    # 为演示目的进行一些简化设置
    config.site_discovery.min_sites = 1
    config.site_discovery.max_sites = 2  # 限制站点数量，加快演示
    config.scheduler.mode = "serial"  # 使用串行模式
    config.scheduler.agent_timeout_min = 15  # 设置15分钟超时

    # 创建orchestrator实例
    orchestrator = Orchestrator(config)

    # 用户需求
    user_input = "帮我找HTML格式的PPT，在codepen.io上寻找相关的在线演示或模板"

    print(f"\\n用户需求: {user_input}\\n")

    try:
        # 手动创建一个包含CodePen的候选站点列表
        candidate_sites = [
            CandidateSite(
                site_name="CodePen",
                site_url="https://codepen.io",
                description="在线代码编辑器和前端社区，有很多HTML格式的PPT演示",
                priority=1
            ),
            # 备选站点
            CandidateSite(
                site_name="GitHub Pages",
                site_url="https://github.com",
                description="开发者社区，可能有reveal.js或impress.js等HTML幻灯片项目",
                priority=2
            )
        ]

        print("已设定候选站点:")
        for i, site in enumerate(candidate_sites, 1):
            print(f"   {i}. {site.site_name} ({site.site_url})")
            print(f"      描述: {site.description}")
            print(f"      优先级: {site.priority}")
        print()

        # 直接运行调度器（跳过需求分析和站点发现步骤，因为这些会消耗API调用）
        print("直接运行调度器测试...")

        # 为演示目的，我们手动创建一个需求对象
        requirement = RefinedRequirement(
            topic="HTML格式PPT",
            target_fields=["title", "author", "content", "tags", "date"],
            scope="global",
            time_range="recent",
            quantity=100,
            constraints={"format": "HTML", "platform": "codepen.io", "content_type": "presentation"}
        )

        print(f"需求规格:")
        print(f"   主题: {requirement.topic}")
        print(f"   目标字段: {', '.join(requirement.target_fields)}")
        print(f"   约束: {requirement.constraints}")
        print()

        # 生成任务ID
        from orchestrator.utils import generate_task_id
        task_id = generate_task_id()
        print(f"任务ID: {task_id}")

        # 注册进度回调
        orchestrator.monitor.register_callback(task_id, progress_callback)

        # 运行调度器
        print(f"\\n开始调度任务到agent...")
        results = await orchestrator.scheduler.schedule(
            task_id=task_id,
            candidate_sites=candidate_sites,
            requirement=requirement
        )

        # 结果整合
        print(f"\\n整合结果...")
        from orchestrator.strategic.result_aggregator import ResultAggregator
        aggregator = ResultAggregator()

        research_result = aggregator.aggregate(
            query=user_input,
            task_id=task_id,
            results=results,
            total_duration_sec=0  # 演示用途
        )

        print(f"\\n演示完成！")
        print(f"成功处理 {research_result.successful_sites}/{research_result.total_sites} 个站点")

        # 输出详细结果
        print(f"\\n详细结果:")
        for result in results:
            print(f"   站点: {result.site_name} ({result.site_url})")
            print(f"      状态: {result.status}")
            print(f"      质量评分: {result.quality_score}/100")
            print(f"      记录数: {result.total_records}")
            if result.samples:
                print(f"      样例: {len(result.samples)} 条")
                for i, sample in enumerate(result.samples[:2]):  # 只显示前2条样例
                    print(f"        {i+1}. {sample}")
            if result.error_message:
                print(f"      错误: {result.error_message}")
            print()

        # 格式化最终结果
        print(f"最终摘要:")
        formatted_result = aggregator.format_summary(research_result)
        print(formatted_result)

    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理回调
        try:
            orchestrator.monitor.unregister_callback(task_id, progress_callback)
        except:
            pass

    print("\\n演示结束")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_demo())