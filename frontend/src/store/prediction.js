import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const usePredictionStore = defineStore('prediction', {
  state: () => ({
    cachedAt: null,
    // 筛选
    selectedCategory: '',
    orderBy: 'play_count',
    searchKeyword: '',
    // 列表
    videos: [],
    totalVideos: 0,
    currentPage: 1,
    categoryOptions: [],
    // 模型
    modelInfo: { predictor: {}, recommender: {} },
    // 分析结果
    selectedVideo: null,
    predictionResult: null,
    recommendResult: null,
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
