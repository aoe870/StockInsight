"""
技术指标计算模块
使用 pandas-ta 计算各类技术指标

支持的指标:
- 趋势类: MA, EMA, SAR, TRIX, DMA
- 震荡类: KDJ, RSI, CCI, WR, ROC, BIAS
- 压力支撑类: BOLL, ATR, BBI
- 量能类: VOL, OBV, VWAP, VR
- 综合类: DMI, MACD, PSY
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import pandas_ta as ta

from src.utils.logger import logger


@dataclass
class IndicatorParams:
    """指标参数配置"""
    # 均线参数
    ma_periods: list[int] = None
    ema_periods: list[int] = None
    # MACD 参数
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # RSI 参数
    rsi_period: int = 14
    # KDJ 参数
    kdj_period: int = 9
    kdj_signal_k: int = 3
    kdj_signal_d: int = 3
    # 布林带参数
    boll_period: int = 20
    boll_std: float = 2.0
    # CCI 参数
    cci_period: int = 14
    # WR 参数
    wr_period: int = 14
    # ATR 参数
    atr_period: int = 14
    # ROC 参数
    roc_period: int = 12
    # TRIX 参数
    trix_period: int = 12
    # DMI 参数
    dmi_period: int = 14
    # PSY 参数
    psy_period: int = 12
    # BIAS 参数
    bias_periods: list[int] = None
    # VR 参数
    vr_period: int = 26

    def __post_init__(self):
        if self.ma_periods is None:
            self.ma_periods = [5, 10, 20, 60, 120, 250]
        if self.ema_periods is None:
            self.ema_periods = [12, 26]
        if self.bias_periods is None:
            self.bias_periods = [6, 12, 24]


class TechnicalIndicators:
    """技术指标计算类"""

    # 可用指标分类
    INDICATOR_CATEGORIES = {
        "trend": ["MA", "EMA", "SAR", "TRIX", "DMA"],
        "oscillator": ["KDJ", "RSI", "CCI", "WR", "ROC", "BIAS"],
        "volatility": ["BOLL", "ATR", "BBI"],
        "volume": ["VOL", "OBV", "VWAP", "VR"],
        "composite": ["DMI", "MACD", "PSY"],
    }

    def __init__(self, params: Optional[IndicatorParams] = None):
        self.params = params or IndicatorParams()

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有基础技术指标"""
        df = df.copy()
        df = self._standardize_columns(df)

        # 基础指标
        df = self.calculate_ma(df)
        df = self.calculate_ema(df)
        df = self.calculate_macd(df)
        df = self.calculate_rsi(df)
        df = self.calculate_kdj(df)
        df = self.calculate_boll(df)

        return df

    def calculate_selected(self, df: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
        """计算指定的技术指标"""
        df = df.copy()
        df = self._standardize_columns(df)

        indicator_methods = {
            "MA": self.calculate_ma,
            "EMA": self.calculate_ema,
            "MACD": self.calculate_macd,
            "RSI": self.calculate_rsi,
            "KDJ": self.calculate_kdj,
            "BOLL": self.calculate_boll,
            "CCI": self.calculate_cci,
            "WR": self.calculate_wr,
            "ATR": self.calculate_atr,
            "ROC": self.calculate_roc,
            "TRIX": self.calculate_trix,
            "DMI": self.calculate_dmi,
            "SAR": self.calculate_sar,
            "OBV": self.calculate_obv,
            "VWAP": self.calculate_vwap,
            "BIAS": self.calculate_bias,
            "PSY": self.calculate_psy,
            "VR": self.calculate_vr,
            "BBI": self.calculate_bbi,
            "DMA": self.calculate_dma,
            "VOL": self.calculate_vol,
        }

        for indicator in indicators:
            indicator_upper = indicator.upper()
            if indicator_upper in indicator_methods:
                df = indicator_methods[indicator_upper](df)

        return df

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
            "成交量": "volume", "成交额": "amount", "日期": "date",
            "open_price": "open", "close_price": "close",
            "high_price": "high", "low_price": "low",
        }
        df = df.rename(columns=column_mapping)
        return df

    # ==================== 趋势类指标 ====================

    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """MA - 简单移动平均线"""
        for period in self.params.ma_periods:
            df[f"ma{period}"] = ta.sma(df["close"], length=period)
        return df

    def calculate_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """EMA - 指数移动平均线"""
        for period in self.params.ema_periods:
            df[f"ema{period}"] = ta.ema(df["close"], length=period)
        return df

    def calculate_sar(self, df: pd.DataFrame) -> pd.DataFrame:
        """SAR - 抛物线指标"""
        sar = ta.psar(df["high"], df["low"], df["close"])
        if sar is not None:
            df["sar_long"] = sar.iloc[:, 0]   # 多头SAR
            df["sar_short"] = sar.iloc[:, 1]  # 空头SAR
            df["sar_af"] = sar.iloc[:, 2]     # 加速因子
            df["sar_reversal"] = sar.iloc[:, 3]  # 反转信号
        return df

    def calculate_trix(self, df: pd.DataFrame) -> pd.DataFrame:
        """TRIX - 三重指数平滑平均"""
        trix = ta.trix(df["close"], length=self.params.trix_period)
        if trix is not None:
            df["trix"] = trix.iloc[:, 0]
            df["trix_signal"] = trix.iloc[:, 1] if trix.shape[1] > 1 else ta.sma(trix.iloc[:, 0], 9)
        return df

    def calculate_dma(self, df: pd.DataFrame) -> pd.DataFrame:
        """DMA - 平均差"""
        ma10 = ta.sma(df["close"], length=10)
        ma50 = ta.sma(df["close"], length=50)
        df["dma"] = ma10 - ma50
        df["dma_ama"] = ta.sma(df["dma"], length=10)
        return df

    # ==================== 震荡/超买超卖类指标 ====================

    def calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """KDJ - 随机指标"""
        stoch = ta.stoch(df["high"], df["low"], df["close"],
                        k=self.params.kdj_period,
                        d=self.params.kdj_signal_k,
                        smooth_d=self.params.kdj_signal_d)
        if stoch is not None:
            df["k"] = stoch.iloc[:, 0]
            df["d"] = stoch.iloc[:, 1]
            df["j"] = 3 * df["k"] - 2 * df["d"]
        return df

    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI - 相对强弱指标"""
        df["rsi"] = ta.rsi(df["close"], length=self.params.rsi_period)
        df["rsi6"] = ta.rsi(df["close"], length=6)
        df["rsi12"] = ta.rsi(df["close"], length=12)
        df["rsi24"] = ta.rsi(df["close"], length=24)
        return df

    def calculate_cci(self, df: pd.DataFrame) -> pd.DataFrame:
        """CCI - 顺势指标"""
        df["cci"] = ta.cci(df["high"], df["low"], df["close"], length=self.params.cci_period)
        return df

    def calculate_wr(self, df: pd.DataFrame) -> pd.DataFrame:
        """WR - 威廉指标"""
        df["wr"] = ta.willr(df["high"], df["low"], df["close"], length=self.params.wr_period)
        df["wr6"] = ta.willr(df["high"], df["low"], df["close"], length=6)
        return df

    def calculate_roc(self, df: pd.DataFrame) -> pd.DataFrame:
        """ROC - 变动率指标"""
        df["roc"] = ta.roc(df["close"], length=self.params.roc_period)
        df["roc_ma"] = ta.sma(df["roc"], length=6)
        return df

    def calculate_bias(self, df: pd.DataFrame) -> pd.DataFrame:
        """BIAS - 乖离率"""
        for period in self.params.bias_periods:
            ma = ta.sma(df["close"], length=period)
            df[f"bias{period}"] = (df["close"] - ma) / ma * 100
        return df

    # ==================== 压力、支撑与波动类指标 ====================

    def calculate_boll(self, df: pd.DataFrame) -> pd.DataFrame:
        """BOLL - 布林带"""
        bbands = ta.bbands(df["close"], length=self.params.boll_period, std=self.params.boll_std)
        if bbands is not None:
            df["boll_lower"] = bbands.iloc[:, 0]
            df["boll_mid"] = bbands.iloc[:, 1]
            df["boll_upper"] = bbands.iloc[:, 2]
            df["boll_bandwidth"] = bbands.iloc[:, 3] if bbands.shape[1] > 3 else None
        return df

    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """ATR - 真实波幅"""
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=self.params.atr_period)
        return df

    def calculate_bbi(self, df: pd.DataFrame) -> pd.DataFrame:
        """BBI - 多空指标"""
        ma3 = ta.sma(df["close"], length=3)
        ma6 = ta.sma(df["close"], length=6)
        ma12 = ta.sma(df["close"], length=12)
        ma24 = ta.sma(df["close"], length=24)
        df["bbi"] = (ma3 + ma6 + ma12 + ma24) / 4
        return df

    # ==================== 量能类指标 ====================

    def calculate_vol(self, df: pd.DataFrame) -> pd.DataFrame:
        """VOL - 成交量及均量"""
        df["vol"] = df["volume"]
        df["vol_ma5"] = ta.sma(df["volume"], length=5)
        df["vol_ma10"] = ta.sma(df["volume"], length=10)
        df["vol_ma20"] = ta.sma(df["volume"], length=20)
        return df

    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """OBV - 能量潮"""
        df["obv"] = ta.obv(df["close"], df["volume"])
        df["obv_ma"] = ta.sma(df["obv"], length=30)
        return df

    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """VWAP - 成交量加权平均价"""
        if "amount" in df.columns and df["amount"].notna().any():
            df["vwap"] = df["amount"] / df["volume"]
        else:
            # 使用典型价格近似
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
        return df

    def calculate_vr(self, df: pd.DataFrame) -> pd.DataFrame:
        """VR - 成交量比率"""
        period = self.params.vr_period
        price_change = df["close"].diff()

        up_vol = df["volume"].where(price_change > 0, 0)
        down_vol = df["volume"].where(price_change < 0, 0)
        flat_vol = df["volume"].where(price_change == 0, 0)

        sum_up = up_vol.rolling(period).sum()
        sum_down = down_vol.rolling(period).sum()
        sum_flat = flat_vol.rolling(period).sum()

        df["vr"] = (sum_up + sum_flat / 2) / (sum_down + sum_flat / 2) * 100
        df["vr_ma"] = ta.sma(df["vr"], length=6)
        return df

    # ==================== 综合类指标 ====================

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD - 指数平滑异同移动平均"""
        macd = ta.macd(df["close"],
                      fast=self.params.macd_fast,
                      slow=self.params.macd_slow,
                      signal=self.params.macd_signal)
        if macd is not None:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 2]
            df["macd_hist"] = macd.iloc[:, 1]
        return df

    def calculate_dmi(self, df: pd.DataFrame) -> pd.DataFrame:
        """DMI - 动向指标"""
        adx = ta.adx(df["high"], df["low"], df["close"], length=self.params.dmi_period)
        if adx is not None:
            df["adx"] = adx.iloc[:, 0]      # ADX
            df["dmp"] = adx.iloc[:, 1]      # +DI
            df["dmn"] = adx.iloc[:, 2]      # -DI
        return df

    def calculate_psy(self, df: pd.DataFrame) -> pd.DataFrame:
        """PSY - 心理线"""
        price_change = df["close"].diff()
        up_days = (price_change > 0).astype(int)
        df["psy"] = up_days.rolling(self.params.psy_period).sum() / self.params.psy_period * 100
        df["psy_ma"] = ta.sma(df["psy"], length=6)
        return df


