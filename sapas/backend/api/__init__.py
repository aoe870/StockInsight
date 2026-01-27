"""
API 路由入口
"""
from fastapi import APIRouter
from .auth import router as auth_router
from .watchlist import router as watchlist_router
from .alert import router as alert_router
from .backtest import router as backtest_router
from .screener import router as screener_router
from .stocks import router as stocks_router

# 创建主路由
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(auth_router)
api_router.include_router(watchlist_router)
api_router.include_router(alert_router)
api_router.include_router(backtest_router)
api_router.include_router(screener_router)
api_router.include_router(stocks_router)

# 导出路由
__all__ = ["api_router"]
