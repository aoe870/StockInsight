"""
股票数据 API 路由
"""

from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import akshare as ak

from src.core.database import get_db
from src.core.indicators import TechnicalIndicators, SignalDetector
from src.models.stock import StockBasics, StockDailyK
from src.schemas.stock import (
    StockBasicsResponse,
    StockListResponse,
    KLineQuery,
    KLineResponse,
    KLineData,
    IndicatorResponse,
    IndicatorData,
    SignalResponse,
    SignalData,
)
from src.utils.logger import logger

router = APIRouter(prefix="/stocks", tags=["股票数据"])


@router.post("/quote/batch")
async def get_batch_quote(
    codes: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    批量获取股票最新行情（基于数据库最新日K数据）

    用于自选股列表等场景显示实时价格
    """
    if not codes:
        return {"items": []}

    if len(codes) > 100:
        raise HTTPException(status_code=400, detail="一次最多查询100只股票")

    result = []

    for code in codes:
        # 获取最近2天的K线数据计算涨跌
        query = select(StockDailyK).where(
            StockDailyK.code == code,
            StockDailyK.adjust_type == "qfq"
        ).order_by(StockDailyK.trade_date.desc()).limit(2)

        rows = await db.execute(query)
        klines = rows.scalars().all()

        if not klines:
            continue

        latest = klines[0]
        prev = klines[1] if len(klines) > 1 else None

        close = float(latest.close_price or 0)
        prev_close = float(prev.close_price or latest.open_price or close) if prev else float(latest.open_price or close)
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        result.append({
            "code": code,
            "current": round(close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "open": float(latest.open_price or 0),
            "high": float(latest.high_price or 0),
            "low": float(latest.low_price or 0),
            "volume": int(latest.volume or 0),
            "trade_date": str(latest.trade_date),
        })

    return {"items": result}


@router.get("", response_model=StockListResponse)
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场筛选: SH/SZ/BJ"),
    keyword: Optional[str] = Query(None, description="搜索关键词(代码或名称)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db)
):
    """获取股票列表"""
    query = select(StockBasics).where(StockBasics.is_active == True)
    
    if market:
        query = query.where(StockBasics.market == market.upper())
    
    if keyword:
        query = query.where(
            (StockBasics.code.contains(keyword)) | 
            (StockBasics.name.contains(keyword))
        )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    stocks = result.scalars().all()
    
    return StockListResponse(
        total=total or 0,
        items=[StockBasicsResponse.model_validate(s) for s in stocks]
    )


@router.get("/{code}", response_model=StockBasicsResponse)
async def get_stock_detail(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单只股票详情"""
    result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    
    return StockBasicsResponse.model_validate(stock)


@router.get("/{code}/kline", response_model=KLineResponse)
async def get_kline(
    code: str,
    period: str = Query("daily", description="周期: daily-日线, weekly-周线, monthly-月线, yearly-年线"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    adjust: str = Query("qfq", description="复权类型: none/qfq/hfq"),
    limit: int = Query(500, ge=1, le=10000, description="返回条数，0表示不限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取K线数据（如果数据库没有数据会自动同步全量历史数据）

    - period: daily(日线), weekly(周线), monthly(月线), yearly(年线)
    - 周线/月线/年线从日线数据聚合生成
    """
    # 获取股票信息
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    # 注意：已有全量历史数据（sync_all_klines.py 已同步）
    # 如果没有数据，记录警告但不阻塞请求
    from datetime import date as dt_date

    check_result = await db.execute(
        select(func.count()).select_from(StockDailyK).where(
            StockDailyK.code == code,
            StockDailyK.adjust_type == adjust
        )
    )
    data_count = check_result.scalar() or 0

    if data_count == 0:
        logger.warning(f"股票 {code} ({adjust}) 无K线数据，请检查是否已同步")

    # 构建查询 - 始终获取日线数据
    query = select(StockDailyK).where(
        StockDailyK.code == code,
        StockDailyK.adjust_type == adjust
    )

    if start_date:
        query = query.where(StockDailyK.trade_date >= start_date)
    if end_date:
        query = query.where(StockDailyK.trade_date <= end_date)

    # 如果是非日线周期，需要获取更多数据用于聚合
    fetch_limit = limit * 30 if period == "monthly" else limit * 7 if period == "weekly" else limit * 365 if period == "yearly" else limit
    query = query.order_by(StockDailyK.trade_date.desc()).limit(fetch_limit)

    result = await db.execute(query)
    klines = result.scalars().all()

    # 转换数据，按日期升序
    data = [KLineData.model_validate(k) for k in reversed(klines)]

    # 如果需要聚合周期
    if period != "daily" and data:
        data = _aggregate_kline(data, period)
        # 限制返回条数
        data = data[-limit:] if len(data) > limit else data

    return KLineResponse(
        code=code,
        name=stock.name,
        adjust=adjust,
        period=period,
        data=data
    )


def _aggregate_kline(daily_data: List[KLineData], period: str) -> List[KLineData]:
    """将日线数据聚合为周线/月线/年线"""
    if not daily_data:
        return []

    # 转换为 DataFrame 处理
    df = pd.DataFrame([{
        "trade_date": d.trade_date,
        "open": d.open,
        "high": d.high,
        "low": d.low,
        "close": d.close,
        "volume": d.volume,
        "amount": d.amount,
        "change_pct": d.change_pct,
    } for d in daily_data])

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date")

    # 确定聚合周期
    if period == "weekly":
        freq = "W"
    elif period == "monthly":
        freq = "ME"
    elif period == "yearly":
        freq = "YE"
    else:
        return daily_data

    # 聚合
    agg_df = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "amount": "sum",
    }).dropna()

    # 计算涨跌幅（Decimal 类型需要先转换为 float）
    close_float = agg_df["close"].astype(float)
    change_pct = close_float.pct_change() * 100
    # 处理无穷值和 NaN
    change_pct = change_pct.replace([float('inf'), float('-inf')], 0).fillna(0)
    agg_df["change_pct"] = change_pct

    # 转换回 KLineData
    result = []
    for idx, row in agg_df.iterrows():
        result.append(KLineData(
            trade_date=idx.date(),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=int(row["volume"]),
            amount=row["amount"],
            change_pct=row["change_pct"],
        ))

    return result


@router.get("/{code}/minute")
async def get_minute_data(
    code: str,
    period: str = Query("1", description="分钟周期: 1/5/15/30/60"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取分时数据（实时从 AKShare 获取）

    - period: 1/5/15/30/60 分钟
    - 数据来源：东方财富，只返回近期数据
    """
    # 获取股票信息
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    try:
        # 使用东财分时接口
        now = datetime.now()
        # 获取当天数据（如果是交易日）
        start_date = now.strftime("%Y-%m-%d 09:30:00")
        end_date = now.strftime("%Y-%m-%d 15:00:00")

        df = ak.stock_zh_a_hist_min_em(
            symbol=code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=""  # 分时数据不复权
        )

        if df.empty:
            # 如果当天没有数据，获取最近的分时数据
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d 09:30:00")
            yesterday_end = (now - timedelta(days=1)).strftime("%Y-%m-%d 15:00:00")
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                start_date=yesterday,
                end_date=yesterday_end,
                period=period,
                adjust=""
            )

        # 转换数据格式
        data = []
        for _, row in df.iterrows():
            time_str = str(row.get("时间", ""))
            data.append({
                "time": time_str,
                "open": float(row.get("开盘", 0)),
                "close": float(row.get("收盘", 0)),
                "high": float(row.get("最高", 0)),
                "low": float(row.get("最低", 0)),
                "volume": int(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "avg_price": float(row.get("均价", 0)) if "均价" in row else None,
            })

        return {
            "code": code,
            "name": stock.name,
            "period": period,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取分时数据失败: {code}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {str(e)}")


@router.get("/{code}/indicators", response_model=IndicatorResponse)
async def get_indicators(
    code: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取技术指标"""
    # 获取股票信息
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    
    # 需要额外获取更多历史数据用于计算指标
    calc_start = (start_date - timedelta(days=300)) if start_date else None

    query = select(StockDailyK).where(
        StockDailyK.code == code,
        StockDailyK.adjust_type == "qfq"
    )

    if calc_start:
        query = query.where(StockDailyK.trade_date >= calc_start)
    if end_date:
        query = query.where(StockDailyK.trade_date <= end_date)

    query = query.order_by(StockDailyK.trade_date)
    result = await db.execute(query)
    klines = result.scalars().all()

    if not klines:
        return IndicatorResponse(code=code, name=stock.name, data=[])

    # 转换为 DataFrame
    df = pd.DataFrame([{
        "date": k.trade_date,
        "open": float(k.open_price) if k.open_price else None,
        "close": float(k.close_price) if k.close_price else None,
        "high": float(k.high_price) if k.high_price else None,
        "low": float(k.low_price) if k.low_price else None,
        "volume": k.volume,
    } for k in klines])

    # 计算指标
    calculator = TechnicalIndicators()
    df = calculator.calculate_all(df)

    # 过滤日期范围
    if start_date:
        df = df[df["date"] >= start_date]

    # 转换为响应格式
    data = []
    for _, row in df.iterrows():
        data.append(IndicatorData(
            trade_date=row["date"],
            ma5=row.get("ma5"),
            ma10=row.get("ma10"),
            ma20=row.get("ma20"),
            ma60=row.get("ma60"),
            ma120=row.get("ma120"),
            ma250=row.get("ma250"),
            macd=row.get("macd"),
            macd_signal=row.get("macd_signal"),
            macd_hist=row.get("macd_hist"),
            rsi=row.get("rsi"),
            k=row.get("k"),
            d=row.get("d"),
            j=row.get("j"),
            boll_upper=row.get("boll_upper"),
            boll_mid=row.get("boll_mid"),
            boll_lower=row.get("boll_lower"),
        ))

    return IndicatorResponse(code=code, name=stock.name, data=data)


@router.get("/{code}/indicators/full")
async def get_full_indicators(
    code: str,
    indicators: str = Query("MA,MACD,KDJ,RSI,BOLL,VOL", description="指标列表，逗号分隔"),
    period: str = Query("daily", description="周期: daily/weekly/monthly/yearly"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(250, ge=1, le=2000),
    db: AsyncSession = Depends(get_db)
):
    """
    获取完整技术指标数据

    支持的指标:
    - 趋势类: MA, EMA, SAR, TRIX, DMA
    - 震荡类: KDJ, RSI, CCI, WR, ROC, BIAS
    - 压力支撑类: BOLL, ATR, BBI
    - 量能类: VOL, OBV, VWAP, VR
    - 综合类: DMI, MACD, PSY
    """
    # 获取股票信息
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    # 解析指标列表
    indicator_list = [i.strip().upper() for i in indicators.split(",")]

    # 需要额外获取更多历史数据用于计算指标
    calc_start = (start_date - timedelta(days=300)) if start_date else None
    fetch_limit = limit * 30 if period == "monthly" else limit * 7 if period == "weekly" else limit * 365 if period == "yearly" else limit + 300

    query = select(StockDailyK).where(
        StockDailyK.code == code,
        StockDailyK.adjust_type == "qfq"
    )

    if calc_start:
        query = query.where(StockDailyK.trade_date >= calc_start)
    if end_date:
        query = query.where(StockDailyK.trade_date <= end_date)

    query = query.order_by(StockDailyK.trade_date.desc()).limit(fetch_limit)
    result = await db.execute(query)
    klines = list(reversed(result.scalars().all()))

    if not klines:
        return {"code": code, "name": stock.name, "period": period, "indicators": indicator_list, "data": []}

    # 转换为 DataFrame
    df = pd.DataFrame([{
        "date": k.trade_date,
        "open": float(k.open_price) if k.open_price else None,
        "close": float(k.close_price) if k.close_price else None,
        "high": float(k.high_price) if k.high_price else None,
        "low": float(k.low_price) if k.low_price else None,
        "volume": k.volume,
        "amount": float(k.amount) if k.amount else None,
    } for k in klines])

    # 如果需要聚合周期
    if period != "daily" and len(df) > 0:
        df = _aggregate_ohlcv(df, period)

    # 计算选定的指标
    calculator = TechnicalIndicators()
    df = calculator.calculate_selected(df, indicator_list)

    # 过滤日期范围
    if start_date:
        df = df[df["date"] >= start_date]

    # 限制返回条数
    df = df.tail(limit)

    # 转换为响应格式，只包含计算出的指标
    result_data = []
    for _, row in df.iterrows():
        item = {"date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"])}
        # OHLCV 基础数据
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            if col in row and pd.notna(row[col]):
                item[col] = float(row[col]) if col != "volume" else int(row[col])
        # 指标数据
        for col in df.columns:
            if col not in ["date", "open", "high", "low", "close", "volume", "amount"] and pd.notna(row[col]):
                item[col] = round(float(row[col]), 4) if isinstance(row[col], (int, float)) else row[col]
        result_data.append(item)

    return {
        "code": code,
        "name": stock.name,
        "period": period,
        "indicators": indicator_list,
        "available_indicators": TechnicalIndicators.INDICATOR_CATEGORIES,
        "data": result_data
    }


def _aggregate_ohlcv(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """将日线 OHLCV 数据聚合为其他周期"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    freq = {"weekly": "W", "monthly": "ME", "yearly": "YE"}.get(period, "D")

    agg_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    if "amount" in df.columns:
        agg_dict["amount"] = "sum"

    agg_df = df.resample(freq).agg(agg_dict).dropna()
    agg_df = agg_df.reset_index()
    agg_df = agg_df.rename(columns={"index": "date"})

    return agg_df


@router.get("/{code}/signals", response_model=SignalResponse)
async def get_signals(
    code: str,
    days: int = Query(30, ge=1, le=365, description="检测天数"),
    db: AsyncSession = Depends(get_db)
):
    """获取最近的交易信号"""
    # 获取股票信息
    stock_result = await db.execute(
        select(StockBasics).where(StockBasics.code == code)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

    # 获取数据（额外获取更多用于计算）
    end_date = date.today()
    start_date = end_date - timedelta(days=days + 300)

    query = select(StockDailyK).where(
        StockDailyK.code == code,
        StockDailyK.adjust_type == "qfq",
        StockDailyK.trade_date >= start_date
    ).order_by(StockDailyK.trade_date)

    result = await db.execute(query)
    klines = result.scalars().all()

    if not klines:
        return SignalResponse(code=code, name=stock.name, signals=[])

    # 转换为 DataFrame
    df = pd.DataFrame([{
        "date": k.trade_date,
        "open": float(k.open_price) if k.open_price else None,
        "close": float(k.close_price) if k.close_price else None,
        "high": float(k.high_price) if k.high_price else None,
        "low": float(k.low_price) if k.low_price else None,
        "volume": k.volume,
    } for k in klines])

    # 计算指标和信号
    calculator = TechnicalIndicators()
    df = calculator.calculate_all(df)
    df = SignalDetector.detect_all_signals(df)

    # 只保留最近N天
    cutoff_date = end_date - timedelta(days=days)
    df = df[df["date"] >= cutoff_date]

    # 提取信号
    signals = []
    signal_columns = [
        ("ma_cross_signal", "MA交叉", {1: "MA5上穿MA20金叉", -1: "MA5下穿MA20死叉"}),
        ("macd_cross_signal", "MACD交叉", {1: "MACD金叉", -1: "MACD死叉"}),
        ("rsi_signal", "RSI信号", {1: "RSI从超卖区回升", -1: "RSI从超买区回落"}),
        ("boll_signal", "布林带", {1: "突破布林带上轨", -1: "跌破布林带下轨"}),
        ("volume_signal", "成交量", {1: "成交量异动放大"}),
    ]

    for col, signal_type, desc_map in signal_columns:
        if col in df.columns:
            for _, row in df[df[col] != 0].iterrows():
                signal_val = int(row[col])
                signals.append(SignalData(
                    trade_date=row["date"],
                    signal_type=signal_type,
                    signal_value=signal_val,
                    description=desc_map.get(signal_val, "未知信号")
                ))

    # 按日期排序
    signals.sort(key=lambda x: x.trade_date, reverse=True)

    return SignalResponse(code=code, name=stock.name, signals=signals)

