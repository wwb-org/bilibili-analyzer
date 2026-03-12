<template>
  <div class="prediction-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">智能预测</h2>
        <span class="page-desc">选择视频，一键分析热度趋势与相似推荐</span>
      </div>
      <div class="header-right">
        <el-tag v-if="modelInfo.predictor?.loaded" type="success" effect="plain">
          预测模型已加载
        </el-tag>
        <el-tag v-else type="warning" effect="plain">
          预测模型未加载
        </el-tag>
        <el-tag v-if="modelInfo.predictor?.coin_model_loaded" type="success" effect="plain">
          投币模型已加载
        </el-tag>
        <el-tag v-else type="warning" effect="plain">
          投币模型未加载
        </el-tag>
        <el-tag v-if="modelInfo.recommender?.loaded" type="success" effect="plain">
          推荐模型已加载
        </el-tag>
        <el-tag v-else type="warning" effect="plain">
          推荐模型未加载
        </el-tag>
      </div>
    </div>

    <!-- 主内容区 - 左右分栏 -->
    <div class="main-content">
      <!-- 左侧：视频选择区 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="panel-title">选择视频</span>
          <span class="video-count">共 {{ totalVideos }} 个视频</span>
        </div>

        <!-- 搜索框 -->
        <div class="search-box">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索视频标题..."
            clearable
            @input="handleSearchDebounce"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <!-- 筛选栏 -->
        <div class="filter-bar">
          <el-select
            v-model="selectedCategory"
            placeholder="全部分区"
            clearable
            size="small"
            @change="handleFilterChange"
          >
            <el-option
              v-for="cat in categoryOptions"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
          <el-select
            v-model="orderBy"
            size="small"
            @change="handleFilterChange"
          >
            <el-option label="播放最高" value="play_count" />
            <el-option label="最新发布" value="publish_time" />
            <el-option label="互动率最高" value="interaction_rate" />
            <el-option label="点赞最多" value="like_count" />
          </el-select>
        </div>

        <!-- 手动输入折叠面板 -->
        <el-collapse v-model="manualInputExpanded" class="manual-collapse">
          <el-collapse-item name="manual">
            <template #title>
              <span class="collapse-title">手动输入 BV 号</span>
            </template>
            <div class="manual-input-section">
              <el-input
                v-model="manualBvid"
                placeholder="输入 BV 号，如 BV1xx411c7mD"
                clearable
                @keyup.enter="handleManualAnalyze"
              >
                <template #prepend>BV</template>
              </el-input>
              <el-button
                type="primary"
                size="small"
                :disabled="!manualBvid"
                @click="handleManualAnalyze"
              >
                分析
              </el-button>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- 视频列表 -->
        <div class="video-list" v-loading="loadingVideos">
          <div
            v-for="video in videos"
            :key="video.bvid"
            class="video-item"
            :class="{ 'is-selected': selectedVideo?.bvid === video.bvid }"
            @click="analyzeVideo(video)"
          >
            <img :src="video.cover_url" class="video-cover" alt="cover" />
            <div class="video-info">
              <div class="video-title" :title="video.title">{{ video.title }}</div>
              <div class="video-meta">
                <span class="author">{{ video.author_name || '未知UP主' }}</span>
                <span class="category" v-if="video.category">{{ video.category }}</span>
              </div>
              <div class="video-stats">
                <span class="stat-item">{{ formatNumber(video.play_count) }} 播放</span>
                <span class="stat-item">{{ formatNumber(video.like_count) }} 点赞</span>
              </div>
            </div>
            <div class="selected-indicator" v-if="selectedVideo?.bvid === video.bvid">
              <el-icon><Check /></el-icon>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty v-if="!loadingVideos && videos.length === 0" description="暂无视频" :image-size="80" />
        </div>

        <!-- 分页 -->
        <div class="pagination-wrapper" v-if="totalVideos > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="totalVideos"
            layout="prev, pager, next"
            small
            @current-change="handlePageChange"
          />
        </div>
      </div>

      <!-- 右侧：分析结果区 -->
      <div class="right-panel">
        <!-- 未选择状态 -->
        <div v-if="!selectedVideo && !analyzing" class="empty-state">
          <el-empty description="从左侧选择一个视频开始分析" :image-size="150" />
        </div>

        <!-- 分析中状态 -->
        <div v-else-if="analyzing" class="loading-state">
          <el-skeleton :rows="10" animated />
        </div>

        <!-- 分析结果 -->
        <div v-else class="result-content">
          <!-- 选中视频信息卡片 -->
          <div class="selected-video-card">
            <img :src="selectedVideo.cover_url" class="card-cover" alt="cover" />
            <div class="card-info">
              <div class="card-title">{{ selectedVideo.title }}</div>
              <div class="card-meta">
                <span class="author">{{ selectedVideo.author_name || '未知UP主' }}</span>
                <el-tag v-if="selectedVideo.category" size="small" type="info">{{ selectedVideo.category }}</el-tag>
                <el-tag size="small">{{ selectedVideo.bvid }}</el-tag>
              </div>
              <div class="card-stats">
                <span>{{ formatNumber(selectedVideo.play_count) }} 播放</span>
                <span>{{ formatNumber(selectedVideo.like_count) }} 点赞</span>
                <span>{{ formatNumber(selectedVideo.coin_count) }} 投币</span>
                <span>{{ formatNumber(selectedVideo.favorite_count) }} 收藏</span>
              </div>
            </div>
          </div>

          <!-- 热度预测结果 -->
          <div class="result-section" v-if="predictionResult">
            <div class="section-header">
              <span class="section-title">热度预测</span>
              <span class="section-desc">预测7天后播放量变化</span>
            </div>

            <!-- 预测失败提示 -->
            <el-alert
              v-if="!predictionResult.success"
              :title="predictionResult.error || '预测失败'"
              type="error"
              show-icon
              :closable="false"
            />

            <!-- 预测成功 -->
            <template v-else>
              <!-- 核心指标卡片 -->
              <div class="metrics-grid">
                <div class="metric-card">
                  <div class="metric-label">当前播放量</div>
                  <div class="metric-value">{{ formatNumber(predictionResult.current_play_count) }}</div>
                </div>
                <div class="metric-card highlight">
                  <div class="metric-label">预测播放量</div>
                  <div class="metric-value">{{ formatNumber(predictionResult.predicted_play_count) }}</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">预计增长</div>
                  <div class="metric-value" :class="predictionResult.play_increment >= 0 ? 'positive' : 'negative'">
                    {{ predictionResult.play_increment >= 0 ? '+' : '' }}{{ formatNumber(predictionResult.play_increment) }}
                  </div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">增长率</div>
                  <div class="metric-value" :class="predictionResult.growth_rate >= 0 ? 'positive' : 'negative'">
                    {{ predictionResult.growth_rate >= 0 ? '+' : '' }}{{ predictionResult.growth_rate?.toFixed(1) }}%
                  </div>
                </div>
              </div>

              <!-- 热度等级 -->
              <div class="heat-level-row">
                <span class="label">热度预测：</span>
                <div class="heat-level" :class="`heat-${predictionResult.heat_level}`">
                  <span class="heat-icon">{{ getHeatIcon(predictionResult.heat_level) }}</span>
                  <span class="heat-text">{{ getHeatText(predictionResult.heat_level) }}</span>
                </div>
              </div>

              <!-- 投币量预测 -->
              <div class="coin-prediction" v-if="predictionResult.predicted_coin_count != null">
                <div class="sub-section-title">投币量预测</div>
                <div class="metrics-grid">
                  <div class="metric-card">
                    <div class="metric-label">当前投币量</div>
                    <div class="metric-value">{{ formatNumber(predictionResult.current_coin_count) }}</div>
                  </div>
                  <div class="metric-card highlight-coin">
                    <div class="metric-label">预测投币量</div>
                    <div class="metric-value">{{ formatNumber(predictionResult.predicted_coin_count) }}</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">投币增长</div>
                    <div class="metric-value" :class="predictionResult.coin_increment >= 0 ? 'positive' : 'negative'">
                      {{ predictionResult.coin_increment >= 0 ? '+' : '' }}{{ formatNumber(predictionResult.coin_increment) }}
                    </div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">投币增长率</div>
                    <div class="metric-value" :class="predictionResult.coin_growth_rate >= 0 ? 'positive' : 'negative'">
                      {{ predictionResult.coin_growth_rate >= 0 ? '+' : '' }}{{ predictionResult.coin_growth_rate?.toFixed(1) }}%
                    </div>
                  </div>
                </div>
              </div>

              <!-- 特征重要性图表 -->
              <div class="chart-container" v-if="predictionResult.feature_importance">
                <div class="chart-title">特征重要性</div>
                <div ref="featureChartRef" class="feature-chart"></div>
              </div>
            </template>
          </div>

          <!-- 相似视频推荐 -->
          <div class="result-section" v-if="recommendResult">
            <div class="section-header">
              <span class="section-title">相似视频推荐</span>
              <span class="section-desc">基于内容相似度分析</span>
            </div>

            <!-- 推荐失败提示 -->
            <el-alert
              v-if="!recommendResult.success"
              :title="recommendResult.error || '推荐失败'"
              type="error"
              show-icon
              :closable="false"
            />

            <!-- 推荐成功 -->
            <template v-else>
              <div class="recommend-info">
                <el-tag size="small" effect="plain">
                  {{ recommendResult.method === 'tfidf_multi_score' ? 'TF-IDF 多维度' : '基于分区' }}
                </el-tag>
                <span class="total-count">共 {{ recommendResult.total }} 个推荐</span>
              </div>

              <div class="recommend-list" v-if="recommendResult.recommendations && recommendResult.recommendations.length > 0">
                <div
                  v-for="(item, index) in recommendResult.recommendations"
                  :key="item.bvid"
                  class="recommend-item"
                  @click="analyzeRecommendedVideo(item)"
                >
                  <div class="rank" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</div>
                  <img v-if="item.cover_url" :src="item.cover_url" class="cover" alt="cover" />
                  <div v-else class="cover cover-placeholder"></div>
                  <div class="info">
                    <div class="title" :title="item.title">{{ item.title }}</div>
                    <div class="meta">
                      <span class="author">{{ item.author_name || '未知UP主' }}</span>
                      <el-tag v-if="item.same_category" size="small" type="success">同分区</el-tag>
                      <el-tag v-if="item.same_author" size="small" type="warning">同UP主</el-tag>
                    </div>
                    <div class="stats">
                      <span>{{ formatNumber(item.play_count) }} 播放</span>
                      <span class="similarity">相似度 {{ (item.similarity_score * 100).toFixed(1) }}%</span>
                    </div>
                  </div>
                  <el-icon class="analyze-icon"><Right /></el-icon>
                </div>
              </div>
              <el-empty v-else description="暂无相似视频推荐" :image-size="60" />
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Check, Right } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  predictByBvid,
  getRecommendations,
  getModelInfo
} from '@/api/ml'
import { getVideos, getCategories } from '@/api/videos'

