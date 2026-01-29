/**
 * 视频数据 API 模块
 */
import api from './index'

/**
 * 获取视频列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.keyword - 关键词搜索
 * @param {string} params.category - 分区筛选
 * @param {string} params.order_by - 排序方式 (play_count|like_count|publish_time|coin_count|comment_count|danmaku_count|favorite_count|interaction_rate)
 * @param {string} params.start_date - 开始日期 (ISO格式)
 * @param {string} params.end_date - 结束日期 (ISO格式)
 */
export const getVideos = (params) => {
  return api.get('/videos', { params })
}

/**
 * 获取视频统计数据（根据筛选条件）
 * @param {Object} params - 查询参数
 * @param {string} params.category - 分区筛选
 * @param {string} params.keyword - 关键词搜索
 * @param {string} params.start_date - 开始日期 (ISO格式)
 * @param {string} params.end_date - 结束日期 (ISO格式)
 */
export const getVideosStats = (params) => {
  return api.get('/videos/stats', { params })
}

/**
 * 获取所有分区列表（数据库中存在的分区）
 */
export const getCategories = () => {
  return api.get('/videos/categories')
}

/**
 * 获取视频详情
 * @param {string} bvid - 视频 BV 号
 */
export const getVideoDetail = (bvid) => {
  return api.get(`/videos/${bvid}`)
}

/**
 * 获取视频分析数据（互动率、情感分布、弹幕词云）
 * @param {string} bvid - 视频 BV 号
 */
export const getVideoAnalysis = (bvid) => {
  return api.get(`/videos/${bvid}/analysis`)
}

/**
 * 获取视频评论列表
 * @param {string} bvid - 视频 BV 号
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.sort_by - 排序方式 (like_count|created_at)
 */
export const getVideoComments = (bvid, params) => {
  return api.get(`/videos/${bvid}/comments`, { params })
}

/**
 * 获取视频弹幕列表
 * @param {string} bvid - 视频 BV 号
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 */
export const getVideoDanmakus = (bvid, params) => {
  return api.get(`/videos/${bvid}/danmakus`, { params })
}

/**
 * 多视频对比
 * @param {string[]} bvids - 视频 BV 号数组（最多5个）
 */
export const compareVideos = (bvids) => {
  return api.post('/videos/compare', { bvids })
}

/**
 * 导出视频数据为CSV
 * @param {Object} params - 查询参数（同getVideos）
 * @returns {string} CSV下载URL
 */
export const getExportUrl = (params) => {
  const baseUrl = api.defaults.baseURL || ''
  const queryParams = new URLSearchParams()

  if (params.category) queryParams.append('category', params.category)
  if (params.keyword) queryParams.append('keyword', params.keyword)
  if (params.start_date) queryParams.append('start_date', params.start_date)
  if (params.end_date) queryParams.append('end_date', params.end_date)
  if (params.order_by) queryParams.append('order_by', params.order_by)

  const queryString = queryParams.toString()
  return `${baseUrl}/videos/export/csv${queryString ? '?' + queryString : ''}`
}
