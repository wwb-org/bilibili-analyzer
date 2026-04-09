import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useHomeStore = defineStore('home', {
  state: () => ({
    cachedAt: null,
    overview: null,
    scatter: [],
    trendVideos: [],
    trendIsFallback: false,
    lifecycle: [],
    categories: [],
    sentiment: null,
    sentimentTrend: [],
    keywords: [],
    heatmap: [],
    opportunities: [],
    authors: [],
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
    ageMinutes: (state) =>
      state.cachedAt ? Math.floor((Date.now() - state.cachedAt) / 60000) : null,
  },
})
