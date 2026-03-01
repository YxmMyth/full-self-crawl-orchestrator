"""
Agent 运行器 — Docker 容器实现

替换原来的 Mock 实现，真正启动 Agent 容器执行任务。
支持两种运行模式:
- Docker 模式（生产）: 每个 Agent 一个容器
- Subprocess 模式（本地开发）: 每个 Agent 一个子进程
"""

import asyncio
import json
import os
import logging
from typing import Optional

from ..models import TaskParams, TaskResult

logger = logging.getLogger('agent_runner')


class AgentRunner:
    """
    Agent 运行器

    mode='docker':     启动 Docker 容器（生产环境）
    mode='subprocess': 启动子进程（本地开发，不需要 Docker）
    mode='mock':       原来的 Mock 模式（纯测试）
    """

    def __init__(
        self,
        agent_path: Optional[str] = None,
        use_subprocess: bool = True,
        mode: str = "subprocess",
        agent_image: str = "full-self-crawl-agent:latest",
        redis_url: str = "redis://localhost:6379",
        agent_memory_limit: str = "2g",
        agent_cpu_limit: float = 2.0,
    ):
        self.agent_path = agent_path or "../full-self-crawl-agent"
        self.mode = mode
        self.agent_image = agent_image
        self.redis_url = redis_url
        self.agent_memory_limit = agent_memory_limit
        self.agent_cpu_limit = agent_cpu_limit

        self._current_task_id: Optional[str] = None
        self._cancelled: bool = False
        self._current_process = None
        self._current_container = None

    async def run(self, task_params: TaskParams) -> TaskResult:
        """分发到对应模式"""
        self._current_task_id = task_params.task_id
        self._cancelled = False

        if self.mode == "docker":
            return await self._run_docker(task_params)
        elif self.mode == "subprocess":
            return await self._run_subprocess(task_params)
        else:
            return await self._run_mock(task_params)

    # ── Docker 模式 ──

    async def _run_docker(self, task_params: TaskParams) -> TaskResult:
        """启动 Docker 容器运行 Agent"""
        try:
            import docker
        except ImportError:
            logger.error("docker 包未安装，无法使用 docker 模式")
            return self._fail_result(task_params, "docker 包未安装")

        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.error("redis 包未安装，无法使用 docker 模式")
            return self._fail_result(task_params, "redis 包未安装")

        client = docker.from_env()
        agent_spec = self._build_agent_spec(task_params)
        container_name = f"agent-{task_params.task_id}".replace(":", "-")[:63]

        try:
            container = client.containers.run(
                self.agent_image,
                detach=True,
                remove=True,
                name=container_name,
                mem_limit=self.agent_memory_limit,
                nano_cpus=int(self.agent_cpu_limit * 1e9),
                environment={
                    "TASK_SPEC": json.dumps(agent_spec),
                    "TASK_ID": task_params.task_id,
                    "RESULT_REDIS_URL": self.redis_url,
                    "ZHIPU_API_KEY": os.environ.get("ZHIPU_API_KEY", ""),
                    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
                },
                network="crawl-network",
            )
            self._current_container = container
        except Exception as e:
            logger.error(f"容器启动失败: {e}")
            return self._fail_result(task_params, f"容器启动失败: {e}")

        # 通过 Redis PubSub 等待结果
        try:
            r = aioredis.from_url(self.redis_url)
            pubsub = r.pubsub()
            await pubsub.subscribe(f"agent:done:{task_params.task_id}")

            async for message in pubsub.listen():
                if self._cancelled:
                    container.kill()
                    return self._fail_result(task_params, "任务被取消")
                if message["type"] == "message":
                    break

            raw = await r.get(f"agent:result:{task_params.task_id}")
            await pubsub.unsubscribe()
            await r.close()

            if raw:
                data = json.loads(raw)
                return self._parse_agent_result(task_params, data)
            else:
                return self._fail_result(task_params, "Agent 无返回结果")
        except Exception as e:
            return self._fail_result(task_params, str(e))

    # ── Subprocess 模式 ──

    async def _run_subprocess(self, task_params: TaskParams) -> TaskResult:
        """本地子进程运行 Agent"""
        import tempfile

        agent_spec = self._build_agent_spec(task_params)

        # Sanitize task_id for use in filename prefix (remove path separators and special chars)
        safe_task_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_params.task_id)[:50]
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, prefix=f'spec_{safe_task_id}_'
        ) as f:
            json.dump(agent_spec, f, ensure_ascii=False)
            spec_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                'python', '-m', 'src.main', spec_path,
                cwd=self.agent_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ},
            )
            self._current_process = proc

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=1800
            )

            if proc.returncode == 0:
                try:
                    result_data = json.loads(stdout.decode('utf-8', errors='replace'))
                    return self._parse_agent_result(task_params, result_data)
                except json.JSONDecodeError:
                    return TaskResult(
                        task_id=task_params.task_id,
                        site_url=task_params.site_url,
                        site_name=task_params.site_name,
                        status="success",
                        quality_score=70.0,
                    )
            else:
                error = stderr.decode('utf-8', errors='replace')[:500]
                return self._fail_result(task_params, f"Agent 进程退出码 {proc.returncode}: {error}")

        except asyncio.TimeoutError:
            if self._current_process:
                self._current_process.kill()
            return self._fail_result(task_params, "Agent 执行超时 (>1800s)")
        finally:
            if os.path.exists(spec_path):
                os.unlink(spec_path)

    # ── Mock 模式（保留原有测试用） ──

    async def _run_mock(self, task_params: TaskParams) -> TaskResult:
        """保留原来的 Mock 实现，用于纯 UI/流程测试"""
        import random
        process_time = random.uniform(1, 3)
        for _ in range(5):
            if self._cancelled:
                return self._fail_result(task_params, "任务被取消")
            await asyncio.sleep(process_time / 5)

        if random.random() < 0.8:
            return TaskResult(
                task_id=task_params.task_id,
                site_url=task_params.site_url,
                site_name=task_params.site_name,
                status="success",
                quality_score=round(random.uniform(60, 98), 1),
                total_records=random.randint(1000, 50000),
                samples=[{"title": f"示例{i}", "url": f"{task_params.site_url}/{i}"} for i in range(3)],
                duration_sec=int(process_time * 5),
            )
        else:
            return self._fail_result(task_params, random.choice(["站点超时", "反爬阻止"]))

    # ── 公共方法 ──

    def _build_agent_spec(self, task_params: TaskParams) -> dict:
        """TaskParams → Agent Spec 格式转换"""
        req = task_params.requirement
        return {
            "task_id": task_params.task_id,
            "task_name": f"crawl_{task_params.site_name}",
            "target_url": task_params.site_url,
            "goal": req.topic,
            "targets": [{"fields": [{"name": field_name, "required": True} for field_name in req.target_fields]}],
            "crawl_mode": "auto",
            "max_iterations": 10,
            "headless": True,
            "completion_gate": ["execution_success", "quality_score >= 0.6"],
        }

    def _parse_agent_result(self, task_params: TaskParams, data: dict) -> TaskResult:
        """Agent 原始结果 → Orchestrator TaskResult"""
        extracted = data.get('extracted_data', [])
        return TaskResult(
            task_id=task_params.task_id,
            site_url=task_params.site_url,
            site_name=task_params.site_name,
            status="success" if data.get("success") else "failed",
            quality_score=float(data.get("quality_score", 0)) * 100,
            total_pages=data.get("total_pages", 0),
            total_records=len(extracted),
            samples=extracted[:5],
            duration_sec=int(data.get("total_time", 0)),
            strategy_used=data.get("crawl_mode", ""),
            error_message=data.get("error", ""),
        )

    def _fail_result(self, task_params: TaskParams, error: str) -> TaskResult:
        return TaskResult(
            task_id=task_params.task_id,
            site_url=task_params.site_url,
            site_name=task_params.site_name,
            status="failed",
            error_message=error,
        )

    async def cancel(self) -> None:
        """取消当前任务"""
        self._cancelled = True
        if self._current_container:
            try:
                self._current_container.kill()
            except Exception:
                pass
        if self._current_process:
            try:
                self._current_process.kill()
            except Exception:
                pass

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._current_task_id is not None and not self._cancelled

    async def listen_progress(self, task_id: str, callback) -> None:
        """监听进度（Mock 实现）"""
        pass
