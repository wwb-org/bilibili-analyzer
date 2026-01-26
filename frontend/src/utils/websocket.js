import { ElMessage } from 'element-plus'

/**
 * 直播 WebSocket 连接管理类
 * 负责连接 B站直播间的 WebSocket 服务，处理消息分发和自动重连
 */
class LiveWebSocket {
  constructor(roomId) {
    this.roomId = roomId
    this.ws = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.eventHandlers = new Map() // 事件处理器存储
    this.shouldReconnect = true // 是否应该重连
  }

  /**
   * 建立 WebSocket 连接
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        // 根据环境构建 WebSocket URL
        const wsUrl = import.meta.env.DEV
          ? `ws://localhost:8000/api/live/ws/${this.roomId}`
          : `ws://${window.location.host}/api/live/ws/${this.roomId}`

        this.ws = new WebSocket(wsUrl)

        // 连接成功
        this.ws.onopen = () => {
          console.log(`[WebSocket] 已连接到直播间 ${this.roomId}`)
          this.isConnected = true
          this.reconnectAttempts = 0
          resolve()
        }

        // 接收消息
        this.ws.onmessage = (event) => {
          this._handleMessage(event)
        }

        // 连接关闭
        this.ws.onclose = (event) => {
          console.log(`[WebSocket] 连接关闭`, event)
          this.isConnected = false

          // 如果不是主动断开，尝试重连
          if (this.shouldReconnect && !event.wasClean) {
            this._reconnect()
          }
        }

        // 连接错误
        this.ws.onerror = (error) => {
          console.error(`[WebSocket] 连接错误`, error)
          this.isConnected = false
          reject(error)
        }
      } catch (error) {
        console.error(`[WebSocket] 创建连接失败`, error)
        reject(error)
      }
    })
  }

  /**
   * 断开 WebSocket 连接
   */
  disconnect() {
    console.log('[WebSocket] 主动断开连接')
    this.shouldReconnect = false // 停止自动重连

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false
    this.eventHandlers.clear()
  }

  /**
   * 注册事件处理器
   * @param {string} eventType - 事件类型 (status, danmaku, gift, interact, stats, wordcloud)
   * @param {function} handler - 处理函数
   */
  on(eventType, handler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, [])
    }
    this.eventHandlers.get(eventType).push(handler)
  }

  /**
   * 移除事件处理器
   * @param {string} eventType - 事件类型
   * @param {function} handler - 处理函数（可选，不传则移除该类型所有处理器）
   */
  off(eventType, handler) {
    if (!handler) {
      this.eventHandlers.delete(eventType)
      return
    }

    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index !== -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件处理器
   * @param {string} eventType - 事件类型
   * @param {object} data - 事件数据
   */
  _emit(eventType, data) {
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`[WebSocket] 事件处理器执行失败 (${eventType})`, error)
        }
      })
    }
  }

  /**
   * 处理接收到的消息
   * @param {MessageEvent} event - WebSocket 消息事件
   */
  _handleMessage(event) {
    try {
      const message = JSON.parse(event.data)
      const { type, data } = message

      // 根据消息类型触发对应的事件处理器
      this._emit(type, data)
    } catch (error) {
      console.error('[WebSocket] 消息解析失败', error)
    }
  }

  /**
   * 自动重连
   */
  _reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      ElMessage.error(`连接失败，已停止重连（已尝试 ${this.reconnectAttempts} 次）`)
      this.shouldReconnect = false
      return
    }

    this.reconnectAttempts++
    console.log(`[WebSocket] 正在尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect().catch(error => {
          console.error('[WebSocket] 重连失败', error)
        })
      }
    }, this.reconnectDelay)
  }

  /**
   * 获取连接状态
   */
  getConnectionState() {
    if (!this.ws) return 'disconnected'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  }
}

export default LiveWebSocket
