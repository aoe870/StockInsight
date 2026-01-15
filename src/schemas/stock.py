"""
股票相关 Pydantic 数据模式
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


# ==================== 股票基础信息 ====================

class StockBasicsBase(BaseModel):
    """股票基础信息基类"""
    code: str = Field(..., description="股票代码", examples=["000001"])
    name: str = Field(..., description="股票名称", examples=["平安银行"])
    industry: Optional[str] = Field(None, description="所属行业")
    market: str = Field(..., description="市场", examples=["SZ"])


class StockBasicsCreate(StockBasicsBase):
    """创建股票信息"""
    list_date: Optional[date] = None


class StockBasicsResponse(StockBasicsBase):
    """股票信息响应"""
    model_config = ConfigDict(from_attributes=True)
    
    list_date: Optional[date] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None


class StockListResponse(BaseModel):
    """股票列表响应"""
    total: int = Field(..., description="总数")
    items: List[StockBasicsResponse] = Field(..., description="股票列表")


# ==================== K线数据 ====================

class KLineData(BaseModel):
    """K线数据"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    trade_date: date = Field(..., description="交易日期")
    open: Optional[Decimal] = Field(None, validation_alias="open_price", description="开盘价")
    close: Optional[Decimal] = Field(None, validation_alias="close_price", description="收盘价")
    high: Optional[Decimal] = Field(None, validation_alias="high_price", description="最高价")
    low: Optional[Decimal] = Field(None, validation_alias="low_price", description="最低价")
    volume: Optional[int] = Field(None, description="成交量")
    amount: Optional[Decimal] = Field(None, description="成交额")
    change_pct: Optional[Decimal] = Field(None, description="涨跌幅%")
    turnover: Optional[Decimal] = Field(None, description="换手率%")


class KLineQuery(BaseModel):
    """K线查询参数"""
    code: str = Field(..., description="股票代码")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    adjust: str = Field(default="qfq", description="复权类型: none/qfq/hfq")
    limit: int = Field(default=250, ge=1, le=1000, description="返回条数")


class KLineResponse(BaseModel):
    """K线数据响应"""
    code: str
    name: str
    adjust: str
    period: str = "daily"
    data: List[KLineData]


# ==================== 技术指标 ====================

class IndicatorData(BaseModel):
    """技术指标数据"""
    trade_date: date
    
    # 均线
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma120: Optional[float] = None
    ma250: Optional[float] = None
    
    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    
    # RSI
    rsi: Optional[float] = None
    
    # KDJ
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None
    
    # 布林带
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None


class IndicatorQuery(BaseModel):
    """指标查询参数"""
    code: str = Field(..., description="股票代码")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    indicators: List[str] = Field(
        default=["ma", "macd", "rsi", "kdj", "boll"],
        description="需要的指标类型"
    )


class IndicatorResponse(BaseModel):
    """指标数据响应"""
    code: str
    name: str
    data: List[IndicatorData]


# ==================== 信号检测 ====================

class SignalData(BaseModel):
    """信号数据"""
    trade_date: date
    signal_type: str = Field(..., description="信号类型")
    signal_value: int = Field(..., description="信号值: 1=买入, -1=卖出, 0=无")
    description: str = Field(..., description="信号描述")


class SignalResponse(BaseModel):
    """信号响应"""
    code: str
    name: str
    signals: List[SignalData]

