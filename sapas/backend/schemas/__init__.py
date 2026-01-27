"""
数据验证 schemas 包
"""
from .user import (
    UserLogin,
    UserRegister,
    UserResponse,
    TokenResponse,
    UserUpdate
)
from .watchlist import (
    WatchlistGroupCreate,
    WatchlistGroupUpdate,
    WatchlistGroupResponse,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemResponse,
    WatchlistResponse
)
from .alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertHistoryResponse
)
from .backtest import (
    BacktestConfig,
    BacktestRun,
    BacktestResult,
    BacktestTradeResponse
)
from .screener import (
    ScreenerConditionCreate,
    ScreenerConditionUpdate,
    ScreenerConditionResponse,
    ScreenerQuery,
    ScreenerResult
)
from .common import (
    ApiResponse,
    PaginationParams,
    PaginatedResponse
)

__all__ = [
    # User
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "TokenResponse",
    "UserUpdate",
    # Watchlist
    "WatchlistGroupCreate",
    "WatchlistGroupUpdate",
    "WatchlistGroupResponse",
    "WatchlistItemCreate",
    "WatchlistItemUpdate",
    "WatchlistItemResponse",
    "WatchlistResponse",
    # Alert
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertHistoryResponse",
    # Backtest
    "BacktestConfig",
    "BacktestRun",
    "BacktestResult",
    "BacktestTradeResponse",
    # Screener
    "ScreenerConditionCreate",
    "ScreenerConditionUpdate",
    "ScreenerConditionResponse",
    "ScreenerQuery",
    "ScreenerResult",
    # Common
    "ApiResponse",
    "PaginationParams",
    "PaginatedResponse",
]
