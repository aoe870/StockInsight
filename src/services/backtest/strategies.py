"""
选股策略类

基于 Backtrader 实现的选股策略
"""

import backtrader as bt
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class StockScreenerStrategy(bt.Strategy):
    """
    选股策略基类

    实现选股策略的核心逻辑：
    1. 定期执行选股
    2. 根据选股结果调仓
    3. 跟踪交易记录
    """

    params = (
        ('max_positions', 10),      # 最大持仓数
        ('hold_days', 20),          # 持有天数
        ('rebalance_freq', 'weekly'),  # 调仓频率: daily, weekly, monthly
        ('position_size', 0.1),     # 单只股票仓位比例
    )

    def __init__(self):
        # 存储持仓信息
        self.position_info: Dict[str, Dict] = {}  # {code: {"shares": int, "buy_date": datetime, "buy_price": float}}

        # 存储交易记录
        self.trades: List[Dict] = []

        # 存储资金曲线
        self.equity_curve: List[Dict] = []

        # 当前选中的股票
        self.selected_stocks: List[str] = []

        # 调仓计数器
        self.rebalance_counter = 0

        # 最后一次调仓日期
        self.last_rebalance_date: Optional[datetime] = None

    def next(self):
        """每个交易日调用"""
        current_date = self.datas[0].datetime.date(0)

        # 检查是否需要调仓
        if self._should_rebalance(current_date):
            self._execute_rebalance(current_date)

        # 记录资金曲线
        self._record_equity(current_date)

        # 检查持仓天数，卖出到期的股票
        self._check_expired_positions(current_date)

    def _should_rebalance(self, current_date: datetime.date) -> bool:
        """判断是否需要调仓"""
        if self.last_rebalance_date is None:
            return True

        days_since_last = (current_date - self.last_rebalance_date).days

        if self.params.rebalance_freq == 'daily':
            return days_since_last >= 1
        elif self.params.rebalance_freq == 'weekly':
            return days_since_last >= 7
        elif self.params.rebalance_freq == 'monthly':
            return days_since_last >= 30

        return False

    def _execute_rebalance(self, current_date: datetime.date):
        """执行调仓"""
        # 1. 执行选股
        self.selected_stocks = self.select_stocks()

        # 2. 获取当前持仓
        current_positions = set(self.position_info.keys())
        target_positions = set(self.selected_stocks)

        # 3. 卖出不在目标列表中的股票
        for code in current_positions - target_positions:
            self._close_position(code, "不在选股列表中")

        # 4. 卖出超出最大持仓数的股票
        if len(current_positions) > self.params.max_positions:
            sorted_positions = sorted(
                current_positions,
                key=lambda x: self.position_info.get(x, {}).get('buy_price', 0),
                reverse=True
            )
            for code in sorted_positions[self.params.max_positions:]:
                self._close_position(code, "超出最大持仓数")

        # 5. 买入新股票
        available_slots = self.params.max_positions - len(self.position_info)
        if available_slots > 0:
            for code in target_positions:
                if code not in self.position_info and available_slots > 0:
                    if self._open_position(code):
                        available_slots -= 1

        # 更新最后调仓日期
        self.last_rebalance_date = current_date

    def _open_position(self, code: str) -> bool:
        """开仓"""
        # 找到对应的数据源
        data = self._get_data_by_name(code)
        if data is None:
            return False

        # 获取当前价格
        price = data.close[0]
        # 检查价格有效性
        import math
        if price == 0 or math.isnan(price) or math.isinf(price):
            return False

        # 计算买入数量
        cash = self.broker.getcash()
        target_value = cash * self.params.position_size

        # 考虑滑点
        slippage = price * 0.001  # 0.1% 滑点
        actual_price = price + slippage

        shares = int(target_value / actual_price / 100) * 100  # 整手

        if shares <= 0:
            return False

        # 执行买入
        order = self.buy(data=data, size=shares)

        # 记录持仓信息
        self.position_info[code] = {
            "shares": shares,
            "buy_date": self.datas[0].datetime.date(0),
            "buy_price": actual_price,
        }

        # 记录交易
        self.trades.append({
            "date": self.datas[0].datetime.date(0).isoformat(),
            "code": code,
            "action": "buy",
            "price": actual_price,
            "shares": shares,
            "amount": shares * actual_price,
        })

        return True

    def _close_position(self, code: str, reason: str = ""):
        """平仓"""
        if code not in self.position_info:
            return

        # 找到对应的数据源
        data = self._get_data_by_name(code)
        if data is None:
            del self.position_info[code]
            return

        # 获取当前价格
        price = data.close[0]
        # 检查价格有效性
        import math
        if price == 0 or math.isnan(price) or math.isinf(price):
            del self.position_info[code]
            return

        # 考虑滑点
        slippage = price * 0.001
        actual_price = price - slippage

        # 获取持仓数量
        shares = self.position_info[code]["shares"]
        buy_price = self.position_info[code]["buy_price"]

        # 执行卖出
        self.sell(data=data, size=shares)

        # 计算盈亏
        profit = (actual_price - buy_price) * shares

        # 记录交易
        self.trades.append({
            "date": self.datas[0].datetime.date(0).isoformat(),
            "code": code,
            "action": "sell",
            "price": actual_price,
            "shares": shares,
            "amount": shares * actual_price,
            "profit": profit,
            "reason": reason,
        })

        # 删除持仓信息
        del self.position_info[code]

    def _check_expired_positions(self, current_date: datetime.date):
        """检查持仓天数，卖出到期的股票"""
        to_close = []

        for code, info in self.position_info.items():
            buy_date = info["buy_date"]
            days_held = (current_date - buy_date).days

            if days_held >= self.params.hold_days:
                to_close.append((code, f"持有{days_held}天到期"))

        for code, reason in to_close:
            self._close_position(code, reason)

    def _get_data_by_name(self, name: str):
        """根据名称获取数据源"""
        for data in self.datas:
            if hasattr(data, '_name') and data._name == name:
                return data
        return None

    def _record_equity(self, current_date: datetime.date):
        """记录资金曲线"""
        total_value = self.broker.getvalue()
        cash = self.broker.getcash()

        self.equity_curve.append({
            "date": current_date.isoformat(),
            "equity": total_value,
            "cash": cash,
            "positions": len(self.position_info),
        })

    def select_stocks(self) -> List[str]:
        """
        选股逻辑（子类需要实现）

        返回: 选中的股票代码列表
        """
        raise NotImplementedError("子类必须实现 select_stocks 方法")

    def stop(self):
        """回测结束时的处理"""
        # 可以在这里做一些清理工作或输出额外信息
        pass


