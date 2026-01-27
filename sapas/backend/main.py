"""
SAPAS 主程序入口
"""
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from api import api_router
from core.database import init_db, get_db_session
from core.websocket import websocket_manager

settings = get_settings()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="股票分析与自动化交易平台",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 包含所有路由
app.include_router(api_router)

# 静态文件（前端构建后）
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@asynccontextmanager
async def get_request_user(request: Request):
    """获取请求中的用户信息"""
    from .core.auth import AuthService

    authorization = request.headers.get("authorization")
    user_id = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            payload = AuthService.decode_token(token)
            user_id = int(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            logger.warning(f"Invalid token in request")

    yield user_id


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.error(f"HTTP exception: {exc.detail}")
    return {
        "code": exc.status_code,
        "message": exc.detail,
        "timestamp": None
    }


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.exception(f"Unhandled exception: {exc}")
    return {
        "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "message": "服务器内部错误",
        "detail": str(exc) if settings.DEBUG else "请稍后重试",
        "timestamp": None
    }


# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时行情推送"""
    # 从查询参数获取用户ID（简化版）
    user_id = 1  # TODO: 从认证上下文获取

    await websocket_manager.connect(websocket, user_id)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "subscribe":
                symbols = set(data.get("symbols", []))
                await websocket_manager.subscribe(user_id, symbols)
                logger.info(f"User {user_id} subscribed to {len(symbols)} stocks")

            elif action == "unsubscribe":
                symbols = set(data.get("symbols", []))
                await websocket_manager.unsubscribe(user_id, symbols)
                logger.info(f"User {user_id} unsubscribed from {len(symbols)} stocks")

            elif action == "ping":
                # 心跳响应
                await websocket.send_json({"action": "pong"})

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    from .core.data_gateway import data_gateway
    try:
        # 测试数据网关连接
        await data_gateway.get_quote("cn_a", ["600519"])
        return {
            "status": "healthy",
            "version": "1.0.0",
            "data_gateway": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "data_gateway": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    # 初始化数据库
    import asyncio
    asyncio.run(init_db())

    logger.info(f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}")
    logger.info(f"Data Gateway: {settings.DATA_GATEWAY_URL}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Redis: {settings.REDIS_URL}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
