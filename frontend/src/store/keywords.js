import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useKeywordsStore = defineStore('keywords', {
  state: () => ({
    cachedAt: null,
    filterKey: '',
    overview: null,
    wordcloudData: [],
    rankingData: [],
    rankingTotal: 0,
    movers: { rising: [], falling: [], previous_date: null },
    opportunityRisk: { opportunities: [], risks: [] },
    categoryCompareData: [],
    suggestionsData: [],
    categoryOptions: [],
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
