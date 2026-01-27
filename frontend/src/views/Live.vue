<template>
  <div class="live-container">
    <!-- 控制区 -->
    <div class="control-panel">
      <div class="input-group">
        <el-input
          v-model="roomId"
          placeholder="请输入直播间ID"
          class="room-input"
          :disabled="isConnected"
          @keyup.enter="connectLive"
        >
          <template #prefix>
            <el-icon><Monitor /></el-icon>
          </template>
        </el-input>
        <el-button
          v-if="!isConnected"
          type="primary"
          class="action-btn"
          @click="connectLive"
          :loading="isConnecting"
        >
          连接直播间
        </el-button>
        <el-button
          v-else
          type="danger"
          class="action-btn"
          @click="disconnectLive"
          plain
        >
          断开连接
        </el-button>
      </div>
      
      <div class="status-indicator">
        <span class="status-dot" :class="{ 'is-active': isConnected }"></span>
        <span class="status-text">{{ connectionStatus }}</span>
      </div>
    </div>

    <!-- 统计卡片区 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon-bg icon-blue">
          <el-icon><ChatLineRound /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_danmaku }}</div>
          <div class="stat-label">弹幕总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-bg icon-green">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.danmaku_rate.toFixed(1) }} <span class="unit">/分</span></div>
          <div class="stat-label">弹幕速率</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-bg icon-orange">
          <el-icon><Sunny /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.avg_sentiment.toFixed(2) }}</div>
          <div class="stat-label">平均情感分</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-bg icon-pink">
          <el-icon><Present /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_gift }}</div>
          <div class="stat-label">礼物总数</div>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="content-row">
      <!-- 左侧：实时弹幕流 -->
      <div class="content-col left-col">
        <div class="panel-header">
          <h3 class="panel-title">实时弹幕流</h3>
          <span class="panel-subtitle">Real-time Danmaku</span>
        </div>
        <div class="danmaku-container">
          <div ref="danmakuStreamRef" class="danmaku-stream">
            <div
              v-for="(item, index) in danmakuList"
              :key="index"
              class="danmaku-item"
            >
              <div class="danmaku-meta">
                <span class="danmaku-user">{{ item.user_name }}</span>
                <span
                  class="sentiment-tag"
                  :class="`sentiment-${item.sentiment_label}`"
                >
                  {{ getSentimentText(item.sentiment_label) }} {{ item.sentiment_score.toFixed(1) }}
                </span>
              </div>
              <div class="danmaku-content">{{ item.content }}</div>
            </div>
            <div v-if="danmakuList.length === 0" class="empty-placeholder">
              <el-empty description="等待连接直播间..." :image-size="100" />
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：可视化图表区 -->
      <div class="content-col right-col">
        <!-- 情感分布饼图 -->
        <div class="chart-panel">
          <div class="panel-header small">
            <h3 class="panel-title">情感分布</h3>
          </div>
          <div ref="pieChartRef" class="chart-container"></div>
        </div>

        <!-- 情感趋势折线图 -->
        <div class="chart-panel">
          <div class="panel-header small">
            <h3 class="panel-title">情感趋势</h3>
          </div>
          <div ref="lineChartRef" class="chart-container"></div>
        </div>

        <!-- 实时词云 -->
        <div class="chart-panel">
          <div class="panel-header small">
            <h3 class="panel-title">实时热词</h3>
          </div>
          <div ref="wordcloudRef" class="chart-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Monitor, ChatLineRound, Timer, Sunny, Present 
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import LiveWebSocket from '@/utils/websocket'

// ========== 状态管理 ==========
const roomId = ref('')
const isConnected = ref(false)
const isConnecting = ref(false)
const connectionStatus = ref('未连接')

// 统计数据
const stats = reactive({
  total_danmaku: 0,
  total_gift: 0,
  danmaku_rate: 0,
  avg_sentiment: 0,
  sentiment_dist: { positive: 0, neutral: 0, negative: 0 }
})

// 弹幕列表（最多显示100条）
const danmakuList = ref([])

// 图表数据
const wordcloudData = ref([])
const sentimentTrend = ref([])

// WebSocket 实例
let ws = null

// DOM 引用
const danmakuStreamRef = ref(null)
const pieChartRef = ref(null)
const lineChartRef = ref(null)
const wordcloudRef = ref(null)

// ECharts 实例
let pieChart = null
let lineChart = null
let wordcloudChart = null

