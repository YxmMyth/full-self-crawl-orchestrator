"""[工具函数和辅助模块]"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Coroutine, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging

T = TypeVar("T")

# [配置日志]
logger = logging.getLogger(__name__)


class LLMClient:
    """LLM [客户端封装] - [支持] DeepSeek API"""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str = "",
        base_url: str = "https://api.deepseek.com"
    ):
        self.model = model
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.client = httpx.AsyncClient(timeout=60.0)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        [调用] DeepSeek API [完成对话] - [带自动重试机制]

        Args:
            system: [系统提示词]
            user: [用户输入]
            temperature: [温度参数]
            max_tokens: [最大生成]token[数]

        Returns:
            str: LLM [生成的响应文本]

        Raises:
            ValueError: API key [未配置]
            RuntimeError: API [调用失败（重试后仍然失败）]
            httpx.ConnectError: [连接错误]
            httpx.TimeoutException: [超时错误]
        """
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY environment variable.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.ConnectError as e:
            logger.error(f"[连接到] DeepSeek API [失败]: {e}")
            raise httpx.ConnectError(f"[无法连接到] DeepSeek API: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"[调用] DeepSeek API [超时]: {e}")
            raise httpx.TimeoutException(f"[调用] DeepSeek API [超时]: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek API HTTP [错误]: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"DeepSeek API error {e.response.status_code}: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"[DeepSeek API [请求失败]: {e}")
            raise RuntimeError(f"DeepSeek API request failed: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"[解析] DeepSeek [响应失败]: {e}")
            raise RuntimeError(f"Failed to parse DeepSeek response: {e}")

    async def close(self):
        """[关闭] HTTP [客户端]"""
        await self.client.aclose()


def get_llm_client() -> LLMClient:
    """[获取] LLM [客户端实例] - [默认使用] DeepSeek Reasoner"""
    import os

    return LLMClient(
        model=os.getenv("LLM_MODEL", "deepseek-reasoner"),
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )


def generate_task_id() -> str:
    """[生成任务]ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"task_{timestamp}_{unique_id}"


def generate_agent_id() -> str:
    """[生成] Agent ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"agent_{timestamp}_{unique_id}"


def format_duration(seconds: int) -> str:
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


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """[截断字符串]"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """[安全的] JSON [序列化]"""
    import json

    def default_serializer(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "dict"):
            return o.dict()
        if hasattr(o, "model_dump"):
            return o.model_dump()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return json.dumps(obj, default=default_serializer, ensure_ascii=False, **kwargs)


def async_retry(
    max_attempts: int = 3,
    exceptions: tuple = (Exception,),
    min_wait: int = 1,
    max_wait: int = 10,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """[异步函数重试装饰器]"""
    return retry(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        reraise=True,
    )


async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    timeout_result: T,
) -> T:
    """[带超时的协程执行]"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return timeout_result


class ProgressBar:
    """[简单的进度条实现]"""

    def __init__(self, total: int, width: int = 40):
        self.total = total
        self.width = width
        self.current = 0

    def update(self, current: int) -> str:
        """[更新进度并返回进度条字符串]"""
        self.current = min(current, self.total)
        percentage = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percentage)
        bar = "[█]" * filled + "[░]" * (self.width - filled)
        return f"[{bar}] {percentage*100:.1f}% ({self.current}/{self.total})"

    def __str__(self) -> str:
        return self.update(self.current)
