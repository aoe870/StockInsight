<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { stockApi, watchlistApi, type KLineData, type MinuteData } from '@/api'
import { ElMessage } from 'element-plus'
import { Star, StarFilled, RefreshRight } from '@element-plus/icons-vue'
import KLineChart from '@/components/KLineChart.vue'

const route = useRoute()
const loading = ref(false)
const stockCode = ref('')
const stockName = ref('')
const klineData = ref<KLineData[]>([])
const minuteData = ref<MinuteData[]>([])
const indicatorData = ref<Record<string, any>[]>([])
const adjust = ref('qfq') // 默认使用前复权（与 sync_all_klines.py 同步的数据一致）
const period = ref('daily')
const selectedIndicators = ref(['MA', 'VOL', 'MACD'])
const isInWatchlist = ref(false)

// WebSocket 实时推送
const wsConnected = ref(false)
const lastRefreshTime = ref<Date | null>(null)
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

// 是否是分时模式
const isMinuteMode = computed(() => period.value === 'minute')

const adjustOptions = [
  { label: '后复权', value: 'hfq' },
  { label: '前复权', value: 'qfq' },
  { label: '不复权', value: 'none' },
]

// 数据范围选项
const dataRange = ref(500) // 默认500条
const dataRangeOptions = [
  { label: '近1年', value: 250 },
  { label: '近2年', value: 500 },
  { label: '近5年', value: 1250 },
  { label: '近10年', value: 2500 },
  { label: '全部', value: 10000 },
]

// 获取 K 线数据
const fetchKLine = async (showLoading = true) => {
  if (!stockCode.value) return
  if (showLoading) loading.value = true
  try {
    const res = await stockApi.getKLine(stockCode.value, {
      adjust: adjust.value,
      period: period.value,
      limit: dataRange.value,
    })
    stockName.value = res.name
    klineData.value = res.data
    lastRefreshTime.value = new Date()

    // 同时获取指标数据
    await fetchIndicators()
  } catch (error) {
    console.error('获取K线数据失败:', error)
    if (showLoading) ElMessage.error('获取K线数据失败')
  } finally {
    loading.value = false
  }
}

// 获取分时数据
const fetchMinuteData = async (showLoading = true) => {
  if (!stockCode.value) return
  if (showLoading) loading.value = true
  try {
    const res = await stockApi.getMinuteData(stockCode.value, '1')
    stockName.value = res.name
    minuteData.value = res.data
    // 转换分时数据为 KLineData 格式以兼容图表
    klineData.value = res.data.map(d => ({
      trade_date: d.time,
      open: d.open,
      close: d.close,
      high: d.high,
      low: d.low,
      volume: d.volume,
      amount: d.amount,
      change_pct: 0,
    }))
    lastRefreshTime.value = new Date()
    // 分时模式不获取指标数据
    indicatorData.value = []
  } catch (error) {
    console.error('获取分时数据失败:', error)
    if (showLoading) ElMessage.error('获取分时数据失败')
  } finally {
    loading.value = false
  }
}

// 获取数据（根据周期类型选择）
const fetchData = async (showLoading = true) => {
  if (isMinuteMode.value) {
    await fetchMinuteData(showLoading)
  } else {
    await fetchKLine(showLoading)
  }
}

// ==================== WebSocket 实时推送 ====================

// 连接 WebSocket
const connectWebSocket = () => {
  if (!stockCode.value || ws?.readyState === WebSocket.OPEN) return

  const wsUrl = `ws://${window.location.hostname}:8081/ws/stock`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('个股 WebSocket 已连接')
    wsConnected.value = true
    // 订阅当前股票
    ws?.send(JSON.stringify({
      action: 'subscribe',
      codes: [stockCode.value]
    }))
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'stock_quote' && msg.data?.code === stockCode.value) {
        // 更新最新价格数据
        const quote = msg.data
        lastRefreshTime.value = new Date()
        // 更新 klineData 最后一条（如果是分时模式）
        if (isMinuteMode.value && klineData.value.length > 0) {
          const last = klineData.value[klineData.value.length - 1]
          if (last.trade_date === quote.time) {
            // 更新最后一条
            last.close = quote.current
            last.high = Math.max(last.high, quote.high)
            last.low = Math.min(last.low, quote.low)
            last.volume = quote.volume
          } else {
            // 添加新的一条
            klineData.value.push({
              trade_date: quote.time,
              open: quote.open,
              close: quote.current,
              high: quote.high,
              low: quote.low,
              volume: quote.volume,
              amount: quote.amount || 0,
              change_pct: 0,
            })
          }
        }
      }
    } catch (e) {
      console.error('解析消息失败:', e)
    }
  }

  ws.onclose = () => {
    console.log('个股 WebSocket 断开')
    wsConnected.value = false
    // 分时模式下自动重连
    if (isMinuteMode.value) {
      reconnectTimer = setTimeout(connectWebSocket, 5000)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket 错误:', error)
  }
}

// 断开 WebSocket
const disconnectWebSocket = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    // 取消订阅
    if (ws.readyState === WebSocket.OPEN && stockCode.value) {
      ws.send(JSON.stringify({
        action: 'unsubscribe',
        codes: [stockCode.value]
      }))
    }
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

// 页面可见性控制
const handleVisibilityChange = () => {
  if (document.hidden) {
    disconnectWebSocket()
  } else if (isMinuteMode.value) {
    connectWebSocket()
  }
}

// 格式化刷新时间
const lastRefreshTimeText = computed(() => {
  if (!lastRefreshTime.value) return ''
  return lastRefreshTime.value.toLocaleTimeString()
})

