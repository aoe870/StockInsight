"""
实时行情历史数据模型
用于存储实时行情快照历史数据，支持查询历史行情状态
"""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Float, DateTime, Index, UniqueConstraint, JSON

from ..database import Base


class RealtimeQuote(Base):
    """
    实时行情历史数据表

    存储实时行情的快照数据，用于历史查询和分析
    """
    __tablename__ = "dg_realtime_quote"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, comment="交易日期")
    trade_time = Column(DateTime, nullable=False, comment="交易时间")

    # 基础行情数据
    name = Column(String(50), nullable=True, comment="股票名称")
    price = Column(Float, nullable=True, comment="当前价格")
    open_price = Column(Float, nullable=True, comment="开盘价")
    high_price = Column(Float, nullable=True, comment="最高价")
    low_price = Column(Float, nullable=True, comment="最低价")
    volume = Column(BigInteger, nullable=True, comment="成交量")
    amount = Column(Float, nullable=True, comment="成交额")
    change = Column(Float, nullable=True, comment="涨跌额")
    change_pct = Column(Float, nullable=True, comment="涨跌幅")
    pre_close = Column(Float, nullable=True, comment="昨收价")

    # 买卖档位
    bid_volume = Column(Float, nullable=True, comment="买一量")
    ask_volume = Column(Float, nullable=True, comment="卖一量")
    buys = Column(JSON, nullable=True, comment="买盘档位 [[价, 量], ...]")
    sells = Column(JSON, nullable=True, comment="卖盘档位 [[价, 量], ...]")

    # 市场数据
    high_limit = Column(Float, nullable=True, comment="涨停价")
    low_limit = Column(Float, nullable=True, comment="跌停价")
    turnover = Column(Float, nullable=True, comment="换手率")
    amplitude = Column(Float, nullable=True, comment="振幅")
    committee = Column(Float, nullable=True, comment="委比")

    # 估值指标
    pe_ttm = Column(Float, nullable=True, comment="TTM市盈率")
    pe_dyn = Column(Float, nullable=True, comment="动态市盈率")
    pe_static = Column(Float, nullable=True, comment="静态市盈率")
    pb = Column(Float, nullable=True, comment="市净率")

    # 股本数据
    market_value = Column(Float, nullable=True, comment="总市值")
    circulation_value = Column(Float, nullable=True, comment="流通市值")
    circulation_shares = Column(Float, nullable=True, comment="流通股本")
    total_shares = Column(Float, nullable=True, comment="总股本")

    # 交易所信息
    country_code = Column(String(10), nullable=True, comment="国家/地区代码")
    exchange_code = Column(String(20), nullable=True, comment="交易所代码")

    market_code = Column(String(20), nullable=False, default="cn_a", comment="市场代码")
    source_code = Column(String(50), comment="数据来源 (miana, akshare, etc)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        UniqueConstraint('code', 'trade_time', 'market_code', name='uk_realtime_quote_code_time'),
        Index('idx_realtime_quote_code', 'code'),
        Index('idx_realtime_quote_date', 'trade_date'),
        Index('idx_realtime_quote_time', 'trade_time'),
        Index('idx_realtime_quote_market', 'market_code'),
        Index('idx_realtime_quote_change_pct', 'change_pct'),
        Index('idx_realtime_quote_amount', 'amount'),
    )
