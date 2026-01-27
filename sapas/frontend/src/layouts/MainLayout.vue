<template>
  <div class="main-layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '200px'" class="aside">
        <div class="logo">
          <span v-if="!isCollapse">SAPAS</span>
          <span v-else>S</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :router="true"
          class="sidebar-menu"
        >
          <el-menu-item index="/market">
            <el-icon><TrendCharts /></el-icon>
            <template #title>行情中心</template>
          </el-menu-item>
          <el-menu-item index="/watchlist">
            <el-icon><Star /></el-icon>
            <template #title>自选股</template>
          </el-menu-item>
          <el-menu-item index="/screener">
            <el-icon><Filter /></el-icon>
            <template #title>选股器</template>
          </el-menu-item>
          <el-menu-item index="/alerts">
            <el-icon><Bell /></el-icon>
            <template #title>预警管理</template>
          </el-menu-item>
          <el-menu-item index="/backtest">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>策略回测</template>
          </el-menu-item>
          <el-menu-item index="/call-auction">
            <el-icon><Odometer /></el-icon>
            <template #title>集合竞价</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主体内容 -->
      <el-container>
        <!-- 顶部栏 -->
        <el-header class="header">
          <div class="header-left">
            <el-button
              text
              @click="toggleCollapse"
              class="collapse-btn"
            >
              <el-icon :size="20">
                <component :is="isCollapse ? 'Expand' : 'Fold'" />
              </el-icon>
            </el-button>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
                {{ item.title }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <el-button text @click="refreshData">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-dropdown @command="handleCommand">
              <div class="user-dropdown">
                <el-avatar :size="32" :icon="UserFilled" />
                <span class="username">{{ authStore.user?.username }}</span>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="settings">系统设置</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <!-- 内容区域 -->
        <el-main class="main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  TrendCharts, Star, Filter, Bell, DataAnalysis, Odometer,
  Expand, Fold, Refresh, UserFilled, ArrowDown
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapse = ref(false)

const activeMenu = computed(() => route.path)

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta && item.meta.title)
  return matched.map(item => ({
    path: item.path,
    title: (item.meta?.title as string) || ''
  }))
})

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}

function refreshData() {
  window.location.reload()
}

async function handleCommand(command: string) {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        authStore.clearAuth()
        router.push('/login')
      } catch {
        // 取消操作
      }
      break
  }
}

// 为路由添加标题
watch(() => route.path, () => {
  document.title = `${route.meta?.title || 'SAPAS'} - 股票分析平台`
}, { immediate: true })
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
  overflow: hidden;

  .el-container {
    height: 100%;
  }
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow-x: hidden;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: bold;
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .sidebar-menu {
    border: none;
    background-color: #304156;

    :deep(.el-menu-item) {
      color: #bfcbd9;

      &:hover {
        background-color: #263445;
      }

      &.is-active {
        color: #409eff;
        background-color: #1f2d3d;
      }
    }

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      .el-icon {
        margin-right: 12px;
      }
    }
  }
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      padding: 8px;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .user-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: background-color 0.3s;

      &:hover {
        background-color: #f5f7fa;
      }

      .username {
        font-size: 14px;
        color: #606266;
      }
    }
  }
}

.main {
  background-color: #f5f7fa;
  overflow: auto;
  padding: 20px;
}
</style>
