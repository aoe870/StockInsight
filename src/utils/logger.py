"""
日志工具模块
使用 loguru 实现结构化日志
"""

import sys
from pathlib import Path
from loguru import logger

from src.config import settings


def setup_logger():
    """配置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 简化格式（用于文件）
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    # 确保日志目录存在
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    alert_log_path = Path(settings.alert_log_file)
    alert_log_path.parent.mkdir(parents=True, exist_ok=True)

    # 主日志文件（按日期轮转）
    logger.add(
        settings.log_file,
        format=file_format,
        level=settings.log_level,
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="gz",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )

    # 告警专用日志
    logger.add(
        settings.alert_log_file,
        format=file_format,
        level="INFO",
        rotation="00:00",
        retention="90 days",  # 告警日志保留更久
        compression="gz",
        encoding="utf-8",
        filter=lambda record: record["extra"].get("alert", False),
    )

    logger.info(f"日志系统初始化完成，级别: {settings.log_level}")
    return logger


def get_alert_logger():
    """获取告警专用 logger"""
    return logger.bind(alert=True)


# 初始化日志
setup_logger()

# 导出
__all__ = ["logger", "get_alert_logger", "setup_logger"]

