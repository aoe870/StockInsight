"""
数据同步服务
支持通过接口主动触发历史数据同步，并存储到数据库
"""
import asyncio
from typing import List, Dict, Optional, Callable
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..gateway.base import KlineData
from ..gateway.manager import gateway_manager
from ..database import get_db_session
from ..models.kline import CachedKline
from ..models.stock_daily_k import StockDailyK
from ..models.sync_log import SyncLog as SyncLogModel

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncType(str, Enum):
    """同步类型"""
    FULL = "full"
    INCREMENTAL = "incremental"
    SYMBOL = "symbol"


@dataclass
class SyncTask:
    """同步任务"""
    task_id: str
    sync_type: SyncType
    market: str
    symbols: List[str] = field(default_factory=list)
    period: str = "daily"
    start_date: str = ""
    end_date: str = ""
    status: SyncStatus = SyncStatus.PENDING
    progress: int = 0
    total: int = 0
    current_symbol: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Dict = field(default_factory=dict)
    _cancel_flag: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "sync_type": self.sync_type.value,
            "market": self.market,
            "symbols": self.symbols[:10],
            "total_symbols": len(self.symbols),
            "period": self.period,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "current_symbol": self.current_symbol,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "started_at": self.started_at.strftime("%Y-%m-%d %H:%M:%S") if self.started_at else None,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else None,
            "result": self.result
        }

    def cancel(self):
        """取消任务"""
        self._cancel_flag = True

    def is_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._cancel_flag


