<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { stockApi, indexApi, type Stock, type IndexQuote } from '@/api'
import { Search, Star, CaretTop, CaretBottom } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const searchKeyword = ref('')
const stocks = ref<Stock[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 大盘指数数据
const indexQuotes = ref<IndexQuote[]>([])
const indexLoading = ref(false)
const lastUpdateTime = ref('')
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 计算市场总成交额（只统计上证指数和深证成指）
const totalMarketAmount = computed(() => {
  return indexQuotes.value
    .filter(item => item.code === 'sh000001' || item.code === 'sz399001')
    .reduce((sum, item) => sum + (item.amount || 0), 0)
})

// 获取指数行情（HTTP 轮询）
const fetchIndexQuotes = async () => {
  try {
    const res = await indexApi.getRealtime()
    indexQuotes.value = res.items || []
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('获取指数行情失败:', error)
  } finally {
    indexLoading.value = false
  }
}

// 启动自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh()
  // 每 10 秒刷新一次
  refreshTimer = setInterval(fetchIndexQuotes, 10000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

const fetchStocks = async () => {
  loading.value = true
  try {
    const res = await stockApi.getList({
      keyword: searchKeyword.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    stocks.value = res.items
    total.value = res.total
  } catch (error) {
    console.error('获取股票列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchStocks()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchStocks()
}

const goToDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

const formatNumber = (num: number) => {
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(2) + '万'
  return num.toFixed(2)
}

const handleVisibilityChange = () => {
  if (document.hidden) {
    stopAutoRefresh()
  } else {
    fetchIndexQuotes()
    startAutoRefresh()
  }
}

onMounted(async () => {
  indexLoading.value = true
  await fetchIndexQuotes()
  await fetchStocks()
  startAutoRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopAutoRefresh()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="market-view">
    <!-- 大盘指数 -->
    <div class="index-header">
      <span class="index-title">大盘指数</span>
      <span v-if="totalMarketAmount > 0" class="total-amount">
        市场总成交: <strong>{{ formatNumber(totalMarketAmount) }}</strong>
      </span>
      <span v-if="lastUpdateTime" class="update-time">更新: {{ lastUpdateTime }}</span>
    </div>
    <div class="index-bar" v-loading="indexLoading">
      <template v-if="indexQuotes.length > 0">
        <div
          v-for="item in indexQuotes"
          :key="item.code"
          class="index-item"
          :class="{ up: item.change >= 0, down: item.change < 0 }"
        >
          <div class="index-name">{{ item.name }}</div>
          <div class="index-price">{{ item.current?.toFixed(2) }}</div>
          <div class="index-change">
            <el-icon v-if="item.change >= 0"><CaretTop /></el-icon>
            <el-icon v-else><CaretBottom /></el-icon>
            <span>{{ item.change >= 0 ? '+' : '' }}{{ item.change?.toFixed(2) }}</span>
            <span class="pct">({{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct?.toFixed(2) }}%)</span>
          </div>
          <div class="index-vol">成交 {{ formatNumber(item.amount || 0) }}</div>
        </div>
      </template>
      <div v-else-if="!indexLoading" class="index-empty">
        <span>暂无指数数据，请检查后端服务</span>
      </div>
    </div>

    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索股票代码或名称"
        :prefix-icon="Search"
        clearable
        @keyup.enter="handleSearch"
        @clear="handleSearch"
        style="width: 300px"
      />
      <el-button type="primary" @click="handleSearch" style="margin-left: 12px">
        搜索
      </el-button>
    </el-card>

    <!-- 股票列表 -->
    <el-card class="stock-list-card">
      <el-table
        v-loading="loading"
        :data="stocks"
        style="width: 100%"
        @row-click="(row: Stock) => goToDetail(row.code)"
        row-class-name="stock-row"
      >
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="market" label="市场" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.market === 'SH' ? 'danger' : 'primary'">
              {{ row.market }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" />
        <el-table-column label="操作" width="100" align="center">
          <template #default>
            <el-button
              type="primary"
              :icon="Star"
              circle
              size="small"
              @click.stop="() => {}"
            />
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.market-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 大盘指数头部 */
.index-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: -8px;
}

.index-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.update-time {
  font-size: 12px;
  color: #999;
}

.total-amount {
  font-size: 14px;
  color: #666;
  margin-right: auto;
  padding-left: 20px;
}

.total-amount strong {
  color: #409eff;
  font-size: 15px;
}

/* 大盘指数栏 */
.index-bar {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
  min-height: 90px;
}

.index-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  color: #999;
  font-size: 14px;
}

.index-item {
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  min-width: 140px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  border-left: 3px solid #ccc;
  transition: all 0.2s;
}

.index-item:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.index-item.up {
  border-left-color: #ec0000;
}

.index-item.down {
  border-left-color: #00da3c;
}

.index-name {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.index-price {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.index-item.up .index-price,
.index-item.up .index-change {
  color: #ec0000;
}

.index-item.down .index-price,
.index-item.down .index-change {
  color: #00da3c;
}

.index-change {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 2px;
}

.index-change .pct {
  margin-left: 4px;
}

.index-vol {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.search-card {
  display: flex;
  align-items: center;
}

.stock-list-card {
  flex: 1;
}

.stock-row {
  cursor: pointer;
}

.stock-row:hover {
  background-color: #f5f7fa;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

