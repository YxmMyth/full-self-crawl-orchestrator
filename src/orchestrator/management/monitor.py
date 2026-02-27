"""[监控器] - [实时进度推送]"""

import json
from datetime import datetime
from typing import Callable, Optional

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None

from ..models import ProgressUpdate, TaskResult


class Monitor:
    """[监控器] - [实时进度推送]"""

    def __init__(
        self,
        redis_client: Optional["Redis"] = None,
        update_interval: int = 5
    ):
        self.redis = redis_client
        self.update_interval = update_interval
        self._callbacks: dict[str, list[Callable]] = {}
        self._local_storage = {}

    async def report_progress(
        self,
        task_id: str,
        current_site: str,
        completed: int,
        total: int,
        message: str = ""
    ) -> None:
        """
        [报告进度]

        Args:
            task_id: [任务]ID
            current_site: [当前处理的站点]
            completed: [已完成数量]
            total: [总数量]
            message: [状态消息]
        """
        progress = ProgressUpdate(
            task_id=task_id,
            status="running",
            current_url=current_site,
            progress=completed / total if total > 0 else 0.0,
            collected_count=completed,
            message=message,
            timestamp=datetime.now().isoformat()
        )

        # [存储进度]
        if self.redis:
            await self.redis.set(
                f"task:{task_id}:progress",
                json.dumps(progress.model_dump())
            )
            # [发布到频道]
            await self.redis.publish(
                f"task:{task_id}:progress_channel",
                json.dumps(progress.model_dump())
            )
        else:
            self._local_storage[f"task:{task_id}:progress"] = progress.model_dump()

        # [触发回调]
        await self._notify_callbacks(task_id, progress)

    async def report_agent_complete(
        self,
        task_id: str,
        site_url: str,
        result: TaskResult
    ) -> None:
        """
        [报告] Agent [完成]

        Args:
            task_id: [任务]ID
            site_url: [站点]URL
            result: [任务结果]
        """
        message = f"[✅] {result.site_name}: [质量分] {result.quality_score:.1f}"

        progress = ProgressUpdate(
            task_id=task_id,
            status="agent_complete",
            current_url=site_url,
            collected_count=result.total_records,
            message=message,
            timestamp=datetime.now().isoformat()
        )

        await self._notify_callbacks(task_id, progress)

    async def report_agent_error(
        self,
        task_id: str,
        site_url: str,
        error: str
    ) -> None:
        """
        [报告] Agent [错误]

        Args:
            task_id: [任务]ID
            site_url: [站点]URL
            error: [错误信息]
        """
        progress = ProgressUpdate(
            task_id=task_id,
            status="agent_error",
            current_url=site_url,
            message=f"[❌] [错误]: {error}",
            timestamp=datetime.now().isoformat()
        )

        await self._notify_callbacks(task_id, progress)

    async def report_task_complete(
        self,
        task_id: str,
        total_sites: int,
        successful_sites: int
    ) -> None:
        """
        [报告任务完成]

        Args:
            task_id: [任务]ID
            total_sites: [总站点数]
            successful_sites: [成功站点数]
        """
        progress = ProgressUpdate(
            task_id=task_id,
            status="completed",
            progress=1.0,
            message=f"[🎉] [任务完成]! [成功] {successful_sites}/{total_sites} [站点]",
            timestamp=datetime.now().isoformat()
        )

        if self.redis:
            await self.redis.set(
                f"task:{task_id}:progress",
                json.dumps(progress.model_dump())
            )
            await self.redis.publish(
                f"task:{task_id}:progress_channel",
                json.dumps(progress.model_dump())
            )

        await self._notify_callbacks(task_id, progress)

    def register_callback(
        self,
        task_id: str,
        callback: Callable[[ProgressUpdate], None]
    ) -> None:
        """
        [注册进度回调]

        Args:
            task_id: [任务]ID
            callback: [回调函数]
        """
        if task_id not in self._callbacks:
            self._callbacks[task_id] = []
        self._callbacks[task_id].append(callback)

    def unregister_callback(
        self,
        task_id: str,
        callback: Callable[[ProgressUpdate], None]
    ) -> None:
        """
        [取消注册进度回调]

        Args:
            task_id: [任务]ID
            callback: [回调函数]
        """
        if task_id in self._callbacks:
            if callback in self._callbacks[task_id]:
                self._callbacks[task_id].remove(callback)

    async def _notify_callbacks(self, task_id: str, progress: ProgressUpdate) -> None:
        """
        [通知所有回调]

        Args:
            task_id: [任务]ID
            progress: [进度更新]
        """
        if task_id in self._callbacks:
            for callback in self._callbacks[task_id]:
                try:
                    result = callback(progress)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    print(f"Error in progress callback: {e}")

    async def get_progress(self, task_id: str) -> Optional[ProgressUpdate]:
        """
        [获取当前进度]

        Args:
            task_id: [任务]ID

        Returns:
            ProgressUpdate: [当前进度]
        """
        if self.redis:
            data = await self.redis.get(f"task:{task_id}:progress")
            if data:
                return ProgressUpdate(**json.loads(data))
        else:
            data = self._local_storage.get(f"task:{task_id}:progress")
            if data:
                return ProgressUpdate(**data)

        return None

    async def listen_progress(self, task_id: str, callback: Callable[[ProgressUpdate], None]) -> None:
        """
        [监听进度推送（通过] Redis Pub/Sub[）]

        Args:
            task_id: [任务]ID
            callback: [回调函数]
        """
        if not self.redis:
            # [如果没有] Redis[，直接注册回调]
            self.register_callback(task_id, callback)
            return

        # [使用] Redis Pub/Sub
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"task:{task_id}:progress_channel")

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        progress = ProgressUpdate(**json.loads(message['data']))
                        await callback(progress)
                    except Exception as e:
                        print(f"Error processing progress message: {e}")
        except Exception as e:
            print(f"Error in progress listener: {e}")
        finally:
            await pubsub.unsubscribe(f"task:{task_id}:progress_channel")
