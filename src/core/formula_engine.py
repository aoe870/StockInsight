"""
选股公式解析引擎
支持类通达信公式语法，用于技术指标选股

支持的函数:
- 引用函数: REF, REFV
- 统计函数: MA, EMA, SMA, COUNT, SUM, HHV, LLV, STD
- 逻辑函数: IF, IIF, AND, OR, NOT
- 数学函数: ABS, MAX, MIN, SQRT, POW
- 跨周期: EVERY, EXIST, BARSLAST

支持的变量:
- OPEN, HIGH, LOW, CLOSE, VOL/VOLUME, AMOUNT
- C, O, H, L, V (简写)
"""

import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from src.utils.logger import logger


@dataclass
class FormulaContext:
    """公式执行上下文"""
    # K线数据 DataFrame，包含 open, high, low, close, volume, amount
    df: pd.DataFrame
    # 缓存计算结果
    cache: Dict[str, np.ndarray] = field(default_factory=dict)
    # 当前计算位置（默认最后一行）
    index: int = -1


class FormulaEngine:
    """公式解析和执行引擎"""
    
    def __init__(self):
        self.functions: Dict[str, Callable] = {
            # 移动平均
            'MA': self._ma,
            'EMA': self._ema,
            'SMA': self._sma,
            # 引用函数
            'REF': self._ref,
            # 统计函数
            'COUNT': self._count,
            'SUM': self._sum,
            'HHV': self._hhv,
            'LLV': self._llv,
            'STD': self._std,
            # 条件函数
            'IF': self._if,
            'IIF': self._if,
            # 数学函数
            'ABS': self._abs,
            'MAX': self._max,
            'MIN': self._min,
            'SQRT': self._sqrt,
            'POW': self._pow,
            # 跨周期
            'EVERY': self._every,
            'EXIST': self._exist,
            'BARSLAST': self._barslast,
            # 交叉
            'CROSS': self._cross,
            'CROSSDOWN': self._crossdown,
        }
        
        self.variables = {
            'OPEN': 'open', 'O': 'open',
            'HIGH': 'high', 'H': 'high',
            'LOW': 'low', 'L': 'low',
            'CLOSE': 'close', 'C': 'close',
            'VOL': 'volume', 'VOLUME': 'volume', 'V': 'volume',
            'AMOUNT': 'amount',
        }
    
    def parse_and_execute(self, formula: str, ctx: FormulaContext) -> Any:
        """
        解析并执行公式
        
        Args:
            formula: 公式字符串
            ctx: 执行上下文
        
        Returns:
            计算结果（标量或数组）
        """
        # 移除注释
        formula = re.sub(r'\{[^}]*\}', '', formula)
        formula = formula.strip()
        
        if not formula:
            return None
        
        # 解析多行公式，返回最后一个结果
        lines = [l.strip() for l in formula.split(';') if l.strip()]
        result = None
        
        for line in lines:
            if ':=' in line:
                # 变量定义
                var_name, expr = line.split(':=', 1)
                var_name = var_name.strip()
                result = self._eval_expr(expr.strip(), ctx)
                # 同时存储原始名称和大写名称，确保后续引用能找到
                ctx.cache[var_name] = result
                ctx.cache[var_name.upper()] = result
            else:
                # 直接表达式
                result = self._eval_expr(line, ctx)
        
        return result
    
    def _eval_expr(self, expr: str, ctx: FormulaContext) -> Any:
        """计算单个表达式"""
        expr = expr.strip()
        
        # 检查缓存
        if expr in ctx.cache:
            return ctx.cache[expr]
        
        # 处理逻辑运算符 (AND, OR)
        expr_upper = expr.upper()
        if ' AND ' in expr_upper:
            parts = re.split(r'\s+AND\s+', expr, flags=re.IGNORECASE)
            results = [self._eval_expr(p, ctx) for p in parts]
            return np.all(results, axis=0)
        
        if ' OR ' in expr_upper:
            parts = re.split(r'\s+OR\s+', expr, flags=re.IGNORECASE)
            results = [self._eval_expr(p, ctx) for p in parts]
            return np.any(results, axis=0)
        
        # 处理比较运算符（需要找到不在括号内的运算符）
        for op in ['>=', '<=', '!=', '>', '<', '=']:
            pos = self._find_comparison_operator(expr, op)
            if pos >= 0:
                left = expr[:pos]
                right = expr[pos + len(op):]
                left_val = self._eval_expr(left, ctx)
                right_val = self._eval_expr(right, ctx)
                if op == '>=':
                    return left_val >= right_val
                elif op == '<=':
                    return left_val <= right_val
                elif op == '>':
                    return left_val > right_val
                elif op == '<':
                    return left_val < right_val
                elif op == '=' or op == '!=':
                    eq = left_val == right_val
                    return ~eq if op == '!=' else eq
        
        # 处理算术运算符（注意优先级）
        # 先处理加减
        if '+' in expr or '-' in expr:
            pos = self._find_operator(expr, ['+', '-'])
            if pos > 0:
                left = expr[:pos]
                op = expr[pos]
                right = expr[pos+1:]
                left_val = self._eval_expr(left, ctx)
                right_val = self._eval_expr(right, ctx)
                return left_val + right_val if op == '+' else left_val - right_val

        # 处理乘除
        if '*' in expr or '/' in expr:
            pos = self._find_operator(expr, ['*', '/'])
            if pos > 0:
                left = expr[:pos]
                op = expr[pos]
                right = expr[pos+1:]
                left_val = self._eval_expr(left, ctx)
                right_val = self._eval_expr(right, ctx)
                if op == '/':
                    right_val = np.where(right_val == 0, np.nan, right_val)
                return left_val * right_val if op == '*' else left_val / right_val

        # 处理括号
        if expr.startswith('(') and expr.endswith(')'):
            return self._eval_expr(expr[1:-1], ctx)

        # 处理函数调用
        match = re.match(r'^([A-Z_][A-Z0-9_]*)\s*\((.*)\)$', expr, re.IGNORECASE)
        if match:
            func_name = match.group(1).upper()
            args_str = match.group(2)
            args = self._parse_args(args_str, ctx)
            if func_name in self.functions:
                return self.functions[func_name](ctx, *args)
            raise ValueError(f"未知函数: {func_name}")

        # 处理变量
        var_upper = expr.upper()
        if var_upper in self.variables:
            col = self.variables[var_upper]
            if col in ctx.df.columns:
                return ctx.df[col].values
            raise ValueError(f"数据列不存在: {col}")

        # 检查缓存的变量（支持大小写不敏感 + 原始名称）
        if var_upper in ctx.cache:
            return ctx.cache[var_upper]
        if expr in ctx.cache:
            return ctx.cache[expr]
        # 遍历 cache 进行大小写不敏感匹配
        for key in ctx.cache:
            if key.upper() == var_upper:
                return ctx.cache[key]

        # 尝试解析为数字
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        raise ValueError(f"无法解析表达式: {expr}")

    def _find_operator(self, expr: str, ops: List[str]) -> int:
        """找到不在括号内的运算符位置（从右往左）"""
        depth = 0
        for i in range(len(expr) - 1, -1, -1):
            c = expr[i]
            if c == ')':
                depth += 1
            elif c == '(':
                depth -= 1
            elif depth == 0 and c in ops:
                return i
        return -1

    def _find_comparison_operator(self, expr: str, op: str) -> int:
        """找到不在括号内的比较运算符位置（从左往右）"""
        depth = 0
        i = 0
        while i < len(expr):
            c = expr[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif depth == 0:
                # 检查是否匹配运算符
                if expr[i:i+len(op)] == op:
                    # 对于 > 和 <，需要确保不是 >= 或 <=
                    if op == '>' and i + 1 < len(expr) and expr[i + 1] == '=':
                        i += 1
                        continue
                    if op == '<' and i + 1 < len(expr) and expr[i + 1] == '=':
                        i += 1
                        continue
                    if op == '=' and i > 0 and expr[i - 1] in ['>', '<', '!']:
                        i += 1
                        continue
                    return i
            i += 1
        return -1

    def _parse_args(self, args_str: str, ctx: FormulaContext) -> List[Any]:
        """解析函数参数"""
        args = []
        depth = 0
        current = []

        for c in args_str:
            if c == '(':
                depth += 1
                current.append(c)
            elif c == ')':
                depth -= 1
                current.append(c)
            elif c == ',' and depth == 0:
                arg_str = ''.join(current).strip()
                if arg_str:
                    args.append(self._eval_expr(arg_str, ctx))
                current = []
            else:
                current.append(c)

        if current:
            arg_str = ''.join(current).strip()
            if arg_str:
                args.append(self._eval_expr(arg_str, ctx))

        return args

    # ========== 函数实现 ==========

    def _ma(self, ctx: FormulaContext, data: np.ndarray, period: int) -> np.ndarray:
        """简单移动平均"""
        return pd.Series(data).rolling(window=int(period)).mean().values

    def _ema(self, ctx: FormulaContext, data: np.ndarray, period: int) -> np.ndarray:
        """指数移动平均"""
        return pd.Series(data).ewm(span=int(period), adjust=False).mean().values

    def _sma(self, ctx: FormulaContext, data: np.ndarray, n: int, m: int = 1) -> np.ndarray:
        """加权移动平均 SMA(X, N, M) = (M*X + (N-M)*REF(SMA, 1)) / N"""
        n, m = int(n), int(m)
        result = np.full(len(data), np.nan)
        # 找到第一个非NaN值作为起点
        start_idx = 0
        for i in range(len(data)):
            if not np.isnan(data[i]):
                result[i] = data[i]
                start_idx = i
                break
        # 从起点开始计算
        for i in range(start_idx + 1, len(data)):
            if np.isnan(data[i]):
                result[i] = result[i-1] if i > 0 else np.nan
            elif np.isnan(result[i-1]):
                result[i] = data[i]
            else:
                result[i] = (m * data[i] + (n - m) * result[i-1]) / n
        return result

    def _ref(self, ctx: FormulaContext, data: np.ndarray, n: int) -> np.ndarray:
        """引用N周期前的值"""
        n = int(n)
        result = np.full(len(data), np.nan)
        if n < len(data):
            result[n:] = data[:-n]
        return result

    def _count(self, ctx: FormulaContext, cond: np.ndarray, n: int) -> np.ndarray:
        """统计N周期内满足条件的次数"""
        n = int(n)
        cond = cond.astype(float)
        return pd.Series(cond).rolling(window=n).sum().values

    def _sum(self, ctx: FormulaContext, data: np.ndarray, n: int) -> np.ndarray:
        """N周期求和"""
        return pd.Series(data).rolling(window=int(n)).sum().values

    def _hhv(self, ctx: FormulaContext, data: np.ndarray, n: int) -> np.ndarray:
        """N周期最高值"""
        return pd.Series(data).rolling(window=int(n)).max().values

    def _llv(self, ctx: FormulaContext, data: np.ndarray, n: int) -> np.ndarray:
        """N周期最低值"""
        return pd.Series(data).rolling(window=int(n)).min().values

    def _std(self, ctx: FormulaContext, data: np.ndarray, n: int) -> np.ndarray:
        """N周期标准差"""
        return pd.Series(data).rolling(window=int(n)).std().values

    def _if(self, ctx: FormulaContext, cond: np.ndarray, val1: Any, val2: Any) -> np.ndarray:
        """条件函数"""
        return np.where(cond, val1, val2)

    def _abs(self, ctx: FormulaContext, data: np.ndarray) -> np.ndarray:
        return np.abs(data)

    def _max(self, ctx: FormulaContext, *args) -> np.ndarray:
        return np.maximum.reduce(args)

    def _min(self, ctx: FormulaContext, *args) -> np.ndarray:
        return np.minimum.reduce(args)

    def _sqrt(self, ctx: FormulaContext, data: np.ndarray) -> np.ndarray:
        return np.sqrt(data)

    def _pow(self, ctx: FormulaContext, base: np.ndarray, exp: float) -> np.ndarray:
        return np.power(base, exp)

    def _every(self, ctx: FormulaContext, cond: np.ndarray, n: int) -> np.ndarray:
        """N周期内是否全部满足条件"""
        n = int(n)
        count = self._count(ctx, cond, n)
        return count >= n

    def _exist(self, ctx: FormulaContext, cond: np.ndarray, n: int) -> np.ndarray:
        """N周期内是否存在满足条件"""
        n = int(n)
        count = self._count(ctx, cond, n)
        return count > 0

    def _barslast(self, ctx: FormulaContext, cond: np.ndarray) -> np.ndarray:
        """上一次条件成立到现在的周期数"""
        result = np.zeros(len(cond))
        last_true = -1
        for i in range(len(cond)):
            if cond[i]:
                last_true = i
            result[i] = i - last_true if last_true >= 0 else np.nan
        return result

    def _cross(self, ctx: FormulaContext, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """金叉: A上穿B"""
        prev_a = self._ref(ctx, a, 1)
        prev_b = self._ref(ctx, b, 1)
        return (prev_a <= prev_b) & (a > b)

    def _crossdown(self, ctx: FormulaContext, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """死叉: A下穿B"""
        prev_a = self._ref(ctx, a, 1)
        prev_b = self._ref(ctx, b, 1)
        return (prev_a >= prev_b) & (a < b)

    def get_last_value(self, result: Any) -> bool:
        """获取最后一个值（用于选股判断）"""
        if isinstance(result, np.ndarray):
            val = result[-1]
            if np.isnan(val):
                return False
            return bool(val)
        return bool(result)


# 全局引擎实例
formula_engine = FormulaEngine()

