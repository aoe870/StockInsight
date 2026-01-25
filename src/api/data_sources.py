"""
数据源管理 API
提供数据源状态查询和健康检查接口
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime

from src.services.multi_source import multi_source_manager

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("/status")
async def get_data_source_status() -> Dict[str, Any]:
    """
    获取所有数据源状态

    返回各数据源的:
    - 优先级
    - 可用性
    - 成功率
    - 平均响应时间
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "sources": multi_source_manager.get_source_status()
    }


@router.get("/health")
async def health_check_data_sources() -> Dict[str, Any]:
    """
    健康检查所有数据源

    返回各数据源的健康状态
    """
    results = await multi_source_manager.health_check_all()

    health_report = {}
    all_healthy = True

    for name, status in results.items():
        is_healthy = status.available
        health_report[name] = {
            "healthy": is_healthy,
            "success_rate": f"{status.success_rate:.1%}",
            "last_error": status.last_error,
            "last_success": status.last_success_time.isoformat() if status.last_success_time else None,
        }
        if not is_healthy:
            all_healthy = False

    return {
        "timestamp": datetime.now().isoformat(),
        "all_healthy": all_healthy,
        "sources": health_report
    }


@router.post("/reset")
async def reset_data_sources() -> Dict[str, str]:
    """
    重置所有数据源状态

    将失败计数清零，重新启用所有数据源
    """
    message = []
    for source in multi_source_manager.sources:
        source.status.fail_count = 0
        source.status.available = True
        message.append(f"{source.name} 重置成功")

    return {
        "status": "success",
        "message": "; ".join(message)
    }


@router.get("/test")
async def test_data_sources() -> Dict[str, Any]:
    """
    测试所有数据源

    尝试从每个数据源获取数据，返回测试结果
    """
    test_codes = ["000001", "600000"]
    results = {}

    for source in multi_source_manager.sources:
        try:
            import time
            start = time.time()
            data = await source.get_realtime_quote(test_codes)
            elapsed = (time.time() - start) * 1000

            results[source.name] = {
                "success": len(data) > 0,
                "data_count": len(data),
                "response_time_ms": round(elapsed, 1),
                "sample": list(data.values())[:1] if data else None
            }
        except Exception as e:
            results[source.name] = {
                "success": False,
                "error": str(e)
            }

    return {
        "timestamp": datetime.now().isoformat(),
        "test_codes": test_codes,
        "results": results
    }
