<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { screenerApi, type ScreenerResult, type ScreenerStatus, type Strategy } from '@/api'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, CaretTop, CaretBottom, Edit } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const status = ref<ScreenerStatus | null>(null)
const results = ref<ScreenerResult[]>([])
const strategies = ref<Strategy[]>([])

// 选股模式: preset=预设策略, custom=自定义公式
const mode = ref<'preset' | 'custom'>('preset')

// 选中的策略（默认地量回调）
const selectedStrategyId = ref('volume_contraction')
const selectedStrategy = computed(() =>
  strategies.value.find(s => s.id === selectedStrategyId.value)
)

// 参数设置
const market = ref('')
const strategyParams = ref<Record<string, number>>({})

// 自定义公式
const customFormula = ref('')
const customFormulaName = ref('')  // 自定义公式名称

// 保存的自定义公式列表
interface SavedFormula {
  name: string
  formula: string
}
const savedFormulas = ref<SavedFormula[]>([])

// 从localStorage加载保存的公式
const loadSavedFormulas = () => {
  try {
    const saved = localStorage.getItem('savedFormulas')
    if (saved) {
      savedFormulas.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载保存的公式失败', e)
  }
}

// 保存公式到localStorage
const saveFormula = () => {
  if (!customFormulaName.value.trim()) {
    ElMessage.warning('请输入公式名称')
    return
  }
  if (!customFormula.value.trim()) {
    ElMessage.warning('请输入公式内容')
    return
  }

  // 检查是否已存在
  const existIndex = savedFormulas.value.findIndex(f => f.name === customFormulaName.value)
  if (existIndex >= 0) {
    savedFormulas.value[existIndex].formula = customFormula.value
  } else {
    savedFormulas.value.push({
      name: customFormulaName.value,
      formula: customFormula.value,
    })
  }

  localStorage.setItem('savedFormulas', JSON.stringify(savedFormulas.value))
  ElMessage.success('公式已保存')
}

// 加载保存的公式
const loadFormula = (formula: SavedFormula) => {
  customFormulaName.value = formula.name
  customFormula.value = formula.formula
}

// 删除保存的公式
const deleteFormula = (index: number) => {
  savedFormulas.value.splice(index, 1)
  localStorage.setItem('savedFormulas', JSON.stringify(savedFormulas.value))
  ElMessage.success('已删除')
}

let pollTimer: ReturnType<typeof setInterval> | null = null

// 是否正在运行
const isRunning = computed(() => status.value?.is_running || false)

// 进度百分比
const progress = computed(() => {
  if (!status.value || status.value.total === 0) return 0
  return Math.round((status.value.processed / status.value.total) * 100)
})

// 加载策略列表
const loadStrategies = async () => {
  try {
    const res = await screenerApi.getStrategies()
    strategies.value = res.strategies
    if (res.strategies.length > 0 && !selectedStrategyId.value) {
      selectedStrategyId.value = res.strategies[0].id
    }
  } catch (error) {
    console.error('加载策略失败:', error)
  }
}

// 监听策略变化，初始化参数
watch(selectedStrategy, (strategy) => {
  if (strategy) {
    const params: Record<string, number> = {}
    strategy.params.forEach(p => {
      params[p.key] = p.default
    })
    strategyParams.value = params
  }
}, { immediate: true })

// 获取状态
const fetchStatus = async () => {
  try {
    const res = await screenerApi.getStatus()
    status.value = res.status
    if (res.status.results && res.status.results.length > 0) {
      results.value = res.status.results
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

// 获取结果
const fetchResults = async () => {
  try {
    const res = await screenerApi.getResults({ sort_by: 'change_pct', sort_order: 'desc' })
    results.value = res.items
  } catch (error) {
    console.error('获取结果失败:', error)
  }
}

// 开始选股
const startScreener = async () => {
  loading.value = true
  try {
    const request: any = {
      market: market.value || undefined,
    }

    if (mode.value === 'preset') {
      request.strategy_id = selectedStrategyId.value
      request.params = strategyParams.value
    } else {
      request.formula = customFormula.value
    }

    const res = await screenerApi.run(request)
    if (res.success) {
      ElMessage.success('选股任务已启动')
      startPolling()
    } else {
      ElMessage.warning(res.message)
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '启动失败')
  } finally {
    loading.value = false
  }
}

// 停止选股
const stopScreener = async () => {
  try {
    await screenerApi.stop()
    ElMessage.info('已停止选股')
    stopPolling()
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

// 轮询状态
const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    await fetchStatus()
    if (!status.value?.is_running) {
      stopPolling()
      await fetchResults()
      ElMessage.success(`选股完成，共找到 ${results.value.length} 只股票`)
    }
  }, 1000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 跳转详情
const goToDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

// 格式化涨跌颜色
const getPriceClass = (change: number) => {
  if (change > 0) return 'price-up'
  if (change < 0) return 'price-down'
  return 'price-flat'
}

// 格式化数字
const formatVolume = (num: number) => {
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(0) + '万'
  return num.toString()
}

// 复制预设公式到自定义
const copyFormulaToCustom = () => {
  if (selectedStrategy.value) {
    customFormula.value = selectedStrategy.value.formula
    mode.value = 'custom'
  }
}

onMounted(async () => {
  loadSavedFormulas()
  await Promise.all([loadStrategies(), fetchStatus()])
  if (status.value?.is_running) {
    startPolling()
  } else if (status.value?.results?.length) {
    results.value = status.value.results
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="screener-view">
    <!-- 策略配置 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>📊 指标选股</span>
          <el-radio-group v-model="mode" size="small">
            <el-radio-button value="preset">预设策略</el-radio-button>
            <el-radio-button value="custom">自定义公式</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 预设策略模式 -->
      <div v-if="mode === 'preset'" class="preset-mode">
        <el-form label-width="80px">
          <el-form-item label="选择策略">
            <el-select v-model="selectedStrategyId" style="width: 200px">
              <el-option-group
                v-for="category in ['量能', '趋势', '突破', '震荡']"
                :key="category"
                :label="category"
              >
                <el-option
                  v-for="s in strategies.filter(x => x.category === category)"
                  :key="s.id"
                  :label="s.name"
                  :value="s.id"
                />
              </el-option-group>
            </el-select>
            <el-button :icon="Edit" text @click="copyFormulaToCustom" title="复制到自定义">
              编辑公式
            </el-button>
          </el-form-item>

          <el-form-item v-if="selectedStrategy">
            <div class="strategy-desc">{{ selectedStrategy.description }}</div>
          </el-form-item>

          <!-- 策略参数 -->
          <el-form-item
            v-for="param in selectedStrategy?.params || []"
            :key="param.key"
            :label="param.name"
          >
            <el-input-number
              v-model="strategyParams[param.key]"
              :min="param.min"
              :max="param.max"
              :step="1"
            />
          </el-form-item>

          <el-form-item label="市场">
            <el-select v-model="market" placeholder="全部" style="width: 120px" clearable>
              <el-option label="上海" value="SH" />
              <el-option label="深圳" value="SZ" />
              <el-option label="北交所" value="BJ" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <!-- 自定义公式模式 -->
      <div v-else class="custom-mode">
        <el-row :gutter="20">
          <!-- 左侧：公式编辑 -->
          <el-col :span="16">
            <el-form label-width="80px">
              <el-form-item label="公式名称">
                <el-input
                  v-model="customFormulaName"
                  placeholder="给公式起个名字..."
                  style="width: 200px"
                />
                <el-button type="primary" text @click="saveFormula">保存公式</el-button>
              </el-form-item>
              <el-form-item label="选股公式">
                <el-input
                  v-model="customFormula"
                  type="textarea"
                  :rows="10"
                  placeholder="输入选股公式，支持通达信语法..."
                  class="formula-editor"
                />
              </el-form-item>
              <el-form-item>
                <div class="formula-help">
                  <p><strong>支持的函数：</strong></p>
                  <code>MA, EMA, SMA, REF, COUNT, SUM, HHV, LLV, STD, CROSS, IF, ABS, MAX, MIN</code>
                  <p><strong>支持的变量：</strong></p>
                  <code>OPEN/O, HIGH/H, LOW/L, CLOSE/C, VOL/VOLUME/V, AMOUNT</code>
                  <p><strong>示例：</strong></p>
                  <code>选股 := CROSS(MA(C,5), MA(C,20)) AND VOL > MA(VOL,5)*1.5;</code>
                </div>
              </el-form-item>
              <el-form-item label="市场">
                <el-select v-model="market" placeholder="全部" style="width: 120px" clearable>
                  <el-option label="上海" value="SH" />
                  <el-option label="深圳" value="SZ" />
                  <el-option label="北交所" value="BJ" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-col>
          <!-- 右侧：保存的公式列表 -->
          <el-col :span="8">
            <div class="saved-formulas">
              <h4>📁 我的公式</h4>
              <el-scrollbar max-height="300px">
                <div v-if="savedFormulas.length === 0" class="empty-tip">
                  暂无保存的公式
                </div>
                <div
                  v-for="(formula, index) in savedFormulas"
                  :key="index"
                  class="formula-item"
                  @click="loadFormula(formula)"
                >
                  <span class="formula-name">{{ formula.name }}</span>
                  <el-button
                    type="danger"
                    text
                    size="small"
                    @click.stop="deleteFormula(index)"
                  >
                    删除
                  </el-button>
                </div>
              </el-scrollbar>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <el-button
          v-if="!isRunning"
          type="primary"
          :icon="VideoPlay"
          :loading="loading"
          @click="startScreener"
        >
          开始选股
        </el-button>
        <el-button
          v-else
          type="danger"
          :icon="VideoPause"
          @click="stopScreener"
        >
          停止
        </el-button>
      </div>

      <!-- 进度条 -->
      <div v-if="isRunning" class="progress-section">
        <el-progress :percentage="progress" :stroke-width="20" striped striped-flow>
          <span>{{ status?.processed || 0 }} / {{ status?.total || 0 }}</span>
        </el-progress>
        <div class="progress-info">
          已找到 <strong>{{ status?.matched || 0 }}</strong> 只符合条件的股票
        </div>
      </div>
    </el-card>

    <!-- 选股结果 -->
    <el-card class="result-card">
      <template #header>
        <div class="card-header">
          <span>选股结果</span>
          <el-tag v-if="results.length > 0" type="success">{{ results.length }} 只</el-tag>
        </div>
      </template>

      <el-table
        :data="results"
        style="width: 100%"
        @row-click="(row: ScreenerResult) => goToDetail(row.code)"
        row-class-name="stock-row"
        max-height="500"
      >
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="market" label="市场" width="70">
          <template #default="{ row }">
            <el-tag size="small" :type="row.market === 'SH' ? 'danger' : 'primary'">
              {{ row.market }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" width="100" show-overflow-tooltip />
        <el-table-column label="收盘价" width="100" align="right" sortable prop="close">
          <template #default="{ row }">
            <span :class="getPriceClass(row.change_pct)">{{ row.close.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="110" align="right" sortable prop="change_pct">
          <template #default="{ row }">
            <span :class="getPriceClass(row.change_pct)" class="change-cell">
              <el-icon v-if="row.change_pct > 0"><CaretTop /></el-icon>
              <el-icon v-else-if="row.change_pct < 0"><CaretBottom /></el-icon>
              {{ row.change_pct >= 0 ? '+' : '' }}{{ row.change_pct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成交量" width="100" align="right" sortable prop="volume">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column prop="trade_date" label="日期" width="110" />
      </el-table>

      <el-empty v-if="results.length === 0 && !isRunning" description="暂无选股结果，请先运行选股" />
    </el-card>
  </div>
</template>

<style scoped>
.screener-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preset-mode,
.custom-mode {
  margin-bottom: 16px;
}

.strategy-desc {
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  color: #666;
}

.formula-editor :deep(textarea) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.formula-help {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
}

.formula-help p {
  margin: 8px 0 4px 0;
}

.formula-help p:first-child {
  margin-top: 0;
}

.formula-help code {
  display: block;
  background: #e8e8e8;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}

.action-bar {
  margin-bottom: 16px;
}

.progress-section {
  margin-top: 16px;
}

.progress-info {
  margin-top: 8px;
  font-size: 14px;
  color: #666;
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

.saved-formulas {
  background: #f9f9f9;
  border-radius: 6px;
  padding: 12px;
}

.saved-formulas h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.empty-tip {
  color: #999;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.formula-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 4px;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.formula-item:hover {
  background: #e8f4ff;
}

.formula-name {
  font-size: 13px;
  color: #333;
}
</style>

