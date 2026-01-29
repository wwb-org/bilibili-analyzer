<template>
  <div class="live-container">
    <!-- 控制区 -->
    <div class="control-panel">
      <div class="input-group">
        <el-input
          v-model="newRoomId"
          placeholder="输入直播间ID添加监控"
          class="room-input"
          @keyup.enter="addRoom"
        >
          <template #prefix>
            <el-icon><Monitor /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          class="action-btn"
          @click="addRoom"
          :disabled="rooms.length >= 4"
        >
          添加房间
        </el-button>
      </div>

      <div class="status-group">
        <el-tag v-if="bilibiliLoggedIn" type="success" effect="plain" size="small">
          B站已登录
        </el-tag>
        <el-tag v-else type="warning" effect="plain" size="small">
          B站未登录
        </el-tag>
        <el-tag v-if="kafkaStatus" type="success" effect="plain" size="small">
          Kafka ✓
        </el-tag>
        <el-tag v-else type="info" effect="plain" size="small">
          Kafka ✗
        </el-tag>
        <span class="room-count">已监控 {{ rooms.length }} / 4 个房间</span>
      </div>
    </div>

    <!-- 房间标签页 -->
    <div class="room-tabs" v-if="rooms.length > 0">
      <div
        v-for="room in rooms"
        :key="room.id"
        class="room-tab"
        :class="{ 'is-active': activeRoom === room.id }"
        @click="switchRoom(room.id)"
      >
        <span class="room-name">房间 {{ room.id }}</span>
        <span class="room-danmaku-count">{{ room.stats.total_danmaku }} 弹幕</span>
        <el-icon class="close-icon" @click.stop="removeRoom(room.id)"><Close /></el-icon>
      </div>
      <div class="room-tab global-tab" :class="{ 'is-active': activeRoom === 'global' }" @click="switchRoom('global')">
        <el-icon><DataAnalysis /></el-icon>
        <span>全局对比</span>
      </div>
    </div>

    <!-- 全局对比视图 -->
    <div v-if="activeRoom === 'global' && rooms.length > 0" class="global-view">
      <!-- 房间热度排行 -->
      <div class="ranking-section">
        <div class="panel-header">
          <h3 class="panel-title">房间热度排行</h3>
          <span class="panel-subtitle">按弹幕数量排序</span>
        </div>
        <div class="ranking-grid">
          <div
            v-for="(room, index) in sortedRooms"
            :key="room.id"
            class="ranking-card"
            :class="`rank-${index + 1}`"
          >
            <div class="rank-badge">{{ index + 1 }}</div>
            <div class="rank-info">
              <div class="rank-room">房间 {{ room.id }}</div>
              <div class="rank-stats">
                <span class="rank-danmaku">{{ room.stats.total_danmaku }} 弹幕</span>
                <span class="rank-sentiment" :class="getSentimentClass(room.stats.avg_sentiment)">
                  {{ getSentimentEmoji(room.stats.avg_sentiment) }} {{ (room.stats.avg_sentiment * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 多房间情感对比图 -->
      <div class="compare-section">
        <div class="panel-header">
          <h3 class="panel-title">情感趋势对比</h3>
          <span class="panel-subtitle">多房间实时对比</span>
        </div>
        <div ref="compareChartRef" class="compare-chart"></div>
      </div>

      <!-- 全局热词 -->
      <div class="global-wordcloud-section">
        <div class="panel-header">
          <h3 class="panel-title">全局热词 TOP20</h3>
          <span class="panel-subtitle">跨房间聚合</span>
        </div>
        <div ref="globalWordcloudRef" class="global-wordcloud-chart"></div>
      </div>
    </div>

    <!-- 单房间详情视图 -->
    <div v-else-if="currentRoom" class="room-detail-view">
      <!-- 统计卡片区 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon-bg icon-blue">
            <el-icon><ChatLineRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ currentRoom.stats.total_danmaku }}</div>
            <div class="stat-label">弹幕总数</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon-bg icon-green">
            <el-icon><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ currentRoom.stats.danmaku_rate.toFixed(1) }} <span class="unit">/分</span></div>
            <div class="stat-label">弹幕速率</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon-bg icon-orange">
            <el-icon><Sunny /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ currentRoom.stats.avg_sentiment.toFixed(2) }}</div>
            <div class="stat-label">平均情感分</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon-bg icon-pink">
            <el-icon><Present /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ currentRoom.stats.total_gift }}</div>
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
            <span class="panel-subtitle">房间 {{ currentRoom.id }}</span>
          </div>
          <div class="danmaku-container">
            <div ref="danmakuStreamRef" class="danmaku-stream">
              <div
                v-for="(item, index) in currentRoom.danmakuList"
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
              <div v-if="currentRoom.danmakuList.length === 0" class="empty-placeholder">
                <el-empty description="等待弹幕数据..." :image-size="100" />
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：可视化图表区 -->
        <div class="content-col right-col">
          <div class="chart-panel">
            <div class="panel-header small">
              <h3 class="panel-title">情感分布</h3>
            </div>
            <div ref="pieChartRef" class="chart-container"></div>
          </div>

          <div class="chart-panel">
            <div class="panel-header small">
              <h3 class="panel-title">情感趋势</h3>
            </div>
            <div ref="lineChartRef" class="chart-container"></div>
          </div>

          <div class="chart-panel">
            <div class="panel-header small">
              <h3 class="panel-title">实时热词</h3>
            </div>
            <div ref="wordcloudRef" class="chart-container"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-empty description="请添加直播间开始监控">
        <template #image>
          <el-icon :size="80" color="#dcdfe6"><Monitor /></el-icon>
        </template>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Monitor, ChatLineRound, Timer, Sunny, Present, Close, DataAnalysis
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import LiveWebSocket from '@/utils/websocket'
import { getServicesStatus } from '@/api/live'

