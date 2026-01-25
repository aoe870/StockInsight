"""
AKShare 数据源封装
作为备用数据源，提供历史数据和基本面数据
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
import logging
import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("AKShare not installed, run: pip install akshare")

from ..data_source_base import DataSourceBase, DataSourcePriority

logger = logging.getLogger(__name__)


class AKShareSource(DataSourceBase):
    """
    AKShare 数据源
    延迟: 3-15分钟
    免费额度: 无限制
    用途: 备用数据源、历史数据、基本面数据
    """

    def __init__(self):
        super().__init__(
            name="AKShare",
            priority=DataSourcePriority.FALLBACK
        )
        if ak is None:
            logger.warning("AKShare not available")

    async def get_realtime_quote(self, codes: List[str]) -> Dict[str, Any]:
        """
        获取实时行情
        AKShare 的实时数据来自东方财富，有延迟
        """
        if ak is None:
            raise Exception("AKShare not installed")

        try:
            # 使用东方财富实时行情
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 获取沪深实时行情
                    df = ak.stock_zh_a_spot_em()
                    result = {}
                    for _, row in df.iterrows():
                        code = row['代码']
                        if code in codes:
                            result[code] = {
                                "name": row['名称'],
                                "price": float(row['最新价']),
                                "open": float(row['今开']),
                                "high": float(row['最高']),
                                "low": float(row['最低']),
                                "volume": int(row['成交量']),
                                "amount": float(row['成交额']),
                                "change": float(row['涨跌额']),
                                "change_pct": float(row['涨跌幅']),
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                    return result
                except Exception as e:
                    logger.error(f"AKShare fetch error: {e}")
                    return {}

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_realtime_quote error: {e}")
            raise

    async def get_minute_kline(self, code: str) -> List[Dict[str, Any]]:
        """
        获取分钟K线
        """
        if ak is None:
            raise Exception("AKShare not installed")

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 获取今日分时数据
                    df = ak.stock_zh_a_hist_min_em(symbol=code, period="1", adjust="")
                    klines = []
                    for _, row in df.iterrows():
                        klines.append({
                            "datetime": row['时间'].strftime("%Y-%m-%d %H:%M:%S"),
                            "open": float(row['开盘']),
                            "close": float(row['收盘']),
                            "high": float(row['最高']),
                            "low": float(row['最低']),
                            "volume": int(row['成交量']),
                            "amount": float(row['成交额']),
                        })
                    return klines
                except Exception as e:
                    logger.error(f"AKShare minute kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_minute_kline error: {e}")
            raise

    async def get_daily_kline(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取日K线
        AKShare 的日K线数据最完整
        """
        if ak is None:
            raise Exception("AKShare not installed")

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 获取历史行情
                    df = ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date.replace("-", ""),
                        end_date=end_date.replace("-", ""),
                        adjust="qfq"  # 前复权
                    )
                    klines = []
                    for _, row in df.iterrows():
                        klines.append({
                            "date": row['日期'].strftime("%Y-%m-%d"),
                            "open": float(row['开盘']),
                            "close": float(row['收盘']),
                            "high": float(row['最高']),
                            "low": float(row['最低']),
                            "volume": int(row['成交量']),
                            "amount": float(row['成交额']),
                            "change_pct": float(row['涨跌幅']),
                            "change": float(row['涨跌额']),
                            "turnover": float(row['换手率']),
                        })
                    return klines
                except Exception as e:
                    logger.error(f"AKShare daily kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_daily_kline error: {e}")
            raise

    async def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取股票列表"""
        if ak is None:
            raise Exception("AKShare not installed")

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 获取A股列表
                    df = ak.stock_info_a_code_name()
                    stocks = []
                    for _, row in df.iterrows():
                        stocks.append({
                            "code": row['code'],
                            "name": row['name'],
                        })
                    return stocks
                except Exception as e:
                    logger.error(f"AKShare stock list error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_stock_list error: {e}")
            raise
