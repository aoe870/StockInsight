"""
指标选股 API
实现基于技术指标的股票筛选功能
支持预设策略和自定义公式
"""

import asyncio
import re
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import numpy as np

from src.core.database import get_db, get_db_session
from src.core.formula_engine import formula_engine, FormulaContext
from src.models.stock import StockBasics, StockDailyK
from src.utils.logger import logger

router = APIRouter(prefix="/screener", tags=["指标选股"])

# 选股任务状态
_screener_status: Dict[str, Any] = {
    "is_running": False,
    "started_at": None,
    "total": 0,
    "processed": 0,
    "matched": 0,
    "results": [],
    "strategy": None,
    "formula": None,
    "error": None,
}

# 预设选股策略
PRESET_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "volume_contraction": {
        "id": "volume_contraction",
        "name": "地量回调",
        "description": "今日缩量（地量信号），但前期有放量活跃迹象，适合捕捉缩量回调后的反弹机会",
        "category": "量能",
        "formula": """
N := 120;
VOL120 := MA(VOL, N);
COND1 := VOL > VOL120;
COND2 := COUNT(COND1, 5) >= 3;
黄金地量 := VOL < 0.3 * VOL120;
地量信号 := VOL < 0.8 * VOL120 OR 黄金地量;
选股 := 地量信号 AND REF(COND2, 1) AND REF(COUNT(COND1, 5) >= 3, 1);
""",
        "params": [
            {"key": "N", "name": "均量周期", "default": 120, "min": 20, "max": 250}
        ],
        "data_days": 150,
    },
    "golden_cross_macd": {
        "id": "golden_cross_macd",
        "name": "MACD金叉",
        "description": "MACD指标DIF上穿DEA形成金叉",
        "category": "趋势",
        "formula": """
EMA12 := EMA(CLOSE, 12);
EMA26 := EMA(CLOSE, 26);
DIF := EMA12 - EMA26;
DEA := EMA(DIF, 9);
选股 := CROSS(DIF, DEA) AND DIF < 0;
""",
        "params": [],
        "data_days": 60,
    },
    "breakout_volume": {
        "id": "breakout_volume",
        "name": "放量突破",
        "description": "股价突破N日新高且成交量放大",
        "category": "突破",
        "formula": """
N := 20;
VOL_MA := MA(VOL, 5);
HIGH_N := HHV(HIGH, N);
选股 := CLOSE > REF(HIGH_N, 1) AND VOL > 2 * VOL_MA;
""",
        "params": [
            {"key": "N", "name": "突破周期", "default": 20, "min": 5, "max": 60}
        ],
        "data_days": 60,
    },
    "ma_support": {
        "id": "ma_support",
        "name": "均线支撑",
        "description": "股价回踩均线获得支撑",
        "category": "趋势",
        "formula": """
N := 20;
MA_N := MA(CLOSE, N);
选股 := LOW < MA_N AND CLOSE > MA_N AND CLOSE > OPEN;
""",
        "params": [
            {"key": "N", "name": "均线周期", "default": 20, "min": 5, "max": 120}
        ],
        "data_days": 150,
    },
    "oversold_rsi": {
        "id": "oversold_rsi",
        "name": "RSI超卖反弹",
        "description": "RSI从超卖区域反弹",
        "category": "震荡",
        "formula": """
N := 14;
LC := REF(CLOSE, 1);
DIFF := CLOSE - LC;
UP := IF(DIFF > 0, DIFF, 0);
DN := IF(DIFF < 0, ABS(DIFF), 0);
SUMUP := SMA(UP, N, 1);
SUMDN := SMA(DN, N, 1);
RSI := SUMUP / (SUMUP + SUMDN) * 100;
选股 := REF(RSI, 1) < 30 AND RSI > REF(RSI, 1);
""",
        "params": [
            {"key": "N", "name": "RSI周期", "default": 14, "min": 6, "max": 24}
        ],
        "data_days": 60,
    },
    "kdj_golden_cross": {
        "id": "kdj_golden_cross",
        "name": "KDJ金叉",
        "description": "KDJ指标K线上穿D线",
        "category": "震荡",
        "formula": """
N := 9;
RSV := (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100;
K := SMA(RSV, 3, 1);
D := SMA(K, 3, 1);
选股 := CROSS(K, D) AND K < 50;
""",
        "params": [
            {"key": "N", "name": "KDJ周期", "default": 9, "min": 5, "max": 21}
        ],
        "data_days": 60,
    },
}


