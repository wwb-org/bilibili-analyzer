/**
 * 机器学习预测 API 模块
 */
import api from './index'

/**
 * 根据 BVID 预测视频热度
 * @param {string} bvid - 视频 BV 号
 */
export const predictByBvid = (bvid) => {
  return api.post('/ml/predict/bvid', { bvid })
}

/**
 * 根据参数预测视频热度（手动输入模式）
 * @param {Object} params - 视频参数
 * @param {number} params.play_count - 当前播放量
 * @param {number} params.like_count - 点赞数
 * @param {number} params.coin_count - 投币数
 * @param {number} params.favorite_count - 收藏数
 * @param {number} params.share_count - 分享数
 * @param {number} params.danmaku_count - 弹幕数
 * @param {number} params.comment_count - 评论数
 * @param {string} params.category - 分区
 * @param {number} params.publish_hour - 发布小时
 * @param {number} params.publish_weekday - 发布星期
 * @param {number} params.video_age_days - 视频发布天数
 * @param {number} params.title_length - 标题长度
 * @param {number} params.duration_minutes - 视频时长(分钟)
 */
export const predictByParams = (params) => {
  return api.post('/ml/predict/params', params)
}

/**
 * 获取相似视频推荐
 * @param {string} bvid - 目标视频 BV 号
 * @param {Object} options - 推荐选项
 * @param {number} options.top_k - 返回数量
 * @param {boolean} options.same_category - 是否优先同分区
 * @param {boolean} options.same_author - 是否包含同作者
 */
export const getRecommendations = (bvid, options = {}) => {
  const params = {
    top_k: options.top_k || 10,
    same_category: options.same_category !== false,
    same_author: options.same_author || false
  }
  return api.get(`/ml/recommend/${bvid}`, { params })
}

/**
 * 获取模型状态信息
 */
export const getModelInfo = () => {
  return api.get('/ml/model-info')
}

/**
 * 训练热度预测模型（管理员）
 */
export const trainPredictor = () => {
  return api.post('/ml/train/predictor')
}

/**
 * 训练推荐模型（管理员）
 */
export const trainRecommender = () => {
  return api.post('/ml/train/recommender')
}

/**
 * 训练所有模型（管理员）
 */
export const trainAllModels = () => {
  return api.post('/ml/train/all')
}
