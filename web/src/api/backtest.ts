/**
 * 回测相关 API
 */

import api from './index'

// 策略参数
export interface StrategyParam {
  name: string
  display_name: string
  default: number
  min: number
  max: number
}

// 策略信息
export interface StrategyInfo {
  name: string
  display_name: string
  description: string
  category: string
  params: StrategyParam[]
}

// 回测配置请求
export interface BacktestConfigRequest {
  strategy_name: string
  strategy_params: Record<string, any>
  start_date: string
  end_date: string
  initial_cash?: number
  commission?: number
  slippage?: number
  max_positions?: number
  position_size?: number
  hold_days?: number
  rebalance_freq?: string
  stock_pool?: string[]
}

// 交易记录
export interface TradeRecord {
  date: string
  code: string
  name: string
  action: string
  price: number
  shares: number
  amount: number
  profit?: number
}

// K线数据
export interface BacktestKLineData {
  trade_date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount?: number | null
}

// 绩效指标
export interface PerformanceMetrics {
  initial_cash: number
  final_cash: number
  total_return: number
  annual_return: number
  sharpe_ratio: number | null
  max_drawdown: number
  max_drawdown_duration: number
  total_trades: number
  profitable_trades: number
  losing_trades: number
  win_rate: number
  avg_profit: number
  avg_loss: number
  profit_loss_ratio: number
  start_date: string
  end_date: string
  trading_days: number
}

// 回测结果响应
export interface BacktestResultResponse {
  config: BacktestConfigRequest
  performance: PerformanceMetrics
  equity_curve: Array<{ date: string; equity: number; cash: number; positions: number }>
  trades: TradeRecord[]
  daily_returns?: number[]
  kline_data?: Record<string, BacktestKLineData[]> | null  // {code: [K线数据]}
  status: string
  error?: string | null
}

// 股票列表项
export interface StockListItem {
  code: string
  name: string
  industry?: string
}

// 股票列表响应
export interface StockListResponse {
  items: StockListItem[]
  total: number
}

export const backtestApi = {
  // 获取策略列表
  getStrategies: () =>
    api.get<any, StrategyInfo[]>('/backtest/strategies'),

  // 运行回测
  run: (config: BacktestConfigRequest) =>
    api.post<any, BacktestResultResponse>('/backtest/run', config),

  // 获取股票列表
  getStockList: (params?: { market?: string; industry?: string }) =>
    api.get<any, StockListResponse>('/backtest/stock-list', { params }),
}
