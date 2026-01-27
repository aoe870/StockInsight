<template>
  <div class="screener-view">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>选股条件</span>
          </template>
          <div class="screener-conditions">
            <el-form label-width="80px">
              <el-form-item label="涨跌幅">
                <div class="range-input">
                  <el-input-number v-model="conditions.changePctMin" :precision="2" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.changePctMax" :precision="2" size="small" />
                </div>
              </el-form-item>
              <el-form-item label="价格区间">
                <div class="range-input">
                  <el-input-number v-model="conditions.priceMin" :precision="2" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.priceMax" :precision="2" size="small" />
                </div>
              </el-form-item>
              <el-form-item label="市盈率">
                <div class="range-input">
                  <el-input-number v-model="conditions.peMin" :precision="2" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.peMax" :precision="2" size="small" />
                </div>
              </el-form-item>
              <el-form-item label="市净率">
                <div class="range-input">
                  <el-input-number v-model="conditions.pbMin" :precision="2" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.pbMax" :precision="2" size="small" />
                </div>
              </el-form-item>
              <el-form-item label="换手率">
                <div class="range-input">
                  <el-input-number v-model="conditions.turnoverMin" :precision="2" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.turnoverMax" :precision="2" size="small" />
                </div>
              </el-form-item>
              <el-form-item label="市值">
                <div class="range-input">
                  <el-input-number v-model="conditions.marketValueMin" :precision="0" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.marketValueMax" :precision="0" size="small" />
                  <span>亿</span>
                </div>
              </el-form-item>
              <el-form-item label="成交量">
                <div class="range-input">
                  <el-input-number v-model="conditions.volumeMin" :precision="0" size="small" />
                  <span>-</span>
                  <el-input-number v-model="conditions.volumeMax" :precision="0" size="small" />
                  <span>万手</span>
                </div>
              </el-form-item>
            </el-form>

            <el-divider />

            <div class="saved-conditions">
              <div class="section-title">已保存条件</div>
              <el-select
                v-model="selectedCondition"
                placeholder="选择已保存条件"
                style="width: 100%; margin-bottom: 8px"
                @change="loadCondition"
              >
                <el-option
                  v-for="item in savedConditions"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
              <el-button
                text
                type="primary"
                size="small"
                :icon="Plus"
                @click="showSaveDialog = true"
              >
                保存当前条件
              </el-button>
            </div>

            <el-divider />

            <el-button type="primary" style="width: 100%" :loading="querying" @click="handleQuery">
              开始选股
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>选股结果 ({{ results.length }}只)</span>
              <el-button :disabled="results.length === 0" @click="exportResults">
                导出结果
              </el-button>
            </div>
          </template>

          <el-table :data="results" style="width: 100%" v-loading="querying">
            <el-table-column prop="code" label="代码" width="100" />
            <el-table-column prop="name" label="名称" width="120" />
            <el-table-column prop="price" label="现价" width="100" align="right">
              <template #default="{ row }">
                <span :class="getPriceColorClass(row.changePct)">
                  {{ row.price?.toFixed(2) || '-' }}
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
            <el-table-column prop="turnover" label="换手率" width="100" align="right">
              <template #default="{ row }">
                {{ row.turnover?.toFixed(2) || '-' }}%
              </template>
            </el-table-column>
            <el-table-column prop="peTtm" label="市盈率" width="100" align="right" />
            <el-table-column prop="pb" label="市净率" width="100" align="right" />
            <el-table-column prop="marketValue" label="市值" width="120" align="right">
              <template #default="{ row }">
                {{ formatAmount(row.marketValue) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewDetail(row.code)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!querying && results.length === 0" description="请设置选股条件后点击开始选股" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 保存条件对话框 -->
    <el-dialog v-model="showSaveDialog" title="保存选股条件" width="400px">
      <el-form :model="saveForm" label-width="80px">
        <el-form-item label="条件名称">
          <el-input v-model="saveForm.name" placeholder="输入条件名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCondition">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatNumber, formatPercent, formatAmount, getPriceColorClass } from '@/utils'

const router = useRouter()
const querying = ref(false)
const results = ref([])
const savedConditions = ref([])
const selectedCondition = ref<number | null>(null)

const conditions = reactive({
  changePctMin: -100,
  changePctMax: 100,
  priceMin: 0,
  priceMax: 10000,
  peMin: 0,
  peMax: 1000,
  pbMin: 0,
  pbMax: 100,
  turnoverMin: 0,
  turnoverMax: 100,
  marketValueMin: 0,
  marketValueMax: 100000,
  volumeMin: 0,
  volumeMax: 1000000
})

const showSaveDialog = ref(false)
const saveForm = reactive({
  name: ''
})

onMounted(() => {
  loadSavedConditions()
})

async function loadSavedConditions() {
  try {
    const result = await api.getScreenerConditions()
    savedConditions.value = result.data || []
  } catch (error) {
    console.error('加载已保存条件失败', error)
  }
}

async function handleQuery() {
  querying.value = true
  try {
    const params: any = {}
    if (conditions.changePctMin !== -100) params.change_pct_min = conditions.changePctMin
    if (conditions.changePctMax !== 100) params.change_pct_max = conditions.changePctMax
    if (conditions.priceMin > 0) params.price_min = conditions.priceMin
    if (conditions.priceMax < 10000) params.price_max = conditions.priceMax
    if (conditions.peMin > 0) params.pe_min = conditions.peMin
    if (conditions.peMax < 1000) params.pe_max = conditions.peMax
    if (conditions.pbMin > 0) params.pb_min = conditions.pbMin
    if (conditions.pbMax < 100) params.pb_max = conditions.pbMax
    if (conditions.turnoverMin > 0) params.turnover_min = conditions.turnoverMin
    if (conditions.turnoverMax < 100) params.turnover_max = conditions.turnoverMax
    if (conditions.marketValueMin > 0) params.market_value_min = conditions.marketValueMin * 100000000
    if (conditions.marketValueMax < 100000) params.market_value_max = conditions.marketValueMax * 100000000
    if (conditions.volumeMin > 0) params.volume_min = conditions.volumeMin * 10000
    if (conditions.volumeMax < 1000000) params.volume_max = conditions.volumeMax * 10000

    const result = await api.screenerQuery(params)
    results.value = result.data || []
    ElMessage.success(`选股完成，共找到 ${results.value.length} 只股票`)
  } catch (error) {
    ElMessage.error('选股失败')
  } finally {
    querying.value = false
  }
}

async function handleSaveCondition() {
  if (!saveForm.name.trim()) {
    ElMessage.warning('请输入条件名称')
    return
  }

  try {
    const config = {
      change_pct_min: conditions.changePctMin,
      change_pct_max: conditions.changePctMax,
      price_min: conditions.priceMin,
      price_max: conditions.priceMax,
      pe_min: conditions.peMin,
      pe_max: conditions.peMax,
      pb_min: conditions.pbMin,
      pb_max: conditions.pbMax,
      turnover_min: conditions.turnoverMin,
      turnover_max: conditions.turnoverMax,
      market_value_min: conditions.marketValueMin,
      market_value_max: conditions.marketValueMax,
      volume_min: conditions.volumeMin,
      volume_max: conditions.volumeMax
    }

    await api.createScreenerCondition({
      name: saveForm.name,
      description: '用户自定义选股条件',
      condition_config: config
    })

    ElMessage.success('保存成功')
    showSaveDialog.value = false
    saveForm.name = ''
    loadSavedConditions()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

function loadCondition(id: number) {
  const condition = savedConditions.value.find((c: any) => c.id === id)
  if (!condition || !condition.condition_config) return

  const config = condition.condition_config
  conditions.changePctMin = config.change_pct_min ?? -100
  conditions.changePctMax = config.change_pct_max ?? 100
  conditions.priceMin = config.price_min ?? 0
  conditions.priceMax = config.price_max ?? 10000
  conditions.peMin = config.pe_min ?? 0
  conditions.peMax = config.pe_max ?? 1000
  conditions.pbMin = config.pb_min ?? 0
  conditions.pbMax = config.pb_max ?? 100
  conditions.turnoverMin = config.turnover_min ?? 0
  conditions.turnoverMax = config.turnover_max ?? 100
  conditions.marketValueMin = config.market_value_min ?? 0
  conditions.marketValueMax = config.market_value_max ?? 100000
  conditions.volumeMin = config.volume_min ?? 0
  conditions.volumeMax = config.volume_max ?? 1000000
}

function exportResults() {
  // 导出CSV格式
  const headers = ['代码', '名称', '现价', '涨跌幅', '成交量', '换手率', '市盈率', '市净率', '市值']
  const rows = results.value.map((r: any) => [
    r.code,
    r.name,
    r.price?.toFixed(2) || '',
    `${r.changePct >= 0 ? '+' : ''}${r.changePct?.toFixed(2)}%`,
    formatNumber(r.volume / 100, 0),
    `${r.turnover?.toFixed(2) || ''}%`,
    r.peTtm?.toFixed(2) || '',
    r.pb?.toFixed(2) || '',
    formatAmount(r.marketValue)
  ])

  const csv = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `选股结果_${new Date().getTime()}.csv`
  link.click()
  ElMessage.success('导出成功')
}

function viewDetail(code: string) {
  router.push(`/stock/${code}`)
}
</script>

<style scoped lang="scss">
.screener-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .screener-conditions {
    .range-input {
      display: flex;
      align-items: center;
      gap: 8px;

      .el-input-number {
        flex: 1;
      }

      span {
        color: #909399;
        font-size: 14px;
      }
    }

    .saved-conditions {
      .section-title {
        font-size: 14px;
        color: #606266;
        margin-bottom: 8px;
      }
    }
  }
}
</style>
