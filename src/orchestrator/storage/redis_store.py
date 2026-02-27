"""Redis [存储封装]"""

import json
from typing import Any, Dict, List, Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class RedisStore:
    """Redis [存储封装]"""

    def __init__(
        self,
        url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        """
        [初始化] Redis [存储]

        Args:
            url: Redis URL ([如] redis://localhost:6379/0)
            host: Redis [主机]
            port: Redis [端口]
            db: Redis [数据库]
            password: Redis [密码]
        """
        self.url = url
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client: Optional[Any] = None

    async def connect(self) -> Any:
        """
        [连接到] Redis

        Returns:
            Redis client
        """
        if aioredis is None:
            raise ImportError("redis is not installed. Run: pip install redis")

        if self.url:
            self._client = aioredis.from_url(
                self.url,
                password=self.password,
                decode_responses=True
            )
        else:
            self._client = aioredis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )

        return self._client

    async def disconnect(self) -> None:
        """[断开连接]"""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """
        [检查连接]

        Returns:
            bool: [是否连接成功]
        """
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def get_client(self) -> Any:
        """
        [获取] Redis [客户端]

        Returns:
            Redis client
        """
        if self._client is None:
            await self.connect()
        return self._client

    # [任务队列操作]

    async def queue_push(self, queue_name: str, *items: str) -> int:
        """
        [向队列添加元素]

        Args:
            queue_name: [队列名称]
            items: [要添加的元素]

        Returns:
            int: [队列长度]
        """
        client = await self.get_client()
        return await client.rpush(queue_name, *items)

    async def queue_pop(self, queue_name: str) -> Optional[str]:
        """
        [从队列取出元素]

        Args:
            queue_name: [队列名称]

        Returns:
            str: [取出的元素，如果没有则返回] None
        """
        client = await self.get_client()
        result = await client.lpop(queue_name)
        return result

    async def queue_length(self, queue_name: str) -> int:
        """
        [获取队列长度]

        Args:
            queue_name: [队列名称]

        Returns:
            int: [队列长度]
        """
        client = await self.get_client()
        return await client.llen(queue_name)

    async def queue_clear(self, queue_name: str) -> None:
        """
        [清空队列]

        Args:
            queue_name: [队列名称]
        """
        client = await self.get_client()
        await client.delete(queue_name)

    # Hash [操作]

    async def hash_set(self, key: str, mapping: Dict[str, str]) -> None:
        """
        [设置] Hash [值]

        Args:
            key: [键名]
            mapping: [键值对]
        """
        client = await self.get_client()
        await client.hset(key, mapping=mapping)

    async def hash_get(self, key: str, field: str) -> Optional[str]:
        """
        [获取] Hash [字段值]

        Args:
            key: [键名]
            field: [字段名]

        Returns:
            str: [字段值]
        """
        client = await self.get_client()
        return await client.hget(key, field)

    async def hash_get_all(self, key: str) -> Dict[str, str]:
        """
        [获取所有] Hash [字段]

        Args:
            key: [键名]

        Returns:
            dict: [所有字段]
        """
        client = await self.get_client()
        return await client.hgetall(key)

    async def hash_delete(self, key: str) -> None:
        """
        [删除] Hash

        Args:
            key: [键名]
        """
        client = await self.get_client()
        await client.delete(key)

    # [发布订阅]

    async def publish(self, channel: str, message: str) -> int:
        """
        [发布消息]

        Args:
            channel: [频道名称]
            message: [消息内容]

        Returns:
            int: [接收消息的客户端数]
        """
        client = await self.get_client()
        return await client.publish(channel, message)

    async def subscribe(self, channel: str):
        """
        [订阅频道]

        Args:
            channel: [频道名称]

        Returns:
            PubSub [对象]
        """
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    # List [操作]

    async def list_push(self, key: str, *values: str) -> int:
        """
        [向列表添加元素]

        Args:
            key: [键名]
            values: [要添加的值]

        Returns:
            int: [列表长度]
        """
        client = await self.get_client()
        return await client.lpush(key, *values)

    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """
        [获取列表范围]

        Args:
            key: [键名]
            start: [开始索引]
            end: [结束索引]

        Returns:
            list: [元素列表]
        """
        client = await self.get_client()
        return await client.lrange(key, start, end)

    # Key [操作]

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        """
        [设置键值]

        Args:
            key: [键名]
            value: [值]
            expire: [过期时间]([秒])
        """
        client = await self.get_client()
        if expire:
            await client.setex(key, expire, value)
        else:
            await client.set(key, value)

    async def get(self, key: str) -> Optional[str]:
        """
        [获取键值]

        Args:
            key: [键名]

        Returns:
            str: [值]
        """
        client = await self.get_client()
        return await client.get(key)

    async def delete(self, *keys: str) -> int:
        """
        [删除键]

        Args:
            keys: [键名列表]

        Returns:
            int: [删除的键数]
        """
        client = await self.get_client()
        return await client.delete(*keys)
