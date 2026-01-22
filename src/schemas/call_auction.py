"""
集合竞价相关数据模型
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class CallAuctionResponse(BaseModel):
    """集合竞价数据响应"""
    code: str
    name: str
    trade_date: str
    auction_time: str
    price: Optional[float] = None
    volume: Optional[int] = None
    amount: Optional[float] = None
    buy_volume: Optional[int] = None
    sell_volume: Optional[int] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None
    bid_ratio: Optional[float] = None

    class Config:
        from_attributes = True


class CallAuctionStatsResponse(BaseModel):
    """集合竞价统计数据响应"""
    trade_date: str
    total_count: int
    total_volume: int
    total_amount: float
    avg_price: float
    rise_count: int
    fall_count: int
    limit_up_count: int
    limit_down_count: int


class CallAuctionSyncRequest(BaseModel):
    """集合竞价数据同步请求"""
    trade_date: str
    codes: Optional[List[str]] = None
