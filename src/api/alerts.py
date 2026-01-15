"""
告警规则 API 路由
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.stock import StockBasics
from src.models.user import User
from src.models.alert import AlertRule, AlertHistory
from src.schemas.alert import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertRuleListResponse,
    AlertHistoryResponse,
    AlertHistoryQuery,
    AlertHistoryListResponse,
    RULE_TYPES,
    RuleTypeInfo,
)
from src.utils.logger import logger

router = APIRouter(prefix="/alerts", tags=["告警管理"])


async def get_current_user_id(db: AsyncSession = Depends(get_db)) -> UUID:
    """获取当前用户ID（临时实现）"""
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户未认证")
    return user.id


@router.get("/rule-types", response_model=List[RuleTypeInfo])
async def get_rule_types():
    """获取支持的规则类型"""
    return RULE_TYPES


@router.get("/rules", response_model=AlertRuleListResponse)
async def get_alert_rules(
    stock_code: Optional[str] = Query(None, description="按股票代码筛选"),
    rule_type: Optional[str] = Query(None, description="按规则类型筛选"),
    is_enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则列表"""
    query = select(AlertRule)
    
    if stock_code:
        query = query.where(AlertRule.stock_code == stock_code)
    if rule_type:
        query = query.where(AlertRule.rule_type == rule_type)
    if is_enabled is not None:
        query = query.where(AlertRule.is_enabled == is_enabled)
    
    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # 分页
    query = query.order_by(AlertRule.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    # 获取股票名称
    items = []
    for rule in rules:
        resp = AlertRuleResponse.model_validate(rule)
        if rule.stock_code:
            stock_result = await db.execute(
                select(StockBasics.name).where(StockBasics.code == rule.stock_code)
            )
            resp.stock_name = stock_result.scalar()
        items.append(resp)
    
    return AlertRuleListResponse(total=total, items=items)


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """创建告警规则"""
    # 如果指定股票，检查是否存在
    stock_name = None
    if data.stock_code:
        stock_result = await db.execute(
            select(StockBasics).where(StockBasics.code == data.stock_code)
        )
        stock = stock_result.scalar_one_or_none()
        if not stock:
            raise HTTPException(status_code=404, detail=f"股票 {data.stock_code} 不存在")
        stock_name = stock.name
    
    # 验证规则类型
    valid_types = [rt.type_code for rt in RULE_TYPES]
    if data.rule_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"无效的规则类型: {data.rule_type}")
    
    rule = AlertRule(
        stock_code=data.stock_code,
        rule_type=data.rule_type,
        rule_name=data.rule_name,
        conditions=data.conditions,
        is_enabled=data.is_enabled,
        cooldown_minutes=data.cooldown_minutes,
        created_by=user_id
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    
    logger.info(f"创建告警规则: {rule.rule_name} (ID: {rule.id})")
    
    resp = AlertRuleResponse.model_validate(rule)
    resp.stock_name = stock_name
    return resp


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取告警规则详情"""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    resp = AlertRuleResponse.model_validate(rule)
    if rule.stock_code:
        stock_result = await db.execute(
            select(StockBasics.name).where(StockBasics.code == rule.stock_code)
        )
        resp.stock_name = stock_result.scalar()

    return resp


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """更新告警规则"""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    # 更新字段
    if data.rule_name is not None:
        rule.rule_name = data.rule_name
    if data.conditions is not None:
        rule.conditions = data.conditions
    if data.is_enabled is not None:
        rule.is_enabled = data.is_enabled
    if data.cooldown_minutes is not None:
        rule.cooldown_minutes = data.cooldown_minutes

    await db.flush()
    await db.refresh(rule)

    logger.info(f"更新告警规则: {rule.rule_name} (ID: {rule.id})")

    resp = AlertRuleResponse.model_validate(rule)
    if rule.stock_code:
        stock_result = await db.execute(
            select(StockBasics.name).where(StockBasics.code == rule.stock_code)
        )
        resp.stock_name = stock_result.scalar()

    return resp


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """删除告警规则"""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule_name = rule.rule_name
    await db.delete(rule)

    logger.info(f"删除告警规则: {rule_name} (ID: {rule_id})")

    return {"success": True, "message": f"已删除规则: {rule_name}"}


# ==================== 告警历史 ====================

@router.get("/history", response_model=AlertHistoryListResponse)
async def get_alert_history(
    stock_code: Optional[str] = Query(None),
    rule_id: Optional[int] = Query(None),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """获取告警历史"""
    query = select(AlertHistory)

    if stock_code:
        query = query.where(AlertHistory.stock_code == stock_code)
    if rule_id:
        query = query.where(AlertHistory.rule_id == rule_id)
    if alert_type:
        query = query.where(AlertHistory.alert_type == alert_type)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页
    query = query.order_by(AlertHistory.triggered_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    history_items = result.scalars().all()

    # 补充关联信息
    items = []
    for h in history_items:
        resp = AlertHistoryResponse.model_validate(h)

        # 获取规则名称
        rule_result = await db.execute(
            select(AlertRule.rule_name).where(AlertRule.id == h.rule_id)
        )
        resp.rule_name = rule_result.scalar()

        # 获取股票名称
        stock_result = await db.execute(
            select(StockBasics.name).where(StockBasics.code == h.stock_code)
        )
        resp.stock_name = stock_result.scalar()

        items.append(resp)

    return AlertHistoryListResponse(total=total, items=items)

