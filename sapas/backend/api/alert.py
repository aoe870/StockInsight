"""
预警相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ..core.database import get_db_session
from ..core.auth import get_current_user_id
from ..schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertsResponse,
    AlertHistoryResponse,
    AlertType
)
from ..models import Alert, AlertHistory

router = APIRouter(prefix="/api/v1/alerts", tags=["预警"])


@router.post("", response_model=dict)
async def create_alert(
    request: AlertCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建预警规则

    请求示例:
    ```json
    {
      "stock_code": "600519",
      "alert_type": "price",
      "name": "价格预警",
      "condition_config": {
        "operator": "gt",
        "value": 1700.00
      },
      "frequency": "daily"
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 验证预警类型
    try:
        alert_type = AlertType(request.alert_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的预警类型: {request.alert_type}"
        )

    # 检查用户预警数量限制
    from ..config import get_settings
    settings = get_settings()
    count_result = await db.execute(
        select(func.count(Alert.id))
        .where(and_(
            Alert.user_id == user_id,
            Alert.status == "active"
        ))
    )
    count = count_result.scalar() or 0
    if count >= settings.ALERT_MAX_RULES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"预警规则数量已达上限 ({settings.ALERT_MAX_RULES_PER_USER})"
        )

    alert = Alert(
        user_id=user_id,
        stock_code=request.stock_code,
        alert_type=request.alert_type,
        name=request.name,
        condition_config=request.condition_config,
        frequency=request.frequency,
        status="active"
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {
        "code": 0,
        "message": "预警创建成功",
        "data": AlertResponse.model_validate(alert)
    }


@router.put("/{alert_id}", response_model=dict)
async def update_alert(
    alert_id: int,
    request: AlertUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新预警规则

    请求示例:
    ```json
    {
      "name": "新名称",
      "condition_config": {
        "operator": "gt",
        "value": 1750.00
      },
      "status": "disabled"
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取预警并验证权限
    result = await db.execute(
        select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == user_id))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    # 更新字段
    if request.name is not None:
        alert.name = request.name
    if request.condition_config is not None:
        alert.condition_config = request.condition_config
    if request.frequency is not None:
        alert.frequency = request.frequency
    if request.status is not None:
        alert.status = request.status

    await db.commit()
    await db.refresh(alert)

    return {
        "code": 0,
        "message": "更新成功",
        "data": AlertResponse.model_validate(alert)
    }


@router.delete("/{alert_id}", response_model=dict)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除预警规则"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取预警并验证权限
    result = await db.execute(
        select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == user_id))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    await db.delete(alert)
    await db.commit()

    return {
        "code": 0,
        "message": "删除成功"
    }


@router.get("", response_model=AlertsResponse)
async def get_alerts(
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取用户的预警规则列表
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取预警列表
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == user_id)
        .order_by(desc(Alert.created_at))
    )
    alerts = result.scalars().all()

    return AlertsResponse(data=[AlertResponse.model_validate(a) for a in alerts])


@router.post("/{alert_id}/enable", response_model=dict)
async def enable_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """启用预警"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    result = await db.execute(
        select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == user_id))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    alert.status = "active"
    await db.commit()

    return {
        "code": 0,
        "message": "预警已启用"
    }


@router.post("/{alert_id}/disable", response_model=dict)
async def disable_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """禁用预警"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    result = await db.execute(
        select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == user_id))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警不存在"
        )

    alert.status = "disabled"
    await db.commit()

    return {
        "code": 0,
        "message": "预警已禁用"
    }


@router.get("/history", response_model=dict)
async def get_alert_history(
    alert_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="过滤: unread/read/archived"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取预警历史记录

    参数:
        alert_id: 预警ID，None表示所有预警
        limit: 返回数量
        status: 状态过滤
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 构建查询
    query = select(AlertHistory)
    if alert_id:
        query = query.where(AlertHistory.alert_id == alert_id)
    else:
        # 获取用户所有预警的历史
            subquery = select(Alert.id).where(Alert.user_id == user_id)
            query = query.where(AlertHistory.alert_id.in_(subquery))

    if status:
        query = query.where(AlertHistory.status == status)

    query = query.order_by(desc(AlertHistory.trigger_time))
    query = query.limit(limit)

    result = await db.execute(query)
    history = result.scalars().all()

    return {
        "code": 0,
        "message": "success",
        "data": [AlertHistoryResponse.model_validate(h) for h in history]
    }
