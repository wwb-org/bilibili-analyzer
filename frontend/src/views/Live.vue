<template>
  <div class="live-container">
    <!-- 控制区 -->
    <div class="control-panel">
      <div class="input-group">
        <el-input
          v-model="newRoomId"
          placeholder="输入直播间ID添加监控"
          class="room-input"
          @keyup.enter="handleAddRoom"
        >
          <template #prefix>
            <el-icon><Monitor /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          class="action-btn"
          @click="handleAddRoom"
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

    <!-- 热门直播间 -->
    <div class="popular-panel">
      <div class="popular-header" @click="popularExpanded = !popularExpanded">
        <h3 class="panel-title">
          <el-icon><Promotion /></el-icon>
          热门直播间
        </h3>
        <div class="popular-actions">
          <el-button size="small" text @click.stop="loadPopularRooms" :loading="popularLoading">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-icon class="expand-arrow" :class="{ 'is-expanded': popularExpanded }">
            <ArrowDown />
          </el-icon>
        </div>
      </div>
      <div v-show="popularExpanded" class="popular-body">
        <div v-if="popularLoading && popularRooms.length === 0" class="popular-loading">
          加载中...
        </div>
        <div v-else-if="popularRooms.length === 0" class="popular-empty">
          暂无数据
        </div>
        <div v-else class="popular-grid">
          <div
            v-for="room in popularRooms"
            :key="room.room_id"
            class="popular-room-card"
            @click="quickAddRoom(room.room_id)"
          >
            <img :src="room.face" class="room-avatar" />
            <div class="room-info">
              <div class="room-title-text">{{ room.title }}</div>
              <div class="room-meta">
                <span class="room-uname">{{ room.uname }}</span>
                <span class="room-online">{{ formatOnline(room.online) }}在线</span>
              </div>
              <div class="room-area" v-if="room.area_name">{{ room.area_name }}</div>
            </div>
            <div class="room-id-badge">{{ room.room_id }}</div>
          </div>
        </div>
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
        <span class="room-status-dot" :class="room.connected ? 'online' : room.paused ? 'paused' : 'offline'" />
        <span class="room-name">房间 {{ room.id }}</span>
        <span class="room-danmaku-count">{{ room.stats.total_danmaku }} 弹幕</span>

        <!-- 暂停/继续按钮 -->
        <el-icon v-if="room.connected" class="action-icon" @click.stop="pauseRoom(room.id)" title="暂停">
          <VideoPause />
        </el-icon>
        <el-icon v-else-if="room.paused" class="action-icon resume" @click.stop="resumeRoom(room.id)" title="继续">
          <VideoPlay />
        </el-icon>
        <el-icon v-else class="action-icon" @click.stop="resumeRoom(room.id)" title="重连">
          <RefreshRight />
        </el-icon>

        <el-icon class="close-icon" @click.stop="handleRemoveRoom(room.id)"><Close /></el-icon>
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
      <!-- 暂停提示 -->
      <div v-if="currentRoom.paused" class="paused-banner">
        <el-icon><VideoPause /></el-icon>
        <span>当前房间已暂停接收数据</span>
        <el-button type="primary" size="small" @click="resumeRoom(currentRoom.id)">恢复连接</el-button>
      </div>

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
          <div class="chart-section">
            <div class="panel-header small">
              <h3 class="panel-title">情感分布</h3>
            </div>
            <div class="chart-panel">
              <div ref="pieChartRef" class="chart-container"></div>
            </div>
          </div>

          <div class="chart-section">
            <div class="panel-header small">
              <h3 class="panel-title">情感趋势</h3>
            </div>
            <div class="chart-panel">
              <div ref="lineChartRef" class="chart-container"></div>
            </div>
          </div>

          <div class="chart-section">
            <div class="panel-header small">
              <h3 class="panel-title">实时热词</h3>
            </div>
            <div class="chart-panel">
              <div ref="wordcloudRef" class="chart-container"></div>
            </div>
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Monitor, ChatLineRound, Timer, Sunny, Present, Close, DataAnalysis,
  Promotion, Refresh, ArrowDown, VideoPause, VideoPlay, RefreshRight
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { getServicesStatus, getPopularRooms } from '@/api/live'
import {
  rooms, activeRoom, popularRooms,
  addRoom, removeRoom, pauseRoom, resumeRoom
} from '@/services/liveManager'

