"""
自选股相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .common import ApiResponse


class WatchlistGroupCreate(BaseModel):
    """创建分组请求"""
    name: str = Field(..., min_length=1, max_length=50, description="分组名称")
    description: Optional[str] = Field(None, description="分组描述")
    icon: Optional[str] = Field(None, description="分组图标")


class WatchlistGroupUpdate(BaseModel):
    """更新分组请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None)
    icon: Optional[str] = Field(None)
    sort_order: Optional[int] = Field(None, ge=0)
    is_default: Optional[bool] = Field(None)


class WatchlistGroupResponse(BaseModel):
    """分组响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    sort_order: int
    is_default: bool
    created_at: datetime
    item_count: Optional[int] = 0

    class Config:
        from_attributes = True


class WatchlistItemCreate(BaseModel):
    """添加自选股请求"""
    stock_codes: List[str] = Field(..., min_items=1, max_items=100, description="股票代码列表")


class WatchlistItemUpdate(BaseModel):
    """更新自选股请求"""
    group_id: Optional[int] = Field(None, description="移动到指定分组")
    sort_order: Optional[int] = Field(None, ge=0, description="排序")
    note: Optional[str] = Field(None, max_length=500, description="备注")
    alert_config: Optional[str] = Field(None, description="预警配置（JSON）")


class WatchlistItemResponse(BaseModel):
    """自选股项目响应"""
    id: int
    group_id: int
    stock_code: str
    stock_name: Optional[str]
    sort_order: int
    note: Optional[str]
    alert_config: Optional[str]
    created_at: datetime
    updated_at: datetime
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    name: Optional[str] = None
    pe_ttm: Optional[float] = None
    market_value: Optional[float] = None

    class Config:
        from_attributes = True


class WatchlistGroupWithItems(WatchlistGroupResponse):
    """分组及自选股"""
    items: List[WatchlistItemResponse] = []


class WatchlistResponse(ApiResponse):
    """自选股响应"""
    groups: List[WatchlistGroupWithItems] = []
