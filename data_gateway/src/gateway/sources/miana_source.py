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
            timeout = aiohttp.ClientTimeout(total=30)
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
            # 辅助函数：安全转换为浮点数
            def to_float(val, default=None):
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            return QuoteData(
                symbol=self._parse_code(item.get("code")),
                name=item.get("chineseName") or item.get("name"),
                price=to_float(item.get("price")),
                open=to_float(item.get("open")),
                high=to_float(item.get("high")),
                low=to_float(item.get("low")),
                volume=int(item.get("volume", 0)) if item.get("volume") else None,
                amount=to_float(item.get("amount")),
                change=to_float(item.get("change")),
                change_pct=to_float(item.get("changeRate")),
                bid=to_float(item.get("buyVolume")),  # 买一量
                ask=to_float(item.get("sellVolume")),  # 卖一量
                timestamp=item.get("date"),
                market=market,
                # 额外的市场数据
                pre_close=to_float(item.get("preClose")),
                high_limit=to_float(item.get("highLimit")),
                low_limit=to_float(item.get("lowLimit")),
                turnover=to_float(item.get("turnover")),
                pe_ttm=to_float(item.get("pe_ttm")),
                pe_dyn=to_float(item.get("pe_dyn")),
                pe_static=to_float(item.get("pe_static")),
                pb=to_float(item.get("pb")),
                amplitude=to_float(item.get("amplitude")),
                committee=to_float(item.get("committee")),
                market_value=to_float(item.get("marketValue")),
                circulation_value=to_float(item.get("circulationValue")),
                circulation_shares=to_float(item.get("circulationShares")),
                total_shares=to_float(item.get("totalShares")),
                country_code=item.get("countryCode"),
                exchange_code=item.get("exchangeCode"),
                # 五档盘口数据
                buys=item.get("buys"),    # 买盘档位 [[价, 量], ...]
                sells=item.get("sells"),   # 卖盘档位 [[价, 量], ...]
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
        klines = []

        try:
            # 根据实际响应格式解析
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
            elif isinstance(data, list):
                items = data
            else:
                logger.warning(f"Unexpected Mina kline response format: {type(data)}")
                return []

            if not items:
                return []

            for item in items:
                try:
                    # 解析日期时间（分钟级带时间，日线级只有日期）
                    date_str = item.get("date") or item.get("datetime", "")
                    if period in ["1m", "5m", "15m", "30m", "60m"]:
                        # 分钟级数据可能包含时间
                        try:
                            if " " in date_str:
                                dt_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                dt_formatted = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                dt_formatted = date_str
                        except ValueError:
                            dt_formatted = date_str
                    else:
                        # 日线及以上
                        try:
                            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            dt_formatted = dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            dt_formatted = date_str

                    klines.append(KlineData(
                        symbol=symbol,
                        datetime=dt_formatted,
                        open=float(item.get("open", 0)),
                        close=float(item.get("close", 0)),
                        high=float(item.get("high", 0)),
                        low=float(item.get("low", 0)),
                        volume=int(item.get("volume", 0)),
                        amount=float(item.get("amount", 0)) if item.get("amount") else None,
                        period=period,
                        market=market
                    ))
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Failed to parse kline item {item}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing Mina kline data: {e}")

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
        - 成交额 amount
        - Mina净流入 mianNetInflowAmount
        - 主力净流入金额净比 mainNetRatio
        - 超大单流入/流出/净流入/净比
        - 大单流入/流出/净流入/净比
        - 中单流入/流出/净流入/净比
        - 小单流入/流出/净流入/净比

        单笔成交额分类:
        - 超大单: > 1000万元
        - 大单: 500万 - 1000万元
        - 中单: 100万 - 500万元
        - 小单: < 100万元

        API文档: https://miana.com.cn/api/stock/v1/dailyMoneyflow
        """
        if not self.enabled:
            return None

        if not self.token:
            logger.warning("Miana token not configured")
            return None

        try:
            session = await self._get_session()

            formatted_symbol = self._format_symbol(symbol, market)

            # API endpoint: /stock/v1/dailyMoneyflow
            params = {
                "token": self.token,
                "symbol": formatted_symbol
            }
            # 注意：接口不需要date参数，返回当日数据

            async with session.get(
                f"{self.BASE_URL}/stock/v1/dailyMoneyflow",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # 解析资金流向数据
                    return self._parse_money_flow(data, symbol)
                else:
                    logger.error(f"Miana money flow API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Miana get_money_flow error: {e}")
            return None

    def _parse_money_flow(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        解析资金流向响应数据

        标准化字段返回:
        {
            "symbol": 股票代码,
            "amount": 成交额,
            "main_net_inflow": 主力净流入金额,
            "main_net_ratio": 主力净流入金额净比,
            "super_large": {
                "inflow": 超大单流入金额,
                "outflow": 超大单流出金额,
                "net_inflow": 超大单净流入金额,
                "net_ratio": 超大单净流入金额净比
            },
            "large": {
                "inflow": 大单流入金额,
                "outflow": 大单流出金额,
                "net_inflow": 大单净流入金额,
                "net_ratio": 大单净流入金额净比
            },
            "medium": {
                "inflow": 中单流入金额,
                "outflow": 中单流出金额,
                "net_inflow": 中单净流入金额,
                "net_ratio": 中单净流入金额净比
            },
            "small": {
                "inflow": 小单流入金额,
                "outflow": 小单流出金额,
                "net_inflow": 小单净流入金额,
                "net_ratio": 小单净流入金额净比
            }
        }
        """
        try:
            # 直接返回标准化后的数据
            return {
                "symbol": self._parse_code(symbol) if symbol.startswith(("sh", "sz", "bj")) else symbol,
                "amount": data.get("amount"),
                "main_net_inflow": data.get("mianNetInflowAmount"),
                "main_net_ratio": data.get("mainNetRatio"),
                "super_large": {
                    "inflow": data.get("superLargeInflow"),
                    "outflow": data.get("superLargeOutflow"),
                    "net_inflow": data.get("superLargeNetInflowAmount"),
                    "net_ratio": data.get("superLargeNetRatio")
                },
                "large": {
                    "inflow": data.get("largeInflow"),
                    "outflow": data.get("largeOutflow"),
                    "net_inflow": data.get("largeNetInflowAmount"),
                    "net_ratio": data.get("largeNetRatio")
                },
                "medium": {
                    "inflow": data.get("mediumInflow"),
                    "outflow": data.get("mediumOutflow"),
                    "net_inflow": data.get("mediumNetInflowAmount"),
                    "net_ratio": data.get("mediumNetRatio")
                },
                "small": {
                    "inflow": data.get("smallInflow"),
                    "outflow": data.get("smallOutflow"),
                    "net_inflow": data.get("smallNetInflowAmount"),
                    "net_ratio": data.get("smallNetRatio")
                }
            }
        except Exception as e:
            logger.error(f"Failed to parse money flow data: {e}")
            return {}

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
