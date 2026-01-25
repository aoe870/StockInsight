"""
数据网关 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
import logging

from ..gateway.manager import gateway_manager
from ..gateway.base import QuoteData, KlineData, FundamentalData

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== 请求模型 ==============

class QuoteRequest(BaseModel):
    """行情请求"""
    market: str          # 市场: cn_a, hk, us, futures, economic
    symbols: List[str]   # 代码列表


class QuoteResponse(BaseModel):
    """行情响应"""
    code: int = 0
    message: str = "success"
    data: Dict[str, dict] = {}

    @classmethod
    def from_quote_data(cls, quotes: Dict[str, QuoteData]):
        """从 QuoteData 创建响应"""
        data = {}
        for symbol, quote in quotes.items():
            data[symbol] = {
                "symbol": quote.symbol,
                "name": quote.name,
                "price": quote.price,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "volume": quote.volume,
                "amount": quote.amount,
                "change": quote.change,
                "change_pct": quote.change_pct,
                "bid": quote.bid,
                "ask": quote.ask,
                "timestamp": quote.timestamp,
                "market": quote.market,
            }
        return cls(data=data)


class KlineResponse(BaseModel):
    """K线响应"""
    code: int = 0
    message: str = "success"
    data: List[dict] = []

    @classmethod
    def from_kline_data(cls, klines: List[KlineData]):
        """从 KlineData 创建响应"""
        data = []
        for k in klines:
            data.append({
                "symbol": k.symbol,
                "datetime": k.datetime,
                "open": k.open,
                "close": k.close,
                "high": k.high,
                "low": k.low,
                "volume": k.volume,
                "amount": k.amount,
                "period": k.period,
                "market": k.market,
            })
        return cls(data=data)


# ============== 路由定义 ==============

@router.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "service": "Data Gateway Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "quote": "/api/v1/quote",
            "kline": "/api/v1/kline",
            "fundamentals": "/api/v1/fundamentals",
            "health": "/api/v1/health"
        }
    }


@router.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    health = await gateway_manager.health_check()

    return {
        "service": "data-gateway",
        "status": "healthy" if all(health.values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "markets": health
    }


@router.post("/api/v1/quote", response_model=QuoteResponse, tags=["数据接口"])
async def get_quote(req: QuoteRequest):
    """
    获取实时行情

    参数:
        market: 市场代码 (cn_a, hk, us, futures, economic)
        symbols: 代码列表
    """
    try:
        quotes = await gateway_manager.get_quote(req.market, req.symbols)
        return QuoteResponse.from_quote_data(quotes)
    except Exception as e:
        logger.error(f"get_quote error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/kline", response_model=KlineResponse, tags=["数据接口"])
async def get_kline(
    market: str = Query(..., description="市场: cn_a, hk, us, futures, economic"),
    symbol: str = Query(..., description="股票代码"),
    period: str = Query("daily", description="周期: 1m, 5m, 15m, 30m, 60m, daily, weekly, monthly"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
):
    """
    获取K线数据

    参数:
        market: 市场代码
        symbol: 股票代码
        period: K线周期
        start_date: 开始日期
        end_date: 结束日期
    """
    try:
        klines = await gateway_manager.get_kline(
            market, symbol, period, start_date, end_date
        )
        return KlineResponse.from_kline_data(klines)
    except Exception as e:
        logger.error(f"get_kline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/fundamentals", tags=["数据接口"])
async def get_fundamentals(
    market: str = Query(..., description="市场: cn_a, hk, us"),
    symbol: str = Query(..., description="股票代码"),
):
    """
    获取基本面数据

    参数:
        market: 市场代码
        symbol: 股票代码
    """
    try:
        data = await gateway_manager.get_fundamentals(market, symbol)
        if not data:
            return {"code": 1, "message": "data not found", "data": None}

        return {
            "code": 0,
            "message": "success",
            "data": {
                "symbol": data.symbol,
                "name": data.name,
                "market": data.market,
                "revenue": data.revenue,
                "net_profit": data.net_profit,
                "eps": data.eps,
                "bvps": data.bvps,
                "pe": data.pe,
                "pb": data.pb,
                "market_cap": data.market_cap,
            }
        }
    except Exception as e:
        logger.error(f"get_fundamentals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/supported-markets", tags=["系统"])
async def supported_markets():
    """支持的市场列表"""
    return {
        "code": 0,
        "data": [
            {"market": "cn_a", "name": "A股", "enabled": True},
            {"market": "hk", "name": "港股", "enabled": True},
            {"market": "us", "name": "美股", "enabled": True},
            {"market": "futures", "name": "期货", "enabled": True},
            {"market": "economic", "name": "经济指标", "enabled": True},
        ]
    }


# ============== 缅A平台特色数据接口 ==============

@router.get("/api/v1/money-flow/{symbol}", tags=["缅A数据"])
async def get_money_flow(
    symbol: str,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认当天"),
):
    """
    获取个股资金流向数据（缅A平台）

    提供详细的资金流向数据：
    - 大单、中单、小单分类
    - 净流入/流出统计
    - 资金流向排名

    参数:
        symbol: 股票代码 (如 600519)
        date: 查询日期，默认当天
    """
    try:
        from ..gateway.markets.cn_a import ChinaAGateway
        gateway = gateway_manager.get_gateway("cn_a")
        if not isinstance(gateway, ChinaAGateway):
            raise HTTPException(status_code=400, detail="Money flow only available for cn_a market")

        data = await gateway.get_money_flow(symbol, date)
        if not data:
            return {"code": 1, "message": "money flow data not available", "data": None}

        return {
            "code": 0,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"get_money_flow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/sectors/industry", tags=["缅A数据"])
async def get_industry_sectors():
    """
    获取行业板块实时行情（缅A平台）

    返回所有行业板块的实时涨跌幅、成交额等数据
    """
    try:
        from ..gateway.markets.cn_a import ChinaAGateway
        gateway = gateway_manager.get_gateway("cn_a")
        if not isinstance(gateway, ChinaAGateway):
            raise HTTPException(status_code=400, detail="Sector data only available for cn_a market")

        data = await gateway.get_sector_realtime(sector_type="industry")
        return {
            "code": 0,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"get_industry_sectors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/sectors/concept", tags=["缅A数据"])
async def get_concept_sectors():
    """
    获取概念板块实时行情（缅A平台）

    返回所有概念板块的实时涨跌幅、成交额等数据
    """
    try:
        from ..gateway.markets.cn_a import ChinaAGateway
        gateway = gateway_manager.get_gateway("cn_a")
        if not isinstance(gateway, ChinaAGateway):
            raise HTTPException(status_code=400, detail="Sector data only available for cn_a market")

        data = await gateway.get_sector_realtime(sector_type="concept")
        return {
            "code": 0,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"get_concept_sectors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