// ========== 模型状态 ==========
const modelInfo = ref({ predictor: {}, recommender: {} })

// ========== 视频列表相关 ==========
const videos = ref([])
const totalVideos = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const searchKeyword = ref('')
const selectedCategory = ref('')
const orderBy = ref('play_count')
const categoryOptions = ref([])
const loadingVideos = ref(false)

// ========== 手动输入 ==========
const manualInputExpanded = ref([])
const manualBvid = ref('')

// ========== 选中视频和分析结果 ==========
const selectedVideo = ref(null)
const analyzing = ref(false)
const predictionResult = ref(null)
const recommendResult = ref(null)

// ========== 图表 ==========
const featureChartRef = ref(null)
let featureChart = null

// ========== 搜索防抖 ==========
let searchTimer = null
const handleSearchDebounce = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadVideos()
  }, 300)
}

// ========== 加载方法 ==========
const loadModelInfo = async () => {
  try {
    const res = await getModelInfo()
    modelInfo.value = res
  } catch (e) {
    console.error('获取模型信息失败', e)
  }
}

const loadCategories = async () => {
  try {
    const res = await getCategories()
    categoryOptions.value = res || []
  } catch (e) {
    console.error('获取分区失败', e)
  }
}

const loadVideos = async () => {
  loadingVideos.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      order_by: orderBy.value
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (selectedCategory.value) params.category = selectedCategory.value

    const res = await getVideos(params)
    videos.value = res.items || []
    totalVideos.value = res.total || 0
  } catch (e) {
    console.error('加载视频失败', e)
    ElMessage.error('加载视频列表失败')
  } finally {
    loadingVideos.value = false
  }
}

