<template>
  <el-drawer
    v-model="visible"
    :title="null"
    :with-header="false"
    size="560px"
    direction="rtl"
    :close-on-click-modal="true"
    class="video-detail-drawer"
    destroy-on-close
    @close="handleClose"
  >
    <div v-loading="loading" class="detail-container">
      <template v-if="videoDetail">
        <!-- 固定区域：头部 + 播放器 + 数据 -->
        <div class="fixed-section">
          <!-- 头部信息 -->
          <div class="detail-header">
            <h2 class="video-title" :title="videoDetail.title">{{ videoDetail.title }}</h2>
            <div class="header-meta">
              <span class="meta-tag channel">{{ videoDetail.category || '全部分区' }}</span>
              <span class="meta-time">{{ formatDate(videoDetail.publish_time) }}</span>
            </div>
          </div>

          <!-- 播放器 -->
          <div class="player-wrapper">
            <VideoPlayer :bvid="bvid" />
          </div>

          <!-- UP主信息 + B站链接 -->
          <div class="uploader-row">
            <div class="uploader-info">
              <el-avatar :size="32" :src="videoDetail.author_face" class="uploader-avatar">
                {{ videoDetail.author_name?.charAt(0) }}
              </el-avatar>
              <span class="uploader-name">{{ videoDetail.author_name || '未知UP主' }}</span>
            </div>
            <a :href="'https://www.bilibili.com/video/' + videoDetail.bvid" target="_blank" class="bili-link">
              前往B站 <el-icon><TopRight /></el-icon>
            </a>
          </div>

          <!-- 数据统计 -->
          <div class="stats-grid">
            <div class="stat-item main">
              <div class="stat-icon"><el-icon><VideoPlay /></el-icon></div>
              <div class="stat-content">
                <div class="stat-num">{{ formatNumber(videoDetail.play_count) }}</div>
                <div class="stat-label">播放</div>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.like_count) }}</div>
              <div class="stat-label">点赞</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.coin_count) }}</div>
              <div class="stat-label">投币</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.favorite_count || 0) }}</div>
              <div class="stat-label">收藏</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.share_count) }}</div>
              <div class="stat-label">分享</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.danmaku_count) }}</div>
              <div class="stat-label">弹幕</div>
            </div>
          </div>

          <!-- 视频简介 -->
          <div class="desc-panel">
            <h3 class="panel-title">简介</h3>
            <div class="desc-content" :class="{ 'expanded': isDescExpanded }">
              {{ videoDetail.description || '暂无简介' }}
            </div>
            <div v-if="videoDetail.description && videoDetail.description.length > 60"
                 class="desc-toggle"
                 @click="isDescExpanded = !isDescExpanded">
              {{ isDescExpanded ? '收起' : '展开' }}
            </div>
          </div>
        </div>

        <!-- 分析图表区 -->
        <div class="analysis-section">
          <h3 class="section-title">数据分析</h3>
          <div class="charts-row">
            <!-- 互动率雷达图 -->
            <div class="chart-wrapper">
              <div class="chart-label">互动率</div>
              <div class="chart-card">
                <div ref="radarChartRef" class="chart-container"></div>
              </div>
            </div>
            <!-- 情感分布饼图 -->
            <div class="chart-wrapper">
              <div class="chart-label">评论情感</div>
              <div class="chart-card">
                <div ref="pieChartRef" class="chart-container"></div>
              </div>
            </div>
          </div>
          <!-- 弹幕词云 -->
          <div class="chart-wrapper">
            <div class="chart-label">弹幕热词</div>
            <div class="chart-card wordcloud-card">
              <div ref="wordcloudChartRef" class="wordcloud-container"></div>
            </div>
          </div>
        </div>

        <!-- 下半部分：评论/弹幕区（可滚动） -->
        <div class="content-section">
          <el-tabs v-model="activeTab" class="content-tabs">
            <el-tab-pane label="评论" name="comments">
              <div class="tab-scroll">
                <CommentList :bvid="bvid" :simple="true" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="弹幕" name="danmakus">
              <div class="tab-scroll">
                <DanmakuList :bvid="bvid" :simple="true" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch, computed, nextTick, onUnmounted } from 'vue'
