"""
通用数据模型
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional
from datetime import datetime


class ApiResponse(BaseModel):
    """API 响应基类"""
    code: int = Field(default=0, description="状态码，0表示成功")
    message: str = Field(default="success", description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(ApiResponse, Generic[T]):
    """分页响应"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
    data: List[T] = Field(description="数据列表")

    @classmethod
    def create(cls, data: List[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        """创建分页响应"""
        total_pages = (total + params.page_size - 1) // params.page_size
        return cls(
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            data=data
        )


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    detail: Optional[str] = Field(default=None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
