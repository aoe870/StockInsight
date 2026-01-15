"""
订阅相关 Pydantic 数据模式
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SubscriptionBase(BaseModel):
    """订阅基类"""
    rule_id: int = Field(..., description="规则ID")
    channel: str = Field(..., description="通知渠道: console/email/webhook/wechat")
    channel_config: Optional[Dict[str, Any]] = Field(None, description="渠道配置")


class SubscriptionCreate(SubscriptionBase):
    """创建订阅"""
    pass


class SubscriptionUpdate(BaseModel):
    """更新订阅"""
    channel: Optional[str] = None
    channel_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(SubscriptionBase):
    """订阅响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: UUID
    is_active: bool
    created_at: datetime
    
    # 关联信息
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None


class SubscriptionListResponse(BaseModel):
    """订阅列表响应"""
    total: int
    items: List[SubscriptionResponse]


# ==================== 通知渠道 ====================

class ChannelInfo(BaseModel):
    """通知渠道信息"""
    channel_code: str
    channel_name: str
    description: str
    config_schema: Dict[str, Any]


NOTIFICATION_CHANNELS: List[ChannelInfo] = [
    ChannelInfo(
        channel_code="console",
        channel_name="控制台",
        description="在控制台输出告警信息",
        config_schema={}
    ),
    ChannelInfo(
        channel_code="email",
        channel_name="邮件",
        description="发送邮件通知",
        config_schema={
            "email": {"type": "string", "description": "接收邮箱", "required": True}
        }
    ),
    ChannelInfo(
        channel_code="webhook",
        channel_name="Webhook",
        description="发送HTTP POST请求到指定URL",
        config_schema={
            "url": {"type": "string", "description": "Webhook URL", "required": True},
            "headers": {"type": "object", "description": "自定义请求头", "required": False}
        }
    ),
    ChannelInfo(
        channel_code="wechat",
        channel_name="微信",
        description="通过企业微信机器人发送消息",
        config_schema={
            "webhook_key": {"type": "string", "description": "机器人Key", "required": True}
        }
    ),
]

