"""
告警相关 Pydantic 数据模式
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ==================== 告警规则 ====================

class AlertRuleBase(BaseModel):
    """告警规则基类"""
    stock_code: Optional[str] = Field(None, description="股票代码，NULL为全局规则")
    rule_type: str = Field(..., description="规则类型")
    rule_name: str = Field(..., description="规则名称")
    conditions: Dict[str, Any] = Field(..., description="触发条件")


class AlertRuleCreate(AlertRuleBase):
    """创建告警规则"""
    is_enabled: bool = True
    cooldown_minutes: int = Field(default=60, ge=0, description="冷却时间(分钟)")


class AlertRuleUpdate(BaseModel):
    """更新告警规则"""
    rule_name: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    cooldown_minutes: Optional[int] = None


class AlertRuleResponse(AlertRuleBase):
    """告警规则响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_enabled: bool
    cooldown_minutes: int
    created_by: Optional[UUID] = None
    created_at: datetime
    stock_name: Optional[str] = Field(None, description="股票名称")


class AlertRuleListResponse(BaseModel):
    """告警规则列表响应"""
    total: int
    items: List[AlertRuleResponse]


# ==================== 告警历史 ====================

class AlertHistoryResponse(BaseModel):
    """告警历史响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    rule_id: int
    rule_name: Optional[str] = None
    stock_code: str
    stock_name: Optional[str] = None
    alert_type: str
    alert_data: Dict[str, Any]
    triggered_at: datetime


class AlertHistoryQuery(BaseModel):
    """告警历史查询参数"""
    stock_code: Optional[str] = None
    rule_id: Optional[int] = None
    alert_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class AlertHistoryListResponse(BaseModel):
    """告警历史列表响应"""
    total: int
    items: List[AlertHistoryResponse]


# ==================== 规则类型枚举 ====================

class RuleTypeInfo(BaseModel):
    """规则类型信息"""
    type_code: str
    type_name: str
    description: str
    default_conditions: Dict[str, Any]


RULE_TYPES: List[RuleTypeInfo] = [
    RuleTypeInfo(
        type_code="PRICE_BREAKOUT",
        type_name="价格突破",
        description="股价突破指定价位或20日最高价",
        default_conditions={"price": None, "use_20d_high": True}
    ),
    RuleTypeInfo(
        type_code="MA_CROSS",
        type_name="均线交叉",
        description="短期均线与长期均线交叉",
        default_conditions={"short_period": 5, "long_period": 20, "cross_type": "golden"}
    ),
    RuleTypeInfo(
        type_code="MACD_SIGNAL",
        type_name="MACD信号",
        description="MACD金叉或死叉",
        default_conditions={"fast": 12, "slow": 26, "signal": 9, "cross_type": "golden"}
    ),
    RuleTypeInfo(
        type_code="RSI_EXTREME",
        type_name="RSI极值",
        description="RSI进入超买或超卖区域",
        default_conditions={"period": 14, "overbought": 80, "oversold": 20}
    ),
    RuleTypeInfo(
        type_code="VOLUME_SURGE",
        type_name="成交量异动",
        description="成交量较均值放大指定倍数",
        default_conditions={"ratio": 2.0, "compare_days": 5}
    ),
    RuleTypeInfo(
        type_code="BOLLINGER_BREAK",
        type_name="布林带突破",
        description="股价突破布林带上轨或下轨",
        default_conditions={"period": 20, "std_dev": 2, "direction": "upper"}
    ),
]

