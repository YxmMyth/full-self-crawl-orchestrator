"""Chatbox - [用户交互界面]"""

from typing import Callable, Optional

from ..models import RefinedRequirement, ResearchResult, ProgressUpdate
from ..strategic import RequirementAnalyzer, ResultAggregator


class Chatbox:
    """Chatbox - [用户交互界面]"""

    def __init__(
        self,
        requirement_analyzer: Optional[RequirementAnalyzer] = None,
        result_aggregator: Optional[ResultAggregator] = None
    ):
        self.requirement_analyzer = requirement_analyzer or RequirementAnalyzer()
        self.result_aggregator = result_aggregator or ResultAggregator()
        self._progress_callback: Optional[Callable[[ProgressUpdate], None]] = None

    async def start_conversation(self) -> RefinedRequirement:
        """
        [启动对话，收集需求]

        Returns:
            RefinedRequirement: [精确化后的需求]
        """
        # [获取用户输入]
        user_input = await self._get_user_input("[请输入您的数据调研需求]: ")

        # [分析需求]
        print("\n[🤔] [正在分析您的需求]...")
        requirement = await self.requirement_analyzer.analyze(user_input)

        # [确认需求]
        while True:
            confirm_message, auto_confirm = await self.requirement_analyzer.confirm(requirement)
            print(f"\n{confirm_message}")

            if auto_confirm:
                break

            user_response = await self._get_user_input("")

            if user_response.lower() in ['y', 'yes', '[是]', '[确认]']:
                break
            elif user_response.lower() in ['n', 'no', '[否]', '[不]']:
                print("\n[请重新描述您的需求]:")
                user_input = await self._get_user_input("")
                print("\n[🤔] [重新分析需求]...")
                requirement = await self.requirement_analyzer.analyze(user_input)
            else:
                # [用户想要修改]
                print("\n[🤔] [正在根据您的意见调整]...")
                requirement = await self.requirement_analyzer.refine(user_response, requirement)

        return requirement

    async def show_progress(self, progress: ProgressUpdate) -> None:
        """
        [显示实时进度]

        Args:
            progress: [进度更新]
        """
        percentage = int(progress.progress * 100)
        bar_length = 30
        filled_length = int(bar_length * progress.progress)
        bar = '[█]' * filled_length + '[░]' * (bar_length - filled_length)

        print(f"\r[{bar}] {percentage}% | {progress.message}", end='', flush=True)

        if progress.status in ['completed', 'agent_complete', 'agent_error']:
            print()  # [换行]

    async def show_progress_simple(self, current: int, total: int, message: str = "") -> None:
        """
        [显示简单进度]

        Args:
            current: [当前进度]
            total: [总数]
            message: [消息]
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        print(f"\r[进度]: {current}/{total} ({percentage}%) {message}", end='', flush=True)

        if current >= total:
            print()

    async def show_results(self, result: ResearchResult) -> None:
        """
        [显示最终结果]

        Args:
            result: [调研结果]
        """
        print(self.result_aggregator.format_summary(result))

    async def _get_user_input(self, prompt: str) -> str:
        """
        [获取用户输入（可异步化）]

        Args:
            prompt: [提示语]

        Returns:
            str: [用户输入]
        """
        # [使用] input() [的包装，便于测试和扩展]
        if prompt:
            print(prompt, end="")
        try:
            return input()
        except EOFError:
            return ""

    def set_progress_callback(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """
        [设置进度回调]

        Args:
            callback: [回调函数]
        """
        self._progress_callback = callback

    async def notify_progress(self, progress: ProgressUpdate) -> None:
        """
        [通知进度更新]

        Args:
            progress: [进度更新]
        """
        if self._progress_callback:
            self._progress_callback(progress)
        await self.show_progress(progress)

    async def show_site_result(self, site_name: str, quality_score: float, sample_count: int) -> None:
        """
        [显示单个站点结果]

        Args:
            site_name: [站点名称]
            quality_score: [质量分数]
            sample_count: [样例数量]
        """
        print(f"\n[📊] {site_name}: [质量分] {quality_score:.1f}, [样例] {sample_count} [条]")

    async def show_error(self, message: str) -> None:
        """
        [显示错误信息]

        Args:
            message: [错误消息]
        """
        print(f"\n[❌] [错误]: {message}")

    async def show_info(self, message: str) -> None:
        """
        [显示信息]

        Args:
            message: [消息]
        """
        print(f"\nℹ[️]  {message}")

    async def confirm_action(self, message: str) -> bool:
        """
        [确认操作]

        Args:
            message: [确认消息]

        Returns:
            bool: [是否确认]
        """
        response = await self._get_user_input(f"{message} (Y/N): ")
        return response.lower() in ['y', 'yes', '[是]', '[确认]']
