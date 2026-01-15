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

// 自动刷新控制 - 只在分时模式下启用
const autoRefresh = ref(false)
const refreshInterval = ref(10) // 分时数据刷新间隔（秒）
const lastRefreshTime = ref<Date | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

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

// 静默刷新（不显示loading）
const silentRefresh = () => {
  fetchData(false)
}

// 启动自动刷新（仅分时模式）
const startAutoRefresh = () => {
  stopAutoRefresh()
  if (autoRefresh.value && isMinuteMode.value) {
    refreshTimer = setInterval(silentRefresh, refreshInterval.value * 1000)
  }
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 切换自动刷新（仅分时模式有效）
const toggleAutoRefresh = () => {
  if (!isMinuteMode.value) {
    ElMessage.warning('自动刷新仅在分时模式下可用')
    return
  }
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startAutoRefresh()
    ElMessage.success('已开启自动刷新')
  } else {
    stopAutoRefresh()
    ElMessage.info('已关闭自动刷新')
  }
}

// 页面可见性控制
const handleVisibilityChange = () => {
  if (document.hidden) {
    stopAutoRefresh()
  } else if (autoRefresh.value && isMinuteMode.value) {
    silentRefresh() // 页面恢复时立即刷新一次
    startAutoRefresh()
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

  // 如果从分时切换到其他模式，停止自动刷新
  if (wasMinuteMode && !isMinuteMode.value) {
    autoRefresh.value = false
    stopAutoRefresh()
  }

  // 如果切换到分时模式，自动开启刷新
  if (!wasMinuteMode && isMinuteMode.value) {
    autoRefresh.value = true
  }

  // 获取数据
  await fetchData()

  // 分时模式启动自动刷新
  if (isMinuteMode.value && autoRefresh.value) {
    startAutoRefresh()
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

watch(() => route.params.code, (newCode) => {
  if (newCode) {
    stockCode.value = newCode as string
    // 初始加载时使用日K（非分时模式，不自动刷新）
    period.value = 'daily'
    autoRefresh.value = false
    fetchData()
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
  stopAutoRefresh()
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
            <!-- 自动刷新按钮：仅分时模式显示 -->
            <el-button
              v-if="isMinuteMode"
              size="small"
              :type="autoRefresh ? 'success' : 'info'"
              @click="toggleAutoRefresh"
            >
              {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
            </el-button>
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
</style>

