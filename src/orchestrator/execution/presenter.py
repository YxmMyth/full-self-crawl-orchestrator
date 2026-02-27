"""[结果展示器] - [格式化展示排行榜]"""

from typing import Any, Dict, List

from ..models import ResearchResult, SiteRanking


class ResultPresenter:
    """[结果展示器] - [格式化展示排行榜]"""

    def __init__(self):
        pass

    def format_rankings(self, result: ResearchResult, top_n: int = 10) -> str:
        """
        [格式化排行榜]

        Args:
            result: [调研结果]
            top_n: [显示前]N[名]

        Returns:
            str: [格式化的排行榜文本]
        """
        lines = [
            f"\n{'='*70}",
            f"[🏆] [数据源调研排行榜]",
            f"{'='*70}",
            f"[需求]: {result.query}",
            f"[成功]: {result.successful_sites}/{result.total_sites} [站点]",
            f"{'='*70}",
        ]

        if not result.rankings:
            lines.append("\n[暂无数据]")
            return "\n".join(lines)

        # [表头]
        lines.extend([
            f"",
            f"{'[排名]':<4} {'[站点]':<20} {'[质量分]':<8} {'[数据量]':<10} {'[难度]':<6}",
            f"{'-'*70}"
        ])

        # [站点列表]
        for ranking in result.rankings[:top_n]:
            medal = self._get_medal(ranking.rank)
            name = ranking.site_name[:18] + ".." if len(ranking.site_name) > 20 else ranking.site_name
            quantity = self._format_quantity(ranking.total_records)
            difficulty = ranking.difficulty or "[未知]"

            lines.append(
                f"{medal:<4} {name:<20} {ranking.quality_score:<8.1f} {quantity:<10} {difficulty:<6}"
            )

        lines.append(f"{'='*70}")

        return "\n".join(lines)

    def format_samples(self, site_name: str, samples: List[Dict[str, Any]]) -> str:
        """
        [格式化样例数据]

        Args:
            site_name: [站点名称]
            samples: [样例数据列表]

        Returns:
            str: [格式化的样例文本]
        """
        lines = [
            f"\n{'='*70}",
            f"[📋] [样例数据] - {site_name}",
            f"{'='*70}"
        ]

        if not samples:
            lines.append("\n[暂无样例数据]")
            return "\n".join(lines)

        for i, sample in enumerate(samples, 1):
            lines.append(f"\n--- [记录] {i} ---")
            for key, value in sample.items():
                # [截断过长的值]
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                lines.append(f"  {key}: {value_str}")

        lines.append(f"\n{'='*70}")

        return "\n".join(lines)

    def format_detailed_report(self, result: ResearchResult) -> str:
        """
        [格式化详细报告]

        Args:
            result: [调研结果]

        Returns:
            str: [格式化的详细报告]
        """
        lines = [
            f"{'='*70}",
            f"[📊] [数据源调研详细报告]",
            f"{'='*70}",
            f"",
            f"[【基本信息】]",
            f"  [任务]ID: {result.task_id}",
            f"  [用户需求]: {result.query}",
            f"  [总站点数]: {result.total_sites}",
            f"  [成功站点]: {result.successful_sites}",
            f"  [失败站点]: {result.failed_sites_count}",
            f"  [总耗时]: {self._format_duration(result.total_duration_sec)}",
            f"  [完成时间]: {result.completed_at or '[未完成]'}",
            f"",
        ]

        # [成功站点]
        if result.rankings:
            lines.extend([
                f"[【成功站点详情】]",
                f"",
            ])
            for ranking in result.rankings:
                medal = self._get_medal(ranking.rank)
                lines.extend([
                    f"  {medal} {ranking.site_name}",
                    f"     URL: {ranking.site_url}",
                    f"     [质量分]: {ranking.quality_score:.1f}",
                    f"     [数据量]: {ranking.total_records}",
                    f"     [难度]: {ranking.difficulty or '[未知]'}",
                    f"     [样例数]: {len(ranking.samples)}",
                    f""
                ])

        # [失败站点]
        if result.failed_sites:
            lines.extend([
                f"[【失败站点】]",
                f"",
            ])
            for site in result.failed_sites:
                lines.append(f"  [❌] {site.site_name}: {site.reason}")
                if site.error_message:
                    error = site.error_message[:50] + "..." if len(site.error_message) > 50 else site.error_message
                    lines.append(f"     [错误]: {error}")
            lines.append("")

        lines.append(f"{'='*70}")

        return "\n".join(lines)

    def export_markdown(self, result: ResearchResult) -> str:
        """
        [导出为] Markdown [格式]

        Args:
            result: [调研结果]

        Returns:
            str: Markdown [格式的报告]
        """
        lines = [
            f"# [数据源调研报告]",
            f"",
            f"## [基本信息]",
            f"",
            f"- **[任务]ID**: {result.task_id}",
            f"- **[用户需求]**: {result.query}",
            f"- **[总站点数]**: {result.total_sites}",
            f"- **[成功站点]**: {result.successful_sites}",
            f"- **[失败站点]**: {result.failed_sites_count}",
            f"- **[总耗时]**: {self._format_duration(result.total_duration_sec)}",
            f"",
            f"## [站点排行榜]",
            f"",
            f"| [排名] | [站点] | [质量分] | [数据量] | [难度] |",
            f"|------|------|--------|--------|------|",
        ]

        for ranking in result.rankings:
            medal = "[🥇]" if ranking.rank == 1 else "[🥈]" if ranking.rank == 2 else "[🥉]" if ranking.rank == 3 else f"{ranking.rank}"
            quantity = self._format_quantity(ranking.total_records)
            difficulty = ranking.difficulty or "[未知]"
            lines.append(f"| {medal} | {ranking.site_name} | {ranking.quality_score:.1f} | {quantity} | {difficulty} |")

        lines.extend([
            f"",
            f"## [失败站点]",
            f"",
        ])

        if result.failed_sites:
            for site in result.failed_sites:
                lines.append(f"- [❌] **{site.site_name}**: {site.reason}")
        else:
            lines.append("[无失败站点]")

        lines.extend([
            f"",
            f"---",
            f"*[报告生成时间]: {result.completed_at or '[未知]'}*",
        ])

        return "\n".join(lines)

    def _get_medal(self, rank: int) -> str:
        """[获取排名奖牌]"""
        if rank == 1:
            return "[🥇]"
        elif rank == 2:
            return "[🥈]"
        elif rank == 3:
            return "[🥉]"
        else:
            return f"{rank}."

    def _format_quantity(self, count: int) -> str:
        """[格式化数量]"""
        if count >= 10000:
            return f"{count/10000:.1f}[万]"
        elif count >= 1000:
            return f"{count/1000:.1f}k"
        else:
            return str(count)

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