def calculate_volume_signals(df: pd.DataFrame, n: int = 120) -> Dict[str, Any]:
    """
    计算成交量信号
    
    Args:
        df: 包含 volume 列的 DataFrame，按日期升序排列
        n: 均量线周期，默认120日
    
    Returns:
        包含各种信号的字典
    """
    if len(df) < n + 5:
        return None
    
    vol = df['volume'].values
    
    # VOL120: 120日均量线
    vol_ma = pd.Series(vol).rolling(window=n).mean().values
    
    # 获取最近几天的数据
    latest_vol = vol[-1]
    latest_vol_ma = vol_ma[-1]
    
    if np.isnan(latest_vol_ma) or latest_vol_ma == 0:
        return None
    
    # COND1: 当日成交量大于120日均量线
    cond1_today = latest_vol > latest_vol_ma
    
    # COND1 最近5天的情况
    cond1_last5 = [vol[-i] > vol_ma[-i] for i in range(1, 6) if not np.isnan(vol_ma[-i])]
    cond1_count_last5 = sum(cond1_last5) if cond1_last5 else 0
    
    # COND2: 最近5日内至少有3天放量 (用于昨天的判断)
    cond1_ref1_last5 = [vol[-i] > vol_ma[-i] for i in range(2, 7) if -i >= -len(vol) and not np.isnan(vol_ma[-i])]
    cond2_ref1 = sum(cond1_ref1_last5) >= 3 if len(cond1_ref1_last5) >= 5 else False
    
    # 黄金地量: VOL < 0.3 * VOL120
    golden_low_vol = latest_vol < 0.3 * latest_vol_ma
    
    # 地量信号: VOL < 0.8 * VOL120 OR 黄金地量
    low_vol_signal = (latest_vol < 0.8 * latest_vol_ma) or golden_low_vol
    
    # REF(COUNT(COND1, 5) >= 3, 1): 昨天的最近5天内有>=3天放量
    ref_cond1_count = sum(cond1_ref1_last5) >= 3 if len(cond1_ref1_last5) >= 5 else False
    
    # 选股条件: 地量信号 AND REF(COND2, 1) AND REF(COUNT(COND1, 5) >= 3, 1)
    is_match = low_vol_signal and cond2_ref1 and ref_cond1_count
    
    return {
        "vol": int(latest_vol),
        "vol_ma120": int(latest_vol_ma),
        "vol_ratio": round(latest_vol / latest_vol_ma, 3),
        "is_low_vol": low_vol_signal,
        "is_golden_low": golden_low_vol,
        "prev_active_days": sum(cond1_ref1_last5) if cond1_ref1_last5 else 0,
        "is_match": is_match,
    }


@router.get("/strategies")
async def get_strategies():
    """获取可用的选股策略列表"""
    strategies = []
    for sid, s in PRESET_STRATEGIES.items():
        strategies.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "category": s["category"],
            "params": s["params"],
            "formula": s["formula"].strip(),
        })
    return {"strategies": strategies}


@router.get("/strategies/{strategy_id}")
async def get_strategy_detail(strategy_id: str):
    """获取策略详情"""
    if strategy_id not in PRESET_STRATEGIES:
        raise HTTPException(status_code=404, detail="策略不存在")
    return PRESET_STRATEGIES[strategy_id]


@router.get("/status")
async def get_screener_status():
    """获取选股任务状态"""
    return {"status": _screener_status}


@router.post("/stop")
async def stop_screener():
    """停止选股任务"""
    global _screener_status
    if _screener_status["is_running"]:
        _screener_status["is_running"] = False
        return {"success": True, "message": "已发送停止信号"}
    return {"success": False, "message": "没有正在运行的任务"}


def apply_params_to_formula(formula: str, params: Dict[str, Any]) -> str:
    """将参数应用到公式中"""
    for key, value in params.items():
        # 替换 N := 120; 这样的定义
        formula = re.sub(
            rf'{key}\s*:=\s*\d+',
            f'{key} := {value}',
            formula,
            flags=re.IGNORECASE
        )
    return formula


