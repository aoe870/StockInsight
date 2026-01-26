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
from ..models.money_flow import MoneyFlow
from ..models.realtime_quote import RealtimeQuote

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
                    # 使用独立的session写入数据库，避免事务问题
                    async with get_db_session() as session:
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

    async def _save_money_flow_to_db(
        self,
        session: AsyncSession,
        symbol: str,
        trade_date: datetime,
        money_flow_data: Dict,
        market: str = "cn_a"
    ) -> bool:
        """
        将资金流向数据保存到数据库

        参数:
            session: 数据库会话
            symbol: 股票代码
            trade_date: 交易日期
            money_flow_data: 资金流向数据（从 Miana 获取）
            market: 市场代码
        """
        try:
            from datetime import datetime as dt

            # 提取资金流向数据
            record = {
                "code": symbol,
                "trade_date": trade_date,
                "amount": money_flow_data.get("amount"),
                "main_net_inflow": money_flow_data.get("main_net_inflow"),
                "main_net_ratio": money_flow_data.get("main_net_ratio"),
                # 超大单
                "super_large_inflow": money_flow_data.get("super_large", {}).get("inflow"),
                "super_large_outflow": money_flow_data.get("super_large", {}).get("outflow"),
                "super_large_net_inflow": money_flow_data.get("super_large", {}).get("net_inflow"),
                "super_large_net_ratio": money_flow_data.get("super_large", {}).get("net_ratio"),
                # 大单
                "large_inflow": money_flow_data.get("large", {}).get("inflow"),
                "large_outflow": money_flow_data.get("large", {}).get("outflow"),
                "large_net_inflow": money_flow_data.get("large", {}).get("net_inflow"),
                "large_net_ratio": money_flow_data.get("large", {}).get("net_ratio"),
                # 中单
                "medium_inflow": money_flow_data.get("medium", {}).get("inflow"),
                "medium_outflow": money_flow_data.get("medium", {}).get("outflow"),
                "medium_net_inflow": money_flow_data.get("medium", {}).get("net_inflow"),
                "medium_net_ratio": money_flow_data.get("medium", {}).get("net_ratio"),
                # 小单
                "small_inflow": money_flow_data.get("small", {}).get("inflow"),
                "small_outflow": money_flow_data.get("small", {}).get("outflow"),
                "small_net_inflow": money_flow_data.get("small", {}).get("net_inflow"),
                "small_net_ratio": money_flow_data.get("small", {}).get("net_ratio"),
                "market_code": market,
                "source_code": "miana",
                "created_at": dt.utcnow(),
                "updated_at": dt.utcnow()
            }

            # 使用 PostgreSQL UPSERT 避免重复
            stmt = insert(MoneyFlow).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['code', 'trade_date', 'market_code'],
                set_={
                    'amount': stmt.excluded.amount,
                    'main_net_inflow': stmt.excluded.main_net_inflow,
                    'main_net_ratio': stmt.excluded.main_net_ratio,
                    'super_large_inflow': stmt.excluded.super_large_inflow,
                    'super_large_outflow': stmt.excluded.super_large_outflow,
                    'super_large_net_inflow': stmt.excluded.super_large_net_inflow,
                    'super_large_net_ratio': stmt.excluded.super_large_net_ratio,
                    'large_inflow': stmt.excluded.large_inflow,
                    'large_outflow': stmt.excluded.large_outflow,
                    'large_net_inflow': stmt.excluded.large_net_inflow,
                    'large_net_ratio': stmt.excluded.large_net_ratio,
                    'medium_inflow': stmt.excluded.medium_inflow,
                    'medium_outflow': stmt.excluded.medium_outflow,
                    'medium_net_inflow': stmt.excluded.medium_net_inflow,
                    'medium_net_ratio': stmt.excluded.medium_net_ratio,
                    'small_inflow': stmt.excluded.small_inflow,
                    'small_outflow': stmt.excluded.small_outflow,
                    'small_net_inflow': stmt.excluded.small_net_inflow,
                    'small_net_ratio': stmt.excluded.small_net_ratio,
                    'source_code': stmt.excluded.source_code,
                    'updated_at': stmt.excluded.updated_at
                }
            )
            await session.execute(stmt)
            return True

        except Exception as e:
            logger.error(f"Failed to save money flow data for {symbol}: {e}")
            return False

    async def sync_money_flow(
        self,
        market: str,
        symbols: List[str],
        trade_date: Optional[str] = None
    ) -> Dict:
        """
        同步资金流向数据

        参数:
            market: 市场代码
            symbols: 股票代码列表
            trade_date: 交易日期 (YYYY-MM-DD)，默认当天

        返回:
            同步结果统计
        """
        from ..gateway.markets.cn_a import ChinaAGateway

        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(symbols),
            "symbols": {}
        }

        # 确定交易日期
        if trade_date:
            try:
                target_date = datetime.strptime(trade_date, "%Y-%m-%d")
            except ValueError:
                logger.error(f"Invalid date format: {trade_date}")
                return {**results, "error": "Invalid date format"}
        else:
            target_date = datetime.now()

        gateway = gateway_manager.get_gateway(market)
        if not isinstance(gateway, ChinaAGateway):
            logger.warning(f"Money flow sync only available for cn_a market, got {market}")
            return {**results, "error": "Market not supported"}

        for symbol in symbols:
            try:
                # 获取资金流向数据
                money_flow_data = await gateway.get_money_flow(symbol)

                if money_flow_data:
                    # 保存到数据库
                    async with get_db_session() as session:
                        success = await self._save_money_flow_to_db(
                            session, symbol, target_date, money_flow_data, market
                        )

                    if success:
                        results["success"] += 1
                        results["symbols"][symbol] = {
                            "status": "success",
                            "main_net_inflow": money_flow_data.get("main_net_inflow")
                        }
                        logger.info(f"Synced money flow for {symbol}: {money_flow_data.get('main_net_inflow')}")
                    else:
                        results["failed"] += 1
                        results["symbols"][symbol] = {"status": "failed", "error": "save_failed"}
                else:
                    results["skipped"] += 1
                    results["symbols"][symbol] = {"status": "no_data"}
                    logger.warning(f"No money flow data for {symbol}")

                await asyncio.sleep(0.1)  # 避免请求过快

            except Exception as e:
                results["failed"] += 1
                results["symbols"][symbol] = {"status": "failed", "error": str(e)}
                logger.error(f"Failed to sync money flow for {symbol}: {e}")

        return results

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

    async def _save_realtime_quote_to_db(
        self,
        session: AsyncSession,
        quote_data,
        market: str = "cn_a"
    ) -> bool:
        """
        将实时行情数据保存到数据库

        参数:
            session: 数据库会话
            quote_data: QuoteData 对象
            market: 市场代码
        """
        try:
            from datetime import datetime as dt

            # 解析交易日期和时间
            timestamp_str = quote_data.timestamp or dt.now().strftime("%Y-%m-%d %H:%M:%S")
            trade_date = dt.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            trade_time = trade_date

            # 提取日期部分用于 trade_date 字段
            trade_date_only = trade_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # 提取五档盘口数据（如果 QuoteData 有 buys/sells 字段）
            buys = None
            sells = None
            if hasattr(quote_data, 'buys') and quote_data.buys:
                buys = quote_data.buys
            if hasattr(quote_data, 'sells') and quote_data.sells:
                sells = quote_data.sells

            record = {
                "code": quote_data.symbol,
                "name": quote_data.name,
                "trade_date": trade_date_only,
                "trade_time": trade_time,
                # 基础行情数据
                "price": quote_data.price,
                "open_price": quote_data.open,
                "high_price": quote_data.high,
                "low_price": quote_data.low,
                "volume": quote_data.volume,
                "amount": quote_data.amount,
                "change": quote_data.change,
                "change_pct": quote_data.change_pct,
                "pre_close": quote_data.pre_close,
                # 买卖档位
                "bid_volume": quote_data.bid,
                "ask_volume": quote_data.ask,
                "buys": buys,
                "sells": sells,
                # 市场数据
                "high_limit": quote_data.high_limit,
                "low_limit": quote_data.low_limit,
                "turnover": quote_data.turnover,
                "amplitude": quote_data.amplitude,
                "committee": quote_data.committee,
                # 估值指标
                "pe_ttm": quote_data.pe_ttm,
                "pe_dyn": quote_data.pe_dyn,
                "pe_static": quote_data.pe_static,
                "pb": quote_data.pb,
                # 股本数据
                "market_value": quote_data.market_value,
                "circulation_value": quote_data.circulation_value,
                "circulation_shares": quote_data.circulation_shares,
                "total_shares": quote_data.total_shares,
                # 交易所信息
                "country_code": quote_data.country_code,
                "exchange_code": quote_data.exchange_code,
                "market_code": market,
                "source_code": "miana",
                "created_at": dt.utcnow()
            }

            # 使用 PostgreSQL UPSERT 避免重复
            stmt = insert(RealtimeQuote).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['code', 'trade_time', 'market_code'],
                set_={
                    'name': stmt.excluded.name,
                    'price': stmt.excluded.price,
                    'open_price': stmt.excluded.open_price,
                    'high_price': stmt.excluded.high_price,
                    'low_price': stmt.excluded.low_price,
                    'volume': stmt.excluded.volume,
                    'amount': stmt.excluded.amount,
                    'change': stmt.excluded.change,
                    'change_pct': stmt.excluded.change_pct,
                    'pre_close': stmt.excluded.pre_close,
                    'bid_volume': stmt.excluded.bid_volume,
                    'ask_volume': stmt.excluded.ask_volume,
                    'buys': stmt.excluded.buys,
                    'sells': stmt.excluded.sells,
                    'high_limit': stmt.excluded.high_limit,
                    'low_limit': stmt.excluded.low_limit,
                    'turnover': stmt.excluded.turnover,
                    'amplitude': stmt.excluded.amplitude,
                    'committee': stmt.excluded.committee,
                    'pe_ttm': stmt.excluded.pe_ttm,
                    'pe_dyn': stmt.excluded.pe_dyn,
                    'pe_static': stmt.excluded.pe_static,
                    'pb': stmt.excluded.pb,
                    'market_value': stmt.excluded.market_value,
                    'circulation_value': stmt.excluded.circulation_value,
                    'circulation_shares': stmt.excluded.circulation_shares,
                    'total_shares': stmt.excluded.total_shares,
                    'country_code': stmt.excluded.country_code,
                    'exchange_code': stmt.excluded.exchange_code,
                    'source_code': stmt.excluded.source_code,
                    'created_at': stmt.excluded.created_at
                }
            )
            await session.execute(stmt)
            return True

        except Exception as e:
            logger.error(f"Failed to save realtime quote data: {e}")
            return False

    async def sync_realtime_quote(
        self,
        market: str,
        symbols: List[str],
        trade_date: Optional[str] = None
    ) -> Dict:
        """
        同步实时行情数据到数据库

        参数:
            market: 市场代码
            symbols: 股票代码列表
            trade_date: 交易日期 YYYY-MM-DD（用于查询历史），默认当前实时数据

        返回:
            同步结果统计
        """
        from ..gateway.markets.cn_a import ChinaAGateway
        from ..gateway.base import QuoteData

        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(symbols),
            "symbols": {}
        }

        # 确定交易日期
        target_date = None
        if trade_date:
            try:
                target_date = datetime.strptime(trade_date, "%Y-%m-%d")
            except ValueError:
                logger.error(f"Invalid date format: {trade_date}")
                return {**results, "error": "Invalid date format"}
        else:
            target_date = datetime.now()

        gateway = gateway_manager.get_gateway(market)
        if not gateway:
            logger.warning(f"Gateway not found for market: {market}")
            return {**results, "error": "Market not supported"}

        for symbol in symbols:
            try:
                # 获取实时行情数据
                quotes = await gateway.get_quote([symbol])

                if quotes and symbol in quotes:
                    quote_data = quotes[symbol]

                    # 保存到数据库
                    async with get_db_session() as session:
                        success = await self._save_realtime_quote_to_db(
                            session, quote_data, market
                        )

                    if success:
                        results["success"] += 1
                        results["symbols"][symbol] = {
                            "status": "success",
                            "price": quote_data.price,
                            "change_pct": quote_data.change_pct
                        }
                        logger.info(f"Synced realtime quote for {symbol}: {quote_data.price}")
                    else:
                        results["failed"] += 1
                        results["symbols"][symbol] = {"status": "failed", "error": "save_failed"}
                else:
                    results["skipped"] += 1
                    results["symbols"][symbol] = {"status": "no_data"}
                    logger.warning(f"No realtime quote data for {symbol}")

                await asyncio.sleep(0.1)  # 避免请求过快

            except Exception as e:
                results["failed"] += 1
                results["symbols"][symbol] = {"status": "failed", "error": str(e)}
                logger.error(f"Failed to sync realtime quote for {symbol}: {e}")

        return results


# 全局单例
sync_service = SyncService()
