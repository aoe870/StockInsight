#!/usr/bin/env python
r"""
批量同步全部股票K线历史数据（并发版本）
用法: .venv\Scripts\python.exe sync_all_klines.py [选项]

选项:
    --limit N       同步股票数量限制，默认全部
    --days N        同步最近N天的数据，默认365天
    --all           同步全部历史数据（从上市至今）
    --start CODE    从指定股票代码开始（用于断点续传）
    --workers N     并发数量，默认5
"""

import asyncio
import argparse
import sys
from datetime import date, timedelta
from sqlalchemy import select, func

# 添加项目路径
sys.path.insert(0, ".")

from src.core.database import get_db_session
from src.models.stock import StockBasics, StockDailyK
from src.services.data_sync import data_sync_service


# 进度统计
class SyncStats:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.success = 0
        self.failed = 0
        self.new_records = 0
        self.lock = asyncio.Lock()

    async def update(self, success: bool, records: int = 0):
        async with self.lock:
            self.completed += 1
            if success:
                self.success += 1
                self.new_records += records
            else:
                self.failed += 1

    def progress(self) -> str:
        return f"[{self.completed}/{self.total}]"


async def get_stats_info():
    """获取当前数据统计"""
    async with get_db_session() as session:
        # 股票总数
        stock_count = await session.execute(
            select(func.count()).select_from(StockBasics).where(StockBasics.is_active == True)
        )
        # K线总数
        kline_count = await session.execute(
            select(func.count()).select_from(StockDailyK)
        )
        # 有K线的股票数
        stocks_with_kline = await session.execute(
            select(func.count(func.distinct(StockDailyK.code)))
        )

        return {
            "stocks": stock_count.scalar(),
            "klines": kline_count.scalar(),
            "stocks_with_kline": stocks_with_kline.scalar()
        }


async def sync_single_stock(code: str, name: str, start_date: date, stats: SyncStats):
    """同步单只股票（独立会话）"""
    import time
    start_time = time.time()
    print(f"{stats.progress()} 开始: {code} {name}")

    try:
        async with get_db_session() as session:
            count = await data_sync_service.sync_daily_k(
                session,
                code,
                start_date=start_date,
                adjust="qfq"
            )
            await session.commit()

            await stats.update(success=True, records=count)
            elapsed = time.time() - start_time

            if count > 0:
                print(f"{stats.progress()} 完成: {code} {name} +{count}条 ({elapsed:.1f}s)")
            else:
                print(f"{stats.progress()} 完成: {code} {name} 已最新 ({elapsed:.1f}s)")

    except Exception as e:
        await stats.update(success=False)
        elapsed = time.time() - start_time
        error_msg = str(e)
        # 简化错误信息
        if "NumericValueOutOfRange" in error_msg:
            error_msg = "数值溢出"
        elif len(error_msg) > 50:
            error_msg = error_msg[:50] + "..."
        print(f"{stats.progress()} 失败: {code} {name} {error_msg} ({elapsed:.1f}s)")


async def sync_all_stocks(
    limit: int = None,
    days: int = None,
    start_code: str = None,
    sync_all: bool = False,
    workers: int = 5
):
    """
    并发同步所有活跃股票的K线数据

    Args:
        limit: 同步股票数量限制，None表示全部
        days: 同步最近多少天的数据，None表示全部历史
        start_code: 从哪个股票代码开始（用于断点续传）
        sync_all: 是否同步全部历史数据
        workers: 并发数量
    """
    # 显示当前统计
    stats_info = await get_stats_info()
    print(f"\n{'='*50}")
    print(f"当前数据统计:")
    print(f"  活跃股票: {stats_info['stocks']} 只")
    print(f"  K线数据: {stats_info['klines']} 条")
    print(f"  有K线的股票: {stats_info['stocks_with_kline']} 只")
    print(f"{'='*50}\n")

    # 获取所有活跃股票（只取 code 和 name，避免后续 session 问题）
    async with get_db_session() as session:
        query = select(StockBasics.code, StockBasics.name).where(
            StockBasics.is_active == True
        ).order_by(StockBasics.code)
        result = await session.execute(query)
        all_stocks = [(row[0], row[1]) for row in result.fetchall()]

    # 过滤：从指定代码开始
    if start_code:
        stocks = [(c, n) for c, n in all_stocks if c >= start_code]
        print(f"从 {start_code} 开始，跳过 {len(all_stocks) - len(stocks)} 只股票")
    else:
        stocks = all_stocks

    # 限制数量
    if limit:
        stocks = stocks[:limit]

    total = len(stocks)

    # 确定同步范围
    if sync_all or days is None:
        start_date = None
        print(f"准备同步 {total} 只股票，获取【全部历史数据】")
    else:
        start_date = date.today() - timedelta(days=days)
        print(f"准备同步 {total} 只股票，获取最近 {days} 天数据")

    print(f"并发数: {workers}\n")

    # 创建统计对象
    stats = SyncStats(total)

    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(workers)

    async def worker(code: str, name: str):
        async with semaphore:
            await sync_single_stock(code, name, start_date, stats)
            # 每个请求后休息，避免被限流
            await asyncio.sleep(1.0)

    # 创建所有任务
    tasks = [worker(code, name) for code, name in stocks]

    # 并发执行
    await asyncio.gather(*tasks)

    # 最终统计
    print(f"\n{'='*50}")
    print(f"同步完成!")
    print(f"  成功: {stats.success} 只")
    print(f"  失败: {stats.failed} 只")
    print(f"  新增K线: {stats.new_records} 条")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="批量同步股票K线数据（并发版本）")
    parser.add_argument("--limit", type=int, default=None, help="同步股票数量限制")
    parser.add_argument("--days", type=int, default=None, help="同步最近N天数据")
    parser.add_argument("--all", action="store_true", dest="sync_all", help="同步全部历史数据")
    parser.add_argument("--start", type=str, default=None, help="从指定代码开始")
    parser.add_argument("--workers", type=int, default=5, help="并发数量（默认5）")

    args = parser.parse_args()

    # 如果没有指定 --days 也没有指定 --all，默认同步全部
    if args.days is None and not args.sync_all:
        args.sync_all = True

    print(f"开始同步K线数据...")
    print(f"  数量限制: {args.limit or '全部'}")
    print(f"  数据范围: {'全部历史' if args.sync_all else f'最近{args.days}天'}")
    print(f"  起始代码: {args.start or '从头开始'}")
    print(f"  并发数量: {args.workers}")

    asyncio.run(sync_all_stocks(
        limit=args.limit,
        days=args.days,
        start_code=args.start,
        sync_all=args.sync_all,
        workers=args.workers
    ))


if __name__ == "__main__":
    main()

