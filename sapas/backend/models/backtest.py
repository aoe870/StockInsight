"""
回测数据模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Date, Decimal, Integer, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import Base


class BacktestStatus(str, SQLEnum):
    """回测状态枚举"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeType(str, SQLEnum):
    """交易类型枚举"""
    BUY = "buy"
    SELL = "sell"


class BacktestRun(Base):
    """回测运行表"""
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON格式
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Decimal(15, 2), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Decimal(5, 4), default=0.0003, nullable=False)
    slippage: Mapped[float] = mapped_column(Decimal(5, 4), default=0.001, nullable=False)
    status: Mapped[BacktestStatus] = mapped_column(String(20), default=BacktestStatus.RUNNING, nullable=False, index=True)

    # 回测结果统计
    final_capital: Mapped[float | None] = mapped_column(Decimal(15, 2), nullable=True)
    total_return: Mapped[float | None] = mapped_column(Decimal(10, 4), nullable=True)
    total_return_pct: Mapped[float | None] = mapped_column(Decimal(10, 4), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Decimal(10, 4), nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Decimal(10, 4), nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Decimal(8, 4), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Decimal(5, 4), nullable=True)
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winning_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    losing_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_profit: Mapped[float | None] = mapped_column(Decimal(15, 4), nullable=True)
    avg_loss: Mapped[float | None] = mapped_column(Decimal(15, 4), nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Decimal(8, 4), nullable=True)  # 盈亏比

    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON格式详细结果
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联
    trades = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_backtest_user", "user_id"),
        Index("idx_backtest_status", "status"),
        Index("idx_backtest_date", "start_date"),
    )

    def __repr__(self) -> str:
        return f"<BacktestRun(id={self.id}, strategy={self.strategy_name}, status={self.status})>"


class BacktestTrade(Base):
    """回测交易记录表"""
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_type: Mapped[TradeType] = mapped_column(String(10), nullable=False)
    trade_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Decimal(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Decimal(15, 2), nullable=False)
    commission: Mapped[float] = mapped_column(Decimal(10, 2), default=0, nullable=False)
    profit: Mapped[float | None] = mapped_column(Decimal(15, 4), nullable=True)
    profit_pct: Mapped[float | None] = mapped_column(Decimal(10, 4), nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_backtest_trade_backtest", "backtest_id"),
        Index("idx_backtest_trade_time", "trade_time"),
    )

    def __repr__(self) -> str:
        return f"<BacktestTrade(id={self.id}, code={self.stock_code}, type={self.trade_type})>"
