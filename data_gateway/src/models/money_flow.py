"""
资金流向数据模型
每日保存资金流向历史数据
"""
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Float, Numeric, DateTime, Index, UniqueConstraint

from ..database import Base


class MoneyFlow(Base):
    """
    资金流向数据表

    每天一条记录，保存当日资金流向数据
    """
    __tablename__ = "dg_money_flow"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, comment="交易日期")

    # 成交额
    amount = Column(Float, nullable=True, comment="成交额（元）")

    # 主力资金
    main_net_inflow = Column(Float, nullable=True, comment="主力净流入金额")
    main_net_ratio = Column(Float, nullable=True, comment="主力净流入金额净比(%)")

    # 超大单 (单笔成交额 > 1000万元)
    super_large_inflow = Column(Float, nullable=True, comment="超大单流入金额")
    super_large_outflow = Column(Float, nullable=True, comment="超大单流出金额")
    super_large_net_inflow = Column(Float, nullable=True, comment="超大单净流入金额")
    super_large_net_ratio = Column(Float, nullable=True, comment="超大单净流入金额净比(%)")

    # 大单 (单笔成交额 500万 - 1000万元)
    large_inflow = Column(Float, nullable=True, comment="大单流入金额")
    large_outflow = Column(Float, nullable=True, comment="大单流出金额")
    large_net_inflow = Column(Float, nullable=True, comment="大单净流入金额")
    large_net_ratio = Column(Float, nullable=True, comment="大单净流入金额净比(%)")

    # 中单 (单笔成交额 100万 - 500万元)
    medium_inflow = Column(Float, nullable=True, comment="中单流入金额")
    medium_outflow = Column(Float, nullable=True, comment="中单流出金额")
    medium_net_inflow = Column(Float, nullable=True, comment="中单净流入金额")
    medium_net_ratio = Column(Float, nullable=True, comment="中单净流入金额净比(%)")

    # 小单 (单笔成交额 < 100万元)
    small_inflow = Column(Float, nullable=True, comment="小单流入金额")
    small_outflow = Column(Float, nullable=True, comment="小单流出金额")
    small_net_inflow = Column(Float, nullable=True, comment="小单净流入金额")
    small_net_ratio = Column(Float, nullable=True, comment="小单净流入金额净比(%)")

    market_code = Column(String(20), nullable=False, default="cn_a", comment="市场代码")
    source_code = Column(String(50), comment="数据来源 (miana, etc)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    __table_args__ = (
        UniqueConstraint('code', 'trade_date', 'market_code', name='uk_money_flow_code_date'),
        Index('idx_money_flow_code', 'code'),
        Index('idx_money_flow_date', 'trade_date'),
        Index('idx_money_flow_market', 'market_code'),
        Index('idx_money_flow_main_net', 'main_net_inflow'),
    )
