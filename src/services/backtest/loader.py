"""
回测数据加载器

从数据库加载股票数据并转换为 Backtrader 可用的格式
"""

import backtrader as bt
from datetime import date, datetime
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import StockBasics, StockDailyK
from src.core.database import get_db


class DataLoader:
    """数据加载器"""

    @staticmethod
    async def load_stock_data(
        codes: List[str],
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> Dict[str, pd.DataFrame]:
        """
        加载多只股票的历史数据

        参数:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            session: 数据库会话

        返回:
            {股票代码: DataFrame} 格式的字典
        """
        result = {}

        for code in codes:
            df = await DataLoader._load_single_stock(code, start_date, end_date, session)
            if df is not None and not df.empty:
                result[code] = df

        return result

    @staticmethod
    async def load_all_stocks(
        start_date: date,
        end_date: date,
        session: AsyncSession,
        market: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        加载所有股票数据

        参数:
            start_date: 开始日期
            end_date: 结束日期
            session: 数据库会话
            market: 市场筛选 (SH/SZ/None)

        返回:
            {股票代码: DataFrame} 格式的字典
        """
        # 获取活跃股票列表
        query = select(StockBasics.code, StockBasics.name).where(
            StockBasics.is_active == True
        )

        if market:
            query = query.where(StockBasics.market == market)

        result = await session.execute(query)
        stock_list = result.all()

        data_dict = {}
        for code, name in stock_list:
            df = await DataLoader._load_single_stock(code, start_date, end_date, session)
            if df is not None and not df.empty:
                df['name'] = name
                data_dict[code] = df

        return data_dict

    @staticmethod
    async def _load_single_stock(
        code: str,
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> Optional[pd.DataFrame]:
        """
        加载单只股票数据

        参数:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            session: 数据库会话

        返回:
            DataFrame 或 None
        """
        query = select(StockDailyK).where(
            StockDailyK.code == code,
            StockDailyK.trade_date >= start_date,
            StockDailyK.trade_date <= end_date,
            StockDailyK.adjust_type == "qfq"  # 使用前复权数据
        ).order_by(StockDailyK.trade_date)

        result = await session.execute(query)
        klines = result.scalars().all()

        if not klines:
            return None

        # 转换为 DataFrame
        data = []
        for k in klines:
            data.append({
                'trade_date': k.trade_date,
                'open': float(k.open_price) if k.open_price else None,
                'high': float(k.high_price) if k.high_price else None,
                'low': float(k.low_price) if k.low_price else None,
                'close': float(k.close_price) if k.close_price else None,
                'volume': int(k.volume) if k.volume else 0,
                'amount': float(k.amount) if k.amount else 0,
            })

        df = pd.DataFrame(data)

        # 删除空值
        df = df.dropna(subset=['open', 'high', 'low', 'close'])

        # 设置日期为索引
        df['datetime'] = pd.to_datetime(df['trade_date'])
        df.set_index('datetime', inplace=True)

        return df

    @staticmethod
    def df_to_feed(df: pd.DataFrame, code: str, name: str = None) -> bt.feeds.PandasData:
        """
        将 DataFrame 转换为 Backtrader 数据源

        参数:
            df: DataFrame (必须有 datetime 索引)
            code: 股票代码
            name: 股票名称

        返回:
            Backtrader Data Feed
        """
        # 确保有所需的列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"DataFrame missing required column: {col}")

        # 创建数据源
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为 datetime
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=None
        )

        # 设置名称
        data._name = code

        return data

    @staticmethod
    async def get_stock_list(
        session: AsyncSession,
        market: Optional[str] = None,
        industry: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        获取股票列表

        参数:
            session: 数据库会话
            market: 市场筛选
            industry: 行业筛选

        返回:
            股票列表 [{"code": "000001", "name": "平安银行"}, ...]
        """
        query = select(StockBasics.code, StockBasics.name, StockBasics.industry).where(
            StockBasics.is_active == True
        )

        if market:
            query = query.where(StockBasics.market == market)

        if industry:
            query = query.where(StockBasics.industry == industry)

        result = await session.execute(query)
        stocks = result.all()

        return [
            {"code": code, "name": name, "industry": ind}
            for code, name, ind in stocks
        ]
