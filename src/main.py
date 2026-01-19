"""
SAPAS 应用入口
Stock Analysis and Processing Automated Service
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.config import settings
from src.core.database import DatabaseManager
from src.api.router import api_router
from src.api.websocket import router as ws_router, ws_manager
from src.utils.logger import logger
from src.schemas.common import HealthResponse, ErrorResponse
from src.services.auto_sync import auto_sync_service
from src.services.scheduler import scheduler_service
from src.core.redis import redis_manager
from src.services.quote_push import quote_push_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"SAPAS v{__version__} 启动中...")
    logger.info(f"环境: {settings.app_env}, 调试模式: {settings.debug}")

    # 初始化数据库连接
    DatabaseManager.get_engine()
    logger.info("数据库连接池已初始化")

    # 初始化 Redis 连接
    try:
        await redis_manager.connect()
        logger.info("Redis 连接已建立")

        # 注意：行情推送服务暂时禁用
        # AKShare 的 py_mini_racer (V8 引擎) 在多线程环境下会崩溃
        # 等待对接更稳定的 Level2 数据源后再启用
        # await quote_push_service.start()
        # logger.info("行情推送服务已启动")

        # 启动 WebSocket 管理器
        await ws_manager.start()
        logger.info("WebSocket 管理器已启动")
    except Exception as e:
        logger.warning(f"Redis 连接失败，实时行情功能不可用: {e}")

    # 启动自动数据同步（后台任务，不阻塞启动）
    asyncio.create_task(auto_sync_service.check_and_sync_on_startup())

    # 启动定时任务调度器
    scheduler_service.start()
    logger.info("定时任务调度器已启动")

    yield

    # 关闭时
    logger.info("SAPAS 正在关闭...")
    scheduler_service.shutdown()

    # 关闭行情推送和 Redis
    try:
        await ws_manager.stop()
        await quote_push_service.stop()
        await redis_manager.disconnect()
    except Exception:
        pass

    await DatabaseManager.close()
    logger.info("SAPAS 已关闭")


# 创建应用
app = FastAPI(
    title="SAPAS - 股票数据获取与分析服务",
    description="""
## 功能概述

SAPAS (Stock Analysis and Processing Automated Service) 是一套自动化股票数据处理系统，提供：

- 📊 **数据同步**: 从 AKShare 获取 A 股行情数据
- 📈 **技术分析**: MA、MACD、RSI、KDJ、布林带等指标计算
- ⭐ **自选股管理**: Web 界面管理自选股列表
- 🔔 **告警订阅**: 基于发布订阅模式的多渠道告警通知

## API 文档

- Swagger UI: `/docs`
- ReDoc: `/redoc`
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message="服务器内部错误",
            detail=str(exc) if settings.debug else None
        ).model_dump()
    )


# 健康检查
@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        version=__version__,
        database="connected"
    )


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "name": "SAPAS",
        "version": __version__,
        "description": "股票数据获取与分析服务",
        "docs": "/docs",
    }


# 注册 API 路由
app.include_router(api_router)

# 注册 WebSocket 路由
app.include_router(ws_router, tags=["WebSocket"])


# 开发环境启动入口
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

