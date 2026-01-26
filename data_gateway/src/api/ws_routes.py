"""
WebSocket 路由
提供实时数据推送接口
"""
import logging
from typing import List, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from .websocket import manager

logger = logging.getLogger(__name__)

ws_router = APIRouter(prefix="/ws", tags=["websocket"])


# ============== 请求/响应模型 ==============

class SubscribeRequest(BaseModel):
    """订阅请求"""
    action: str = "subscribe"  # subscribe/unsubscribe
    symbols: Optional[List[str]] = None
    market: Optional[str] = None


class WSSubscription(BaseModel):
    """客户端订阅信息"""
    client_id: str
    symbols: List[str] = []
    markets: List[str] = []


# ============== WebSocket 接口 ==============

@ws_router.websocket("/quote")
async def websocket_quote(websocket: WebSocket):
    """
    实时行情推送

    **连接方式**:
    ```
    ws = new WebSocket("ws://localhost:8001/ws/quote")
    ```

    **订阅消息格式** (发送到服务端):
    ```json
    {
      "action": "subscribe",
      "symbols": ["000001", "600000"],
      "market": "cn_a"
    }
    ```

    **推送消息格式** (服务端推送):
    ```json
    {
      "type": "quote",
      "symbol": "000001",
      "name": "平安银行",
      "price": 11.23,
      "open": 11.20,
      "high": 11.30,
      "low": 11.15,
      "volume": 12345678,
      "amount": 138765432.1,
      "change": 0.05,
      "change_pct": 0.45,
      "timestamp": "2026-01-26 10:30:00"
    }
    ```
    """
    await websocket.accept()

    client_id = await manager.connect(websocket)
    logger.info(f"WebSocket client connected: {client_id}")

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = SubscribeRequest.model_validate_json(data)

                if message.action == "subscribe":
                    # 订阅
                    if message.symbols:
                        symbols = set(message.symbols)
                        market = message.market or "cn_a"
                        await manager.subscribe_symbols(client_id, symbols, market)

                        # 发送订阅确认
                        await websocket.send_text({
                            "type": "subscription_confirmed",
                            "client_id": client_id,
                            "symbols": message.symbols,
                            "market": market,
                            "timestamp": None
                        })

                    elif message.market:
                        await manager.subscribe_market(client_id, message.market)

                        await websocket.send_text({
                            "type": "subscription_confirmed",
                            "client_id": client_id,
                            "market": message.market,
                            "timestamp": None
                        })

                elif message.action == "unsubscribe":
                    # 取消订阅 - 断开连接处理
                    manager.disconnect(client_id)
                    await websocket.close()
                    break

                elif message.action == "ping":
                    # 心跳
                    await websocket.send_text({
                        "type": "pong",
                        "timestamp": None
                    })

            except Exception as e:
                logger.error(f"Failed to parse message: {e}")
                await websocket.send_text({
                    "type": "error",
                    "message": f"Invalid message: {str(e)}",
                    "timestamp": None
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(client_id)


@ws_router.websocket("/market/{market}")
async def websocket_market(websocket: WebSocket, market: str):
    """
    按市场订阅实时行情

    **连接方式**:
    ```
    ws = new WebSocket("ws://localhost:8001/ws/market/cn_a")
    ```

    **参数**:
    - `market`: 市场代码 (cn_a, hk, us, futures)
    """
    if market not in ["cn_a", "hk", "us", "futures", "economic"]:
        await websocket.close(code=4000, reason="Invalid market")
        return

    await websocket.accept()
    client_id = await manager.connect(websocket)
    await manager.subscribe_market(client_id, market)

    logger.info(f"WebSocket client {client_id} subscribed to market {market}")

    # 发送订阅确认
    await websocket.send_text({
        "type": "subscription_confirmed",
        "client_id": client_id,
        "market": market,
        "timestamp": None
    })

    try:
        while True:
            # 保持连接，等待心跳或断开
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(client_id)


@ws_router.websocket("/symbols")
async def websocket_symbols(
    websocket: WebSocket,
    symbols: str = Query(..., description="股票代码，逗号分隔")
):
    """
    按股票列表订阅实时行情

    **连接方式**:
    ```
    ws = new WebSocket("ws://localhost:8001/ws/symbols?symbols=000001,600000")
    ```
    """
    await websocket.accept()
    client_id = await manager.connect(websocket)

    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    await manager.subscribe_symbols(client_id, set(symbol_list))

    logger.info(f"WebSocket client {client_id} subscribed to {len(symbol_list)} symbols")

    # 发送订阅确认
    await websocket.send_text({
        "type": "subscription_confirmed",
        "client_id": client_id,
        "symbols": symbol_list,
        "timestamp": None
    })

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(client_id)


# ============== 管理接口 ==============

@ws_router.get("/stats")
async def get_ws_stats():
    """获取 WebSocket 连接统计"""
    return {
        "code": 0,
        "message": "success",
        "data": manager.get_stats()
    }


@ws_router.get("/test")
async def websocket_test():
    """
    WebSocket 测试页面

    返回一个简单的 HTML 页面用于测试 WebSocket 连接
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket 实时行情测试</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .input-group { margin-bottom: 20px; }
            input, button { padding: 8px; margin-right: 10px; }
            #messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
            .message { padding: 5px; margin-bottom: 5px; border-bottom: 1px solid #eee; }
            .quote { color: #2ecc71; }
            .error { color: #e74c3c; }
            .info { color: #3498db; }
            .status { padding: 10px; margin-bottom: 20px; background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket 实时行情测试</h1>

            <div class="status">
                <strong>状态:</strong> <span id="status">未连接</span>
            </div>

            <div class="input-group">
                <input type="text" id="wsUrl" value="ws://localhost:8001/ws/quote" placeholder="WebSocket URL">
                <button onclick="connect()">连接</button>
                <button onclick="disconnect()">断开</button>
            </div>

            <div class="input-group">
                <input type="text" id="symbols" value="000001,600000" placeholder="股票代码，逗号分隔">
                <button onclick="subscribe()">订阅</button>
            </div>

            <div class="input-group">
                <button onclick="sendPing()">发送心跳</button>
                <button onclick="clearMessages()">清空消息</button>
            </div>

            <h3>消息:</h3>
            <div id="messages"></div>
        </div>

        <script>
            let ws = null;
            let clientId = null;

            function connect() {
                const url = document.getElementById('wsUrl').value;
                ws = new WebSocket(url);

                ws.onopen = function() {
                    document.getElementById('status').textContent = '已连接';
                    document.getElementById('status').style.color = '#2ecc71';
                    addMessage('info', 'WebSocket 连接成功');
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'quote') {
                        addMessage('quote', JSON.stringify(data, null, 2));
                    } else if (data.type === 'subscription_confirmed') {
                        clientId = data.client_id;
                        addMessage('info', '订阅确认: ' + data.symbols?.join(', ') || data.market);
                    } else if (data.type === 'pong') {
                        addMessage('info', '收到心跳响应');
                    } else {
                        addMessage('info', JSON.stringify(data, null, 2));
                    }
                };

                ws.onerror = function(error) {
                    document.getElementById('status').textContent = '连接错误';
                    document.getElementById('status').style.color = '#e74c3c';
                    addMessage('error', '连接错误: ' + error);
                };

                ws.onclose = function() {
                    document.getElementById('status').textContent = '已断开';
                    document.getElementById('status').style.color = '#e74c3c';
                    addMessage('info', 'WebSocket 连接关闭');
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }

            function subscribe() {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('请先连接 WebSocket');
                    return;
                }

                const symbols = document.getElementById('symbols').value;
                const message = {
                    action: 'subscribe',
                    symbols: symbols.split(',').map(s => s.trim()),
                    market: 'cn_a'
                };

                ws.send(JSON.stringify(message));
                addMessage('info', '发送订阅请求: ' + symbols);
            }

            function sendPing() {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('请先连接 WebSocket');
                    return;
                }

                ws.send(JSON.stringify({ action: 'ping' }));
                addMessage('info', '发送心跳');
            }

            function clearMessages() {
                document.getElementById('messages').innerHTML = '';
            }

            function addMessage(type, text) {
                const div = document.createElement('div');
                div.className = 'message ' + type;
                div.textContent = text;
                const messages = document.getElementById('messages');
                messages.insertBefore(div, messages.firstChild);
            }
        </script>
    </body>
    </html>
    """
