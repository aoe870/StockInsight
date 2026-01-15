<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { watchlistApi, stockApi, type WatchlistItem, type Stock, type StockQuote } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Search, CaretTop, CaretBottom } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const watchlist = ref<WatchlistItem[]>([])
const dialogVisible = ref(false)
const searchKeyword = ref('')
const searchResults = ref<Stock[]>([])
const searching = ref(false)

// 实时行情数据
const quoteMap = ref<Map<string, StockQuote>>(new Map())
const quoteLoading = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const fetchWatchlist = async () => {
  loading.value = true
  try {
    watchlist.value = await watchlistApi.getList()
    // 获取行情
    await fetchQuotes()
  } catch (error) {
    console.error('获取自选股失败:', error)
    ElMessage.error('获取自选股失败')
  } finally {
    loading.value = false
  }
}

// 获取实时行情
const fetchQuotes = async () => {
  if (watchlist.value.length === 0) return

  quoteLoading.value = true
  try {
    const codes = watchlist.value.map(item => item.stock_code)
    const res = await stockApi.getBatchQuote(codes)
    const newMap = new Map<string, StockQuote>()
    res.items.forEach(q => newMap.set(q.code, q))
    quoteMap.value = newMap
  } catch (error) {
    console.error('获取行情失败:', error)
  } finally {
    quoteLoading.value = false
  }
}

// 获取股票行情
const getQuote = (code: string) => quoteMap.value.get(code)

// 格式化涨跌颜色
const getPriceClass = (change: number) => {
  if (change > 0) return 'price-up'
  if (change < 0) return 'price-down'
  return 'price-flat'
}

// 自动刷新控制
const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = setInterval(fetchQuotes, 30000) // 30秒刷新
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 页面可见性控制
const handleVisibilityChange = () => {
  if (document.hidden) {
    stopAutoRefresh()
  } else {
    fetchQuotes()
    startAutoRefresh()
  }
}

const searchStock = async () => {
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }
  searching.value = true
  try {
    searchResults.value = await stockApi.search(searchKeyword.value)
  } catch (error) {
    console.error('搜索失败:', error)
  } finally {
    searching.value = false
  }
}

const addStock = async (stock: Stock) => {
  try {
    await watchlistApi.add({ stock_code: stock.code })
    ElMessage.success(`已添加 ${stock.name}`)
    dialogVisible.value = false
    searchKeyword.value = ''
    searchResults.value = []
    fetchWatchlist()
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

const removeStock = async (item: WatchlistItem) => {
  try {
    await ElMessageBox.confirm(`确定删除 ${item.stock_name} 吗？`, '确认删除', {
      type: 'warning',
    })
    await watchlistApi.remove(item.id)
    ElMessage.success('已删除')
    fetchWatchlist()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const goToDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

onMounted(() => {
  fetchWatchlist()
  startAutoRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopAutoRefresh()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="watchlist-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>自选股列表</span>
          <el-button type="primary" :icon="Plus" @click="dialogVisible = true">
            添加股票
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="watchlist"
        style="width: 100%"
        @row-click="(row: WatchlistItem) => goToDetail(row.stock_code)"
        row-class-name="stock-row"
      >
        <el-table-column prop="stock_code" label="代码" width="100" />
        <el-table-column prop="stock_name" label="名称" width="120" />
        <el-table-column label="最新价" width="100" align="right">
          <template #default="{ row }">
            <span :class="getPriceClass(getQuote(row.stock_code)?.change || 0)">
              {{ getQuote(row.stock_code)?.current?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="120" align="right">
          <template #default="{ row }">
            <span
              v-if="getQuote(row.stock_code)"
              :class="getPriceClass(getQuote(row.stock_code)?.change || 0)"
              class="change-cell"
            >
              <el-icon v-if="(getQuote(row.stock_code)?.change || 0) > 0"><CaretTop /></el-icon>
              <el-icon v-else-if="(getQuote(row.stock_code)?.change || 0) < 0"><CaretBottom /></el-icon>
              {{ (getQuote(row.stock_code)?.change_pct || 0) >= 0 ? '+' : '' }}{{ getQuote(row.stock_code)?.change_pct?.toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="100" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button
              type="danger"
              :icon="Delete"
              circle
              size="small"
              @click.stop="removeStock(row)"
            />
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && watchlist.length === 0" description="暂无自选股" />
    </el-card>

    <!-- 添加股票对话框 -->
    <el-dialog v-model="dialogVisible" title="添加自选股" width="500px">
      <el-input
        v-model="searchKeyword"
        placeholder="输入股票代码或名称搜索"
        :prefix-icon="Search"
        @input="searchStock"
      />
      
      <el-table
        v-loading="searching"
        :data="searchResults"
        style="margin-top: 16px"
        max-height="300"
      >
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="addStock(row)">
              添加
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-row {
  cursor: pointer;
}

.stock-row:hover {
  background-color: #f5f7fa;
}

.price-up {
  color: #ec0000;
}

.price-down {
  color: #00da3c;
}

.price-flat {
  color: #666;
}

.change-cell {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
</style>

