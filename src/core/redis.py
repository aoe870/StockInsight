"""
Redis 连接管理模块
提供 Redis 连接池和 Pub/Sub 功能
"""

import asyncio
import json
from typing import Optional, Callable, Awaitable, Dict, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from src.config import settings
from src.utils.logger import logger


class RedisManager:
    """Redis 连接管理器"""
    
    _instance: Optional['RedisManager'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def url(self) -> str:
        """Redis 连接 URL"""
        host = getattr(settings, 'redis_host', 'localhost')
        port = getattr(settings, 'redis_port', 6379)
        db = getattr(settings, 'redis_db', 0)
        password = getattr(settings, 'redis_password', None)
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"
    
    async def connect(self) -> None:
        """建立 Redis 连接"""
        if self._pool is not None:
            return
        
        try:
            self._pool = ConnectionPool.from_url(
                self.url,
                max_connections=20,
                decode_responses=True,
            )
            self._client = Redis(connection_pool=self._pool)
            # 测试连接
            await self._client.ping()
            logger.info(f"Redis 连接成功: {self.url.split('@')[-1]}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            self._pool = None
            self._client = None
            raise
    
    async def disconnect(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis 连接已关闭")
    
    @property
    def client(self) -> Redis:
        """获取 Redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis 未连接，请先调用 connect()")
        return self._client
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        发布消息到频道
        
        Args:
            channel: 频道名称
            message: 消息内容（会被序列化为 JSON）
        
        Returns:
            接收到消息的订阅者数量
        """
        data = json.dumps(message, ensure_ascii=False, default=str)
        return await self.client.publish(channel, data)
    
    async def subscribe(
        self,
        *channels: str,
        callback: Callable[[str, Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        订阅频道
        
        Args:
            channels: 要订阅的频道列表
            callback: 收到消息时的回调函数 (channel, message) -> None
        """
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        logger.info(f"已订阅频道: {channels}")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    try:
                        data = json.loads(message['data'])
                    except json.JSONDecodeError:
                        data = message['data']
                    await callback(channel, data)
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
    
    async def set_cache(self, key: str, value: Any, expire: int = 60) -> None:
        """设置缓存"""
        data = json.dumps(value, ensure_ascii=False, default=str)
        await self.client.set(key, data, ex=expire)
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        data = await self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None


# 全局实例
redis_manager = RedisManager()


async def get_redis() -> Redis:
    """获取 Redis 客户端（用于依赖注入）"""
    return redis_manager.client

