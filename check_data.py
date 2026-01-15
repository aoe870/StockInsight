"""检查并同步数据"""
import asyncio
import sys
from datetime import date, timedelta
from sqlalchemy import text
from src.core.database import get_db_session
from src.services.data_sync import data_sync_service


async def check():
    """检查数据库状态"""
    async with get_db_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM stock_basics"))
        print(f"股票列表: {result.scalar()} 条")

        result = await session.execute(text("SELECT COUNT(*) FROM stock_daily_k"))
        kline_count = result.scalar()
        print(f"K线数据: {kline_count} 条")

        result = await session.execute(text("SELECT stock_code FROM watchlist_items"))
        codes = [r[0] for r in result.fetchall()]
        print(f"自选股: {codes}")

        # 显示K线数据的日期范围
        if kline_count > 0:
            result = await session.execute(text(
                "SELECT code, MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_daily_k GROUP BY code"
            ))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} ~ {row[2]} ({row[3]}条)")


async def reset_and_sync(code: str, days: int = 365):
    """删除并重新同步历史K线数据"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    async with get_db_session() as session:
        # 先删除现有数据
        await session.execute(text(f"DELETE FROM stock_daily_k WHERE code = '{code}'"))
        await session.commit()
        print(f"已删除 {code} 的现有K线数据")

        # 重新同步
        print(f"同步 {code} 历史数据: {start_date} ~ {end_date}")
        count = await data_sync_service.sync_daily_k(
            session, code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        await session.commit()
        print(f"✅ 同步完成: {count} 条记录")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        code = sys.argv[2] if len(sys.argv) > 2 else "000001"
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 365
        asyncio.run(reset_and_sync(code, days))
    else:
        asyncio.run(check())

