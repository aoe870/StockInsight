#!/usr/bin/env python
r"""
每日增量同步脚本 - 追加缺失的K线数据

功能：
  - 检查每只股票的最新K线日期
  - 只同步缺失的数据（从最新日期+1天到今天）
  - 适合作为每日定时任务运行

用法: 
  .venv\Scripts\python.exe sync_daily_update.py [选项]

选项:
    --workers N     并发数量，默认10（增量更新可以更快）
    --limit N       处理股票数量限制，默认全部
    --force         强制同步最近7天数据（忽略已有数据检查）

定时任务设置（Windows 任务计划程序）:
    触发器: 每个工作日 16:00
    操作: .venv\Scripts\python.exe sync_daily_update.py
"""

import asyncio
import argparse
import sys
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import select, func

# 添加项目路径
sys.path.insert(0, ".")

from src.core.database import get_db_session
from src.models.stock import StockBasics, StockDailyK
from src.services.data_sync import data_sync_service


class DailyUpdateStats:
    """每日更新统计"""
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.updated = 0  # 有更新的股票数
        self.skipped = 0  # 已是最新的股票数
        self.failed = 0
        self.new_records = 0
        self.lock = asyncio.Lock()

    async def update(self, status: str, records: int = 0):
        async with self.lock:
            self.completed += 1
            if status == "updated":
                self.updated += 1
                self.new_records += records
            elif status == "skipped":
                self.skipped += 1
            else:
                self.failed += 1

    def progress(self) -> str:
        return f"[{self.completed}/{self.total}]"


async def get_stock_latest_date(session, code: str, adjust: str = "qfq") -> Optional[date]:
    """获取股票最新K线日期"""
    result = await session.execute(
        select(func.max(StockDailyK.trade_date)).where(
            StockDailyK.code == code,
            StockDailyK.adjust_type == adjust
        )
    )
    return result.scalar()


async def sync_single_stock_incremental(
    code: str, 
    name: str, 
    stats: DailyUpdateStats,
    force_days: int = None
):
    """增量同步单只股票"""
    import time
    start_time = time.time()
    today = date.today()

    try:
        async with get_db_session() as session:
            # 获取最新日期
            latest_date = await get_stock_latest_date(session, code)

            if force_days:
                # 强制模式：同步最近N天
                start_date = today - timedelta(days=force_days)
            elif latest_date is None:
                # 没有数据，跳过（应该先运行全量同步）
                await stats.update("skipped")
                print(f"{stats.progress()} 跳过: {code} {name} (无历史数据，请先运行全量同步)")
                return
            elif latest_date >= today - timedelta(days=1):
                # 数据已是最新（允许1天延迟，因为当天可能还没收盘）
                await stats.update("skipped")
                elapsed = time.time() - start_time
                print(f"{stats.progress()} 最新: {code} {name} ({latest_date}) ({elapsed:.1f}s)")
                return
            else:
                # 需要追加同步
                start_date = latest_date + timedelta(days=1)

            # 执行同步
            count = await data_sync_service.sync_daily_k(
                session,
                code,
                start_date=start_date,
                end_date=today,
                adjust="qfq"
            )
            await session.commit()

            elapsed = time.time() - start_time
            if count > 0:
                await stats.update("updated", count)
                print(f"{stats.progress()} 更新: {code} {name} +{count}条 ({start_date}~{today}) ({elapsed:.1f}s)")
            else:
                await stats.update("skipped")
                print(f"{stats.progress()} 无新: {code} {name} ({elapsed:.1f}s)")

    except Exception as e:
        await stats.update("failed")
        elapsed = time.time() - start_time
        error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
        print(f"{stats.progress()} 失败: {code} {name} {error_msg} ({elapsed:.1f}s)")


async def run_daily_update(workers: int = 10, limit: int = None, force_days: int = None):
    """运行每日增量更新"""
    print(f"\n{'='*60}")
    print(f"每日增量同步 - {date.today()}")
    print(f"{'='*60}\n")

    # 获取所有股票
    async with get_db_session() as session:
        query = select(StockBasics.code, StockBasics.name).where(
            StockBasics.is_active == True
        ).order_by(StockBasics.code)
        result = await session.execute(query)
        stocks = [(row[0], row[1]) for row in result.fetchall()]

    if limit:
        stocks = stocks[:limit]

    total = len(stocks)
    print(f"待检查股票: {total} 只")
    print(f"并发数: {workers}")
    if force_days:
        print(f"强制模式: 同步最近 {force_days} 天")
    print()

    stats = DailyUpdateStats(total)
    semaphore = asyncio.Semaphore(workers)

    async def worker(code: str, name: str):
        async with semaphore:
            await sync_single_stock_incremental(code, name, stats, force_days)
            await asyncio.sleep(0.5)  # 增量更新可以更快

    tasks = [worker(code, name) for code, name in stocks]
    await asyncio.gather(*tasks)

    # 结果统计
    print(f"\n{'='*60}")
    print(f"每日增量同步完成!")
    print(f"  已更新: {stats.updated} 只股票")
    print(f"  已是最新: {stats.skipped} 只股票")
    print(f"  失败: {stats.failed} 只股票")
    print(f"  新增K线: {stats.new_records} 条")
    print(f"{'='*60}")


def is_trading_day() -> bool:
    """简单判断是否是交易日（周一到周五）"""
    today = date.today()
    return today.weekday() < 5  # 0-4 是周一到周五


def main():
    parser = argparse.ArgumentParser(description="每日增量同步K线数据")
    parser.add_argument("--workers", type=int, default=10, help="并发数量（默认10）")
    parser.add_argument("--limit", type=int, default=None, help="处理股票数量限制")
    parser.add_argument("--force", type=int, nargs="?", const=7, default=None,
                        help="强制同步最近N天数据（默认7天）")
    parser.add_argument("--skip-weekend", action="store_true",
                        help="周末自动跳过不执行")

    args = parser.parse_args()

    # 周末跳过检查
    if args.skip_weekend and not is_trading_day():
        print(f"今天是周末，跳过同步")
        return

    print(f"每日增量同步")
    print(f"  并发数: {args.workers}")
    print(f"  限制: {args.limit or '全部'}")
    if args.force:
        print(f"  强制模式: 同步最近 {args.force} 天")

    asyncio.run(run_daily_update(
        workers=args.workers,
        limit=args.limit,
        force_days=args.force
    ))


if __name__ == "__main__":
    main()

