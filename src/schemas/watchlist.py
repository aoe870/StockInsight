"""
自选股相关 Pydantic 数据模式
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class WatchlistItemBase(BaseModel):
    """自选股项基类"""
    stock_code: str = Field(..., description="股票代码")
    note: Optional[str] = Field(None, description="备注")


class WatchlistItemCreate(WatchlistItemBase):
    """创建自选股"""
    pass


class WatchlistItemUpdate(BaseModel):
    """更新自选股"""
    note: Optional[str] = Field(None, description="备注")
    sort_order: Optional[int] = Field(None, description="排序顺序")


class WatchlistItemResponse(WatchlistItemBase):
    """自选股响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: UUID
    stock_name: Optional[str] = Field(None, description="股票名称")
    sort_order: int = 0
    added_at: datetime


class WatchlistResponse(BaseModel):
    """自选股列表响应"""
    total: int
    items: List[WatchlistItemResponse]


class WatchlistBatchCreate(BaseModel):
    """批量添加自选股"""
    stock_codes: List[str] = Field(..., min_length=1, max_length=50, description="股票代码列表")


class WatchlistBatchResponse(BaseModel):
    """批量操作响应"""
    success_count: int
    failed_count: int
    failed_codes: List[str] = Field(default_factory=list)

