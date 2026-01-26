"""
数据网关数据库连接管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .config import settings


class Base(DeclarativeBase):
    """数据网关模型基类"""
    pass


# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# 创建会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    用法:
        async with get_db_session() as session:
            # 执行数据库操作
            await session.commit()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """初始化数据库（创建表）"""
    from .models.kline import CachedKline
    from .models.sync_log import SyncLog
    from .models.stock_daily_k import StockDailyK
    from .models.money_flow import MoneyFlow
    from .models.realtime_quote import RealtimeQuote

    async with engine.begin() as conn:
        # 只在开发环境自动创建表（生产环境应该使用迁移）
        if settings.debug:
            await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """关闭数据库连接"""
    await engine.dispose()
