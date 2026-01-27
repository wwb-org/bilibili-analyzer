import api from './index'

/**
 * WebSocket 连接地址配置
 * 开发环境和生产环境自动切换
 */
export const LIVE_WS_URL = import.meta.env.DEV
  ? 'ws://localhost:8000/api/live/ws'
  : `ws://${window.location.host}/api/live/ws`

/**
 * 获取活跃直播间列表
 * @returns {Promise} 直播间列表
 */
export const getLiveRooms = () => {
  return api.get('/live/rooms')
}

/**
 * 获取直播间连接状态
 * @param {number|string} roomId - 直播间ID
 * @returns {Promise} 直播间状态信息
 */
export const getRoomStatus = (roomId) => {
  return api.get(`/live/rooms/${roomId}/status`)
}

// ==================== 多房间统计 API ====================

/**
 * 获取所有活跃房间的统计数据
 * @returns {Promise} { source: 'spark'|'memory', rooms: [...] }
 */
export const getMultiRoomStats = () => {
  return api.get('/live/multi/stats')
}

/**
 * 获取单个房间的历史统计数据（趋势图用）
 * @param {number|string} roomId - 直播间ID
 * @param {number} limit - 返回记录数量
 * @returns {Promise} { room_id, history: [...] }
 */
export const getRoomStatsHistory = (roomId, limit = 50) => {
  return api.get(`/live/multi/stats/${roomId}/history`, { params: { limit } })
}

/**
 * 获取全局热词（跨房间聚合）
 * @returns {Promise} { source, data: [...] }
 */
export const getGlobalWordcloud = () => {
  return api.get('/live/multi/wordcloud')
}

/**
 * 获取房间热度排行
 * @returns {Promise} { source, ranking: [...] }
 */
export const getRoomRanking = () => {
  return api.get('/live/multi/ranking')
}

/**
 * 获取后端服务状态（Kafka、Redis）
 * @returns {Promise} { kafka: {...}, redis: {...}, active_rooms }
 */
export const getServicesStatus = () => {
  return api.get('/live/status/services')
}

