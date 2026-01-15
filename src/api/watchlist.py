"""
自选股 API 路由
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.stock import StockBasics
from src.models.user import User, WatchlistItem
from src.schemas.watchlist import (
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistBatchCreate,
    WatchlistBatchResponse,
)
from src.utils.logger import logger

router = APIRouter(prefix="/watchlist", tags=["自选股"])


# 临时: 获取默认用户ID (后续替换为认证系统)
async def get_current_user_id(db: AsyncSession = Depends(get_db)) -> UUID:
    """获取当前用户ID（临时实现）"""
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户未认证")
    return user.id


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """获取自选股列表"""
    query = (
        select(WatchlistItem, StockBasics.name)
        .join(StockBasics, WatchlistItem.stock_code == StockBasics.code)
        .where(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.sort_order, WatchlistItem.added_at.desc())
    )
    
    result = await db.execute(query)
    items = result.all()
    
    response_items = []
    for item, stock_name in items:
        resp = WatchlistItemResponse.model_validate(item)
        resp.stock_name = stock_name
        response_items.append(resp)
    
    return WatchlistResponse(total=len(response_items), items=response_items)


@router.post("", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    data: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """添加自选股"""
    # 检查股票是否存在
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == data.stock_code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {data.stock_code} 不存在")
    
    # 检查是否已添加
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.stock_code == data.stock_code
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该股票已在自选股中")
    
    # 获取最大排序号
    max_order_result = await db.execute(
        select(func.max(WatchlistItem.sort_order))
        .where(WatchlistItem.user_id == user_id)
    )
    max_order = max_order_result.scalar() or 0
    
    # 创建自选股
    item = WatchlistItem(
        user_id=user_id,
        stock_code=data.stock_code,
        note=data.note,
        sort_order=max_order + 1
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    
    logger.info(f"用户 {user_id} 添加自选股: {data.stock_code}")
    
    resp = WatchlistItemResponse.model_validate(item)
    resp.stock_name = stock.name
    return resp


@router.post("/batch", response_model=WatchlistBatchResponse)
async def batch_add_to_watchlist(
    data: WatchlistBatchCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """批量添加自选股"""
    success_count = 0
    failed_codes = []
    
    # 获取当前最大排序号
    max_order_result = await db.execute(
        select(func.max(WatchlistItem.sort_order))
        .where(WatchlistItem.user_id == user_id)
    )
    current_order = (max_order_result.scalar() or 0) + 1
    
    for code in data.stock_codes:
        # 检查股票是否存在
        stock_result = await db.execute(
            select(StockBasics).where(StockBasics.code == code)
        )
        if not stock_result.scalar_one_or_none():
            failed_codes.append(code)
            continue
        
        # 检查是否已存在
        existing = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.stock_code == code
            )
        )
        if existing.scalar_one_or_none():
            failed_codes.append(code)
            continue
        
        # 添加
        item = WatchlistItem(
            user_id=user_id,
            stock_code=code,
            sort_order=current_order
        )
        db.add(item)
        success_count += 1
        current_order += 1
    
    return WatchlistBatchResponse(
        success_count=success_count,
        failed_count=len(failed_codes),
        failed_codes=failed_codes
    )


@router.put("/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    item_id: int,
    data: WatchlistItemUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """更新自选股"""
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="自选股不存在")

    # 更新字段
    if data.note is not None:
        item.note = data.note
    if data.sort_order is not None:
        item.sort_order = data.sort_order

    await db.flush()
    await db.refresh(item)

    # 获取股票名称
    stock_result = await db.execute(
        select(StockBasics.name).where(StockBasics.code == item.stock_code)
    )
    stock_name = stock_result.scalar()

    resp = WatchlistItemResponse.model_validate(item)
    resp.stock_name = stock_name
    return resp


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """删除自选股"""
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="自选股不存在")

    stock_code = item.stock_code
    await db.delete(item)

    logger.info(f"用户 {user_id} 删除自选股: {stock_code}")

    return {"success": True, "message": f"已删除 {stock_code}"}


@router.delete("")
async def clear_watchlist(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """清空自选股"""
    await db.execute(
        delete(WatchlistItem).where(WatchlistItem.user_id == user_id)
    )

    logger.info(f"用户 {user_id} 清空自选股")

    return {"success": True, "message": "已清空自选股"}

