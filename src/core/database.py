"""
数据库连接模块
提供异步数据库连接池和会话管理
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from src.config import settings
from src.utils.logger import logger


class DatabaseManager:
    """数据库管理器"""
    
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """获取数据库引擎（单例）"""
        if cls._engine is None:
            cls._engine = create_async_engine(
                settings.database_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,  # 连接健康检查
                echo=False,  # 关闭SQL日志
            )
            logger.info(f"数据库引擎创建成功: {settings.database_url.split('@')[-1]}")
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂"""
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                bind=cls.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return cls._session_factory

    @classmethod
    async def close(cls):
        """关闭数据库连接"""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("数据库连接已关闭")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话上下文管理器
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    session_factory = DatabaseManager.get_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入用的数据库会话获取器
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = DatabaseManager.get_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


def create_test_engine() -> AsyncEngine:
    """创建测试用数据库引擎（不使用连接池）"""
    return create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=True,
    )


# 导出
__all__ = [
    "DatabaseManager",
    "get_db_session",
    "get_db",
    "create_test_engine",
]

