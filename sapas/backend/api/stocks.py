"""
股票数据 API 路由 - 对接数据网关
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date

from ..core.database import get_db_session
from ..core.data_gateway import data_gateway
from ..core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/stocks", tags=["股票数据"])


@router.get("/quote")
async def get_stocks_quote(
    market: str = Query("cn_a", description="市场代码"),
    symbols: Optional[List[str]] = Query(None, description="股票代码列表")
):
    """
    获取实时行情（代理到数据网关）

    参数:
        market: 市场代码 (cn_a, hk, us)
        symbols: 股票代码列表（最多100个）
    """
    # 限制查询数量
    if symbols and len(symbols) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次查询最多100只股票"
        )

    result = await data_gateway.get_quote(market, symbols or [])
    return result


@router.get("/kline/{symbol}")
async def get_stock_kline(
    symbol: str,
    market: str = Query("cn_a", description="市场代码"),
    period: str = Query("daily", description="周期"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD")
):
    """
    获取K线数据（代理到数据网关）

    参数:
        symbol: 股票代码
        market: 市场代码
        period: 周期 (1m, 5m, 15m, 30m, 60m, daily, weekly, monthly)
        start_date: 开始日期
        end_date: 结束日期
    """
    result = await data_gateway.get_kline(symbol, market, period, start_date, end_date)
    return result


@router.get("/fundamentals/{symbol}")
async def get_stock_fundamentals(
    symbol: str,
    market: str = Query("cn_a", description="市场代码")
):
    """
    获取基本面数据（代理到数据网关）

    参数:
        symbol: 股票代码
        market: 市场代码
    """
    result = await data_gateway.get_fundamentals(symbol, market)
    return result


@router.get("/money-flow/{code}")
async def get_stock_money_flow(
    code: str,
    date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD")
):
    """
    获取资金流向数据（代理到数据网关）

    参数:
        code: 股票代码
        date: 交易日期，默认当天
    """
    result = await data_gateway.get_money_flow(code, date)
    return result


@router.get("/money-flow/ranking")
async def get_money_flow_ranking(
    market: str = Query("cn_a", description="市场代码"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """
    获取资金流向排名（代理到数据网关）

    参数:
        market: 市场代码
        limit: 返回数量
    """
    result = await data_gateway.get_money_flow_ranking(market, limit)
    return result


@router.get("/sectors/industry")
async def get_industry_sectors():
    """
    获取行业板块（代理到数据网关）
    """
    result = await data_gateway.get_industry_sectors()
    return result


@router.get("/sectors/concept")
async def get_concept_sectors():
    """
    获取概念板块（代理到数据网关）
    """
    result = await data_gateway.get_concept_sectors()
    return result


@router.get("/sectors/{name}/stocks")
async def get_sector_stocks(
    name: str,
    limit: int = Query(50, ge=1, le=200, description="返回数量")
):
    """
    获取板块成分股（代理到数据网关）

    参数:
        name: 板块名称
        limit: 返回数量
    """
    result = await data_gateway.get_sector_stocks(name, limit)
    return result


@router.get("/search")
async def search_stocks(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    market: str = Query("cn_a", description="市场代码"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """
    搜索股票

    参数:
        keyword: 搜索关键词（代码或名称）
        market: 市场代码
        limit: 返回数量
    """
    # 通过数据网关搜索
    try:
        quote_result = await data_gateway.get_quote(market, [])  # 获取所有股票
        if quote_result.get("code") == 0:
            return {"code": 0, "data": []}

        all_quotes = quote_result.get("data", {})
        results = []

        # 简化搜索：先返回前N个结果
        count = 0
        for code, quote in all_quotes.items():
            if count >= limit:
                break
            name = quote.get("name", "")
            if keyword.lower() in code.lower() or keyword.lower() in name.lower():
                results.append({
                    "code": code,
                    "name": name,
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change_pct", 0)
                })
                count += 1

        return {"code": 0, "data": results}
    except Exception as e:
        from ..config import settings
        settings.LOGGER.error(f"Stock search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索失败"
        )


@router.get("/list")
async def get_stock_list(
    market: str = Query("cn_a", description="市场代码"),
    limit: int = Query(500, ge=1, le=2000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取股票列表（分页）

    参数:
        market: 市场代码
        limit: 每页数量
        offset: 偏移量
    """
    try:
        # 通过数据网关获取所有股票（简化实现）
        quote_result = await data_gateway.get_quote(market, [])
        if quote_result.get("code") != 0:
            all_quotes = quote_result.get("data", {})

            # 转换为列表
            stock_list = []
            for code, quote in all_quotes.items():
                stock_list.append({
                    "code": code,
                    "name": quote.get("name", ""),
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change_pct", 0)
                })

            # 分页
            total = len(stock_list)
            start = offset
            end = min(offset + limit, total)

            paginated_stocks = stock_list[start:end]

            return {
                "code": 0,
                "data": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "stocks": paginated_stocks
                }
            }
        else:
            return {"code": 0, "data": {"total": 0, "limit": limit, "offset": offset, "stocks": []}}

    except Exception as e:
        from ..config import settings
        settings.LOGGER.error(f"Get stock list error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取股票列表失败"
        )
