"""
回测相关API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.schemas.backtest import (
    BacktestConfigRequest,
    BacktestResultResponse,
    StrategyInfo
)
from src.services.backtest import BacktestEngine, BacktestConfig, DataLoader, StrategyFactory
from src.core.database import get_db

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/strategies", response_model=List[StrategyInfo])
async def get_strategies():
    """
    获取所有可用策略列表

    返回策略信息，包括名称、描述、参数等
    """
    strategies = StrategyFactory.get_strategy_info()

    return [
        StrategyInfo(
            name=s["name"],
            display_name=s["display_name"],
            description=s["description"],
            category=s["category"],
            params=s["params"]
        )
        for s in strategies
    ]


@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest(
    request: BacktestConfigRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    运行回测

    参数:
        request: 回测配置请求

    返回:
        回测结果
    """
    try:
        # 1. 加载股票数据
        if request.stock_pool:
            # 加载指定股票池
            stock_data = await DataLoader.load_stock_data(
                codes=request.stock_pool,
                start_date=request.start_date,
                end_date=request.end_date,
                session=db
            )
        else:
            # 加载所有股票
            stock_data = await DataLoader.load_all_stocks(
                start_date=request.start_date,
                end_date=request.end_date,
                session=db
            )

        if not stock_data:
            raise HTTPException(status_code=400, detail="没有可用的股票数据")

        # 2. 构建回测配置
        config = BacktestConfig(
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=request.initial_cash,
            commission=request.commission,
            slippage_perc=request.slippage,
            max_positions=request.max_positions,
            position_size=request.position_size,
            hold_days=request.hold_days,
            rebalance_freq=request.rebalance_freq,
            stock_pool=request.stock_pool,
        )

        # 3. 运行回测
        engine = BacktestEngine()
        result = engine.run(config, stock_data)

        # 4. 构建响应
        if result.status == "error":
            raise HTTPException(status_code=400, detail=result.error)

        # 格式化交易记录
        formatted_trades = []
        for trade in result.trades:
            # 获取股票名称
            code = trade.get("code", "")
            stock_info = await _get_stock_info(code, db)

            formatted_trades.append({
                "date": trade.get("date"),
                "code": code,
                "name": stock_info.get("name", ""),
                "action": trade.get("action"),
                "price": trade.get("price"),
                "shares": trade.get("shares"),
                "amount": trade.get("amount"),
                "profit": trade.get("profit"),
            })

        # 构建响应
        response = BacktestResultResponse(
            config=request,
            performance={
                "initial_cash": result.initial_cash,
                "final_cash": result.final_cash,
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "max_drawdown_duration": result.max_drawdown_duration,
                "total_trades": result.total_trades,
                "profitable_trades": result.profitable_trades,
                "losing_trades": result.losing_trades,
                "win_rate": result.win_rate,
                "avg_profit": result.avg_profit,
                "avg_loss": result.avg_loss,
                "profit_loss_ratio": result.profit_loss_ratio,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "trading_days": result.trading_days,
            },
            equity_curve=result.equity_curve,
            trades=formatted_trades,
            daily_returns=result.daily_returns,
            kline_data=result.kline_data if result.kline_data else None,
            status=result.status,
            error=result.error,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测执行失败: {str(e)}")


async def _get_stock_info(code: str, db: AsyncSession) -> dict:
    """获取股票信息"""
    from sqlalchemy import select
    from src.models.stock import StockBasics

    query = select(StockBasics.code, StockBasics.name).where(
        StockBasics.code == code
    )
    result = await db.execute(query)
    stock = result.first()

    if stock:
        return {"code": stock[0], "name": stock[1]}
    return {"code": code, "name": ""}


@router.get("/stock-list")
async def get_stock_list(
    market: str = None,
    industry: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票列表（用于构建股票池）

    参数:
        market: 市场筛选 (SH/SZ)
        industry: 行业筛选

    返回:
        股票列表
    """
    try:
        stock_list = await DataLoader.get_stock_list(db, market, industry)
        return {"items": stock_list, "total": len(stock_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票列表失败: {str(e)}")
