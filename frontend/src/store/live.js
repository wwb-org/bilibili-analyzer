import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useLiveStore = defineStore('live', {
  state: () => ({
    cachedAt: null,
    popularRooms: [],
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
