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
