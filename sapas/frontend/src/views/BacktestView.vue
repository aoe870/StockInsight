<template>
  <div class="backtest-view">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>回测配置</span>
          </template>
          <el-form :model="backtestConfig" label-width="100px">
            <el-form-item label="策略名称">
              <el-select v-model="backtestConfig.strategyName" style="width: 100%" @change="loadStrategyTemplate">
                <el-option
                  v-for="item in strategies"
                  :key="item.name"
                  :label="item.display_name || item.name"
                  :value="item.name"
                />
              </el-select>
            </el-form-item>

            <el-divider />

            <div v-if="strategyTemplate" class="strategy-params">
              <div class="section-title">策略参数</div>
              <el-form-item
                v-for="param in strategyParams"
                :key="param.name"
                :label="param.display_name || param.name"
              >
                <el-input-number
                  v-model="backtestConfig.params[param.name]"
                  :min="param.min"
                  :max="param.max"
                  :step="param.step || 1"
                  :precision="param.precision || 0"
                  style="width: 100%"
                />
              </el-form-item>
            </div>

            <el-divider />

            <el-form-item label="回测区间">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="-"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                style="width: 100%"
                @change="handleDateChange"
              />
            </el-form-item>

            <el-form-item label="初始资金">
              <el-input-number v-model="backtestConfig.initialCapital" :min="10000" :step="10000" style="width: 100%" />
            </el-form-item>

            <el-form-item label="手续费率">
              <el-input-number v-model="backtestConfig.commissionRate" :min="0" :max="0.01" :step="0.0001" :precision="4" style="width: 100%" />
              <span style="margin-left: 8px; color: #909399">（0.0001 = 万分之一）</span>
            </el-form-item>

            <el-form-item label="滑点">
              <el-input-number v-model="backtestConfig.slippage" :min="0" :max="0.01" :step="0.0001" :precision="4" style="width: 100%" />
            </el-form-item>

            <el-button type="primary" style="width: 100%" :loading="running" @click="runBacktest">
              开始回测
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>回测结果</span>
              <el-button-group>
                <el-button @click="loadBacktestRuns">历史记录</el-button>
                <el-button :disabled="!currentResult" @click="exportResult">导出报告</el-button>
              </el-button-group>
            </div>
          </template>

          <div v-if="currentResult" class="backtest-result">
            <!-- 回测统计 -->
            <div class="result-summary">
              <el-row :gutter="16">
                <el-col :span="6">
                  <div class="summary-item">
                    <div class="summary-label">初始资金</div>
                    <div class="summary-value">{{ formatAmount(currentResult.initialCapital) }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="summary-item">
                    <div class="summary-label">最终资金</div>
                    <div class="summary-value" :class="currentResult.totalReturnPct >= 0 ? 'up' : 'down'">
                      {{ formatAmount(currentResult.finalCapital) }}
                    </div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="summary-item">
                    <div class="summary-label">总收益</div>
                    <div class="summary-value" :class="currentResult.totalReturnPct >= 0 ? 'up' : 'down'">
                      {{ currentResult.totalReturnPct >= 0 ? '+' : '' }}{{ currentResult.totalReturnPct?.toFixed(2) }}%
                    </div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="summary-item">
                    <div class="summary-label">最大回撤</div>
                    <div class="summary-value down">
                      -{{ currentResult.maxDrawdownPct?.toFixed(2) }}%
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <el-divider />

            <!-- 详细指标 -->
            <el-row :gutter="16" class="detail-metrics">
              <el-col :span="8">
                <div class="metric-card">
                  <div class="metric-title">夏普比率</div>
                  <div class="metric-value">{{ currentResult.sharpeRatio?.toFixed(2) || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-card">
                  <div class="metric-title">胜率</div>
                  <div class="metric-value">{{ currentResult.winRate?.toFixed(2) || '-' }}%</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric-card">
                  <div class="metric-title">盈亏比</div>
                  <div class="metric-value">{{ currentResult.profitFactor?.toFixed(2) || '-' }}</div>
                </div>
              </el-col>
            </el-row>

            <el-row :gutter="16" class="detail-metrics" style="margin-top: 16px">
              <el-col :span="6">
                <div class="metric-card small">
                  <div class="metric-label">总交易次数</div>
                  <div class="metric-num">{{ currentResult.totalTrades || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card small">
                  <div class="metric-label">盈利交易</div>
                  <div class="metric-num">{{ currentResult.winningTrades || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card small">
                  <div class="metric-label">亏损交易</div>
                  <div class="metric-num">{{ currentResult.losingTrades || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card small">
                  <div class="metric-label">平均盈利</div>
                  <div class="metric-num">{{ currentResult.avgProfit?.toFixed(2) || '-' }}</div>
                </div>
              </el-col>
            </el-row>

            <el-divider />

            <!-- 交易记录 -->
            <div class="section-title">交易记录</div>
            <el-table :data="trades" style="width: 100%" max-height="300">
              <el-table-column prop="stockCode" label="股票代码" width="100" />
              <el-table-column prop="tradeType" label="类型" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.tradeType === 'buy' ? 'success' : 'danger'" size="small">
                    {{ row.tradeType === 'buy' ? '买入' : '卖出' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="tradeTime" label="时间" width="160">
                <template #default="{ row }">
                  {{ formatDateTime(row.tradeTime, 'YYYY-MM-DD') }}
                </template>
              </el-table-column>
              <el-table-column prop="price" label="价格" width="100" align="right" />
              <el-table-column prop="quantity" label="数量" width="100" align="right" />
              <el-table-column prop="amount" label="金额" width="120" align="right">
                <template #default="{ row }">
                  {{ formatAmount(row.amount) }}
                </template>
              </el-table-column>
              <el-table-column prop="profit" label="盈亏" width="120" align="right">
                <template #default="{ row }">
                  <span v-if="row.profit !== undefined" :class="row.profit >= 0 ? 'up' : 'down'">
                    {{ row.profit >= 0 ? '+' : '' }}{{ row.profit?.toFixed(2) }}
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-empty v-else-if="!running" description="请配置策略参数后开始回测" />
          <div v-else class="loading-container">
            <el-icon class="is-loading" :size="40"><Loading /></el-icon>
            <p>回测进行中，请稍候...</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatAmount, formatDateTime } from '@/utils'

const running = ref(false)
const strategies = ref([])
const strategyTemplate = ref<any>(null)
const currentResult = ref<any>(null)
const trades = ref([])

const dateRange = ref<[Date, Date] | null>(null)

const backtestConfig = reactive({
  strategyName: '',
  params: {} as Record<string, number>,
  startDate: '',
  endDate: '',
  initialCapital: 100000,
  commissionRate: 0.0003,
  slippage: 0.0001
})

const strategyParams = ref<any[]>([])

onMounted(() => {
  loadStrategies()
  // 设置默认日期范围
  const endDate = new Date()
  const startDate = new Date()
  startDate.setFullYear(startDate.getFullYear() - 1)
  dateRange.value = [startDate, endDate]
  handleDateChange([startDate, endDate])
})

async function loadStrategies() {
  try {
    const result = await api.getStrategies()
    strategies.value = result.data || []
    if (strategies.value.length > 0) {
      backtestConfig.strategyName = strategies.value[0].name
      loadStrategyTemplate()
    }
  } catch (error) {
    ElMessage.error('加载策略列表失败')
  }
}

async function loadStrategyTemplate() {
  if (!backtestConfig.strategyName) return

  try {
    const result = await api.getStrategyTemplate(backtestConfig.strategyName)
    strategyTemplate.value = result.data

    // 重置参数
    backtestConfig.params = {}
    strategyParams.value = result.data?.parameters || []

    // 设置默认值
    strategyParams.value.forEach(param => {
      backtestConfig.params[param.name] = param.default !== undefined ? param.default : 0
    })
  } catch (error) {
    ElMessage.error('加载策略模板失败')
  }
}

function handleDateChange(dates: [Date, Date] | null) {
  if (!dates) return
  backtestConfig.startDate = dates[0].toISOString().split('T')[0]
  backtestConfig.endDate = dates[1].toISOString().split('T')[0]
}

async function runBacktest() {
  if (!backtestConfig.strategyName) {
    ElMessage.warning('请选择策略')
    return
  }

  running.value = true
  currentResult.value = null
  trades.value = []

  try {
    const result = await api.runBacktest({
      strategy_name: backtestConfig.strategyName,
      strategy_config: backtestConfig.params,
      start_date: backtestConfig.startDate,
      end_date: backtestConfig.endDate,
      initial_capital: backtestConfig.initialCapital,
      commission_rate: backtestConfig.commissionRate,
      slippage: backtestConfig.slippage
    })

    if (result.data?.run_id) {
      // 等待回测完成
      await pollBacktestResult(result.data.run_id)
    }
  } catch (error) {
    ElMessage.error('启动回测失败')
    running.value = false
  }
}

async function pollBacktestResult(runId: number) {
  const maxAttempts = 60 // 最多等待60次（5分钟）
  let attempts = 0

  const poll = setInterval(async () => {
    attempts++
    try {
      const result = await api.getBacktestResult(runId)
      if (result.data) {
        currentResult.value = result.data
        trades.value = result.data.trades || []

        if (result.data.status === 'completed' || result.data.status === 'failed') {
          clearInterval(poll)
          running.value = false
          if (result.data.status === 'completed') {
            ElMessage.success('回测完成')
          } else {
            ElMessage.error('回测失败：' + (result.data.errorMessage || '未知错误'))
          }
        }
      }
    } catch (error) {
      clearInterval(poll)
      running.value = false
      ElMessage.error('获取回测结果失败')
    }

    if (attempts >= maxAttempts) {
      clearInterval(poll)
      running.value = false
      ElMessage.error('回测超时')
    }
  }, 5000)
}

function exportResult() {
  if (!currentResult.value) return

  const lines = [
    `回测报告 - ${new Date().toLocaleString()}`,
    '',
    '策略名称：' + backtestConfig.strategyName,
    '回测期间：' + backtestConfig.startDate + ' ~ ' + backtestConfig.endDate,
    '',
    '=== 回测统计 ===',
    '初始资金：' + backtestConfig.initialCapital,
    '最终资金：' + currentResult.value.finalCapital,
    '总收益率：' + currentResult.value.totalReturnPct + '%',
    '最大回撤：' + currentResult.value.maxDrawdownPct + '%',
    '夏普比率：' + currentResult.value.sharpeRatio,
    '胜率：' + currentResult.value.winRate + '%',
    '盈亏比：' + currentResult.value.profitFactor,
    '',
    '=== 交易统计 ===',
    '总交易次数：' + currentResult.value.totalTrades,
    '盈利交易：' + currentResult.value.winningTrades,
    '亏损交易：' + currentResult.value.losingTrades,
    '平均盈利：' + currentResult.value.avgProfit,
    ''
  ]

  const blob = new Blob(lines.join('\n'), { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `回测报告_${backtestConfig.strategyName}_${Date.now()}.txt`
  link.click()
  ElMessage.success('导出成功')
}

function loadBacktestRuns() {
  ElMessage.info('历史记录功能开发中')
}
</script>

<style scoped lang="scss">
.backtest-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .strategy-params {
    .section-title {
      font-size: 14px;
      color: #606266;
      margin-bottom: 12px;
      font-weight: 500;
    }
  }

  .backtest-result {
    .result-summary {
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;

      .summary-item {
        text-align: center;

        .summary-label {
          font-size: 14px;
          color: #909399;
          margin-bottom: 8px;
        }

        .summary-value {
          font-size: 24px;
          font-weight: bold;
          color: #303133;

          &.up {
            color: #f56c6c;
          }

          &.down {
            color: #67c23a;
          }
        }
      }
    }

    .detail-metrics {
      .metric-card {
        text-align: center;
        padding: 16px;
        background: #fafafa;
        border-radius: 8px;

        .metric-title {
          font-size: 14px;
          color: #909399;
          margin-bottom: 8px;
        }

        .metric-value {
          font-size: 20px;
          font-weight: bold;
          color: #303133;
        }

        &.small {
          padding: 12px;

          .metric-label {
            font-size: 12px;
            color: #909399;
            margin-bottom: 4px;
          }

          .metric-num {
            font-size: 16px;
            font-weight: 500;
            color: #303133;
          }
        }
      }
    }

    .section-title {
      font-size: 14px;
      color: #606266;
      margin-bottom: 12px;
      font-weight: 500;
    }

    .up {
      color: #f56c6c !important;
    }

    .down {
      color: #67c23a !important;
    }
  }

  .loading-container {
    text-align: center;
    padding: 60px 0;
    color: #909399;

    p {
      margin-top: 16px;
    }
  }
}
</style>
