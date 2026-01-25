"""
多数据源基类
支持多种数据源自动切换、失败重试、数据聚合
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourcePriority(Enum):
    """数据源优先级"""
    REALTIME = 1  # 实时数据源
    MINUTE = 2    # 分钟级数据源
    DAILY = 3     # 日线数据源
    FALLBACK = 4  # 备用数据源


@dataclass
class SourceStatus:
    """数据源状态"""
    name: str
    priority: DataSourcePriority
    available: bool = True
    success_count: int = 0
    fail_count: int = 0
    last_success_time: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_response_time: float = 0.0  # 平均响应时间(ms)

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0

    def should_use(self) -> bool:
        """是否应该使用此数据源"""
        if not self.available:
            return False
        # 连续失败3次暂时禁用
        if self.fail_count >= 3 and self.success_count == 0:
            return False
        return True


class DataSourceBase(ABC):
    """数据源基类"""

    def __init__(self, name: str, priority: DataSourcePriority):
        self.name = name
        self.priority = priority
        self.status = SourceStatus(name=name, priority=priority)
        self._rate_limit = 0  # 速率限制(次/秒)

    @abstractmethod
    async def get_realtime_quote(self, codes: List[str]) -> Dict[str, Any]:
        """获取实时行情"""
        pass

    @abstractmethod
    async def get_minute_kline(self, code: str) -> List[Dict[str, Any]]:
        """获取分钟K线"""
        pass

    @abstractmethod
    async def get_daily_kline(self, code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取日K线"""
        pass

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单测试请求
            await self.get_realtime_quote(["000001"])
            return True
        except Exception as e:
            logger.warning(f"{self.name} health check failed: {e}")
            return False

    def record_success(self, response_time: float = 0):
        """记录成功"""
        self.status.success_count += 1
        self.status.last_success_time = datetime.now()
        self.status.last_error = None
        self.status.available = True

        # 更新平均响应时间
        if response_time > 0:
            total_requests = self.status.success_count
            self.status.avg_response_time = (
                (self.status.avg_response_time * (total_requests - 1) + response_time)
                / total_requests
            )

    def record_failure(self, error: str):
        """记录失败"""
        self.status.fail_count += 1
        self.status.last_error = error
        # 连续失败则禁用
        if self.status.fail_count >= 3:
            self.status.available = False
            logger.warning(f"{self.name} disabled after {self.status.fail_count} failures")
