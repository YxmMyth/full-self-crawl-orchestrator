"""单元测试 - 战略层模块"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from orchestrator.models import (
    CandidateSite,
    RefinedRequirement,
    TaskParams,
    TaskResult,
    ResearchResult,
)
from orchestrator.strategic.requirement_analyzer import RequirementAnalyzer
from orchestrator.strategic.site_discovery import SiteDiscovery
from orchestrator.strategic.result_aggregator import ResultAggregator


class TestModels:
    """测试数据模型"""

    def test_refined_requirement_creation(self):
        """测试 RefinedRequirement 创建"""
        req = RefinedRequirement(
            topic="科技媒体",
            target_fields=["标题", "作者", "时间"],
            scope="国内",
            quantity=1000
        )
        assert req.topic == "科技媒体"
        assert len(req.target_fields) == 3
        assert req.quantity == 1000

    def test_candidate_site_creation(self):
        """测试 CandidateSite 创建"""
        site = CandidateSite(
            site_name="36氪",
            site_url="https://36kr.com",
            description="创投科技媒体",
            priority=1
        )
        assert site.site_name == "36氪"
        assert site.priority == 1

    def test_task_result_creation(self):
        """测试 TaskResult 创建"""
        result = TaskResult(
            task_id="task_001",
            site_url="https://36kr.com",
            site_name="36氪",
            status="success",
            quality_score=85.5,
            total_records=1000
        )
        assert result.status == "success"
        assert result.quality_score == 85.5


class TestResultAggregator:
    """测试结果整合模块"""

    @pytest.fixture
    def aggregator(self):
        return ResultAggregator()

    @pytest.fixture
    def sample_results(self):
        """生成示例结果"""
        return [
            TaskResult(
                task_id="task_1",
                site_url="https://site1.com",
                site_name="站点1",
                status="success",
                quality_score=90.0,
                total_records=1000
            ),
            TaskResult(
                task_id="task_2",
                site_url="https://site2.com",
                site_name="站点2",
                status="success",
                quality_score=80.0,
                total_records=500
            ),
            TaskResult(
                task_id="task_3",
                site_url="https://site3.com",
                site_name="站点3",
                status="failed",
                error_message="连接超时"
            ),
        ]

    def test_aggregate_creates_correct_rankings(self, aggregator, sample_results):
        """测试聚合结果生成正确的排行榜"""
        result = aggregator.aggregate(
            query="测试查询",
            task_id="test_task",
            results=sample_results
        )

        assert result.total_sites == 3
        assert result.successful_sites == 2
        assert result.failed_sites_count == 1
        assert len(result.rankings) == 2

        # 验证排序（质量分高的在前）
        assert result.rankings[0].quality_score == 90.0
        assert result.rankings[1].quality_score == 80.0

    def test_aggregate_creates_correct_failed_list(self, aggregator, sample_results):
        """测试聚合结果生成正确的失败列表"""
        result = aggregator.aggregate(
            query="测试查询",
            task_id="test_task",
            results=sample_results
        )

        assert len(result.failed_sites) == 1
        assert result.failed_sites[0].site_name == "站点3"
        # 错误消息中包含"超时"
        assert "超时" in result.failed_sites[0].error_message


class TestSiteDiscovery:
    """测试站点挖掘模块"""

    @pytest.fixture
    def discovery(self):
        return SiteDiscovery(min_sites=5, max_sites=10)

    @pytest.fixture
    def sample_requirement(self):
        return RefinedRequirement(
            topic="科技媒体",
            target_fields=["标题", "作者"],
            scope="国内"
        )

    def test_filter_sites_respects_max_sites(self, discovery, sample_requirement):
        """测试站点过滤遵守最大数量限制"""
        sites = [
            CandidateSite(site_name=f"站点{i}", site_url=f"https://site{i}.com", priority=min(i, 10))
            for i in range(1, 20)
        ]

        filtered = discovery.filter_sites(sites, sample_requirement)
        assert len(filtered) <= discovery.max_sites

    def test_fallback_sites_returned_on_empty_topic(self, discovery, sample_requirement):
        """测试当主题匹配不到时返回 fallback 站点"""
        fallback_sites = discovery._get_fallback_sites(sample_requirement)
        assert len(fallback_sites) > 0
        assert all(isinstance(s, CandidateSite) for s in fallback_sites)


class TestRequirementAnalyzer:
    """测试需求分析模块"""

    @pytest.fixture
    def analyzer(self):
        return RequirementAnalyzer()

    @pytest.mark.asyncio
    async def test_suggest_fields_for_known_topics(self, analyzer):
        """测试已知主题的字段建议"""
        # 使用包含关键词的主题
        fields = await analyzer.suggest_fields("[新闻]数据")
        assert "[标题]" in fields
        assert "[作者]" in fields

        # 使用电商主题
        fields = await analyzer.suggest_fields("[电商]商品")
        assert "[价格]" in fields
        assert "[销量]" in fields

    @pytest.mark.asyncio
    async def test_suggest_fields_returns_default_for_unknown_topics(self, analyzer):
        """测试未知主题返回默认字段"""
        fields = await analyzer.suggest_fields("未知主题")
        assert len(fields) >= 3  # 默认字段

    @pytest.mark.asyncio
    async def test_confirm_returns_expected_format(self, analyzer):
        """测试确认消息格式正确"""
        req = RefinedRequirement(
            topic="测试主题",
            target_fields=["字段1", "字段2"],
            quantity=100
        )

        message, auto_confirm = await analyzer.confirm(req)
        assert "测试主题" in message
        assert "字段1" in message
        assert auto_confirm is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
