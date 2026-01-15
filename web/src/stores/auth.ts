/**
 * 认证状态管理
 */
import { ref, computed } from 'vue'

// 用户信息接口
export interface UserInfo {
  id: string
  username: string
  email: string | null
  nickname: string | null
  avatar: string | null
  role: string
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

// Token 存储键
const TOKEN_KEY = 'sapas_token'
const USER_KEY = 'sapas_user'

// 状态
const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
const user = ref<UserInfo | null>(null)

// 初始化时加载用户信息
const savedUser = localStorage.getItem(USER_KEY)
if (savedUser) {
  try {
    user.value = JSON.parse(savedUser)
  } catch (e) {
    console.error('Failed to parse user info:', e)
  }
}

// 计算属性
export const isAuthenticated = computed(() => !!token.value)
export const currentUser = computed(() => user.value)
export const isAdmin = computed(() => user.value?.role === 'admin')

// 获取 Token
export function getToken(): string | null {
  return token.value
}

// 设置认证信息
export function setAuth(accessToken: string, userInfo: UserInfo) {
  token.value = accessToken
  user.value = userInfo
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

// 清除认证信息
export function clearAuth() {
  token.value = null
  user.value = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// 更新用户信息
export function updateUser(userInfo: UserInfo) {
  user.value = userInfo
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

