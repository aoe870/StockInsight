"""
通用 Pydantic 数据模式
"""

from typing import Generic, TypeVar, Optional, List, Any

from pydantic import BaseModel, Field


T = TypeVar("T")


class ResponseBase(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "ok"


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页条数")
    items: List[T] = Field(..., description="数据列表")
    
    @property
    def total_pages(self) -> int:
        """总页数"""
        return (self.total + self.page_size - 1) // self.page_size


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")
    
    @property
    def offset(self) -> int:
        """偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """限制数量"""
        return self.page_size


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    database: str = "connected"

