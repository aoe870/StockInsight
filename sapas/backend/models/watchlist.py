"""
自选股数据模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..models import Base


class WatchlistGroup(Base):
    """自选股分组表"""
    __tablename__ = "watchlist_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    items = relationship("WatchlistItem", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_watchlist_group_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<WatchlistGroup(id={self.id}, name={self.name})>"


class WatchlistItem(Base):
    """自选股项目表"""
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("watchlist_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON格式，存储该股票的预警配置
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    group = relationship("WatchlistGroup", back_populates="items")

    __table_args__ = (
        Index("idx_watchlist_item_group", "group_id"),
        Index("idx_watchlist_item_code", "stock_code"),
        Index("idx_watchlist_item_unique", "group_id", "stock_code", unique=True),
    )

    def __repr__(self) -> str:
        return f"<WatchlistItem(id={self.id}, code={self.stock_code}, group={self.group_id})>"
