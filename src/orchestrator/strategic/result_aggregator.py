"""[结果整合模块] - [汇总] Agent [结果，生成排行榜]"""

from datetime import datetime
from typing import List

from ..models import FailedSite, ResearchResult, SiteRanking, TaskResult


class ResultAggregator:
    """[结果整合] - [汇总] Agent [结果，生成排行榜]"""

    def __init__(self):
        pass

    def aggregate(
        self,
        query: str,
        task_id: str,
        results: List[TaskResult],
        total_duration_sec: int = 0
    ) -> ResearchResult:
        """
        [汇总所有] Agent [结果]

        Args:
            query: [用户原始需求]
            task_id: [任务]ID
            results: [所有] Agent [返回的结果列表]
            total_duration_sec: [总耗时]([秒])

        Returns:
            ResearchResult: [整合后的调研结果]
        """
        # [分类成功和失败的结果]
        successful_results = [r for r in results if r.status == "success"]
        failed_results = [r for r in results if r.status == "failed"]

        # [按质量分数排序生成排行榜]
        rankings = self._create_rankings(successful_results)

        # [创建失败站点列表]
        failed_sites = self._create_failed_list(failed_results)

        return ResearchResult(
            query=query,
            task_id=task_id,
            total_sites=len(results),
            successful_sites=len(successful_results),
            failed_sites_count=len(failed_results),
            rankings=rankings,
            failed_sites=failed_sites,
            total_duration_sec=total_duration_sec,
            completed_at=datetime.now().isoformat()
        )

    def _create_rankings(self, results: List[TaskResult]) -> List[SiteRanking]:
        """
        [创建站点排行榜]

        Args:
            results: [成功的任务结果列表]

        Returns:
            List[SiteRanking]: [排序后的排行榜]
        """
        # [按质量分数降序排序]
        sorted_results = sorted(
            results,
            key=lambda r: r.quality_score,
            reverse=True
        )

        rankings = []
        for i, result in enumerate(sorted_results, 1):
            ranking = SiteRanking(
                rank=i,
                site_name=result.site_name or result.site_url,
                site_url=result.site_url,
                quality_score=result.quality_score,
                total_records=result.total_records,
                difficulty=result.difficulty,
                samples=result.samples[:5] if result.samples else []  # [只取前]5[个样例]
            )
            rankings.append(ranking)

        return rankings

    def _create_failed_list(self, results: List[TaskResult]) -> List[FailedSite]:
        """
        [创建失败站点列表]

        Args:
            results: [失败的任务结果列表]

        Returns:
            List[FailedSite]: [失败站点信息列表]
        """
        failed_sites = []
        for result in results:
            # [根据错误信息推断失败原因]
            reason = self._categorize_error(result.error_message)

            failed_site = FailedSite(
                site_url=result.site_url,
                site_name=result.site_name or result.site_url,
                reason=reason,
                error_message=result.error_message
            )
            failed_sites.append(failed_site)

        return failed_sites

    def _categorize_error(self, error_message: str) -> str:
        """
        [根据错误信息分类失败原因]

        Args:
            error_message: [错误信息]

        Returns:
            str: [失败原因分类]
        """
        error_lower = error_message.lower()

        if not error_message:
            return "[未知错误]"

        if "timeout" in error_lower or "[超时]" in error_message:
            return "[超时]"
        elif "block" in error_lower or "[拒绝]" in error_message or "forbid" in error_lower:
            return "[被阻止]"
        elif "structure" in error_lower or "[结构]" in error_message or "change" in error_lower:
            return "[结构变化]"
        elif "network" in error_lower or "connection" in error_lower or "[网络]" in error_message:
            return "[网络错误]"
        elif "access" in error_lower or "denied" in error_lower or "403" in error_message:
            return "[访问被拒绝]"
        elif "not found" in error_lower or "404" in error_message:
            return "[页面不存在]"
        else:
            return "[其他错误]"

    def format_summary(self, result: ResearchResult) -> str:
        """
        [格式化结果摘要]

        Args:
            result: [调研结果]

        Returns:
            str: [格式化的摘要文本]
        """
        lines = [
            f"\n{'='*60}",
            f"[📊] [调研完成]: {result.query}",
            f"{'='*60}",
            f"",
            f"[📈] [统计]:",
            f"   - [总探测站点]: {result.total_sites}",
            f"   - [成功]: {result.successful_sites}",
            f"   - [失败]: {result.failed_sites_count}",
            f"   - [总耗时]: {self._format_duration(result.total_duration_sec)}",
            f"",
        ]

        if result.rankings:
            lines.extend([
                f"[🏆] [站点排行榜] ([前]5[名]):",
                f"",
            ])
            for ranking in result.rankings[:5]:
                medal = "[🥇]" if ranking.rank == 1 else "[🥈]" if ranking.rank == 2 else "[🥉]" if ranking.rank == 3 else "  "
                lines.append(
                    f"   {medal} #{ranking.rank} {ranking.site_name}"
                )
                lines.append(
                    f"      [质量分]: {ranking.quality_score:.1f} | "
                    f"[数据量]: {ranking.total_records} | "
                    f"[难度]: {ranking.difficulty or '[未知]'}"
                )
                lines.append(f"")

        if result.failed_sites:
            lines.extend([
                f"[⚠️]  [失败站点]:",
            ])
            for site in result.failed_sites[:3]:
                lines.append(f"   - {site.site_name}: {site.reason}")

        lines.append(f"{'='*60}")

        return "\n".join(lines)

    def _format_duration(self, seconds: int) -> str:
        """[格式化时长]"""
        if seconds < 60:
            return f"{seconds}[秒]"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}[分]{secs}[秒]"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}[小时]{minutes}[分]"
