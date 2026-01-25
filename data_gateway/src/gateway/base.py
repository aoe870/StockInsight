"""
数据网关基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class Market(str, Enum):
    """支持的市场"""
    CN_A = "cn_a"        # A股
    HK = "hk"            # 港股
    US = "us"            # 美股
    FUTURES = "futures"  # 期货
    ECONOMIC = "economic"  # 经济指标


class Period(str, Enum):
    """K线周期"""
    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    MIN_60 = "60m"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class QuoteData:
    """统一行情数据格式"""
    symbol: str                    # 代码
    name: Optional[str] = None     # 名称
    price: Optional[float] = None  # 最新价
    open: Optional[float] = None   # 开盘价
    high: Optional[float] = None   # 最高价
    low: Optional[float] = None    # 最低价
    volume: Optional[int] = None   # 成交量
    amount: Optional[float] = None # 成交额
    change: Optional[float] = None # 涨跌额
    change_pct: Optional[float] = None  # 涨跌幅
    bid: Optional[float] = None    # 买一价
    ask: Optional[float] = None    # 卖一价
    timestamp: Optional[str] = None  # 时间戳
    market: Optional[str] = None   # 市场


@dataclass
class KlineData:
    """统一K线数据格式"""
    symbol: str                    # 代码
    datetime: str                  # 时间
    open: float                    # 开盘价
    close: float                   # 收盘价
    high: float                    # 最高价
    low: float                     # 最低价
    volume: int                    # 成交量
    amount: Optional[float] = None # 成交额
    period: str = "daily"          # 周期
    market: str = "cn_a"           # 市场


@dataclass
class FundamentalData:
    """统一基本面数据格式"""
    symbol: str                    # 代码
    name: Optional[str] = None     # 名称
    market: str = "cn_a"           # 市场
    # 财务数据
    revenue: Optional[float] = None      # 营业收入
    net_profit: Optional[float] = None   # 净利润
    total_assets: Optional[float] = None # 总资产
    total_liab: Optional[float] = None   # 总负债
    eps: Optional[float] = None          # 每股收益
    bvps: Optional[float] = None         # 每股净资产
    # 估值数据
    pe: Optional[float] = None           # 市盈率
    pb: Optional[float] = None           # 市净率
    market_cap: Optional[float] = None   # 总市值
    circulating_cap: Optional[float] = None  # 流通市值


class DataSource(ABC):
    """数据源基类"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    @abstractmethod
    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取实时行情"""
        pass

    @abstractmethod
    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据"""
        pass

    @abstractmethod
    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """获取基本面数据"""
        pass

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self.get_quote(["000001"])
            return len(result) > 0
        except Exception as e:
            logger.warning(f"{self.name} health check failed: {e}")
            return False


class MarketGateway(ABC):
    """市场网关基类"""

    def __init__(self, market: Market):
        self.market = market
        self.sources: List[DataSource] = []

    def register_source(self, source: DataSource):
        """注册数据源"""
        self.sources.append(source)

    async def get_quote(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取实时行情（自动切换数据源）"""
        for source in self.sources:
            if not source.enabled:
                continue
            try:
                result = await source.get_quote(symbols)
                if result:
                    logger.info(f"Got quotes from {source.name}")
                    return result
            except Exception as e:
                logger.warning(f"{source.name} get_quote failed: {e}")
                continue

        logger.error(f"All sources failed for {self.market.value}")
        return {}

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据（自动切换数据源）"""
        for source in self.sources:
            if not source.enabled:
                continue
            try:
                result = await source.get_kline(symbol, period, start_date, end_date)
                if result:
                    logger.info(f"Got klines from {source.name}")
                    return result
            except Exception as e:
                logger.warning(f"{source.name} get_kline failed: {e}")
                continue

        return []

    async def get_fundamentals(self, symbol: str) -> Optional[FundamentalData]:
        """获取基本面数据（自动切换数据源）"""
        for source in self.sources:
            if not source.enabled:
                continue
            try:
                result = await source.get_fundamentals(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"{source.name} get_fundamentals failed: {e}")
                continue

        return None
