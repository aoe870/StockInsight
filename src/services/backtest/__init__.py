"""
回测服务模块

基于 Backtrader 实现选股策略回测功能
"""

from .engine import BacktestEngine, BacktestConfig, BacktestResult
from .strategies import StockScreenerStrategy, RsiMacdStrategy, StrategyFactory
from .loader import DataLoader

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'StockScreenerStrategy',
    'RsiMacdStrategy',
    'StrategyFactory',
    'DataLoader',
]
