"""
多数据源模块初始化
"""

from .sina_source import SinaFinanceSource
from .tencent_source import TencentFinanceSource
from .akshare_source import AKShareSource
from ..source_manager import multi_source_manager

__all__ = [
    "SinaFinanceSource",
    "TencentFinanceSource",
    "AKShareSource",
    "multi_source_manager",
]


def init_data_sources():
    """
    初始化数据源
    按优先级注册数据源
    """
    # 1. 实时数据源（秒级延迟）
    multi_source_manager.register_source(SinaFinanceSource())
    multi_source_manager.register_source(TencentFinanceSource())

    # 2. 备用数据源（分钟级延迟）
    multi_source_manager.register_source(AKShareSource())

    return multi_source_manager