// 获取指标数据（分时模式不获取）
const fetchIndicators = async () => {
  if (!stockCode.value || selectedIndicators.value.length === 0 || isMinuteMode.value) {
    indicatorData.value = []
    return
  }
  try {
    const res = await stockApi.getFullIndicators(stockCode.value, {
      indicators: selectedIndicators.value.join(','),
      period: period.value,
      limit: dataRange.value,
    })
    indicatorData.value = res.data || []
  } catch (error) {
    console.error('获取指标数据失败:', error)
  }
}

// 数据范围变化
const onDataRangeChange = () => {
  fetchData()
}

// 周期变化
const onPeriodChange = async (newPeriod: string) => {
  const wasMinuteMode = isMinuteMode.value
  period.value = newPeriod

  // 如果从分时切换到其他模式，断开 WebSocket
  if (wasMinuteMode && !isMinuteMode.value) {
    disconnectWebSocket()
  }

  // 获取数据
  await fetchData()

  // 如果切换到分时模式，连接 WebSocket
  if (!wasMinuteMode && isMinuteMode.value) {
    connectWebSocket()
  }
}

// 指标变化
const onIndicatorChange = async (indicators: string[]) => {
  selectedIndicators.value = indicators
  await fetchIndicators()
}

const addToWatchlist = async () => {
  try {
    await watchlistApi.add({ stock_code: stockCode.value })
    isInWatchlist.value = true
    ElMessage.success('已添加到自选股')
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

const latestData = () => {
  if (klineData.value.length === 0) return null
  return klineData.value[klineData.value.length - 1]
}

const priceChange = () => {
  const latest = latestData()
  if (!latest) return { value: 0, percent: 0, class: 'price-flat' }
  const change = latest.change_pct || 0
  return {
    value: (latest.close - latest.open).toFixed(2),
    percent: change.toFixed(2),
    class: change > 0 ? 'price-up' : change < 0 ? 'price-down' : 'price-flat',
  }
}

watch(() => route.params.code, (newCode, oldCode) => {
  if (newCode) {
    // 如果切换股票，先断开旧的 WebSocket 订阅
    if (oldCode && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'unsubscribe',
        codes: [oldCode]
      }))
    }

    stockCode.value = newCode as string
    // 初始加载时使用日K
    period.value = 'daily'
    fetchData()

    // 如果之前是分时模式，需要订阅新股票
    if (isMinuteMode.value && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'subscribe',
        codes: [newCode]
      }))
    }
  }
}, { immediate: true })

// 复权类型变化时重新获取数据（分时模式不需要）
watch(adjust, () => {
  if (!isMinuteMode.value) {
    fetchKLine()
  }
})

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  disconnectWebSocket()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="stock-detail">
    <!-- 股票信息头部 -->
    <el-card class="stock-header">
      <div class="header-main">
        <div class="stock-info">
          <h1 class="stock-name">{{ stockName }}</h1>
          <span class="stock-code">{{ stockCode }}</span>
        </div>
        <div class="stock-price" v-if="latestData()">
          <span class="current-price" :class="priceChange().class">
            {{ latestData()?.close.toFixed(2) }}
          </span>
          <span class="price-change" :class="priceChange().class">
            {{ priceChange().value }} ({{ priceChange().percent }}%)
          </span>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          :type="isInWatchlist ? 'warning' : 'default'"
          :icon="isInWatchlist ? StarFilled : Star"
          @click="addToWatchlist"
        >
          {{ isInWatchlist ? '已关注' : '加自选' }}
        </el-button>
      </div>
    </el-card>

    <!-- K线图 -->
    <el-card class="chart-card" v-loading="loading">
      <template #header>
        <div class="chart-header">
          <span>{{ isMinuteMode ? '分时图' : 'K线图' }}</span>
          <div class="chart-controls">
            <span v-if="lastRefreshTimeText" class="refresh-time">
              更新: {{ lastRefreshTimeText }}
            </span>
            <!-- 数据范围选择：分时模式不显示 -->
            <el-select v-if="!isMinuteMode" v-model="dataRange" size="small" style="width: 100px" @change="onDataRangeChange">
              <el-option
                v-for="opt in dataRangeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <!-- 复权类型选择：分时模式不显示 -->
            <el-select v-if="!isMinuteMode" v-model="adjust" size="small" style="width: 100px">
              <el-option
                v-for="opt in adjustOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-button :icon="RefreshRight" size="small" @click="() => fetchData()">
              刷新
            </el-button>
            <!-- WebSocket 状态：仅分时模式显示 -->
            <span v-if="isMinuteMode" class="ws-status" :class="{ connected: wsConnected }">
              <span class="status-dot"></span>
              {{ wsConnected ? '实时' : '离线' }}
            </span>
          </div>
        </div>
      </template>
      <KLineChart
        :data="klineData"
        :stock-name="stockName"
        :period="period"
        :indicator-data="indicatorData"
        @period-change="onPeriodChange"
        @indicator-change="onIndicatorChange"
      />
    </el-card>
  </div>
</template>

<style scoped>
.stock-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-main {
  display: flex;
  align-items: baseline;
  gap: 32px;
}

.stock-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.stock-name {
  margin: 0;
  font-size: 24px;
}

.stock-code {
  color: #909399;
  font-size: 14px;
}

.stock-price {
  display: flex;
  flex-direction: column;
}

.current-price {
  font-size: 28px;
  font-weight: bold;
}

.price-change {
  font-size: 14px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.refresh-time {
  font-size: 12px;
  color: #909399;
}

.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f5f5f5;
}

.ws-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}

.ws-status.connected .status-dot {
  background: #52c41a;
  box-shadow: 0 0 6px rgba(82, 196, 26, 0.6);
}

.ws-status.connected {
  color: #52c41a;
  background: #f6ffed;
}
</style>

