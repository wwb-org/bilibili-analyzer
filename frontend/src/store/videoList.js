import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useVideoListStore = defineStore('videoList', {
  state: () => ({
    cachedAt: null,
    // 筛选
    keyword: '',
    category: '',
    orderBy: 'play_count',
    dateRange: null,
    // 列表
    videos: [],
    totalVideos: 0,
    currentPage: 1,
    pageSize: 20,
    // 统计 & 分区
    categoryOptions: [],
    statsData: {
      total_videos: 0,
      total_play_count: 0,
      avg_play_count: 0,
      avg_interaction_rate: 0,
      sentiment_distribution: { positive: 0, neutral: 0, negative: 0 },
      category_distribution: [],
    },
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
