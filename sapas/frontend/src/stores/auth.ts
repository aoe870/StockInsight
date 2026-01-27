/**
 * 认证状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'

interface AuthState {
  user: any | null
  token: string | null
  isLoggedIn: boolean
  isLoading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: localStorage.getItem('access_token') || null,
    isLoggedIn: !!localStorage.getItem('access_token'),
    isLoading: false
  }),

  getters: {
    currentUser: (state) => computed(() => state.user),
    isAuthenticated: (state) => computed(() => !!state.token && !!state.user),
    hasRole: (state) => (role: string) => computed(() => {
      if (!state.user) return false
      return state.user.role === role
    })
  },

  actions: {
    setUser(state, user: any) {
      state.user = user
    },

    setToken(state, token: string) {
      state.token = token
      state.isLoggedIn = !!token
      if (token) {
        localStorage.setItem('access_token', token)
      } else {
        localStorage.removeItem('access_token')
      }
    },

    clearAuth(state) {
      state.user = null
      state.token = null
      state.isLoggedIn = false
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },

    setLoading(state, loading: boolean) {
      state.isLoading = loading
    },

    async login(username: string, password: string) {
      this.setLoading(true)
      try {
        const result = await api.login(username, password)
        if (result.data?.access_token) {
          this.setToken(result.data.access_token)
          await this.getProfile()
        }
        return result
      } finally {
        this.setLoading(false)
      }
    },

    async register(username: string, password: string, email?: string) {
      this.setLoading(true)
      try {
        const result = await api.register(username, password, email)
        return result
      } finally {
        this.setLoading(false)
      }
    },

    async logout() {
      try {
        await api.logout()
      } finally {
        this.clearAuth()
      }
    },

    async getProfile() {
      this.setLoading(true)
      try {
        const result = await api.getProfile()
        if (result.data) {
          this.setUser(result.data)
        }
        return result
      } finally {
        this.setLoading(false)
      }
    },

    async changePassword(oldPassword: string, newPassword: string) {
      this.setLoading(true)
      try {
        const result = await api.post('/auth/change-password', {
          old_password: oldPassword,
          new_password: newPassword
        })
        return result
      } finally {
        this.setLoading(false)
      }
    }
  }
})

export default useAuthStore