// ========== 筛选和分页 ==========
const handleFilterChange = () => {
  currentPage.value = 1
  loadVideos()
}

const handlePageChange = () => {
  loadVideos()
}

// ========== 分析方法 ==========
const analyzeVideo = async (video) => {
  // 如果是同一个视频，不重复分析
  if (selectedVideo.value?.bvid === video.bvid && predictionResult.value) {
    return
  }

  selectedVideo.value = video
  analyzing.value = true
  predictionResult.value = null
  recommendResult.value = null

  // 销毁旧图表
  if (featureChart) {
    featureChart.dispose()
    featureChart = null
  }

  try {
    // 并行请求预测和推荐
    const [predictRes, recommendRes] = await Promise.all([
      predictByBvid(video.bvid).catch(e => ({ success: false, error: e.response?.data?.detail || e.message })),
      getRecommendations(video.bvid, { top_k: 10, same_category: true }).catch(e => ({ success: false, error: e.response?.data?.detail || e.message }))
    ])

    predictionResult.value = predictRes
    recommendResult.value = recommendRes
  } catch (e) {
    ElMessage.error('分析失败: ' + e.message)
  } finally {
    analyzing.value = false
  }

  // 必须在 analyzing=false 之后渲染图表，否则 DOM 还在显示骨架屏
  if (predictionResult.value?.success && predictionResult.value?.feature_importance
      && Object.keys(predictionResult.value.feature_importance).length > 0) {
    await nextTick()
    renderFeatureChart(predictionResult.value.feature_importance)
  }
}

