import { defineStore } from 'pinia'

const CACHE_TTL = 60 * 60 * 1000 // 1 小时

export const useCommentsStore = defineStore('comments', {
  state: () => ({
    cachedAt: null,
    // 筛选
    analysisMode: 'single',
    selectedCategory: '',
    orderBy: 'comment_count',
    searchKeyword: '',
    // 视频列表
    videos: [],
    totalVideos: 0,
    currentPage: 1,
    categoryOptions: [],
    // 单视频分析结果
    selectedVideo: null,
    commentStats: null,
    audienceProfile: null,
    topComments: [],
    wordcloudData: [],
    commentList: [],
    commentTotal: 0,
    commentPage: 1,
    commentSentimentFilter: '',
    commentEmotionFilter: '',
    commentSortBy: 'like_count',
    // 对比
    compareResult: null,
    selectedBvids: [],
  }),

  getters: {
    isFresh: (state) =>
      !!state.cachedAt && Date.now() - state.cachedAt < CACHE_TTL,
  },
})