// ========== 状态管理 ==========
const newRoomId = ref('')
const activeRoom = ref('global')
const kafkaStatus = ref(false)
const bilibiliLoggedIn = ref(false)

// 房间数据结构
const rooms = ref([])
// WebSocket 实例映射
const wsMap = {}
// ECharts 实例映射
const chartInstances = {}

// DOM 引用
const danmakuStreamRef = ref(null)
const compareChartRef = ref(null)
const globalWordcloudRef = ref(null)
const pieChartRef = ref(null)
const lineChartRef = ref(null)
const wordcloudRef = ref(null)

// 当前选中的房间
const currentRoom = computed(() => {
  if (activeRoom.value === 'global') return null
  return rooms.value.find(r => r.id === activeRoom.value)
})

// 按弹幕数排序的房间
const sortedRooms = computed(() => {
  return [...rooms.value].sort((a, b) => b.stats.total_danmaku - a.stats.total_danmaku)
})

// ========== 房间管理 ==========
const addRoom = async () => {
  if (!newRoomId.value) {
    ElMessage.warning('请输入直播间ID')
    return
  }

  if (!/^\d+$/.test(newRoomId.value)) {
    ElMessage.error('直播间ID格式错误，请输入纯数字')
    return
  }

  const roomId = parseInt(newRoomId.value)

  if (rooms.value.find(r => r.id === roomId)) {
    ElMessage.warning('该房间已在监控中')
    return
  }

  if (rooms.value.length >= 4) {
    ElMessage.warning('最多同时监控4个房间')
    return
  }

  // 创建房间数据
  const room = reactive({
    id: roomId,
    connected: false,
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

  rooms.value.push(room)
  newRoomId.value = ''

  // 连接 WebSocket
  await connectRoom(room)

  // 切换到该房间
  activeRoom.value = roomId

  // 初始化图表
  await nextTick()
  initRoomCharts()
}

const removeRoom = (roomId) => {
  // 断开 WebSocket
  if (wsMap[roomId]) {
    wsMap[roomId].disconnect()
    delete wsMap[roomId]
  }

  // 销毁图表
  if (activeRoom.value === roomId) {
    destroyRoomCharts()
  }

  // 移除房间
  const index = rooms.value.findIndex(r => r.id === roomId)
  if (index > -1) {
    rooms.value.splice(index, 1)
  }

  // 切换视图
  if (activeRoom.value === roomId) {
    activeRoom.value = rooms.value.length > 0 ? rooms.value[0].id : 'global'
  }

  ElMessage.info(`已移除房间 ${roomId}`)
}

const switchRoom = (roomId) => {
  activeRoom.value = roomId

  if (roomId !== 'global') {
    destroyGlobalCharts()
    nextTick(() => {
      initRoomCharts()
      updateRoomCharts()
      updateWordcloud()
    })
  } else {
    nextTick(() => {
      initGlobalCharts()
      updateGlobalCharts()
    })
  }
}

// ========== WebSocket 连接 ==========
const connectRoom = async (room) => {
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

      // 更新趋势数据
      room.sentimentTrend.push({
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        avg: data.avg_sentiment,
        ...data.sentiment_dist
      })
      if (room.sentimentTrend.length > 30) {
        room.sentimentTrend.shift()
      }

      // 更新图表
      if (activeRoom.value === room.id) {
        updateRoomCharts()
      }
      if (activeRoom.value === 'global') {
        updateGlobalCharts()
      }
    })

    ws.on('wordcloud', (data) => {
      room.wordcloudData = data
      if (activeRoom.value === room.id) {
        updateWordcloud()
      }
    })

    await ws.connect()
    wsMap[room.id] = ws
    room.connected = true

    ElMessage.success(`房间 ${room.id} 连接成功`)
  } catch (error) {
    ElMessage.error(`房间 ${room.id} 连接失败`)
    room.connected = false
  }
}

