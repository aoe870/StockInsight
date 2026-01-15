"""
订阅相关数据模型
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Boolean, BigInteger, ForeignKey, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.alert import AlertRule


class Subscription(Base):
    """用户告警订阅表"""
    
    __tablename__ = "subscriptions"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 外键
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    rule_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 通知配置
    channel: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        comment="通知渠道: console/email/webhook/wechat"
    )
    channel_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        comment="渠道特定配置"
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, comment="创建时间")
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    rule: Mapped["AlertRule"] = relationship(back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint("user_id", "rule_id", "channel", name="uq_subscription_user_rule_channel"),
        Index("idx_subscriptions_user", "user_id"),
        Index("idx_subscriptions_rule", "rule_id"),
    )

