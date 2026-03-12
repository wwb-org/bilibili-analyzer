import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useAdminStore = defineStore('admin', {
  state: () => ({
    cachedAt: null,
    redisStatus: false,
    kafkaStatus: false,
    bilibiliStatus: {
      configured: false,
      valid: false,
      logged_in: false,
      username: '',
      message: ''
    },
    etlStatus: { is_running: false, jobs: [] },
    crawlLogs: [],
    users: [],
    modelInfo: { predictor: {}, recommender: {} },
    dataOverview: null,
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
