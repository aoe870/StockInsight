<template>
  <div class="stock-detail-view">
    <el-card class="stock-header">
      <div class="stock-info">
        <div class="stock-basic">
          <h2>{{ stockName }} <span class="stock-code">({{ stockCode }})</span></h2>
          <div class="stock-tags">
            <el-tag v-for="tag in tags" :key="tag" size="small">{{ tag }}</el-tag>
          </div>
        </div>
        <div class="stock-price" :class="priceDirection">
          <div class="current-price">{{ currentPrice }}</div>
          <div class="price-change">
            <span class="change-value">{{ changeValue }}</span>
            <span class="change-pct">({{ changePct }})</span>
          </div>
        </div>
      </div>
      <el-button type="primary" @click="addToWatchlist">加入自选</el-button>
    </el-card>

    <el-row :gutter="20">
      <!-- K线图 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>K线图</span>
              <el-radio-group v-model="period" size="small" @change="loadKline">
                <el-radio-button label="day">日线</el-radio-button>
                <el-radio-button label="week">周线</el-radio-button>
                <el-radio-button label="month">月线</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="chartRef" class="kline-chart" v-loading="klineLoading"></div>
        </el-card>
      </el-col>

      <!-- 基本信息 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>基本信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="开盘">{{ quote?.open?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最高">{{ quote?.high?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最低">{{ quote?.low?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="昨收">{{ quote?.preClose?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="涨停">{{ quote?.highLimit?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="跌停">{{ quote?.lowLimit?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="成交量">{{ formatNumber(quote?.volume || 0, 0) }}</el-descriptions-item>
            <el-descriptions-item label="成交额">{{ formatAmount(quote?.amount || 0) }}</el-descriptions-item>
            <el-descriptions-item label="换手率">{{ quote?.turnover?.toFixed(2) || '-' }}%</el-descriptions-item>
            <el-descriptions-item label="市盈率(TTM)">{{ quote?.peTtm?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="市净率">{{ quote?.pb?.toFixed(2) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="总市值">{{ formatAmount(quote?.marketValue || 0) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 资金流向 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>资金流向</span>
              <el-date-picker
                v-model="moneyFlowDate"
                type="date"
                placeholder="选择日期"
                size="small"
                @change="loadMoneyFlow"
              />
            </div>
          </template>
          <div v-if="moneyFlowData" class="money-flow">
            <el-row :gutter="16" class="money-flow-summary">
              <el-col :span="12">
                <div class="flow-item">
                  <div class="flow-label">主力净流入</div>
                  <div class="flow-value" :class="moneyFlowData.mainNetInflow >= 0 ? 'up' : 'down'">
                    {{ formatAmount(moneyFlowData.mainNetInflow) }}
                  </div>
                  <div class="flow-ratio">
                    净占比 {{ moneyFlowData.mainNetRatio.toFixed(2) }}%
                  </div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="flow-item">
                  <div class="flow-label">成交总额</div>
                  <div class="flow-value">
                    {{ formatAmount(moneyFlowData.amount) }}
                  </div>
                </div>
              </el-col>
            </el-row>
            <el-divider />
            <el-row :gutter="16">
              <el-col :span="6">
                <div class="flow-type">
                  <div class="flow-type-label">超大单</div>
                  <div class="flow-type-value" :class="moneyFlowData.superLarge.netInflow >= 0 ? 'up' : 'down'">
                    {{ formatAmount(moneyFlowData.superLarge.netInflow) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="flow-type">
                  <div class="flow-type-label">大单</div>
                  <div class="flow-type-value" :class="moneyFlowData.large.netInflow >= 0 ? 'up' : 'down'">
                    {{ formatAmount(moneyFlowData.large.netInflow) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="flow-type">
                  <div class="flow-type-label">中单</div>
                  <div class="flow-type-value" :class="moneyFlowData.medium.netInflow >= 0 ? 'up' : 'down'">
                    {{ formatAmount(moneyFlowData.medium.netInflow) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="flow-type">
                  <div class="flow-type-label">小单</div>
                  <div class="flow-type-value" :class="moneyFlowData.small.netInflow >= 0 ? 'up' : 'down'">
                    {{ formatAmount(moneyFlowData.small.netInflow) }}
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>

      <!-- 财务指标 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>财务指标</span>
          </template>
          <div v-loading="fundamentalsLoading">
            <el-descriptions v-if="fundamentals" :column="2" border>
              <el-descriptions-item label="总股本">{{ formatNumber(fundamentals.totalShares || 0, 0) }}万股</el-descriptions-item>
              <el-descriptions-item label="流通股">{{ formatNumber(fundamentals.floatShares || 0, 0) }}万股</el-descriptions-item>
              <el-descriptions-item label="每股收益">{{ fundamentals.eps?.toFixed(2) || '-' }}元</el-descriptions-item>
              <el-descriptions-item label="每股净资产">{{ fundamentals.bps?.toFixed(2) || '-' }}元</el-descriptions-item>
              <el-descriptions-item label="净资产收益率">{{ fundamentals.roe?.toFixed(2) || '-' }}%</el-descriptions-item>
              <el-descriptions-item label="毛利率">{{ fundamentals.grossMargin?.toFixed(2) || '-' }}%</el-descriptions-item>
              <el-descriptions-item label="净利润增长率">{{ fundamentals.netProfitGrowth?.toFixed(2) || '-' }}%</el-descriptions-item>
              <el-descriptions-item label="营业收入增长率">{{ fundamentals.revenueGrowth?.toFixed(2) || '-' }}%</el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="暂无数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { api } from '@/api'
import { formatNumber, formatAmount } from '@/utils'

const route = useRoute()
const stockCode = computed(() => route.params.code as string)

const chartRef = ref<HTMLElement>()
const period = ref('day')
const klineLoading = ref(false)
const fundamentalsLoading = ref(false)
const moneyFlowDate = ref(new Date())

const stockName = ref('')
const quote = ref<any>(null)
const klineData = ref<any[]>([])
const fundamentals = ref<any>(null)
const moneyFlowData = ref<any>(null)

const tags = computed(() => {
  const t = []
  if (stockCode.value.startsWith('6')) {
    t.push('沪市A股')
  } else if (stockCode.value.startsWith('0') || stockCode.value.startsWith('3')) {
    t.push('深市A股')
  }
  return t
})

const currentPrice = computed(() => quote.value?.price?.toFixed(2) || '-')
const changeValue = computed(() => {
  const change = quote.value?.change || 0
  return change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2)
})
const changePct = computed(() => {
  const pct = quote.value?.changePct || 0
  return pct >= 0 ? `+${pct.toFixed(2)}%` : `${pct.toFixed(2)}%`
})
const priceDirection = computed(() => {
  const pct = quote.value?.changePct || 0
  if (pct > 0) return 'up'
  if (pct < 0) return 'down'
  return 'flat'
})

let chart: echarts.ECharts | null = null

onMounted(async () => {
  await loadQuote()
  loadKline()
  loadFundamentals()
  loadMoneyFlow()

  await nextTick()
  initChart()
})

async function loadQuote() {
  try {
    const result = await api.getStocksQuote([stockCode.value], 'cn_a')
    if (result.data && result.data.length > 0) {
      quote.value = result.data[0]
      stockName.value = result.data[0].name || ''
    }
  } catch (error) {
    ElMessage.error('加载行情数据失败')
  }
}

async function loadKline() {
  klineLoading.value = true
  try {
    const result = await api.getStockKline(stockCode.value, 'cn_a', period.value)
    klineData.value = result.data || []
    renderChart()
  } catch (error) {
    ElMessage.error('加载K线数据失败')
  } finally {
    klineLoading.value = false
  }
}

async function loadFundamentals() {
  fundamentalsLoading.value = true
  try {
    const result = await api.getStockFundamentals(stockCode.value, 'cn_a')
    fundamentals.value = result.data
  } catch (error) {
    console.error('加载财务数据失败', error)
  } finally {
    fundamentalsLoading.value = false
  }
}

async function loadMoneyFlow() {
  try {
    const dateStr = moneyFlowDate.value.toISOString().split('T')[0]
    const result = await api.getStockMoneyFlow(stockCode.value, dateStr)
    moneyFlowData.value = result.data
  } catch (error) {
    console.error('加载资金流向数据失败', error)
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()
}

function renderChart() {
  if (!chart || !klineData.value.length) return

  const dates = klineData.value.map((item: any) => item.datetime.split(' ')[0])
  const data = klineData.value.map((item: any) => [item.open, item.close, item.low, item.high])
  const volumes = klineData.value.map((item: any) => ({
    value: item.volume,
    itemStyle: { color: item.close >= item.open ? '#f56c6c' : '#67c23a' }
  }))

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    grid: [
      { left: '10%', right: '8%', top: '10%', height: '55%' },
      { left: '10%', right: '8%', top: '75%', height: '15%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#8392A5' } }
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 1,
        axisLabel: { show: false }
      }
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitNumber: 5,
        axisLine: { lineStyle: { color: '#8392A5' } },
        splitLine: { show: true, lineStyle: { color: '#E0E6F1' } }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 },
      { show: true, xAxisIndex: [0, 1], type: 'slider', top: '90%', start: 70, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: data,
        itemStyle: {
          color: '#f56c6c',
          color0: '#67c23a',
          borderColor: '#f56c6c',
          borderColor0: '#67c23a'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes
      }
    ]
  }

  chart.setOption(option)
}

function addToWatchlist() {
  ElMessage.success('已添加到自选股')
}
</script>

<style scoped lang="scss">
.stock-detail-view {
  .stock-header {
    margin-bottom: 20px;

    .stock-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex: 1;

      .stock-basic {
        h2 {
          margin: 0 0 8px 0;
          font-size: 24px;
          font-weight: 500;

          .stock-code {
            font-size: 18px;
            color: #909399;
            font-weight: normal;
          }
        }

        .stock-tags {
          .el-tag {
            margin-right: 8px;
          }
        }
      }

      .stock-price {
        text-align: right;

        .current-price {
          font-size: 32px;
          font-weight: bold;
          line-height: 1.2;
        }

        .price-change {
          font-size: 14px;

          .change-value {
            margin-right: 8px;
          }
        }

        &.up {
          .current-price, .price-change {
            color: #f56c6c;
          }
        }

        &.down {
          .current-price, .price-change {
            color: #67c23a;
          }
        }

        &.flat {
          .current-price, .price-change {
            color: #909399;
          }
        }
      }
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .kline-chart {
    height: 400px;
  }

  .money-flow {
    .money-flow-summary {
      margin-bottom: 20px;

      .flow-item {
        text-align: center;
        padding: 16px;
        background: #f5f7fa;
        border-radius: 8px;

        .flow-label {
          font-size: 14px;
          color: #909399;
          margin-bottom: 8px;
        }

        .flow-value {
          font-size: 24px;
          font-weight: bold;
          margin-bottom: 4px;

          &.up {
            color: #f56c6c;
          }

          &.down {
            color: #67c23a;
          }
        }

        .flow-ratio {
          font-size: 12px;
          color: #909399;
        }
      }
    }

    .flow-type {
      text-align: center;
      padding: 12px;
      border-radius: 8px;
      background: #fafafa;

      .flow-type-label {
        font-size: 12px;
        color: #909399;
        margin-bottom: 4px;
      }

      .flow-type-value {
        font-size: 16px;
        font-weight: bold;

        &.up {
          color: #f56c6c;
        }

        &.down {
          color: #67c23a;
        }
      }
    }
  }
}
</style>