// ========== 本地 UI 状态 ==========
const newRoomId = ref('')
const kafkaStatus = ref(false)
const bilibiliLoggedIn = ref(false)

// 热门直播间（UI 状态）
const popularExpanded = ref(true)
const popularLoading = ref(false)

// ECharts 实例映射（组件本地，mount 时创建，unmount 时销毁）
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

// ========== 房间操作（本地包装） ==========
const handleAddRoom = async () => {
  if (!newRoomId.value) {
    ElMessage.warning('请输入直播间ID')
    return
  }

  if (!/^\d+$/.test(newRoomId.value)) {
    ElMessage.error('直播间ID格式错误，请输入纯数字')
    return
  }

  const roomId = parseInt(newRoomId.value)
  newRoomId.value = ''

  const { success } = await addRoom(roomId)
  if (success) {
    activeRoom.value = roomId
  }
}

const quickAddRoom = (roomId) => {
  newRoomId.value = String(roomId)
  handleAddRoom()
}

const handleRemoveRoom = (roomId) => {
  // 销毁当前房间的图表（如果正在查看）
  if (activeRoom.value === roomId) {
    destroyRoomCharts()
  }
  removeRoom(roomId)
}

const switchRoom = (roomId) => {
  activeRoom.value = roomId
}

// ========== 热门直播间 ==========
const loadPopularRooms = async () => {
  popularLoading.value = true
  try {
    const res = await getPopularRooms()
    popularRooms.value = res.rooms || []
  } catch {
    popularRooms.value = []
  } finally {
    popularLoading.value = false
  }
}

