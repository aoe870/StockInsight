"""Quick script to check database records"""
import asyncio
from sqlalchemy import text
from data_gateway.src.database import async_session_maker

async def check():
    async with async_session_maker() as session:
        # Check latest records for 000001
        result = await session.execute(text("""
            SELECT code, trade_date, open_price, close_price, volume
            FROM dg_stock_daily_k
            WHERE code = '000001'
            ORDER BY trade_date DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        print('Latest 5 records for 000001 in dg_stock_daily_k:')
        for row in rows:
            print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}')

        # Check total records
        count_result = await session.execute(text("SELECT COUNT(*) FROM dg_stock_daily_k"))
        total = count_result.scalar()
        print(f'\nTotal records in dg_stock_daily_k: {total}')

        # Check count per stock
        count_by_stock = await session.execute(text("""
            SELECT code, COUNT(*) as count
            FROM dg_stock_daily_k
            GROUP BY code
            ORDER BY count DESC
        """))
        print('\nRecords per stock:')
        for row in count_by_stock.fetchall():
            print(f'{row[0]}: {row[1]} records')

if __name__ == "__main__":
    asyncio.run(check())
