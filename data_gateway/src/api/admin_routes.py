"""
数据网关管理接口
提供数据同步、任务管理等管理功能
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging
import asyncio

from ..services.sync_service import (
    sync_service,
    SyncStatus,
    SyncType
)
from ..services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============== 请求/响应模型 ==============

class SyncTaskRequest(BaseModel):
    """同步任务请求"""
    market: str                              # 市场: cn_a, hk, us
    sync_type: SyncType = SyncType.INCREMENTAL  # 同步类型
    symbols: Optional[List[str]] = None      # 股票列表 (None表示全部)
    period: str = "daily"                    # 周期
    start_date: Optional[str] = None         # 开始日期 (YYYY-MM-DD)
    end_date: Optional[str] = None           # 结束日期 (YYYY-MM-DD)
    days: int = 30                           # 增量同步天数


class SyncTaskResponse(BaseModel):
    """同步任务响应"""
    code: int = 0
    message: str = "success"
    data: Dict = {}


class TaskListResponse(BaseModel):
    """任务列表响应"""
    code: int = 0
    message: str = "success"
    data: Dict = {}


# ============== 后台任务管理 ==============

_running_tasks: Dict[str, asyncio.Task] = {}


async def run_sync_task(task_id: str):
    """后台执行同步任务"""
    task = sync_service.get_task(task_id)
    if not task:
        return

    async def progress_callback(t):
        """进度回调"""
        logger.info(f"Task {t.task_id} progress: {t.progress}% - {t.current_symbol}")

    try:
        await sync_service.start_sync(task_id, progress_callback)
    except Exception as e:
        logger.error(f"Background sync task {task_id} failed: {e}")
    finally:
        if task_id in _running_tasks:
            del _running_tasks[task_id]


# ============== API 接口 ==============

@admin_router.post("/sync/create", response_model=SyncTaskResponse)
async def create_sync_task(request: SyncTaskRequest, background_tasks: BackgroundTasks):
    """
    创建并启动数据同步任务

    **同步类型说明:**
    - `incremental`: 增量同步，同步最近N天的数据
    - `full`: 全量同步，同步所有历史数据
    - `symbol`: 单个股票同步

    **示例:**
    ```json
    {
      "market": "cn_a",
      "sync_type": "incremental",
      "days": 30
    }
    ```
    """
    try:
        # 检查是否有正在运行的任务
        active = sync_service.get_active_task()
        if active:
            return SyncTaskResponse(
                code=1,
                message=f"Another task {active.task_id} is running",
                data={"active_task": active.to_dict()}
            )

        # 创建任务
        if request.sync_type == SyncType.INCREMENTAL:
            task = await sync_service.incremental_sync(
                market=request.market,
                symbols=request.symbols or await sync_service.get_stock_list(request.market),
                days=request.days
            )
        elif request.sync_type == SyncType.FULL:
            task = await sync_service.full_sync(
                market=request.market,
                symbols=request.symbols
            )
        else:
            task = await sync_service.create_task(
                sync_type=request.sync_type,
                market=request.market,
                symbols=request.symbols or [],
                period=request.period,
                start_date=request.start_date or "",
                end_date=request.end_date or ""
            )

        # 覆盖日期参数
        if request.start_date:
            task.start_date = request.start_date
        if request.end_date:
            task.end_date = request.end_date

        # 启动后台任务
        background_tasks.add_task(run_sync_task, task.task_id)

        return SyncTaskResponse(
            data={
                "task_id": task.task_id,
                "message": "Sync task created and started",
                "task": task.to_dict()
            }
        )

    except Exception as e:
        logger.error(f"Failed to create sync task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/sync/status/{task_id}", response_model=SyncTaskResponse)
async def get_sync_status(task_id: str):
    """
    获取同步任务状态

    **返回字段说明:**
    - `status`: 任务状态 (pending/running/completed/failed/cancelled)
    - `progress`: 进度百分比 (0-100)
    - `result`: 同步结果 (完成后可用)
    """
    task = sync_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return SyncTaskResponse(
        data={
            "task": task.to_dict()
        }
    )


@admin_router.get("/sync/active", response_model=SyncTaskResponse)
async def get_active_task():
    """获取当前运行中的任务"""
    task = sync_service.get_active_task()
    if not task:
        return SyncTaskResponse(
            data={
                "active_task": None,
                "message": "No active task"
            }
        )

    return SyncTaskResponse(
        data={
            "active_task": task.to_dict()
        }
    )


@admin_router.get("/sync/tasks", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(10, description="返回最近N个任务", ge=1, le=100),
    status: Optional[SyncStatus] = Query(None, description="过滤状态")
):
    """
    获取任务列表

    **参数:**
    - `limit`: 返回最近N个任务 (默认10)
    - `status`: 按状态过滤
    """
    all_tasks = sync_service.get_all_tasks()

    # 按状态过滤
    if status:
        all_tasks = [t for t in all_tasks if t["status"] == status.value]

    # 按创建时间倒序，取前N个
    all_tasks.sort(key=lambda x: x["created_at"], reverse=True)
    tasks = all_tasks[:limit]

    return TaskListResponse(
        data={
            "total": len(all_tasks),
            "tasks": tasks
        }
    )


@admin_router.post("/sync/cancel/{task_id}", response_model=SyncTaskResponse)
async def cancel_task(task_id: str):
    """取消同步任务"""
    success = await sync_service.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task {task_id} (not found or not running)"
        )

    return SyncTaskResponse(
        data={
            "task_id": task_id,
            "message": "Task cancelled"
        }
    )


@admin_router.get("/stocks/list", response_model=SyncTaskResponse)
async def get_stock_list(
    market: str = Query(..., description="市场代码: cn_a, hk, us")
):
    """
    获取市场股票列表

    **用于全量同步时获取所有股票代码**
    """
    try:
        symbols = await sync_service.get_stock_list(market)

        return SyncTaskResponse(
            data={
                "market": market,
                "total": len(symbols),
                "symbols": symbols
            }
        )
    except Exception as e:
        logger.error(f"Failed to get stock list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/sync/quick", response_model=SyncTaskResponse)
async def quick_sync(
    market: str = Query(..., description="市场代码"),
    days: int = Query(30, description="同步最近N天", ge=1, le=365)
):
    """
    快速同步接口

    **快速增量同步指定市场最近N天的数据**

    **示例:**
    - `POST /api/v1/admin/sync/quick?market=cn_a&days=7`
    """
    try:
        # 检查是否有正在运行的任务
        active = sync_service.get_active_task()
        if active:
            return SyncTaskResponse(
                code=1,
                message=f"Another task {active.task_id} is running",
                data={"active_task": active.to_dict()}
            )

        # 创建增量同步任务
        task = await sync_service.incremental_sync(
            market=market,
            symbols=await sync_service.get_stock_list(market),
            days=days
        )

        # 启动后台任务
        asyncio.create_task(run_sync_task(task.task_id))

        return SyncTaskResponse(
            data={
                "task_id": task.task_id,
                "message": f"Quick sync started for {market} (last {days} days)",
                "task": task.to_dict()
            }
        )

    except Exception as e:
        logger.error(f"Failed to start quick sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/stats", response_model=SyncTaskResponse)
async def get_sync_stats():
    """获取同步统计信息"""
    all_tasks = sync_service.get_all_tasks()

    stats = {
        "total_tasks": len(all_tasks),
        "by_status": {},
        "by_market": {},
        "recent_tasks": all_tasks[:5]
    }

    for task in all_tasks:
        # 按状态统计
        status = task["status"]
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # 按市场统计
        market = task["market"]
        stats["by_market"][market] = stats["by_market"].get(market, 0) + 1

    return SyncTaskResponse(data=stats)


# ============== 定时调度器接口 ==============

@admin_router.get("/scheduler/status", response_model=SyncTaskResponse)
async def get_scheduler_status():
    """
    获取定时调度器状态

    **返回信息:**
    - `running`: 是否运行中
    - `next_run_time`: 下次运行时间
    - `jobs`: 定时任务列表
    """
    status = scheduler_service.get_status()

    # 格式化下次运行时间
    if status.get("next_run_time"):
        status["next_run_time"] = status["next_run_time"].strftime("%Y-%m-%d %H:%M:%S")

    return SyncTaskResponse(data=status)


@admin_router.post("/scheduler/trigger", response_model=SyncTaskResponse)
async def trigger_scheduler_sync(
    days: int = Query(30, description="同步最近N天", ge=1, le=365)
):
    """
    手动触发定时同步任务

    **立即执行增量同步（与定时任务相同的逻辑）**

    **示例:**
    - `POST /api/v1/admin/scheduler/trigger?days=7`
    """
    try:
        # 检查是否有正在运行的任务
        active = sync_service.get_active_task()
        if active:
            return SyncTaskResponse(
                code=1,
                message=f"Another task {active.task_id} is running",
                data={"active_task": active.to_dict()}
            )

        # 触发手动同步
        result = await scheduler_service.trigger_manual_sync(days=days)

        return SyncTaskResponse(
            data={
                "message": f"Manual sync triggered for {days} days",
                "result": result
            }
        )

    except Exception as e:
        logger.error(f"Failed to trigger manual sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