class RsiMacdStrategy(StockScreenerStrategy):
    """
    RSI超卖 + MACD金叉 选股策略

    参数:
        rsi_period: RSI周期
        rsi_threshold: RSI超卖阈值
        macd_fast: MACD快线周期
        macd_slow: MACD慢线周期
        macd_signal: MACD信号线周期
    """

    params = (
        ('rsi_period', 14),
        ('rsi_threshold', 30),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
    )

    def __init__(self):
        super().__init__()

        # 为每个数据源计算指标
        self.rsi = {}
        self.macd = {}
        self.macd_signal = {}

        for data in self.datas:
            if hasattr(data, '_name'):
                # RSI
                self.rsi[data._name] = bt.indicators.RSI(
                    data.close,
                    period=self.params.rsi_period,
                    plot=False
                )

                # MACD
                macd_line = bt.indicators.MACD(
                    data.close,
                    period_me1=self.params.macd_fast,
                    period_me2=self.params.macd_slow,
                    period_signal=self.params.macd_signal,
                    plot=False
                )
                self.macd[data._name] = macd_line.macd
                self.macd_signal[data._name] = macd_line.signal

    def select_stocks(self) -> List[str]:
        """执行选股"""
        selected = []

        for data in self.datas:
            if not hasattr(data, '_name'):
                continue

            code = data._name
            if code not in self.rsi or code not in self.macd:
                continue

            # 获取最新指标值
            rsi_val = self.rsi[code][0]
            macd_val = self.macd[code][0]
            signal_val = self.macd_signal[code][0]

            # 检查数据有效性
            if (rsi_val != rsi_val or  # NaN check
                macd_val != macd_val or
                signal_val != signal_val):
                continue

            # 选股条件:
            # 1. RSI 超卖 (< threshold)
            # 2. MACD 金叉 (MACD > Signal)
            # 3. 当前没有持仓
            if (rsi_val < self.params.rsi_threshold and
                macd_val > signal_val and
                code not in self.position_info):

                selected.append(code)

        return selected


# 策略工厂
class StrategyFactory:
    """策略工厂"""

    strategies = {
        "rsi_macd": RsiMacdStrategy,
    }

    @classmethod
    def create(cls, strategy_name: str, **params):
        """创建策略实例"""
        if strategy_name not in cls.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy_class = cls.strategies[strategy_name]

        # 合并参数 - 使用 _getitems() 方法获取 (key, value) 对
        strategy_params = {}
        for item in strategy_class.params._getitems():
            if len(item) >= 2:
                key, value = item[0], item[1]
                strategy_params[key] = value

        strategy_params.update(params)

        return type(strategy_name, (strategy_class,), {
            'params': (
                (k, v) for k, v in strategy_params.items()
            )
        })

    @classmethod
    def get_strategy_info(cls) -> List[Dict[str, Any]]:
        """获取所有策略的信息"""
        return [
            {
                "name": "rsi_macd",
                "display_name": "RSI超卖+MACD金叉",
                "description": "当RSI超卖且MACD金叉时买入，持有N天后卖出",
                "category": "oscillator",
                "params": [
                    {"name": "rsi_period", "display_name": "RSI周期", "default": 14, "min": 5, "max": 30},
                    {"name": "rsi_threshold", "display_name": "RSI阈值", "default": 30, "min": 20, "max": 50},
                    {"name": "macd_fast", "display_name": "MACD快线", "default": 12, "min": 5, "max": 20},
                    {"name": "macd_slow", "display_name": "MACD慢线", "default": 26, "min": 15, "max": 40},
                ],
            }
        ]
