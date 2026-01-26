"""
数据网关 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime, date as dt_date
from pydantic import BaseModel
import logging
from sqlalchemy import select, and_, desc

from ..gateway.manager import gateway_manager
from ..gateway.base import QuoteData, KlineData, FundamentalData
from ..database import get_db_session
from ..models.money_flow import MoneyFlow

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


@router.get("/api/v1/money-flow/history/{symbol}", tags=["资金流向"])
async def get_money_flow_history(
    symbol: str,
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(30, description="返回最近N条记录", ge=1, le=365),
):
    """
    获取历史资金流向数据

    **返回指定股票的历史资金流向数据**

    **参数:**
        symbol: 股票代码 (如 600519)
        start_date: 开始日期 (可选，默认最近30天)
        end_date: 结束日期 (可选，默认今天)
        limit: 返回记录数 (默认30条)

    **数据字段:**
        - amount: 成交额
        - main_net_inflow: 主力净流入金额
        - main_net_ratio: 主力净流入净比
        - super_large_*: 超大单相关数据
        - large_*: 大单相关数据
        - medium_*: 中单相关数据
        - small_*: 小单相关数据
    """
    try:
        async with get_db_session() as session:
            # 构建查询条件
            conditions = [MoneyFlow.code == symbol]

            # 添加日期范围
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    conditions.append(MoneyFlow.trade_date >= start_dt)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format")

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    conditions.append(MoneyFlow.trade_date <= end_dt)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format")

            # 查询数据，按日期倒序
            stmt = select(MoneyFlow).where(and_(*conditions)).order_by(desc(MoneyFlow.trade_date)).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return {
                    "code": 1,
                    "message": "No money flow data found",
                    "data": []
                }

            # 格式化返回数据
            data = []
            for record in records:
                data.append({
                    "symbol": record.code,
                    "trade_date": record.trade_date.strftime("%Y-%m-%d"),
                    "amount": record.amount,
                    "main_net_inflow": record.main_net_inflow,
                    "main_net_ratio": record.main_net_ratio,
                    "super_large": {
                        "inflow": record.super_large_inflow,
                        "outflow": record.super_large_outflow,
                        "net_inflow": record.super_large_net_inflow,
                        "net_ratio": record.super_large_net_ratio
                    },
                    "large": {
                        "inflow": record.large_inflow,
                        "outflow": record.large_outflow,
                        "net_inflow": record.large_net_inflow,
                        "net_ratio": record.large_net_ratio
                    },
                    "medium": {
                        "inflow": record.medium_inflow,
                        "outflow": record.medium_outflow,
                        "net_inflow": record.medium_net_inflow,
                        "net_ratio": record.medium_net_ratio
                    },
                    "small": {
                        "inflow": record.small_inflow,
                        "outflow": record.small_outflow,
                        "net_inflow": record.small_net_inflow,
                        "net_ratio": record.small_net_ratio
                    }
                })

            return {
                "code": 0,
                "message": "success",
                "data": data
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_money_flow_history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/money-flow/ranking", tags=["资金流向"])
async def get_money_flow_ranking(
    trade_date: str = Query(None, description="交易日期 YYYY-MM-DD，默认最新日期"),
    order_by: str = Query("main_net_inflow", description="排序字段: main_net_inflow, amount"),
    order_desc: bool = Query(True, description="是否倒序"),
    limit: int = Query(20, description="返回前N条", ge=1, le=100),
    market: str = Query("cn_a", description="市场代码")
):
    """
    获取资金流向排名

    **返回指定日期的资金流向排名列表**

    **参数:**
        trade_date: 交易日期 (可选，默认最新数据)
        order_by: 排序字段 (main_net_inflow 主力净流入, amount 成交额)
        order_desc: 是否倒序 (默认true)
        limit: 返回前N条 (默认20)
        market: 市场代码 (默认cn_a)

    **示例:**
    - `GET /api/v1/money-flow/ranking?order_by=main_net_inflow&limit=10`
    - `GET /api/v1/money-flow/ranking?trade_date=2026-01-26`
    """
    try:
        async with get_db_session() as session:
            # 确定查询日期
            target_date = None
            if trade_date:
                try:
                    target_date = datetime.strptime(trade_date, "%Y-%m-%d")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format")
            else:
                # 查询最新的日期
                latest_stmt = select(MoneyFlow.trade_date).where(
                    MoneyFlow.market_code == market
                ).order_by(desc(MoneyFlow.trade_date)).limit(1)
                result = await session.execute(latest_stmt)
                target_date = result.scalar_one_or_none()
                if not target_date:
                    return {
                        "code": 1,
                        "message": "No money flow data found",
                        "data": []
                    }

            # 构建查询
            conditions = and_(
                MoneyFlow.trade_date == target_date,
                MoneyFlow.market_code == market
            )

            # 确定排序字段
            order_field = MoneyFlow.main_net_inflow
            if order_by == "amount":
                order_field = MoneyFlow.amount

            # 查询数据
            stmt = select(MoneyFlow).where(conditions).order_by(
                desc(order_field) if order_desc else order_field
            ).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return {
                    "code": 1,
                    "message": "No money flow data found",
                    "data": []
                }

            # 格式化返回数据
            data = []
            for idx, record in enumerate(records, 1):
                data.append({
                    "rank": idx,
                    "symbol": record.code,
                    "trade_date": record.trade_date.strftime("%Y-%m-%d"),
                    "amount": record.amount,
                    "main_net_inflow": record.main_net_inflow,
                    "main_net_ratio": record.main_net_ratio,
                    "super_large_net": record.super_large_net_inflow,
                    "large_net": record.large_net_inflow
                })

            return {
                "code": 0,
                "message": "success",
                "data": data,
                "summary": {
                    "trade_date": target_date.strftime("%Y-%m-%d"),
                    "total": len(data)
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_money_flow_ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 实时行情历史数据接口 ==============

@router.get("/api/v1/realtime-quote/history/{symbol}", tags=["实时行情"])
async def get_realtime_quote_history(
    symbol: str,
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(50, description="返回最近N条记录", ge=1, le=500),
):
    """
    获取实时行情历史数据

    **返回指定股票的实时行情历史快照**

    **参数:**
        symbol: 股票代码 (如 600519)
        start_date: 开始日期 (可选，默认最近N条)
        end_date: 结束日期 (可选)
        limit: 返回记录数 (默认50)

    **数据字段:**
        - 基础行情: price, open, high, low, volume, amount, change, change_pct
        - 买卖档位: bid_volume, ask_volume, buys, sells
        - 市场数据: high_limit, low_limit, turnover, amplitude, committee
        - 估值指标: pe_ttm, pe_dyn, pe_static, pb
        - 股本数据: market_value, circulation_value, circulation_shares, total_shares
    """
    try:
        async with get_db_session() as session:
            from ..models.realtime_quote import RealtimeQuote

            # 构建查询条件
            conditions = [RealtimeQuote.code == symbol]

            # 添加日期范围
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    conditions.append(RealtimeQuote.trade_time >= start_dt)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format")

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    conditions.append(RealtimeQuote.trade_time <= end_dt)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format")

            # 查询数据，按时间倒序
            stmt = select(RealtimeQuote).where(and_(*conditions)).order_by(desc(RealtimeQuote.trade_time)).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return {
                    "code": 1,
                    "message": "No realtime quote data found",
                    "data": []
                }

            # 格式化返回数据
            data = []
            for record in records:
                data.append({
                    "symbol": record.code,
                    "name": record.name,
                    "trade_date": record.trade_date.strftime("%Y-%m-%d"),
                    "trade_time": record.trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                    # 基础行情
                    "price": record.price,
                    "open": record.open_price,
                    "high": record.high_price,
                    "low": record.low_price,
                    "volume": record.volume,
                    "amount": record.amount,
                    "change": record.change,
                    "change_pct": record.change_pct,
                    "pre_close": record.pre_close,
                    # 买卖档位
                    "bid_volume": record.bid_volume,
                    "ask_volume": record.ask_volume,
                    "buys": record.buys,
                    "sells": record.sells,
                    # 市场数据
                    "high_limit": record.high_limit,
                    "low_limit": record.low_limit,
                    "turnover": record.turnover,
                    "amplitude": record.amplitude,
                    "committee": record.committee,
                    # 估值指标
                    "pe_ttm": record.pe_ttm,
                    "pe_dyn": record.pe_dyn,
                    "pe_static": record.pe_static,
                    "pb": record.pb,
                    # 股本数据
                    "market_value": record.market_value,
                    "circulation_value": record.circulation_value,
                    "circulation_shares": record.circulation_shares,
                    "total_shares": record.total_shares
                })

            return {
                "code": 0,
                "message": "success",
                "data": data
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_realtime_quote_history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/realtime-quote/ranking", tags=["实时行情"])
async def get_realtime_quote_ranking(
    trade_date: str = Query(None, description="交易日期 YYYY-MM-DD，默认最新日期"),
    trade_time: str = Query(None, description="交易时间 YYYY-MM-DD HH:MM:SS，指定具体时间点"),
    order_by: str = Query("change_pct", description="排序字段: change_pct, amount, volume"),
    order_desc: bool = Query(True, description="是否倒序"),
    limit: int = Query(20, description="返回前N条", ge=1, le=100),
    market: str = Query("cn_a", description="市场代码")
):
    """
    获取实时行情排名

    **返回指定日期/时间的行情排名列表**

    **参数:**
        trade_date: 交易日期 (可选，默认最新数据)
        trade_time: 交易时间 (可选，指定具体时间点)
        order_by: 排序字段 (change_pct 涨跌幅, amount 成交额, volume 成交量)
        order_desc: 是否倒序 (默认true)
        limit: 返回前N条 (默认20)
        market: 市场代码 (默认cn_a)
    """
    try:
        async with get_db_session() as session:
            from ..models.realtime_quote import RealtimeQuote

            # 确定查询时间
            target_time = None
            if trade_date and trade_time:
                try:
                    target_time = datetime.strptime(f"{trade_date} {trade_time}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            if not target_time:
                # 查询最新的交易时间
                if trade_date:
                    try:
                        target_dt = datetime.strptime(trade_date, "%Y-%m-%d")
                        # 查询当天最晚的时间点
                        latest_stmt = select(RealtimeQuote.trade_time).where(
                            and_(
                                RealtimeQuote.trade_date == target_dt.date(),
                                RealtimeQuote.market_code == market
                            )
                        ).order_by(desc(RealtimeQuote.trade_time)).limit(1)
                        result = await session.execute(latest_stmt)
                        target_time = result.scalar_one_or_none()
                    except ValueError:
                        pass
                else:
                    # 查询最新的时间点
                    latest_stmt = select(RealtimeQuote.trade_time).where(
                        RealtimeQuote.market_code == market
                    ).order_by(desc(RealtimeQuote.trade_time)).limit(1)
                    result = await session.execute(latest_stmt)
                    target_time = result.scalar_one_or_none()

            if not target_time:
                return {
                    "code": 1,
                    "message": "No realtime quote data found",
                    "data": []
                }

            # 构建查询条件
            # 使用 trade_time 和 trade_time 进行匹配
            trade_dt = target_time.date()
            conditions = and_(
                RealtimeQuote.trade_date == trade_dt,
                RealtimeQuote.market_code == market
            )

            # 确定排序字段
            order_field = RealtimeQuote.change_pct
            if order_by == "amount":
                order_field = RealtimeQuote.amount
            elif order_by == "volume":
                order_field = RealtimeQuote.volume

            # 查询数据
            stmt = select(RealtimeQuote).where(conditions).order_by(
                desc(order_field) if order_desc else order_field
            ).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()

            if not records:
                return {
                    "code": 1,
                    "message": "No realtime quote data found",
                    "data": []
                }

            # 格式化返回数据
            data = []
            for idx, record in enumerate(records, 1):
                data.append({
                    "rank": idx,
                    "symbol": record.code,
                    "name": record.name,
                    "trade_time": record.trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "price": record.price,
                    "change": record.change,
                    "change_pct": record.change_pct,
                    "volume": record.volume,
                    "amount": record.amount,
                    "turnover": record.turnover,
                    "pe_ttm": record.pe_ttm,
                    "pb": record.pb,
                    "market_value": record.market_value
                })

            return {
                "code": 0,
                "message": "success",
                "data": data,
                "summary": {
                    "trade_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(data)
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_realtime_quote_ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
