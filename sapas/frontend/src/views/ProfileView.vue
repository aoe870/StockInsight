<template>
  <div class="profile-view">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>个人信息</span>
          </template>
          <div class="profile-info">
            <div class="avatar-section">
              <el-avatar :size="80" :icon="UserFilled" />
              <div class="user-basic">
                <div class="username">{{ user?.username }}</div>
                <div class="role-badge">{{ getRoleName(user?.role) }}</div>
              </div>
            </div>
            <el-divider />
            <el-descriptions :column="1" border>
              <el-descriptions-item label="用户ID">{{ user?.id }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ user?.email || '-' }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ user?.phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="注册时间">{{ formatDate(user?.createdAt) }}</el-descriptions-item>
              <el-descriptions-item label="最后登录">{{ formatDateTime(user?.lastLoginAt) }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="user?.isActive ? 'success' : 'danger'">
                  {{ user?.isActive ? '正常' : '禁用' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <span>修改密码</span>
          </template>
          <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="100px" style="max-width: 500px">
            <el-form-item label="当前密码" prop="oldPassword">
              <el-input
                v-model="passwordForm.oldPassword"
                type="password"
                placeholder="请输入当前密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                placeholder="请输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="changing" @click="handleChangePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card style="margin-top: 20px">
          <template #header>
            <span>使用统计</span>
          </template>
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon">
                  <el-icon><Star /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ stats.watchlistCount }}</div>
                  <div class="stat-label">自选股</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon warning">
                  <el-icon><Bell /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ stats.alertCount }}</div>
                  <div class="stat-label">预警规则</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon success">
                  <el-icon><DataAnalysis /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ stats.backtestCount }}</div>
                  <div class="stat-label">回测记录</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-icon danger">
                  <el-icon><TrendCharts /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ stats.screenerCount }}</div>
                  <div class="stat-label">选股条件</div>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { UserFilled, Star, Bell, DataAnalysis, TrendCharts } from '@element-plus/icons-vue'
import { formatDate, formatDateTime } from '@/utils'

const authStore = useAuthStore()

const user = computed(() => authStore.user)
const passwordFormRef = ref<FormInstance>()
const changing = ref(false)

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const stats = ref({
  watchlistCount: 0,
  alertCount: 0,
  backtestCount: 0,
  screenerCount: 0
})

const validateConfirmPassword = (_rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入新密码'))
  } else if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度为 6-32 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

onMounted(() => {
  loadProfile()
  loadStats()
})

async function loadProfile() {
  try {
    const result = await authStore.getProfile()
    authStore.setUser(result.data)
  } catch (error) {
    console.error('加载用户信息失败', error)
  }
}

async function loadStats() {
  // 加载用户统计数据
  stats.value = {
    watchlistCount: 12,
    alertCount: 5,
    backtestCount: 8,
    screenerCount: 3
  }
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    changing.value = true
    try {
      await authStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
      ElMessage.success('密码修改成功')
      // 清空表单
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
      passwordFormRef.value?.resetFields()
    } catch (error: any) {
      ElMessage.error(error.message || '密码修改失败')
    } finally {
      changing.value = false
    }
  })
}

function getRoleName(role?: string): string {
  const map: Record<string, string> = {
    admin: '管理员',
    user: '普通用户',
    vip: 'VIP用户'
  }
  return map[role || ''] || '普通用户'
}
</script>

<style scoped lang="scss">
.profile-view {
  .profile-info {
    .avatar-section {
      display: flex;
      align-items: center;
      gap: 20px;
      padding: 0 20px;

      .user-basic {
        .username {
          font-size: 18px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 4px;
        }

        .role-badge {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }

  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;
    background: #f5f7fa;
    border-radius: 8px;
    transition: all 0.3s;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #e6f7ff;
      color: #1890ff;
      margin-right: 16px;

      .el-icon {
        font-size: 24px;
      }

      &.warning {
        background: #fffbe6;
        color: #faad14;
      }

      &.success {
        background: #f6ffed;
        color: #52c41a;
      }

      &.danger {
        background: #fff1f0;
        color: #ff4d4f;
      }
    }

    .stat-info {
      flex: 1;

      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
        line-height: 1.2;
        margin-bottom: 4px;
      }

      .stat-label {
        font-size: 14px;
        color: #909399;
      }
    }
  }
}
</style>
