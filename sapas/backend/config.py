"""
SAPAS 配置管理
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "SAPAS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "sapas-secret-key-change-in-production"

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8082

    # 数据网关配置
    DATA_GATEWAY_URL: str = "http://localhost:8001"

    # 数据库配置 (SAPAS 独立数据库)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/sapas_db"
    DATABASE_SYNC_URL: str = "postgresql://postgres:password@localhost:5432/sapas_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MESSAGE_QUEUE: str = "sapas:queue"

    # JWT 配置
    JWT_SECRET_KEY: str = "sapas-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24小时

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/sapas.log"

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000

    # 选股配置
    SCREENER_MAX_RESULTS: int = 1000

    # 预警配置
    ALERT_CHECK_INTERVAL: int = 60  # 秒
    ALERT_MAX_RULES_PER_USER: int = 50

    # 回测配置
    BACKTEST_MAX_TRADES: int = 10000
    BACKTEST_MAX_PERIODS: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
