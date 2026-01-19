"""
配置管理模块
使用 pydantic-settings 进行环境变量管理
"""

from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = Field(default="SAPAS", description="应用名称")
    app_env: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="密钥")

    # 数据库配置
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/sapas_db",
        description="异步数据库连接URL"
    )
    database_sync_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/sapas_db",
        description="同步数据库连接URL"
    )
    database_pool_size: int = Field(default=10, description="连接池大小")
    database_max_overflow: int = Field(default=20, description="最大溢出连接数")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="logs/sapas.log", description="日志文件路径")
    alert_log_file: str = Field(default="logs/alert_history.log", description="告警日志文件")

    # 数据同步配置
    sync_retry_times: int = Field(default=3, description="同步重试次数")
    sync_retry_delay: int = Field(default=5, description="重试延迟(秒)")
    sync_rate_limit: int = Field(default=5, description="每秒请求限制")

    # 告警配置
    alert_check_interval: int = Field(default=60, description="告警检查间隔(秒)")
    trading_start_am: str = Field(default="09:30", description="上午开盘时间")
    trading_end_am: str = Field(default="11:30", description="上午收盘时间")
    trading_start_pm: str = Field(default="13:00", description="下午开盘时间")
    trading_end_pm: str = Field(default="15:00", description="下午收盘时间")

    # Redis 配置
    redis_host: str = Field(default="localhost", description="Redis 主机")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_db: int = Field(default=0, description="Redis 数据库")
    redis_password: str = Field(default="", description="Redis 密码")

    # JWT 配置
    jwt_secret_key: str = Field(default="jwt-secret-key-change-in-production", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_expire_minutes: int = Field(default=1440, description="JWT过期时间(分钟)")

    # CORS 配置
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="允许的跨域来源"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """解析 CORS origins，支持字符串和列表"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例
    使用 lru_cache 确保只加载一次配置
    """
    return Settings()


# 导出便捷访问
settings = get_settings()

