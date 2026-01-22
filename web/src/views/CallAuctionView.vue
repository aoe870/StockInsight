<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElDatePicker, ElButton, ElTable, ElTableColumn, ElTag, ElStatistic, ElRow, ElCol, ElEmpty, ElAlert } from 'element-plus'
import { callAuctionApi, type CallAuctionData, type CallAuctionStats } from '@/api/callAuction'

// 数据状态
const loading = ref(false)
const syncing = ref(false)
const auctionData = ref<CallAuctionData[]>([])
const stats = ref<CallAuctionStats | null>(null)
const displayDate = ref('') // 显示当前查询的日期

// 自动刷新
const autoRefresh = ref(true)
const refreshInterval = ref<NodeJS.Timeout | null>(null)

// 判断应该查询哪天的数据
const getQueryDate = (): { date: string, isToday: boolean, hint: string } => {
  const now = new Date()
  const hour = now.getHours()
  const minute = now.getMinutes()
  const currentTime = hour * 60 + minute

  // 9:15 = 9*60 + 15 = 555 分钟
  // 12:00 = 12*60 = 720 分钟
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  const todayStr = formatDate(today)
  const yesterdayStr = formatDate(yesterday)

  // 0:00-9:15: 查询前一天的数据
  if (currentTime < 9 * 60 + 15) {
    return {
      date: yesterdayStr,
      isToday: false,
      hint: `当前显示 ${yesterdayStr} 集合竞价数据（今日未开盘）`
    }
  }

  // 9:15-12:00: 查询今天的数据
  return {
    date: todayStr,
    isToday: true,
    hint: `当前显示 ${todayStr} 集合竞价数据`
  }
}

// 统计数据计算
const riseRate = computed(() => {
  if (!stats.value || stats.value.total_count === 0) return 0
  return ((stats.value.rise_count / stats.value.total_count) * 100).toFixed(2)
})

const limitUpRate = computed(() => {
  if (!stats.value || stats.value.total_count === 0) return 0
  return ((stats.value.limit_up_count / stats.value.total_count) * 100).toFixed(2)
})