// 手动输入分析
const handleManualAnalyze = async () => {
  if (!manualBvid.value) return

  let bvid = manualBvid.value.trim()
  if (bvid.startsWith('BV')) {
    bvid = bvid.substring(2)
  }

  // 构造一个简单的视频对象
  const video = {
    bvid: 'BV' + bvid,
    title: '手动输入的视频',
    author_name: '加载中...',
    cover_url: '',
    play_count: 0,
    like_count: 0,
    coin_count: 0,
    favorite_count: 0
  }

  await analyzeVideo(video)

  // 如果预测成功，更新视频信息
  if (predictionResult.value?.success) {
    selectedVideo.value = {
      ...video,
      title: predictionResult.value.title || video.title,
      play_count: predictionResult.value.current_play_count || 0
    }
  }
}

// 点击推荐视频进行分析
const analyzeRecommendedVideo = async (item) => {
  const video = {
    bvid: item.bvid,
    title: item.title,
    author_name: item.author_name,
    cover_url: item.cover_url,
    category: item.category,
    play_count: item.play_count || 0,
    like_count: item.like_count || 0,
    coin_count: item.coin_count || 0,
    favorite_count: item.favorite_count || 0
  }
  await analyzeVideo(video)
}

// ========== 图表渲染 ==========
const renderFeatureChart = (importance) => {
  if (!featureChartRef.value || !importance) return

  if (featureChart) {
    featureChart.dispose()
  }
  featureChart = echarts.init(featureChartRef.value)

  // 特征名称映射
  const nameMap = {
    like_rate: '点赞率',
    coin_rate: '投币率',
    favorite_rate: '收藏率',
    share_rate: '分享率',
    interaction_rate: '综合互动率',
    danmaku_rate: '弹幕率',
    comment_rate: '评论率',
    publish_hour: '发布时间',
    publish_weekday: '发布星期',
    video_age_days: '视频天数',
    title_length: '标题长度',
    has_description: '有描述',
    duration_minutes: '视频时长',
    category_code: '分区',
    current_play_count: '当前播放量'
  }

  // 转换数据并排序
  const data = Object.entries(importance)
    .map(([key, value]) => ({
      name: nameMap[key] || key,
      value: value
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#61666D' },
      splitLine: { lineStyle: { color: '#E7E7E7' } }
    },
    yAxis: {
      type: 'category',
      data: data.map(d => d.name),
      axisLabel: { fontSize: 11, color: '#61666D' },
      axisLine: { lineStyle: { color: '#E7E7E7' } }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d.value),
      itemStyle: {
        color: '#00A1D6',
        borderRadius: [0, 4, 4, 0]
      },
      barWidth: '60%'
    }]
  }

  featureChart.setOption(option)
}

// ========== 工具方法 ==========
const formatNumber = (num) => {
  if (num === null || num === undefined) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toLocaleString()
}

const getHeatIcon = (level) => {
  const icons = { hot: '🔥', rising: '📈', normal: '➡️', cold: '❄️' }
  return icons[level] || '❓'
}

const getHeatText = (level) => {
  const texts = { hot: '爆款潜力', rising: '上升趋势', normal: '正常表现', cold: '热度下降' }
  return texts[level] || '未知'
}

const handleResize = () => {
  featureChart?.resize()
}

// ========== 生命周期 ==========
onMounted(() => {
  loadModelInfo()
  loadCategories()
  loadVideos()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (featureChart) {
    featureChart.dispose()
    featureChart = null
  }
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})
</script>

<style scoped>
.prediction-container {
  height: calc(100vh - 60px - 48px); /* 减去 header 高度和 main padding */
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  gap: 8px;
}