class SignalDetector:
    """信号检测类"""

    @staticmethod
    def detect_ma_cross(df: pd.DataFrame, short: int = 5, long: int = 20) -> pd.DataFrame:
        """
        检测均线金叉/死叉

        Returns:
            添加 ma_cross_signal 列: 1=金叉, -1=死叉, 0=无信号
        """
        short_ma = f"ma{short}"
        long_ma = f"ma{long}"

        if short_ma not in df.columns or long_ma not in df.columns:
            df["ma_cross_signal"] = 0
            return df

        df["ma_cross_signal"] = 0

        # 金叉: 短期均线从下方穿越长期均线
        golden_cross = (df[short_ma].shift(1) < df[long_ma].shift(1)) & (df[short_ma] > df[long_ma])
        df.loc[golden_cross, "ma_cross_signal"] = 1

        # 死叉: 短期均线从上方穿越长期均线
        death_cross = (df[short_ma].shift(1) > df[long_ma].shift(1)) & (df[short_ma] < df[long_ma])
        df.loc[death_cross, "ma_cross_signal"] = -1

        return df

    @staticmethod
    def detect_macd_cross(df: pd.DataFrame) -> pd.DataFrame:
        """
        检测 MACD 金叉/死叉

        Returns:
            添加 macd_cross_signal 列: 1=金叉, -1=死叉, 0=无信号
        """
        if "macd" not in df.columns or "macd_signal" not in df.columns:
            df["macd_cross_signal"] = 0
            return df

        df["macd_cross_signal"] = 0

        # MACD 金叉
        golden = (df["macd"].shift(1) < df["macd_signal"].shift(1)) & (df["macd"] > df["macd_signal"])
        df.loc[golden, "macd_cross_signal"] = 1

        # MACD 死叉
        death = (df["macd"].shift(1) > df["macd_signal"].shift(1)) & (df["macd"] < df["macd_signal"])
        df.loc[death, "macd_cross_signal"] = -1

        return df

    @staticmethod
    def detect_rsi_extreme(df: pd.DataFrame, overbought: float = 80, oversold: float = 20) -> pd.DataFrame:
        """
        检测 RSI 超买超卖

        Returns:
            添加 rsi_signal 列: 1=超卖反弹, -1=超买回落, 0=无信号
        """
        if "rsi" not in df.columns:
            df["rsi_signal"] = 0
            return df

        df["rsi_signal"] = 0

        # 从超卖区回升
        oversold_recover = (df["rsi"].shift(1) < oversold) & (df["rsi"] >= oversold)
        df.loc[oversold_recover, "rsi_signal"] = 1

        # 从超买区回落
        overbought_fall = (df["rsi"].shift(1) > overbought) & (df["rsi"] <= overbought)
        df.loc[overbought_fall, "rsi_signal"] = -1

        return df

    @staticmethod
    def detect_boll_break(df: pd.DataFrame) -> pd.DataFrame:
        """
        检测布林带突破

        Returns:
            添加 boll_signal 列: 1=突破上轨, -1=跌破下轨, 0=无信号
        """
        if "boll_upper" not in df.columns or "boll_lower" not in df.columns:
            df["boll_signal"] = 0
            return df

        df["boll_signal"] = 0

        # 突破上轨
        break_upper = (df["close"].shift(1) <= df["boll_upper"].shift(1)) & (df["close"] > df["boll_upper"])
        df.loc[break_upper, "boll_signal"] = 1

        # 跌破下轨
        break_lower = (df["close"].shift(1) >= df["boll_lower"].shift(1)) & (df["close"] < df["boll_lower"])
        df.loc[break_lower, "boll_signal"] = -1

        return df

    @staticmethod
    def detect_volume_surge(df: pd.DataFrame, ratio: float = 2.0, days: int = 5) -> pd.DataFrame:
        """
        检测成交量异动

        Args:
            ratio: 放量倍数阈值
            days: 对比均量的天数

        Returns:
            添加 volume_signal 列: 1=放量, 0=正常
        """
        if "volume" not in df.columns:
            df["volume_signal"] = 0
            return df

        # 计算前N日均量
        df["volume_ma"] = df["volume"].rolling(window=days).mean().shift(1)
        df["volume_ratio"] = df["volume"] / df["volume_ma"]

        df["volume_signal"] = 0
        df.loc[df["volume_ratio"] >= ratio, "volume_signal"] = 1

        return df

    @classmethod
    def detect_all_signals(cls, df: pd.DataFrame) -> pd.DataFrame:
        """检测所有信号"""
        df = cls.detect_ma_cross(df)
        df = cls.detect_macd_cross(df)
        df = cls.detect_rsi_extreme(df)
        df = cls.detect_boll_break(df)
        df = cls.detect_volume_surge(df)
        return df


# 导出
__all__ = ["TechnicalIndicators", "SignalDetector", "IndicatorParams"]

