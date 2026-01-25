"""
同步日志模型
"""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Integer, Text, DateTime, Index

from ..database import Base


class SyncLog(Base):
    """
    数据同步日志表

    记录每次数据同步任务的执行情况
    """
    __tablename__ = "dg_sync_logs"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(100), comment="任务ID")
    sync_type = Column(String(20), nullable=False, comment="同步类型 (full, incremental)")
    market_code = Column(String(20), nullable=False, comment="市场代码")
    stock_code = Column(String(20), comment="股票代码")
    status = Column(String(20), nullable=False, comment="状态 (pending, running, completed, failed)")
    start_date = Column(String(20), comment="开始日期")
    end_date = Column(String(20), comment="结束日期")
    records_count = Column(Integer, default=0, comment="记录数量")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, comment="开始时间")
    finished_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        Index('idx_dg_sync_logs_task', 'task_id'),
        Index('idx_dg_sync_logs_stock', 'stock_code', 'market_code'),
        Index('idx_dg_sync_logs_status', 'status'),
    )
