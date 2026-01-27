"""
数据模型包
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .user import User
from .watchlist import WatchlistGroup, WatchlistItem
from .alert import Alert, AlertHistory
from .backtest import BacktestRun, BacktestTrade
from .screener import ScreenerCondition

# 创建基类
Base = declarative_base()


async def get_db_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session() as session:
        yield session


__all__ = [
    "Base",
    "User",
    "WatchlistGroup",
    "WatchlistItem",
    "Alert",
    "AlertHistory",
    "BacktestRun",
    "BacktestTrade",
    "ScreenerCondition",
]
