"""
数据网关管理器
统一管理所有市场和数据源
"""
import asyncio
from typing import Dict, List, Optional
import logging

from .base import (
    Market, Period, QuoteData, KlineData, FundamentalData,
    MarketGateway, DataSource
)
from .markets.cn_a import ChinaAGateway
from .markets.hk import HKGateway
from .markets.us import USGateway
from .markets.futures import FuturesGateway
from .markets.economic import EconomicGateway

logger = logging.getLogger(__name__)


class DataGatewayManager:
    """数据网关管理器"""

    def __init__(self):
        self.gateways: Dict[Market, MarketGateway] = {}
        self._initialized = False

    async def initialize(self):
        """初始化所有市场网关"""
        if self._initialized:
            return

        logger.info("Initializing data gateway manager...")

        # 初始化各市场网关
        self.gateways[Market.CN_A] = ChinaAGateway()
        self.gateways[Market.HK] = HKGateway()
        self.gateways[Market.US] = USGateway()
        self.gateways[Market.FUTURES] = FuturesGateway()
        self.gateways[Market.ECONOMIC] = EconomicGateway()

        # 启动各网关
        for market, gateway in self.gateways.items():
            try:
                await gateway.initialize()
                logger.info(f"{market.value} gateway initialized")
            except Exception as e:
                logger.error(f"Failed to initialize {market.value}: {e}")

        self._initialized = True
        logger.info("Data gateway manager initialized")

    def get_gateway(self, market: str) -> Optional[MarketGateway]:
        """获取市场网关"""
        try:
            market_enum = Market(market)
            return self.gateways.get(market_enum)
        except ValueError:
            logger.error(f"Unknown market: {market}")
            return None

    async def get_quote(self, market: str, symbols: List[str]) -> Dict[str, QuoteData]:
        """获取实时行情"""
        gateway = self.get_gateway(market)
        if not gateway:
            return {}
        return await gateway.get_quote(symbols)

    async def get_kline(self, market: str, symbol: str,
                       period: str, start_date: str, end_date: str) -> List[KlineData]:
        """获取K线数据"""
        gateway = self.get_gateway(market)
        if not gateway:
            return []
        return await gateway.get_kline(symbol, period, start_date, end_date)

    async def get_fundamentals(self, market: str, symbol: str) -> Optional[FundamentalData]:
        """获取基本面数据"""
        gateway = self.get_gateway(market)
        if not gateway:
            return None
        return await gateway.get_fundamentals(symbol)

    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        for market, gateway in self.gateways.items():
            try:
                # 检查第一个数据源
                if gateway.sources:
                    results[market.value] = await gateway.sources[0].health_check()
                else:
                    results[market.value] = False
            except Exception as e:
                logger.error(f"Health check failed for {market.value}: {e}")
                results[market.value] = False
        return results


# 全局单例
gateway_manager = DataGatewayManager()
