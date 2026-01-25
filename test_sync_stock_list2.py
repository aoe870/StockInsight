"""Test sync_service get_stock_list function - direct import"""
import asyncio
import sys
import os

# Add the data_gateway directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_gateway'))

# Import after setting path
from src.services.sync_service import sync_service

async def test():
    print("Testing sync_service.get_stock_list()...")
    stocks = await sync_service.get_stock_list("cn_a")
    print(f"Total stocks: {len(stocks)}")
    if len(stocks) > 20:
        print(f"First 20: {stocks[:20]}")
    if len(stocks) > 10:
        print(f"Last 10: {stocks[-10:]}")

if __name__ == "__main__":
    asyncio.run(test())