class SyncService:
    """数据同步服务"""

    def __init__(self):
        self.tasks: Dict[str, SyncTask] = {}
        self.active_task_id: Optional[str] = None

    def generate_task_id(self) -> str:
        """生成任务ID"""
        return f"sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    async def create_task(
        self,
        sync_type: SyncType,
        market: str,
        symbols: List[str],
        period: str = "daily",
        start_date: str = "",
        end_date: str = ""
    ) -> SyncTask:
        """创建同步任务"""
        task_id = self.generate_task_id()

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not start_date and sync_type == SyncType.FULL:
            start_date = "1990-01-01"  # A股成立时间
        elif not start_date and sync_type == SyncType.INCREMENTAL:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        task = SyncTask(
            task_id=task_id,
            sync_type=sync_type,
            market=market,
            symbols=symbols,
            period=period,
            start_date=start_date,
            end_date=end_date
        )

        self.tasks[task_id] = task
        return task

    async def start_sync(self, task_id: str, progress_callback: Optional[Callable] = None) -> Dict:
        """启动同步任务"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        if self.active_task_id:
            raise RuntimeError(f"Another task {self.active_task_id} is running")

        task.status = SyncStatus.RUNNING
        task.started_at = datetime.now()
        self.active_task_id = task_id

        logger.info(f"Starting sync task {task_id}: {task.sync_type.value} for {len(task.symbols)} symbols")

        try:
            result = await self._execute_sync(task, progress_callback)
            task.status = SyncStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            logger.info(f"Sync task {task_id} completed: {result}")
        except Exception as e:
            task.status = SyncStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Sync task {task_id} failed: {e}")
            result = {"error": str(e)}

        self.active_task_id = None
        return result

    async def _execute_sync(self, task: SyncTask, progress_callback: Optional[Callable] = None) -> Dict:
        """执行同步任务"""
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total_records": 0,
            "symbols": {}
        }

        task.total = len(task.symbols)

        async with get_db_session() as session:
            for idx, symbol in enumerate(task.symbols):
                if task.is_cancelled():
                    task.status = SyncStatus.CANCELLED
                    logger.info(f"Task {task.task_id} was cancelled")
                    break

                task.current_symbol = symbol
                task.progress = int((idx / task.total) * 100)

                if progress_callback:
                    await progress_callback(task)

                try:
                    # 获取K线数据
                    klines = await gateway_manager.get_kline(
                        market=task.market,
                        symbol=symbol,
                        period=task.period,
                        start_date=task.start_date,
                        end_date=task.end_date
                    )

                    if klines:
                        # 写入数据库
                        count = await self._save_klines_to_db(
                            session,
                            symbol,
                            task.market,
                            task.period,
                            klines,
                            task.start_date,
                            task.end_date
                        )

                        results["symbols"][symbol] = {
                            "status": "success",
                            "records": count,
                            "date_range": f"{klines[0].datetime} ~ {klines[-1].datetime}" if klines else ""
                        }
                        results["success"] += 1
                        results["total_records"] += count
                        logger.info(f"Synced {symbol}: {count} records")
                    else:
                        results["symbols"][symbol] = {
                            "status": "no_data",
                            "records": 0
                        }
                        results["skipped"] += 1
                        logger.warning(f"No data for {symbol}")

                    await asyncio.sleep(0.1)

                except Exception as e:
                    results["symbols"][symbol] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    results["failed"] += 1
                    logger.error(f"Failed to sync {symbol}: {e}")

        task.progress = 100
        return results

    async def _save_klines_to_db(
        self,
        session: AsyncSession,
        symbol: str,
        market: str,
        period: str,
        klines: List[KlineData],
        start_date: str,
        end_date: str
    ) -> int:
        """
        将K线数据保存到数据库

        每天一条记录，不聚合，写入 dg_stock_daily_k 表
        """
        from datetime import datetime as dt
        from sqlalchemy.dialects.postgresql import insert

        # 确定数据源
        source_code = "baostock"  # 主要数据源

        # 准备批量插入数据
        records_to_insert = []

        for k in klines:
            # 解析交易日期
            try:
                trade_date = dt.strptime(k.datetime, "%Y-%m-%d")
            except ValueError:
                # 如果格式不对，尝试其他格式
                try:
                    trade_date = dt.strptime(k.datetime, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"Invalid datetime format for {symbol}: {k.datetime}")
                    continue

            daily_record = {
                "code": symbol,
                "trade_date": trade_date,
                "open_price": k.open,
                "close_price": k.close,
                "high_price": k.high,
                "low_price": k.low,
                "volume": k.volume,
                "amount": k.amount,
                "market_code": market,
                "source_code": source_code,
                "created_at": dt.utcnow()
            }
            records_to_insert.append(daily_record)

        # 批量插入（使用 PostgreSQL UPSERT 避免重复）
        if records_to_insert:
            stmt = insert(StockDailyK).values(records_to_insert)
            # 如果记录已存在则更新，否则插入
            stmt = stmt.on_conflict_do_update(
                index_elements=['code', 'trade_date'],
                set_={
                    'open_price': stmt.excluded.open_price,
                    'close_price': stmt.excluded.close_price,
                    'high_price': stmt.excluded.high_price,
                    'low_price': stmt.excluded.low_price,
                    'volume': stmt.excluded.volume,
                    'amount': stmt.excluded.amount,
                    'source_code': stmt.excluded.source_code,
                    'created_at': stmt.excluded.created_at
                }
            )
            await session.execute(stmt)

        return len(klines)

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        if task.status == SyncStatus.RUNNING:
            task.cancel()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[SyncTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return [task.to_dict() for task in self.tasks.values()]

    def get_active_task(self) -> Optional[SyncTask]:
        """获取当前运行的任务"""
        if self.active_task_id:
            return self.tasks.get(self.active_task_id)
        return None

    async def get_stock_list(self, market: str) -> List[str]:
        """获取股票列表（用于全量同步）"""
        try:
            # 优先从数据库获取（如果SAPAS数据库有stock_basics表）
            all_stocks = []

            if market == "cn_a":
                # 方法1：尝试从AKShare获取全部A股列表
                try:
                    import akshare as ak
                    df = ak.stock_info_a_code_name()
                    all_stocks = [str(code).zfill(6) for code in df['code'].tolist()]
                    logger.info(f"Got {len(all_stocks)} stocks from AKShare")
                    return all_stocks
                except Exception as e:
                    logger.warning(f"Failed to get stock list from AKShare: {e}")

                # 方法2：如果AKShare失败，返回更多示例股票
                all_stocks = [
                    "000001", "000002", "000004", "000005", "000006", "000007", "000008", "000009", "000010", "000011",
                    "000012", "000014", "000016", "000017", "000018", "000019", "000020", "000021", "000022", "000023",
                    "000025", "000026", "000027", "000028", "000029", "000030", "000031", "000032", "000034", "000035",
                    # ... 主板股票前100只
                    "600000", "600004", "600009", "600010", "600011", "600015", "600016", "600017", "600018", "600019",
                    "600020", "600021", "600022", "600023", "600025", "600026", "600027", "600028", "600029", "600030",
                    # ... 沪深主板股票
                    "688001", "688002", "688003", "688005", "688006", "688007", "688008", "688009", "688010", "688011",
                    # ... 科创板股票
                    "300001", "300002", "300003", "300004", "300005", "300006", "300007", "300008", "300009", "300010",
                    # ... 创业板股票
                    "301001", "301002", "301003", "301004", "301005", "301006", "301007", "301008", "301009", "301010",
                ]
                return all_stocks

            elif market == "hk":
                return [
                    "00700", "00941", "01024", "01093", "01299",
                    "01810", "02318", "06690", "08803", "09988"
                ]
            elif market == "us":
                return [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
                    "META", "NVDA", "TSM", "V", "JPM"
                ]
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to get stock list for {market}: {e}")
            return []

    async def incremental_sync(
        self,
        market: str,
        symbols: List[str],
        days: int = 30
    ) -> SyncTask:
        """增量同步（最近N天）"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        task = await self.create_task(
            sync_type=SyncType.INCREMENTAL,
            market=market,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )

        return task

    async def full_sync(
        self,
        market: str,
        symbols: Optional[List[str]] = None
    ) -> SyncTask:
        """全量同步（从1990年开始，完整A股历史数据）"""
        if not symbols:
            symbols = await self.get_stock_list(market)

        start_date = "1990-01-01"

        task = await self.create_task(
            sync_type=SyncType.FULL,
            market=market,
            symbols=symbols,
            start_date=start_date,
            end_date=datetime.now().strftime("%Y-%m-%d")
        )

        return task


# 全局单例
sync_service = SyncService()
