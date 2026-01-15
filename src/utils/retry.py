"""
重试与限流工具模块
"""

import asyncio
import time
from functools import wraps
from typing import Callable, TypeVar, ParamSpec
from collections.abc import Awaitable

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.config import settings
from src.utils.logger import logger

P = ParamSpec("P")
T = TypeVar("T")


def sync_retry(
    max_attempts: int | None = None,
    delay: float | None = None,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    同步函数重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 基础延迟时间(秒)
        exceptions: 需要重试的异常类型
    """
    max_attempts = max_attempts or settings.sync_retry_times
    delay = delay or settings.sync_retry_delay
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=delay, min=delay, max=delay * 10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )


def async_retry(
    max_attempts: int | None = None,
    delay: float | None = None,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    异步函数重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 基础延迟时间(秒)
        exceptions: 需要重试的异常类型
    """
    max_attempts = max_attempts or settings.sync_retry_times
    delay = delay or settings.sync_retry_delay
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=delay, min=delay, max=delay * 10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )


class RateLimiter:
    """
    请求限流器
    使用令牌桶算法控制请求频率
    """
    
    def __init__(self, rate: float | None = None):
        """
        Args:
            rate: 每秒允许的请求数
        """
        self.rate = rate or settings.sync_rate_limit
        self.tokens = self.rate
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取一个令牌，如果没有令牌则等待"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                logger.debug(f"限流等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1
    
    def acquire_sync(self) -> None:
        """同步版本的获取令牌"""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.rate
            logger.debug(f"限流等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1


def rate_limited(limiter: RateLimiter):
    """
    限流装饰器
    
    Usage:
        limiter = RateLimiter(rate=5)
        
        @rate_limited(limiter)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 全局限流器实例
global_rate_limiter = RateLimiter()

__all__ = [
    "sync_retry",
    "async_retry", 
    "RateLimiter",
    "rate_limited",
    "global_rate_limiter",
]

