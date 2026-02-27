"""[串行调度器] - [一个一个分派任务给] Agent"""

import asyncio
from datetime import datetime
from typing import List

from ..models import CandidateSite, RefinedRequirement, TaskParams, TaskResult
from .agent_runner import AgentRunner
from .monitor import Monitor
from .state_manager import StateManager


class SerialScheduler:
    """[串行调度器] - [一个一个分派任务给] Agent"""

    def __init__(
        self,
        agent_runner: AgentRunner,
        state_manager: StateManager,
        monitor: Monitor,
        agent_timeout: int = 1800  # 30 minutes
    ):
        self.agent_runner = agent_runner
        self.state_manager = state_manager
        self.monitor = monitor
        self.agent_timeout = agent_timeout
        self._current_task_id: str = ""
        self._cancelled: bool = False

    async def schedule(
        self,
        task_id: str,
        candidate_sites: List[CandidateSite],
        requirement: RefinedRequirement
    ) -> List[TaskResult]:
        """
        [串行调度执行流程：]
        1. [将候选站点加入] FIFO [队列]
        2. [逐个取出站点，调用] Agent [探测]
        3. [等待] Agent [完成，收集结果]
        4. [继续下一个，直到队列为空]

        Args:
            task_id: [任务]ID
            candidate_sites: [候选站点列表]
            requirement: [精确化需求]

        Returns:
            List[TaskResult]: [所有] Agent [返回的结果]
        """
        self._current_task_id = task_id
        self._cancelled = False

        results = []
        total_sites = len(candidate_sites)

        # [将站点加入队列]
        await self.state_manager.create_site_queue(task_id, candidate_sites)

        # [逐个处理站点]
        for i, site in enumerate(candidate_sites):
            # [检查是否被取消]
            if self._cancelled:
                print(f"Task {task_id} cancelled")
                break

            # [更新当前站点]
            await self.state_manager.set_current_site(task_id, site)

            # [上报进度]
            await self.monitor.report_progress(
                task_id=task_id,
                current_site=site.site_url,
                completed=i,
                total=total_sites,
                message=f"[正在探测]: {site.site_name}"
            )

            # [构建任务参数]
            task_params = TaskParams(
                task_id=f"{task_id}:{site.site_url}",
                site_url=site.site_url,
                site_name=site.site_name,
                requirement=requirement
            )

            try:
                # [调用] Agent[（串行等待）]
                result = await self._run_agent_with_timeout(task_params)
                results.append(result)

                # [保存结果]
                await self.state_manager.save_result(task_id, result)

                # [上报成功]
                await self.monitor.report_agent_complete(
                    task_id=task_id,
                    site_url=site.site_url,
                    result=result
                )

            except Exception as e:
                # Agent [执行失败]
                error_result = TaskResult(
                    task_id=task_params.task_id,
                    site_url=site.site_url,
                    site_name=site.site_name,
                    status="failed",
                    error_message=str(e)
                )
                results.append(error_result)
                await self.state_manager.save_result(task_id, error_result)

                await self.monitor.report_agent_error(
                    task_id=task_id,
                    site_url=site.site_url,
                    error=str(e)
                )

        # [最终进度报告]
        await self.monitor.report_progress(
            task_id=task_id,
            current_site="",
            completed=len(results),
            total=total_sites,
            message="[探测完成]"
        )

        return results

    async def _run_agent_with_timeout(self, task_params: TaskParams) -> TaskResult:
        """
        [带超时地运行] Agent

        Args:
            task_params: [任务参数]

        Returns:
            TaskResult: [任务结果]
        """
        try:
            result = await asyncio.wait_for(
                self.agent_runner.run(task_params),
                timeout=self.agent_timeout
            )
            return result

        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task_params.task_id,
                site_url=task_params.site_url,
                site_name=task_params.site_name,
                status="failed",
                error_message=f"Agent [执行超时] (>{self.agent_timeout}[秒])"
            )

    async def cancel(self) -> None:
        """[取消当前调度]"""
        self._cancelled = True
        await self.agent_runner.cancel()

    def get_current_task_id(self) -> str:
        """[获取当前任务]ID"""
        return self._current_task_id
