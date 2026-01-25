"""
美股市场网关
使用 AKShare 获取美股数据
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


class USStockSource(DataSource):
    """美股数据源 - AKShare"""

    def __init__(self):
        super().__init__("AKShare_US")
        self.enabled = ak is not None

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取美股实时行情 - 延迟数据"""
        if not self.enabled:
            return {}

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    result = {}
                    for symbol in symbols:
                        try:
                            # 美股实时行情（有延迟）
                            df = ak.stock_us_spot_em()
                            stock_data = df[df['symbol'] == symbol.upper()]
                            if not stock_data.empty:
                                row = stock_data.iloc[0]
                                result[symbol] = QuoteData(
                                    symbol=symbol,
                                    name=row.get('name'),
                                    price=float(row['current']) if row['current'] else None,
                                    open=float(row['open']) if row['open'] else None,
                                    high=float(row['high']) if row['high'] else None,
                                    low=float(row['low']) if row['low'] else None,
                                    volume=int(row['volume']) if row['volume'] else 0,
                                    change=float(row['ch']) if row['ch'] else None,
                                    change_pct=float(row['percent']) if row['percent'] else None,
                                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    market="us"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to fetch {symbol}: {e}")
                            continue
                    return result
                except Exception as e:
                    logger.error(f"AKShare US fetch error: {e}")
                    return {}

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare US get_quote error: {e}")
            return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取美股K线"""
        if not self.enabled:
            return []

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    period_map = {
                        "daily": "daily",
                        "weekly": "weekly",
                        "monthly": "monthly"
                    }

                    df = ak.stock_us_hist(
                        symbol=symbol.upper(),
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
                            market="us"
                        ))
                    return klines
                except Exception as e:
                    logger.error(f"AKShare US kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare US get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """美股基本面数据 - 暂不支持"""
        return None


class USGateway(MarketGateway):
    """美股市场网关"""

    def __init__(self):
        super().__init__(Market.US)

    async def initialize(self):
        """初始化"""
        source = USStockSource()
        if source.enabled:
            self.register_source(source)
        logger.info(f"US Gateway initialized with {len(self.sources)} sources")
