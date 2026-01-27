"""
选股相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..core.database import get_db_session
from ..core.auth import get_current_user_id
from ..core.data_gateway import data_gateway
from ..schemas.screener import (
    ScreenerQuery,
    ScreenerResponse,
    ScreenerResult,
    ScreenerResultsResponse,
    SCREENER_TEMPLATES
)
from ..models import ScreenerCondition

router = APIRouter(prefix="/api/v1/screener", tags=["选股"])


@router.get("/templates", response_model=dict)
async def get_templates():
    """获取预设选股模板"""
    return {
        "code": 0,
        "message": "success",
        "data": SCREENER_TEMPLATES
    }


@router.post("/query", response_model=dict)
async def screener_query(
    request: ScreenerQuery,
    db: AsyncSession = Depends(get_db_session)
):
    """
    执行选股查询

    请求示例:
    ```json
    {
      "pe_max": 15,
      "roe_min": 10,
      "change_pct_min": 5,
      "net_inflow_days": 3
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    # 获取所有A股代码（通过数据网关）
    try:
        from ..config import get_settings
        settings = get_settings()
        quote_result = await data_gateway.get_quote("cn_a", [])  # 获取所有股票列表
        if quote_result.get("code") != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取股票列表失败"
            )

        # 模拟所有股票代码（实际应该从数据网关获取）
        all_stocks = list(quote_result.get("data", {}).keys())

        # 拦量获取实时行情
        quotes_result = await data_gateway.get_quote("cn_a", all_stocks[:200])
        if quotes_result.get("code") != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取行情数据失败"
            )

        quotes = quotes_result.get("data", {})

    except Exception as e:
        from ..config import settings
        settings.LOGGER.error(f"Screener query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"选股查询失败: {e}"
        )

    # 过滤股票
    results = []
    for code, quote in quotes.items():
        try:
            stock_name = quote.get("name", "")
            price = quote.get("price", 0)
            change_pct = quote.get("change_pct", 0)
            volume = quote.get("volume", 0)
            amount = quote.get("amount", 0)
            pe_ttm = quote.get("pe_ttm", 0)
            pb = quote.get("pb", 0)
            roe = quote.get("roe", 0)
            market_cap = quote.get("market_value", 0)
            turnover = quote.get("turnover", 0)

            # 基本面筛选
            if request.pe_min is not None and pe_ttm and pe_ttm < request.pe_min:
                continue
            if request.pe_max is not None and pe_ttm and pe_ttm > request.pe_max:
                continue
            if request.pb_min is not None and pb and pb < request.pb_min:
                continue
            if request.pb_max is not None and pb and pb > request.pb_max:
                continue
            if request.roe_min is not None and roe and roe < request.roe_min:
                continue
            if request.roe_max is not None and roe and roe > request.roe_max:
                continue
            if request.market_cap_min is not None and market_cap and market_cap < request.market_cap_min:
                continue
            if request.market_cap_max is not None and market_cap and market_cap > request.market_cap_max:
                continue

            # 技术面筛选（需要K线数据，这里简化处理）
            ma_cross_type = request.ma_cross_type
            if ma_cross_type == "golden_cross":
                # 金叉：短线上穿长线
                # 简化处理：假设价格涨幅超过5%
                if change_pct and change_pct > 5:
                    results.append(ScreenerResult(
                        code=code,
                        name=stock_name,
                        price=price,
                        change_pct=change_pct,
                        volume=volume,
                        amount=amount,
                        pe_ttm=pe_ttm,
                        pb=pb,
                        roe=roe,
                        market_cap=market_cap,
                        turnover=turnover,
                        reason={"golden_cross": "涨幅超过5%"}
                    ))
            elif ma_cross_type == "death_cross":
                # 死叉：短线下穿长线
                if change_pct and change_pct < -5:
                    results.append(ScreenerResult(
                        code=code,
                        name=stock_name,
                        price=price,
                        change_pct=change_pct,
                        volume=volume,
                        amount=amount,
                        pe_ttm=pe_ttm,
                        pb=pb,
                        roe=roe,
                        market_cap=market_cap,
                        turnover=turnover,
                        reason={"death_cross": "跌幅超过5%"}
                    ))

            # RSI筛选
            if request.rsi_min is not None and rsi_max is not None:
                if volume > 0:  # 有成交量数据才计算RSI
                    rsi = abs(change_pct) * 2 + 50  # 简化RSI计算
                    if request.rsi_min <= rsi <= request.rsi_max:
                        results.append(ScreenerResult(
                            code=code,
                            name=stock_name,
                            price=price,
                            change_pct=change_pct,
                            volume=volume,
                            amount=amount,
                            pe_ttm=pe_ttm,
                            pb=pb,
                            roe=roe,
                            market_cap=market_cap,
                            turnover=turnover,
                            reason={"rsi": f"RSI在{request.rsi_min}-{request.rsi_max}区间"}
                        ))

        except Exception as e:
            # 忽略单只股票的错误，继续处理其他股票
            continue

    # 统计各条件匹配数量
    match_reasons = {}
    for result in results:
        for reason, value in result.reason.items():
            if isinstance(value, str):
                match_reasons[reason] = match_reasons.get(reason, 0) + 1

    return ScreenerResultsResponse(
        code=0,
        message="success",
        data=results,
        total=len(results),
        match_reasons=match_reasons
    )


@router.post("/conditions", response_model=dict)
async def create_condition(
    request: ScreenerConditionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建选股条件

    请求示例:
    ```json
    {
      "name": "我的选股条件",
      "description": "自定义选股条件",
      "condition_config": {
        "pe_max": 15,
        "change_pct_min": 5
      },
      "is_public": false
    }
    ```
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    condition = ScreenerCondition(
        user_id=user_id,
        name=request.name,
        description=request.description,
        condition_config=request.condition_config,
        is_public=request.is_public
    )

    db.add(condition)
    await db.commit()
    await db.refresh(condition)

    return {
        "code": 0,
        "message": "条件创建成功",
        "data": condition
    }


@router.get("/conditions", response_model=dict)
async def get_conditions(
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取用户的选股条件列表
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    result = await db.execute(
        select(ScreenerCondition)
        .where(ScreenerCondition.user_id == user_id)
        .order_by(desc(ScreenerCondition.created_at))
    )
    conditions = result.scalars().all()

    return {
        "code": 0,
        "message": "success",
        "data": [ScreenerCondition.model_validate(c) for c in conditions]
    }


@router.put("/conditions/{condition_id}", response_model=dict)
async def update_condition(
    condition_id: int,
    request: ScreenerConditionUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新选股条件
    """
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    result = await db.execute(
        select(ScreenerCondition).where(and_(ScreenerCondition.id == condition_id, ScreenerCondition.user_id == user_id))
    )
    condition = result.scalar_one_or_none()
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="条件不存在"
        )

    if request.name is not None:
        condition.name = request.name
    if request.description is not None:
        condition.description = request.description
    if request.condition_config is not None:
        condition.condition_config = request.condition_config
    if request.is_public is not None:
        condition.is_public = request.is_public

    condition.use_count += 1

    await db.commit()

    return {
        "code": 0,
        "message": "更新成功",
        "data": condition
    }


@router.delete("/conditions/{condition_id}", response_model=dict)
async def delete_condition(
    condition_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """删除选股条件"""
    user_id = await get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    result = await db.execute(
        select(ScreenerCondition).where(and_(ScreenerCondition.id == condition_id, ScreenerCondition.user_id == user_id))
    )
    condition = result.scalar_one_or_none()
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="条件不存在"
        )

    await db.delete(condition)
    await db.commit()

    return {
        "code": 0,
        "message": "删除成功"
    }