// ========== WebSocket 连接管理 ==========
const connectLive = async () => {
  // 验证房间号
  if (!roomId.value) {
    ElMessage.warning('请输入直播间ID')
    return
  }

  if (!/^\d+$/.test(roomId.value)) {
    ElMessage.error('直播间ID格式错误，请输入纯数字')
    return
  }

  isConnecting.value = true
  connectionStatus.value = '正在连接...'

  try {
    ws = new LiveWebSocket(roomId.value)

    // 注册事件处理器
    ws.on('status', handleStatus)
    ws.on('danmaku', handleDanmaku)
    ws.on('gift', handleGift)
    ws.on('interact', handleInteract)
    ws.on('stats', handleStats)
    ws.on('wordcloud', handleWordcloud)

    await ws.connect()

    isConnected.value = true
    connectionStatus.value = '直播间已连接'
    ElMessage.success(`成功连接到直播间 ${roomId.value}`)
  } catch (error) {
    ElMessage.error('连接失败，请检查直播间ID是否正确')
    connectionStatus.value = '连接失败'
  } finally {
    isConnecting.value = false
  }
}

const disconnectLive = () => {
  if (ws) {
    ws.disconnect()
    ws = null
  }

  isConnected.value = false
  connectionStatus.value = '已断开'

  // 重置数据
  resetData()

  ElMessage.info('已断开连接')
}

const resetData = () => {
  stats.total_danmaku = 0
  stats.total_gift = 0
  stats.danmaku_rate = 0
  stats.avg_sentiment = 0
  stats.sentiment_dist = { positive: 0, neutral: 0, negative: 0 }
  danmakuList.value = []
  wordcloudData.value = []
  sentimentTrend.value = []

  // 更新图表
  updateCharts()
}

// ========== 消息处理函数 ==========
const handleStatus = (data) => {
  console.log('[Status]', data)
}

const handleDanmaku = (data) => {
  // 添加到弹幕列表顶部
  danmakuList.value.unshift(data)
  if (danmakuList.value.length > 100) {
    danmakuList.value.pop()
  }
}

const handleGift = (data) => {
  console.log('[Gift]', data)
}

const handleInteract = (data) => {
  console.log('[Interact]', data)
}

const handleStats = (data) => {
  // 更新统计卡片
  Object.assign(stats, data)

  // 更新情感趋势数据
  sentimentTrend.value.push({
    timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
    ...data.sentiment_dist
  })

  // 只保留最近30个数据点
  if (sentimentTrend.value.length > 30) {
    sentimentTrend.value.shift()
  }

  // 触发图表更新
  updateCharts()
}

const handleWordcloud = (data) => {
  wordcloudData.value = data
  updateWordcloud()
}

// ========== 工具函数 ==========
const getSentimentText = (label) => {
  const map = {
    positive: '积极',
    neutral: '中性',
    negative: '消极'
  }
  return map[label] || label
}

// ========== ECharts 图表初始化 ==========
const initCharts = () => {
  // 情感分布饼图
  pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      itemStyle: {
        borderRadius: 5,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      data: [
        { value: 0, name: '积极', itemStyle: { color: '#00B578' } },
        { value: 0, name: '中性', itemStyle: { color: '#9499A0' } },
        { value: 0, name: '消极', itemStyle: { color: '#F56C6C' } }
      ]
    }]
  })

  // 情感趋势折线图
  lineChart = echarts.init(lineChartRef.value)
  lineChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['积极', '中性', '消极'],
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { fontSize: 12, color: '#61666D' }
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '10%',
      bottom: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#9499A0', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed', color: '#E7E7E7' } },
      axisLabel: { color: '#9499A0', fontSize: 10 }
    },
    series: [
      {
        name: '积极',
        type: 'line',
        data: [],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#00B578' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 181, 120, 0.3)' },
            { offset: 1, color: 'rgba(0, 181, 120, 0.01)' }
          ])
        }
      },
      {
        name: '中性',
        type: 'line',
        data: [],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#9499A0' }
      },
      {
        name: '消极',
        type: 'line',
        data: [],
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#F56C6C' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
            { offset: 1, color: 'rgba(245, 108, 108, 0.01)' }
          ])
        }
      }
    ]
  })

  // 实时词云
  wordcloudChart = echarts.init(wordcloudRef.value)
  wordcloudChart.setOption({
    tooltip: { show: true },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '100%',
      height: '100%',
      right: null,
      bottom: null,
      sizeRange: [12, 40],
      rotationRange: [-45, 45],
      rotationStep: 45,
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => {
          const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#61666D']
          return colors[Math.floor(Math.random() * colors.length)]
        }
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          textShadowBlur: 10,
          textShadowColor: '#333'
        }
      },
      data: []
    }]
  })
}

