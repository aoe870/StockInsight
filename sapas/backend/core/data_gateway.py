"""
数据网关服务 - 对接数据网关API
"""
from typing import List, Dict, Any, Optional
import logging

import httpx
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DataGatewayService:
    """数据网关服务"""

    def __init__(self):
        self.base_url = settings.DATA_GATEWAY_URL
        self.timeout = httpx.Timeout(10.0)

    async def _get(
        self,
        path: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送GET请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}{path}"
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Data Gateway API error: {e}")
            raise

    async def _post(
        self,
        path: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送POST请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}{path}"
                response = await client.post(url, json=data, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Data Gateway API error: {e}")
            raise

    # ============== 实时行情 API ==============

    async def get_quote(
        self,
        market: str,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        获取实时行情

        参数:
            market: 市场代码 (cn_a, hk, us)
            symbols: 股票代码列表

        返回:
            {
                "code": 0,
                "message": "success",
                "data": {
                    "symbol1": {...},
                    "symbol2": {...}
                }
            }
        """
        return await self._post("/api/v1/quote", {
            "market": market,
            "symbols": symbols
        })

    # ============== K线数据 API ==============

    async def get_kline(
        self,
        symbol: str,
        market: str = "cn_a",
        period: str = "daily",
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        获取K线数据

        参数:
            symbol: 股票代码
            market: 市场代码
            period: 周期 (1m, 5m, 15m, 30m, 60m, daily, weekly, monthly)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        params = {
            "symbol": symbol,
            "period": period,
            "market": market
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return await self._get("/api/v1/kline", params)

    # ============== 基本面数据 API ==============

    async def get_fundamentals(
        self,
        symbol: str,
        market: str = "cn_a"
    ) -> Dict[str, Any]:
        """
        获取基本面数据

        参数:
            symbol: 股票代码
            market: 市场代码
        """
        return await self._get(f"/api/v1/stock/{symbol}/fundamentals", {"market": market})

    # ============== 资金流向 API ==============

    async def get_money_flow(
        self,
        code: str,
        date: str = None
    ) -> Dict[str, Any]:
        """
        获取资金流向数据

        参数:
            code: 股票代码
            date: 日期 (YYYY-MM-DD)，默认当天
        """
        params = {"date": date} if date else {}
        return await self._get(f"/api/v1/money-flow/{code}", params)

    async def get_money_flow_ranking(
        self,
        market: str = "cn_a",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取资金流向排名

        参数:
            market: 市场代码
            limit: 返回数量
        """
        return await self._get("/api/v1/money-flow/ranking", {"market": market, "limit": limit})

    # ============== 板块数据 API ==============

    async def get_industry_sectors(self) -> List[Dict[str, Any]]:
        """获取行业板块"""
        result = await self._get("/api/v1/sectors/industry")
        return result.get("data", [])

    async def get_concept_sectors(self) -> List[Dict[str, Any]]:
        """获取概念板块"""
        result = await self._get("/api/v1/sectors/concept")
        return result.get("data", [])

    async def get_sector_stocks(self, name: str) -> List[Dict[str, Any]]:
        """获取板块成分股"""
        result = await self._get(f"/api/v1/sectors/{name}/stocks")
        return result.get("data", [])

    # ============== 龙虎榜 API (待添加到数据网关) ==============

    async def get_dragon_tiger_list(
        self,
        trade_date: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取龙虎榜数据

        参数:
            trade_date: 交易日期
            limit: 返回数量

        注意：此功能需要数据网关支持
        """
        # 暂时返回空数据
        return {
            "code": 0,
            "message": "success",
            "data": {
                "trade_date": trade_date or "",
                "total_count": 0,
                "data": []
            }
        }

    # ============== 跌停分析 API (待添加到数据网关) ==============

    async def get_limit_down_stocks(
        self,
        trade_date: str = None
    ) -> Dict[str, Any]:
        """
        获取跌停股票

        注意：此功能需要数据网关支持
        """
        return {
            "code": 0,
            "message": "success",
            "data": []
        }

    # ============== 集合竞价 API (待添加到数据网关) ==============

    async def get_call_auction(
        self,
        code: str
    ) -> Dict[str, Any]:
        """
        获取集合竞价数据

        注意：此功能需要数据网关支持
        """
        return {
            "code": 0,
            "message": "success",
            "data": {
                "code": code,
                "auction_data": []
            }
        }

    # ============== 实时行情历史 API ==============

    async def get_realtime_history(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取实时行情历史数据

        参数:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量

        注意：此功能需要数据网关支持
        """
        params = {
            "symbol": symbol,
            "limit": limit
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return await self._get("/api/v1/realtime-quote/history/{symbol}", params)

    async def get_realtime_ranking(
        self,
        trade_date: str = None,
        order_by: str = "change_pct",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取实时行情排名

        参数:
            trade_date: 交易日期
            order_by: 排序字段
            limit: 返回数量

        注意：此功能需要数据网关支持
        """
        params = {
            "trade_date": trade_date,
            "order_by": order_by,
            "limit": limit
        }

        return await self._get("/api/v1/realtime-quote/ranking", params)


# 单例实例
data_gateway = DataGatewayService()
