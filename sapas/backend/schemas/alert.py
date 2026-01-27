"""
预警相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import ApiResponse


class AlertCreate(BaseModel):
    """创建预警请求"""
    stock_code: Optional[str] = Field(None, description="股票代码，None表示所有股票")
    alert_type: str = Field(..., description="预警类型: price/pct_change/indicator/money_flow/custom")
    name: str = Field(..., min_length=1, max_length=100, description="预警名称")
    condition_config: Dict[str, Any] = Field(..., description="预警条件配置（JSON）")
    frequency: Optional[str] = Field("once", description="触发频率: once/daily")


class AlertUpdate(BaseModel):
    """更新预警请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    condition_config: Optional[Dict[str, Any]] = Field(None)
    frequency: Optional[str] = Field(None)
    status: Optional[str] = Field(None)


class AlertResponse(BaseModel):
    """预警响应"""
    id: int
    user_id: int
    stock_code: Optional[str]
    alert_type: str
    name: str
    condition_config: Dict[str, Any]
    frequency: str
    status: str
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """预警历史响应"""
    id: int
    alert_id: int
    stock_code: str
    trigger_time: datetime
    trigger_value: Dict[str, Any]
    message: str
    status: str
    sent_email: bool
    sent_sms: bool
    created_at: datetime


class AlertsResponse(ApiResponse):
    """预警列表响应"""
    data: List[AlertResponse] = []