// ========== ECharts 图表 ==========
const initRoomCharts = () => {
  if (pieChartRef.value && !chartInstances.detailPie) {
    const pieChart = echarts.init(pieChartRef.value)
    pieChart.setOption(getPieOption())
    chartInstances.detailPie = pieChart
  }

  if (lineChartRef.value && !chartInstances.detailLine) {
    const lineChart = echarts.init(lineChartRef.value)
    lineChart.setOption(getLineOption())
    chartInstances.detailLine = lineChart
  }

  if (wordcloudRef.value && !chartInstances.detailWordcloud) {
    const wordcloudChart = echarts.init(wordcloudRef.value)
    wordcloudChart.setOption(getWordcloudOption())
    chartInstances.detailWordcloud = wordcloudChart
  }
}

const destroyRoomCharts = () => {
  if (chartInstances.detailPie) {
    chartInstances.detailPie.dispose()
    delete chartInstances.detailPie
  }
  if (chartInstances.detailLine) {
    chartInstances.detailLine.dispose()
    delete chartInstances.detailLine
  }
  if (chartInstances.detailWordcloud) {
    chartInstances.detailWordcloud.dispose()
    delete chartInstances.detailWordcloud
  }
}

const updateRoomCharts = () => {
  const room = currentRoom.value
  if (!room) return

  // 更新饼图
  const pieChart = chartInstances.detailPie
  if (pieChart) {
    pieChart.setOption({
      series: [{
        data: [
          { value: room.stats.sentiment_dist.positive, name: '积极' },
          { value: room.stats.sentiment_dist.neutral, name: '中性' },
          { value: room.stats.sentiment_dist.negative, name: '消极' }
        ]
      }]
    })
  }

  // 更新折线图
  const lineChart = chartInstances.detailLine
  if (lineChart && room.sentimentTrend.length > 0) {
    lineChart.setOption({
      xAxis: { data: room.sentimentTrend.map(d => d.timestamp) },
      series: [
        { data: room.sentimentTrend.map(d => d.positive) },
        { data: room.sentimentTrend.map(d => d.neutral) },
        { data: room.sentimentTrend.map(d => d.negative) }
      ]
    })
  }
}

const updateWordcloud = () => {
  const room = currentRoom.value
  if (!room) return

  const wordcloudChart = chartInstances.detailWordcloud
  if (wordcloudChart && room.wordcloudData.length > 0) {
    wordcloudChart.setOption({
      series: [{ data: room.wordcloudData }]
    })
  }
}

const destroyGlobalCharts = () => {
  if (chartInstances.compare) {
    chartInstances.compare.dispose()
    delete chartInstances.compare
  }
  if (chartInstances.globalWordcloud) {
    chartInstances.globalWordcloud.dispose()
    delete chartInstances.globalWordcloud
  }
}

