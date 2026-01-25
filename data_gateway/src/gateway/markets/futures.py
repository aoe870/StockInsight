"""
期货市场网关
支持黄金、白银等贵金属期货
使用 AKShare 获取期货数据
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


class FuturesSource(DataSource):
    """期货数据源 - AKShare"""

    def __init__(self):
        super().__init__("AKShare_Futures")
        self.enabled = ak is not None

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取期货实时行情"""
        if not self.enabled:
            return {}

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 获取期货实时行情
                    df = ak.futures_zh_spot()
                    result = {}

                    for symbol in symbols:
                        # 查找匹配的合约
                        symbol_data = df[df['symbol'].str.contains(symbol, case=False, na=False)]
                        if not symbol_data.empty:
                            row = symbol_data.iloc[0]
                            result[symbol] = QuoteData(
                                symbol=symbol,
                                name=row.get('name'),
                                price=float(row['last_price']) if row['last_price'] else None,
                                open=float(row['open']) if row['open'] else None,
                                high=float(row['high']) if row['high'] else None,
                                low=float(row['low']) if row['low'] else None,
                                volume=int(row['volume']) if row['volume'] else 0,
                                change=float(row['change']) if row['change'] else None,
                                change_pct=float(row['change_pct']) if row['change_pct'] else None,
                                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                market="futures"
                            )
                    return result
                except Exception as e:
                    logger.error(f"AKShare Futures fetch error: {e}")
                    return {}

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare Futures get_quote error: {e}")
            return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取期货K线"""
        if not self.enabled:
            return []

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    # 周期映射
                    period_map = {
                        "daily": "1",
                        "weekly": "1",
                        "monthly": "1"
                    }

                    # 上海期货交易所
                    df = ak.futures_zh_hist_sina(
                        symbol=symbol,
                        start_date=start_date.replace("-", ""),
                        end_date=end_date.replace("-", "")
                    )

                    klines = []
                    for _, row in df.iterrows():
                        klines.append(KlineData(
                            symbol=symbol,
                            datetime=str(row.index[0]) if hasattr(row.index, 'to_list') else str(row.index),
                            open=float(row['open']),
                            close=float(row['close']),
                            high=float(row['high']),
                            low=float(row['low']),
                            volume=int(row['volume']),
                            amount=float(row['amount']) if 'amount' in row else None,
                            period=period,
                            market="futures"
                        ))
                    return klines
                except Exception as e:
                    logger.error(f"AKShare Futures kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare Futures get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """期货基本面数据"""
        return None


class FuturesGateway(MarketGateway):
    """期货市场网关"""

    def __init__(self):
        super().__init__(Market.FUTURES)

    async def initialize(self):
        """初始化"""
        source = FuturesSource()
        if source.enabled:
            self.register_source(source)
        logger.info(f"Futures Gateway initialized with {len(self.sources)} sources")
