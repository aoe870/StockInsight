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
    """获取主要指数实时行情（使用新浪实时接口）"""
    global _index_cache

    # 检查缓存是否有效（缓存 5 秒，避免频繁请求）
    now = time.time()
    if _index_cache["data"] and (now - _index_cache["updated_at"]) < 5:
        logger.debug("返回缓存的指数数据")
        return {"items": _index_cache["data"]}

    try:
        def fetch_realtime():
            """使用新浪实时行情接口获取所有指数数据"""
            try:
                # 新浪接口返回所有指数，包括上证和深证
                df = ak.stock_zh_index_spot_sina()
                if df.empty:
                    logger.warning("获取实时指数数据返回空")
                    return None

                result = []

                for code, info in MAIN_INDEXES.items():
                    # 新浪接口的代码格式与我们的格式一致
                    row = df[df.iloc[:, 0] == code]

                    if not row.empty:
                        item = row.iloc[0]
                        try:
                            # 新浪接口的列索引（共11列）
                            # 0:代码, 1:名称, 2:最新价, 3:涨跌额, 4:涨跌幅, 5:昨收, 6:今开, 7:最高, 8:最低, 9:成交量, 10:成交额
                            current = float(item.iloc[2])
                            change = float(item.iloc[3])
                            change_pct = float(item.iloc[4])
                            open_price = float(item.iloc[6])
                            high = float(item.iloc[7])
                            low = float(item.iloc[8])
                            volume = float(item.iloc[9])
                            amount = float(item.iloc[10])

                            result.append({
                                "code": code,
                                "name": info["name"],
                                "current": current,
                                "change": round(change, 2),
                                "change_pct": round(change_pct, 2),
                                "open": open_price,
                                "high": high,
                                "low": low,
                                "volume": volume,
                                "amount": amount,
                                "trade_date": datetime.now().strftime("%Y-%m-%d"),
                            })
                        except (ValueError, TypeError, IndexError) as e:
                            logger.warning(f"解析指数 {code} 数据失败: {e}")
                            continue
                    else:
                        logger.debug(f"未找到指数 {code}")

                return result if result else None
            except Exception as e:
                logger.error(f"获取实时指数数据失败: {e}")
                return None

        # 执行获取
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, fetch_realtime),
            timeout=5.0
        )

        # 如果实时接口失败，降级使用日线数据
        if result is None:
            logger.info("实时接口获取失败，降级使用日线数据")
            return await get_realtime_quote_fallback()

        # 更新缓存
        _index_cache["data"] = result
        _index_cache["updated_at"] = now
        logger.info(f"指数实时数据已更新: {len(result)} 条")

        return {"items": result}

    except asyncio.TimeoutError:
        logger.warning("获取实时指数数据超时，返回缓存")
        return {"items": _index_cache.get("data", [])}
    except Exception as e:
        logger.error(f"获取实时指数数据异常: {e}")
        return {"items": _index_cache.get("data", [])}


def get_realtime_quote_fallback():
    """降级方案：使用日线数据（辅助函数，实际逻辑在下面）"""
    # 这是一个占位符，实际逻辑在主函数中处理
    return {"items": []}


async def get_realtime_quote_fallback():
    """降级方案：使用日线数据"""
    global _index_cache

    try:
        def fetch_single(code: str, info: dict):
            try:
                df = get_index_daily(code)
                if df.empty or len(df) < 2:
                    return None

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
                logger.warning(f"获取指数 {code} 日线数据失败: {e}")
                return None

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, fetch_single, code, info)
            for code, info in MAIN_INDEXES.items()
        ]

        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=10.0
        )
        result = [r for r in results if r is not None and not isinstance(r, Exception)]

        if result:
            _index_cache["data"] = result
            _index_cache["updated_at"] = time.time()

        return {"items": result}
    except Exception as e:
        logger.error(f"降级获取指数数据失败: {e}")
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