async def _run_formula_screener(
    formula: str,
    strategy_id: str,
    market: Optional[str] = None,
    data_days: int = 150,
):
    """通用公式选股"""
    global _screener_status

    _screener_status["is_running"] = True
    _screener_status["started_at"] = date.today().isoformat()
    _screener_status["processed"] = 0
    _screener_status["matched"] = 0
    _screener_status["results"] = []
    _screener_status["strategy"] = strategy_id
    _screener_status["formula"] = formula
    _screener_status["error"] = None

    try:
        async with get_db_session() as session:
            # 获取所有股票
            query = select(StockBasics).where(StockBasics.is_active == True)
            if market:
                query = query.where(StockBasics.market == market.upper())

            result = await session.execute(query)
            stocks = result.scalars().all()
            _screener_status["total"] = len(stocks)

            logger.info(f"开始选股: {strategy_id}, 共 {len(stocks)} 只股票")

            for i, stock in enumerate(stocks):
                if not _screener_status["is_running"]:
                    logger.info("选股任务被停止")
                    break

                _screener_status["processed"] = i + 1

                try:
                    # 获取K线数据
                    kline_query = select(StockDailyK).where(
                        StockDailyK.code == stock.code,
                        StockDailyK.adjust_type == "qfq"
                    ).order_by(StockDailyK.trade_date.desc()).limit(data_days)

                    kline_result = await session.execute(kline_query)
                    klines = kline_result.scalars().all()

                    if len(klines) < 30:  # 至少需要30天数据
                        continue

                    # 转为 DataFrame（反转为升序）
                    df = pd.DataFrame([{
                        "open": float(k.open_price or 0),
                        "close": float(k.close_price or 0),
                        "high": float(k.high_price or 0),
                        "low": float(k.low_price or 0),
                        "volume": float(k.volume or 0),
                        "amount": float(k.amount or 0),
                    } for k in reversed(klines)])

                    # 执行公式
                    ctx = FormulaContext(df=df)
                    result_val = formula_engine.parse_and_execute(formula, ctx)
                    is_match = formula_engine.get_last_value(result_val)

                    if is_match:
                        latest = klines[0]
                        prev = klines[1] if len(klines) > 1 else None

                        close = float(latest.close_price or 0)
                        prev_close = float(prev.close_price or close) if prev else close
                        change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0

                        _screener_status["results"].append({
                            "code": stock.code,
                            "name": stock.name,
                            "market": stock.market,
                            "industry": stock.industry,
                            "close": round(close, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": int(latest.volume or 0),
                            "trade_date": str(latest.trade_date),
                        })
                        _screener_status["matched"] += 1
                        logger.info(f"匹配: {stock.code} {stock.name}")

                except Exception as e:
                    # 单个股票出错不中断整体
                    logger.debug(f"处理 {stock.code} 出错: {e}")
                    continue

                # 每100只暂停一下
                if (i + 1) % 100 == 0:
                    await asyncio.sleep(0.1)

            logger.info(f"选股完成: 共筛选 {_screener_status['matched']} 只")

    except Exception as e:
        logger.error(f"选股任务异常: {e}")
        _screener_status["error"] = str(e)
    finally:
        _screener_status["is_running"] = False


class RunScreenerRequest(BaseModel):
    """运行选股请求"""
    strategy_id: Optional[str] = None  # 预设策略ID
    formula: Optional[str] = None  # 自定义公式
    params: Optional[Dict[str, Any]] = None  # 参数
    market: Optional[str] = None  # 市场筛选


@router.post("/run")
async def run_screener(
    background_tasks: BackgroundTasks,
    request: RunScreenerRequest,
):
    """
    运行选股

    可以选择预设策略或自定义公式:
    - strategy_id: 使用预设策略
    - formula: 使用自定义公式
    - params: 自定义参数（会替换公式中的默认值）
    """
    global _screener_status

    if _screener_status["is_running"]:
        return {
            "success": False,
            "message": "已有选股任务在运行",
            "status": _screener_status
        }

    # 确定使用的公式
    if request.strategy_id:
        if request.strategy_id not in PRESET_STRATEGIES:
            raise HTTPException(status_code=400, detail=f"未知策略: {request.strategy_id}")
        strategy = PRESET_STRATEGIES[request.strategy_id]
        formula = strategy["formula"]
        data_days = strategy.get("data_days", 150)
        strategy_id = request.strategy_id
    elif request.formula:
        formula = request.formula
        data_days = 150
        strategy_id = "custom"
    else:
        raise HTTPException(status_code=400, detail="需要指定 strategy_id 或 formula")

    # 应用参数
    if request.params:
        formula = apply_params_to_formula(formula, request.params)

    # 验证公式（测试解析）
    try:
        test_df = pd.DataFrame({
            'open': [1.0] * 50,
            'high': [1.0] * 50,
            'low': [1.0] * 50,
            'close': [1.0] * 50,
            'volume': [1000.0] * 50,
            'amount': [10000.0] * 50,
        })
        ctx = FormulaContext(df=test_df)
        formula_engine.parse_and_execute(formula, ctx)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"公式语法错误: {e}")

    background_tasks.add_task(
        _run_formula_screener,
        formula,
        strategy_id,
        request.market,
        data_days
    )

    return {
        "success": True,
        "message": "选股任务已启动",
        "strategy_id": strategy_id,
    }


@router.get("/results")
async def get_screener_results(
    sort_by: str = Query("vol_ratio", description="排序字段"),
    sort_order: str = Query("asc", description="排序方向: asc/desc"),
):
    """获取选股结果"""
    results = _screener_status.get("results", [])

    if results and sort_by:
        reverse = sort_order.lower() == "desc"
        results = sorted(results, key=lambda x: x.get(sort_by, 0), reverse=reverse)

    return {
        "total": len(results),
        "strategy": _screener_status.get("strategy"),
        "items": results
    }

