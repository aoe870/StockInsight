"""
用户相关数据模型
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, BigInteger, Text, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """用户表"""

    __tablename__ = "users"

    # 主键
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # 用户信息
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="用户名"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        comment="邮箱"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="昵称"
    )
    avatar: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="头像URL"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        comment="角色: admin/user"
    )

    # 偏好设置
    notify_channel: Mapped[str] = mapped_column(
        String(20),
        default="console",
        comment="默认通知渠道"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否激活"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        comment="最后登录时间"
    )
    
    # 关系
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class WatchlistItem(Base):
    """自选股表"""
    
    __tablename__ = "watchlist_items"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 外键
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    stock_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basics.code", ondelete="CASCADE"),
        nullable=False
    )
    
    # 用户数据
    note: Mapped[Optional[str]] = mapped_column(Text, comment="用户备注")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序顺序")
    added_at: Mapped[datetime] = mapped_column(default=datetime.now, comment="添加时间")
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="watchlist_items")
    stock: Mapped["StockBasics"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "stock_code", name="uq_watchlist_user_stock"),
        Index("idx_watchlist_user", "user_id", "sort_order"),
    )


# 避免循环导入
from src.models.subscription import Subscription
from src.models.stock import StockBasics

