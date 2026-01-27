<template>
  <div class="alerts-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>预警管理</span>
          <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
            新建预警
          </el-button>
        </div>
      </template>

      <el-table :data="alerts" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="预警名称" width="180" />
        <el-table-column prop="stockCode" label="股票代码" width="100" />
        <el-table-column prop="alertType" label="预警类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getAlertTypeColor(row.alertType)" size="small">
              {{ getAlertTypeName(row.alertType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="conditionConfig" label="预警条件" min-width="200">
          <template #default="{ row }">
            {{ formatCondition(row.alertType, row.conditionConfig) }}
          </template>
        </el-table-column>
        <el-table-column prop="frequency" label="触发频率" width="100" />
        <el-table-column prop="triggerCount" label="触发次数" width="100" align="right" />
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="'enabled'"
              :inactive-value="'disabled'"
              @change="toggleAlertStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="lastTriggeredAt" label="最后触发" width="160">
          <template #default="{ row }">
            {{ row.lastTriggeredAt ? formatDateTime(row.lastTriggeredAt) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewHistory(row)">历史</el-button>
            <el-button type="primary" link @click="editAlert(row)">编辑</el-button>
            <el-button type="danger" link @click="deleteAlert(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && alerts.length === 0" description="暂无预警规则" />
    </el-card>

    <!-- 新建/编辑预警对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingAlert ? '编辑预警' : '新建预警'"
      width="600px"
    >
      <el-form :model="alertForm" :rules="alertRules" ref="alertFormRef" label-width="100px">
        <el-form-item label="预警名称" prop="name">
          <el-input v-model="alertForm.name" placeholder="输入预警名称" />
        </el-form-item>
        <el-form-item label="股票代码" prop="stockCode">
          <el-input v-model="alertForm.stockCode" placeholder="输入股票代码，如：000001" />
        </el-form-item>
        <el-form-item label="预警类型" prop="alertType">
          <el-select v-model="alertForm.alertType" style="width: 100%" @change="handleAlertTypeChange">
            <el-option label="价格预警" value="price" />
            <el-option label="涨跌幅预警" value="change_pct" />
            <el-option label="成交量预警" value="volume" />
            <el-option label="资金流向预警" value="money_flow" />
          </el-select>
        </el-form-item>

        <!-- 价格预警条件 -->
        <template v-if="alertForm.alertType === 'price'">
          <el-form-item label="价格条件" prop="condition">
            <el-select v-model="alertForm.operator" style="width: 100px; margin-right: 8px">
              <el-option label="高于" value=">" />
              <el-option label="低于" value="<" />
              <el-option label="高于等于" value=">=" />
              <el-option label="低于等于" value="<=" />
            </el-select>
            <el-input-number v-model="alertForm.value" :precision="2" :min="0" />
          </el-form-item>
        </template>

        <!-- 涨跌幅预警条件 -->
        <template v-if="alertForm.alertType === 'change_pct'">
          <el-form-item label="涨跌幅条件" prop="condition">
            <el-select v-model="alertForm.operator" style="width: 100px; margin-right: 8px">
              <el-option label="高于" value=">" />
              <el-option label="低于" value="<" />
              <el-option label="高于等于" value=">=" />
              <el-option label="低于等于" value="<=" />
            </el-select>
            <el-input-number v-model="alertForm.value" :precision="2" />
            <span style="margin-left: 8px">%</span>
          </el-form-item>
        </template>

        <!-- 成交量预警条件 -->
        <template v-if="alertForm.alertType === 'volume'">
          <el-form-item label="成交量条件" prop="condition">
            <el-select v-model="alertForm.operator" style="width: 100px; margin-right: 8px">
              <el-option label="高于" value=">" />
              <el-option label="低于" value="<" />
              <el-option label="高于等于" value=">=" />
              <el-option label="低于等于" value="<=" />
            </el-select>
            <el-input-number v-model="alertForm.value" :precision="0" :min="0" />
            <span style="margin-left: 8px">手</span>
          </el-form-item>
        </template>

        <!-- 资金流向预警条件 -->
        <template v-if="alertForm.alertType === 'money_flow'">
          <el-form-item label="净流入额" prop="condition">
            <el-select v-model="alertForm.operator" style="width: 100px; margin-right: 8px">
              <el-option label="高于" value=">" />
              <el-option label="低于" value="<" />
              <el-option label="高于等于" value=">=" />
              <el-option label="低于等于" value="<=" />
            </el-select>
            <el-input-number v-model="alertForm.value" :precision="0" :min="0" />
            <span style="margin-left: 8px">万</span>
          </el-form-item>
          <el-form-item label="天数">
            <el-input-number v-model="alertForm.days" :min="1" :max="30" />
          </el-form-item>
        </template>

        <el-form-item label="触发频率" prop="frequency">
          <el-select v-model="alertForm.frequency" style="width: 100%">
            <el-option label="仅一次" value="once" />
            <el-option label="每次触发" value="always" />
            <el-option label="每天一次" value="daily" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveAlert">确定</el-button>
      </template>
    </el-dialog>

    <!-- 预警历史对话框 -->
    <el-dialog v-model="showHistoryDialog" title="预警历史" width="800px">
      <el-table :data="alertHistory" style="width: 100%" v-loading="historyLoading">
        <el-table-column prop="triggeredAt" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.triggeredAt) }}
          </template>
        </el-table-column>
        <el-table-column prop="triggerValue" label="触发值" width="150" align="right" />
        <el-table-column prop="condition" label="预警条件" />
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'read' ? 'info' : 'success'" size="small">
              {{ row.status === 'read' ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!historyLoading && alertHistory.length === 0" description="暂无触发历史" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatDateTime } from '@/utils'

const loading = ref(false)
const saving = ref(false)
const historyLoading = ref(false)

const alerts = ref([])
const alertHistory = ref([])
const editingAlert = ref<any>(null)

const showCreateDialog = ref(false)
const showHistoryDialog = ref(false)
const alertFormRef = ref<FormInstance>()

const alertForm = reactive({
  name: '',
  stockCode: '',
  alertType: 'price',
  operator: '>',
  value: 0,
  days: 1,
  frequency: 'once'
})

const alertRules: FormRules = {
  name: [{ required: true, message: '请输入预警名称', trigger: 'blur' }],
  stockCode: [{ required: true, message: '请输入股票代码', trigger: 'blur' }],
  alertType: [{ required: true, message: '请选择预警类型', trigger: 'change' }]
}

onMounted(() => {
  loadAlerts()
})

async function loadAlerts() {
  loading.value = true
  try {
    const result = await api.getAlerts()
    alerts.value = result.data || []
  } catch (error) {
    ElMessage.error('加载预警列表失败')
  } finally {
    loading.value = false
  }
}

async function handleSaveAlert() {
  if (!alertFormRef.value) return

  await alertFormRef.value.validate(async (valid) => {
    if (!valid) return

    const config: any = { operator: alertForm.operator, value: alertForm.value }
    if (alertForm.alertType === 'money_flow') {
      config.days = alertForm.days
    }

    const data = {
      name: alertForm.name,
      stockCode: alertForm.stockCode,
      alertType: alertForm.alertType,
      conditionConfig: config,
      frequency: alertForm.frequency
    }

    saving.value = true
    try {
      if (editingAlert.value) {
        await api.updateAlert(editingAlert.value.id, data)
        ElMessage.success('更新成功')
      } else {
        await api.createAlert(data)
        ElMessage.success('创建成功')
      }
      showCreateDialog.value = false
      resetAlertForm()
      loadAlerts()
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

function editAlert(alert: any) {
  editingAlert.value = alert
  alertForm.name = alert.name
  alertForm.stockCode = alert.stockCode
  alertForm.alertType = alert.alertType
  alertForm.frequency = alert.frequency
  alertForm.operator = (alert.conditionConfig as any)?.operator || '>'
  alertForm.value = (alert.conditionConfig as any)?.value || 0
  alertForm.days = (alert.conditionConfig as any)?.days || 1
  showCreateDialog.value = true
}

async function deleteAlert(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除这条预警吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.deleteAlert(id)
    ElMessage.success('删除成功')
    loadAlerts()
  } catch (error) {
    // 用户取消
  }
}

async function toggleAlertStatus(alert: any) {
  try {
    if (alert.status === 'enabled') {
      await api.enableAlert(alert.id)
    } else {
      await api.disableAlert(alert.id)
    }
    ElMessage.success(alert.status === 'enabled' ? '已启用' : '已禁用')
  } catch (error) {
    ElMessage.error('操作失败')
    alert.status = alert.status === 'enabled' ? 'disabled' : 'enabled'
  }
}

async function viewHistory(alert: any) {
  showHistoryDialog.value = true
  historyLoading.value = true
  try {
    const result = await api.getAlertHistory(alert.id, 50)
    alertHistory.value = result.data || []
  } catch (error) {
    ElMessage.error('加载历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

function handleAlertTypeChange() {
  alertForm.operator = '>'
  alertForm.value = 0
  alertForm.days = 1
}

function resetAlertForm() {
  editingAlert.value = null
  alertForm.name = ''
  alertForm.stockCode = ''
  alertForm.alertType = 'price'
  alertForm.operator = '>'
  alertForm.value = 0
  alertForm.days = 1
  alertForm.frequency = 'once'
}

function getAlertTypeName(type: string): string {
  const map: Record<string, string> = {
    price: '价格预警',
    change_pct: '涨跌幅预警',
    volume: '成交量预警',
    money_flow: '资金流向预警'
  }
  return map[type] || type
}

function getAlertTypeColor(type: string): string {
  const map: Record<string, string> = {
    price: '',
    change_pct: 'warning',
    volume: 'success',
    money_flow: 'danger'
  }
  return map[type] || ''
}

function formatCondition(type: string, config: any): string {
  if (!config) return '-'
  const map: Record<string, string> = {
    price: `价格${config.operator}${config.value}`,
    change_pct: `涨跌幅${config.operator}${config.value}%`,
    volume: `成交量${config.operator}${config.value}手`,
    money_flow: `净流入${config.operator}${config.value}万（${config.days}天）`
  }
  return map[type] || '-'
}
</script>

<style scoped lang="scss">
.alerts-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
