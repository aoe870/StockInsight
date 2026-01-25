"""
多数据源聚合模块
支持多数据源自动切换、失败重试、数据聚合

使用示例:
```python
from src.services.multi_source import init_data_sources, multi_source_manager

# 初始化数据源
init_data_sources()

# 获取实时行情（自动选择最优数据源）
quotes = await multi_source_manager.get_realtime_quote(["000001", "600000"])

# 获取分钟K线
minute_klines = await multi_source_manager.get_minute_kline("000001")

# 获取日K线
daily_klines = await multi_source_manager.get_daily_kline(
    "000001",
    "2025-01-01",
    "2026-01-23"
)

# 查看数据源状态
status = multi_source_manager.get_source_status()
```
"""

from .source_manager import MultiSourceManager, multi_source_manager
from .data_source_base import DataSourceBase, DataSourcePriority, SourceStatus
from .sources import init_data_sources

__all__ = [
    "MultiSourceManager",
    "multi_source_manager",
    "DataSourceBase",
    "DataSourcePriority",
    "SourceStatus",
    "init_data_sources",
]
