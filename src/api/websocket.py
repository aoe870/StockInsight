"""
WebSocket API 模块
提供实时行情数据推送，支持 Redis Pub/Sub
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.redis import redis_manager
from src.services.quote_push import QuoteChannel, quote_push_service
from src.utils.logger import logger

router = APIRouter()


class QuoteWebSocketManager:
    """
    行情 WebSocket 管理器
    负责管理客户端连接和消息分发
    """

    def __init__(self):
        # 指数行情订阅者
        self._index_clients: Set[WebSocket] = set()
        # 个股行情订阅者: code -> Set[WebSocket]
        self._stock_clients: Dict[str, Set[WebSocket]] = {}
        # 客户端订阅的股票: WebSocket -> Set[code]
        self._client_subscriptions: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._redis_listener_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动管理器"""
        # 启动 Redis 订阅监听
        self._redis_listener_task = asyncio.create_task(self._redis_listener())
        logger.info("WebSocket 管理器已启动")

    async def stop(self):
        """停止管理器"""
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket 管理器已停止")

    async def _redis_listener(self):
        """监听 Redis 消息并分发给客户端"""
        pubsub = redis_manager.client.pubsub()

        # 订阅指数频道
        await pubsub.subscribe(QuoteChannel.INDEX)
        # 使用模式订阅所有个股频道
        await pubsub.psubscribe(f"{QuoteChannel.STOCK_PREFIX}*")

        logger.info("开始监听 Redis 行情频道")

        try:
            async for message in pubsub.listen():
                if message['type'] in ('message', 'pmessage'):
                    channel = message.get('channel', message.get('pattern', ''))
                    try:
                        data = json.loads(message['data'])
                    except (json.JSONDecodeError, TypeError):
                        continue

                    # 分发消息
                    if channel == QuoteChannel.INDEX:
                        await self._broadcast_to_index_clients(data)
                    elif channel.startswith(QuoteChannel.STOCK_PREFIX):
                        code = channel.replace(QuoteChannel.STOCK_PREFIX, '')
                        await self._broadcast_to_stock_clients(code, data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe()
            await pubsub.punsubscribe()
            await pubsub.close()

    async def _broadcast_to_index_clients(self, data: dict):
        """广播指数行情给所有订阅者"""
        if not self._index_clients:
            return
        message = json.dumps(data, ensure_ascii=False)
        dead_clients = set()
        for client in self._index_clients.copy():
            try:
                await client.send_text(message)
            except Exception:
                dead_clients.add(client)
        for client in dead_clients:
            self._index_clients.discard(client)

    async def _broadcast_to_stock_clients(self, code: str, data: dict):
        """广播个股行情给订阅者"""
        clients = self._stock_clients.get(code, set())
        if not clients:
            return
        message = json.dumps(data, ensure_ascii=False)
        dead_clients = set()
        for client in clients.copy():
            try:
                await client.send_text(message)
            except Exception:
                dead_clients.add(client)
        for client in dead_clients:
            clients.discard(client)

    async def connect_index(self, websocket: WebSocket):
        """连接指数行情"""
        await websocket.accept()
        async with self._lock:
            self._index_clients.add(websocket)
        logger.info(f"指数行情客户端连接，当前: {len(self._index_clients)}")

    async def disconnect_index(self, websocket: WebSocket):
        """断开指数行情"""
        async with self._lock:
            self._index_clients.discard(websocket)
        logger.info(f"指数行情客户端断开，当前: {len(self._index_clients)}")

    async def connect_stock(self, websocket: WebSocket):
        """连接个股行情"""
        await websocket.accept()
        async with self._lock:
            self._client_subscriptions[websocket] = set()
        logger.info("个股行情客户端连接")

    async def disconnect_stock(self, websocket: WebSocket):
        """断开个股行情"""
        async with self._lock:
            # 取消该客户端的所有订阅
            codes = self._client_subscriptions.pop(websocket, set())
            for code in codes:
                if code in self._stock_clients:
                    self._stock_clients[code].discard(websocket)
                    if not self._stock_clients[code]:
                        del self._stock_clients[code]
                        # 通知推送服务取消订阅
                        await quote_push_service.unsubscribe_stock(code)
        logger.info("个股行情客户端断开")

    async def subscribe_stocks(self, websocket: WebSocket, codes: list):
        """订阅个股"""
        async with self._lock:
            for code in codes:
                if code not in self._stock_clients:
                    self._stock_clients[code] = set()
                    # 通知推送服务开始推送
                    await quote_push_service.subscribe_stock(code)
                self._stock_clients[code].add(websocket)
                self._client_subscriptions[websocket].add(code)
        logger.info(f"客户端订阅股票: {codes}")

    async def unsubscribe_stocks(self, websocket: WebSocket, codes: list):
        """取消订阅个股"""
        async with self._lock:
            for code in codes:
                if code in self._stock_clients:
                    self._stock_clients[code].discard(websocket)
                    if not self._stock_clients[code]:
                        del self._stock_clients[code]
                        await quote_push_service.unsubscribe_stock(code)
                if websocket in self._client_subscriptions:
                    self._client_subscriptions[websocket].discard(code)
        logger.info(f"客户端取消订阅: {codes}")


# 全局管理器
ws_manager = QuoteWebSocketManager()


@router.websocket("/ws/index")
async def websocket_index_quote(websocket: WebSocket):
    """
    指数实时行情 WebSocket 端点
    自动推送大盘指数数据
    """
    await ws_manager.connect_index(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        await ws_manager.disconnect_index(websocket)


@router.websocket("/ws/stock")
async def websocket_stock_quote(websocket: WebSocket):
    """
    个股实时行情 WebSocket 端点
    支持订阅/取消订阅机制

    客户端消息格式:
    - 订阅: {"action": "subscribe", "codes": ["600519", "000001"]}
    - 取消: {"action": "unsubscribe", "codes": ["600519"]}
    - 心跳: "ping"
    """
    await ws_manager.connect_stock(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
                continue

            try:
                msg = json.loads(data)
                action = msg.get("action")
                codes = msg.get("codes", [])

                if action == "subscribe" and codes:
                    await ws_manager.subscribe_stocks(websocket, codes)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "codes": codes
                    }))
                elif action == "unsubscribe" and codes:
                    await ws_manager.unsubscribe_stocks(websocket, codes)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "codes": codes
                    }))
            except json.JSONDecodeError:
                await websocket.send_text('{"type":"error","message":"Invalid JSON"}')
    except WebSocketDisconnect:
        await ws_manager.disconnect_stock(websocket)
