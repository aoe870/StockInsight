"""
预警数据模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import Base


class AlertType(str, SQLEnum):
    """预警类型枚举"""
    PRICE = "price"           # 价格预警
    PCT_CHANGE = "pct_change" # 涨跌幅预警
    INDICATOR = "indicator"     # 技术指标预警
    MONEY_FLOW = "money_flow"   # 资金流向预警
    CUSTOM = "custom"          # 自定义公式预警


class AlertFrequency(str, SQLEnum):
    """预警频率枚举"""
    ONCE = "once"      # 单次触发
    DAILY = "daily"    # 每日触发
    EVERY_TIME = "every_time"  # 定时触发


class AlertStatus(str, SQLEnum):
    """预警状态枚举"""
    ACTIVE = "active"     # 启用
    DISABLED = "disabled" # 禁用
    PAUSED = "paused"     # 暂停


class Alert(Base):
    """预警规则表"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_code: Mapped[str] = mapped_column(String(20), nullable=True)  # None表示所有股票
    alert_type: Mapped[AlertType] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON格式
    frequency: Mapped[AlertFrequency] = mapped_column(String(20), default=AlertFrequency.ONCE, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(String(20), default=AlertStatus.ACTIVE, nullable=False, index=True)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    history = relationship("AlertHistory", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alert_user", "user_id"),
        Index("idx_alert_status", "status"),
        Index("idx_alert_type", "alert_type"),
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, name={self.name})>"


class AlertStatusEnum(str, SQLEnum):
    """预警历史状态"""
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class AlertHistory(Base):
    """预警历史表"""
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    trigger_value: Mapped[str] = mapped_column(Text, nullable=True)  # JSON格式
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AlertStatusEnum] = mapped_column(String(20), default=AlertStatusEnum.UNREAD, nullable=False, index=True)
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联
    alert = relationship("Alert", back_populates="history")

    __table_args__ = (
        Index("idx_alert_history_alert", "alert_id"),
        Index("idx_alert_history_time", "trigger_time"),
    )

    def __repr__(self) -> str:
        return f"<AlertHistory(id={self.id}, alert_id={self.alert_id}, time={self.trigger_time})>"
