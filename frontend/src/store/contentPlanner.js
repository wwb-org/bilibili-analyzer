import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useContentPlannerStore = defineStore('contentPlanner', {
  state: () => ({
    cachedAt: null,
    selectedCategory: '',
    categories: [],
    analysisReady: false,
    features: {},
    keywords: [],
    suggestions: [],
    inputTitle: '',
    scoreResult: null,
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