import { VideoPlay, TopRight } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import VideoPlayer from './VideoPlayer.vue'
import CommentList from './CommentList.vue'
import DanmakuList from './DanmakuList.vue'
import { getVideoDetail, getVideoAnalysis } from '@/api/videos'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  bvid: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const videoDetail = ref(null)
const analysisData = ref(null)
const isDescExpanded = ref(false)
const activeTab = ref('comments')

// 图表 refs
const radarChartRef = ref(null)
const pieChartRef = ref(null)
const wordcloudChartRef = ref(null)

// 图表实例
let radarChart = null
let pieChart = null
let wordcloudChart = null

const fetchVideoDetail = async () => {
  if (!props.bvid) return

  loading.value = true
  try {
    const [detailRes, analysisRes] = await Promise.all([
      getVideoDetail(props.bvid),
      getVideoAnalysis(props.bvid)
    ])
    videoDetail.value = detailRes
    analysisData.value = analysisRes

    // 初始化图表
    await nextTick()
    initCharts()
  } catch (error) {
    console.error('获取视频详情失败:', error)
    videoDetail.value = null
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  initRadarChart()
  initPieChart()
  initWordcloudChart()
}

const initRadarChart = () => {
  if (!radarChartRef.value || !analysisData.value) return

  radarChart = echarts.init(radarChartRef.value)
  const rates = analysisData.value.interaction_rates

  // 动态计算 max 值，确保数据不会溢出，并留出一定余量
  const getMax = (value, defaultMax) => {
    if (value <= defaultMax) return defaultMax
    return Math.ceil(value * 1.2) // 超出时取实际值的 1.2 倍并向上取整
  }

  radarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '点赞率', max: getMax(rates.like_rate, 15) },
        { name: '投币率', max: getMax(rates.coin_rate, 5) },
        { name: '收藏率', max: getMax(rates.favorite_rate, 10) },
        { name: '分享率', max: getMax(rates.share_rate, 3) }
      ],
      radius: '65%',
      axisName: {
        color: '#61666D',
        fontSize: 11
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [rates.like_rate, rates.coin_rate, rates.favorite_rate, rates.share_rate],
        name: '互动率',
        areaStyle: {
          color: 'rgba(0, 161, 214, 0.3)'
        },
        lineStyle: {
          color: '#00A1D6'
        },
        itemStyle: {
          color: '#00A1D6'
        }
      }]
    }]
  })
}

const initPieChart = () => {
  if (!pieChartRef.value || !analysisData.value) return

  pieChart = echarts.init(pieChartRef.value)
  const sentiment = analysisData.value.sentiment_stats

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
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        fontSize: 11,
        formatter: '{b}\n{d}%'
      },
      data: [
        { value: sentiment.positive, name: '正面', itemStyle: { color: '#00B578' } },
        { value: sentiment.neutral, name: '中性', itemStyle: { color: '#9499A0' } },
        { value: sentiment.negative, name: '负面', itemStyle: { color: '#F56C6C' } }
      ]
    }]
  })
}

const initWordcloudChart = () => {
  if (!wordcloudChartRef.value || !analysisData.value) return

  wordcloudChart = echarts.init(wordcloudChartRef.value)
  const keywords = analysisData.value.danmaku_keywords || []

  if (keywords.length === 0) {
    wordcloudChart.setOption({
      title: {
        text: '暂无弹幕数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#9499A0',
          fontSize: 14
        }
      }
    })
    return
  }

  wordcloudChart.setOption({
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [12, 28],
      rotationRange: [-45, 45],
      gridSize: 8,
      textStyle: {
        fontWeight: 'bold',
        color: () => {
          const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#61666D']
          return colors[Math.floor(Math.random() * colors.length)]
        }
      },
      data: keywords.map(k => ({ name: k.word, value: k.count }))
    }]
  })
}

