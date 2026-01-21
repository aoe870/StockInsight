"""
回测相关数据模型
"""

from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BacktestConfigRequest(BaseModel):
    """回测配置请求"""
    # 策略配置
    strategy_name: str = Field(..., description="策略名称: rsi_macd, low_pe, etc.")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")

    # 回测时间范围
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")

    # 资金管理
    initial_cash: float = Field(default=100000.0, ge=1000, description="初始资金")
    commission: float = Field(default=0.0003, ge=0, le=0.01, description="手续费率")
    slippage: float = Field(default=0.001, ge=0, le=0.05, description="滑点率")

    # 仓位管理
    max_positions: int = Field(default=10, ge=1, le=50, description="最大持仓数")
    position_size: float = Field(default=0.1, ge=0.01, le=1.0, description="单只股票仓位比例")
    hold_days: int = Field(default=20, ge=1, le=365, description="持有天数")

    # 股票池
    stock_pool: Optional[List[str]] = Field(default=None, description="股票池代码列表，None表示全市场")

    # 调仓频率
    rebalance_freq: str = Field(default="weekly", description="调仓频率: daily, weekly, monthly")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_name": "rsi_macd",
                "strategy_params": {"rsi_period": 14, "rsi_threshold": 30, "macd_fast": 12, "macd_slow": 26},
                "start_date": "2023-01-01",
                "end_date": "2024-12-31",
                "initial_cash": 100000,
                "max_positions": 10,
                "hold_days": 20,
                "rebalance_freq": "weekly"
            }
        }


class TradeRecord(BaseModel):
    """交易记录"""
    date: str
    code: str
    name: str
    action: str  # buy/sell
    price: float
    shares: int
    amount: float
    profit: Optional[float] = None  # 卖出时的盈亏


class PerformanceMetrics(BaseModel):
    """绩效指标"""
    # 基础指标
    initial_cash: float
    final_cash: float
    total_return: float
    annual_return: float

    # 风险指标
    sharpe_ratio: Optional[float]
    max_drawdown: float
    max_drawdown_duration: int  # 最大回撤持续天数

    # 交易统计
    total_trades: int
    profitable_trades: int
    losing_trades: int
    win_rate: float

    avg_profit: float
    avg_loss: float
    profit_loss_ratio: float

    # 时间统计
    start_date: str
    end_date: str
    trading_days: int


class BacktestResultResponse(BaseModel):
    """回测结果响应"""
    # 配置
    config: BacktestConfigRequest

    # 绩效指标
    performance: PerformanceMetrics

    # 详细数据
    equity_curve: List[Dict[str, Any]]  # 资金曲线
    trades: List[TradeRecord]  # 交易记录
    daily_returns: Optional[List[float]] = None  # 每日收益率

    # 状态
    status: str  # success, error
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "config": {"strategy_name": "rsi_macd", "start_date": "2023-01-01", "end_date": "2024-12-31"},
                "performance": {
                    "total_return": 0.25,
                    "annual_return": 0.18,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.15,
                    "win_rate": 0.55
                },
                "equity_curve": [{"date": "2023-01-01", "equity": 100000}],
                "trades": [],
                "status": "success"
            }
        }


class StrategyInfo(BaseModel):
    """策略信息"""
    name: str
    display_name: str
    description: str
    category: str  # trend, oscillator, value, etc.
    params: List[Dict[str, Any]]  # 参数列表

    class Config:
        json_schema_extra = {
            "example": {
                "name": "rsi_macd",
                "display_name": "RSI超卖+MACD金叉",
                "description": "当RSI超卖且MACD金叉时买入",
                "category": "oscillator",
                "params": [
                    {"name": "rsi_period", "default": 14, "min": 5, "max": 30},
                    {"name": "rsi_threshold", "default": 30, "min": 20, "max": 50}
                ]
            }
        }
