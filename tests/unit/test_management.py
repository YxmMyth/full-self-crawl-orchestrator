"""单元测试 - 管理层模块"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
import asyncio
from orchestrator.management.state_manager import StateManager
from orchestrator.management.monitor import Monitor
from orchestrator.management.agent_runner import AgentRunner
from orchestrator.models import (
    CandidateSite,
    RefinedRequirement,
    TaskParams,
    TaskResult,
    ProgressUpdate,
)


class TestStateManager:
    """测试状态管理器"""

    @pytest.fixture
    def state_manager(self):
        return StateManager()

    @pytest.fixture
    def sample_requirement(self):
        return RefinedRequirement(
            topic="测试主题",
            target_fields=["字段1"],
            quantity=100
        )

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, state_manager, sample_requirement):
        """测试创建和获取任务"""
        task_id = "test_task_001"
        user_query = "测试查询"

        await state_manager.create_task(task_id, user_query, sample_requirement)
        task_info = await state_manager.get_task_info(task_id)

        assert task_info is not None
        assert task_info.task_id == task_id
        assert task_info.user_query == user_query
        assert task_info.status == "pending"

    @pytest.mark.asyncio
    async def test_set_task_status(self, state_manager, sample_requirement):
        """测试设置任务状态"""
        task_id = "test_task_002"
        await state_manager.create_task(task_id, "测试", sample_requirement)

        await state_manager.set_task_status(task_id, "running")
        task_info = await state_manager.get_task_info(task_id)
        assert task_info.status == "running"

    @pytest.mark.asyncio
    async def test_site_queue_operations(self, state_manager):
        """测试站点队列操作"""
        task_id = "test_task_003"
        sites = [
            CandidateSite(site_name=f"站点{i}", site_url=f"https://site{i}.com", priority=i)
            for i in range(1, 4)
        ]

        await state_manager.create_site_queue(task_id, sites)

        # 测试获取下一个站点
        next_site = await state_manager.get_next_site(task_id)
        assert next_site is not None
        assert next_site.site_name == "站点1"

    @pytest.mark.asyncio
    async def test_save_and_get_results(self, state_manager):
        """测试保存和获取结果"""
        task_id = "test_task_004"
        result = TaskResult(
            task_id=f"{task_id}:site1",
            site_url="https://site1.com",
            site_name="站点1",
            status="success",
            quality_score=85.0
        )

        await state_manager.save_result(task_id, result)
        results = await state_manager.get_results(task_id)

        assert len(results) == 1
        assert results[0].quality_score == 85.0


class TestMonitor:
    """测试监控器"""

    @pytest.fixture
    def monitor(self):
        return Monitor(update_interval=1)

    @pytest.mark.asyncio
    async def test_report_progress(self, monitor):
        """测试报告进度"""
        task_id = "test_task_005"

        await monitor.report_progress(
            task_id=task_id,
            current_site="https://example.com",
            completed=5,
            total=10,
            message="测试中"
        )

        progress = await monitor.get_progress(task_id)
        assert progress is not None
        assert progress.progress == 0.5
        assert progress.message == "测试中"

    @pytest.mark.asyncio
    async def test_callback_registration(self, monitor):
        """测试回调函数注册"""
        task_id = "test_task_006"
        callback_called = False
        received_progress = None

        def test_callback(progress: ProgressUpdate):
            nonlocal callback_called, received_progress
            callback_called = True
            received_progress = progress

        monitor.register_callback(task_id, test_callback)

        await monitor.report_progress(
            task_id=task_id,
            current_site="https://example.com",
            completed=1,
            total=2,
            message="测试回调"
        )

        # 给回调一点时间执行
        await asyncio.sleep(0.1)
        assert callback_called is True
        assert received_progress is not None


class TestAgentRunner:
    """测试 Agent 运行器（Mock 模式）"""

    @pytest.fixture
    def agent_runner(self):
        return AgentRunner(use_subprocess=True)

    @pytest.fixture
    def sample_task_params(self):
        return TaskParams(
            task_id="test_task_007:https://example.com",
            site_url="https://example.com",
            site_name="测试站点",
            requirement=RefinedRequirement(topic="测试", target_fields=["标题"])
        )

    @pytest.mark.asyncio
    async def test_run_returns_task_result(self, agent_runner, sample_task_params):
        """测试运行返回 TaskResult"""
        result = await agent_runner.run(sample_task_params)

        assert isinstance(result, TaskResult)
        assert result.task_id == sample_task_params.task_id
        assert result.site_url == sample_task_params.site_url

    @pytest.mark.asyncio
    async def test_run_returns_valid_status(self, agent_runner, sample_task_params):
        """测试运行返回有效的状态"""
        result = await agent_runner.run(sample_task_params)

        assert result.status in ["success", "failed"]

        if result.status == "success":
            assert 0 <= result.quality_score <= 100
            assert result.total_records >= 0
        else:
            assert result.error_message != ""

    @pytest.mark.asyncio
    async def test_cancel_stops_execution(self, agent_runner):
        """测试取消功能"""
        # 取消不应该抛出异常
        await agent_runner.cancel()
        assert agent_runner._cancelled is True


class TestIntegration:
    """集成测试 - 管理层模块协同工作"""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self):
        """测试完整的任务生命周期"""
        state_manager = StateManager()
        monitor = Monitor()

        task_id = "integration_test_001"
        requirement = RefinedRequirement(topic="集成测试", target_fields=["字段1"])

        # 1. 创建任务
        await state_manager.create_task(task_id, "集成测试查询", requirement)

        # 2. 更新状态为运行中
        await state_manager.set_task_status(task_id, "running")

        # 3. 创建站点队列
        sites = [
            CandidateSite(site_name="站点1", site_url="https://site1.com", priority=1),
            CandidateSite(site_name="站点2", site_url="https://site2.com", priority=2),
        ]
        await state_manager.create_site_queue(task_id, sites)

        # 4. 报告进度
        await monitor.report_progress(
            task_id=task_id,
            current_site="https://site1.com",
            completed=1,
            total=2,
            message="处理中"
        )

        # 5. 保存结果
        result = TaskResult(
            task_id=f"{task_id}:site1",
            site_url="https://site1.com",
            site_name="站点1",
            status="success",
            quality_score=90.0
        )
        await state_manager.save_result(task_id, result)

        # 6. 验证状态
        task_info = await state_manager.get_task_info(task_id)
        assert task_info.status == "running"

        results = await state_manager.get_results(task_id)
        assert len(results) == 1

        progress = await monitor.get_progress(task_id)
        assert progress.progress == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
