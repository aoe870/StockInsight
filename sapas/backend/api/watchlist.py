"""
自选股相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..core.database import get_db_session
from ..core.auth import get_current_user_id
from ..schemas.watchlist import (
    WatchlistGroupCreate,
    WatchlistGroupUpdate,
    WatchlistGroupResponse,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistResponse,
    WatchlistGroupWithItems
)
from ..models import WatchlistGroup, WatchlistItem

router = APIRouter(prefix="/api/v1/watchlist", tags=["自选股"])


@router.post("/groups", response_model=dict)
async def create_group(
    request: WatchlistGroupCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建自选股分组

    请求示例:
    ```json
    {
      "name": "核心股池",
      "description": "长期持有的核心股票",
      "icon": "star"
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    group = WatchlistGroup(
        user_id=user_id,
        name=request.name,
        description=request.description,
        icon=request.icon
    )

    db.add(group)
    await db.commit()
    await db.refresh(group)

    return {
        "code": 0,
        "message": "分组创建成功",
        "data": WatchlistGroupResponse.model_validate(group)
    }


@router.put("/groups/{group_id}", response_model=dict)
async def update_group(
    group_id: int,
    request: WatchlistGroupUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新自选股分组

    请求示例:
    ```json
    {
      "name": "新名称",
      "sort_order": 1
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取分组并验证权限
    result = await db.execute(
        select(WatchlistGroup).where(WatchlistGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group or group.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分组不存在或无权限"
        )

    # 更新字段
    if request.name is not None:
        group.name = request.name
    if request.description is not None:
        group.description = request.description
    if request.icon is not None:
        group.icon = request.icon
    if request.sort_order is not None:
        group.sort_order = request.sort_order
    if request.is_default is not None:
        # 如果设为默认，取消其他默认分组
        if request.is_default:
            await db.execute(
                select(WatchlistGroup)
                .where(and_(
                    WatchlistGroup.user_id == user_id,
                    WatchlistGroup.id != group_id,
                    WatchlistGroup.is_default == True
                ))
                .values(is_default=False)
            )
        group.is_default = request.is_default

    await db.commit()

    return {
        "code": 0,
        "message": "分组更新成功",
        "data": WatchlistGroupResponse.model_validate(group)
    }


@router.delete("/groups/{group_id}", response_model=dict)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除自选股分组"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取分组并验证权限
    result = await db.execute(
        select(WatchlistGroup).where(WatchlistGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group or group.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分组不存在或无权限"
        )

    await db.delete(group)
    await db.commit()

    return {
        "code": 0,
        "message": "分组删除成功"
    }


@router.get("/groups", response_model=dict)
async def get_groups(
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取用户的自选股分组列表

    返回示例:
    ```json
    {
      "code": 0,
      "message": "success",
      "data": [
        {
          "id": 1,
          "name": "默认分组",
          "item_count": 10
        }
      ]
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取用户分组
    result = await db.execute(
        select(WatchlistGroup)
        .where(WatchlistGroup.user_id == user_id)
        .order_by(WatchlistGroup.sort_order)
    )

    groups = result.scalars().all()

    # 获取每个分组的自选股数量
    group_data = []
    for group in groups:
        # 统计自选股数量
        count_result = await db.execute(
            select(func.count(WatchlistItem.id))
            .where(WatchlistItem.group_id == group.id)
        )
        count = count_result.scalar() or 0

        group_response = WatchlistGroupResponse.model_validate(group)
        group_response.item_count = count
        group_data.append(group_response)

    return {
        "code": 0,
        "message": "success",
        "data": group_data
    }


@router.post("/items", response_model=dict)
async def add_items(
    request: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    添加自选股

    请求示例:
    ```json
    {
      "stock_codes": ["600519", "000001", "000002"]
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    if len(request.stock_codes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="股票代码列表不能为空"
        )

    if len(request.stock_codes) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次最多添加100只股票"
        )

    # 获取默认分组或第一个分组
    group_result = await db.execute(
        select(WatchlistGroup)
        .where(and_(
            WatchlistGroup.user_id == user_id,
            or_(
                WatchlistGroup.is_default == True,
                WatchlistGroup.id == select(WatchlistGroup.id)
                    .where(WatchlistGroup.user_id == user_id)
                    .order_by(WatchlistGroup.id)
                    .limit(1)
            )
        ))
    )
    group = group_result.scalar_one_or_none()

    if not group:
        # 创建默认分组
        group = WatchlistGroup(
            user_id=user_id,
            name="默认分组",
            is_default=True
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)

    # 添加自选股
    from ..core.data_gateway import data_gateway
    added_count = 0

    for stock_code in request.stock_codes:
        # 检查是否已存在
        existing_result = await db.execute(
            select(WatchlistItem).where(and_(
                WatchlistItem.group_id == group.id,
                WatchlistItem.stock_code == stock_code
            ))
        existing = existing_result.scalar_one_or_none()

        if not existing:
            item = WatchlistItem(
                group_id=group.id,
                stock_code=stock_code
            )
            db.add(item)
            added_count += 1

    await db.commit()

    return {
        "code": 0,
        "message": f"成功添加{added_count}只股票",
        "data": {"added_count": added_count, "skipped": len(request.stock_codes) - added_count}
    }


@router.put("/items/{item_id}", response_model=dict)
async def update_item(
    item_id: int,
    request: WatchlistItemUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新自选股

    请求示例:
    ```json
    {
      "group_id": 2,
      "sort_order": 5,
      "note": "长期持有",
      "alert_config": "{\"price_above\": 100.50}"
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取项目并验证权限
    result = await db.execute(
        select(WatchlistItem, WatchlistGroup)
        .join(WatchlistGroup, WatchlistItem.group_id == WatchlistGroup.id)
        .where(WatchlistItem.id == item_id)
    )
    item_data = result.one_or_none()
    if not item_data or len(item_data) != 2 or item_data[1].user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="自选股不存在或无权限"
        )

    item, group = item_data

    # 更新字段
    if request.group_id is not None:
        # 验证新分组所有权
        group_result = await db.execute(
            select(WatchlistGroup).where(and_(
                WatchlistGroup.id == request.group_id,
                WatchlistGroup.user_id == user_id
            ))
        new_group = group_result.scalar_one_or_none()
        if not new_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标分组不存在"
            )
        item.group_id = request.group_id
    if request.sort_order is not None:
        item.sort_order = request.sort_order
    if request.note is not None:
        item.note = request.note
    if request.alert_config is not None:
        item.alert_config = request.alert_config

    await db.commit()

    return {
        "code": 0,
        "message": "更新成功",
        "data": {"item_id": item_id}
    }


@router.delete("/items/{item_id}", response_model=dict)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除自选股"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取项目并验证权限
    result = await db.execute(
        select(WatchlistItem, WatchlistGroup)
        .join(WatchlistGroup, WatchlistItem.group_id == WatchlistGroup.id)
        .where(WatchlistItem.id == item_id)
    )
    item_data = result.one_or_none()
    if not item_data or len(item_data) != 2 or item_data[1].user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="自选股不存在或无权限"
        )

    await db.delete(item_data[0])
    await db.commit()

    return {
        "code": 0,
        "message": "删除成功"
    }


@router.get("/items", response_model=dict)
async def get_items(
    group_id: int | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取自选股列表

    参数:
        group_id: 分组ID，None表示所有分组

    返回示例:
    ```json
    {
      "code": 0,
      "message": "success",
      "data": [
        {
          "id": 1,
          "stock_code": "600519",
          "stock_name": "贵州茅台",
          "current_price": 1678.00,
          "change_pct": 0.18
        }
      ]
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 构建查询
    query = select(WatchlistItem, WatchlistGroup)
        .join(WatchlistGroup, WatchlistItem.group_id == WatchlistGroup.id)
        .where(WatchlistGroup.user_id == user_id)
        .order_by(WatchlistItem.sort_order)

    if group_id is not None:
        query = query.where(WatchlistItem.group_id == group_id)

    result = await db.execute(query)
    items = result.all()

    # 获取所有自选股的代码
    all_stock_codes = [item[0].stock_code for item in items]
    all_stock_codes_set = set(all_stock_codes)

    # 批量获取实时行情
    from ..core.data_gateway import data_gateway
    quotes = {}
    if all_stock_codes_set:
        try:
            quote_data = await data_gateway.get_quote("cn_a", list(all_stock_codes_set))
            if quote_data.get("code") == 0:
                quotes = quote_data.get("data", {})
        except Exception as e:
            from ..config import settings
            settings.LOGGER.error(f"Failed to get quotes: {e}")

    # 组装响应数据
    response_data = []
    for item in items:
        item_data = WatchlistItemResponse.model_validate(item[0])
        quote = quotes.get(item[0].stock_code, {})
        if quote:
            item_data.current_price = quote.get("price")
            item_data.change_pct = quote.get("change_pct")
            item_data.name = quote.get("name")
            item_data.pe_ttm = quote.get("pe_ttm")
            item_data.market_value = quote.get("market_value")
        response_data.append(item_data)

    return {
        "code": 0,
        "message": "success",
        "data": response_data
    }
