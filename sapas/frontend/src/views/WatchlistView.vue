<template>
  <div class="watchlist-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>自选股</span>
          <el-button type="primary" :icon="Plus" @click="showAddDialog = true">添加股票</el-button>
        </div>
      </template>

      <div class="watchlist-content">
        <!-- 分组标签 -->
        <el-tabs v-model="activeGroupId" @tab-change="handleGroupChange">
          <el-tab-pane
            v-for="group in groups"
            :key="group.id"
            :label="group.name"
            :name="String(group.id)"
          >
            <el-table :data="items" style="width: 100%" v-loading="loading">
              <el-table-column prop="stockCode" label="代码" width="100" />
              <el-table-column prop="stockName" label="名称" width="120" />
              <el-table-column prop="currentPrice" label="现价" width="100" align="right">
                <template #default="{ row }">
                  <span :class="getPriceColorClass(row.changePct)">
                    {{ row.currentPrice?.toFixed(2) || '-' }}
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
              <el-table-column prop="peTtm" label="市盈率" width="100" align="right" />
              <el-table-column prop="marketValue" label="总市值" width="120" align="right">
                <template #default="{ row }">
                  {{ formatAmount(row.marketValue) }}
                </template>
              </el-table-column>
              <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
              <el-table-column label="操作" width="150" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link @click="editItem(row)">编辑</el-button>
                  <el-button type="danger" link @click="deleteItem(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>

        <el-empty v-if="!loading && items.length === 0" description="暂无自选股" />
      </div>
    </el-card>

    <!-- 添加股票对话框 -->
    <el-dialog v-model="showAddDialog" title="添加股票" width="500px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="股票代码">
          <el-input
            v-model="addForm.stockCodes"
            placeholder="多个代码用逗号分隔，如：000001,600000"
          />
        </el-form-item>
        <el-form-item label="添加到">
          <el-select v-model="addForm.groupId" style="width: 100%">
            <el-option
              v-for="group in groups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑自选股" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="备注">
          <el-input
            v-model="editForm.note"
            type="textarea"
            :rows="3"
            placeholder="输入备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '@/api'
import { formatPercent, formatAmount, getPriceColorClass } from '@/utils'

const loading = ref(false)
const adding = ref(false)
const activeGroupId = ref('0')
const groups = ref([])
const items = ref([])

const showAddDialog = ref(false)
const showEditDialog = ref(false)

const addForm = reactive({
  stockCodes: '',
  groupId: 0
})

const editForm = reactive({
  id: 0,
  note: ''
})

onMounted(() => {
  loadGroups()
})

async function loadGroups() {
  loading.value = true
  try {
    const result = await api.getGroups()
    groups.value = result.data || []
    if (groups.value.length > 0) {
      activeGroupId.value = String(groups.value[0].id)
      addForm.groupId = groups.value[0].id
      loadItems()
    }
  } catch (error) {
    ElMessage.error('加载分组失败')
  } finally {
    loading.value = false
  }
}

function handleGroupChange() {
  loadItems()
}

async function loadItems() {
  const groupId = parseInt(activeGroupId.value)
  loading.value = true
  try {
    const result = await api.getItems(groupId)
    items.value = result.data || []
  } catch (error) {
    ElMessage.error('加载自选股失败')
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  if (!addForm.stockCodes.trim()) {
    ElMessage.warning('请输入股票代码')
    return
  }

  const codes = addForm.stockCodes.split(/[，,]/).map(c => c.trim()).filter(c => c)

  adding.value = true
  try {
    await api.addItem(codes)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.stockCodes = ''
    loadItems()
  } catch (error: any) {
    ElMessage.error(error.message || '添加失败')
  } finally {
    adding.value = false
  }
}

function editItem(row: any) {
  editForm.id = row.id
  editForm.note = row.note || ''
  showEditDialog.value = true
}

async function handleEdit() {
  try {
    await api.updateItem(editForm.id, { note: editForm.note })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    loadItems()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

async function deleteItem(id: number) {
  try {
    await ElMessageBox.confirm('确定要删除这只自选股吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.deleteItem(id)
    ElMessage.success('删除成功')
    loadItems()
  } catch (error) {
    // 用户取消
  }
}
</script>

<style scoped lang="scss">
.watchlist-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .watchlist-content {
    min-height: 300px;
  }
}
</style>
