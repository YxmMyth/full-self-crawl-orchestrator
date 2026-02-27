"""[状态管理器] - [管理任务状态]"""

import json
from datetime import datetime
from typing import Dict, List, Optional

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None

from ..models import CandidateSite, RefinedRequirement, TaskInfo, TaskResult


class StateManager:
    """[状态管理器] - [管理任务状态]"""

    def __init__(self, redis_client: Optional["Redis"] = None):
        self.redis = redis_client
        self._local_storage: Dict[str, any] = {}

    async def create_task(
        self,
        task_id: str,
        user_query: str,
        requirement: RefinedRequirement
    ) -> None:
        """
        [创建任务]

        Args:
            task_id: [任务]ID
            user_query: [用户原始查询]
            requirement: [精确化需求]
        """
        task_info = TaskInfo(
            task_id=task_id,
            user_query=user_query,
            refined_requirement=requirement,
            status="pending"
        )

        if self.redis:
            await self.redis.hset(f"task:{task_id}", mapping={
                "status": "pending",
                "user_query": user_query,
                "requirement": json.dumps(requirement.model_dump()),
                "created_at": datetime.now().isoformat()
            })
        else:
            self._local_storage[f"task:{task_id}"] = task_info.model_dump()

    async def set_task_status(self, task_id: str, status: str) -> None:
        """
        [设置任务状态]

        Args:
            task_id: [任务]ID
            status: [状态] (pending/running/completed/failed)
        """
        if self.redis:
            await self.redis.hset(f"task:{task_id}", "status", status)
            if status in ["completed", "failed"]:
                await self.redis.hset(
                    f"task:{task_id}",
                    "completed_at",
                    datetime.now().isoformat()
                )
        else:
            key = f"task:{task_id}"
            if key in self._local_storage:
                self._local_storage[key]["status"] = status
                if status in ["completed", "failed"]:
                    self._local_storage[key]["completed_at"] = datetime.now().isoformat()

    async def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """
        [获取任务信息]

        Args:
            task_id: [任务]ID

        Returns:
            TaskInfo: [任务信息]
        """
        if self.redis:
            data = await self.redis.hgetall(f"task:{task_id}")
            if data:
                return TaskInfo(
                    task_id=task_id,
                    user_query=data.get("user_query", ""),
                    refined_requirement=RefinedRequirement(
                        **json.loads(data.get("requirement", "{}"))
                    ) if "requirement" in data else None,
                    status=data.get("status", "unknown"),
                    created_at=data.get("created_at", ""),
                    completed_at=data.get("completed_at")
                )
        else:
            key = f"task:{task_id}"
            if key in self._local_storage:
                return TaskInfo(**self._local_storage[key])

        return None

    async def create_site_queue(
        self,
        task_id: str,
        sites: List[CandidateSite]
    ) -> None:
        """
        [创建站点队列]

        Args:
            task_id: [任务]ID
            sites: [候选站点列表]
        """
        sites_json = [json.dumps(site.model_dump()) for site in sites]

        if self.redis:
            await self.redis.delete(f"task:{task_id}:queue")
            if sites_json:
                await self.redis.rpush(f"task:{task_id}:queue", *sites_json)
        else:
            self._local_storage[f"task:{task_id}:queue"] = sites_json

    async def get_next_site(self, task_id: str) -> Optional[CandidateSite]:
        """
        [获取下一个待处理站点]

        Args:
            task_id: [任务]ID

        Returns:
            CandidateSite: [下一个站点，如果没有则返回] None
        """
        if self.redis:
            site_json = await self.redis.lpop(f"task:{task_id}:queue")
            if site_json:
                return CandidateSite(**json.loads(site_json))
        else:
            key = f"task:{task_id}:queue"
            if key in self._local_storage and self._local_storage[key]:
                site_json = self._local_storage[key].pop(0)
                return CandidateSite(**json.loads(site_json))

        return None

    async def set_current_site(
        self,
        task_id: str,
        site: CandidateSite
    ) -> None:
        """
        [设置当前处理的站点]

        Args:
            task_id: [任务]ID
            site: [当前站点]
        """
        data = {
            "site_url": site.site_url,
            "site_name": site.site_name,
            "started_at": datetime.now().isoformat()
        }

        if self.redis:
            await self.redis.hset(f"task:{task_id}:current", mapping=data)
        else:
            self._local_storage[f"task:{task_id}:current"] = data

    async def get_current_site(self, task_id: str) -> Optional[CandidateSite]:
        """
        [获取当前处理的站点]

        Args:
            task_id: [任务]ID

        Returns:
            CandidateSite: [当前站点]
        """
        if self.redis:
            data = await self.redis.hgetall(f"task:{task_id}:current")
            if data:
                return CandidateSite(
                    site_name=data.get("site_name", ""),
                    site_url=data.get("site_url", ""),
                    description="",
                    priority=5
                )
        else:
            key = f"task:{task_id}:current"
            if key in self._local_storage:
                data = self._local_storage[key]
                return CandidateSite(
                    site_name=data.get("site_name", ""),
                    site_url=data.get("site_url", ""),
                    description="",
                    priority=5
                )

        return None

    async def save_result(self, task_id: str, result: TaskResult) -> None:
        """
        [保存] Agent [结果]

        Args:
            task_id: [任务]ID
            result: [任务结果]
        """
        result_json = json.dumps(result.model_dump())

        if self.redis:
            await self.redis.lpush(f"task:{task_id}:results", result_json)
        else:
            key = f"task:{task_id}:results"
            if key not in self._local_storage:
                self._local_storage[key] = []
            self._local_storage[key].append(result.model_dump())

    async def get_results(self, task_id: str) -> List[TaskResult]:
        """
        [获取所有结果]

        Args:
            task_id: [任务]ID

        Returns:
            List[TaskResult]: [结果列表]
        """
        if self.redis:
            results_json = await self.redis.lrange(f"task:{task_id}:results", 0, -1)
            return [TaskResult(**json.loads(r)) for r in results_json]
        else:
            key = f"task:{task_id}:results"
            results = self._local_storage.get(key, [])
            return [TaskResult(**r) for r in results]

    async def increment_successful_count(self, task_id: str) -> None:
        """
        [增加成功站点计数]

        Args:
            task_id: [任务]ID
        """
        if self.redis:
            await self.redis.hincrby(f"task:{task_id}", "successful_sites", 1)
        else:
            key = f"task:{task_id}"
            if key in self._local_storage:
                current = self._local_storage[key].get("successful_sites", 0)
                self._local_storage[key]["successful_sites"] = current + 1

    async def clear_task(self, task_id: str) -> None:
        """
        [清理任务数据]

        Args:
            task_id: [任务]ID
        """
        if self.redis:
            keys = [
                f"task:{task_id}",
                f"task:{task_id}:queue",
                f"task:{task_id}:current",
                f"task:{task_id}:results"
            ]
            for key in keys:
                await self.redis.delete(key)
        else:
            keys_to_delete = [
                f"task:{task_id}",
                f"task:{task_id}:queue",
                f"task:{task_id}:current",
                f"task:{task_id}:results"
            ]
            for key in keys_to_delete:
                if key in self._local_storage:
                    del self._local_storage[key]
