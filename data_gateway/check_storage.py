"""Check K-line data storage location"""
import asyncio
from sqlalchemy import text
from src.database import async_session_maker

async def check():
    async with async_session_maker() as session:
        # Get all data gateway tables
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'dg_%'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        print('=' * 60)
        print('数据网关数据库表 (Data Gateway Tables):')
        print('=' * 60)
        for row in tables:
            print(f'  - {row[0]}')
        print()

        # Check cache_kline table (aggregated JSON storage)
        result2 = await session.execute(text("SELECT COUNT(*) FROM dg_cache_kline"))
        cache_count = result2.scalar()
        print(f'dg_cache_kline (聚合JSON存储): {cache_count} 条记录')

        # Check stock_daily_k table (daily records storage)
        result3 = await session.execute(text("SELECT COUNT(*) FROM dg_stock_daily_k"))
        daily_count = result3.scalar()
        print(f'dg_stock_daily_k (每日一条记录): {daily_count} 条记录')

        # Show sample from stock_daily_k
        if daily_count > 0:
            print()
            print('=' * 60)
            print('dg_stock_daily_k 示例数据:')
            print('=' * 60)
            result4 = await session.execute(text("""
                SELECT code, trade_date, open_price, close_price,
                       high_price, low_price, volume, amount
                FROM dg_stock_daily_k
                ORDER BY trade_date DESC
                LIMIT 5
            """))
            rows = result4.fetchall()
            for row in rows:
                print(f'  {row[0]} | {row[1].strftime("%Y-%m-%d")} | '
                      f'开:{row[2]} 收:{row[3]} | '
                      f'高:{row[4]} 低:{row[5]} | '
                      f'量:{row[6]:,} 额:{row[7]:,.0f}')

        print()
        print('=' * 60)
        print('存储方式说明:')
        print('=' * 60)
        print('  dg_cache_kline:   每只股票一条记录，K线数据以JSON格式存储')
        print('  dg_stock_daily_k: 每只股票每天一条记录，每个字段独立存储')
        print()
        print(f'  当前主要存储: dg_stock_daily_k ({daily_count} 条记录)')
        print('=' * 60)

if __name__ == "__main__":
    asyncio.run(check())
