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

from src.models.stock import StockBasics, StockDailyK, StockCallAuction
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

    # ==================== 集合竞价数据同步 ====================

    @sync_retry(exceptions=(Exception,))
    def fetch_call_auction_realtime(self) -> pd.DataFrame:
        """
        从 AKShare 获取实时集合竞价数据

        Returns:
            包含集合竞价数据的 DataFrame
        """
        self.rate_limiter.acquire_sync()

        try:
            # 获取实时行情数据（包含集合竞价时段数据）
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            # 非交易时段获取数据失败是正常现象，降低日志级别
            logger.info(f"非交易时段，无法获取实时集合竞价数据")
            # 返回空 DataFrame，不会中断流程
            return pd.DataFrame()

    async def sync_call_auction_realtime(
        self,
        session: AsyncSession
    ) -> int:
        """
        同步实时集合竞价数据到数据库

        Args:
            session: 数据库会话

        Returns:
            同步的记录数
        """
        sync_log = SyncLog(
            sync_type="CALL_AUCTION_REALTIME",
            status="RUNNING",
            started_at=datetime.now()
        )
        session.add(sync_log)
        await session.flush()

        try:
            df = self.fetch_call_auction_realtime()

            if df.empty:
                sync_log.records_count = 0
                sync_log.status = "SUCCESS"
                sync_log.finished_at = datetime.now()
                return 0

            count = 0
            today = date.today()
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_time_minutes = current_hour * 60 + current_minute

            # 9:15 = 555 分钟, 15:00 = 900 分钟（下午收盘）
            is_trading_time = 555 <= current_time_minutes <= 900

            for _, row in df.iterrows():
                try:
                    # 获取股票代码（兼容不同的列名）
                    code = None
                    for col in ['代码', 'code', 'symbol']:
                        if col in df.columns:
                            code = str(row[col]).zfill(6)
                            break

                    if not code:
                        continue

                    # 获取价格数据（兼容不同的列名）
                    price = None
                    for col in ['最新价', 'price', 'close', 'current_price']:
                        if col in df.columns:
                            price = row[col]
                            break

                    if pd.isna(price) or price == 0:
                        continue

                    # 获取其他数据
                    volume = 0
                    for col in ['成交量', 'volume', 'vol']:
                        if col in df.columns:
                            volume = row[col]
                            break

                    amount = 0
                    for col in ['成交额', 'amount', 'turnover']:
                        if col in df.columns:
                            amount = row[col]
                            break

                    change_pct = None
                    for col in ['涨跌幅', 'change_pct', 'percent_change']:
                        if col in df.columns:
                            change_pct = row[col]
                            break

                    # 只在交易时段保存数据
                    if not is_trading_time:
                        continue

                    # 记录当前时间
                    auction_time = now.strftime("%H:%M:%S")

                    stmt = insert(StockCallAuction).values(
                        code=code,
                        trade_date=today,
                        auction_time=auction_time,
                        price=float(price) if not pd.isna(price) else None,
                        volume=int(volume) if not pd.isna(volume) and volume else 0,
                        amount=float(amount) if not pd.isna(amount) and amount else None,
                        change_pct=float(change_pct) if not pd.isna(change_pct) else None,
                        data_source="AKShare",
                        update_time=now
                    ).on_conflict_do_nothing()

                    await session.execute(stmt)
                    count += 1

                except Exception as e:
                    logger.warning(f"处理股票 {code} 数据失败: {e}")
                    continue

            sync_log.records_count = count
            sync_log.status = "SUCCESS"
            sync_log.finished_at = datetime.now()

            return count

        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.finished_at = datetime.now()
            raise

    @sync_retry(exceptions=(Exception,))
    def fetch_call_auction_history(
        self,
        code: str,
        date_str: str
    ) -> pd.DataFrame:
        """
        从 AKShare 获取历史集合竞价数据

        Args:
            code: 股票代码
            date_str: 日期字符串 (YYYYMMDD)

        Returns:
            包含集合竞价数据的 DataFrame
        """
        self.rate_limiter.acquire_sync()

        try:
            # 获取盘前分时数据（包含集合竞价时段）
            df = ak.stock_zh_a_hist_pre_min_em(symbol=code, date=date_str)

            # 筛选集合竞价时段的数据 (9:15-9:25)
            if not df.empty and "时间" in df.columns:
                df["时间"] = pd.to_datetime(df["时间"]).dt.time
                df = df[df["时间"].apply(lambda x: x.hour == 9 and 15 <= x.minute <= 25)]

            return df

        except Exception as e:
            logger.warning(f"获取股票 {code} 在 {date_str} 的集合竞价数据失败: {e}")
            return pd.DataFrame()

    async def sync_call_auction_history(
        self,
        session: AsyncSession,
        code: str,
        trade_date: date
    ) -> int:
        """
        同步历史集合竞价数据到数据库

        Args:
            session: 数据库会话
            code: 股票代码
            trade_date: 交易日期

        Returns:
            同步的记录数
        """
        sync_log = SyncLog(
            sync_type="CALL_AUCTION_HISTORY",
            stock_code=code,
            start_date=trade_date,
            status="RUNNING",
            started_at=datetime.now()
        )
        session.add(sync_log)
        await session.flush()

        try:
            df = self.fetch_call_auction_history(
                code=code,
                date_str=trade_date.strftime("%Y%m%d")
            )

            if df.empty:
                sync_log.records_count = 0
                sync_log.status = "SUCCESS"
                sync_log.finished_at = datetime.now()
                return 0

            count = 0
            for _, row in df.iterrows():
                auction_time = row["时间"].strftime("%H:%M:%S")

                stmt = insert(StockCallAuction).values(
                    code=code,
                    trade_date=trade_date,
                    auction_time=auction_time,
                    price=row.get("收盘"),
                    volume=int(row.get("成交量", 0)) if not pd.isna(row.get("成交量")) else 0,
                    amount=row.get("成交额"),
                    change_pct=row.get("涨跌幅"),
                    data_source="AKShare",
                    update_time=datetime.now()
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

    async def sync_call_auction_by_date(
        self,
        session: AsyncSession,
        trade_date: date,
        codes: Optional[list[str]] = None
    ) -> dict[str, int]:
        """
        批量同步指定日期的集合竞价数据

        Args:
            session: 数据库会话
            trade_date: 交易日期
            codes: 股票代码列表，为空时同步全部股票

        Returns:
            每只股票同步的记录数 {code: count}
        """
        results = {}

        # 如果没有指定股票列表，获取全部活跃股票
        if codes is None:
            query = select(StockBasics.code).where(StockBasics.is_active == True)
            result = await session.execute(query)
            codes = [row[0] for row in result.all()]

        for code in codes:
            try:
                count = await self.sync_call_auction_history(session, code, trade_date)
                results[code] = count
            except Exception as e:
                logger.error(f"同步股票 {code} 的集合竞价数据失败: {e}")
                results[code] = -1

        return results

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

