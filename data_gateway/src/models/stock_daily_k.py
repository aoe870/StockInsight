"""
股票每日K线数据模型
每天一条记录（不聚合）
"""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Integer, Float, Numeric, DateTime, Index, UniqueConstraint

from ..database import Base


class StockDailyK(Base):
    """
    股票每日K线数据表

    每天一条记录，不聚合，类似 SAPAS 的 stock_daily_k 表
    """
    __tablename__ = "dg_stock_daily_k"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, comment="交易日期")
    open_price = Column(Float, nullable=True, comment="开盘价")
    close_price = Column(Float, nullable=True, comment="收盘价")
    high_price = Column(Float, nullable=True, comment="最高价")
    low_price = Column(Float, nullable=True, comment="最低价")
    volume = Column(BigInteger, nullable=True, comment="成交量（股）")
    amount = Column(Float, nullable=True, comment="成交额（元）")
    change_pct = Column(Float, nullable=True, comment="涨跌幅(%)")
    turnover = Column(Float, nullable=True, comment="换手率(%)")
    market_code = Column(String(20), nullable=False, default="cn_a", comment="市场代码")
    source_code = Column(String(50), comment="数据来源")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', name='uk_stock_daily_k_code_date'),
        Index('idx_stock_daily_k_code', 'code'),
        Index('idx_stock_daily_k_date', 'trade_date'),
        Index('idx_stock_daily_k_market', 'market_code'),
    )
