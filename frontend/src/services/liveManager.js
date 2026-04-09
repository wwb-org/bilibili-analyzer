/**
 * 直播间管理单例服务
 * 模块级状态在 SPA 生命周期内持久存在，切换页面不会断开 WebSocket
 */
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import LiveWebSocket from '@/utils/websocket'

// ========== 模块级持久状态 ==========
const rooms = ref([])
const activeRoom = ref('global')
const popularRooms = ref([])
const wsMap = {}

// ========== 创建房间数据结构 ==========
function createRoomData(roomId) {
  return reactive({
    id: roomId,
    connected: false,
    paused: false,
    stats: {
      total_danmaku: 0,
      total_gift: 0,
      danmaku_rate: 0,
      avg_sentiment: 0.5,
      sentiment_dist: { positive: 0, neutral: 0, negative: 0 }
    },
    danmakuList: [],
    wordcloudData: [],
    sentimentTrend: []
  })
}

// ========== WebSocket 连接（仅更新数据，不碰图表） ==========
async function connectRoom(room) {
  // 如果已有连接先断开
  if (wsMap[room.id]) {
    wsMap[room.id].disconnect()
    delete wsMap[room.id]
  }

  try {
    const ws = new LiveWebSocket(room.id)

    ws.on('status', (data) => {
      room.connected = data.status === 'connected'
    })

    ws.on('danmaku', (data) => {
      room.danmakuList.unshift(data)
      if (room.danmakuList.length > 100) {
        room.danmakuList.pop()
      }
    })

    ws.on('gift', () => {
      // 礼物统计在 stats 中更新
    })

    ws.on('stats', (data) => {
      Object.assign(room.stats, data)

      room.sentimentTrend.push({
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        avg: data.avg_sentiment,
        ...data.sentiment_dist
      })
      if (room.sentimentTrend.length > 30) {
        room.sentimentTrend.shift()
      }
    })

    ws.on('wordcloud', (data) => {
      room.wordcloudData = data
    })

    await ws.connect()
    wsMap[room.id] = ws
    room.connected = true
    room.paused = false

    return true
  } catch {
    room.connected = false
    return false
  }
}

// ========== 公开方法 ==========

/**
 * 添加房间并连接 WebSocket
 * @param {number} roomId
 * @returns {{ success: boolean, room?: object }}
 */
export async function addRoom(roomId) {
  if (rooms.value.find(r => r.id === roomId)) {
    ElMessage.warning('该房间已在监控中')
    return { success: false }
  }

  if (rooms.value.length >= 4) {
    ElMessage.warning('最多同时监控4个房间')
    return { success: false }
  }

  const room = createRoomData(roomId)
  rooms.value.push(room)

  const ok = await connectRoom(room)
  if (ok) {
    ElMessage.success(`房间 ${roomId} 连接成功`)
  } else {
    ElMessage.error(`房间 ${roomId} 连接失败`)
  }

  return { success: ok, room }
}

/**
 * 移除房间并断开 WebSocket
 */
export function removeRoom(roomId) {
  if (wsMap[roomId]) {
    wsMap[roomId].disconnect()
    delete wsMap[roomId]
  }

  const index = rooms.value.findIndex(r => r.id === roomId)
  if (index > -1) {
    rooms.value.splice(index, 1)
  }

  // 如果当前正在查看被移除的房间，切换视图
  if (activeRoom.value === roomId) {
    activeRoom.value = rooms.value.length > 0 ? rooms.value[0].id : 'global'
  }

  ElMessage.info(`已移除房间 ${roomId}`)
}

/**
 * 暂停房间：断开 WebSocket，保留数据
 */
export function pauseRoom(roomId) {
  const room = rooms.value.find(r => r.id === roomId)
  if (!room) return

  if (wsMap[roomId]) {
    wsMap[roomId].disconnect()
    delete wsMap[roomId]
  }

  room.connected = false
  room.paused = true
  ElMessage.warning(`房间 ${roomId} 已暂停`)
}

/**
 * 恢复房间：重新连接 WebSocket
 */
export async function resumeRoom(roomId) {
  const room = rooms.value.find(r => r.id === roomId)
  if (!room) return

  const ok = await connectRoom(room)
  if (ok) {
    ElMessage.success(`房间 ${roomId} 已恢复连接`)
  } else {
    ElMessage.error(`房间 ${roomId} 重连失败`)
  }
}

// 导出响应式状态
export { rooms, activeRoom, popularRooms }
