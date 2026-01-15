"""
SQLAlchemy 基类模型
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    
    # 类型注解映射
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    def to_dict(self) -> dict[str, Any]:
        """将模型转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """模型的字符串表示"""
        class_name = self.__class__.__name__
        attrs = ", ".join(
            f"{col.name}={getattr(self, col.name)!r}"
            for col in self.__table__.columns
            if col.primary_key
        )
        return f"<{class_name}({attrs})>"


class TimestampMixin:
    """时间戳混入类"""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

