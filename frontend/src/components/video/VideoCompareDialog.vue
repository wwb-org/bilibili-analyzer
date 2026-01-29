<template>
  <el-dialog
    v-model="visible"
    title="视频对比"
    width="900px"
    :close-on-click-modal="false"
    class="compare-dialog"
    destroy-on-close
    align-center
  >
    <div v-loading="loading" class="compare-content">
      <template v-if="compareData.length > 0">
        <!-- 对比表格 -->
        <div class="compare-table-wrapper">
          <table class="compare-table">
            <thead>
              <tr>
                <th class="metric-col">指标</th>
                <th v-for="video in compareData" :key="video.bvid" class="video-col">
                  <div class="video-header">
                    <el-image :src="video.cover_url" fit="cover" class="video-thumb">
                      <template #error>
                        <div class="thumb-error">
                          <el-icon><Picture /></el-icon>
                        </div>
                      </template>
                    </el-image>
                    <div class="video-name" :title="video.title">{{ video.title }}</div>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="metric-name">播放量</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('play_count', video.play_count)">
                  {{ formatNumber(video.play_count) }}
                </td>
              </tr>
              <tr>
                <td class="metric-name">点赞数</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('like_count', video.like_count)">
                  {{ formatNumber(video.like_count) }}
                </td>
              </tr>
              <tr>
                <td class="metric-name">投币数</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('coin_count', video.coin_count)">
                  {{ formatNumber(video.coin_count) }}
                </td>
              </tr>
              <tr>
                <td class="metric-name">收藏数</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('favorite_count', video.favorite_count)">
                  {{ formatNumber(video.favorite_count) }}
                </td>
              </tr>
              <tr>
                <td class="metric-name">点赞率</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('like_rate', video.like_rate)">
                  {{ video.like_rate }}%
                </td>
              </tr>
              <tr>
                <td class="metric-name">投币率</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('coin_rate', video.coin_rate)">
                  {{ video.coin_rate }}%
                </td>
              </tr>
              <tr>
                <td class="metric-name">正面评论</td>
                <td v-for="video in compareData" :key="video.bvid" :class="getHighlightClass('sentiment.positive', video.sentiment.positive)">
                  {{ video.sentiment.positive }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 图表区 -->
        <div class="charts-section">
          <div class="chart-panel">
            <h4 class="chart-title">互动率对比</h4>
            <div ref="radarChartRef" class="chart-area"></div>
          </div>
          <div class="chart-panel">
            <h4 class="chart-title">情感分布对比</h4>
            <div ref="barChartRef" class="chart-area"></div>
          </div>
        </div>
      </template>

      <el-empty v-else description="请选择要对比的视频" />
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { compareVideos } from '@/api/videos'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  bvids: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const compareData = ref([])

// 图表 refs
const radarChartRef = ref(null)
const barChartRef = ref(null)

// 图表实例
let radarChart = null
let barChart = null

// 获取最大值（用于高亮）
const maxValues = computed(() => {
  if (compareData.value.length === 0) return {}
  return {
    play_count: Math.max(...compareData.value.map(v => v.play_count)),
    like_count: Math.max(...compareData.value.map(v => v.like_count)),
    coin_count: Math.max(...compareData.value.map(v => v.coin_count)),
    favorite_count: Math.max(...compareData.value.map(v => v.favorite_count)),
    like_rate: Math.max(...compareData.value.map(v => v.like_rate)),
    coin_rate: Math.max(...compareData.value.map(v => v.coin_rate)),
    'sentiment.positive': Math.max(...compareData.value.map(v => v.sentiment.positive))
  }
})

// 获取高亮类名
const getHighlightClass = (metric, value) => {
  if (value === maxValues.value[metric]) {
    return 'is-max'
  }
  return ''
}

const fetchCompareData = async () => {
  if (props.bvids.length === 0) return

  loading.value = true
  try {
    const res = await compareVideos(props.bvids)
    compareData.value = res.videos || []

    await nextTick()
    initCharts()
  } catch (error) {
    console.error('获取对比数据失败:', error)
    compareData.value = []
  } finally {
    loading.value = false
  }
}

const initCharts = () => {
  initRadarChart()
  initBarChart()
}

const initRadarChart = () => {
  if (!radarChartRef.value || compareData.value.length === 0) return

  radarChart = echarts.init(radarChartRef.value)

  const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#9499A0']
  const seriesData = compareData.value.map((video, index) => ({
    value: [video.like_rate, video.coin_rate, video.favorite_rate, video.share_rate],
    name: video.title.slice(0, 10) + (video.title.length > 10 ? '...' : ''),
    lineStyle: { color: colors[index] },
    itemStyle: { color: colors[index] },
    areaStyle: { color: colors[index], opacity: 0.2 }
  }))

  // 动态计算 max 值，取所有视频中的最大值，确保数据不会溢出
  const getMax = (key, defaultMax) => {
    const maxValue = Math.max(...compareData.value.map(v => v[key] || 0))
    if (maxValue <= defaultMax) return defaultMax
    return Math.ceil(maxValue * 1.2) // 超出时取最大值的 1.2 倍并向上取整
  }

  radarChart.setOption({
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      data: seriesData.map(s => s.name),
      textStyle: { fontSize: 11 }
    },
    radar: {
      indicator: [
        { name: '点赞率', max: getMax('like_rate', 15) },
        { name: '投币率', max: getMax('coin_rate', 5) },
        { name: '收藏率', max: getMax('favorite_rate', 10) },
        { name: '分享率', max: getMax('share_rate', 3) }
      ],
      radius: '55%',
      center: ['50%', '45%'],
      axisName: {
        color: '#61666D',
        fontSize: 11
      }
    },
    series: [{
      type: 'radar',
      data: seriesData
    }]
  })
}

