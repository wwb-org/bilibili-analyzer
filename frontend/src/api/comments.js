/**
 * 评论分析 API 模块
 */
import api from './index'

/**
 * 获取视频列表（含评论统计摘要）
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.category - 分区筛选
 * @param {string} params.keyword - 关键词搜索
 * @param {string} params.order_by - 排序方式 (comment_count|positive_count|negative_count)
 */
export const getVideosWithComments = (params) => {
  return api.get('/comments/videos', { params })
}

/**
 * 获取单视频评论统计
 * @param {string} bvid - 视频 BV 号
 */
export const getCommentStats = (bvid) => {
  return api.get(`/comments/${bvid}/stats`)
}

/**
 * 获取单视频评论列表
 * @param {string} bvid - 视频 BV 号
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.sentiment - 情感筛选 (positive|neutral|negative)
 * @param {string} params.emotion - 细粒度情绪筛选 (GoEmotions 28类，如 joy|anger|sadness|surprise|neutral 等)
 * @param {string} params.sort_by - 排序方式 (like_count|created_at|sentiment_score)
 */
export const getCommentList = (bvid, params) => {
  return api.get(`/comments/${bvid}/list`, { params })
}

/**
 * 获取单视频评论词云
 * @param {string} bvid - 视频 BV 号
 * @param {Object} params - 查询参数
 * @param {number} params.top_k - 返回词数
 * @param {string} params.sentiment - 三分类情感筛选
 * @param {string} params.emotion - 细粒度情绪筛选
 */
export const getCommentWordcloud = (bvid, params) => {
  return api.get(`/comments/${bvid}/wordcloud`, { params })
}

/**
 * 获取单视频高赞评论TOP
 * @param {string} bvid - 视频 BV 号
 * @param {number} limit - 返回数量
 */
export const getTopComments = (bvid, limit = 10) => {
  return api.get(`/comments/${bvid}/top`, { params: { limit } })
}

/**
 * 多视频评论对比
 * @param {string[]} bvids - 视频 BV 号数组（2-5个）
 */
export const compareComments = (bvids) => {
  return api.post('/comments/compare', { bvids })
}

/**
 * 获取评论导出URL
 * @param {string} bvid - 视频 BV 号
 * @param {string} sentiment - 三分类情感筛选
 * @param {string} emotion - 细粒度情绪筛选
 */
export const getCommentExportUrl = (bvid, sentiment, emotion) => {
  const baseUrl = api.defaults.baseURL || ''
  const params = new URLSearchParams()
  params.append('bvid', bvid)
  if (sentiment) params.append('sentiment', sentiment)
  if (emotion) params.append('emotion', emotion)
  return `${baseUrl}/comments/export/csv?${params.toString()}`
}
