"""
股票相关数据模型
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Date, Boolean, BigInteger,
    Numeric, Index, UniqueConstraint, ForeignKey, JSON, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class StockBasics(Base, TimestampMixin):
    """股票基础信息表"""
    
    __tablename__ = "stock_basics"
    
    # 主键：股票代码
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    industry: Mapped[Optional[str]] = mapped_column(String(50), comment="所属行业")
    list_date: Mapped[Optional[date]] = mapped_column(Date, comment="上市日期")
    market: Mapped[str] = mapped_column(String(10), nullable=False, comment="市场(SH/SZ/BJ)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否活跃")
    
    # 关系
    daily_k_lines: Mapped[list["StockDailyK"]] = relationship(
        back_populates="stock", 
        cascade="all, delete-orphan"
    )
    indicators: Mapped[list["StockIndicators"]] = relationship(
        back_populates="stock",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_stock_basics_market", "market"),
        Index("idx_stock_basics_industry", "industry"),
    )


class StockDailyK(Base):
    """股票日K线行情表"""
    
    __tablename__ = "stock_daily_k"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 外键
    code: Mapped[str] = mapped_column(
        String(10), 
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 交易数据
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    open_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="开盘价")
    close_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="收盘价")
    high_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="最高价")
    low_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="最低价")
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="成交量(股)")
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="成交额(元)")
    adjust_type: Mapped[str] = mapped_column(
        String(10), 
        nullable=False, 
        default="none",
        comment="复权类型: none/qfq/hfq"
    )
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="涨跌幅%")
    turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="换手率%")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        comment="创建时间"
    )
    
    # 关系
    stock: Mapped["StockBasics"] = relationship(back_populates="daily_k_lines")

    __table_args__ = (
        # 联合唯一索引，确保数据幂等
        UniqueConstraint("code", "trade_date", "adjust_type", name="uq_daily_k_code_date_adjust"),
        Index("idx_daily_k_date", "trade_date"),
        Index("idx_daily_k_code_date", "code", "trade_date"),
    )


class StockIndicators(Base):
    """技术指标缓存表"""

    __tablename__ = "stock_indicators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    indicator_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="指标类型: MA/MACD/RSI/KDJ/BOLL"
    )
    indicator_data: Mapped[dict] = mapped_column(JSON, nullable=False, comment="指标值JSON")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # 关系
    stock: Mapped["StockBasics"] = relationship(back_populates="indicators")

    __table_args__ = (
        UniqueConstraint("code", "trade_date", "indicator_type", name="uq_indicators_unique"),
        Index("idx_indicators_code_date", "code", "trade_date"),
    )


class StockFundamentals(Base, TimestampMixin):
    """股票基本面数据表"""

    __tablename__ = "stock_fundamentals"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 股票代码
    code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 报告期
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="报告期"
    )

    # 估值指标
    pe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="市盈率(动态)")
    pe_ttm: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="市盈率(TTM)")
    pb: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="市净率")
    ps: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="市销率")
    total_market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="总市值(元)")
    circulating_market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="流通市值(元)")
    circulating_shares: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="流通股本(股)")

    # 盈利能力
    eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="每股收益(元)")
    eps_diluted: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="稀释每股收益(元)")
    net_profit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="销售净利率(%)")
    gross_profit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="毛利率(%)")
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="净资产收益率(%)")
    roa: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="总资产收益率(%)")

    # 成长性
    revenue_yoy: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="营业收入同比增长(%)")
    profit_yoy: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="净利润同比增长(%)")
    revenue_qoq: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="营业收入环比增长(%)")
    profit_qoq: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="净利润环比增长(%)")

    # 财务健康
    reserve_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="每股公积金(元)")
    retained_earnings_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="每股未分配利润(元)")
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="总资产(元)")
    total_liabilities: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="总负债(元)")

    # 经营指标
    operating_cash_flow_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="每股经营现金流(元)")
    debt_to_asset_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="资产负债率(%)")
    current_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="流动比率")
    quick_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="速动比率")

    # 数据来源
    data_source: Mapped[Optional[str]] = mapped_column(String(50), comment="数据来源")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="数据更新时间")

    __table_args__ = (
        UniqueConstraint("code", "end_date", name="uq_fundamentals_code_date"),
        Index("idx_fundamentals_code_date", "code", "end_date"),
        Index("idx_fundamentals_date", "end_date"),
    )


class StockCallAuction(Base, TimestampMixin):
    """股票集合竞价数据表"""

    __tablename__ = "stock_call_auction"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 股票代码
    code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="交易日期")

    # 集合竞价时段 (09:15:00, 09:20:00, 09:25:00)
    auction_time: Mapped[str] = mapped_column(String(8), nullable=False, comment="竞价时间(HH:MM:SS)")

    # 竞价数据
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="集合竞价价格")
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="集合竞价成交量(股)")
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), comment="集合竞价成交额(元)")
    buy_volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="买盘量(股)")
    sell_volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="卖盘量(股)")

    # 涨跌信息
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="涨跌幅(%)")
    change_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="涨跌额")

    # 委比和买卖盘
    bid_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="委比(%)")

    # 数据来源和更新时间
    data_source: Mapped[Optional[str]] = mapped_column(String(50), comment="数据来源")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="数据更新时间")

    __table_args__ = (
        UniqueConstraint("code", "trade_date", "auction_time", name="uq_call_auction_unique"),
        Index("idx_call_auction_code_date", "code", "trade_date"),
        Index("idx_call_auction_date", "trade_date"),
    )

