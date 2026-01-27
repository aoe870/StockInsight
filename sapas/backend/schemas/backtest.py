"""
回测相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from .common import ApiResponse, PaginatedResponse


class BacktestConfig(BaseModel):
    """回测配置"""
    strategy_name: str = Field(..., description="策略名称")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    initial_capital: Decimal = Field(default=Decimal("100000"), ge=Decimal("1000"), description="初始资金")
    commission_rate: Decimal = Field(default=Decimal("0.0003"), ge=Decimal("0"), le=Decimal("0.01"), description="手续费率")
    slippage: Decimal = Field(default=Decimal("0.001"), ge=Decimal("0"), le=Decimal("0.01"), description="滑点")


class BacktestRun(BaseModel):
    """回测运行信息"""
    id: int
    user_id: int
    strategy_name: str
    strategy_config: Dict[str, Any]
    start_date: date
    end_date: date
    initial_capital: Decimal
    commission_rate: Decimal
    slippage: Decimal
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

    # 结果统计
    final_capital: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_pct: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    max_drawdown_pct: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    avg_profit: Optional[Decimal] = None
    avg_loss: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class BacktestResult(BaseModel):
    """回测结果详情"""
    summary: BacktestRun
    trades: List["BacktestTradeResponse"] = []


class BacktestTradeResponse(BaseModel):
    """回测交易响应"""
    id: int
    backtest_id: int
    stock_code: str
    trade_type: str
    trade_time: datetime
    price: Decimal
    quantity: int
    amount: Decimal
    commission: Decimal
    profit: Optional[Decimal]
    profit_pct: Optional[Decimal]
    exit_reason: Optional[str]

    class Config:
        from_attributes = True


class BacktestResponse(ApiResponse):
    """回测列表响应"""
    data: List[BacktestRun] = []


# 预定义策略模板
STRATEGY_TEMPLATES = {
    "ma_cross": {
        "name": "双均线交叉",
        "description": "当短期均线上穿长期均线时买入，下穿时卖出",
        "params": {
            "fast_period": {"type": "integer", "default": 5, "min": 1, "max": 60, "label": "快速周期"},
            "slow_period": {"type": "integer", "default": 20, "min": 5, "max": 120, "label": "慢速周期"}
        }
    },
    "macd": {
        "name": "MACD策略",
        "description": "MACD金叉买入，死叉卖出",
        "params": {
            "fast_period": {"type": "integer", "default": 12, "min": 1, "max": 30, "label": "快线周期"},
            "slow_period": {"type": "integer", "default": 26, "min": 10, "max": 60, "label": "慢线周期"},
            "signal_period": {"type": "integer", "default": 9, "min": 1, "max": 20, "label": "信号周期"}
        }
    },
    "kdj": {
        "name": "KDJ策略",
        "description": "KDJ超卖区买入，超买区卖出",
        "params": {
            "k_period": {"type": "integer", "default": 9, "min": 1, "max": 30, "label": "K线周期"},
            "d_period": {"type": "integer", "default": 3, "min": 1, "max": 10, "label": "D线周期"},
            "j_period": {"type": "integer", "default": 3, "min": 1, "max": 10, "label": "J线周期"}
        }
    }
}
