"""
数据网关服务主入口
"""
import asyncio
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.gateway.manager import gateway_manager
from src.database import init_database, close_database
from src.api.routes import router
from src.api.admin_routes import admin_router
from src.services.scheduler_service import scheduler_service
from src.utils.logger import setup_logger

# 设置日志
setup_logger(
    log_level=settings.log_level,
    log_file=settings.log_file
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=" * 60)
    logger.info(f"Data Gateway Service v{settings.version} starting...")
    logger.info("=" * 60)

    # 初始化数据库
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # 初始化数据网关
    try:
        await gateway_manager.initialize()
        logger.info("Data gateway initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize data gateway: {e}")
        raise

    # 启动定时调度器
    try:
        scheduler_service.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

    logger.info(f"Server running on http://{settings.host}:{settings.port}")
    logger.info(f"API docs: http://{settings.host}:{settings.port}/docs")
    logger.info("")

    yield

    # 关闭时
    logger.info("Data Gateway Service shutting down...")
    scheduler_service.stop()
    await close_database()


# 创建应用
app = FastAPI(
    title="Data Gateway Service",
    description="""
## 数据网关服务

统一的数据接口服务，支持多市场数据获取。

### 支持的市场
- **A股** (cn_a): 实时行情 + K线 + 基本面
- **港股** (hk): 实时行情 + K线
- **美股** (us): 实时行情 + K线
- **期货** (futures): 贵金属期货数据
- **经济指标** (economic): 宏观经济数据

### 数据源
- 实时数据: AKShare
- 历史数据: BaoStock

### 调用方式
- HTTP API (REST/JSON)
- Redis 消息队列 (实时推送)

### API 文档
- Swagger UI: `/docs`
- ReDoc: `/redoc`
    """,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """请求日志"""
    import time
    start_time = time.time()

    # 记录请求
    path = request.url.path
    if path not in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        logger.info(f"[{request.method}] {path}")

    # 处理请求
    response = await call_next(request)

    # 记录响应
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}"

    if path not in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
        logger.info(f"[{request.method}] {path} - {response.status_code} ({process_time:.2f}ms)")

    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": -1,
            "message": "Internal server error",
            "detail": str(exc) if settings.debug else None
        }
    )


# 注册路由
app.include_router(router, tags=["api"])
app.include_router(admin_router, tags=["admin"])


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """服务信息"""
    return {
        "service": "Data Gateway Service",
        "version": settings.version,
        "status": "running",
        "markets": {
            "cn_a": "A股",
            "hk": "港股",
            "us": "美股",
            "futures": "期货",
            "economic": "经济指标"
        },
        "endpoints": {
            "quote": "/api/v1/quote",
            "kline": "/api/v1/kline",
            "fundamentals": "/api/v1/fundamentals",
            "health": "/health",
            "admin": {
                "sync_create": "/api/v1/admin/sync/create",
                "sync_status": "/api/v1/admin/sync/status/{task_id}",
                "sync_active": "/api/v1/admin/sync/active",
                "sync_quick": "/api/v1/admin/sync/quick",
                "stock_list": "/api/v1/admin/stocks/list",
                "sync_stats": "/api/v1/admin/stats"
            }
        }
    }


# 开发环境启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
