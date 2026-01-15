"""
数据同步服务
负责从 AKShare 获取股票数据并存入数据库
"""

from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.models.stock import StockBasics, StockDailyK
from src.models.alert import SyncLog
from src.core.database import get_db_session
from src.utils.logger import logger
from src.utils.retry import sync_retry, RateLimiter


class DataSyncService:
    """数据同步服务类"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(rate=5)  # 每秒5次请求
    
    # ==================== 股票列表同步 ====================
    
    @sync_retry(exceptions=(Exception,))
    def fetch_stock_list(self) -> pd.DataFrame:
        """
        从 AKShare 获取 A 股股票列表
        
        Returns:
            包含股票代码、名称等信息的 DataFrame
        """
        self.rate_limiter.acquire_sync()

        # 获取沪深A股列表
        df = ak.stock_info_a_code_name()
        return df
    
    async def sync_stock_list(self, session: AsyncSession) -> int:
        """
        同步股票列表到数据库
        
        Returns:
            同步的记录数
        """
        # 创建同步日志
        sync_log = SyncLog(
            sync_type="STOCK_LIST",
            status="RUNNING",
            started_at=datetime.now()
        )
        session.add(sync_log)
        await session.flush()
        
        try:
            df = self.fetch_stock_list()
            
            count = 0
            for _, row in df.iterrows():
                code = str(row["code"]).zfill(6)
                name = row["name"]
                
                # 判断市场
                if code.startswith(("60", "68")):
                    market = "SH"
                elif code.startswith(("00", "30")):
                    market = "SZ"
                elif code.startswith(("8", "4")):
                    market = "BJ"
                else:
                    market = "OTHER"
                
                # 使用 upsert 插入或更新
                stmt = insert(StockBasics).values(
                    code=code,
                    name=name,
                    market=market,
                    is_active=True,
                    updated_at=datetime.now()
                ).on_conflict_do_update(
                    index_elements=["code"],
                    set_={
                        "name": name,
                        "market": market,
                        "is_active": True,
                        "updated_at": datetime.now()
                    }
                )
                await session.execute(stmt)
                count += 1
            
            # 更新同步日志
            sync_log.records_count = count
            sync_log.status = "SUCCESS"
            sync_log.finished_at = datetime.now()

            return count

        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.finished_at = datetime.now()
            raise
    
    # ==================== 日K线数据同步 ====================
    
    @sync_retry(exceptions=(Exception,))
    def fetch_kline(
        self,
        code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        从 AKShare 获取K线数据

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期类型 (daily-日线, weekly-周线, monthly-月线)
            adjust: 复权类型 (qfq-前复权, hfq-后复权, 空-不复权)

        Returns:
            K线数据 DataFrame
        """
        self.rate_limiter.acquire_sync()

        # 判断市场并构造完整代码
        if code.startswith(("60", "68")):
            symbol = f"sh{code}"
        else:
            symbol = f"sz{code}"

        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust if adjust else ""
        )

        return df

    # 兼容旧方法名
    def fetch_daily_k(self, code: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """兼容旧方法"""
        return self.fetch_kline(code, start_date, end_date, period="daily", adjust=adjust)
    
    async def get_latest_date(
        self,
        session: AsyncSession,
        code: str,
        adjust_type: str = "qfq"
    ) -> Optional[date]:
        """获取数据库中某股票的最新交易日期"""
        result = await session.execute(
            select(func.max(StockDailyK.trade_date))
            .where(StockDailyK.code == code)
            .where(StockDailyK.adjust_type == adjust_type)
        )
        return result.scalar()

    async def sync_daily_k(
        self,
        session: AsyncSession,
        code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust: str = "qfq"
    ) -> int:
        """
        同步单只股票的日K线数据

        Args:
            session: 数据库会话
            code: 股票代码
            start_date: 开始日期，默认为数据库最新日期+1
            end_date: 结束日期，默认为今天
            adjust: 复权类型

        Returns:
            同步的记录数
        """
        # 确定日期范围
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            latest = await self.get_latest_date(session, code, adjust)
            if latest:
                start_date = latest + timedelta(days=1)
            else:
                # 默认获取全量历史数据（从1990年中国股市成立开始）
                start_date = date(1990, 12, 19)

        # 如果开始日期已超过结束日期，无需同步
        if start_date > end_date:
            return 0

        # 创建同步日志
        sync_log = SyncLog(
            sync_type="DAILY_K",
            stock_code=code,
            start_date=start_date,
            end_date=end_date,
            status="RUNNING",
            started_at=datetime.now()
        )
        session.add(sync_log)
        await session.flush()

        try:
            # 获取数据
            df = self.fetch_daily_k(
                code=code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=adjust
            )

            if df.empty:
                sync_log.records_count = 0
                sync_log.status = "SUCCESS"
                sync_log.finished_at = datetime.now()
                return 0

            # 批量插入数据
            count = 0
            for _, row in df.iterrows():
                trade_date = pd.to_datetime(row["日期"]).date()

                stmt = insert(StockDailyK).values(
                    code=code,
                    trade_date=trade_date,
                    open_price=row.get("开盘"),
                    close_price=row.get("收盘"),
                    high_price=row.get("最高"),
                    low_price=row.get("最低"),
                    volume=int(row.get("成交量", 0)),
                    amount=row.get("成交额"),
                    adjust_type=adjust,
                    change_pct=row.get("涨跌幅"),
                    turnover=row.get("换手率"),
                ).on_conflict_do_nothing()

                await session.execute(stmt)
                count += 1

            sync_log.records_count = count
            sync_log.status = "SUCCESS"
            sync_log.finished_at = datetime.now()

            return count

        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.finished_at = datetime.now()
            raise

    async def sync_watchlist_daily_k(
        self,
        session: AsyncSession,
        stock_codes: list[str],
        adjust: str = "qfq"
    ) -> dict[str, int]:
        """
        批量同步自选股的日K线数据

        Args:
            session: 数据库会话
            stock_codes: 股票代码列表
            adjust: 复权类型

        Returns:
            每只股票同步的记录数 {code: count}
        """
        results = {}

        for code in stock_codes:
            try:
                count = await self.sync_daily_k(session, code, adjust=adjust)
                results[code] = count
            except Exception:
                results[code] = -1

        return results


# 全局服务实例
data_sync_service = DataSyncService()

