import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { isAuthenticated } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    redirect: '/market',
  },
  {
    path: '/market',
    name: 'Market',
    component: () => import('@/views/MarketView.vue'),
    meta: { title: '行情中心' },
  },
  {
    path: '/screener',
    name: 'Screener',
    component: () => import('@/views/ScreenerView.vue'),
    meta: { title: '指标选股' },
  },
  {
    path: '/watchlist',
    name: 'Watchlist',
    component: () => import('@/views/WatchlistView.vue'),
    meta: { title: '自选股' },
  },
  {
    path: '/alerts',
    name: 'Alerts',
    component: () => import('@/views/AlertsView.vue'),
    meta: { title: '预警中心' },
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('@/views/BacktestView.vue'),
    meta: { title: '策略回测' },
  },
  {
    path: '/call-auction',
    name: 'CallAuction',
    component: () => import('@/views/CallAuctionView.vue'),
    meta: { title: '集合竞价' },
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: () => import('@/views/StockDetailView.vue'),
    meta: { title: '股票详情' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'SAPAS'} - 股票分析系统`

  // 检查是否需要登录
  const isPublic = to.meta.public === true

  if (!isPublic && !isAuthenticated.value) {
    // 需要登录但未登录，跳转登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && isAuthenticated.value) {
    // 已登录访问登录页，跳转首页
    next('/')
  } else {
    next()
  }
})

export default router

