import axios from 'axios'
import { getToken, clearAuth } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证 token
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401 未授权，清除认证并跳转登录
    if (error.response?.status === 401) {
      clearAuth()
      router.push('/login')
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default api

// ==================== 股票相关 API ====================
export interface Stock {
  code: string
  name: string
  market: string
  industry?: string
}

export interface KLineData {
  trade_date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount?: number
  change_pct?: number
}

export interface StockListParams {
  keyword?: string
  market?: string
  page?: number
  page_size?: number
}

// 股票实时行情
export interface StockQuote {
  code: string
  current: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  volume: number
  trade_date: string
}

// 资金流向数据类型
export interface FundFlowData {
  date: string
  close: number
  change_pct: number
  main_net_amount: number
  main_net_pct: number
  super_large_net_amount: number
  super_large_net_pct: number
  large_net_amount: number
  large_net_pct: number
  medium_net_amount: number
  medium_net_pct: number
  small_net_amount: number
  small_net_pct: number
}

export interface FundFlowResponse {
  code: string
  name: string
  market: string
  data: FundFlowData[]
}

// 分时数据类型
export interface MinuteData {
  time: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount: number
  avg_price?: number
}

export const stockApi = {
  // 获取股票列表
  getList: (params: StockListParams) =>
    api.get<any, { items: Stock[]; total: number }>('/stocks', { params }),

  // 搜索股票
  search: (keyword: string) =>
    api.get<any, Stock[]>('/stocks/search', { params: { keyword } }),

  // 获取K线数据
  getKLine: (code: string, params?: { start_date?: string; end_date?: string; adjust?: string; period?: string; limit?: number }) =>
    api.get<any, { code: string; name: string; adjust: string; period: string; data: KLineData[] }>(`/stocks/${code}/kline`, { params }),

  // 获取分时数据
  getMinuteData: (code: string, period?: string) =>
    api.get<any, { code: string; name: string; period: string; data: MinuteData[] }>(`/stocks/${code}/minute`, { params: { period: period || '1' } }),

  // 获取技术指标（基础）
  getIndicators: (code: string, params?: { indicators?: string; period?: number }) =>
    api.get<any, any>(`/stocks/${code}/indicators`, { params }),

  // 获取完整技术指标数据
  getFullIndicators: (code: string, params?: { indicators?: string; period?: string; limit?: number }) =>
    api.get<any, { code: string; name: string; period: string; indicators: string[]; data: Record<string, any>[] }>(`/stocks/${code}/indicators/full`, { params }),

  // 批量获取实时行情
  getBatchQuote: (codes: string[]) =>
    api.post<any, { items: StockQuote[] }>('/stocks/quote/batch', codes),

  // 获取资金流向数据
  getFundFlow: (code: string, params?: { start_date?: string; end_date?: string; days?: number }) =>
    api.get<any, FundFlowResponse>(`/stocks/${code}/fundflow`, { params }),
}

// ==================== 自选股 API ====================
export interface WatchlistItem {
  id: number
  stock_code: string
  stock_name: string
  sort_order: number
  note?: string
  added_at: string
}

export interface WatchlistResponse {
  total: number
  items: WatchlistItem[]
}

export const watchlistApi = {
  // 获取自选股列表
  getList: async (group?: string): Promise<WatchlistItem[]> => {
    const response = await api.get<any, WatchlistResponse>('/watchlist', { params: { group } })
    return response.items
  },
  
  // 添加自选股
  add: (data: { stock_code: string; group_name?: string; notes?: string }) =>
    api.post<any, WatchlistItem>('/watchlist', data),
  
  // 删除自选股
  remove: (id: number) =>
    api.delete(`/watchlist/${id}`),
  
  // 更新排序
  updateOrder: (items: { id: number; sort_order: number }[]) =>
    api.put('/watchlist/order', { items }),
}

// ==================== 预警 API ====================
export interface AlertRule {
  id: number
  stock_code: string
  stock_name: string
  alert_type: string
  condition: string
  threshold: number
  is_enabled: boolean
  created_at: string
}

export interface AlertHistory {
  id: number
  rule_id: number
  stock_code: string
  alert_type: string
  message: string
  triggered_at: string
}

export const alertApi = {
  // 获取预警规则
  getRules: () =>
    api.get<any, AlertRule[]>('/alerts/rules'),
  
  // 创建预警规则
  createRule: (data: Partial<AlertRule>) =>
    api.post<any, AlertRule>('/alerts/rules', data),
  
  // 删除预警规则
  deleteRule: (id: number) =>
    api.delete(`/alerts/rules/${id}`),

  // 获取预警历史
  getHistory: (params?: { limit?: number }) =>
    api.get<any, AlertHistory[]>('/alerts/history', { params }),
}

// ==================== 大盘指数 API ====================
export interface IndexQuote {
  code: string
  name: string
  current: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  volume: number
  amount: number
}

export interface IndexInfo {
  code: string
  name: string
  market: string
}

export const indexApi = {
  // 获取指数列表
  getList: () =>
    api.get<any, { items: IndexInfo[] }>('/index/list'),

  // 获取实时行情
  getRealtime: () =>
    api.get<any, { items: IndexQuote[] }>('/index/realtime'),

  // 获取指数K线
  getKLine: (code: string, params?: { limit?: number }) =>
    api.get<any, { code: string; name: string; data: KLineData[] }>(`/index/${code}/kline`, { params }),
}

// ==================== 选股 API ====================
export interface ScreenerResult {
  code: string
  name: string
  market: string
  industry: string
  close: number
  change_pct: number
  volume: number
  trade_date: string
}

export interface ScreenerStatus {
  is_running: boolean
  started_at: string | null
  total: number
  processed: number
  matched: number
  results: ScreenerResult[]
  strategy: string | null
  formula: string | null
  error: string | null
}

export interface StrategyParam {
  key: string
  name: string
  default: number
  min: number
  max: number
}

export interface Strategy {
  id: string
  name: string
  description: string
  category: string
  params: StrategyParam[]
  formula: string
}

export interface RunScreenerRequest {
  strategy_id?: string
  formula?: string
  params?: Record<string, number>
  market?: string
}

export const screenerApi = {
  // 获取选股策略列表
  getStrategies: () =>
    api.get<any, { strategies: Strategy[] }>('/screener/strategies'),

  // 获取策略详情
  getStrategy: (id: string) =>
    api.get<any, Strategy>(`/screener/strategies/${id}`),

  // 获取选股状态
  getStatus: () =>
    api.get<any, { status: ScreenerStatus }>('/screener/status'),

  // 运行选股（通用接口）
  run: (request: RunScreenerRequest) =>
    api.post<any, { success: boolean; message: string; strategy_id: string }>('/screener/run', request),

  // 停止选股
  stop: () =>
    api.post<any, { success: boolean; message: string }>('/screener/stop'),

  // 获取选股结果
  getResults: (params?: { sort_by?: string; sort_order?: string }) =>
    api.get<any, { total: number; strategy: string; items: ScreenerResult[] }>('/screener/results', { params }),
}

// ==================== 认证 API ====================
import type { UserInfo } from '@/stores/auth'
import { setAuth } from '@/stores/auth'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
  nickname?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export const authApi = {
  // 登录
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post<any, TokenResponse>('/auth/login', data)
    setAuth(response.access_token, response.user)
    return response
  },

  // 注册
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await api.post<any, TokenResponse>('/auth/register', data)
    setAuth(response.access_token, response.user)
    return response
  },

  // 获取当前用户
  getMe: () =>
    api.get<any, UserInfo>('/auth/me'),

  // 更新个人信息
  updateProfile: (data: { nickname?: string; email?: string; avatar?: string }) =>
    api.put<any, UserInfo>('/auth/profile', data),

  // 修改密码
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post<any, { success: boolean; message: string }>('/auth/change-password', data),

  // 登出
  logout: async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      clearAuth()
    }
  },
}
