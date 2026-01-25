"""
经济指标网关
使用 AKShare 获取宏观经济数据
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging

try:
    import akshare as ak
except ImportError:
    ak = None

from ..base import (
    Market, QuoteData, KlineData, FundamentalData,
    MarketGateway, DataSource
)

logger = logging.getLogger(__name__)


class EconomicSource(DataSource):
    """经济指标数据源 - AKShare"""

    def __init__(self):
        super().__init__("AKShare_Economic")
        self.enabled = ak is not None

        # 常用指标映射
        self.indicators = {
            "GDP": "macro_china_gdp",
            "CPI": "macro_china_cpi",
            "PPI": "macro_china_ppi",
            "PMI": "macro_china_pmi",
            "M0": "macro_china_m0",
            "M1": "macro_china_m1",
            "M2": "macro_china_m2",
            "SHIBOR": "china_shibor",
            "LPR": "china_lpr",
        }

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """经济指标没有实时行情概念，返回空"""
        return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取经济指标历史数据"""
        if not self.enabled:
            return []

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    func = getattr(ak, self.indicators.get(symbol.upper(), ""), None)
                    if not func:
                        logger.warning(f"Unknown economic indicator: {symbol}")
                        return []

                    df = func()

                    klines = []
                    for _, row in df.iterrows():
                        # 获取日期和数值列
                        date_col = df.columns[0]
                        value_col = df.columns[1]

                        klines.append(KlineData(
                            symbol=symbol,
                            datetime=str(row[date_col]),
                            open=float(row[value_col]) if row[value_col] else 0,
                            close=float(row[value_col]) if row[value_col] else 0,
                            high=float(row[value_col]) if row[value_col] else 0,
                            low=float(row[value_col]) if row[value_col] else 0,
                            volume=0,
                            period=period,
                            market="economic"
                        ))
                    return klines
                except Exception as e:
                    logger.error(f"AKShare Economic kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare Economic get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """获取经济指标基本面"""
        return None


class EconomicGateway(MarketGateway):
    """经济指标网关"""

    def __init__(self):
        super().__init__(Market.ECONOMIC)

    async def initialize(self):
        """初始化"""
        source = EconomicSource()
        if source.enabled:
            self.register_source(source)
        logger.info(f"Economic Gateway initialized with {len(self.sources)} sources")

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取经济指标数据"""
        for source in self.sources:
            if not source.enabled:
                continue
            try:
                result = await source.get_kline(symbol, period, start_date, end_date)
                if result:
                    # 过滤日期范围
                    filtered = [
                        k for k in result
                        if start_date <= k.datetime <= end_date
                    ]
                    return filtered
            except Exception as e:
                logger.warning(f"{source.name} get_kline failed: {e}")
                continue
        return []
