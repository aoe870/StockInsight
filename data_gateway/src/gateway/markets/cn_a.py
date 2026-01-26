"""
A股市场网关
实时数据: 缅A平台（五档）、AKShare
历史数据: BaoStock
资金流向: 缅A平台
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import logging
import os

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("AKShare not installed")

try:
    import baostock as bs
except ImportError:
    bs = None
    logging.warning("BaoStock not installed")

from ..base import (
    Market, QuoteData, KlineData, FundamentalData,
    MarketGateway, DataSource
)
from ..sources.miana_source import MianaSource
from ...config import settings

logger = logging.getLogger(__name__)


class AKShareSource(DataSource):
    """AKShare 数据源 - 用于实时行情"""

    def __init__(self):
        super().__init__("AKShare")
        self.enabled = ak is not None

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取实时行情"""
        if not self.enabled:
            return {}

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    df = ak.stock_zh_a_spot_em()
                    result = {}
                    for _, row in df.iterrows():
                        code = row['代码']
                        if code in symbols:
                            result[code] = QuoteData(
                                symbol=code,
                                name=row['名称'],
                                price=float(row['最新价']) if row['最新价'] else None,
                                open=float(row['今开']) if row['今开'] else None,
                                high=float(row['最高']) if row['最高'] else None,
                                low=float(row['最低']) if row['最低'] else None,
                                volume=int(row['成交量']) if row['成交量'] else 0,
                                amount=float(row['成交额']) if row['成交额'] else 0,
                                change=float(row['涨跌额']) if row['涨跌额'] else None,
                                change_pct=float(row['涨跌幅']) if row['涨跌幅'] else None,
                                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                market="cn_a"
                            )
                    return result
                except Exception as e:
                    logger.error(f"AKShare fetch error: {e}")
                    return {}

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_quote error: {e}")
            return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据"""
        # AKShare 也提供历史数据，但优先使用 BaoStock
        return await self._fetch_kline(symbol, period, start_date, end_date)

    async def _fetch_kline(self, symbol: str, period: str,
                          start_date: str, end_date: str) -> List[KlineData]:
        """AKShare K线获取"""
        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    adj = "qfq"  # 前复权

                    # 分钟级 K 线使用 AKShare 的分钟数据接口
                    if period in ["1m", "5m", "15m", "30m", "60m"]:
                        # 分钟级数据：使用新浪财经的分钟数据（更稳定）
                        df = ak.stock_zh_a_hist_min_sina(
                            symbol=symbol,
                            period=period.replace("m", ""),  # 1, 5, 15, 30, 60
                            start_date=start_date.replace("-", ""),
                            end_date=end_date.replace("-", ""),
                            adjust=adj
                        )
                    else:
                        # 日线及以上：使用东方财经数据（数据更全面）
                        period_map = {
                            "daily": "daily",
                            "weekly": "weekly",
                            "monthly": "monthly"
                        }
                        df = ak.stock_zh_a_hist(
                            symbol=symbol,
                            period=period_map.get(period, "daily"),
                            start_date=start_date.replace("-", ""),
                            end_date=end_date.replace("-", ""),
                            adjust=adj
                        )

                    klines = []
                    for _, row in df.iterrows():
                        # 处理日期列（分钟数据可能有多列）
                        if period in ["1m", "5m", "15m", "30m", "60m"]:
                            # 分钟数据：日期格式 "2026-01-26 10:30:00"
                            dt_str = str(row.index[0]) if hasattr(row.index, 'to_list') else str(row.index)
                            # 解析日期时间
                            try:
                                if ' ' in dt_str:
                                    dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                                    dt_formatted = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                                else:
                                    dt_formatted = dt_str
                            except ValueError:
                                dt_formatted = dt_str
                        else:
                            # 日线及以上：日期格式 "2026-01-26"
                            dt_formatted = row['日期'].strftime("%Y-%m-%d")

                        klines.append(KlineData(
                            symbol=symbol,
                            datetime=dt_formatted,
                            open=float(row['开盘']),
                            close=float(row['收盘']),
                            high=float(row['最高']),
                            low=float(row['最低']),
                            volume=int(row['成交量']),
                            amount=float(row['成交额']) if '成交额' in row else None,
                            period=period,
                            market="cn_a"
                        ))
                    return klines
                except Exception as e:
                    logger.error(f"AKShare kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"AKShare get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """获取基本面数据"""
        return None


class BaoStockSource(DataSource):
    """BaoStock 数据源 - 用于历史数据和基本面"""

    def __init__(self):
        super().__init__("BaoStock")
        self.enabled = bs is not None
        self._lg = None

    def _connect(self):
        """建立连接"""
        if not self.enabled:
            return
        if self._lg is None:
            self._lg = bs.login()

    def _format_code(self, code: str) -> str:
        """格式化代码为 BaoStock 格式"""
        if code.startswith("6"):
            return f"sh.{code}"
        elif code.startswith(("0", "3")):
            return f"sz.{code}"
        return code

    def _parse_code(self, code: str) -> str:
        """解析 BaoStock 代码为普通格式"""
        return code.replace("sh.", "").replace("sz.", "")

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """BaoStock 不支持实时行情，返回空"""
        return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据"""
        if not self.enabled:
            return []

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    self._connect()

                    # 周期映射
                    period_map = {
                        "daily": "d",
                        "weekly": "w",
                        "monthly": "m"
                    }
                    bs_period = period_map.get(period, "d")

                    # 获取数据
                    rs = bs.query_history_k_data_plus(
                        self._format_code(symbol),
                        "date,open,high,low,close,volume,amount",
                        start_date=start_date,
                        end_date=end_date,
                        frequency=bs_period,
                        adjustflag="2"  # 2=前复权
                    )

                    klines = []
                    while (rs.error_code == '0') & rs.next():
                        row = rs.get_row_data()
                        klines.append(KlineData(
                            symbol=symbol,
                            datetime=row[0],
                            open=float(row[1]),
                            close=float(row[4]),
                            high=float(row[2]),
                            low=float(row[3]),
                            volume=int(row[5]),
                            amount=float(row[6]) if row[6] else None,
                            period=period,
                            market="cn_a"
                        ))
                    return klines

                except Exception as e:
                    logger.error(f"BaoStock kline error: {e}")
                    return []

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"BaoStock get_kline error: {e}")
            return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """获取基本面数据"""
        if not self.enabled:
            return None

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                try:
                    self._connect()

                    # 获取基本面信息
                    rs = bs.query_stock_basic(self._format_code(symbol))
                    if rs.error_code != '0':
                        return None

                    return FundamentalData(
                        symbol=symbol,
                        market="cn_a"
                    )

                except Exception as e:
                    logger.error(f"BaoStock fundamentals error: {e}")
                    return None

            return await loop.run_in_executor(None, _fetch)

        except Exception as e:
            logger.error(f"BaoStock get_fundamentals error: {e}")
            return None

    def __del__(self):
        """清理连接"""
        if self._lg:
            bs.logout()


