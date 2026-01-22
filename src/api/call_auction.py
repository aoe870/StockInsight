"""
集合竞价相关API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime

from src.core.database import get_db
from src.models.stock import StockCallAuction, StockBasics
from src.services.data_sync import data_sync_service
from src.schemas.call_auction import (
    CallAuctionResponse,
    CallAuctionStatsResponse,
    CallAuctionSyncRequest
)

router = APIRouter(prefix="/call-auction", tags=["call-auction"])


@router.get("/realtime", response_model=List[CallAuctionResponse])
async def get_realtime_call_auction(
    query_date: Optional[str] = Query(None, description="查询日期 (YYYY-MM-DD)，不传则查询今天"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取集合竞价数据

    参数:
        query_date: 查询日期，不传则查询今天

    返回:
        指定日期所有股票的集合竞价数据
    """
    try:
        # 确定查询日期
        if query_date:
            target_date = date.fromisoformat(query_date)
        else:
            target_date = date.today()

        # 查询指定日期的集合竞价数据
        from sqlalchemy import select
        query = select(StockCallAuction, StockBasics.name).join(
            StockBasics, StockCallAuction.code == StockBasics.code
        ).where(
            StockCallAuction.trade_date == target_date
        ).order_by(
            StockCallAuction.auction_time.desc()
        )

        result = await db.execute(query)
        rows = result.all()

        auction_data = []
        for row in rows:
            auction, name = row
            auction_data.append(CallAuctionResponse(
                code=auction.code,
                name=name,
                trade_date=auction.trade_date.isoformat(),
                auction_time=auction.auction_time,
                price=float(auction.price) if auction.price else None,
                volume=auction.volume,
                amount=float(auction.amount) if auction.amount else None,
                buy_volume=auction.buy_volume,
                sell_volume=auction.sell_volume,
                change_pct=float(auction.change_pct) if auction.change_pct else None,
                change_amount=float(auction.change_amount) if auction.change_amount else None,
                bid_ratio=float(auction.bid_ratio) if auction.bid_ratio else None,
            ))

        return auction_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取集合竞价数据失败: {str(e)}")


@router.get("/history/{code}", response_model=List[CallAuctionResponse])
async def get_call_auction_history(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定股票的历史集合竞价数据

    参数:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    返回:
        历史集合竞价数据列表
    """
    try:
        from sqlalchemy import select

        query = select(StockCallAuction, StockBasics.name).join(
            StockBasics, StockCallAuction.code == StockBasics.code
        ).where(
            StockCallAuction.code == code
        )

        if start_date:
            query = query.where(StockCallAuction.trade_date >= date.fromisoformat(start_date))
        if end_date:
            query = query.where(StockCallAuction.trade_date <= date.fromisoformat(end_date))

        query = query.order_by(
            StockCallAuction.trade_date.desc(),
            StockCallAuction.auction_time.desc()
        )

        result = await db.execute(query)
        rows = result.all()

        auction_data = []
        for row in rows:
            auction, name = row
            auction_data.append(CallAuctionResponse(
                code=auction.code,
                name=name,
                trade_date=auction.trade_date.isoformat(),
                auction_time=auction.auction_time,
                price=float(auction.price) if auction.price else None,
                volume=auction.volume,
                amount=float(auction.amount) if auction.amount else None,
                buy_volume=auction.buy_volume,
                sell_volume=auction.sell_volume,
                change_pct=float(auction.change_pct) if auction.change_pct else None,
                change_amount=float(auction.change_amount) if auction.change_amount else None,
                bid_ratio=float(auction.bid_ratio) if auction.bid_ratio else None,
            ))

        return auction_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史集合竞价数据失败: {str(e)}")


@router.get("/stats/{trade_date_str}", response_model=CallAuctionStatsResponse)
async def get_call_auction_stats(
    trade_date_str: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定日期的集合竞价统计数据

    参数:
        trade_date_str: 交易日期 (YYYY-MM-DD)

    返回:
        集合竞价统计数据
    """
    try:
        from sqlalchemy import select, func

        query_date = date.fromisoformat(trade_date_str)

        # 查询当日所有集合竞价数据
        query = select(
            func.count().label("total_count"),
            func.sum(StockCallAuction.volume).label("total_volume"),
            func.sum(StockCallAuction.amount).label("total_amount")
        ).where(
            StockCallAuction.trade_date == query_date
        )

        result = await db.execute(query)
        row = result.one_or_none()

        if not row or row.total_count == 0:
            return CallAuctionStatsResponse(
                trade_date=trade_date_str,
                total_count=0,
                total_volume=0,
                total_amount=0,
                avg_price=0,
                rise_count=0,
                fall_count=0,
                limit_up_count=0,
                limit_down_count=0,
            )

        total_count = row.total_count or 0
        total_volume = row.total_volume or 0
        total_amount = row.total_amount or 0

        # 计算平均价格
        avg_price = total_amount / total_volume if total_volume > 0 else 0

        # 统计涨跌数量
        rise_query = select(func.count()).where(
            StockCallAuction.trade_date == query_date,
            StockCallAuction.change_pct > 0
        )
        rise_count = (await db.execute(rise_query)).scalar() or 0

        fall_query = select(func.count()).where(
            StockCallAuction.trade_date == query_date,
            StockCallAuction.change_pct < 0
        )
        fall_count = (await db.execute(fall_query)).scalar() or 0

        # 统计涨跌停数量
        limit_up_query = select(func.count()).where(
            StockCallAuction.trade_date == query_date,
            StockCallAuction.change_pct >= 9.9
        )
        limit_up_count = (await db.execute(limit_up_query)).scalar() or 0

        limit_down_query = select(func.count()).where(
            StockCallAuction.trade_date == query_date,
            StockCallAuction.change_pct <= -9.9
        )
        limit_down_count = (await db.execute(limit_down_query)).scalar() or 0

        return CallAuctionStatsResponse(
            trade_date=trade_date_str,
            total_count=total_count,
            total_volume=total_volume,
            total_amount=total_amount,
            avg_price=avg_price,
            rise_count=rise_count,
            fall_count=fall_count,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取集合竞价统计失败: {str(e)}")


@router.post("/sync/realtime")
async def sync_realtime_call_auction(
    db: AsyncSession = Depends(get_db)
):
    """
    同步实时集合竞价数据

    返回:
        同步结果
    """
    try:
        count = await data_sync_service.sync_call_auction_realtime(db)
        await db.commit()

        return {
            "success": True,
            "message": f"成功同步 {count} 条集合竞价数据",
            "count": count
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"同步集合竞价数据失败: {str(e)}")


@router.post("/sync/history")
async def sync_history_call_auction(
    request: CallAuctionSyncRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    同步历史集合竞价数据

    参数:
        request: 同步请求参数

    返回:
        同步结果
    """
    try:
        trade_date = date.fromisoformat(request.trade_date)
        results = await data_sync_service.sync_call_auction_by_date(
            db,
            trade_date=trade_date,
            codes=request.codes
        )
        await db.commit()

        success_count = sum(1 for v in results.values() if v > 0)

        return {
            "success": True,
            "message": f"成功同步 {success_count}/{len(results)} 只股票的集合竞价数据",
            "results": results
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"同步历史集合竞价数据失败: {str(e)}")
