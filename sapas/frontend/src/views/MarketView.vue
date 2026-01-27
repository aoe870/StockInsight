<template>
  <div class="market-view">
    <el-card class="page-header">
      <h2>行情中心</h2>
      <p>实时股票行情与市场数据</p>
    </el-card>

    <div class="market-content">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>市场概览</span>
                <el-button-group>
                  <el-button :type="marketTab === 'index' ? 'primary' : ''" @click="marketTab = 'index'">指数</el-button>
                  <el-button :type="marketTab === 'sector' ? 'primary' : ''" @click="marketTab = 'sector'">板块</el-button>
                  <el-button :type="marketTab === 'stock' ? 'primary' : ''" @click="marketTab = 'stock'">个股</el-button>
                </el-button-group>
              </div>
            </template>

            <!-- 指数行情 -->
            <div v-if="marketTab === 'index'" class="index-board">
              <el-row :gutter="16">
                <el-col :span="8" v-for="item in indexList" :key="item.code">
                  <div class="index-card" :class="item.change >= 0 ? 'up' : 'down'">
                    <div class="index-name">{{ item.name }}</div>
                    <div class="index-price">{{ item.price }}</div>
                    <div class="index-change">
                      {{ item.change >= 0 ? '+' : '' }}{{ item.change.toFixed(2) }}
                      ({{ item.changePct >= 0 ? '+' : '' }}{{ item.changePct.toFixed(2) }}%)
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <!-- 板块行情 -->
            <div v-if="marketTab === 'sector'" class="sector-board">
              <el-tabs v-model="sectorTab" type="border-card">
                <el-tab-pane label="行业板块" name="industry">
                  <el-table :data="industrySectors" style="width: 100%">
                    <el-table-column prop="name" label="板块名称" />
                    <el-table-column prop="stockCount" label="股票数" width="100" align="right" />
                    <el-table-column prop="amount" label="成交额" width="150" align="right">
                      <template #default="{ row }">
                        {{ formatAmount(row.amount) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="changePct" label="涨跌幅" width="120" align="right">
                      <template #default="{ row }">
                        <span :class="getPriceColorClass(row.changePct)">
                          {{ formatPercent(row.changePct) }}
                        </span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
                <el-tab-pane label="概念板块" name="concept">
                  <el-table :data="conceptSectors" style="width: 100%">
                    <el-table-column prop="name" label="板块名称" />
                    <el-table-column prop="stockCount" label="股票数" width="100" align="right" />
                    <el-table-column prop="amount" label="成交额" width="150" align="right">
                      <template #default="{ row }">
                        {{ formatAmount(row.amount) }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="changePct" label="涨跌幅" width="120" align="right">
                      <template #default="{ row }">
                        <span :class="getPriceColorClass(row.changePct)">
                          {{ formatPercent(row.changePct) }}
                        </span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
              </el-tabs>
            </div>

            <!-- 个股行情 -->
            <div v-if="marketTab === 'stock'" class="stock-board">
              <div class="search-bar">
                <el-input
                  v-model="searchKeyword"
                  placeholder="搜索股票代码或名称"
                  @keyup.enter="handleSearch"
                >
                  <template #append>
                    <el-button :icon="Search" @click="handleSearch" />
                  </template>
                </el-input>
              </div>
              <el-table :data="stockList" style="width: 100%" v-loading="loading">
                <el-table-column prop="code" label="代码" width="100" />
                <el-table-column prop="name" label="名称" width="120" />
                <el-table-column prop="price" label="现价" width="100" align="right">
                  <template #default="{ row }">
                    <span :class="getPriceColorClass(row.changePct)">
                      {{ row.price.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="changePct" label="涨跌幅" width="100" align="right">
                  <template #default="{ row }">
                    <span :class="getPriceColorClass(row.changePct)">
                      {{ formatPercent(row.changePct) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="volume" label="成交量(手)" width="120" align="right">
                  <template #default="{ row }">
                    {{ formatNumber(row.volume / 100, 0) }}
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="成交额" width="150" align="right">
                  <template #default="{ row }">
                    {{ formatAmount(row.amount) }}
                  </template>
                </el-table-column>
                <el-table-column prop="peTtm" label="市盈率" width="100" align="right" />
                <el-table-column label="操作" width="100" align="center">
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
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatNumber, formatPercent, formatAmount, getPriceColorClass } from '@/utils'

const router = useRouter()

const marketTab = ref('index')
const sectorTab = ref('industry')
const searchKeyword = ref('')
const loading = ref(false)

const indexList = ref([
  { code: '000001', name: '上证指数', price: 3050.23, change: 15.32, changePct: 0.50 },
  { code: '399001', name: '深证成指', price: 9850.67, change: -25.43, changePct: -0.26 },
  { code: '399006', name: '创业板指', price: 1950.89, change: 8.76, changePct: 0.45 }
])

const industrySectors = ref([])
const conceptSectors = ref([])
const stockList = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

onMounted(() => {
  loadSectors()
  loadStocks()
})

async function loadSectors() {
  try {
    const [industry, concept] = await Promise.all([
      api.getIndustrySectors(),
      api.getConceptSectors()
    ])
    industrySectors.value = industry.data || []
    conceptSectors.value = concept.data || []
  } catch (error) {
    console.error('加载板块数据失败', error)
  }
}

async function loadStocks() {
  loading.value = true
  try {
    const result = await api.getStockList('cn_a', pagination.pageSize, (pagination.page - 1) * pagination.pageSize)
    stockList.value = result.data || []
    pagination.total = result.total || 0
  } catch (error) {
    ElMessage.error('加载股票列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  if (!searchKeyword.value) {
    loadStocks()
    return
  }

  loading.value = true
  api.searchStocks(searchKeyword.value, 'cn_a', 50)
    .then(result => {
      stockList.value = result.data || []
      pagination.total = result.data?.length || 0
      pagination.page = 1
    })
    .catch(() => ElMessage.error('搜索失败'))
    .finally(() => loading.value = false)
}

function handleSizeChange() {
  loadStocks()
}

function handlePageChange() {
  loadStocks()
}

function viewDetail(code: string) {
  router.push(`/stock/${code}`)
}
</script>

<style scoped lang="scss">
.market-view {
  .page-header {
    margin-bottom: 20px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 500;
    }

    p {
      margin: 0;
      color: #909399;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .index-board {
    padding: 20px 0;

    .index-card {
      padding: 20px;
      border-radius: 8px;
      text-align: center;
      background: #f5f7fa;
      transition: all 0.3s;
      cursor: pointer;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      }

      &.up {
        .index-price {
          color: #f56c6c;
        }

        .index-change {
          color: #f56c6c;
        }
      }

      &.down {
        .index-price {
          color: #67c23a;
        }

        .index-change {
          color: #67c23a;
        }
      }

      .index-name {
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 12px;
      }

      .index-price {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 8px;
      }

      .index-change {
        font-size: 14px;
      }
    }
  }

  .search-bar {
    margin-bottom: 20px;
  }
}
</style>
