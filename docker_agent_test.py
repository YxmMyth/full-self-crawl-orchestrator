#!/usr/bin/env python3
"""
真实测试：orchestrator调用实际agent（Docker模式）访问CodePen寻找HTML格式PPT
"""

import asyncio
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.config import OrchestratorConfig
from orchestrator.models import RefinedRequirement, CandidateSite, ProgressUpdate


async def progress_callback(progress: ProgressUpdate):
    """进度回调函数"""
    print(f"[PROGRESS] {progress.message} - {progress.progress:.1f}%")


async def run_real_test_docker():
    """运行真实测试（Docker模式）"""

    print("开始真实测试：orchestrator调用实际agent（Docker模式）")
    print("目标：寻找HTML格式的PPT资源")
    print("="*60)

    # 创建配置 - 使用Docker模式连接到实际的agent
    config = OrchestratorConfig()

    # 更新配置使用Docker模式
    config.agent.path = "../full-self-crawl-agent"
    config.agent.mode = "docker"  # 使用Docker模式
    config.agent.image = "full-self-crawl-agent:latest"
    config.site_discovery.min_sites = 1
    config.site_discovery.max_sites = 1  # 只测试一个站点
    config.scheduler.mode = "serial"  # 使用串行模式
    config.scheduler.agent_timeout_min = 30  # 设置较长超时时间

    print(f"Agent路径: {config.agent.path}")
    print(f"Agent模式: {config.agent.mode}")
    print(f"Agent镜像: {config.agent.image}")
    print(f"超时设置: {config.scheduler.agent_timeout_min}分钟")
    print()

    # 创建orchestrator实例
    orchestrator = Orchestrator(config)

    # 用户需求
    user_input = "帮我找HTML格式的PPT，在codepen.io上寻找相关的在线演示或模板"

    print(f"用户需求: {user_input}")
    print()

    try:
        print("阶段1: 需求分析")
        # 分析用户输入
        requirement = await orchestrator.requirement_analyzer.analyze(user_input)
        print(f"主题: {requirement.topic}")
        print(f"目标字段: {requirement.target_fields}")
        print(f"约束: {requirement.constraints}")
        print()

        print("阶段2: 候选站点发现")
        # 发现相关网站
        candidate_sites = await orchestrator.site_discovery.discover(requirement)

        # 确保包含CodePen
        codepen_exists = any("codepen.io" in site.site_url.lower() for site in candidate_sites)
        if not codepen_exists:
            candidate_sites.insert(0, CandidateSite(
                site_name="CodePen",
                site_url="https://codepen.io",
                description="前端开发者社区，有很多HTML格式的PPT演示",
                priority=1
            ))

        print(f"发现 {len(candidate_sites)} 个候选站点:")
        for i, site in enumerate(candidate_sites[:3]):  # 最多显示3个
            print(f"  {i+1}. {site.site_name} - {site.site_url}")
        print()

        print("阶段3: 实际调用agent（Docker模式）")
        print("开始调度任务到真实agent...")
        print("agent将访问网站并执行搜索任务")
        print()

        # 执行完整流程
        result = await orchestrator.run_research(
            user_input=user_input,
            progress_callback=progress_callback
        )

        print()
        print("阶段4: 结果展示")
        print(f"成功处理: {result.successful_sites}/{result.total_sites} 个站点")
        print(f"总耗时: {result.total_duration_sec} 秒")

        if result.rankings:
            print("发现的高质量资源:")
            for ranking in result.rankings[:3]:  # 显示前3个
                print(f"  * {ranking.site_name} - 质量: {ranking.quality_score}/100")
                print(f"    记录数: {ranking.total_records}")
                if ranking.samples:
                    print(f"    样例: {len(ranking.samples)} 条")
                    for sample in ranking.samples[:2]:  # 显示前2个样例
                        print(f"      - {sample}")
        print()

        print("测试完成！")
        print("系统成功调用了实际的agent组件来完成任务")

    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 使用兼容的异步执行方式
    try:
        if hasattr(asyncio, 'run'):
            asyncio.run(run_real_test_docker())
        else:
            # Python 3.6及以下版本的兼容性
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_real_test_docker())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"启动测试失败: {e}")