const initBarChart = () => {
  if (!barChartRef.value || compareData.value.length === 0) return

  barChart = echarts.init(barChartRef.value)

  const categories = compareData.value.map(v =>
    v.title.slice(0, 8) + (v.title.length > 8 ? '...' : '')
  )

  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      bottom: 0,
      data: ['正面', '中性', '负面'],
      textStyle: { fontSize: 11 }
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
      data: categories,
      axisLabel: {
        fontSize: 10,
        interval: 0,
        rotate: categories.length > 3 ? 15 : 0
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%',
        fontSize: 10
      }
    },
    series: [
      {
        name: '正面',
        type: 'bar',
        stack: 'sentiment',
        data: compareData.value.map(v => v.sentiment.positive),
        itemStyle: { color: '#00B578' }
      },
      {
        name: '中性',
        type: 'bar',
        stack: 'sentiment',
        data: compareData.value.map(v => v.sentiment.neutral),
        itemStyle: { color: '#9499A0' }
      },
      {
        name: '负面',
        type: 'bar',
        stack: 'sentiment',
        data: compareData.value.map(v => v.sentiment.negative),
        itemStyle: { color: '#F56C6C' }
      }
    ]
  })
}

const destroyCharts = () => {
  radarChart?.dispose()
  barChart?.dispose()
  radarChart = null
  barChart = null
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

watch(() => props.modelValue, (newVal) => {
  if (newVal && props.bvids.length > 0) {
    fetchCompareData()
  } else if (!newVal) {
    compareData.value = []
    destroyCharts()
  }
})

onUnmounted(() => {
  destroyCharts()
})
</script>

<style scoped>
/* Dialog 全局样式 */
:global(.compare-dialog) {
  --el-dialog-margin-top: 0;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

:global(.compare-dialog .el-dialog__body) {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

:global(.compare-dialog .el-dialog__header) {
  flex-shrink: 0;
}

:global(.compare-dialog .el-dialog__footer) {
  flex-shrink: 0;
}

.compare-content {
  min-height: 300px;
}

/* 表格样式 */
.compare-table-wrapper {
  overflow-x: auto;
  margin-bottom: 24px;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.compare-table th,
.compare-table td {
  padding: 12px 16px;
  text-align: center;
  border-bottom: 1px solid var(--border-light);
}

.compare-table th {
  background: var(--bg-gray-light);
  font-weight: 500;
  color: var(--text-primary);
}

.metric-col {
  width: 100px;
  text-align: left !important;
}

.video-col {
  min-width: 150px;
}

.video-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.video-thumb {
  width: 80px;
  height: 45px;
  border-radius: 4px;
  overflow: hidden;
}

.thumb-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-gray);
  color: var(--text-secondary);
}

.video-name {
  font-size: 12px;
  color: var(--text-regular);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-name {
  font-weight: 500;
  color: var(--text-secondary);
  text-align: left !important;
}

.compare-table td {
  color: var(--text-primary);
}

.compare-table td.is-max {
  color: var(--bili-blue);
  font-weight: 600;
  background: rgba(0, 161, 214, 0.05);
}

/* 图表区 */
.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-panel {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  text-align: center;
}

.chart-area {
  height: 280px;
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}
</style>
