"""
自动数据同步服务
服务启动时自动检测并同步数据
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import StockBasics, StockDailyK
from src.models.user import WatchlistItem
from src.services.data_sync import data_sync_service
from src.core.database import get_db_session
from src.utils.logger import logger


class AutoSyncService:
    """自动同步服务"""

    def __init__(self):
        self.default_history_days = 365  # 默认获取过去一年数据（约250个交易日）
        self.is_running = False
    
    async def check_and_sync_on_startup(self):
        """启动时检查并同步数据"""
        logger.info("=== 启动自动数据同步检查 ===")
        
        async with get_db_session() as session:
            # 1. 检查股票列表
            await self._ensure_stock_list(session)
            
            # 2. 同步自选股K线数据
            await self._sync_watchlist_klines(session)
            
        logger.info("=== 自动数据同步检查完成 ===")
    
    async def _ensure_stock_list(self, session: AsyncSession):
        """确保股票列表存在"""
        # 检查股票列表是否为空
        result = await session.execute(
            select(func.count()).select_from(StockBasics)
        )
        count = result.scalar() or 0
        
        if count == 0:
            logger.info("股票列表为空，开始同步...")
            try:
                synced = await data_sync_service.sync_stock_list(session)
                await session.commit()
                logger.info(f"股票列表同步完成: {synced} 只股票")
            except Exception as e:
                logger.error(f"股票列表同步失败: {e}")
                await session.rollback()
        else:
            logger.info(f"股票列表已存在: {count} 只股票")
    
    async def _sync_watchlist_klines(self, session: AsyncSession):
        """同步自选股的K线数据"""
        try:
            # 获取所有自选股代码（去重）
            result = await session.execute(
                select(WatchlistItem.stock_code).distinct()
            )
            stock_codes = [row[0] for row in result.all()]

            if not stock_codes:
                logger.info("暂无自选股，跳过K线同步")
                return

            logger.info(f"检查 {len(stock_codes)} 只自选股的K线数据...")

            for code in stock_codes:
                await self._sync_single_stock(session, code)
        except Exception as e:
            logger.warning(f"自选股K线同步跳过: {e}")
    
    async def _sync_single_stock(self, session: AsyncSession, code: str):
        """同步单只股票的K线数据"""
        today = date.today()
        
        # 获取该股票最新的K线日期
        result = await session.execute(
            select(func.max(StockDailyK.trade_date))
            .where(StockDailyK.code == code)
            .where(StockDailyK.adjust_type == "qfq")
        )
        latest_date = result.scalar()
        
        if latest_date is None:
            # 没有数据，获取过去30天
            start_date = today - timedelta(days=self.default_history_days)
            logger.info(f"{code}: 无历史数据，获取过去{self.default_history_days}天")
        elif latest_date < today - timedelta(days=1):
            # 数据不是最新的，追加同步
            start_date = latest_date + timedelta(days=1)
            logger.info(f"{code}: 数据截止到 {latest_date}，追加同步")
        else:
            # 数据已是最新
            logger.debug(f"{code}: 数据已是最新 ({latest_date})")
            return
        
        try:
            count = await data_sync_service.sync_daily_k(
                session, code, start_date=start_date, end_date=today
            )
            await session.commit()
            if count > 0:
                logger.info(f"{code}: 同步完成，新增 {count} 条记录")
        except Exception as e:
            logger.error(f"{code}: 同步失败 - {e}")
            await session.rollback()
    
    async def sync_all_watchlist(self):
        """同步所有自选股（供定时任务调用）"""
        if self.is_running:
            logger.warning("同步任务正在运行中，跳过本次执行")
            return
        
        self.is_running = True
        try:
            async with get_db_session() as session:
                await self._sync_watchlist_klines(session)
        finally:
            self.is_running = False


# 全局服务实例
auto_sync_service = AutoSyncService()

