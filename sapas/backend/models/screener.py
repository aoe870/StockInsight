"""
选股数据模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..models import Base


class ScreenerCondition(Base):
    """选股条件表"""
    __tablename__ = "screener_conditions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON格式选股条件
    is_public: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)  # 是否公开
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 使用次数
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_screener_user", "user_id"),
        Index("idx_screener_public", "is_public"),
    )

    def __repr__(self) -> str:
        return f"<ScreenerCondition(id={self.id}, name={self.name})>"
