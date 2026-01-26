"""
WebSocket 推送服务
订阅 Redis 中的实时行情，推送到 WebSocket 客户端
"""
import json
import asyncio
import logging
from typing import Set, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
except ImportError:
    redis = None

from ..config import settings
from ..api.websocket import manager

logger = logging.getLogger(__name__)


class WSPushService:
    """WebSocket 推送服务"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.PubSub] = None
        self._running = False
        self._tasks: Set[asyncio.Task] = set()

    async def initialize(self):
        """初始化 Redis 连接"""
        if not redis:
            logger.warning("Redis not installed, WebSocket push service disabled")
            return False

        try:
            # 创建连接池
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self._pubsub = self._redis.pubsub()

            # 订阅行情频道
            channels = [
                f"{settings.redis_quote_channel_prefix}:quote",  # 实时行情
                f"{settings.redis_quote_channel_prefix}:tick",   # 逐笔数据
            ]

            await self._pubsub.subscribe(*channels)
            logger.info(f"Subscribed to Redis channels: {channels}")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket push service: {e}")
            return False

    async def start(self):
        """启动推送服务"""
        if self._running:
            logger.warning("WebSocket push service already running")
            return

        success = await self.initialize()
        if not success:
            return

        self._running = True
        logger.info("WebSocket push service started")

        # 启动监听任务
        task = asyncio.create_task(self._listen_messages())
        self._tasks.add(task)

    async def stop(self):
        """停止推送服务"""
        if not self._running:
            return

        self._running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()

        # 取消订阅
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        logger.info("WebSocket push service stopped")

    async def _listen_messages(self):
        """监听 Redis 消息"""
        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_message(message)

        except asyncio.CancelledError:
            logger.info("WebSocket push listener cancelled")
        except Exception as e:
            logger.error(f"Error listening to Redis messages: {e}")

    async def _handle_message(self, message: dict):
        """处理收到的消息"""
        try:
            # 解析消息
            channel = message.get('channel', '')
            data_str = message.get('data', '{}')
            data = json.loads(data_str) if isinstance(data_str, str) else data_str

            # 根据频道类型处理
            if ':quote:' in channel or ':tick:' in channel:
                # 实时行情数据
                await self._push_quote_data(data)

            elif ':kline:' in channel:
                # K线数据
                await self._push_kline_data(data)

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _push_quote_data(self, data: dict):
        """推送行情数据"""
        symbol = data.get('symbol')

        if not symbol:
            return

        # 构造推送消息
        message = {
            "type": "quote",
            **data
        }

        # 推送给该股票的订阅者
        await manager.broadcast_to_symbol(symbol, message)

    async def _push_kline_data(self, data: dict):
        """推送K线数据"""
        symbol = data.get('symbol')

        if not symbol:
            return

        message = {
            "type": "kline",
            **data
        }

        await manager.broadcast_to_symbol(symbol, message)

    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "running": self._running,
            "redis_connected": self._redis is not None,
            "active_subscribers": len(manager.active_connections),
            "ws_stats": manager.get_stats()
        }


# 全局单例
ws_push_service = WSPushService()
