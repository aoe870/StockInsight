<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { stockApi, watchlistApi, type KLineData } from '@/api'
import { ElMessage } from 'element-plus'
import { Star, StarFilled, RefreshRight } from '@element-plus/icons-vue'
import KLineChart from '@/components/KLineChart.vue'

const route = useRoute()
const loading = ref(false)
const stockCode = ref('')
const stockName = ref('')
const klineData = ref<KLineData[]>([])
const indicatorData = ref<Record<string, any>[]>([])
const adjust = ref('qfq') // 默认使用前复权（与 sync_all_klines.py 同步的数据一致）
const period = ref('daily')
const selectedIndicators = ref(['MA', 'VOL', 'MACD'])
const isInWatchlist = ref(false)

// 自动刷新控制
const autoRefresh = ref(true)
const refreshInterval = ref(60) // 秒
const lastRefreshTime = ref<Date | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

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

// 获取 K 线和指标数据
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

// 静默刷新（不显示loading）
const silentRefresh = () => {
  fetchKLine(false)
}

// 启动自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh()
  if (autoRefresh.value) {
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

// 切换自动刷新
const toggleAutoRefresh = () => {
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
  } else if (autoRefresh.value) {
    silentRefresh() // 页面恢复时立即刷新一次
    startAutoRefresh()
  }
}

// 格式化刷新时间
const lastRefreshTimeText = computed(() => {
  if (!lastRefreshTime.value) return ''
  return lastRefreshTime.value.toLocaleTimeString()
})

// 获取指标数据
const fetchIndicators = async () => {
  if (!stockCode.value || selectedIndicators.value.length === 0) {
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
  fetchKLine()
}

// 周期变化
const onPeriodChange = async (newPeriod: string) => {
  period.value = newPeriod
  await fetchKLine()
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
    fetchKLine()
    startAutoRefresh()
  }
}, { immediate: true })

watch(adjust, () => fetchKLine())

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
          <span>K线图</span>
          <div class="chart-controls">
            <span v-if="lastRefreshTimeText" class="refresh-time">
              更新: {{ lastRefreshTimeText }}
            </span>
            <el-select v-model="dataRange" size="small" style="width: 100px" @change="onDataRangeChange">
              <el-option
                v-for="opt in dataRangeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-select v-model="adjust" size="small" style="width: 100px">
              <el-option
                v-for="opt in adjustOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-button :icon="RefreshRight" size="small" @click="() => fetchKLine()">
              刷新
            </el-button>
            <el-button
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

