"""
选股相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .common import ApiResponse, PaginatedResponse


class ScreenerConditionCreate(BaseModel):
    """创建选股条件请求"""
    name: str = Field(..., min_length=1, max_length=100, description="条件名称")
    description: Optional[str] = Field(None, max_length=500, description="条件描述")
    condition_config: Dict[str, Any] = Field(..., description="选股条件配置（JSON）")
    is_public: bool = Field(default=False, description="是否公开共享")


class ScreenerConditionUpdate(BaseModel):
    """更新选股条件请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None)
    condition_config: Optional[Dict[str, Any]] = Field(None)
    is_public: Optional[bool] = Field(None)


class ScreenerConditionResponse(BaseModel):
    """选股条件响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    condition_config: Dict[str, Any]
    is_public: bool
    use_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScreenerQuery(BaseModel):
    """选股查询请求"""
    # 基本面条件
    pe_min: Optional[Decimal] = Field(None, ge=Decimal("0"), description="PE最小值")
    pe_max: Optional[Decimal] = Field(None, ge=Decimal("0"), description="PE最大值")
    pb_min: Optional[Decimal] = Field(None, ge=Decimal("0"), description="PB最小值")
    pb_max: Optional[Decimal] = Field(None, ge=Decimal("0"), description="PB最大值")
    roe_min: Optional[Decimal] = Field(None, ge=Decimal("-100"), description="ROE最小值")
    roe_max: Optional[Decimal] = Field(None, ge=Decimal("-100"), description="ROE最大值")
    market_cap_min: Optional[Decimal] = Field(None, ge=Decimal("0"), description="市值最小值（亿）")
    market_cap_max: Optional[Decimal] = Field(None, ge=Decimal("0"), description="市值最大值（亿）")

    # 技术面条件
    ma_cross_fast: Optional[int] = Field(None, ge=1, description="快速均线周期")
    ma_cross_slow: Optional[int] = Field(None, ge=1, description="慢速均线周期")
    ma_cross_type: Optional[str] = Field(None, description="交叉类型: golden_cross(金叉)/death_cross(死叉)")
    macd_dif_gt_zero: Optional[bool] = Field(None, description="DIF大于0")
    kdj_j_gt_d: Optional[bool] = Field(None, description="J值大于D值")
    kdj_j_lt_k: Optional[bool] = Field(None, description="J值小于D值")
    kdj_j_overbought: Optional[bool] = Field(None, description="J值超买")
    kdj_j_oversold: Optional[bool] = Field(None, description="J值超卖")
    rsi_min: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("100"), description="RSI最小值")
    rsi_max: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("100"), description="RSI最大值")

    # 资金面条件
    money_flow_in_min: Optional[Decimal] = Field(None, ge=Decimal("-10000000"), description="净流入最小值（万元）")
    net_inflow_days: Optional[int] = Field(None, ge=1, description="连续净流入天数")

    # 价格条件
    price_min: Optional[Decimal] = Field(None, ge=Decimal("0"), description="价格最小值")
    price_max: Optional[Decimal] = Field(None, ge=Decimal("0"), description="价格最大值")
    change_pct_min: Optional[Decimal] = Field(None, ge=Decimal("-20"), le=Decimal("20"), description="涨跌幅最小值(%)")
    change_pct_max: Optional[Decimal] = Field(None, ge=Decimal("-20"), le=Decimal("20"), description="涨跌幅最大值(%)")

    # 涨跌停
    limit_up: Optional[bool] = Field(None, description="涨停")
    limit_down: Optional[bool] = Field(None, description="跌停")

    # 排序
    order_by: Optional[str] = Field(None, description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")

    # 涨跌幅筛选
    exclude_st: Optional[List[str]] = Field(None, description="排除ST股票")
    exclude_new_days: Optional[int] = Field(None, ge=0, description="排除新股上市天数")


class ScreenerResult(BaseModel):
    """选股结果"""
    code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    price: Optional[float] = Field(None, description="最新价")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")
    volume: Optional[int] = Field(None, description="成交量(手）")
    amount: Optional[float] = Field(None, description="成交额(万元）")
    pe_ttm: Optional[float] = Field(None, description="TTM市盈率")
    pb: Optional[float] = Field(None, description="市净率")
    roe: Optional[float] = Field(None, description="净资产收益率")
    market_cap: Optional[float] = Field(None, description="市值(亿元）")
    turnover: Optional[float] = Field(None, description="换手率(%)")
    reason: Optional[Dict[str, Any]] = Field(None, description="匹配原因说明")

    class Config:
        from_attributes = True


class ScreenerResponse(ApiResponse):
    """选股响应"""
    data: List[ScreenerResult] = []


class ScreenerResultsResponse(ApiResponse):
    """选股结果响应（带统计）"""
    data: List[ScreenerResult] = []
    total: Optional[int] = None
    match_reasons: Optional[Dict[str, int]] = None  # 各类条件的匹配数量


# 预定义选股模板
SCREENER_TEMPLATES = {
    "low_pe_high_quality": {
        "name": "低估值优质股",
        "description": "选择市盈率较低且基本面优秀的股票",
        "config": {
            "pe_max": 15,
            "roe_min": 10
        }
    },
    "strong_momentum": {
        "name": "强势上涨股",
        "description": "近期连续上涨且放量",
        "config": {
            "change_pct_min": 5,
            "net_inflow_days": 3
        }
    },
    "oversold_rebound": {
        "name": "超卖反弹股",
        "description": "RSI超卖区，有反弹需求",
        "config": {
            "rsi_max": 30
        }
    }
}