const formatOnline = (num) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return String(num)
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
  if (compareChartRef.value && !chartInstances['compare']) {
    const compareChart = echarts.init(compareChartRef.value)
    compareChart.setOption(getCompareChartOption())
    chartInstances['compare'] = compareChart
  }

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
onMounted(async () => {
  checkServicesStatus()
  window.addEventListener('resize', handleResize)

  // 如果没有房间且热门列表为空，加载热门直播间
  if (rooms.value.length === 0 && popularRooms.value.length === 0) {
    loadPopularRooms()
  }

  // 初始化当前视图的图表
  await nextTick()
  if (activeRoom.value === 'global' && rooms.value.length > 0) {
    initGlobalCharts()
    updateGlobalCharts()
  } else if (currentRoom.value) {
    initRoomCharts()
    updateRoomCharts()
    updateWordcloud()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // 仅销毁图表，不断开 WebSocket（liveManager 持久管理）
  Object.values(chartInstances).forEach(chart => chart.dispose())
})

const handleResize = () => {
  Object.values(chartInstances).forEach(chart => chart.resize())
}

// ========== watch：数据变化时更新图表 ==========

// 监听 activeRoom 变化 → 切换图表
watch(activeRoom, () => {
  nextTick(() => {
    if (activeRoom.value === 'global') {
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

// 监听当前房间 stats 变化 → 更新单房间图表
watch(
  () => currentRoom.value?.stats,
  () => {
    if (activeRoom.value !== 'global' && currentRoom.value) {
      updateRoomCharts()
    }
  },
  { deep: true }
)

// 监听当前房间 sentimentTrend 长度变化 → 更新折线图
watch(
  () => currentRoom.value?.sentimentTrend?.length,
  () => {
    if (activeRoom.value !== 'global' && currentRoom.value) {
      updateRoomCharts()
    }
  }
)

// 监听当前房间 wordcloudData 变化 → 更新词云
watch(
  () => currentRoom.value?.wordcloudData,
  () => {
    if (activeRoom.value !== 'global' && currentRoom.value) {
      updateWordcloud()
    }
  }
)

// 全局视图：监听所有房间的数据变化
watch(
  () => rooms.value.map(r => r.sentimentTrend.length),
  () => {
    if (activeRoom.value === 'global') {
      updateGlobalCharts()
    }
  },
  { deep: true }
)

watch(
  () => rooms.value.map(r => r.wordcloudData),
  () => {
    if (activeRoom.value === 'global') {
      updateGlobalCharts()
    }
  },
  { deep: true }
)
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

/* 状态指示灯 */
.room-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.room-status-dot.online {
  background: #00B578;
  box-shadow: 0 0 6px rgba(0, 181, 120, 0.6);
  animation: pulse-green 2s infinite;
}

.room-status-dot.paused {
  background: #E6A23C;
}

.room-status-dot.offline {
  background: #909399;
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 暂停/继续按钮 */
.action-icon {
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s, color 0.2s;
  cursor: pointer;
}

.action-icon:hover {
  opacity: 1;
}

.action-icon.resume {
  color: #00B578;
  opacity: 0.8;
}

.room-tab.is-active .action-icon.resume {
  color: white;
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
  background: var(--bili-pink);
  color: white;
  border: none;
}

.global-tab:hover {
  background: #f2618a;
}

.global-tab.is-active {
  background: var(--bili-pink);
}

/* 暂停提示横幅 */
.paused-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #FDF6EC;
  border: 1px solid #E6A23C;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #E6A23C;
  font-size: 14px;
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
  background: #FFD700;
  color: white;
}

.ranking-card.rank-2 {
  background: #C0C0C0;
  color: white;
}

.ranking-card.rank-3 {
  background: #CD7F32;
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

/* 单房间视图 */
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
}

.left-col {
  min-width: 0;
}

.right-col {
  min-width: 0;
  gap: 20px;
}

.panel-header {
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.panel-header.small {
  margin-bottom: 10px;
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
  height: 600px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.danmaku-stream {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.danmaku-stream::-webkit-scrollbar {
  width: 6px;
}

.danmaku-stream::-webkit-scrollbar-track {
  background: var(--bg-gray-light);
  border-radius: 3px;
}

.danmaku-stream::-webkit-scrollbar-thumb {
  background: #C0C4CC;
  border-radius: 3px;
}

.danmaku-stream::-webkit-scrollbar-thumb:hover {
  background: #909399;
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

.chart-section {
  display: flex;
  flex-direction: column;
}

.chart-panel {
  background: var(--bg-white);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-light);
  height: 175px;
}

.chart-container {
  width: 100%;
  height: 100%;
}

/* 热门直播间面板 */
.popular-panel {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  margin-bottom: 16px;
  overflow: hidden;
}

.popular-header {
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background 0.2s;
}

.popular-header:hover {
  background: var(--bg-gray-light);
}

.popular-header .panel-title {
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.popular-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expand-arrow {
  transition: transform 0.2s;
}

.expand-arrow.is-expanded {
  transform: rotate(180deg);
}

.popular-body {
  padding: 0 20px 16px;
}

.popular-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.popular-room-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-gray-light);
  cursor: pointer;
  transition: background 0.2s;
}

.popular-room-card:hover {
  background: var(--bg-gray);
}

.room-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.room-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.room-title-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.room-uname {
  color: var(--text-regular);
}

.room-online {
  color: var(--bili-blue);
}

.room-area {
  font-size: 11px;
  color: var(--text-placeholder);
  margin-top: 2px;
}

.room-id-badge {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-gray);
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}

.popular-loading,
.popular-empty {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.empty-state {
  background: var(--bg-white);
  border-radius: 12px;
  padding: 80px 20px;
  text-align: center;
  border: 1px solid var(--border-light);
}
</style>
