"""
定时任务调度服务
使用 APScheduler 实现定时数据同步
"""

from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.utils.logger import logger


class SchedulerService:
    """定时任务调度服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """设置定时任务"""
        # 1. 盘后同步任务 - 每个交易日 15:30 执行
        self.scheduler.add_job(
            self._sync_after_market,
            CronTrigger(
                day_of_week='mon-fri',  # 周一到周五
                hour=15,
                minute=30,
                timezone='Asia/Shanghai'
            ),
            id='sync_after_market',
            name='盘后数据同步',
            replace_existing=True
        )
        
        # 2. 股票列表更新 - 每周一 9:00 执行
        self.scheduler.add_job(
            self._sync_stock_list,
            CronTrigger(
                day_of_week='mon',
                hour=9,
                minute=0,
                timezone='Asia/Shanghai'
            ),
            id='sync_stock_list_weekly',
            name='每周更新股票列表',
            replace_existing=True
        )
        
        # 3. 盘中定时检查 - 交易时段每30分钟
        self.scheduler.add_job(
            self._sync_during_market,
            CronTrigger(
                day_of_week='mon-fri',
                hour='9-11,13-14',  # 9:00-11:59, 13:00-14:59
                minute='0,30',
                timezone='Asia/Shanghai'
            ),
            id='sync_during_market',
            name='盘中数据更新',
            replace_existing=True
        )
    
    async def _sync_after_market(self):
        """盘后同步任务"""
        logger.info("[定时任务] 执行盘后数据同步...")
        try:
            from src.services.auto_sync import auto_sync_service
            await auto_sync_service.sync_all_watchlist()
            logger.info("[定时任务] 盘后数据同步完成")
        except Exception as e:
            logger.error(f"[定时任务] 盘后同步失败: {e}")
    
    async def _sync_stock_list(self):
        """每周更新股票列表"""
        logger.info("[定时任务] 执行股票列表更新...")
        try:
            from src.services.data_sync import data_sync_service
            from src.core.database import get_db_session
            
            async with get_db_session() as session:
                count = await data_sync_service.sync_stock_list(session)
                await session.commit()
                logger.info(f"[定时任务] 股票列表更新完成: {count} 只股票")
        except Exception as e:
            logger.error(f"[定时任务] 股票列表更新失败: {e}")
    
    async def _sync_during_market(self):
        """盘中数据更新（可选，用于实时性要求高的场景）"""
        # 检查是否为交易时间
        now = datetime.now()
        current_time = now.time()
        
        # 交易时间: 9:30-11:30, 13:00-15:00
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        is_trading_time = (
            (morning_start <= current_time <= morning_end) or
            (afternoon_start <= current_time <= afternoon_end)
        )
        
        if not is_trading_time:
            logger.debug("[定时任务] 非交易时间，跳过盘中同步")
            return
        
        logger.info("[定时任务] 执行盘中数据更新...")
        try:
            from src.services.auto_sync import auto_sync_service
            await auto_sync_service.sync_all_watchlist()
            logger.info("[定时任务] 盘中数据更新完成")
        except Exception as e:
            logger.error(f"[定时任务] 盘中同步失败: {e}")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
            self._log_jobs()
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("定时任务调度器已关闭")
    
    def _log_jobs(self):
        """打印所有定时任务"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"已注册 {len(jobs)} 个定时任务:")
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")


# 全局调度器实例
scheduler_service = SchedulerService()

