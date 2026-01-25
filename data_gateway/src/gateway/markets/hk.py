"""
港股市场网关
使用 AKShare 获取港股数据
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


class HKStockSource(DataSource):
    """港股数据源 - AKShare"""

    def __init__(self):
        super().__init__("AKShare_HK")
        self.enabled = ak is not None

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取港股实时行情"""
        if not self.enabled:
            return {}

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    result = {}
                    for symbol in symbols:
                        # 格式化代码
                        code = symbol.replace("HK", "").replace("hk", "")
                        try:
                            df = ak.stock_hk_spot_em()
                            stock_data = df[df['代码'] == code]
                            if not stock_data.empty:
                                row = stock_data.iloc[0]
                                result[symbol] = QuoteData(
                                    symbol=symbol,
                                    name=row.get('名称'),
                                    price=float(row['最新价']) if row['最新价'] else None,
                                    open=float(row['今开']) if row['今开'] else None,
                                    high=float(row['最高']) if row['最高'] else None,
                                    low=float(row['最低']) if row['最低'] else None,
                                    volume=int(row['成交量']) if row['成交量'] else 0,
                                    change=float(row['涨跌额']) if row['涨跌额'] else None,
                                    change_pct=float(row['涨跌幅']) if row['涨跌幅'] else None,
                                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    market="hk"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to fetch {symbol}: {e}")
                            continue
                    return result
                except Exception as e:
                    logger.error(f"AKShare HK fetch error: {e}")
                    return {}

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare HK get_quote error: {e}")
            return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取港股K线"""
        if not self.enabled:
            return []

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    code = symbol.replace("HK", "").replace("hk", "")
                    period_map = {
                        "daily": "daily",
                        "weekly": "weekly",
                        "monthly": "monthly"
                    }

                    df = ak.stock_hk_hist(
                        symbol=code,
                        period=period_map.get(period, "daily"),
                        start_date=start_date.replace("-", ""),
                        end_date=end_date.replace("-", ""),
                        adjust="qfq"
                    )

                    klines = []
                    for _, row in df.iterrows():
                        klines.append(KlineData(
                            symbol=symbol,
                            datetime=row['日期'].strftime("%Y-%m-%d"),
                            open=float(row['开盘']),
                            close=float(row['收盘']),
                            high=float(row['最高']),
                            low=float(row['最低']),
                            volume=int(row['成交量']),
                            amount=float(row['成交额']) if '成交额' in row else None,
                            period=period,
                            market="hk"
                        ))
                    return klines
                except Exception as e:
                    logger.error(f"AKShare HK kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare HK get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """港股基本面数据 - 暂不支持"""
        return None


class HKGateway(MarketGateway):
    """港股市场网关"""

    def __init__(self):
        super().__init__(Market.HK)

    async def initialize(self):
        """初始化"""
        source = HKStockSource()
        if source.enabled:
            self.register_source(source)
        logger.info(f"HK Gateway initialized with {len(self.sources)} sources")
