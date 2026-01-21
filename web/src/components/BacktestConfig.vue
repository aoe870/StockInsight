<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElDatePicker, ElSelect, ElInputNumber, ElButton, ElForm, ElFormItem, ElCheckbox } from 'element-plus'
import type { StrategyInfo, StrategyParam } from '@/api/backtest'

interface Props {
  strategies: StrategyInfo[]
  loading?: boolean
}

interface Emits {
  (e: 'run', config: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 配置表单
const config = ref({
  strategy_name: 'rsi_macd',
  strategy_params: {} as Record<string, any>,
  start_date: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000), // 默认一年前
  end_date: new Date(),
  initial_cash: 100000,
  commission: 0.0003,
  slippage: 0.001,
  max_positions: 10,
  position_size: 0.1,
  hold_days: 20,
  rebalance_freq: 'weekly',
  stock_pool: [] as string[],
})

const stockPoolMode = ref<'all' | 'custom'>('all')
const customStocks = ref('')

// 当前策略
const currentStrategy = computed(() => {
  return props.strategies.find(s => s.name === config.value.strategy_name)
})

// 策略参数
const strategyParams = computed(() => {
  return currentStrategy.value?.params || []
})

// 获取策略参数的默认值
const initStrategyParams = () => {
  const params: Record<string, any> = {}
  strategyParams.value.forEach((param: StrategyParam) => {
    params[param.name] = param.default
  })
  config.value.strategy_params = params
}

// 策略变化时初始化参数
const onStrategyChange = () => {
  initStrategyParams()
}

// 格式化日期
const formatDate = (date: Date) => {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 运行回测
const handleRun = () => {
  // 处理股票池
  let stockPool: string[] | undefined = undefined
  if (stockPoolMode.value === 'custom' && customStocks.value.trim()) {
    stockPool = customStocks.value
      .split(/[,，\n]/)
      .map(s => s.trim())
      .filter(s => s.length > 0)
  }

  const requestData = {
    strategy_name: config.value.strategy_name,
    strategy_params: config.value.strategy_params,
    start_date: formatDate(config.value.start_date as Date),
    end_date: formatDate(config.value.end_date as Date),
    initial_cash: config.value.initial_cash,
    commission: config.value.commission,
    slippage: config.value.slippage,
    max_positions: config.value.max_positions,
    position_size: config.value.position_size,
    hold_days: config.value.hold_days,
    rebalance_freq: config.value.rebalance_freq,
    stock_pool: stockPool,
  }

  emit('run', requestData)
}

// 初始化
initStrategyParams()
</script>

<template>
  <div class="backtest-config">
    <h2>回测配置</h2>

    <ElForm label-width="100px" label-position="left">
      <!-- 策略选择 -->
      <ElFormItem label="策略">
        <ElSelect
          v-model="config.strategy_name"
          @change="onStrategyChange"
          style="width: 100%"
        >
          <ElOption
            v-for="s in strategies"
            :key="s.name"
            :label="s.display_name"
            :value="s.name"
          >
            <div>{{ s.display_name }}</div>
            <div style="font-size: 12px; color: #999;">{{ s.description }}</div>
          </ElOption>
        </ElSelect>
      </ElFormItem>

      <!-- 策略参数 -->
      <div v-if="strategyParams.length > 0" class="strategy-params">
        <div style="margin-bottom: 10px; font-weight: 500;">策略参数</div>
        <ElFormItem
          v-for="param in strategyParams"
          :key="param.name"
          :label="param.display_name"
        >
          <ElInputNumber
            v-model="config.strategy_params[param.name]"
            :min="param.min"
            :max="param.max"
            style="width: 100%"
          />
        </ElFormItem>
      </div>

      <!-- 时间范围 -->
      <ElFormItem label="时间范围">
        <div class="date-range">
          <ElDatePicker
            v-model="config.start_date"
            type="date"
            placeholder="开始日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
          <span style="margin: 0 8px;">-</span>
          <ElDatePicker
            v-model="config.end_date"
            type="date"
            placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </div>
      </ElFormItem>

      <!-- 资金管理 -->
      <div class="section-title">资金管理</div>

      <ElFormItem label="初始资金">
        <ElInputNumber
          v-model="config.initial_cash"
          :min="1000"
          :step="10000"
          style="width: 100%"
        />
      </ElFormItem>

      <ElFormItem label="手续费率">
        <ElInputNumber
          v-model="config.commission"
          :min="0"
          :max="0.01"
          :step="0.0001"
          :precision="4"
          style="width: 100%"
        />
      </ElFormItem>

      <ElFormItem label="滑点率">
        <ElInputNumber
          v-model="config.slippage"
          :min="0"
          :max="0.05"
          :step="0.0001"
          :precision="4"
          style="width: 100%"
        />
      </ElFormItem>

      <!-- 仓位管理 -->
      <div class="section-title">仓位管理</div>

      <ElFormItem label="最大持仓">
        <ElInputNumber
          v-model="config.max_positions"
          :min="1"
          :max="50"
          style="width: 100%"
        />
      </ElFormItem>

      <ElFormItem label="单股仓位">
        <ElInputNumber
          v-model="config.position_size"
          :min="0.01"
          :max="1.0"
          :step="0.05"
          :precision="2"
          style="width: 100%"
        />
      </ElFormItem>

      <ElFormItem label="持有天数">
        <ElInputNumber
          v-model="config.hold_days"
          :min="1"
          :max="365"
          style="width: 100%"
        />
      </ElFormItem>

      <ElFormItem label="调仓频率">
        <ElSelect v-model="config.rebalance_freq" style="width: 100%">
          <ElOption label="每日" value="daily" />
          <ElOption label="每周" value="weekly" />
          <ElOption label="每月" value="monthly" />
        </ElSelect>
      </ElFormItem>

      <!-- 股票池 -->
      <div class="section-title">股票池</div>

      <ElFormItem label="股票池">
        <ElCheckbox v-model="stockPoolMode" true-label="all" false-label="custom">
          {{ stockPoolMode === 'all' ? '全市场' : '自定义' }}
        </ElCheckbox>
      </ElFormItem>

      <ElFormItem v-if="stockPoolMode === 'custom'" label="股票代码">
        <ElInput
          v-model="customStocks"
          type="textarea"
          :rows="3"
          placeholder="输入股票代码，用逗号或换行分隔&#10;例如：000001, 000002, 600000"
        />
      </ElFormItem>

      <!-- 提交按钮 -->
      <ElFormItem>
        <ElButton
          type="primary"
          @click="handleRun"
          :loading="loading"
          style="width: 100%"
        >
          开始回测
        </ElButton>
      </ElFormItem>
    </ElForm>
  </div>
</template>

<style scoped>
.backtest-config {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.backtest-config h2 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #666;
  margin: 16px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #eee;
}

.strategy-params {
  margin: 12px 0;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.date-range {
  display: flex;
  align-items: center;
  width: 100%;
}
</style>