/* 主内容区 */
.main-content {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  flex: 1;
  min-height: 0; /* 重要：允许 flex 子元素收缩 */
  overflow: hidden;
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.video-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.search-box {
  margin-bottom: 12px;
}

.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.filter-bar .el-select {
  flex: 1;
}

/* 手动输入折叠面板 */
.manual-collapse {
  margin-bottom: 12px;
  border: none;
}

.manual-collapse :deep(.el-collapse-item__header) {
  height: 36px;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: none;
  background: var(--bg-gray-light);
  border-radius: 4px;
  padding: 0 12px;
}

.manual-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.manual-collapse :deep(.el-collapse-item__content) {
  padding: 12px 0 0;
}

.collapse-title {
  font-size: 12px;
}

.manual-input-section {
  display: flex;
  gap: 8px;
}

.manual-input-section .el-input {
  flex: 1;
}

/* 视频列表 */
.video-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 12px;
  background: var(--bg-white);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.video-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  border: 2px solid transparent;
  position: relative;
}

.video-item:hover {
  background: var(--bg-gray);
}

.video-item.is-selected {
  border-color: var(--bili-blue);
  background: #E6F7FF;
}

.video-cover {
  width: 80px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  background: var(--bg-gray);
}

.video-info {
  flex: 1;
  min-width: 0;
}

.video-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.video-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.video-meta .category {
  padding: 0 4px;
  background: var(--bg-gray);
  border-radius: 2px;
}

.video-stats {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--text-secondary);
}

.selected-indicator {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  background: var(--bili-blue);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
}

/* 分页 */
.pagination-wrapper {
  padding-top: 12px;
  margin-top: 12px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

/* 右侧面板 */
.right-panel {
  overflow-y: auto;
  min-height: 0;
}

.empty-state,
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

/* 选中视频卡片 */
.selected-video-card {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-white);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid var(--border-light);
}

.card-cover {
  width: 160px;
  height: 100px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  background: var(--bg-gray);
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.card-meta .author {
  font-size: 13px;
  color: var(--text-secondary);
}

.card-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 结果区块 */
.result-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--bg-white);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.result-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 指标卡片 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: var(--bg-gray-light);
  padding: 14px;
  border-radius: 8px;
  text-align: center;
}

.metric-card.highlight {
  background: #E6F7FF;
}

.metric-card.highlight-coin {
  background: #FFF7E6;
}

.coin-prediction {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-light);
}

.sub-section-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.metric-value.positive {
  color: var(--color-success);
}

.metric-value.negative {
  color: var(--color-error);
}

/* 热度等级 */
.heat-level-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.heat-level-row .label {
  font-size: 13px;
  color: var(--text-secondary);
}

.heat-level {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.heat-hot {
  background: #FFEBE5;
  color: #E6553A;
}

.heat-rising {
  background: #E5F9E7;
  color: #00B578;
}

.heat-normal {
  background: var(--bg-gray);
  color: var(--text-regular);
}

.heat-cold {
  background: #E5F4FF;
  color: #0091FF;
}

/* 图表容器 */
.chart-container {
  margin-top: 16px;
}

.chart-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.feature-chart {
  height: 220px;
}

/* 推荐信息 */
.recommend-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.total-count {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 推荐列表 */
.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.recommend-item:hover {
  background: var(--bg-gray);
}

.recommend-item:hover .analyze-icon {
  opacity: 1;
}

.rank {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: var(--bg-gray);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 11px;
  flex-shrink: 0;
}

.rank.top-3 {
  background: var(--bili-blue);
  color: white;
}

.recommend-item:nth-child(1) .rank {
  background: #FFD93D;
  color: #8B6914;
}

.recommend-item:nth-child(2) .rank {
  background: #C0C0C0;
  color: #5A5A5A;
}

.recommend-item:nth-child(3) .rank {
  background: #CD7F32;
  color: white;
}

.recommend-item .cover {
  width: 64px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  background: var(--bg-gray);
}

.recommend-item .cover-placeholder {
  background: var(--bg-gray-dark);
}

.recommend-item .info {
  flex: 1;
  min-width: 0;
}

.recommend-item .title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.recommend-item .meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.recommend-item .author {
  font-size: 11px;
  color: var(--text-secondary);
}

.recommend-item .stats {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-secondary);
}

.recommend-item .similarity {
  color: var(--bili-blue);
  font-weight: 500;
}

.analyze-icon {
  color: var(--text-secondary);
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

/* 响应式 */
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .main-content {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }

  .left-panel {
    order: 1;
  }

  .right-panel {
    order: 2;
  }
}
</style>
