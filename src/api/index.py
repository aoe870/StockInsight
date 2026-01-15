"""
大盘指数 API
提供上证指数、深证成指、创业板指等主要指数数据
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
import asyncio
import time

from fastapi import APIRouter, Query, HTTPException
import akshare as ak
import pandas as pd

from src.utils.logger import logger

router = APIRouter(prefix="/index", tags=["大盘指数"])


# 主要指数代码 (akshare格式)
MAIN_INDEXES = {
    "sh000001": {"name": "上证指数", "market": "SH"},
    "sz399001": {"name": "深证成指", "market": "SZ"},
    "sz399006": {"name": "创业板指", "market": "SZ"},
    "sh000300": {"name": "沪深300", "market": "SH"},
    "sh000016": {"name": "上证50", "market": "SH"},
    "sz399005": {"name": "中小100", "market": "SZ"},
}

# 简单缓存：存储指数数据和更新时间
_index_cache: Dict[str, Any] = {
    "data": [],
    "updated_at": 0,
    "ttl": 60,  # 缓存 60 秒
}


def get_index_daily(symbol: str) -> pd.DataFrame:
    """获取指数日线数据"""
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        return df
    except Exception as e:
        logger.error(f"获取指数 {symbol} 数据失败: {e}")
        return pd.DataFrame()


@router.get("/list")
async def get_index_list():
    """获取主要指数列表"""
    return {
        "items": [
            {"code": code, "name": info["name"], "market": info["market"]}
            for code, info in MAIN_INDEXES.items()
        ]
    }


@router.get("/realtime")
async def get_realtime_quote():
    """获取主要指数行情（基于最新日K数据，带缓存）"""
    global _index_cache

    # 检查缓存是否有效
    now = time.time()
    if _index_cache["data"] and (now - _index_cache["updated_at"]) < _index_cache["ttl"]:
        logger.debug("返回缓存的指数数据")
        return {"items": _index_cache["data"]}

    # 如果网络有问题，直接返回空数据，避免阻塞
    try:
        def fetch_single(code: str, info: dict):
            try:
                df = get_index_daily(code)
                if df.empty or len(df) < 2:
                    return None

                # 获取最近两天数据计算涨跌
                latest = df.iloc[-1]
                prev = df.iloc[-2]

                close = float(latest.get("close", 0))
                prev_close = float(prev.get("close", 0))
                change = close - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0

                return {
                    "code": code,
                    "name": info["name"],
                    "current": close,
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "open": float(latest.get("open", 0)),
                    "high": float(latest.get("high", 0)),
                    "low": float(latest.get("low", 0)),
                    "volume": float(latest.get("volume", 0)),
                    "amount": float(latest.get("volume", 0)) * close,
                    "trade_date": str(latest.get("date", ""))[:10],
                }
            except Exception as e:
                logger.warning(f"获取指数 {code} 失败: {e}")
                return None

        # 并行获取，设置超时
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, fetch_single, code, info)
            for code, info in MAIN_INDEXES.items()
        ]

        # 添加超时控制，10秒内完成
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=10.0
        )
        result = [r for r in results if r is not None and not isinstance(r, Exception)]

        # 更新缓存
        if result:
            _index_cache["data"] = result
            _index_cache["updated_at"] = now
            logger.info(f"指数数据已更新缓存: {len(result)} 条")

        return {"items": result}

    except asyncio.TimeoutError:
        logger.warning("获取指数数据超时，返回缓存或空数据")
        return {"items": _index_cache.get("data", [])}
    except Exception as e:
        logger.error(f"获取指数数据异常: {e}")
        return {"items": _index_cache.get("data", [])}


@router.get("/{code}/kline")
async def get_index_kline_data(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(250, ge=1, le=5000, description="返回条数"),
):
    """获取指数K线数据"""
    if code not in MAIN_INDEXES:
        raise HTTPException(status_code=404, detail=f"指数 {code} 不存在")

    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, get_index_daily, code)

        if df.empty:
            return {
                "code": code,
                "name": MAIN_INDEXES[code]["name"],
                "data": []
            }

        # 过滤日期范围
        if start_date or end_date:
            df['date'] = pd.to_datetime(df['date'])
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]

        # 取最近 limit 条
        df = df.tail(limit)

        data = []
        for _, row in df.iterrows():
            data.append({
                "trade_date": str(row.get("date", ""))[:10],
                "open": float(row.get("open", 0)),
                "close": float(row.get("close", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "volume": float(row.get("volume", 0)),
            })

        return {
            "code": code,
            "name": MAIN_INDEXES[code]["name"],
            "data": data
        }
    except Exception as e:
        logger.error(f"获取指数 {code} K线失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