// 全局图表
const initGlobalCharts = () => {
  // 多房间对比折线图
  if (compareChartRef.value && !chartInstances['compare']) {
    const compareChart = echarts.init(compareChartRef.value)
    compareChart.setOption(getCompareChartOption())
    chartInstances['compare'] = compareChart
  }

  // 全局词云
  if (globalWordcloudRef.value && !chartInstances['globalWordcloud']) {
    const globalWordcloud = echarts.init(globalWordcloudRef.value)
    globalWordcloud.setOption(getWordcloudOption())
    chartInstances['globalWordcloud'] = globalWordcloud
  }
}

const updateGlobalCharts = () => {
  // 更新对比图
  const compareChart = chartInstances['compare']
  if (compareChart && rooms.value.length > 0) {
    const series = rooms.value.map(room => ({
      name: `房间 ${room.id}`,
      type: 'line',
      smooth: true,
      data: room.sentimentTrend.map(d => (d.avg * 100).toFixed(0))
    }))

    const xAxisData = rooms.value[0]?.sentimentTrend.map(d => d.timestamp) || []

    compareChart.setOption({
      legend: { data: rooms.value.map(r => `房间 ${r.id}`) },
      xAxis: { data: xAxisData },
      series
    })
  }

  // 更新全局词云（合并所有房间的词云数据）
  const globalWordcloud = chartInstances['globalWordcloud']
  if (globalWordcloud) {
    const allWords = {}
    rooms.value.forEach(room => {
      room.wordcloudData.forEach(item => {
        allWords[item.name] = (allWords[item.name] || 0) + item.value
      })
    })
    const mergedData = Object.entries(allWords)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 50)

    globalWordcloud.setOption({
      series: [{ data: mergedData }]
    })
  }
}

// ========== 图表配置 ==========
const getPieOption = () => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['50%', '50%'],
    itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
    data: [
      { value: 0, name: '积极', itemStyle: { color: '#00B578' } },
      { value: 0, name: '中性', itemStyle: { color: '#9499A0' } },
      { value: 0, name: '消极', itemStyle: { color: '#F56C6C' } }
    ]
  }]
})

const getLineOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: {
    data: ['积极', '中性', '消极'],
    bottom: 0,
    icon: 'circle',
    itemWidth: 8,
    textStyle: { fontSize: 11 }
  },
  grid: { left: '3%', right: '4%', top: '10%', bottom: '20%', containLabel: true },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: [],
    axisLabel: { fontSize: 10 }
  },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  series: [
    { name: '积极', type: 'line', data: [], smooth: true, showSymbol: false, itemStyle: { color: '#00B578' } },
    { name: '中性', type: 'line', data: [], smooth: true, showSymbol: false, itemStyle: { color: '#9499A0' } },
    { name: '消极', type: 'line', data: [], smooth: true, showSymbol: false, itemStyle: { color: '#F56C6C' } }
  ]
})

const getWordcloudOption = () => ({
  tooltip: { show: true },
  series: [{
    type: 'wordCloud',
    shape: 'circle',
    sizeRange: [12, 36],
    rotationRange: [-45, 45],
    gridSize: 8,
    textStyle: {
      fontWeight: 'bold',
      color: () => {
        const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#61666D']
        return colors[Math.floor(Math.random() * colors.length)]
      }
    },
    data: []
  }]
})

const getCompareChartOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: [], bottom: 0 },
  grid: { left: '3%', right: '4%', top: '10%', bottom: '15%', containLabel: true },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value', name: '情感分 %', max: 100 },
  series: []
})

// ========== 工具函数 ==========
const getSentimentText = (label) => {
  const map = { positive: '积极', neutral: '中性', negative: '消极' }
  return map[label] || label
}

const getSentimentEmoji = (score) => {
  if (score >= 0.6) return '😊'
  if (score <= 0.4) return '😔'
  return '😐'
}

const getSentimentClass = (score) => {
  if (score >= 0.6) return 'sentiment-good'
  if (score <= 0.4) return 'sentiment-bad'
  return 'sentiment-normal'
}

