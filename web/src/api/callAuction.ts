/**
 * 集合竞价相关 API
 */

import api from './index'

// 集合竞价数据
export interface CallAuctionData {
  code: string
  name: string
  trade_date: string
  auction_time: string
  price: number | null
  volume: number | null
  amount: number | null
  buy_volume: number | null
  sell_volume: number | null
  change_pct: number | null
  change_amount: number | null
  bid_ratio: number | null
}

// 集合竞价统计数据
export interface CallAuctionStats {
  trade_date: string
  total_count: number
  total_volume: number
  total_amount: number
  avg_price: number
  rise_count: number
  fall_count: number
  limit_up_count: number
  limit_down_count: number
}

// 集合竞价同步请求
export interface CallAuctionSyncRequest {
  trade_date: string
  codes?: string[]
}

// 集合竞价同步响应
export interface CallAuctionSyncResponse {
  success: boolean
  message: string
  count?: number
  results?: Record<string, number>
}

export const callAuctionApi = {
  // 获取集合竞价数据（可指定日期）
  getRealtime: (queryDate?: string) =>
    api.get<any, CallAuctionData[]>('/call-auction/realtime', {
      params: queryDate ? { query_date: queryDate } : {}
    }),

  // 获取指定股票的历史集合竞价数据
  getHistory: (code: string, startDate?: string, endDate?: string) =>
    api.get<any, CallAuctionData[]>(`/call-auction/history/${code}`, {
      params: { start_date: startDate, end_date: endDate }
    }),

  // 获取指定日期的集合竞价统计数据
  getStats: (date: string) =>
    api.get<any, CallAuctionStats>(`/call-auction/stats/${date}`),

  // 同步实时集合竞价数据
  syncRealtime: () =>
    api.post<any, CallAuctionSyncResponse>('/call-auction/sync/realtime'),

  // 同步历史集合竞价数据
  syncHistory: (request: CallAuctionSyncRequest) =>
    api.post<any, CallAuctionSyncResponse>('/call-auction/sync/history', request),
}
