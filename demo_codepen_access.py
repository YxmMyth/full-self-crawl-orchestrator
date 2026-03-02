#!/usr/bin/env python3
"""
演示orchestrator调用agent访问codepen.io的完整流程
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator.orchestrator import Orchestrator
from orchestrator.models import ProgressUpdate


async def progress_callback(progress: ProgressUpdate):
    """进度回调函数"""
    print(f"[PROGRESS] {progress.message} ({progress.progress:.1f}%)")


async def main():
    """主函数"""
    print("=== 开始演示orchestrator调用agent访问codepen.io ===\n")

    # 创建orchestrator实例
    orchestrator = Orchestrator()

    # 用户需求：访问codepen.io
    user_input = "访问 https://codepen.io 网站，查找与HTML格式PPT相关的资源"

    try:
        print(f"用户需求: {user_input}\n")

        # 运行调研流程
        result = await orchestrator.run_research(
            user_input=user_input,
            progress_callback=progress_callback
        )

        # 输出结果
        print("\n=== 调研结果 ===")
        print(orchestrator.format_result(result))

        print("\n=== 完成演示 ===")

    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())