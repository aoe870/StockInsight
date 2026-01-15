<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { alertApi, type AlertRule, type AlertHistory } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Bell, Clock } from '@element-plus/icons-vue'

const activeTab = ref('rules')
const loading = ref(false)
const rules = ref<AlertRule[]>([])
const history = ref<AlertHistory[]>([])

const fetchRules = async () => {
  loading.value = true
  try {
    rules.value = await alertApi.getRules()
  } catch (error) {
    console.error('获取预警规则失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  loading.value = true
  try {
    history.value = await alertApi.getHistory({ limit: 50 })
  } catch (error) {
    console.error('获取预警历史失败:', error)
  } finally {
    loading.value = false
  }
}

const deleteRule = async (rule: AlertRule) => {
  try {
    await ElMessageBox.confirm(`确定删除该预警规则吗？`, '确认删除', {
      type: 'warning',
    })
    await alertApi.deleteRule(rule.id)
    ElMessage.success('已删除')
    fetchRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const alertTypeMap: Record<string, string> = {
  price_above: '价格上穿',
  price_below: '价格下穿',
  change_above: '涨幅超过',
  change_below: '跌幅超过',
  volume_above: '成交量突破',
}

const formatAlertType = (type: string) => alertTypeMap[type] || type

onMounted(() => {
  fetchRules()
})
</script>

<template>
  <div class="alerts-view">
    <el-card>
      <el-tabs v-model="activeTab" @tab-change="(tab: string) => tab === 'history' && fetchHistory()">
        <!-- 预警规则 -->
        <el-tab-pane label="预警规则" name="rules">
          <template #label>
            <span><el-icon><Bell /></el-icon> 预警规则</span>
          </template>

          <div class="tab-header">
            <el-button type="primary" :icon="Plus">新建规则</el-button>
          </div>

          <el-table v-loading="loading" :data="rules" style="width: 100%">
            <el-table-column prop="stock_code" label="股票代码" width="100" />
            <el-table-column prop="stock_name" label="股票名称" width="120" />
            <el-table-column label="预警类型" width="120">
              <template #default="{ row }">
                {{ formatAlertType(row.alert_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="threshold" label="阈值" width="100" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.created_at).toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button
                  type="danger"
                  :icon="Delete"
                  circle
                  size="small"
                  @click="deleteRule(row)"
                />
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && rules.length === 0" description="暂无预警规则" />
        </el-tab-pane>

        <!-- 预警历史 -->
        <el-tab-pane label="预警历史" name="history">
          <template #label>
            <span><el-icon><Clock /></el-icon> 预警历史</span>
          </template>

          <el-table v-loading="loading" :data="history" style="width: 100%">
            <el-table-column prop="stock_code" label="股票代码" width="100" />
            <el-table-column label="预警类型" width="120">
              <template #default="{ row }">
                {{ formatAlertType(row.alert_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="message" label="预警信息" />
            <el-table-column label="触发时间" width="180">
              <template #default="{ row }">
                {{ new Date(row.triggered_at).toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && history.length === 0" description="暂无预警记录" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.tab-header {
  margin-bottom: 16px;
}
</style>

