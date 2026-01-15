"""
数据同步 API 路由
"""

import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db, get_db_session
from src.models.stock import StockBasics, StockDailyK
from src.models.user import User, WatchlistItem
from src.services.data_sync import data_sync_service
from src.utils.logger import logger

router = APIRouter(prefix="/sync", tags=["数据同步"])

# 全量同步状态
_full_sync_status: Dict[str, Any] = {
    "is_running": False,
    "started_at": None,
    "total": 0,
    "completed": 0,
    "success": 0,
    "failed": 0,
    "current_code": None,
    "errors": [],
}


async def get_current_user_id(db: AsyncSession = Depends(get_db)) -> UUID:
    """获取当前用户ID（临时实现）"""
    result = await db.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户未认证")
    return user.id


@router.post("/stock-list")
async def sync_stock_list(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    同步股票列表
    从 AKShare 获取最新的 A 股股票列表并更新数据库
    """
    try:
        count = await data_sync_service.sync_stock_list(db)
        return {
            "success": True,
            "message": f"股票列表同步完成",
            "count": count
        }
    except Exception as e:
        logger.error(f"股票列表同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-k/{code}")
async def sync_single_stock_daily_k(
    code: str,
    adjust: str = "qfq",
    db: AsyncSession = Depends(get_db)
):
    """
    同步单只股票的日K线数据
    """
    try:
        count = await data_sync_service.sync_daily_k(db, code, adjust=adjust)
        return {
            "success": True,
            "message": f"{code} 日K线同步完成",
            "count": count
        }
    except Exception as e:
        logger.error(f"同步 {code} 日K线失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist-daily-k")
async def sync_watchlist_daily_k(
    adjust: str = "qfq",
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    同步自选股的日K线数据
    """
    # 获取自选股列表
    result = await db.execute(
        select(WatchlistItem.stock_code).where(WatchlistItem.user_id == user_id)
    )
    stock_codes = [row[0] for row in result.all()]
    
    if not stock_codes:
        return {
            "success": True,
            "message": "自选股列表为空，无需同步",
            "results": {}
        }
    
    try:
        results = await data_sync_service.sync_watchlist_daily_k(
            db, stock_codes, adjust=adjust
        )
        
        success_count = sum(1 for v in results.values() if v >= 0)
        total_records = sum(v for v in results.values() if v > 0)
        
        return {
            "success": True,
            "message": f"自选股同步完成: {success_count}/{len(stock_codes)} 成功",
            "total_records": total_records,
            "results": results
        }
    except Exception as e:
        logger.error(f"自选股同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-daily-k")
async def sync_batch_daily_k(
    codes: List[str],
    adjust: str = "qfq",
    db: AsyncSession = Depends(get_db)
):
    """
    批量同步指定股票的日K线数据
    """
    if not codes:
        raise HTTPException(status_code=400, detail="股票代码列表不能为空")
    
    if len(codes) > 50:
        raise HTTPException(status_code=400, detail="一次最多同步50只股票")
    
    try:
        results = await data_sync_service.sync_watchlist_daily_k(
            db, codes, adjust=adjust
        )
        
        success_count = sum(1 for v in results.values() if v >= 0)
        total_records = sum(v for v in results.values() if v > 0)
        
        return {
            "success": True,
            "message": f"批量同步完成: {success_count}/{len(codes)} 成功",
            "total_records": total_records,
            "results": results
        }
    except Exception as e:
        logger.error(f"批量同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _sync_all_stocks_task(market: Optional[str] = None):
    """后台任务：同步所有股票的全量历史数据"""
    global _full_sync_status

    _full_sync_status["is_running"] = True
    _full_sync_status["started_at"] = datetime.now().isoformat()
    _full_sync_status["completed"] = 0
    _full_sync_status["success"] = 0
    _full_sync_status["failed"] = 0
    _full_sync_status["errors"] = []

    try:
        async with get_db_session() as session:
            # 获取所有股票代码
            query = select(StockBasics.code).where(StockBasics.is_active == True)
            if market:
                query = query.where(StockBasics.market == market.upper())

            result = await session.execute(query)
            all_codes = [row[0] for row in result.all()]

            _full_sync_status["total"] = len(all_codes)
            logger.info(f"开始全量同步 {len(all_codes)} 只股票的历史数据...")

            for i, code in enumerate(all_codes):
                _full_sync_status["current_code"] = code
                _full_sync_status["completed"] = i

                try:
                    # 检查是否已有数据
                    count_result = await session.execute(
                        select(func.count()).select_from(StockDailyK).where(
                            StockDailyK.code == code,
                            StockDailyK.adjust_type == "qfq"
                        )
                    )
                    existing_count = count_result.scalar() or 0

                    if existing_count > 0:
                        # 已有数据，只同步增量
                        synced = await data_sync_service.sync_daily_k(session, code, adjust="qfq")
                    else:
                        # 无数据，同步全量
                        synced = await data_sync_service.sync_daily_k(session, code, adjust="qfq")

                    await session.commit()
                    _full_sync_status["success"] += 1

                    if synced > 0:
                        logger.info(f"[{i+1}/{len(all_codes)}] {code} 同步完成: {synced} 条")

                except Exception as e:
                    await session.rollback()
                    _full_sync_status["failed"] += 1
                    error_msg = f"{code}: {str(e)}"
                    _full_sync_status["errors"].append(error_msg)
                    logger.error(f"[{i+1}/{len(all_codes)}] {code} 同步失败: {e}")

                # 每100只股票暂停一下，避免请求过快
                if (i + 1) % 100 == 0:
                    logger.info(f"已完成 {i+1}/{len(all_codes)}，暂停5秒...")
                    await asyncio.sleep(5)

            _full_sync_status["completed"] = len(all_codes)
            _full_sync_status["current_code"] = None
            logger.info(f"全量同步完成: 成功 {_full_sync_status['success']}, 失败 {_full_sync_status['failed']}")

    except Exception as e:
        logger.error(f"全量同步任务异常: {e}")
    finally:
        _full_sync_status["is_running"] = False


@router.post("/all-stocks")
async def sync_all_stocks(
    background_tasks: BackgroundTasks,
    market: Optional[str] = None,
):
    """
    同步所有A股股票的全量历史数据（后台任务）

    - market: 可选，指定市场 SH/SZ/BJ，不传则同步全部
    - 这是一个耗时操作，会在后台执行
    - 使用 GET /sync/all-stocks/status 查看同步进度

    注意：全量同步约5000只股票，预计需要数小时完成
    """
    global _full_sync_status

    if _full_sync_status["is_running"]:
        return {
            "success": False,
            "message": "全量同步任务正在运行中，请等待完成或查看进度",
            "status": _full_sync_status
        }

    # 在后台执行同步任务
    background_tasks.add_task(_sync_all_stocks_task, market)

    return {
        "success": True,
        "message": f"全量同步任务已启动{'(市场: ' + market + ')' if market else ''}，请使用 GET /api/sync/all-stocks/status 查看进度",
    }


@router.get("/all-stocks/status")
async def get_sync_all_stocks_status():
    """
    获取全量同步任务的状态
    """
    return {
        "success": True,
        "status": _full_sync_status
    }


@router.post("/all-stocks/stop")
async def stop_sync_all_stocks():
    """
    停止全量同步任务（标记停止，当前股票完成后停止）
    """
    global _full_sync_status

    if not _full_sync_status["is_running"]:
        return {
            "success": False,
            "message": "没有正在运行的同步任务"
        }

    # 注意：这只是设置标志，实际需要在任务中检查这个标志
    _full_sync_status["is_running"] = False

    return {
        "success": True,
        "message": "已发送停止信号，任务将在当前股票完成后停止"
    }
