/**
 * 工具函数
 */

/**
 * 格式化数字，添加千位分隔符
 */
export function formatNumber(num: number, decimals = 2): string {
  if (num === null || num === undefined) return '-'
  return num.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 格式化百分比
 */
export function formatPercent(value: number, decimals = 2): string {
  if (value === null || value === undefined) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/**
 * 格式化金额（万、亿单位）
 */
export function formatAmount(amount: number): string {
  if (amount === null || amount === undefined) return '-'

  const abs = Math.abs(amount)
  if (abs >= 100000000) {
    return `${(amount / 100000000).toFixed(2)}亿`
  }
  if (abs >= 10000) {
    return `${(amount / 10000).toFixed(2)}万`
  }
  return formatNumber(amount, 0)
}

/**
 * 格式化日期时间
 */
export function formatDateTime(dateStr: string, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!dateStr) return '-'

  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')

  return format
    .replace('YYYY', year.toString())
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化日期
 */
export function formatDate(dateStr: string): string {
  return formatDateTime(dateStr, 'YYYY-MM-DD')
}

/**
 * 格式化时间
 */
export function formatTime(dateStr: string): string {
  return formatDateTime(dateStr, 'HH:mm:ss')
}

/**
 * 获取涨跌颜色类名
 */
export function getPriceColorClass(value: number): string {
  if (value > 0) return 'text-red'
  if (value < 0) return 'text-green'
  return 'text-gray'
}

/**
 * 获取涨跌颜色（用于ECharts）
 */
export function getPriceColor(value: number): string {
  if (value > 0) return '#f56c6c'
  if (value < 0) return '#67c23a'
  return '#909399'
}

/**
 * 复制文本到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn.apply(this, args), delay)
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastTime = 0
  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      fn.apply(this, args)
    }
  }
}

/**
 * 深度克隆对象
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as any
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as any
  if (obj instanceof Object) {
    const copy: any = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        copy[key] = deepClone(obj[key])
      }
    }
    return copy
  }
  return obj
}

/**
 * 生成随机字符串
 */
export function randomString(length = 8): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 下载文件
 */
export function downloadFile(data: Blob, filename: string): void {
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 股票代码格式化
 */
export function formatStockCode(code: string): string {
  if (!code) return '-'
  // 假设A股代码格式为 6位数字
  if (/^\d{6}$/.test(code)) {
    const market = code.startsWith('6') ? 'SH' : 'SZ'
    return `${market}${code}`
  }
  return code
}

/**
 * 解析股票代码
 */
export function parseStockCode(code: string): { market: string; symbol: string } | null {
  if (!code) return null

  // 6位纯数字
  if (/^\d{6}$/.test(code)) {
    const market = code.startsWith('6') ? 'SH' : 'SZ'
    return { market, symbol: code }
  }

  // SH000001 或 SZ000001 格式
  const match = code.match(/^(SH|SZ|BJ)(\d{6})$/)
  if (match) {
    return { market: match[1], symbol: match[2] }
  }

  return null
}

/**
 * 判断是否为交易时间
 */
export function isTradingTime(): boolean {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false // 周末

  const hours = now.getHours()
  const minutes = now.getMinutes()
  const time = hours * 60 + minutes

  // 上午 9:30 - 11:30
  const morningStart = 9 * 60 + 30
  const morningEnd = 11 * 60 + 30

  // 下午 13:00 - 15:00
  const afternoonStart = 13 * 60
  const afternoonEnd = 15 * 60

  return (time >= morningStart && time < morningEnd) ||
         (time >= afternoonStart && time < afternoonEnd)
}

/**
 * 获取当前交易日期
 */
export function getTradingDate(): string {
  const now = new Date()
  const hours = now.getHours()

  // 如果当前时间在 9:00 之前，返回上一个交易日
  if (hours < 9) {
    now.setDate(now.getDate() - 1)
  }

  // 跳过周末
  const day = now.getDay()
  if (day === 0) { // 周日
    now.setDate(now.getDate() - 2)
  } else if (day === 6) { // 周六
    now.setDate(now.getDate() - 1)
  }

  return formatDate(now.toISOString())
}

/**
 * 本地存储封装
 */
export const storage = {
  get<T>(key: string, defaultValue?: T): T | null {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue ?? null
    } catch {
      return defaultValue ?? null
    }
  },

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (err) {
      console.error('Failed to save to localStorage:', err)
    }
  },

  remove(key: string): void {
    localStorage.removeItem(key)
  },

  clear(): void {
    localStorage.clear()
  }
}
