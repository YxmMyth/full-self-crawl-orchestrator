"""[调度器模块] - [支持串行和并发两种模式]"""

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


class ConcurrentScheduler:
    """[并发调度器] - [同时分派多个任务给] Agent [池]"""

    def __init__(
        self,
        agent_runner: AgentRunner,
        state_manager: StateManager,
        monitor: Monitor,
        agent_timeout: int = 1800,  # 30 minutes
        max_concurrency: int = 3,   # 默认3个并发
    ):
        self.agent_runner = agent_runner
        self.state_manager = state_manager
        self.monitor = monitor
        self.agent_timeout = agent_timeout
        self.max_concurrency = max_concurrency
        self._current_task_id: str = ""
        self._cancelled: bool = False
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)

    async def schedule(
        self,
        task_id: str,
        candidate_sites: List[CandidateSite],
        requirement: RefinedRequirement
    ) -> List[TaskResult]:
        """
        [并发调度执行流程：]
        1. [将候选站点加入队列]
        2. [创建信号量控制并发数]
        3. [同时启动多个] Agent [任务]
        4. [等待所有任务完成，收集结果]

        Args:
            task_id: [任务]ID
            candidate_sites: [候选站点列表]
            requirement: [精确化需求]

        Returns:
            List[TaskResult]: [所有] Agent [返回的结果]
        """
        self._current_task_id = task_id
        self._cancelled = False

        results: List[TaskResult] = []
        total_sites = len(candidate_sites)
        completed_count = 0

        # [将站点加入队列]
        await self.state_manager.create_site_queue(task_id, candidate_sites)

        # [创建任务列表]
        async def process_site(site: CandidateSite, index: int) -> TaskResult:
            nonlocal completed_count

            # [使用信号量控制并发]
            async with self._semaphore:
                # [检查是否被取消]
                if self._cancelled:
                    return TaskResult(
                        task_id=f"{task_id}:{site.site_url}",
                        site_url=site.site_url,
                        site_name=site.site_name,
                        status="cancelled",
                        error_message="[任务已取消]"
                    )

                # [更新当前站点]
                await self.state_manager.set_current_site(task_id, site)

                # [上报进度]
                await self.monitor.report_progress(
                    task_id=task_id,
                    current_site=site.site_url,
                    completed=completed_count,
                    total=total_sites,
                    message=f"[正在探测]: {site.site_name} ([并发] {index + 1}/{total_sites})"
                )

                # [构建任务参数]
                task_params = TaskParams(
                    task_id=f"{task_id}:{site.site_url}",
                    site_url=site.site_url,
                    site_name=site.site_name,
                    requirement=requirement
                )

                try:
                    # [调用] Agent
                    result = await self._run_agent_with_timeout(task_params)

                    # [保存结果]
                    await self.state_manager.save_result(task_id, result)

                    # [上报成功]
                    await self.monitor.report_agent_complete(
                        task_id=task_id,
                        site_url=site.site_url,
                        result=result
                    )

                    completed_count += 1
                    return result

                except Exception as e:
                    # Agent [执行失败]
                    error_result = TaskResult(
                        task_id=task_params.task_id,
                        site_url=site.site_url,
                        site_name=site.site_name,
                        status="failed",
                        error_message=str(e)
                    )
                    await self.state_manager.save_result(task_id, error_result)

                    await self.monitor.report_agent_error(
                        task_id=task_id,
                        site_url=site.site_url,
                        error=str(e)
                    )

                    completed_count += 1
                    return error_result

        # [并发执行所有任务]
        tasks = [
            process_site(site, i)
            for i, site in enumerate(candidate_sites)
        ]

        # [等待所有任务完成]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # [处理可能的异常结果]
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # [如果发生异常，创建失败结果]
                site = candidate_sites[i]
                error_result = TaskResult(
                    task_id=f"{task_id}:{site.site_url}",
                    site_url=site.site_url,
                    site_name=site.site_name,
                    status="failed",
                    error_message=str(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        # [最终进度报告]
        await self.monitor.report_progress(
            task_id=task_id,
            current_site="",
            completed=len(processed_results),
            total=total_sites,
            message=f"[探测完成] ([并发模式], [并发数]: {self.max_concurrency})"
        )

        return processed_results

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

    def set_max_concurrency(self, max_concurrency: int) -> None:
        """
        [动态设置最大并发数]

        Args:
            max_concurrency: [新的最大并发数]
        """
        self.max_concurrency = max(max_concurrency, 1)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
