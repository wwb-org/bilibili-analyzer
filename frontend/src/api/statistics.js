import api from './index'

// ====== 原始表接口 ======
export const getOverview = () => api.get('/statistics/overview')
export const getTrends = (days = 7, metric = 'play_count') =>
  api.get('/statistics/trends', { params: { days, metric } })
export const getCategories = () => api.get('/statistics/categories')
export const getTopVideos = (limit = 10) =>
  api.get('/statistics/top-videos', { params: { limit } })
export const getSentiment = () => api.get('/statistics/sentiment')
export const getKeywords = (limit = 80) =>
  api.get('/statistics/keywords', { params: { limit } })
export const getPublishHeatmap = () => api.get('/statistics/publish-heatmap')
export const getVideoScatter = (limit = 300) =>
  api.get('/statistics/video-scatter', { params: { limit } })

// ====== 数仓优化接口 ======
export const getDwOverview = () => api.get('/statistics/dw/overview')
export const getDwTrends = (days = 7, metric = 'play_count') =>
  api.get('/statistics/dw/trends', { params: { days, metric } })
export const getDwCategories = () => api.get('/statistics/dw/categories')
export const getDwSentiment = () => api.get('/statistics/dw/sentiment')
export const getDwSentimentTrends = (days = 14) =>
  api.get('/statistics/dw/sentiment-trends', { params: { days } })
export const getDwVideoTrends = (limit = 10, orderBy = 'heat_score') =>
  api.get('/statistics/dw/video-trends', { params: { limit, order_by: orderBy } })

// ====== 新增特色分析接口 ======
export const getLifecycle = () => api.get('/statistics/lifecycle')
export const getOpportunities = (limit = 10) =>
  api.get('/statistics/opportunities', { params: { limit } })
export const getAuthorRanking = (limit = 12) =>
  api.get('/statistics/author-ranking', { params: { limit } })
export const getCrawlTrends = (days = 14) =>
  api.get('/statistics/crawl-trends', { params: { days } })
