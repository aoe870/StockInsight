"""
定时同步服务
每日收盘后自动同步A股数据
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .sync_service import sync_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时调度服务"""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

    def start(self):
        """启动定时调度器"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.scheduler = AsyncIOScheduler()

        # 每日0点执行（确保BaoStock数据已更新）
        self.scheduler.add_job(
            self._daily_sync_job,
            CronTrigger(hour=0, minute=0),
            id='daily_stock_sync',
            name='Daily A-Stock K-line Sync',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Scheduler started - Daily sync at 00:00 every day")

    def stop(self):
        """停止定时调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler stopped")

    async def _daily_sync_job(self):
        """每日同步任务"""
        try:
            logger.info("=" * 60)
            logger.info("Starting daily A-stock sync job")
            logger.info("=" * 60)

            # 获取所有A股列表
            all_stocks = await sync_service.get_stock_list("cn_a")
            logger.info(f"Total stocks to sync: {len(all_stocks)}")

            # 创建增量同步任务（最近30天）
            task = await sync_service.incremental_sync(
                market="cn_a",
                symbols=all_stocks,
                days=30  # 同步最近30天数据
            )

            logger.info(f"Created incremental sync task: {task.task_id}")
            logger.info(f"Date range: {task.start_date} to {task.end_date}")
            logger.info(f"Stocks: {len(task.symbols)}")

            # 启动同步
            result = await sync_service.start_sync(task)

            logger.info("=" * 60)
            logger.info(f"Daily sync completed: {result}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Daily sync job failed: {e}", exc_info=True)

    async def trigger_manual_sync(self, days: int = 30):
        """手动触发增量同步"""
        logger.info(f"Manual sync triggered for {days} days")

        all_stocks = await sync_service.get_stock_list("cn_a")

        task = await sync_service.incremental_sync(
            market="cn_a",
            symbols=all_stocks,
            days=days
        )

        result = await sync_service.start_sync(task)
        return result

    def get_next_run_time(self) -> Optional[datetime]:
        """获取下次运行时间"""
        if self.scheduler and self.scheduler.running:
            job = self.scheduler.get_job('daily_stock_sync')
            if job:
                return job.next_run_time
        return None

    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self.is_running,
            "next_run_time": self.get_next_run_time(),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time
                }
                for job in self.scheduler.get_jobs()
            ] if self.scheduler else []
        }


# 全局单例
scheduler_service = SchedulerService()
