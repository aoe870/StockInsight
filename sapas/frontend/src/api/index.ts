/**
 * API 客户端
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

const baseURL = 'http://localhost:8082/api/v1'

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    const res = response.data as ApiResponse<any>
    if (res.code !== 0) {
      console.error('API Error:', res.message)
    }
    return response
  }
)

// 通用请求函数
export const api = {
  // ============== 认证 API ==============

  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/login', {
      username,
      password
    })
    return response.data
  },

  logout: async () => {
    const response = await apiClient.post('/auth/logout')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    return response.data
  },

  register: async (username: string, password: string, email?: string) => {
    const response = await apiClient.post('/auth/register', {
      username,
      password,
      email
    })
    return response.data
  },

  getProfile: async () => {
    const response = await apiClient.get('/auth/profile')
    return response.data
  },

  changePassword: async (oldPassword: string, newPassword: string) => {
    const response = await apiClient.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    })
    return response.data
  },

  post: async (url: string, data?: any) => {
    const response = await apiClient.post(url, data)
    return response.data
  },

  // ============== 自选股 API ==============

  getGroups: async () => {
    const response = await apiClient.get('/watchlist/groups')
    return response.data
  },

  createGroup: async (name: string, description?: string) => {
    const response = await apiClient.post('/watchlist/groups', {
      name,
      description
    })
    return response.data
  },

  updateGroup: async (id: number, data: any) => {
    const response = await apiClient.put(`/watchlist/groups/${id}`, data)
    return response.data
  },

  deleteGroup: async (id: number) => {
    const response = await apiClient.delete(`/watchlist/groups/${id}`)
    return response.data
  },

  getItems: async (groupId?: number) => {
    const url = groupId ? `/watchlist/items?group_id=${groupId}` : '/watchlist/items'
    const response = await apiClient.get(url)
    return response.data
  },

  addItem: async (stockCodes: string[]) => {
    const response = await apiClient.post('/watchlist/items', {
      stock_codes: stockCodes
    })
    return response.data
  },

  updateItem: async (id: number, data: any) => {
    const response = await apiClient.put(`/watchlist/items/${id}`, data)
    return response.data
  },

  deleteItem: async (id: number) => {
    const response = await apiClient.delete(`/watchlist/items/${id}`)
    return response.data
  },

  // ============== 预警 API ==============

  getAlerts: async () => {
    const response = await apiClient.get('/alerts')
    return response.data
  },

  createAlert: async (data: any) => {
    const response = await apiClient.post('/alerts', data)
    return response.data
  },

  updateAlert: async (id: number, data: any) => {
    const response = await apiClient.put(`/alerts/${id}`, data)
    return response.data
  },

  deleteAlert: async (id: number) => {
    const response = await apiClient.delete(`/alerts/${id}`)
    return response.data
  },

  enableAlert: async (id: number) => {
    const response = await apiClient.post(`/alerts/${id}/enable`)
    return response.data
  },

  disableAlert: async (id: number) => {
    const response = await apiClient.post(`/alerts/${id}/disable`)
    return response.data
  },

  getAlertHistory: async (alertId?: number, limit?: number, status?: string) => {
    const params = new URLSearchParams()
    if (alertId) params.append('alert_id', alertId.toString())
    if (limit) params.append('limit', limit.toString())
    if (status) params.append('status', status)

    const response = await apiClient.get(`/alerts/history?${params}`)
    return response.data
  },

  // ============== 回测 API ==============

  getStrategies: async () => {
    const response = await apiClient.get('/backtest/strategies')
    return response.data
  },

  getStrategyTemplate: async (name: string) => {
    const response = await apiClient.get(`/backtest/strategies/${name}`)
    return response.data
  },

  runBacktest: async (config: any) => {
    const response = await apiClient.post('/backtest/run', config)
    return response.data
  },

  getBacktestRuns: async (limit?: number, status?: string) => {
    const params = new URLSearchParams()
    if (limit) params.append('limit', limit.toString())
    if (status) params.append('status', status)

    const response = await apiClient.get(`/backtest/runs?${params}`)
    return response.data
  },

  getBacktestResult: async (runId: number) => {
    const response = await apiClient.get(`/backtest/runs/${runId}`)
    return response.data
  },

  deleteBacktestRun: async (runId: number) => {
    const response = await apiClient.delete(`/backtest/runs/${runId}`)
    return response.data
  },

  cancelBacktestRun: async (runId: number) => {
    const response = await apiClient.post(`/backtest/runs/${runId}/cancel`)
    return response.data
  },

  // ============== 选股 API ==============

  getScreenerTemplates: async () => {
    const response = await apiClient.get('/screener/templates')
    return response.data
  },

  screenerQuery: async (params: any) => {
    const response = await apiClient.post('/screener/query', params)
    return response.data
  },

  getScreenerConditions: async () => {
    const response = await apiClient.get('/screener/conditions')
    return response.data
  },

  createScreenerCondition: async (data: any) => {
    const response = await apiClient.post('/screener/conditions', data)
    return response.data
  },

  updateScreenerCondition: async (id: number, data: any) => {
    const response = await apiClient.put(`/screener/conditions/${id}`, data)
    return response.data
  },

  deleteScreenerCondition: async (id: number) => {
    const response = await apiClient.delete(`/screener/conditions/${id}`)
    return response.data
  },

  // ============== 股票数据 API ==============

  getStocksQuote: async (symbols?: string[], market?: string) => {
    const params = new URLSearchParams()
    if (symbols && symbols.length > 0) {
      symbols.forEach(s => params.append('symbols', s))
    }
    if (market) params.append('market', market)

    const response = await apiClient.get(`/stocks/quote?${params}`)
    return response.data
  },

  getStockKline: async (symbol: string, market?: string, period?: string, startDate?: string, endDate?: string) => {
    const params = new URLSearchParams()
    params.append('symbol', symbol)
    if (market) params.append('market', market)
    if (period) params.append('period', period)
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)

    const response = await apiClient.get(`/stocks/kline/${symbol}?${params}`)
    return response.data
  },

  getStockFundamentals: async (symbol: string, market?: string) => {
    const params = new URLSearchParams()
    params.append('symbol', symbol)
    if (market) params.append('market', market)

    const response = await apiClient.get(`/stocks/fundamentals/${symbol}?${params}`)
    return response.data
  },

  getStockMoneyFlow: async (code: string, date?: string) => {
    const params = new URLSearchParams()
    if (date) params.append('date', date)

    const response = await apiClient.get(`/stocks/money-flow/${code}?${params}`)
    return response.data
  },

  getMoneyFlowRanking: async (market?: string, limit?: number) => {
    const params = new URLSearchParams()
    if (market) params.append('market', market)
    if (limit) params.append('limit', limit?.toString())

    const response = await apiClient.get(`/stocks/money-flow/ranking?${params}`)
    return response.data
  },

  getIndustrySectors: async () => {
    const response = await apiClient.get('/stocks/sectors/industry')
    return response.data
  },

  getConceptSectors: async () => {
    const response = await apiClient.get('/stocks/sectors/concept')
    return response.data
  },

  getSectorStocks: async (name: string, limit?: number) => {
    const params = new URLSearchParams()
    if (limit) params.append('limit', limit?.toString())

    const response = await apiClient.get(`/stocks/sectors/${name}/stocks?${params}`)
    return response.data
  },

  searchStocks: async (keyword: string, market?: string, limit?: number) => {
    const params = new URLSearchParams()
    params.append('keyword', keyword)
    if (market) params.append('market', market)
    if (limit) params.append('limit', limit?.toString())

    const response = await apiClient.get(`/stocks/search?${params}`)
    return response.data
  },

  getStockList: async (market?: string, limit?: number, offset?: number) => {
    const params = new URLSearchParams()
    if (market) params.append('market', market)
    if (limit) params.append('limit', limit?.toString())
    if (offset) params.append('offset', offset?.toString())

    const response = await apiClient.get(`/stocks/list?${params}`)
    return response.data
  }
}

export default api