// ========== 检查服务状态 ==========
const checkServicesStatus = async () => {
  try {
    const res = await getServicesStatus()
    kafkaStatus.value = res.kafka?.available || false
    bilibiliLoggedIn.value = res.bilibili?.logged_in || false
  } catch {
    kafkaStatus.value = false
    bilibiliLoggedIn.value = false
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  checkServicesStatus()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)

  // 断开所有 WebSocket
  Object.values(wsMap).forEach(ws => ws.disconnect())

  // 销毁所有图表
  Object.values(chartInstances).forEach(chart => chart.dispose())
})

const handleResize = () => {
  Object.values(chartInstances).forEach(chart => chart.resize())
}

// 监听 activeRoom 变化
watch(activeRoom, (newVal) => {
  nextTick(() => {
    if (newVal === 'global') {
      destroyRoomCharts()
      initGlobalCharts()
      updateGlobalCharts()
    } else {
      destroyGlobalCharts()
      initRoomCharts()
      updateRoomCharts()
      updateWordcloud()
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
  margin-bottom: 16px;
  border: 1px solid var(--border-light);
}

.input-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.room-input {
  width: 220px;
}

:deep(.room-input .el-input__wrapper) {
  border-radius: 20px;
}

.action-btn {
  border-radius: 20px;
}

.status-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.room-count {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 房间标签页 */
.room-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.room-tab {
  background: var(--bg-white);
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.room-tab:hover {
  border-color: var(--bili-blue);
}

.room-tab.is-active {
  background: var(--bili-blue);
  color: white;
  border-color: var(--bili-blue);
}

.room-name {
  font-weight: 500;
}

.room-danmaku-count {
  font-size: 12px;
  opacity: 0.8;
}

.close-icon {
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.close-icon:hover {
  opacity: 1;
}

.global-tab {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.global-tab.is-active {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* 全局视图 */
.global-view {
  display: grid;
  gap: 20px;
}

.ranking-section,
.compare-section,
.global-wordcloud-section {
  background: var(--bg-white);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.ranking-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.ranking-card {
  background: var(--bg-gray-light);
  padding: 16px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.ranking-card.rank-1 {
  background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
  color: white;
}

.ranking-card.rank-2 {
  background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%);
  color: white;
}

.ranking-card.rank-3 {
  background: linear-gradient(135deg, #CD7F32 0%, #B8860B 100%);
  color: white;
}

.rank-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
}

.rank-info {
  flex: 1;
}

.rank-room {
  font-weight: 600;
  margin-bottom: 4px;
}

.rank-stats {
  display: flex;
  gap: 12px;
  font-size: 13px;
  opacity: 0.9;
}

.sentiment-good { color: #00B578; }
.sentiment-normal { color: #9499A0; }
.sentiment-bad { color: #F56C6C; }

.ranking-card.rank-1 .sentiment-good,
.ranking-card.rank-2 .sentiment-good,
.ranking-card.rank-3 .sentiment-good,
.ranking-card.rank-1 .sentiment-normal,
.ranking-card.rank-2 .sentiment-normal,
.ranking-card.rank-3 .sentiment-normal,
.ranking-card.rank-1 .sentiment-bad,
.ranking-card.rank-2 .sentiment-bad,
.ranking-card.rank-3 .sentiment-bad {
  color: inherit;
  opacity: 0.9;
}

.compare-chart {
  height: 300px;
}

.global-wordcloud-chart {
  height: 250px;
}

/* 单房间视图 - 复用原有样式 */
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

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
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
}

.danmaku-container {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  height: 520px;
  padding: 16px;
}

.danmaku-stream {
  height: 100%;
  overflow-y: auto;
  padding-right: 8px;
}

.danmaku-item {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
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
}

.sentiment-positive { background: #E6F7EF; color: var(--color-success); }
.sentiment-neutral { background: #F4F4F4; color: var(--text-secondary); }
.sentiment-negative { background: #FEF0F0; color: var(--color-error); }

.danmaku-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
}

.chart-panel {
  background: var(--bg-white);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-light);
  height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-container {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.empty-state {
  background: var(--bg-white);
  border-radius: 12px;
  padding: 80px 20px;
  text-align: center;
  border: 1px solid var(--border-light);
}
</style>
