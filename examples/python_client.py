#!/usr/bin/env python3
"""
Python 客户端示例 - 数据源调研平台 API

安装依赖:
    pip install httpx

运行示例:
    python python_client.py
"""

import asyncio
import json
import sys
from typing import Optional

try:
    import httpx
except ImportError:
    print("请先安装 httpx: pip install httpx")
    sys.exit(1)


BASE_URL = "http://localhost:8000"


class DataSourceResearchClient:
    """数据源调研平台客户端"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def health_check(self) -> dict:
        """健康检查"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def start_research(self, query: str) -> dict:
        """
        启动新的调研任务

        Args:
            query: 用户的调研需求描述

        Returns:
            包含 task_id 的响应
        """
        response = await self.client.post(
            f"{self.base_url}/api/research",
            json={"query": query}
        )
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_id: str) -> dict:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态信息
        """
        response = await self.client.get(
            f"{self.base_url}/api/research/{task_id}/status"
        )
        response.raise_for_status()
        return response.json()

    async def get_task_result(self, task_id: str) -> Optional[dict]:
        """
        获取任务结果

        Args:
            task_id: 任务 ID

        Returns:
            任务结果，如果任务未完成则返回 None
        """
        response = await self.client.get(
            f"{self.base_url}/api/research/{task_id}/result"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def stream_progress(self, task_id: str):
        """
        流式获取任务进度 (SSE)

        Args:
            task_id: 任务 ID

        Yields:
            进度更新数据
        """
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{self.base_url}/api/research/{task_id}/progress",
                headers={"Accept": "text/event-stream"}
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 去掉 "data: " 前缀
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            pass

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0
    ) -> Optional[dict]:
        """
        等待任务完成并获取结果

        Args:
            task_id: 任务 ID
            poll_interval: 轮询间隔（秒）
            timeout: 超时时间（秒）

        Returns:
            任务结果，如果超时则返回 None
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = await self.get_task_result(task_id)
            if result is not None:
                return result

            status = await self.get_task_status(task_id)
            print(f"  状态: {status.get('status')}, "
                  f"进度: {status.get('progress', 0)*100:.1f}%, "
                  f"消息: {status.get('message', '...')}")

            await asyncio.sleep(poll_interval)

        return None

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


async def main():
    """主函数 - 运行示例"""
    client = DataSourceResearchClient()

    try:
        print("=" * 50)
        print("数据源调研平台 - Python 客户端示例")
        print("=" * 50)
        print()

        # 1. 健康检查
        print("1. 健康检查")
        health = await client.health_check()
        print(f"   状态: {health}")
        print()

        # 2. 启动调研任务
        print("2. 启动调研任务")
        query = "找科技媒体的数据源，需要包含标题、作者、发布时间"
        print(f"   查询: {query}")

        research = await client.start_research(query)
        task_id = research["task_id"]
        print(f"   任务 ID: {task_id}")
        print(f"   响应: {research}")
        print()

        # 3. 获取任务状态
        print("3. 获取任务状态")
        status = await client.get_task_status(task_id)
        print(f"   状态: {status}")
        print()

        # 4. 等待任务完成
        print("4. 等待任务完成（按 Ctrl+C 取消）")
        print("   正在轮询结果...")
        result = await client.wait_for_completion(task_id, poll_interval=2.0)

        if result:
            print()
            print("   任务完成!")
            print(f"   结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print("   等待超时")

        print()

        # 5. SSE 进度流示例（可选）
        print("5. SSE 进度流示例")
        print("   启动新任务并监听进度...")

        research2 = await client.start_research("找电商商品数据源")
        task_id2 = research2["task_id"]
        print(f"   新任务 ID: {task_id2}")

        print("   接收进度更新（最多 10 条）:")
        count = 0
        async for progress in client.stream_progress(task_id2):
            print(f"   进度: {progress}")
            count += 1
            if count >= 10 or progress.get("status") == "completed":
                break

    except httpx.HTTPError as e:
        print(f"HTTP 错误: {e}")
    except KeyboardInterrupt:
        print("\n用户取消")
    finally:
        await client.close()

    print()
    print("=" * 50)
    print("示例完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
