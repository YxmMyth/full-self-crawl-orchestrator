"""Orchestrator [工作流] - [整合三层架构]"""

import time
from datetime import datetime
from typing import Callable, List, Optional

from .config import OrchestratorConfig
from .execution.chatbox import Chatbox
from .execution.presenter import ResultPresenter
from .management.agent_runner import AgentRunner
from .management.monitor import Monitor
from .management.scheduler import ConcurrentScheduler, SerialScheduler
from .management.state_manager import StateManager
from .models import CandidateSite, ProgressUpdate, RefinedRequirement, ResearchResult, TaskResult
from .strategic.requirement_analyzer import RequirementAnalyzer
from .strategic.result_aggregator import ResultAggregator
from .storage.postgres_store import PostgresStore


class Orchestrator:
    """
    Orchestrator [主类] - [整合三层架构]

    [负责协调战略层、管理层、执行层的协作，完成整个调研流程。]
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        [初始化] Orchestrator

        Args:
            config: [配置对象，如果为] None [则加载默认配置]
        """
        self.config = config or OrchestratorConfig()

        # [战略层组件]
        self.requirement_analyzer = RequirementAnalyzer()
        self.site_discovery = SiteDiscovery(
            min_sites=self.config.site_discovery.min_sites,
            max_sites=self.config.site_discovery.max_sites
        )
        self.result_aggregator = ResultAggregator()

        # [管理层组件]
        self.state_manager = StateManager()
        self.monitor = Monitor(update_interval=self.config.monitor.progress_update_interval)
        self.agent_runner = AgentRunner(
            agent_path=self.config.agent.path,
            use_subprocess=True
        )

        # [根据配置选择调度器模式]
        if self.config.scheduler.mode == "concurrent":
            self.scheduler = ConcurrentScheduler(
                agent_runner=self.agent_runner,
                state_manager=self.state_manager,
                monitor=self.monitor,
                agent_timeout=self.config.scheduler.agent_timeout_min * 60,
                max_concurrency=self.config.scheduler.max_concurrency
            )
            print(f"[INFO] [使用并发调度器], [最大并发数]: {self.config.scheduler.max_concurrency}")
        else:
            self.scheduler = SerialScheduler(
                agent_runner=self.agent_runner,
                state_manager=self.state_manager,
                monitor=self.monitor,
                agent_timeout=self.config.scheduler.agent_timeout_min * 60
            )
            print("[INFO] [使用串行调度器]")

        # [执行层组件]
        self.chatbox = Chatbox(self.config)
        self.presenter = ResultPresenter()

        # [PostgreSQL 存储]
        self.postgres_store: Optional[PostgresStore] = None
        try:
            self.postgres_store = PostgresStore(
                host=self.config.storage.postgres.host,
                port=self.config.storage.postgres.port,
                database=self.config.storage.postgres.database,
                user=self.config.storage.postgres.user,
                password=self.config.storage.postgres.password
            )
        except Exception as e:
            print(f"[WARN] PostgreSQL [初始化失败]: {e}")

        # [状态]
        self.current_task_id: Optional[str] = None
        self.current_requirement: Optional[RefinedRequirement] = None
        self.progress_callback: Optional[Callable[[ProgressUpdate], None]] = None

    async def run_research(
        self,
        user_input: str,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> ResearchResult:
        """
        [运行完整的调研流程]

        Args:
            user_input: [用户输入的需求描述]
            progress_callback: [进度回调函数]

        Returns:
            ResearchResult: [调研结果]
        """
        self.progress_callback = progress_callback
        start_time = time.time()

        # 1. [生成任务]ID
        task_id = generate_task_id()
        self.current_task_id = task_id

        print(f"\n[START] [启动调研任务]: {task_id}")
        print(f"[INPUT] [用户输入]: {user_input}\n")

        # 2. [需求分析（战略层）]
        print("[STAGE 1/4] [需求分析]...")
        requirement = await self.requirement_analyzer.analyze(user_input)
        self.current_requirement = requirement

        print(f"   [OK] [主题]: {requirement.topic}")
        print(f"   [OK] [目标字段]: {', '.join(requirement.target_fields)}")
        print(f"   [OK] [范围]: {requirement.scope or '[不限]'}")
        print(f"   [OK] [期望数量]: {requirement.quantity}\n")

        # [创建任务记录]
        await self.state_manager.create_task(task_id, user_input, requirement)
        await self.state_manager.set_task_status(task_id, "running")

        # [持久化到 PostgreSQL]
        if self.postgres_store:
            try:
                await self.postgres_store.create_task(
                    task_id=task_id,
                    user_query=user_input,
                    refined_requirement=requirement.model_dump()
                )
                await self.postgres_store.update_task_status(
                    task_id=task_id,
                    status="running"
                )
            except Exception as e:
                print(f"[WARN] [保存任务到] PostgreSQL [失败]: {e}")

        # 3. [候选站挖掘（战略层）]
        print("[STAGE 2/4] [候选站挖掘]...")
        candidate_sites = await self.site_discovery.discover(requirement)

        print(f"   [OK] [发现] {len(candidate_sites)} [个候选站点]:")
        for i, site in enumerate(candidate_sites[:5], 1):
            print(f"      {i}. {site.site_name} ({site.site_url}) - [优先级]: {site.priority}")
        if len(candidate_sites) > 5:
            print(f"      ... [还有] {len(candidate_sites) - 5} [个站点]")
        print()

        # [注册进度回调]
        if progress_callback:
            self.monitor.register_callback(task_id, progress_callback)

        # 4. [串行调度执行（管理层）]
        print("[STAGE 3/4] [串行调度] Agent [探测]...")
        print(f"   [预计耗时]: {len(candidate_sites) * 2}-{len(candidate_sites) * 5} [分钟]\n")

        results = await self.scheduler.schedule(task_id, candidate_sites, requirement)

        # 5. [结果整合（战略层）]
        print("\n[STAGE 4/4] [结果整合]...")
        total_duration = int(time.time() - start_time)

        research_result = self.result_aggregator.aggregate(
            query=user_input,
            task_id=task_id,
            results=results,
            total_duration_sec=total_duration
        )

        # [更新任务状态]
        await self.state_manager.set_task_status(task_id, "completed")

        # [持久化任务结果到 PostgreSQL]
        if self.postgres_store:
            try:
                await self.postgres_store.update_task_status(
                    task_id=task_id,
                    status="completed",
                    candidate_sites=[site.model_dump() for site in candidate_sites],
                    successful_sites=research_result.successful_sites
                )

                # [保存站点结果]
                for result in results:
                    if result.status == "success":
                        await self.postgres_store.save_site_result(
                            result.model_dump()
                        )
            except Exception as e:
                print(f"[WARN] [保存任务结果到] PostgreSQL [失败]: {e}")

        # [取消注册回调]
        if progress_callback:
            self.monitor.unregister_callback(task_id, progress_callback)

        # [报告完成]
        await self.monitor.report_task_complete(
            task_id=task_id,
            total_sites=research_result.total_sites,
            successful_sites=research_result.successful_sites
        )

        print(f"   [OK] [完成]! [成功] {research_result.successful_sites}/{research_result.total_sites} [站点]")
        print(f"   [OK] [总耗时]: {total_duration // 60}[分]{total_duration % 60}[秒]\n")

        return research_result

    async def run_research_with_confirmation(
        self,
        user_input: str,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> Optional[ResearchResult]:
        """
        [带确认的运行调研流程]

        Args:
            user_input: [用户输入]
            progress_callback: [进度回调]

        Returns:
            ResearchResult: [调研结果，如果用户取消则返回] None
        """
        # 1. [分析需求]
        requirement = await self.requirement_analyzer.analyze(user_input)

        # 2. [显示确认]
        confirm_msg, _ = await self.requirement_analyzer.confirm(requirement)
        print(confirm_msg)

        # [这里应该等待用户输入，但在自动化流程中默认确认]
        # [实际应用中可以通过] chatbox [交互]

        # 3. [运行调研]
        return await self.run_research(user_input, progress_callback)

    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        [获取任务状态]

        Args:
            task_id: [任务]ID

        Returns:
            dict: [任务状态信息]
        """
        task_info = await self.state_manager.get_task_info(task_id)
        current_site = await self.state_manager.get_current_site(task_id)
        progress = await self.monitor.get_progress(task_id)

        if not task_info:
            return None

        return {
            "task_id": task_id,
            "status": task_info.status,
            "current_site": current_site.site_url if current_site else None,
            "progress": progress.progress if progress else 0.0,
            "requirement": task_info.refined_requirement.model_dump() if task_info.refined_requirement else None,
            "created_at": task_info.created_at,
        }

    async def cancel_current_task(self) -> bool:
        """
        [取消当前任务]

        Returns:
            bool: [是否成功取消]
        """
        if self.current_task_id:
            await self.scheduler.cancel()
            await self.state_manager.set_task_status(self.current_task_id, "failed")
            return True
        return False

    def format_result(self, result: ResearchResult) -> str:
        """
        [格式化结果]

        Args:
            result: [调研结果]

        Returns:
            str: [格式化的结果文本]
        """
        return self.result_aggregator.format_summary(result)

    async def list_historical_tasks(self, limit: int = 10) -> List[dict]:
        """
        [列出历史任务]

        Args:
            limit: [数量限制]

        Returns:
            List[dict]: [任务列表]
        """
        if self.postgres_store:
            try:
                tasks = await self.postgres_store.list_tasks(limit=limit)
                return tasks
            except Exception as e:
                print(f"[WARN] [查询历史任务失败]: {e}")

        return []
