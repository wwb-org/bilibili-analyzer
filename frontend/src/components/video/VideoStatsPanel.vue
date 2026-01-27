<template>
  <div class="stats-panel" v-loading="loading">
    <div class="stats-grid">
      <!-- 视频数 -->
      <div class="stat-card">
        <div class="stat-icon-bg icon-blue">
          <el-icon><VideoPlay /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_videos }}</div>
          <div class="stat-label">视频数</div>
        </div>
      </div>

      <!-- 平均播放 -->
      <div class="stat-card">
        <div class="stat-icon-bg icon-green">
          <el-icon><View /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatNumber(stats.avg_play_count) }}</div>
          <div class="stat-label">平均播放</div>
        </div>
      </div>

      <!-- 平均互动率 -->
      <div class="stat-card">
        <div class="stat-icon-bg icon-orange">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.avg_interaction_rate }}%</div>
          <div class="stat-label">平均互动率</div>
        </div>
      </div>

      <!-- 正面评论占比 -->
      <div class="stat-card">
        <div class="stat-icon-bg icon-pink">
          <el-icon><ChatDotSquare /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ positiveRate }}%</div>
          <div class="stat-label">正面评论</div>
        </div>
      </div>

      <!-- 分区分布迷你图 -->
      <div class="stat-card chart-card">
        <div class="chart-label">分区分布</div>
        <div ref="chartRef" class="mini-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPlay, View, TrendCharts, ChatDotSquare } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({
      total_videos: 0,
      total_play_count: 0,
      avg_play_count: 0,
      avg_interaction_rate: 0,
      sentiment_distribution: { positive: 0, neutral: 0, negative: 0 },
      category_distribution: []
    })
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartRef = ref(null)
let chartInstance = null

// 计算正面评论占比
const positiveRate = computed(() => {
  const { positive, neutral, negative } = props.stats.sentiment_distribution || {}
  const total = (positive || 0) + (neutral || 0) + (negative || 0)
  if (total === 0) return 0
  return Math.round((positive || 0) / total * 100)
})

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return Math.round(num).toLocaleString()
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return

  const data = (props.stats.category_distribution || [])
    .slice(0, 6) // 最多显示6个分区
    .map(item => ({
      name: item.category || '未分类',
      value: item.count
    }))

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}',
      confine: true
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '50%'],
      itemStyle: {
        borderRadius: 3,
        borderColor: '#fff',
        borderWidth: 1
      },
      label: { show: false },
      emphasis: {
        label: {
          show: true,
          fontSize: 10,
          fontWeight: 'bold'
        },
        scale: true,
        scaleSize: 3
      },
      data: data.length > 0 ? data : [{ name: '暂无数据', value: 1 }],
      color: ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#9499A0', '#61666D']
    }]
  })
}

// 监听数据变化
watch(() => props.stats.category_distribution, () => {
  nextTick(updateChart)
}, { deep: true })

// 窗口大小变化
const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  nextTick(initChart)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.stats-panel {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  padding: 16px 20px;
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
}

.stat-icon-bg {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.icon-blue {
  background: rgba(0, 161, 214, 0.1);
  color: var(--bili-blue);
}

.icon-green {
  background: rgba(0, 181, 120, 0.1);
  color: var(--color-success);
}

.icon-orange {
  background: rgba(255, 151, 54, 0.1);
  color: var(--color-warning);
}

.icon-pink {
  background: rgba(251, 114, 153, 0.1);
  color: var(--bili-pink);
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* 图表卡片 */
.chart-card {
  flex-direction: column;
  align-items: stretch;
  padding: 8px 12px;
}

.chart-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  margin-bottom: 4px;
}

.mini-chart {
  height: 50px;
  width: 100%;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .chart-card {
    grid-column: span 3;
  }

  .mini-chart {
    height: 80px;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .chart-card {
    grid-column: span 2;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .chart-card {
    grid-column: span 1;
  }
}
</style>
