"""
WebSocket 实时数据推送服务
用于向客户端推送实时行情数据
"""
import json
import asyncio
import logging
from typing import Set, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活跃连接: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # 订阅关系: client_id -> Set[symbols]
        self.subscriptions: Dict[str, Set[str]] = {}

        # 符号订阅者: symbol -> Set[client_ids]
        self.symbol_subscribers: Dict[str, Set[str]] = {}

        # 市场订阅者: market -> Set[client_ids]
        self.market_subscribers: Dict[str, Set[str]] = {}

    def get_client_id(self, websocket: WebSocket) -> str:
        """生成客户端ID"""
        return f"client_{id(websocket)}_{datetime.now().timestamp()}"

    async def connect(self, websocket: WebSocket) -> str:
        """新连接"""
        client_id = self.get_client_id(websocket)
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        logger.info(f"WebSocket connected: {client_id}")
        return client_id

    def disconnect(self, client_id: str):
        """断开连接"""
        # 移除连接
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # 移除订阅
        if client_id in self.subscriptions:
            symbols = self.subscriptions[client_id]
            for symbol in symbols:
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
            del self.subscriptions[client_id]

        logger.info(f"WebSocket disconnected: {client_id}")

    async def subscribe_symbols(self, client_id: str, symbols: Set[str], market: str = "cn_a"):
        """订阅指定股票"""
        # 清理旧订阅
        if client_id in self.subscriptions:
            old_symbols = self.subscriptions[client_id]
            for symbol in old_symbols:
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)

        # 添加新订阅
        for symbol in symbols:
            if symbol not in self.symbol_subscribers:
                self.symbol_subscribers[symbol] = set()
            self.symbol_subscribers[symbol].add(client_id)

        self.subscriptions[client_id] = symbols
        logger.info(f"Client {client_id} subscribed to {len(symbols)} symbols")

    async def subscribe_market(self, client_id: str, market: str):
        """订阅整个市场"""
        if market not in self.market_subscribers:
            self.market_subscribers[market] = set()
        self.market_subscribers[market].add(client_id)
        logger.info(f"Client {client_id} subscribed to market {market}")

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """向指定股票的订阅者推送"""
        if symbol not in self.symbol_subscribers:
            return

        # 添加元数据
        message["symbol"] = symbol
        message["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = json.dumps(message, ensure_ascii=False)

        # 向所有订阅者发送
        disconnected = set()
        for client_id in self.symbol_subscribers[symbol]:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Send to {client_id} failed: {e}")
                    disconnected.add(client_id)

        # 清理断开的连接
        for cid in disconnected:
            self.disconnect(cid)

    async def broadcast_to_market(self, market: str, message: dict):
        """向指定市场的订阅者推送"""
        if market not in self.market_subscribers:
            return

        message["market"] = market
        message["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = json.dumps(message, ensure_ascii=False)

        disconnected = set()
        for client_id in self.market_subscribers[market]:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Send to {client_id} failed: {e}")
                    disconnected.add(client_id)

        for cid in disconnected:
            self.disconnect(cid)

    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            "total_connections": len(self.active_connections),
            "total_symbol_subscriptions": sum(len(subs) for subs in self.symbol_subscribers.values()),
            "total_market_subscriptions": sum(len(subs) for subs in self.market_subscribers.values()),
            "symbol_count": len(self.symbol_subscribers),
            "market_count": len(self.market_subscribers)
        }


# 全局连接管理器
manager = ConnectionManager()
