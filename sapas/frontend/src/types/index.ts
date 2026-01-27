/**
 * 全局类型定义
 */

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  timestamp?: string
}

export interface PaginationParams {
  page: number
  pageSize: number
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  total: number
  page: number
  pageSize: number
  totalPages: number
  data: T[]
}

export interface User {
  id: number
  username: string
  email?: string
  nickname?: string
  role: string
  avatar?: string
  phone?: string
  isActive: boolean
  createdAt: string
  lastLoginAt?: string
}

export interface WatchlistGroup {
  id: number
  userId: number
  name: string
  description?: string
  icon?: string
  sortOrder: number
  isDefault: boolean
  createdAt: string
  itemCount?: number
  items?: WatchlistItem[]
}

export interface WatchlistItem {
  id: number
  groupId: number
  stockCode: string
  stockName?: string
  sortOrder: number
  note?: string
  alertConfig?: string
  currentPrice?: number
  changePct?: number
  peTtm?: number
  marketValue?: number
}

export interface Alert {
  id: number
  userId: number
  stockCode?: string
  alertType: string
  name: string
  conditionConfig: Record<string, unknown>
  frequency: string
  status: string
  triggerCount: number
  lastTriggeredAt?: string
  createdAt: string
  updatedAt: string
}

export interface BacktestRun {
  id: number
  userId: number
  strategyName: string
  strategyConfig: Record<string, unknown>
  startDate: string
  endDate: string
  initialCapital: number
  commissionRate: number
  slippage: number
  status: string
  createdAt: string
  completedAt?: string

  // 回测结果统计
  finalCapital?: number
  totalReturn?: number
  totalReturnPct?: number
  maxDrawdown?: number
  maxDrawdownPct?: number
  sharpeRatio?: number
  winRate?: number
  totalTrades?: number
  winningTrades?: number
  losingTrades?: number
  avgProfit?: number
  avgLoss?: number
  profitFactor?: number
  resultSummary?: Record<string, unknown>
  errorMessage?: string
}

export interface BacktestTrade {
  id: number
  backtestId: number
  stockCode: string
  tradeType: string
  tradeTime: string
  price: number
  quantity: number
  amount: number
  commission: number
  profit?: number
  profitPct?: number
  exitReason?: string
}

export interface ScreenerCondition {
  id: number
  userId: number
  name: string
  description?: string
  conditionConfig: Record<string, unknown>
  isPublic: boolean
  useCount: number
  lastUsedAt?: string
  createdAt: string
  updatedAt: string
}

export interface StockQuote {
  code: string
  name?: string
  price: number
  open?: number
  high?: number
  low?: number
  volume: number
  amount?: number
  change: number
  changePct: number
  preClose?: number
  highLimit?: number
  lowLimit?: number
  turnover?: number
  peTtm?: number
  peDyn?: number
  peStatic?: number
  pb?: number
  amplitude?: number
  committee?: number
  marketValue?: number
  circulationValue?: number
  timestamp?: string
}

export interface KlineData {
  symbol: string
  datetime: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  period: string
}

export interface MoneyFlowData {
  symbol: string
  date: string
  amount: number
  mainNetInflow: number
  mainNetRatio: number
  superLarge: MoneyFlowItem
  large: MoneyFlowItem
  medium: MoneyFlowItem
  small: MoneyFlowItem
}

export interface MoneyFlowItem {
  inflow: number
  outflow: number
  netInflow: number
  netRatio: number
}

export interface Sector {
  name: string
  changePct: number
  amount: number
  stockCount: number
}

export interface TradingTime {
  open: string
  close: string
}

export interface PriceAlertConfig {
  operator: '>' | '<' | '>=' | '<=' | '=='
  value: number
}

export interface IndicatorAlertConfig {
  indicator: string
  condition: string
  value: number
}

export interface MoneyFlowAlertConfig {
  minAmount?: number
  maxAmount?: number
  days?: number
}
