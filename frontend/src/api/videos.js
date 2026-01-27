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
 * @param {string} params.order_by - 排序方式 (play_count|like_count|publish_time)
 */
export const getVideos = (params) => {
  return api.get('/videos', { params })
}

/**
 * 获取视频详情
 * @param {string} bvid - 视频 BV 号
 */
export const getVideoDetail = (bvid) => {
  return api.get(`/videos/${bvid}`)
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
