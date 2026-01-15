"""
告警相关数据模型
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    String, Boolean, BigInteger, Text, Integer, 
    ForeignKey, Index, Date, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class AlertRule(Base, TimestampMixin):
    """告警规则表"""
    
    __tablename__ = "alert_rules"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 规则定义
    stock_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        comment="股票代码，NULL表示全局规则"
    )
    rule_type: Mapped[str] = mapped_column(
        String(30), 
        nullable=False,
        comment="规则类型"
    )
    rule_name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        comment="规则名称"
    )
    conditions: Mapped[dict] = mapped_column(
        JSON, 
        nullable=False,
        comment="触发条件配置"
    )
    
    # 状态
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, 
        default=60,
        comment="冷却时间(分钟)"
    )
    
    # 创建者
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # 关系
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    alert_history: Mapped[list["AlertHistory"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    stock: Mapped[Optional["StockBasics"]] = relationship()

    __table_args__ = (
        Index("idx_alert_rules_stock", "stock_code"),
        Index("idx_alert_rules_type", "rule_type"),
    )


class AlertHistory(Base):
    """告警历史记录表"""
    
    __tablename__ = "alert_history"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 外键
    rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 告警详情
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="股票代码")
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="告警类型")
    alert_data: Mapped[dict] = mapped_column(JSON, nullable=False, comment="告警详情")
    triggered_at: Mapped[datetime] = mapped_column(default=datetime.now, comment="触发时间")
    
    # 关系
    rule: Mapped["AlertRule"] = relationship(back_populates="alert_history")

    __table_args__ = (
        Index("idx_alert_history_rule", "rule_id"),
        Index("idx_alert_history_stock", "stock_code"),
        Index("idx_alert_history_time", "triggered_at"),
    )


class SyncLog(Base):
    """数据同步日志表"""
    
    __tablename__ = "sync_logs"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 同步信息
    sync_type: Mapped[str] = mapped_column(
        String(30), 
        nullable=False,
        comment="同步类型: STOCK_LIST/DAILY_K"
    )
    stock_code: Mapped[Optional[str]] = mapped_column(String(10), comment="股票代码")
    start_date: Mapped[Optional[date]] = mapped_column(Date, comment="同步起始日期")
    end_date: Mapped[Optional[date]] = mapped_column(Date, comment="同步结束日期")
    records_count: Mapped[Optional[int]] = mapped_column(Integer, comment="同步记录数")
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        comment="状态: RUNNING/SUCCESS/FAILED"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    
    # 时间
    started_at: Mapped[datetime] = mapped_column(default=datetime.now, comment="开始时间")
    finished_at: Mapped[Optional[datetime]] = mapped_column(comment="结束时间")

    __table_args__ = (
        Index("idx_sync_logs_type", "sync_type"),
        Index("idx_sync_logs_status", "status"),
        Index("idx_sync_logs_time", "started_at"),
    )


# 避免循环导入
from src.models.subscription import Subscription
from src.models.stock import StockBasics

