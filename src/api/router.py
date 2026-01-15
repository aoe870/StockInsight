"""
API 路由汇总
"""

from fastapi import APIRouter

from src.api.auth import router as auth_router
from src.api.stocks import router as stocks_router
from src.api.watchlist import router as watchlist_router
from src.api.alerts import router as alerts_router
from src.api.subscriptions import router as subscriptions_router
from src.api.sync import router as sync_router
from src.api.index import router as index_router
from src.api.screener import router as screener_router


# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(auth_router)
api_router.include_router(stocks_router)
api_router.include_router(watchlist_router)
api_router.include_router(alerts_router)
api_router.include_router(subscriptions_router)
api_router.include_router(sync_router)
api_router.include_router(index_router)
api_router.include_router(screener_router)

