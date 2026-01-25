"""
K线数据缓存模型
"""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, JSON, DateTime, Index

from ..database import Base


class CachedKline(Base):
    """
    K线数据缓存表

    对应数据库表: dg_cache_kline
    """
    __tablename__ = "dg_cache_kline"

    cache_id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol_code = Column(String(20), nullable=False, comment="股票代码")
    market_code = Column(String(20), nullable=False, comment="市场代码 (cn_a, hk, us)")
    period_type = Column(String(20), nullable=False, comment="周期类型 (daily, weekly, monthly, 1m, 5m, etc)")
    kline_data = Column("kline_data", JSON, nullable=False, comment="K线数据 (JSON格式)")
    source_code = Column(String(50), comment="数据来源 (baostock, akshare, miana)")
    date_range = Column("date_range", JSON, comment="日期范围 {start, end}")
    created_at_ts = Column("created_at_ts", DateTime, default=datetime.utcnow, comment="创建时间")
    expire_at_ts = Column("expire_at_ts", DateTime, nullable=False, comment="过期时间")

    __table_args__ = (
        Index('idx_dg_cache_kline_symbol', 'symbol_code', 'market_code', 'period_type'),
        Index('idx_dg_cache_kline_expire', 'expire_at_ts'),
    )
