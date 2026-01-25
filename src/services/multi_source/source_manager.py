"""
多数据源管理器
自动切换数据源、失败重试、数据聚合
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .data_source_base import DataSourceBase, DataSourcePriority, SourceStatus

logger = logging.getLogger(__name__)


class MultiSourceManager:
    """多数据源管理器"""

    def __init__(self):
        self.sources: List[DataSourceBase] = []
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 5  # 缓存有效期(秒)

    def register_source(self, source: DataSourceBase):
        """注册数据源"""
        self.sources.append(source)
        # 按优先级排序
        self.sources.sort(key=lambda s: s.priority.value)
        logger.info(f"Registered data source: {source.name} (priority: {source.priority.name})")

    def get_available_sources(self) -> List[DataSourceBase]:
        """获取可用数据源"""
        return [s for s in self.sources if s.status.should_use()]

    async def get_realtime_quote(self, codes: List[str]) -> Dict[str, Any]:
        """
        获取实时行情
        自动按优先级尝试数据源
        """
        # 检查缓存
        cache_key = f"realtime_{'_'.join(sorted(codes))}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug(f"Using cached realtime data for {codes}")
                return cached_data

        available_sources = self.get_available_sources()
        if not available_sources:
            logger.error("No available data sources")
            return {}

        # 按优先级尝试
        last_error = None
        for source in available_sources:
            try:
                start_time = time.time()
                logger.info(f"Trying {source.name} for realtime quote")
                data = await asyncio.wait_for(
                    source.get_realtime_quote(codes),
                    timeout=5.0  # 5秒超时
                )
                response_time = (time.time() - start_time) * 1000

                if data:
                    source.record_success(response_time)
                    self.cache[cache_key] = (data, time.time())
                    logger.info(f"Success from {source.name} ({response_time:.0f}ms)")
                    return data
                else:
                    source.record_failure("Empty data")

            except asyncio.TimeoutError:
                error = f"Timeout after 5s"
                source.record_failure(error)
                last_error = error
                logger.warning(f"{source.name} timeout")

            except Exception as e:
                error = str(e)
                source.record_failure(error)
                last_error = error
                logger.warning(f"{source.name} failed: {error}")

        logger.error(f"All sources failed. Last error: {last_error}")
        return {}

    async def get_minute_kline(self, code: str, retry_all: bool = True) -> List[Dict[str, Any]]:
        """
        获取分钟K线
        """
        available_sources = self.get_available_sources()
        if not available_sources:
            logger.error("No available data sources")
            return []

        for source in available_sources:
            try:
                start_time = time.time()
                logger.info(f"Trying {source.name} for minute kline")
                data = await asyncio.wait_for(
                    source.get_minute_kline(code),
                    timeout=10.0
                )
                response_time = (time.time() - start_time) * 1000

                if data:
                    source.record_success(response_time)
                    logger.info(f"Success from {source.name} ({response_time:.0f}ms)")
                    return data
                else:
                    source.record_failure("Empty data")

            except Exception as e:
                source.record_failure(str(e))
                logger.warning(f"{source.name} failed: {e}")

        return []

    async def get_daily_kline(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取日K线
        优先使用免费且稳定的数据源
        """
        available_sources = self.get_available_sources()
        if not available_sources:
            return []

        for source in available_sources:
            try:
                start_time = time.time()
                data = await asyncio.wait_for(
                    source.get_daily_kline(code, start_date, end_date),
                    timeout=15.0
                )
                response_time = (time.time() - start_time) * 1000

                if data:
                    source.record_success(response_time)
                    return data
                else:
                    source.record_failure("Empty data")

            except Exception as e:
                source.record_failure(str(e))
                logger.warning(f"{source.name} failed: {e}")

        return []

    async def health_check_all(self) -> Dict[str, SourceStatus]:
        """检查所有数据源健康状态"""
        results = {}
        for source in self.sources:
            try:
                is_healthy = await asyncio.wait_for(
                    source.health_check(),
                    timeout=5.0
                )
                source.status.available = is_healthy
                if is_healthy:
                    source.record_success()
            except Exception as e:
                source.status.available = False
                source.record_failure(str(e))

            results[source.name] = source.status

        return results

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据源状态"""
        return {
            s.name: {
                "priority": s.priority.name,
                "available": s.status.available,
                "success_rate": f"{s.status.success_rate:.1%}",
                "success_count": s.status.success_count,
                "fail_count": s.status.fail_count,
                "avg_response_time": f"{s.status.avg_response_time:.0f}ms",
                "last_success": s.status.last_success_time.isoformat() if s.status.last_success_time else None,
                "last_error": s.status.last_error,
            }
            for s in self.sources
        }


# 全局实例
multi_source_manager = MultiSourceManager()
