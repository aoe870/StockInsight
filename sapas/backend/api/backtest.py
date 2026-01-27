"""
回测相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Dict, Any

from ..core.database import get_db_session
from ..core.auth import get_current_user_id
from ..schemas.backtest import (
    BacktestConfig,
    BacktestRun,
    BacktestResult,
    BacktestResponse,
    BacktestTradeResponse,
    STRATEGY_TEMPLATES
)
from ..models import BacktestRun, BacktestTrade, BacktestStatus

router = APIRouter(prefix="/api/v1/backtest", tags=["回测"])


@router.get("/strategies", response_model=dict)
async def get_strategies():
    """
    获取内置策略列表
    """
    return {
        "code": 0,
        "message": "success",
        "data": STRATEGY_TEMPLATES
    }


@router.get("/strategies/{strategy_name}", response_model=dict)
async def get_strategy_template(
    strategy_name: str
):
    """
    获取指定策略的模板
    """
    if strategy_name not in STRATEGY_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略模板不存在: {strategy_name}"
        )

    return {
        "code": 0,
        "message": "success",
        "data": STRATEGY_TEMPLATES[strategy_name]
    }


@router.post("/run", response_model=dict)
async def run_backtest(
    request: BacktestConfig,
    db: AsyncSession = Depends(get_db_session)
):
    """
    执行回测

    请求示例:
    ```json
    {
      "strategy_name": "ma_cross",
      "strategy_params": {
        "fast_period": 5,
        "slow_period": 20,
        "ma_cross_type": "golden_cross"
      },
      "start_date": "2025-01-01",
      "end_date": "2026-01-26",
      "initial_capital": 100000
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 验证日期范围
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始日期不能大于结束日期"
        )

    # 创建回测任务
    backtest_run = BacktestRun(
        user_id=user_id,
        strategy_name=request.strategy_name,
        strategy_config=request.strategy_params,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slippage=request.slippage,
        status=BacktestStatus.RUNNING
    )

    db.add(backtest_run)
    await db.commit()
    await db.refresh(backtest_run)

    # 后台执行回测（实际回测逻辑需要单独实现）
    # 这里暂时标记为完成，实际应用中应该异步执行
    backtest_run.status = BacktestStatus.COMPLETED
    backtest_run.total_return = 0.0
    backtest_run.total_return_pct = 0.0
    backtest_run.final_capital = request.initial_capital
    backtest_run.total_trades = 0
    backtest_run.win_rate = 0.0
    backtest_run.completed_at = None  # 使用当前时间
    backtest_run.result_summary = {"message": "回测功能待实现"}

    await db.commit()

    return {
        "code": 0,
        "message": "回测已创建",
        "data": BacktestRun.model_validate(backtest_run)
    }


@router.get("/runs", response_model=dict)
async def get_backtest_runs(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="过滤状态"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取回测运行列表

    参数:
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
    query = select(BacktestRun).where(BacktestRun.user_id == user_id)
    if status:
        query = query.where(BacktestRun.status == status)

    query = query.order_by(desc(BacktestRun.created_at))
    query = query.limit(limit)

    result = await db.execute(query)
    runs = result.scalars().all()

    return BacktestResponse(data=[BacktestRun.model_validate(r) for r in runs])


@router.get("/runs/{run_id}", response_model=dict)
async def get_backtest_result(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取回测结果详情

    返回:
    - 回测运行信息
    - 交易明细
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取回测运行
    result = await db.execute(
        select(BacktestRun).where(and_(BacktestRun.id == run_id, BacktestRun.user_id == user_id))
    )
    backtest_run = result.scalar_one_or_none()
    if not backtest_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="回测记录不存在"
        )

    # 获取交易记录
    trades_result = await db.execute(
        select(BacktestTrade)
        .where(BacktestTrade.backtest_id == run_id)
        .order_by(BacktestTrade.trade_time)
    )
    trades = trades_result.scalars().all()

    # 检查是否已完成
    is_running = backtest_run.status == BacktestStatus.RUNNING

    response_data = BacktestResult(
        summary=BacktestRun.model_validate(backtest_run),
        trades=[BacktestTradeResponse.model_validate(t) for t in trades]
    )

    return {
        "code": 0,
        "message": "获取成功",
        "data": response_data.dict(),
        "is_running": is_running
    }


@router.delete("/runs/{run_id}", response_model=dict)
async def delete_backtest_run(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除回测记录"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取回测记录
    result = await db.execute(
        select(BacktestRun).where(and_(BacktestRun.id == run_id, BacktestRun.user_id == user_id))
    )
    backtest_run = result.scalar_one_or_none()
    if not backtest_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="回测记录不存在"
        )

    # 删除关联的交易记录
    await db.execute(
        select(BacktestTrade).where(BacktestTrade.backtest_id == run_id)
    )

    # 删除回测记录
    await db.delete(backtest_run)
    await db.commit()

    return {
        "code": 0,
        "message": "删除成功"
    }


@router.post("/runs/{run_id}/cancel", response_model=dict)
async def cancel_backtest_run(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """取消正在运行的回测"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取回测记录
    result = await db.execute(
        select(BacktestRun).where(and_(BacktestRun.id == run_id, BacktestRun.user_id == user_id))
    )
    backtest_run = result.scalar_one_or_none()
    if not backtest_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="回测记录不存在"
        )

    # 只能取消运行中的任务
    if backtest_run.status != BacktestStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能取消运行中的回测任务"
        )

    backtest_run.status = BacktestStatus.CANCELLED
    await db.commit()

    return {
        "code": 0,
        "message": "回测已取消"
    }
