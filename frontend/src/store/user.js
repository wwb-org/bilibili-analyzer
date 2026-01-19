import { defineStore } from 'pinia'
import { getProfile } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null,
    isLoggedIn: false
  }),

  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
    username: (state) => state.user?.username || ''
  },

  actions: {
    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    },

    async fetchUser() {
      if (!this.token) return false
      try {
        const user = await getProfile()
        this.user = user
        this.isLoggedIn = true
        return true
      } catch (error) {
        this.logout()
        return false
      }
    },

    logout() {
      this.token = ''
      this.user = null
      this.isLoggedIn = false
      localStorage.removeItem('token')
    },

    async checkAuth() {
      if (!this.token) return false
      if (this.user) return true
      return await this.fetchUser()
    }
  }
})
