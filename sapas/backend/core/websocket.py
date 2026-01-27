"""
WebSocket 管理器 - 实时行情推送
"""
import json
import logging
from typing import Set, Dict, Callable, Any
from fastapi import WebSocket, WebSocketDisconnect

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活跃连接
        self.active_connections: Dict[int, WebSocket] = {}
        # 用户订阅的股票
        self.user_subscriptions: Dict[int, Set[str]] = {}
        # 股票到订阅用户的映射
        self.stock_subscribers: Dict[str, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """新连接"""
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, user_id: int):
        """断开连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def subscribe(self, user_id: int, symbols: Set[str]):
        """
        用户订阅股票

        参数:
            user_id: 用户ID
            symbols: 股票代码集合
        """
        self.user_subscriptions[user_id] = symbols
        for symbol in symbols:
            if symbol not in self.stock_subscribers:
                self.stock_subscribers[symbol] = set()
            self.stock_subscribers[symbol].add(user_id)
        logger.info(f"User {user_id} subscribed to {len(symbols)} stocks")

    async def unsubscribe(self, user_id: int, symbols: Set[str]):
        """
        用户取消订阅股票

        参数:
            user_id: 用户ID
            symbols: 要取消订阅的股票代码集合
        """
        if user_id not in self.user_subscriptions:
            return

        for symbol in symbols:
            if symbol in self.stock_subscribers:
                self.stock_subscribers[symbol].discard(user_id)

        # 清理空股票
        for symbol in list(self.stock_subscribers.keys()):
            if not self.stock_subscribers[symbol]:
                del self.stock_subscribers[symbol]

        logger.info(f"User {user_id} unsubscribed from {len(symbols)} stocks")

    async def broadcast_quote(self, symbol: str, quote_data: Dict[str, Any]):
        """
        向订阅了某股票的所有用户广播行情

        参数:
            symbol: 股票代码
            quote_data: 行情数据
        """
        if symbol not in self.stock_subscribers:
            return

        users = self.stock_subscribers[symbol]
        disconnected_users = []

        for user_id in users:
            if user_id not in self.active_connections:
                disconnected_users.append(user_id)
                continue

            try:
                ws = self.active_connections[user_id]
                await ws.send_json({
                    "type": "quote",
                    "symbol": symbol,
                    "data": quote_data
                })
            except Exception as e:
                logger.error(f"Failed to send quote to user {user_id}: {e}")

        # 清理断开连接的用户
        for user_id in disconnected_users:
            self.stock_subscribers[symbol].discard(user_id)

    async def send_personal_message(self, user_id: int, message_type: str, data: Dict[str, Any]):
        """
        向指定用户发送消息

        参数:
            user_id: 用户ID
            message_type: 消息类型 (alert, backtest, etc)
            data: 消息数据
        """
        if user_id not in self.active_connections:
            return

        try:
            ws = self.active_connections[user_id]
            await ws.send_json({
                "type": message_type,
                "data": data
            })
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")

    async def get_connection_stats(self) -> Dict[str, int]:
        """获取连接统计"""
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(symbols) for symbols in self.user_subscriptions.values()),
            "unique_stocks": len(self.stock_subscribers),
            "total_users": len(self.user_subscriptions)
        }


# 单例实例
websocket_manager = WebSocketManager()
