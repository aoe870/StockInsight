"""Test script to verify AKShare stock list fetching"""
import asyncio
from data_gateway.src.services.sync_service import sync_service

async def test():
    # Get stock list for cn_a market
    stocks = await sync_service.get_stock_list("cn_a")
    print(f"Total stocks from AKShare: {len(stocks)}")
    print(f"\nFirst 20 stocks: {stocks[:20]}")
    print(f"\nLast 10 stocks: {stocks[-10:]}")

if __name__ == "__main__":
    asyncio.run(test())
