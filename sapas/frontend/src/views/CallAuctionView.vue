<template>
  <div class="call-auction-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>集合竞价</span>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            placeholder="选择日期"
            :clearable="false"
            @change="handleDateChange"
          />
        </div>
      </template>

      <div class="auction-content">
        <!-- 竞价统计 -->
        <el-row :gutter="20" class="auction-stats">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">竞价涨停</div>
              <div class="stat-value text-red">{{ auctionStats.limitUp || '-' }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">竞价跌停</div>
              <div class="stat-value text-green">{{ auctionStats.limitDown || '-' }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">高开</div>
              <div class="stat-value text-red">{{ auctionStats.highOpen || '-' }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-label">低开</div>
              <div class="stat-value text-green">{{ auctionStats.lowOpen || '-' }}</div>
            </div>
          </el-col>
        </el-row>

        <el-divider />

        <!-- 筛选条件 -->
        <div class="filter-bar">
          <el-space>
            <el-select v-model="filterType" placeholder="筛选类型" @change="handleFilter">
              <el-option label="全部" value="all" />
              <el-option label="竞价涨停" value="limit_up" />
              <el-option label="竞价跌停" value="limit_down" />
              <el-option label="高开" value="high_open" />
              <el-option label="低开" value="low_open" />
              <el-option label="平开" value="flat_open" />
            </el-select>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索股票代码或名称"
              style="width: 200px"
              @keyup.enter="handleSearch"
            >
              <template #append>
                <el-button :icon="Search" @click="handleSearch" />
              </template>
            </el-input>
            <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
          </el-space>
        </div>

        <!-- 竞价数据表 -->
        <el-table :data="auctionData" style="width: 100%" v-loading="loading">
          <el-table-column prop="code" label="代码" width="100" fixed="left" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="auctionPrice" label="竞价价" width="100" align="right">
            <template #default="{ row }">
              <span :class="getAuctionPriceClass(row)">
                {{ row.auctionPrice?.toFixed(2) || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="auctionVolume" label="竞价量(手)" width="120" align="right">
            <template #default="{ row }">
              {{ formatNumber(row.auctionVolume || 0, 0) }}
            </template>
          </el-table-column>
          <el-table-column prop="auctionAmount" label="竞价额" width="150" align="right">
            <template #default="{ row }">
              {{ formatAmount(row.auctionAmount || 0) }}
            </template>
          </el-table-column>
          <el-table-column prop="preClose" label="昨收" width="100" align="right">
            <template #default="{ row }">
              {{ row.preClose?.toFixed(2) || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="openPct" label="开盘涨幅" width="100" align="right">
            <template #default="{ row }">
              <span :class="getPriceColorClass(row.openPct)">
                {{ formatPercent(row.openPct) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="matchedVolume" label="匹配量(手)" width="120" align="right">
            <template #default="{ row }">
              {{ formatNumber(row.matchedVolume || 0, 0) }}
            </template>
          </el-table-column>
          <el-table-column prop="buyOrders" label="买盘(手)" width="100" align="right">
            <template #default="{ row }">
              {{ formatNumber(row.buyOrders || 0, 0) }}
            </template>
          </el-table-column>
          <el-table-column prop="sellOrders" label="卖盘(手)" width="100" align="right">
            <template #default="{ row }">
              {{ formatNumber(row.sellOrders || 0, 0) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewDetail(row.code)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          style="margin-top: 20px; justify-content: center"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />

        <el-empty v-if="!loading && auctionData.length === 0" description="暂无竞价数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatNumber, formatPercent, formatAmount, getPriceColorClass } from '@/utils'

const router = useRouter()

const selectedDate = ref(new Date())
const filterType = ref('all')
const searchKeyword = ref('')
const loading = ref(false)

const auctionStats = ref({
  limitUp: 0,
  limitDown: 0,
  highOpen: 0,
  lowOpen: 0
})

const auctionData = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadAuctionData()
})

function handleDateChange() {
  loadAuctionData()
}

function handleFilter() {
  pagination.page = 1
  loadAuctionData()
}

function handleSearch() {
  pagination.page = 1
  loadAuctionData()
}

function refreshData() {
  loadAuctionData()
  ElMessage.success('已刷新')
}

async function loadAuctionData() {
  loading.value = true
  try {
    const dateStr = selectedDate.value.toISOString().split('T')[0]
    const params: any = {
      date: dateStr,
      page: pagination.page,
      page_size: pagination.pageSize
    }

    if (filterType.value !== 'all') {
      params.filter_type = filterType.value
    }

    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }

    // 这里假设有一个集合竞价的API端点
    // const result = await api.getCallAuctionData(params)

    // 模拟数据
    const mockData = generateMockData()
    auctionData.value = mockData.list
    auctionStats.value = mockData.stats
    pagination.total = mockData.total
  } catch (error) {
    ElMessage.error('加载竞价数据失败')
  } finally {
    loading.value = false
  }
}

function handleSizeChange() {
  loadAuctionData()
}

function handlePageChange() {
  loadAuctionData()
}

function viewDetail(code: string) {
  router.push(`/stock/${code}`)
}

function getAuctionPriceClass(row: any): string {
  if (!row.auctionPrice || !row.preClose) return ''
  if (row.auctionPrice > row.preClose) return 'text-red'
  if (row.auctionPrice < row.preClose) return 'text-green'
  return 'text-gray'
}

// 生成模拟数据
function generateMockData() {
  const list = []
  let limitUp = 0
  let limitDown = 0
  let highOpen = 0
  let lowOpen = 0

  for (let i = 0; i < 20; i++) {
    const code = (i + 1).toString().padStart(6, '0')
    const preClose = 10 + Math.random() * 90
    const limitPrice = preClose * 1.1
    const floorPrice = preClose * 0.9

    let auctionPrice, openPct

    if (i < 3) {
      // 竞价涨停
      auctionPrice = limitPrice
      openPct = 10
      limitUp++
    } else if (i < 6) {
      // 竞价跌停
      auctionPrice = floorPrice
      openPct = -10
      limitDown++
    } else if (i < 12) {
      // 高开
      auctionPrice = preClose * (1 + Math.random() * 0.09)
      openPct = (auctionPrice / preClose - 1) * 100
      highOpen++
    } else {
      // 低开
      auctionPrice = preClose * (1 - Math.random() * 0.09)
      openPct = (auctionPrice / preClose - 1) * 100
      lowOpen++
    }

    list.push({
      code,
      name: `股票${code}`,
      auctionPrice,
      auctionVolume: Math.floor(Math.random() * 100000),
      auctionAmount: auctionPrice * Math.floor(Math.random() * 100000) * 100,
      preClose,
      openPct,
      matchedVolume: Math.floor(Math.random() * 50000),
      buyOrders: Math.floor(Math.random() * 50000),
      sellOrders: Math.floor(Math.random() * 50000)
    })
  }

  return {
    list,
    stats: { limitUp, limitDown, highOpen, lowOpen },
    total: 100
  }
}
</script>

<style scoped lang="scss">
.call-auction-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .auction-stats {
    margin-bottom: 20px;

    .stat-card {
      text-align: center;
      padding: 20px;
      background: #f5f7fa;
      border-radius: 8px;

      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }
    }
  }

  .filter-bar {
    margin-bottom: 20px;
  }
}
</style>
