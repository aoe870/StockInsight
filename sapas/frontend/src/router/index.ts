/**
 * 路由配置
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/market'
      },
      {
        path: 'market',
        name: 'Market',
        component: () => import('@/views/MarketView.vue')
      },
      {
        path: 'stock/:code',
        name: 'StockDetail',
        component: () => import('@/views/StockDetailView.vue')
      },
      {
        path: 'watchlist',
        name: 'Watchlist',
        component: () => import('@/views/WatchlistView.vue')
      },
      {
        path: 'screener',
        name: 'Screener',
        component: () => import('@/views/ScreenerView.vue')
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/AlertsView.vue')
      },
      {
        path: 'backtest',
        name: 'Backtest',
        component: () => import('@/views/BacktestView.vue')
      },
      {
        path: 'call-auction',
        name: 'CallAuction',
        component: () => import('@/views/CallAuctionView.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/ProfileView.vue')
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 验证认证状态
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth && !authStore.isAuthenticated.value) {
    // 需要认证但未登录，重定向到登录页
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && authStore.isAuthenticated.value) {
    // 已登录用户访问登录/注册页，重定向到首页
    next('/market')
  } else {
    next()
  }
})

export default router
