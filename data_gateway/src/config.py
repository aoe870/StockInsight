"""
数据网关服务配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """服务配置"""

    # 服务配置
    service_name: str = "data-gateway"
    version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8001

    # 数据库配置
    database_url: str = "postgresql+asyncpg://root:J7aXgk2BJUj=@localhost:5432/data_gateway"
    database_sync_url: str = "postgresql://root:J7aXgk2BJUj=@localhost:5432/data_gateway"

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    redis_message_queue: str = "data-gateway:queue"
    redis_quote_channel_prefix: str = "quote"

    # 缓存配置
    cache_ttl_realtime: int = 5   # 实时行情缓存时间(秒)
    cache_ttl_kline: int = 60     # K线缓存时间(秒)

    # 数据源配置
    akshare_enabled: bool = True
    baostock_enabled: bool = True
    miana_token: str = ""  # 缅A平台Token（可选，用于实时五档、资金流向等）

    # 限流配置
    rate_limit_per_minute: int = 120
    rate_limit_per_hour: int = 1000

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/data_gateway.log"

    # 支持的市场
    supported_markets: List[str] = [
        "cn_a",      # A股
        # "hk",        # 港股 - 已禁用
        # "us",        # 美股 - 已禁用
        # "futures",   # 期货 - 已禁用
        # "economic",  # 经济指标 - 已禁用
    ]

    model_config = SettingsConfigDict(
        env_file="../.env",  # Load from parent directory
        env_prefix="DG_",
        extra="ignore"  # Ignore extra environment variables
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
