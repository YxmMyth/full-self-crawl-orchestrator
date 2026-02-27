"""Agent [运行器] - Mock [实现（用于本地测试）]"""

import asyncio
import random
from typing import Optional

from ..models import TaskParams, TaskResult


class AgentRunner:
    """Agent [运行器] - Mock [实现]

    [当前为本地测试阶段，]Agent [返回模拟数据。]
    [后续接入真实的] Agent [执行器。]
    """

    def __init__(self, agent_path: Optional[str] = None, use_subprocess: bool = True):
        self.agent_path = agent_path or "../full-self-crawl-agent"
        self.use_subprocess = use_subprocess
        self._current_task_id: Optional[str] = None
        self._cancelled: bool = False

    async def run(self, task_params: TaskParams) -> TaskResult:
        """
        Mock [运行] Agent

        [模拟] Agent [探测站点，返回模拟结果]
        """
        self._current_task_id = task_params.task_id
        self._cancelled = False

        # [模拟处理时间（]1-3[秒）]
        process_time = random.uniform(1, 3)

        # [模拟进度上报]
        steps = 5
        for i in range(steps):
            if self._cancelled:
                return TaskResult(
                    task_id=task_params.task_id,
                    site_url=task_params.site_url,
                    site_name=task_params.site_name,
                    status="failed",
                    error_message="[任务被取消]"
                )

            await asyncio.sleep(process_time / steps)

        # [模拟成功]/[失败（]80% [成功率）]
        is_success = random.random() < 0.8

        if is_success:
            # [生成模拟成功结果]
            quality_score = random.uniform(60, 98)
            total_records = random.randint(1000, 50000)

            # [生成模拟样例数据]
            samples = []
            for i in range(min(5, random.randint(3, 8))):
                samples.append({
                    "title": f"[示例文章标题] {i+1}",
                    "author": f"[作者]{random.randint(1, 10)}",
                    "publish_time": f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "url": f"{task_params.site_url}/article/{i+1}",
                    "content": "[这是模拟的文章内容摘要，用于展示数据格式]..."
                })

            return TaskResult(
                task_id=task_params.task_id,
                site_url=task_params.site_url,
                site_name=task_params.site_name,
                status="success",
                quality_score=round(quality_score, 1),
                total_pages=random.randint(5, 50),
                total_records=total_records,
                samples=samples,
                duration_sec=int(process_time * steps),
                strategy_used=random.choice(["static", "api_first", "dynamic"]),
                difficulty=random.choice(["easy", "medium", "hard"]),
                anti_bot=[] if random.random() < 0.7 else ["cloudflare", "captcha"]
            )
        else:
            # [模拟失败]
            error_reasons = [
                "[站点访问超时]",
                "[页面结构变化]",
                "[被反爬机制阻止]",
                "[无法获取有效数据]"
            ]
            return TaskResult(
                task_id=task_params.task_id,
                site_url=task_params.site_url,
                site_name=task_params.site_name,
                status="failed",
                error_message=random.choice(error_reasons)
            )

    async def cancel(self) -> None:
        """[取消当前任务]"""
        self._cancelled = True

    def is_running(self) -> bool:
        """[检查是否正在运行]"""
        return self._current_task_id is not None and not self._cancelled

    async def listen_progress(self, task_id: str, callback) -> None:
        """[监听进度（]Mock [实现）]"""
        pass
