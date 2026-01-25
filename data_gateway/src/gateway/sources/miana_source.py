"""
缅A数据平台数据源
商业数据平台，提供实时行情、资金流向、板块等数据

官网: https://miana.com.cn
基础URL: https://miana.com.cn/api

数据特点:
- 全球覆盖：30+ 国家，40+ 交易所
- 实时数据：包含五档盘口数据
- 资金流向：当日资金流向
- 历史数据：30+ 年
- 股票数量：100,000+
"""
import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
import logging

try:
    import aiohttp
except ImportError:
    aiohttp = None
    logging.warning("aiohttp not installed")

from ..base import DataSource, QuoteData, KlineData, FundamentalData

# 使用 TYPE_CHECKING 避免运行时导入错误
if TYPE_CHECKING:
    if aiohttp:
        ClientSession = aiohttp.ClientSession
        ClientTimeout = aiohttp.ClientTimeout
    else:
        ClientSession = Any
        ClientTimeout = Any
else:
    ClientSession = Any
    ClientTimeout = Any

logger = logging.getLogger(__name__)


class MianaSource(DataSource):
    """
    缅A数据平台数据源

    需要token认证，通过登录获取
    提供实时行情（含五档）、资金流向、板块等数据
    """

    # API基础URL
    BASE_URL = "https://miana.com.cn/api"

    # 支持的市场代码映射
    MARKET_MAPPING = {
        "sh": "sh",  # 上海证券交易所
        "sz": "sz",  # 深圳证券交易所
        "bj": "bj",  # 北京证券交易所
        "hk": "hk",  # 香港证券交易所
        "us": "us",  # 美股
    }

    def __init__(self, token: str = ""):
        super().__init__("Miana")
        self.enabled = aiohttp is not None
        self.token = token
        self._session: Optional[ClientSession] = None

    async def _get_session(self) -> Optional[ClientSession]:
        """获取或创建HTTP会话"""
        if not aiohttp:
            return None
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=30) if aiohttp else 30
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _format_symbol(self, code: str, market: str = "cn_a") -> str:
        """
        格式化股票代码为缅A平台格式

        缅A平台格式:
        - 上海: sh600519
        - 深圳: sz000001
        - 北京: bj920106
        - 香港: hk00700
        - 美股: usAAPL
        """
        if market == "cn_a":
            if code.startswith("6"):
                return f"sh{code}"
            elif code.startswith(("0", "3")):
                return f"sz{code}"
            elif code.startswith("8") or code.startswith("4"):
                return f"bj{code}"
        elif market == "hk":
            return f"hk{code}"
        elif market == "us":
            return f"us{code}"

        return code

    async def get_quote(self, symbols: List[str], market: str = "cn_a") -> Dict[str, QuoteData]:
        """
        获取实时行情数据（包含五档盘口）

        缅A平台提供的实时行情非常全面：
        - 基础OHLCV数据
        - 买一~买五、卖一~卖五
        - 市值、股本数据
        - 涨跌停价格
        - 委比、换手率等
        """
        if not self.enabled:
            return {}

        if not self.token:
            logger.warning("Miana token not configured")
            return {}

        try:
            session = await self._get_session()

            # 格式化股票代码
            formatted_symbols = [self._format_symbol(s, market) for s in symbols]

            # 一次最多查询20支股票
            chunks = [formatted_symbols[i:i+20] for i in range(0, len(formatted_symbols), 20)]

            result = {}

            for chunk in chunks:
                params = {
                    "token": self.token,
                    "symbol": ",".join(chunk),
                    "format": "json"
                }

                async with session.get(
                    f"{self.BASE_URL}/stock/v2/realtime",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        # 处理响应数据
                        if isinstance(data, list):
                            for item in data:
                                if item.get("type") == "STOCK":
                                    code = self._parse_code(item.get("code"))
                                    if code and code in symbols:
                                        result[code] = self._parse_quote(item, market)

            return result

        except Exception as e:
            logger.error(f"Miana get_quote error: {e}")
            return {}

    def _parse_code(self, miana_code: str) -> Optional[str]:
        """将缅A平台代码转换回标准格式"""
        if not miana_code:
            return None

        if miana_code.startswith("sh"):
            return miana_code[2:]
        elif miana_code.startswith("sz"):
            return miana_code[2:]
        elif miana_code.startswith("bj"):
            return miana_code[2:]
        elif miana_code.startswith("hk"):
            return miana_code[2:]
        elif miana_code.startswith("us"):
            return miana_code[2:]

        return miana_code

    def _parse_quote(self, item: Dict, market: str) -> QuoteData:
        """解析缅A平台的行情数据"""
        try:
            return QuoteData(
                symbol=self._parse_code(item.get("code")),
                name=item.get("chineseName") or item.get("name"),
                price=float(item.get("price", 0)) if item.get("price") else None,
                open=float(item.get("open", 0)) if item.get("open") else None,
                high=float(item.get("high", 0)) if item.get("high") else None,
                low=float(item.get("low", 0)) if item.get("low") else None,
                volume=int(item.get("volume", 0)) if item.get("volume") else None,
                amount=float(item.get("amount", 0)) if item.get("amount") else None,
                change=float(item.get("change", 0)) if item.get("change") else None,
                change_pct=float(item.get("changeRate", 0)) if item.get("changeRate") else None,
                bid=float(item.get("buyVolume", 0)) if item.get("buyVolume") else None,  # 买一量
                ask=float(item.get("sellVolume", 0)) if item.get("sellVolume") else None,  # 卖一量
                timestamp=item.get("date"),
                market=market,
                # 额外的五档盘口数据
                extra={
                    "pre_close": float(item.get("preClose", 0)) if item.get("preClose") else None,
                    "high_limit": float(item.get("highLimit", 0)) if item.get("highLimit") else None,
                    "low_limit": float(item.get("lowLimit", 0)) if item.get("lowLimit") else None,
                    "turnover": float(item.get("turnover", 0)) if item.get("turnover") else None,
                    "pe_ttm": float(item.get("pe_ttm", 0)) if item.get("pe_ttm") else None,
                    "pb": float(item.get("pb", 0)) if item.get("pb") else None,
                    "market_value": item.get("marketValue"),
                    "circulation_value": item.get("circulationValue"),
                    "sells": item.get("sells"),  # 卖盘档位 [价, 量]
                    "buys": item.get("buys"),    # 买盘档位 [价, 量]
                }
            )
        except Exception as e:
            logger.error(f"Failed to parse quote data: {e}")
            return QuoteData(symbol=item.get("code", ""))

    async def get_kline(self, symbol: str, period: str,
                       start_date: str, end_date: str,
                       market: str = "cn_a") -> List[KlineData]:
        """
        获取K线数据

        支持分钟K线、日K线、周K线、月K线等
        """
        if not self.enabled:
            return []

        if not self.token:
            logger.warning("Miana token not configured")
            return []

        try:
            session = await self._get_session()

            # 缅A平台的K线接口
            # API endpoint: /stock/v2/kline
            # 需要进一步查看具体参数

            formatted_symbol = self._format_symbol(symbol, market)

            params = {
                "token": self.token,
                "symbol": formatted_symbol,
                "start": start_date,
                "end": end_date,
                "period": self._map_period(period),
                "format": "json"
            }

            async with session.get(
                f"{self.BASE_URL}/stock/v2/kline",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # 解析K线数据
                    return self._parse_kline(data, symbol, period, market)
                else:
                    logger.error(f"Miana kline API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Miana get_kline error: {e}")
            return []

    def _map_period(self, period: str) -> str:
        """映射周期参数"""
        period_map = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "60m": "60",
            "daily": "day",
            "weekly": "week",
            "monthly": "month"
        }
        return period_map.get(period, "day")

    def _parse_kline(self, data: Any, symbol: str, period: str, market: str) -> List[KlineData]:
        """解析K线数据"""
        # 根据实际响应格式解析
        # 这里需要根据缅A平台的实际响应格式实现
        klines = []

        # TODO: 根据缅A平台实际返回格式实现解析逻辑
        # 示例：
        # if isinstance(data, list):
        #     for item in data:
        #         klines.append(KlineData(
        #             symbol=symbol,
        #             datetime=item["date"],
        #             open=float(item["open"]),
        #             close=float(item["close"]),
        #             ...
        #         ))

        return klines

    async def get_fundamentals(self, symbol: str, market: str = "cn_a") -> Optional[FundamentalData]:
        """
        获取基本面数据

        缅A平台提供企业资料、财务数据等
        注意：缅A平台主要专注于实时行情，基本面数据建议使用 BaoStock
        """
        # 缅A平台不作为基本面数据的主要来源
        # 返回 None，让网关使用其他数据源（如 BaoStock）
        return None

    async def get_money_flow(self, symbol: str, date: str = None,
                            market: str = "cn_a") -> Optional[Dict[str, Any]]:
        """
        获取当日资金流向数据

        缅A平台提供的资金流向数据包括：
        - 大单净流入
        - 中单净流入
        - 小单净流入
        - 资金流向排名
        """
        if not self.enabled:
            return None

        if not self.token:
            logger.warning("Miana token not configured")
            return None

        try:
            session = await self._get_session()

            formatted_symbol = self._format_symbol(symbol, market)

            # API endpoint: /stock/v2/money-flow (推测)
            # 实际endpoint需要根据文档确认
            params = {
                "token": self.token,
                "symbol": formatted_symbol,
                "date": date or datetime.now().strftime("%Y-%m-%d")
            }

            async with session.get(
                f"{self.BASE_URL}/stock/v2/money-flow",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Miana money flow API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Miana get_money_flow error: {e}")
            return None

    async def get_sector_realtime(self, sector_type: str = "industry") -> List[Dict[str, Any]]:
        """
        获取板块实时行情

        参数:
            sector_type: 板块类型 (industry/concept)
        """
        if not self.enabled:
            return []

        if not self.token:
            logger.warning("Miana token not configured")
            return []

        try:
            session = await self._get_session()

            # API endpoint: /sector/v2/realtime (推测)
            params = {
                "token": self.token,
                "type": sector_type,
                "format": "json"
            }

            async with session.get(
                f"{self.BASE_URL}/sector/v2/realtime",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Miana sector API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Miana get_sector_realtime error: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试获取一个简单接口
            result = await self.get_quote(["sh600519"], market="cn_a")
            return len(result) > 0
        except Exception as e:
            logger.warning(f"Miana health check failed: {e}")
            return False

    async def close(self):
        """关闭连接"""
        if self._session and not self._session.closed:
            await self._session.close()

    def __del__(self):
        """析构函数"""
        if self._session and not self._session.closed:
            # 注意：这里无法使用await，需要在外部调用close方法
            pass