// 更新图表
const updateCharts = () => {
  if (!pieChart || !lineChart) return

  // 更新饼图
  pieChart.setOption({
    series: [{
      data: [
        { value: stats.sentiment_dist.positive, name: '积极' },
        { value: stats.sentiment_dist.neutral, name: '中性' },
        { value: stats.sentiment_dist.negative, name: '消极' }
      ]
    }]
  })

  // 更新折线图
  if (sentimentTrend.value.length > 0) {
    lineChart.setOption({
      xAxis: {
        data: sentimentTrend.value.map(d => d.timestamp)
      },
      series: [
        { data: sentimentTrend.value.map(d => d.positive) },
        { data: sentimentTrend.value.map(d => d.neutral) },
        { data: sentimentTrend.value.map(d => d.negative) }
      ]
    })
  }
}

// 更新词云
const updateWordcloud = () => {
  if (!wordcloudChart || wordcloudData.value.length === 0) return

  wordcloudChart.setOption({
    series: [{
      data: wordcloudData.value
    }]
  })
}

// ========== 生命周期钩子 ==========
onMounted(() => {
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // 断开 WebSocket 连接
  if (ws) {
    ws.disconnect()
  }

  // 销毁 ECharts 实例
  [pieChart, lineChart, wordcloudChart].forEach(chart => {
    if (chart) chart.dispose()
  })
})

const handleResize = () => {
  [pieChart, lineChart, wordcloudChart].forEach(chart => {
    if (chart) chart.resize()
  })
}

// 监听弹幕列表变化，自动滚动到顶部
watch(() => danmakuList.value.length, () => {
  nextTick(() => {
    if (danmakuStreamRef.value) {
      danmakuStreamRef.value.scrollTop = 0
    }
  })
})
</script>

<style scoped>
.live-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* 控制面板 */
.control-panel {
  background: var(--bg-white);
  padding: 16px 24px;
  border-radius: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid var(--border-light);
}

.input-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.room-input {
  width: 240px;
}

:deep(.room-input .el-input__wrapper) {
  border-radius: 20px;
}

.action-btn {
  border-radius: 20px;
  padding: 8px 24px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--text-placeholder);
  transition: all 0.3s;
}

.status-dot.is-active {
  background-color: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

.status-text {
  font-size: 14px;
  color: var(--text-regular);
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-white);
  padding: 24px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--border-light);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.04);
}

.stat-icon-bg {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.icon-blue { background: var(--bili-blue-light); color: var(--bili-blue); }
.icon-green { background: #E6F7EF; color: var(--color-success); }
.icon-orange { background: #FFF3E6; color: var(--color-warning); }
.icon-pink { background: #FFEAF0; color: var(--bili-pink); }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.unit {
  font-size: 14px;
  font-weight: normal;
  color: var(--text-secondary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 内容区域布局 */
.content-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.content-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.left-col {
  flex: 5;
}

.right-col {
  flex: 4;
}

/* 通用面板样式 */
.panel-header {
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.panel-header.small {
  margin-bottom: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel-header.small .panel-title {
  font-size: 16px;
}

.panel-subtitle {
  font-size: 14px;
  color: var(--text-placeholder);
  font-family: Arial, sans-serif;
}

/* 弹幕流容器 */
.danmaku-container {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  height: 600px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.02);
}

.danmaku-stream {
  height: 100%;
  overflow-y: auto;
  padding-right: 8px;
  scrollbar-width: thin;
  scrollbar-color: var(--text-placeholder) transparent;
}

.danmaku-stream::-webkit-scrollbar {
  width: 6px;
}

.danmaku-stream::-webkit-scrollbar-thumb {
  background-color: var(--border-regular);
  border-radius: 3px;
}

.danmaku-item {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  transition: background 0.2s;
}

.danmaku-item:hover {
  background: #F0F2F5;
}

.danmaku-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.danmaku-user {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
}

.sentiment-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  transform: scale(0.9);
  transform-origin: right center;
}

.sentiment-positive { background: #E6F7EF; color: var(--color-success); }
.sentiment-neutral { background: #F4F4F4; color: var(--text-secondary); }
.sentiment-negative { background: #FEF0F0; color: var(--color-error); }

.danmaku-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-all;
}

/* 图表卡片 */
.chart-panel {
  background: var(--bg-white);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-light);
  height: 220px;
  display: flex;
  flex-direction: column;
}

.chart-container {
  flex: 1;
  width: 100%;
  min-height: 0; /* Flexbox 溢出修复 */
}
</style>