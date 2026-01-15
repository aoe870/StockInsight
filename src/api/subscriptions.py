"""
订阅管理 API 路由
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.stock import StockBasics
from src.models.user import User
from src.models.alert import AlertRule
from src.models.subscription import Subscription
from src.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionListResponse,
    NOTIFICATION_CHANNELS,
    ChannelInfo,
)
from src.utils.logger import logger

router = APIRouter(prefix="/subscriptions", tags=["订阅管理"])


async def get_current_user_id(db: AsyncSession = Depends(get_db)) -> UUID:
    """获取当前用户ID（临时实现）"""
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户未认证")
    return user.id


@router.get("/channels", response_model=List[ChannelInfo])
async def get_notification_channels():
    """获取支持的通知渠道"""
    return NOTIFICATION_CHANNELS


@router.get("", response_model=SubscriptionListResponse)
async def get_subscriptions(
    is_active: bool | None = Query(None, description="按激活状态筛选"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """获取当前用户的订阅列表"""
    query = select(Subscription).where(Subscription.user_id == user_id)
    
    if is_active is not None:
        query = query.where(Subscription.is_active == is_active)
    
    query = query.order_by(Subscription.created_at.desc())
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    # 补充关联信息
    items = []
    for sub in subscriptions:
        resp = SubscriptionResponse.model_validate(sub)
        
        # 获取规则信息
        rule_result = await db.execute(
            select(AlertRule).where(AlertRule.id == sub.rule_id)
        )
        rule = rule_result.scalar_one_or_none()
        if rule:
            resp.rule_name = rule.rule_name
            resp.rule_type = rule.rule_type
            resp.stock_code = rule.stock_code
            
            # 获取股票名称
            if rule.stock_code:
                stock_result = await db.execute(
                    select(StockBasics.name).where(StockBasics.code == rule.stock_code)
                )
                resp.stock_name = stock_result.scalar()
        
        items.append(resp)
    
    return SubscriptionListResponse(total=len(items), items=items)


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """创建订阅"""
    # 检查规则是否存在
    rule_result = await db.execute(
        select(AlertRule).where(AlertRule.id == data.rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 验证通知渠道
    valid_channels = [ch.channel_code for ch in NOTIFICATION_CHANNELS]
    if data.channel not in valid_channels:
        raise HTTPException(status_code=400, detail=f"无效的通知渠道: {data.channel}")
    
    # 检查是否已订阅
    existing = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.rule_id == data.rule_id,
            Subscription.channel == data.channel
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已存在相同的订阅")
    
    # 创建订阅
    sub = Subscription(
        user_id=user_id,
        rule_id=data.rule_id,
        channel=data.channel,
        channel_config=data.channel_config,
        is_active=True
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    
    logger.info(f"用户 {user_id} 订阅规则 {rule.rule_name} (渠道: {data.channel})")
    
    resp = SubscriptionResponse.model_validate(sub)
    resp.rule_name = rule.rule_name
    resp.rule_type = rule.rule_type
    resp.stock_code = rule.stock_code
    
    if rule.stock_code:
        stock_result = await db.execute(
            select(StockBasics.name).where(StockBasics.code == rule.stock_code)
        )
        resp.stock_name = stock_result.scalar()

    return resp


@router.put("/{sub_id}", response_model=SubscriptionResponse)
async def update_subscription(
    sub_id: int,
    data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """更新订阅"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == sub_id,
            Subscription.user_id == user_id
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    # 更新字段
    if data.channel is not None:
        valid_channels = [ch.channel_code for ch in NOTIFICATION_CHANNELS]
        if data.channel not in valid_channels:
            raise HTTPException(status_code=400, detail=f"无效的通知渠道: {data.channel}")
        sub.channel = data.channel
    if data.channel_config is not None:
        sub.channel_config = data.channel_config
    if data.is_active is not None:
        sub.is_active = data.is_active

    await db.flush()
    await db.refresh(sub)

    # 获取关联信息
    rule_result = await db.execute(
        select(AlertRule).where(AlertRule.id == sub.rule_id)
    )
    rule = rule_result.scalar_one_or_none()

    resp = SubscriptionResponse.model_validate(sub)
    if rule:
        resp.rule_name = rule.rule_name
        resp.rule_type = rule.rule_type
        resp.stock_code = rule.stock_code

        if rule.stock_code:
            stock_result = await db.execute(
                select(StockBasics.name).where(StockBasics.code == rule.stock_code)
            )
            resp.stock_name = stock_result.scalar()

    return resp


@router.delete("/{sub_id}")
async def delete_subscription(
    sub_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """删除订阅"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == sub_id,
            Subscription.user_id == user_id
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    await db.delete(sub)

    logger.info(f"用户 {user_id} 取消订阅 (ID: {sub_id})")

    return {"success": True, "message": "已取消订阅"}


@router.post("/{sub_id}/toggle")
async def toggle_subscription(
    sub_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """切换订阅激活状态"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == sub_id,
            Subscription.user_id == user_id
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    sub.is_active = not sub.is_active
    await db.flush()

    status = "激活" if sub.is_active else "暂停"
    logger.info(f"用户 {user_id} {status}订阅 (ID: {sub_id})")

    return {"success": True, "is_active": sub.is_active, "message": f"订阅已{status}"}

