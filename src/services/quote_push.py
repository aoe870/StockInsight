"""
行情推送服务
负责从数据源获取行情并通过 Redis Pub/Sub 分发
"""

import asyncio
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import akshare as ak
import pandas as pd

from src.core.redis import redis_manager
from src.utils.logger import logger


class QuoteChannel(str, Enum):
    """行情频道定义"""
    INDEX = "quote:index"           # 大盘指数
    STOCK_PREFIX = "quote:stock:"   # 个股前缀，如 quote:stock:600519


# 主要指数代码
MAIN_INDEXES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
    "sh000016": "上证50",
    "sz399005": "中小100",
}


class QuotePushService:
    """行情推送服务"""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._running = False
        self._index_task: Optional[asyncio.Task] = None
        self._stock_tasks: Dict[str, asyncio.Task] = {}  # code -> task
        self._subscribed_stocks: Dict[str, int] = {}  # code -> subscriber count
    
    def is_trading_time(self) -> bool:
        """判断是否为交易时间"""
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        current = now.time()
        # 9:15-11:30, 13:00-15:05
        return ((dt_time(9, 15) <= current <= dt_time(11, 30)) or
                (dt_time(13, 0) <= current <= dt_time(15, 5)))
    
    # ==================== 指数行情 ====================
    
    def _fetch_index_quotes(self) -> List[Dict[str, Any]]:
        """同步获取指数实时行情"""
        results = []
        try:
            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                return results
            
            for code, name in MAIN_INDEXES.items():
                pure_code = code[2:]
                row = df[df["代码"] == pure_code]
                if row.empty:
                    continue
                row = row.iloc[0]
                results.append({
                    "code": code,
                    "name": name,
                    "current": float(row.get("最新价", 0) or 0),
                    "change": float(row.get("涨跌额", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "open": float(row.get("今开", 0) or 0),
                    "high": float(row.get("最高", 0) or 0),
                    "low": float(row.get("最低", 0) or 0),
                    "volume": float(row.get("成交量", 0) or 0),
                    "amount": float(row.get("成交额", 0) or 0),
                })
        except Exception as e:
            logger.error(f"获取指数行情失败: {e}")
        return results
    
    async def _index_push_loop(self):
        """指数行情推送循环"""
        logger.info("指数行情推送服务启动")
        while self._running:
            try:
                interval = 3 if self.is_trading_time() else 30
                
                loop = asyncio.get_event_loop()
                quotes = await loop.run_in_executor(self._executor, self._fetch_index_quotes)
                
                if quotes:
                    message = {
                        "type": "index_quote",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "data": quotes
                    }
                    await redis_manager.publish(QuoteChannel.INDEX, message)
                    # 同时缓存最新数据
                    await redis_manager.set_cache("latest:index", quotes, expire=60)
                
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指数推送异常: {e}")
                await asyncio.sleep(5)
        logger.info("指数行情推送服务停止")
    
    async def start_index_push(self):
        """启动指数行情推送"""
        if self._index_task is not None:
            return
        self._running = True
        self._index_task = asyncio.create_task(self._index_push_loop())
    
    async def stop_index_push(self):
        """停止指数行情推送"""
        self._running = False
        if self._index_task:
            self._index_task.cancel()
            try:
                await self._index_task
            except asyncio.CancelledError:
                pass
            self._index_task = None
    
    # ==================== 个股行情 ====================
    
    def _fetch_stock_minute(self, code: str) -> Optional[Dict[str, Any]]:
        """同步获取个股分时数据"""
        try:
            df = ak.stock_zh_a_minute(symbol=code, period='1', adjust='')
            if df is None or df.empty:
                return None

            # 只返回最新的一条数据用于实时推送
            row = df.iloc[-1]
            return {
                "code": code,
                "time": str(row.get("day", "")),
                "current": float(row.get("close", 0)),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "volume": float(row.get("volume", 0)),
                "amount": float(row.get("amount", 0) if "amount" in row else 0),
            }
        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return None

    async def _stock_push_loop(self, code: str):
        """个股行情推送循环"""
        channel = f"{QuoteChannel.STOCK_PREFIX}{code}"
        logger.info(f"个股 {code} 行情推送启动")

        while self._running and code in self._subscribed_stocks:
            try:
                interval = 5 if self.is_trading_time() else 60

                loop = asyncio.get_event_loop()
                quote = await loop.run_in_executor(self._executor, self._fetch_stock_minute, code)

                if quote:
                    message = {
                        "type": "stock_quote",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "data": quote
                    }
                    await redis_manager.publish(channel, message)
                    await redis_manager.set_cache(f"latest:stock:{code}", quote, expire=60)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"个股 {code} 推送异常: {e}")
                await asyncio.sleep(5)

        logger.info(f"个股 {code} 行情推送停止")

    async def subscribe_stock(self, code: str) -> None:
        """订阅个股行情"""
        if code in self._subscribed_stocks:
            self._subscribed_stocks[code] += 1
            logger.debug(f"个股 {code} 订阅数: {self._subscribed_stocks[code]}")
            return

        self._subscribed_stocks[code] = 1
        task = asyncio.create_task(self._stock_push_loop(code))
        self._stock_tasks[code] = task
        logger.info(f"开始推送个股 {code} 行情")

    async def unsubscribe_stock(self, code: str) -> None:
        """取消订阅个股行情"""
        if code not in self._subscribed_stocks:
            return

        self._subscribed_stocks[code] -= 1
        if self._subscribed_stocks[code] <= 0:
            del self._subscribed_stocks[code]
            if code in self._stock_tasks:
                self._stock_tasks[code].cancel()
                try:
                    await self._stock_tasks[code]
                except asyncio.CancelledError:
                    pass
                del self._stock_tasks[code]
            logger.info(f"停止推送个股 {code} 行情")

    async def start(self):
        """启动服务"""
        self._running = True
        await self.start_index_push()
        logger.info("行情推送服务已启动")

    async def stop(self):
        """停止服务"""
        self._running = False
        await self.stop_index_push()
        # 停止所有个股推送
        for code in list(self._stock_tasks.keys()):
            task = self._stock_tasks.pop(code, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._subscribed_stocks.clear()
        logger.info("行情推送服务已停止")


# 全局实例
quote_push_service = QuotePushService()

