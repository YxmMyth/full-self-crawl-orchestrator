"""PostgreSQL [存储封装]"""

import json
from datetime import datetime
from typing import Dict, List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None


class PostgresStore:
    """PostgreSQL [存储封装]"""

    def __init__(
        self,
        dsn: Optional[str] = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "crawler",
        user: str = "postgres",
        password: str = ""
    ):
        """
        [初始化] PostgreSQL [存储]

        Args:
            dsn: [数据库连接字符串]
            host: [数据库主机]
            port: [数据库端口]
            database: [数据库名]
            user: [用户名]
            password: [密码]
        """
        self.dsn = dsn
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._pool: Optional[Any] = None

    async def connect(self) -> Any:
        """
        [连接到] PostgreSQL

        Returns:
            [连接池]
        """
        if asyncpg is None:
            raise ImportError("asyncpg is not installed. Run: pip install asyncpg")

        if self.dsn:
            self._pool = await asyncpg.create_pool(self.dsn)
        else:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )

        return self._pool

    async def disconnect(self) -> None:
        """[断开连接]"""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_pool(self) -> Any:
        """
        [获取连接池]

        Returns:
            [连接池]
        """
        if self._pool is None:
            await self.connect()
        return self._pool

    # [任务记录操作]

    async def create_task(
        self,
        task_id: str,
        user_query: str,
        refined_requirement: Optional[Dict] = None
    ) -> None:
        """
        [创建任务记录]

        Args:
            task_id: [任务]ID
            user_query: [用户查询]
            refined_requirement: [精确化需求]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO research_tasks (
                    task_id, user_query, refined_requirement, status, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (task_id) DO UPDATE SET
                    user_query = EXCLUDED.user_query,
                    refined_requirement = EXCLUDED.refined_requirement
                """,
                task_id,
                user_query,
                json.dumps(refined_requirement) if refined_requirement else "{}",
                "pending",
                datetime.now()
            )

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        candidate_sites: Optional[List[Dict]] = None,
        successful_sites: Optional[int] = None
    ) -> None:
        """
        [更新任务状态]

        Args:
            task_id: [任务]ID
            status: [状态]
            candidate_sites: [候选站点列表]
            successful_sites: [成功站点数]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            updates = ["status = $1"]
            params = [status]
            param_idx = 2

            if candidate_sites is not None:
                updates.append(f"candidate_sites = ${param_idx}")
                params.append(json.dumps(candidate_sites))
                param_idx += 1

            if successful_sites is not None:
                updates.append(f"successful_sites = ${param_idx}")
                params.append(successful_sites)
                param_idx += 1

            if status in ["completed", "failed"]:
                updates.append(f"completed_at = ${param_idx}")
                params.append(datetime.now())
                param_idx += 1

            params.append(task_id)

            query = f"""
                UPDATE research_tasks
                SET {', '.join(updates)}
                WHERE task_id = ${param_idx}
            """

            await conn.execute(query, *params)

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """
        [获取任务记录]

        Args:
            task_id: [任务]ID

        Returns:
            dict: [任务记录]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM research_tasks WHERE task_id = $1",
                task_id
            )
            if row:
                return dict(row)
            return None

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        [列出任务]

        Args:
            status: [状态筛选]
            limit: [数量限制]
            offset: [偏移量]

        Returns:
            list: [任务列表]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT * FROM research_tasks
                    WHERE status = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    status, limit, offset
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM research_tasks
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit, offset
                )
            return [dict(row) for row in rows]

    # [站点结果操作]

    async def save_site_result(self, result: Dict) -> None:
        """
        [保存站点结果]

        Args:
            result: [结果字典]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO site_results (
                    task_id, site_url, site_name, quality_score,
                    total_records, sample_records, duration_sec,
                    strategy_used, difficulty, status, error_message,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (task_id, site_url) DO UPDATE SET
                    site_name = EXCLUDED.site_name,
                    quality_score = EXCLUDED.quality_score,
                    total_records = EXCLUDED.total_records,
                    sample_records = EXCLUDED.sample_records,
                    duration_sec = EXCLUDED.duration_sec,
                    strategy_used = EXCLUDED.strategy_used,
                    difficulty = EXCLUDED.difficulty,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
                """,
                result.get("task_id"),
                result.get("site_url"),
                result.get("site_name"),
                result.get("quality_score"),
                result.get("total_records"),
                json.dumps(result.get("samples", [])),
                result.get("duration_sec"),
                result.get("strategy_used"),
                result.get("difficulty"),
                result.get("status"),
                result.get("error_message"),
                datetime.now()
            )

    async def get_site_results(self, task_id: str) -> List[Dict]:
        """
        [获取站点结果]

        Args:
            task_id: [任务]ID

        Returns:
            list: [结果列表]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM site_results
                WHERE task_id = $1
                ORDER BY quality_score DESC
                """,
                task_id
            )
            return [dict(row) for row in rows]

    # [样本数据操作]

    async def save_sample_records(
        self,
        task_id: str,
        site_url: str,
        records: List[Dict]
    ) -> None:
        """
        [保存样本记录]

        Args:
            task_id: [任务]ID
            site_url: [站点]URL
            records: [记录列表]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            for record in records:
                await conn.execute(
                    """
                    INSERT INTO sample_records (
                        task_id, site_url, record_data, created_at
                    ) VALUES ($1, $2, $3, $4)
                    """,
                    task_id,
                    site_url,
                    json.dumps(record),
                    datetime.now()
                )

    async def get_sample_records(
        self,
        task_id: str,
        site_url: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        [获取样本记录]

        Args:
            task_id: [任务]ID
            site_url: [站点]URL[（可选）]
            limit: [数量限制]

        Returns:
            list: [记录列表]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if site_url:
                rows = await conn.fetch(
                    """
                    SELECT * FROM sample_records
                    WHERE task_id = $1 AND site_url = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    task_id, site_url, limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM sample_records
                    WHERE task_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    task_id, limit
                )
            return [dict(row) for row in rows]

    async def get_stats(self) -> Dict:
        """
        [获取统计信息]

        Returns:
            dict: [统计信息]
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            total_tasks = await conn.fetchval(
                "SELECT COUNT(*) FROM research_tasks"
            )
            completed_tasks = await conn.fetchval(
                "SELECT COUNT(*) FROM research_tasks WHERE status = 'completed'"
            )
            total_sites = await conn.fetchval(
                "SELECT COUNT(*) FROM site_results"
            )
            successful_sites = await conn.fetchval(
                "SELECT COUNT(*) FROM site_results WHERE status = 'success'"
            )

            avg_quality = await conn.fetchval(
                "SELECT AVG(quality_score) FROM site_results WHERE status = 'success'"
            )

            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "total_sites": total_sites,
                "successful_sites": successful_sites,
                "avg_quality_score": float(avg_quality) if avg_quality else 0.0
            }
