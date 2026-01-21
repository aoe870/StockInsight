<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import BacktestConfig from '@/components/BacktestConfig.vue'
import BacktestResult from '@/components/BacktestResult.vue'
import { backtestApi, type StrategyInfo, type BacktestResultResponse } from '@/api/backtest'

const loading = ref(false)
const strategies = ref<StrategyInfo[]>([])
const result = ref<BacktestResultResponse | null>(null)

// 获取策略列表
const fetchStrategies = async () => {
  try {
    const data = await backtestApi.getStrategies()
    strategies.value = data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取策略列表失败')
  }
}

// 运行回测
const handleRunBacktest = async (config: any) => {
  loading.value = true
  result.value = null

  try {
    const data = await backtestApi.run(config)
    result.value = data
    ElMessage.success('回测完成')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '回测执行失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStrategies()
})
</script>

<template>
  <div class="backtest-view">
    <h1>选股策略回测</h1>

    <div class="backtest-layout">
      <!-- 左侧：配置面板 -->
      <div class="config-panel">
        <BacktestConfig
          :strategies="strategies"
          :loading="loading"
          @run="handleRunBacktest"
        />
      </div>

      <!-- 右侧：结果展示 -->
      <div class="result-panel">
        <BacktestResult v-if="result" :result="result" />
        <div v-else class="placeholder">
          <p>配置回测参数后点击"开始回测"查看结果</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backtest-view {
  padding: 20px;
}

.backtest-view h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}

.backtest-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
  align-items: start;
}

.config-panel {
  position: sticky;
  top: 20px;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  background: #f9f9f9;
  border-radius: 8px;
  color: #999;
}

@media (max-width: 1200px) {
  .backtest-layout {
    grid-template-columns: 1fr;
  }

  .config-panel {
    position: static;
  }
}
</style>
