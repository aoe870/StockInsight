"""
回测引擎

基于 Backtrader 实现的选股策略回测引擎
"""

import backtrader as bt
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import date
import numpy as np

from .loader import DataLoader
from .strategies import StrategyFactory


@dataclass
class BacktestConfig:
    """回测配置"""
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    start_date: date = None
    end_date: date = None

    initial_cash: float = 100000.0
    commission: float = 0.0003
    slippage_perc: float = 0.001

    max_positions: int = 10
    position_size: float = 0.1
    hold_days: int = 20
    rebalance_freq: str = "weekly"

    stock_pool: Optional[List[str]] = None


@dataclass
class BacktestResult:
    """回测结果"""
    # 配置
    config: BacktestConfig

    # 状态
    status: str = "success"
    error: Optional[str] = None

    # 绩效指标
    initial_cash: float = 0
    final_cash: float = 0
    total_return: float = 0
    annual_return: float = 0
    sharpe_ratio: Optional[float] = None
    max_drawdown: float = 0
    max_drawdown_duration: int = 0

    # 交易统计
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    avg_profit: float = 0
    avg_loss: float = 0
    profit_loss_ratio: float = 0

    # 详细数据
    equity_curve: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    daily_returns: Optional[List[float]] = None

    # 时间统计
    start_date: str = ""
    end_date: str = ""
    trading_days: int = 0


class BacktestEngine:
    """回测引擎"""

    def __init__(self):
        self.cerebro = None
        self.data_feeds = {}
        self.strategy = None

    def run(self, config: BacktestConfig, stock_data: Dict[str, Any]) -> BacktestResult:
        """
        运行回测

        参数:
            config: 回测配置
            stock_data: {code: DataFrame} 格式的股票数据

        返回:
            BacktestResult
        """
        try:
            # 创建 Cerebro 引擎
            self.cerebro = bt.Cerebro()

            # 设置初始资金
            self.cerebro.broker.setcash(config.initial_cash)
            self.cerebro.broker.setcommission(commission=config.commission)

            # 添加数据源
            for code, df in stock_data.items():
                # 获取股票名称（如果 DataFrame 中有）
                name = df.get('name', [code])[0] if isinstance(df.get('name'), list) else df.get('name', code)

                data = DataLoader.df_to_feed(df, code, name)
                self.cerebro.adddata(data)

            # 添加策略
            strategy_params = {
                'max_positions': config.max_positions,
                'hold_days': config.hold_days,
                'rebalance_freq': config.rebalance_freq,
                'position_size': config.position_size,
            }
            strategy_params.update(config.strategy_params)

            strategy_class = StrategyFactory.create(config.strategy_name)
            self.cerebro.addstrategy(strategy_class, **strategy_params)

            # 添加分析器
            self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

            # 运行回测
            results = self.cerebro.run()
            strat = results[0]

            # 提取结果
            result = self._extract_result(config, strat)

            return result

        except Exception as e:
            return BacktestResult(
                config=config,
                status="error",
                error=str(e),
                initial_cash=config.initial_cash,
                final_cash=config.initial_cash,
            )

    def _extract_result(self, config: BacktestConfig, strat) -> BacktestResult:
        """提取回测结果"""
        # 基础信息
        initial_cash = config.initial_cash
        final_cash = self.cerebro.broker.getvalue()
        total_return = (final_cash - initial_cash) / initial_cash

        # 获取分析器结果
        sharpe_analyzer = strat.analyzers.sharpe.get_analysis()
        drawdown_analyzer = strat.analyzers.drawdown.get_analysis()
        returns_analyzer = strat.analyzers.returns.get_analysis()
        trades_analyzer = strat.analyzers.trades.get_analysis()

        # 夏普比率
        sharpe_ratio = sharpe_analyzer.get('sharperatio') if sharpe_analyzer else None

        # 最大回撤
        max_drawdown = drawdown_analyzer.get('max', {}).get('drawdown', 0) if drawdown_analyzer else 0
        max_drawdown_duration = drawdown_analyzer.get('max', {}).get('len', 0) if drawdown_analyzer else 0

        # 年化收益率
        annual_return = returns_analyzer.get('rnorm', 0) if returns_analyzer else 0
        if annual_return == 0 and returns_analyzer:
            # 如果没有年化收益，手动计算
            rnorm = returns_analyzer.get('rtot', 0)
            trading_days = len(strat.equity_curve)
            if trading_days > 0:
                annual_return = (1 + rnorm) ** (252 / trading_days) - 1

        # 交易统计
        total_trades = 0
        profitable_trades = 0
        losing_trades = 0
        win_rate = 0
        avg_profit = 0
        avg_loss = 0
        profit_loss_ratio = 0

        if trades_analyzer:
            total_trades = trades_analyzer.get('total', {}).get('total', 0)
            won = trades_analyzer.get('won', {}).get('total', 0)
            lost = trades_analyzer.get('lost', {}).get('total', 0)

            profitable_trades = won
            losing_trades = lost
            win_rate = won / total_trades if total_trades > 0 else 0

            # 平均盈亏
            if won > 0:
                avg_profit = trades_analyzer.get('won', {}).get('pnl', {}).get('average', 0)
            if lost > 0:
                avg_loss = abs(trades_analyzer.get('lost', {}).get('pnl', {}).get('average', 0))

            profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

        # 交易日期范围
        equity_curve = strat.equity_curve if hasattr(strat, 'equity_curve') else []
        trading_days = len(equity_curve)
        start_date = equity_curve[0].get('date', '') if equity_curve else ''
        end_date = equity_curve[-1].get('date', '') if equity_curve else ''

        # 构建结果
        result = BacktestResult(
            config=config,
            status="success",
            initial_cash=initial_cash,
            final_cash=final_cash,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_loss_ratio=profit_loss_ratio,
            equity_curve=self._format_equity_curve(strat.equity_curve) if hasattr(strat, 'equity_curve') else [],
            trades=strat.trades if hasattr(strat, 'trades') else [],
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
        )

        return result

    def _format_equity_curve(self, equity_curve: List[Dict]) -> List[Dict[str, Any]]:
        """格式化资金曲线数据"""
        return [
            {
                "date": item.get('date', ''),
                "equity": float(item.get('equity', 0)),
                "cash": float(item.get('cash', 0)),
                "positions": int(item.get('positions', 0)),
            }
            for item in equity_curve
        ]

    def optimize(self, config: BacktestConfig, stock_data: Dict[str, Any], **opt_params):
        """
        参数优化

        参数:
            config: 回测配置
            stock_data: 股票数据
            opt_params: 优化参数

        返回:
            优化结果
        """
        # 创建 Cerebro 引擎
        self.cerebro = bt.Cerebro()

        # 设置初始资金
        self.cerebro.broker.setcash(config.initial_cash)
        self.cerebro.broker.setcommission(commission=config.commission)

        # 添加数据源
        for code, df in stock_data.items():
            name = df.get('name', [code])[0] if 'name' in df else code
            data = DataLoader.df_to_feed(df, code, name)
            self.cerebro.adddata(data)

        # 添加策略
        strategy_params = {
            'max_positions': config.max_positions,
            'hold_days': config.hold_days,
            'rebalance_freq': config.rebalance_freq,
            'position_size': config.position_size,
        }
        strategy_params.update(config.strategy_params)

        strategy_class = StrategyFactory.create(config.strategy_name)

        # 设置优化参数
        # 这里可以添加更多的优化参数
        self.cerebro.optstrategy(
            strategy_class,
            **strategy_params
        )

        # 运行优化
        results = self.cerebro.run()

        return results