const destroyCharts = () => {
  radarChart?.dispose()
  pieChart?.dispose()
  wordcloudChart?.dispose()
  radarChart = null
  pieChart = null
  wordcloudChart = null
}

const handleClose = () => {
  videoDetail.value = null
  analysisData.value = null
  isDescExpanded.value = false
  activeTab.value = 'comments'
  destroyCharts()
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

const formatDate = (date) => {
  if (!date) return '未知'
  return new Date(date).toLocaleDateString('zh-CN') + ' ' + new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

watch(() => props.bvid, (newVal) => {
  if (newVal && props.modelValue) {
    fetchVideoDetail()
  }
})

watch(() => props.modelValue, (newVal) => {
  if (newVal && props.bvid) {
    fetchVideoDetail()
  }
})

onUnmounted(() => {
  destroyCharts()
})
</script>

<style scoped>
/* Drawer 全局样式 */
:global(.video-detail-drawer) {
  --el-drawer-padding-primary: 0;
}

:global(.video-detail-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}

/* 容器 */
.detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-white);
  overflow-y: auto;
}

/* 固定区域 */
.fixed-section {
  flex-shrink: 0;
  padding: 20px;
  border-bottom: 1px solid var(--border-light);
}

/* 头部 */
.detail-header {
  margin-bottom: 12px;
}

.video-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-tag {
  color: var(--bili-pink);
  background: rgba(251, 114, 153, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 播放器 */
.player-wrapper {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

/* UP主行 */
.uploader-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  margin-bottom: 12px;
}

.uploader-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uploader-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.bili-link {
  font-size: 12px;
  color: var(--bili-blue);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 2px;
  transition: color 0.2s;
}

.bili-link:hover {
  color: var(--bili-blue-hover);
}

/* 数据统计网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
  padding: 10px 4px;
  background: var(--bg-gray-light);
  border-radius: 6px;
}

.stat-item.main {
  grid-column: span 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  background: rgba(0, 161, 214, 0.1);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bili-blue);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.stat-item.main .stat-num {
  font-size: 20px;
  color: var(--bili-blue);
}

.stat-num {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* 简介 */
.desc-panel {
  margin-bottom: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 6px 0;
  color: var(--text-primary);
}

.desc-content {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-regular);
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.desc-content.expanded {
  -webkit-line-clamp: unset;
}

.desc-toggle {
  font-size: 12px;
  color: var(--bili-blue);
  cursor: pointer;
  margin-top: 4px;
}

/* 分析图表区 */
.analysis-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chart-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.chart-card {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 10px;
}

.chart-container {
  height: 140px;
  width: 100%;
}

.wordcloud-card {
  width: 100%;
}

.wordcloud-container {
  height: 120px;
  width: 100%;
}

/* 内容区（评论/弹幕标签页） */
.content-section {
  flex-shrink: 0;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  padding: 16px 20px 20px;
}

.content-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.content-tabs .el-tabs__header) {
  margin-bottom: 12px;
  flex-shrink: 0;
}

:deep(.content-tabs .el-tabs__content) {
  flex: 1;
  min-height: 300px;
}

:deep(.content-tabs .el-tab-pane) {
  height: 100%;
}

.tab-scroll {
  height: 100%;
  max-height: 350px;
  overflow-y: auto;
  padding-right: 4px;
}

/* 滚动条样式 */
.tab-scroll::-webkit-scrollbar {
  width: 4px;
}

.tab-scroll::-webkit-scrollbar-track {
  background: var(--bg-gray-light);
  border-radius: 2px;
}

.tab-scroll::-webkit-scrollbar-thumb {
  background: var(--border-regular);
  border-radius: 2px;
}

.tab-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
