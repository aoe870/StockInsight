"""Test sync_service get_stock_list function"""
import asyncio
import sys
sys.path.insert(0, 'D:/Develop/StockInsight/data_gateway')

from src.services.sync_service import sync_service

async def test():
    print("Testing sync_service.get_stock_list()...")
    stocks = await sync_service.get_stock_list("cn_a")
    print(f"Total stocks: {len(stocks)}")
    print(f"First 20: {stocks[:20]}")
    print(f"Last 10: {stocks[-10:]}")

if __name__ == "__main__":
    asyncio.run(test())
