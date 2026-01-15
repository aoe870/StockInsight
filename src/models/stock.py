"""
股票相关数据模型
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Date, Boolean, BigInteger, 
    Numeric, Index, UniqueConstraint, ForeignKey, JSON
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