class ChinaAGateway(MarketGateway):
    """A股市场网关"""

    def __init__(self):
        super().__init__(Market.CN_A)
        self.akshare = AKShareSource()
        self.baostock = BaoStockSource()

        # 缅A平台数据源（需要token）
        self.miana = MianaSource(token=settings.miana_token) if settings.miana_token else None

    async def initialize(self):
        """初始化"""
        # 注册数据源
        if self.miana and self.miana.enabled:
            self.register_source(self.miana)
            logger.info("  - Miana平台 (实时五档、资金流向) [优先]")
        if self.akshare.enabled:
            self.register_source(self.akshare)
            logger.info("  - AKShare (备用实时)")
        if self.baostock.enabled:
            self.register_source(self.baostock)
            logger.info("  - BaoStock (历史数据)")

        logger.info(f"China A Gateway initialized with {len(self.sources)} sources")

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """
        获取实时行情 - 优先缅A平台（五档数据）

        数据源优先级:
        1. 缅A平台（实时五档、完整数据）
        2. AKShare（备用）
        """
        # 优先使用缅A平台（如果有token且启用）
        if self.miana and self.miana.enabled:
            try:
                result = await self.miana.get_quote(symbols, market="cn_a")
                if result:
                    logger.info(f"Got quotes from Miana (with 5-level depth)")
                    return result
            except Exception as e:
                logger.warning(f"Miana get_quote failed: {e}, fallback to AKShare")

        # 备用 AKShare
        return await self.akshare.get_quote(symbols)

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据 - 优先 BaoStock"""
        # 历史数据优先使用 BaoStock
        if self.baostock.enabled:
            result = await self.baostock.get_kline(symbol, period, start_date, end_date)
            if result:
                return result

        # 备用 AKShare
        if self.akshare.enabled:
            return await self.akshare.get_kline(symbol, period, start_date, end_date)

        return []

    async def get_money_flow(self, symbol: str, date: str = None) -> Optional[Dict[str, Any]]:
        """
        获取资金流向数据 - 缅A平台

        提供详细的资金流向数据：
        - 大单、中单、小单分类
        - 净流入/流出统计
        - 资金流向排名
        """
        if not self.miana or not self.miana.enabled:
            logger.warning("Miana source not available for money flow")
            return None

        try:
            result = await self.miana.get_money_flow(symbol, date, market="cn_a")
            return result
        except Exception as e:
            logger.error(f"Miana get_money_flow error: {e}")
            return None

    async def get_sector_realtime(self, sector_type: str = "industry") -> List[Dict[str, Any]]:
        """
        获取板块实时行情 - 缅A平台

        参数:
            sector_type: 板块类型
                - industry: 行业板块
                - concept: 概念板块
        """
        if not self.miana or not self.miana.enabled:
            logger.warning("Miana source not available for sector data")
            return []

        try:
            result = await self.miana.get_sector_realtime(sector_type)
            return result
        except Exception as e:
            logger.error(f"Miana get_sector_realtime error: {e}")
            return []