// 获取集合竞价数据
const fetchAuctionData = async () => {
  loading.value = true
  try {
    // 根据时间判断应该查询哪天的数据
    const { date: queryDate, hint } = getQueryDate()
    displayDate.value = hint

    // 获取指定日期的数据
    const data = await callAuctionApi.getRealtime(queryDate)
    auctionData.value = data

    // 获取统计数据
    try {
      stats.value = await callAuctionApi.getStats(queryDate)
    } catch (error) {
      // 统计数据可能不存在
      stats.value = null
    }
  } catch (error: any) {
    // 如果查询失败，清空数据
    auctionData.value = []
    stats.value = null
    // 不显示错误消息，只记录日志
    console.error('获取集合竞价数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 同步集合竞价数据
const handleSync = async () => {
  syncing.value = true
  try {
    const result = await callAuctionApi.syncRealtime()
    ElMessage.success(result.message || '同步成功')
    await fetchAuctionData()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '同步失败')
  } finally {
    syncing.value = false
  }
}

// 格式化日期
const formatDate = (date: Date) => {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 格式化数字
const formatNumber = (num: number | null, decimals: number = 2) => {
  if (num === null || num === undefined) return '-'
  return num.toFixed(decimals)
}

// 格式化金额
const formatAmount = (amount: number | null) => {
  if (amount === null || amount === undefined) return '-'
  if (amount >= 100000000) {
    return (amount / 100000000).toFixed(2) + '亿'
  } else if (amount >= 10000) {
    return (amount / 10000).toFixed(2) + '万'
  }
  return amount.toFixed(2)
}

// 格式化成交量
const formatVolume = (volume: number | null) => {
  if (volume === null || volume === undefined) return '-'
  if (volume >= 100000000) {
    return (volume / 100000000).toFixed(2) + '亿'
  } else if (volume >= 10000) {
    return (volume / 10000).toFixed(2) + '万'
  }
  return volume.toString()
}

// 获取涨跌标签类型
const getChangeType = (changePct: number | null) => {
  if (changePct === null || changePct === undefined) return 'info'
  if (changePct > 0) return 'danger'
  if (changePct < 0) return 'success'
  return 'info'
}

// 获取涨跌文本
const getChangeText = (changePct: number | null) => {
  if (changePct === null || changePct === undefined) return '-'
  const sign = changePct > 0 ? '+' : ''
  return `${sign}${changePct.toFixed(2)}%`
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

// 开启自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshInterval.value = setInterval(() => {
    fetchAuctionData()
  }, 30000) // 30秒刷新一次
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

onMounted(() => {
  fetchAuctionData()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div class="call-auction-view">
    <div class="header">
      <h1>集合竞价分析</h1>
      <div class="actions">
        <ElButton @click="toggleAutoRefresh" :type="autoRefresh ? 'success' : 'info'">
          {{ autoRefresh ? '自动刷新中' : '开启自动刷新' }}
        </ElButton>
        <ElButton type="primary" @click="handleSync" :loading="syncing">
          同步数据
        </ElButton>
        <ElButton @click="fetchAuctionData" :loading="loading">
          刷新
        </ElButton>
      </div>
    </div>

    <!-- 数据提示 -->
    <ElAlert v-if="displayDate" type="info" :closable="false" style="margin-bottom: 20px">
      {{ displayDate }}
    </ElAlert>

    <!-- 空状态提示 -->
    <ElEmpty
      v-if="!loading && auctionData.length === 0"
      description="暂无集合竞价数据"
      style="margin: 60px 0"
    >
      <template #image>
        <span style="font-size: 60px">📊</span>
      </template>
      <template #extra>
        <div style="text-align: left; padding: 20px; background: #f9f9f9; border-radius: 8px;">
          <p style="margin: 0 0 10px 0; font-weight: 600;">数据说明：</p>
          <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
            <li>0:00-9:15：显示前一天的集合竞价数据</li>
            <li>9:15-9:25：实时获取当日集合竞价数据</li>
            <li>9:25 之后：显示当日已确定的集合竞价数据</li>
            <li>集合竞价数据需先同步才能查看（点击"同步数据"按钮）</li>
            <li>非交易日不会有集合竞价数据</li>
          </ul>
        </div>
      </template>
    </ElEmpty>

    <!-- 统计数据和表格（只在有数据时显示） -->
    <template v-if="auctionData.length > 0">
      <!-- 统计数据 -->
      <div v-if="stats" class="stats-section">
      <div class="section-title">市场概况</div>
      <ElRow :gutter="20">
        <ElCol :span="6">
          <div class="stat-card">
            <div class="stat-label">总数量</div>
            <div class="stat-value">{{ stats.total_count }}</div>
          </div>
        </ElCol>
        <ElCol :span="6">
          <div class="stat-card rise">
            <div class="stat-label">上涨数量</div>
            <div class="stat-value">{{ stats.rise_count }}</div>
            <div class="stat-sub">占比: {{ riseRate }}%</div>
          </div>
        </ElCol>
        <ElCol :span="6">
          <div class="stat-card fall">
            <div class="stat-label">下跌数量</div>
            <div class="stat-value">{{ stats.fall_count }}</div>
          </div>
        </ElCol>
        <ElCol :span="6">
          <div class="stat-card limit-up">
            <div class="stat-label">涨停数量</div>
            <div class="stat-value">{{ stats.limit_up_count }}</div>
            <div class="stat-sub">占比: {{ limitUpRate }}%</div>
          </div>
        </ElCol>
      </ElRow>
      <ElRow :gutter="20" style="margin-top: 20px">
        <ElCol :span="8">
          <div class="stat-card">
            <div class="stat-label">总成交量</div>
            <div class="stat-value">{{ formatVolume(stats.total_volume) }}</div>
          </div>
        </ElCol>
        <ElCol :span="8">
          <div class="stat-card">
            <div class="stat-label">总成交额</div>
            <div class="stat-value">{{ formatAmount(stats.total_amount) }}</div>
          </div>
        </ElCol>
        <ElCol :span="8">
          <div class="stat-card">
            <div class="stat-label">平均价格</div>
            <div class="stat-value">{{ formatNumber(stats.avg_price, 2) }}</div>
          </div>
        </ElCol>
      </ElRow>
    </div>

    <!-- 集合竞价数据表格 -->
    <div class="table-section">
      <div class="section-title">
        <span>竞价数据</span>
        <span v-if="autoRefresh" class="refresh-hint">(每30秒自动刷新)</span>
      </div>

      <ElTable :data="auctionData" v-loading="loading" stripe>
        <ElTableColumn prop="code" label="代码" width="100" />
        <ElTableColumn prop="name" label="名称" width="120" />
        <ElTableColumn label="竞价时间" width="100">
          <template #default="{ row }">
            {{ row.auction_time }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="价格" width="100">
          <template #default="{ row }">
            <span :class="{ 'price-up': row.change_pct > 0, 'price-down': row.change_pct < 0 }">
              {{ formatNumber(row.price, 2) }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="涨跌幅" width="100">
          <template #default="{ row }">
            <ElTag :type="getChangeType(row.change_pct)">
              {{ getChangeText(row.change_pct) }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="成交量" width="120">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="成交额" width="120">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="买盘量" width="100">
          <template #default="{ row }">
            {{ formatVolume(row.buy_volume) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="卖盘量" width="100">
          <template #default="{ row }">
            {{ formatVolume(row.sell_volume) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="委比" width="100">
          <template #default="{ row }">
            {{ row.bid_ratio !== null ? formatNumber(row.bid_ratio, 2) + '%' : '-' }}
          </template>
        </ElTableColumn>
      </ElTable>
    </div>
    </template>
  </div>
</template>

<style scoped>
.call-auction-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.actions {
  display: flex;
  gap: 10px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.refresh-hint {
  font-size: 14px;
  color: #999;
  font-weight: normal;
}

.stats-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-card {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-card.rise {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border: 1px solid #ffcccc;
}

.stat-card.fall {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #cce5ff;
}

.stat-card.limit-up {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border: 1px solid #fed7aa;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #333;
}

.stat-sub {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

.table-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.price-up {
  color: #f56c6c;
  font-weight: 600;
}

.price-down {
  color: #67c23a;
  font-weight: 600;
}
</style>
