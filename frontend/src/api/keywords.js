/**
 * 热词分析 API 模块
 */
import api from './index'

/**
 * 获取热词概览统计
 * @param {Object} params - 查询参数
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {string} params.category - 分区筛选
 * @param {string} params.source - 来源筛选 (title/comment/danmaku)
 */
export const getKeywordOverview = (params) => {
  return api.get('/keywords/overview', { params })
}

/**
 * 获取热词词云数据
 * @param {Object} params - 查询参数
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {string} params.category - 分区筛选
 * @param {string} params.source - 来源筛选 (title/comment/danmaku)
 * @param {number} params.top_k - 返回数量 (默认100)
 */
export const getKeywordWordcloud = (params) => {
  return api.get('/keywords/wordcloud', { params })
}

/**
 * 获取热词排行榜
 * @param {Object} params - 查询参数
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {string} params.category - 分区筛选
 * @param {string} params.source - 来源筛选 (title/comment/danmaku)
 * @param {string} params.order_by - 排序方式 (frequency/trend/heat)
 * @param {string} params.search - 搜索关键词
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 */
export const getKeywordRanking = (params) => {
  return api.get('/keywords/ranking', { params })
}

/**
 * 获取热词异动榜
 * @param {Object} params - 查询参数
 */
export const getKeywordMovers = (params) => {
  return api.get('/keywords/movers', { params })
}

/**
 * 获取热词机会榜/风险榜
 * @param {Object} params - 查询参数
 */
export const getKeywordOpportunityRisk = (params) => {
  return api.get('/keywords/opportunity-risk', { params })
}

/**
 * 获取热词详情
 * @param {string} word - 热词
 * @param {Object} params - 查询参数
 * @param {number} params.days - 趋势天数 (默认7)
 * @param {string} params.category - 分区筛选
 */
export const getKeywordDetail = (word, params = {}) => {
  return api.get(`/keywords/${encodeURIComponent(word)}/detail`, { params })
}

/**
 * 获取热词贡献视频
 * @param {string} word - 热词
 * @param {Object} params - 查询参数
 */
export const getKeywordContributors = (word, params = {}) => {
  return api.get(`/keywords/${encodeURIComponent(word)}/contributors`, { params })
}

/**
 * 热词趋势对比
 * @param {Object} data - 请求数据
 * @param {string[]} data.words - 热词列表 (最多5个)
 * @param {number} data.days - 天数 (默认7)
 * @param {string} data.category - 分区筛选
 */
export const compareKeywords = (data) => {
  return api.post('/keywords/compare', data)
}

/**
 * 分区热词对比
 * @param {Object} params - 查询参数
 * @param {string} params.stat_date - 统计日期 (YYYY-MM-DD)
 * @param {number} params.top_k - 每分区返回热词数 (默认10)
 */
export const getCategoryCompare = (params) => {
  return api.get('/keywords/category-compare', { params })
}

/**
 * 获取预警订阅配置
 */
export const getKeywordAlertSubscription = () => {
  return api.get('/keywords/alerts/subscription')
}

/**
 * 更新预警订阅配置
 * @param {Object} data - 配置数据
 */
export const updateKeywordAlertSubscription = (data) => {
  return api.put('/keywords/alerts/subscription', data)
}

/**
 * 获取预警命中
 * @param {Object} params - 查询参数
 */
export const getKeywordAlertHits = (params) => {
  return api.get('/keywords/alerts/hits', { params })
}

/**
 * 获取热词导出URL
 * @param {Object} params - 查询参数
 * @param {string} params.format - 导出格式 (csv/json)
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {string} params.category - 分区筛选
 * @param {string} params.source - 来源筛选
 * @param {number} params.top_k - 导出数量
 */
export const getExportUrl = (params) => {
  const queryParams = new URLSearchParams()

  if (params.format) queryParams.append('format', params.format)
  if (params.start_date) queryParams.append('start_date', params.start_date)
  if (params.end_date) queryParams.append('end_date', params.end_date)
  if (params.category) queryParams.append('category', params.category)
  if (params.source) queryParams.append('source', params.source)
  if (params.top_k) queryParams.append('top_k', params.top_k)

  const queryString = queryParams.toString()
  const baseUrl = '/api/keywords/export'
  return queryString ? `${baseUrl}?${queryString}` : baseUrl
}

/**
 * 导出热词数据（通过API直接下载）
 * @param {Object} params - 查询参数
 */
export const exportKeywords = (params) => {
  return api.get('/keywords/export', {
    params,
    responseType: params.format === 'csv' ? 'blob' : 'json'
  })
}
