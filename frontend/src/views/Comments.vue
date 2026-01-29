<template>
  <div class="comments-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">评论分析</h2>
        <span class="page-desc">选择视频，深度分析评论区情感与热词</span>
      </div>
      <div class="header-right">
        <el-radio-group v-model="analysisMode" size="small">
          <el-radio-button value="single">单视频分析</el-radio-button>
          <el-radio-button value="compare">多视频对比</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 主内容区 -->
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
            <el-option label="评论最多" value="comment_count" />
            <el-option label="正面最多" value="positive_count" />
            <el-option label="负面最多" value="negative_count" />
          </el-select>
        </div>

        <!-- 视频列表 -->
        <div class="video-list" v-loading="loadingVideos">
          <div
            v-for="video in videos"
            :key="video.bvid"
            class="video-item"
            :class="{
              'is-selected': analysisMode === 'single' && selectedVideo?.bvid === video.bvid,
              'is-checked': analysisMode === 'compare' && selectedBvids.includes(video.bvid)
            }"
            @click="handleVideoClick(video)"
          >
            <!-- 对比模式勾选框 -->
            <el-checkbox
              v-if="analysisMode === 'compare'"
              :model-value="selectedBvids.includes(video.bvid)"
              @click.stop
              @change="toggleVideoSelection(video.bvid)"
              class="video-checkbox"
            />
            <img :src="video.cover_url" class="video-cover" alt="cover" />
            <div class="video-info">
              <div class="video-title" :title="video.title">{{ video.title }}</div>
              <div class="video-meta">
                <span class="comment-count">{{ video.comment_count }} 评论</span>
                <el-tag
                  :type="getSentimentTagType(video.sentiment_summary?.dominant)"
                  size="small"
                  effect="plain"
                >
                  {{ getSentimentText(video.sentiment_summary?.dominant) }}
                </el-tag>
              </div>
            </div>
            <div class="selected-indicator" v-if="analysisMode === 'single' && selectedVideo?.bvid === video.bvid">
              <el-icon><Check /></el-icon>
            </div>
          </div>

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

        <!-- 对比模式底部操作栏 -->
        <div class="compare-actions" v-if="analysisMode === 'compare'">
          <span class="selected-count">已选 {{ selectedBvids.length }}/5</span>
          <el-button
            type="primary"
            size="small"
            :disabled="selectedBvids.length < 2"
            @click="startCompare"
          >
            开始对比
          </el-button>
        </div>
      </div>

      <!-- 右侧：分析结果区 -->
      <div class="right-panel">
        <!-- 未选择状态 -->
        <div v-if="!selectedVideo && !compareResult && !analyzing" class="empty-state">
          <el-empty
            :description="analysisMode === 'single' ? '从左侧选择一个视频开始分析' : '选择2-5个视频进行对比'"
            :image-size="150"
          />
        </div>

        <!-- 分析中状态 -->
        <div v-else-if="analyzing" class="loading-state">
          <el-skeleton :rows="10" animated />
        </div>

        <!-- 单视频分析结果 -->
        <div v-else-if="analysisMode === 'single' && selectedVideo" class="result-content">
          <!-- 视频信息卡片 -->
          <div class="selected-video-card">
            <img :src="selectedVideo.cover_url" class="card-cover" alt="cover" />
            <div class="card-info">
              <div class="card-title">{{ selectedVideo.title }}</div>
              <div class="card-meta">
                <span class="author">{{ selectedVideo.author_name || '未知UP主' }}</span>
                <el-tag v-if="selectedVideo.category" size="small" type="info">{{ selectedVideo.category }}</el-tag>
              </div>
            </div>
            <el-button size="small" @click="handleExport">导出评论</el-button>
          </div>

          <!-- 统计卡片 -->
          <div class="stats-grid" v-if="commentStats">
            <div class="stat-card">
              <div class="stat-value">{{ commentStats.total_count }}</div>
              <div class="stat-label">评论总数</div>
            </div>
            <div class="stat-card positive">
              <div class="stat-value">{{ commentStats.positive_count }}</div>
              <div class="stat-label">正面 {{ commentStats.positive_rate }}%</div>
            </div>
            <div class="stat-card neutral">
              <div class="stat-value">{{ commentStats.neutral_count }}</div>
              <div class="stat-label">中性 {{ commentStats.neutral_rate }}%</div>
            </div>
            <div class="stat-card negative">
              <div class="stat-value">{{ commentStats.negative_count }}</div>
              <div class="stat-label">负面 {{ commentStats.negative_rate }}%</div>
            </div>
          </div>

          <!-- 图表区域 -->
          <div class="charts-row">
            <div class="chart-card">
              <div class="chart-title">情感分布</div>
              <div ref="pieChartRef" class="chart-container"></div>
            </div>
            <div class="chart-card">
              <div class="chart-title">评论词云</div>
              <div ref="wordcloudChartRef" class="chart-container"></div>
            </div>
          </div>

          <!-- 高赞评论 -->
          <div class="section-card" v-if="topComments.length > 0">
            <div class="section-header">
              <span class="section-title">高赞评论 TOP10</span>
            </div>
            <div class="top-comments-list">
              <div v-for="(comment, index) in topComments" :key="comment.id" class="top-comment-item">
                <div class="rank" :class="{ 'top-3': index < 3 }">{{ index + 1 }}</div>
                <div class="comment-content">
                  <div class="comment-text">{{ comment.content }}</div>
                  <div class="comment-meta">
                    <span class="user">{{ comment.user_name }}</span>
                    <el-tag :type="getSentimentTagType(comment.sentiment_label)" size="small">
                      {{ getSentimentText(comment.sentiment_label) }}
                    </el-tag>
                    <span class="likes">{{ comment.like_count }} 赞</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 评论列表 -->
          <div class="section-card">
            <div class="section-header">
              <span class="section-title">评论列表</span>
              <div class="section-filters">
                <el-select v-model="commentSentimentFilter" size="small" placeholder="全部情感" clearable @change="loadCommentList">
                  <el-option label="正面" value="positive" />
                  <el-option label="中性" value="neutral" />
                  <el-option label="负面" value="negative" />
                </el-select>
                <el-select v-model="commentSortBy" size="small" @change="loadCommentList">
                  <el-option label="点赞最多" value="like_count" />
                  <el-option label="最新发布" value="created_at" />
                </el-select>
              </div>
            </div>
            <div class="comments-list" v-loading="loadingComments">
              <div v-for="comment in commentList" :key="comment.id" class="comment-item">
                <div class="comment-header">
                  <span class="user-name">{{ comment.user_name }}</span>
                  <el-tag :type="getSentimentTagType(comment.sentiment_label)" size="small">
                    {{ getSentimentText(comment.sentiment_label) }}
                  </el-tag>
                </div>
                <div class="comment-body">{{ comment.content }}</div>
                <div class="comment-footer">
                  <span class="likes">{{ comment.like_count }} 赞</span>
                  <span class="time">{{ formatTime(comment.created_at) }}</span>
                </div>
              </div>
              <el-empty v-if="!loadingComments && commentList.length === 0" description="暂无评论" :image-size="60" />
            </div>
            <div class="comments-pagination" v-if="commentTotal > commentPageSize">
              <el-pagination
                v-model:current-page="commentPage"
                :page-size="commentPageSize"
                :total="commentTotal"
                layout="prev, pager, next"
                small
                @current-change="loadCommentList"
              />
            </div>
          </div>
        </div>

        <!-- 多视频对比结果 -->
        <div v-else-if="analysisMode === 'compare' && compareResult" class="result-content">
          <!-- 对比统计表格 -->
          <div class="section-card">
            <div class="section-header">
              <span class="section-title">评论统计对比</span>
            </div>
            <el-table :data="compareResult.videos" stripe>
              <el-table-column prop="title" label="视频" min-width="200" show-overflow-tooltip />
              <el-table-column prop="comment_count" label="评论数" width="100" />
              <el-table-column label="正面%" width="80">
                <template #default="{ row }">
                  <span class="positive-text">{{ row.positive_rate }}%</span>
                </template>
              </el-table-column>
              <el-table-column label="中性%" width="80">
                <template #default="{ row }">
                  <span class="neutral-text">{{ row.neutral_rate }}%</span>
                </template>
              </el-table-column>
              <el-table-column label="负面%" width="80">
                <template #default="{ row }">
                  <span class="negative-text">{{ row.negative_rate }}%</span>
                </template>
              </el-table-column>
              <el-table-column prop="avg_sentiment_score" label="平均分" width="80">
                <template #default="{ row }">
                  {{ row.avg_sentiment_score?.toFixed(2) }}
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 对比图表 -->
          <div class="charts-row">
            <div class="chart-card">
              <div class="chart-title">情感分布对比</div>
              <div ref="compareBarChartRef" class="chart-container"></div>
            </div>
            <div class="chart-card">
              <div class="chart-title">评论质量雷达图</div>
              <div ref="compareRadarChartRef" class="chart-container"></div>
            </div>
          </div>

          <!-- 热词对比 -->
          <div class="section-card">
            <div class="section-header">
              <span class="section-title">热词对比</span>
            </div>
            <div class="keywords-compare">
              <div v-for="video in compareResult.videos" :key="video.bvid" class="keywords-column">
                <div class="column-title">{{ video.title }}</div>
                <div class="keywords-list">
                  <el-tag
                    v-for="(kw, idx) in video.top_keywords.slice(0, 10)"
                    :key="idx"
                    size="small"
                    effect="plain"
                  >
                    {{ kw.name }} ({{ kw.value }})
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Check } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import {
  getVideosWithComments,
  getCommentStats,
  getCommentList,
  getCommentWordcloud,
  getTopComments,
  compareComments,
  getCommentExportUrl
} from '@/api/comments'
import { getCategories } from '@/api/videos'

// ========== 模式切换 ==========
const analysisMode = ref('single')

// ========== 视频列表 ==========
const videos = ref([])
const totalVideos = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchKeyword = ref('')
const selectedCategory = ref('')
const orderBy = ref('comment_count')
const categoryOptions = ref([])
const loadingVideos = ref(false)

// ========== 单视频分析 ==========
const selectedVideo = ref(null)
const analyzing = ref(false)
const commentStats = ref(null)
const topComments = ref([])
const wordcloudData = ref([])

// ========== 评论列表 ==========
const commentList = ref([])
const commentTotal = ref(0)
const commentPage = ref(1)
const commentPageSize = ref(20)
const commentSentimentFilter = ref('')
const commentSortBy = ref('like_count')
const loadingComments = ref(false)

// ========== 多视频对比 ==========
const selectedBvids = ref([])
const compareResult = ref(null)

// ========== 图表引用 ==========
const pieChartRef = ref(null)
const wordcloudChartRef = ref(null)
const compareBarChartRef = ref(null)
const compareRadarChartRef = ref(null)
let pieChart = null
let wordcloudChart = null
let compareBarChart = null
let compareRadarChart = null

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

    const res = await getVideosWithComments(params)
    videos.value = res.items || []
    totalVideos.value = res.total || 0
  } catch (e) {
    console.error('加载视频失败', e)
    ElMessage.error('加载视频列表失败')
  } finally {
    loadingVideos.value = false
  }
}

const handleFilterChange = () => {
  currentPage.value = 1
  loadVideos()
}

const handlePageChange = () => {
  loadVideos()
}

// ========== 视频选择 ==========
const handleVideoClick = (video) => {
  if (analysisMode.value === 'single') {
    analyzeVideo(video)
  } else {
    toggleVideoSelection(video.bvid)
  }
}

const toggleVideoSelection = (bvid) => {
  const index = selectedBvids.value.indexOf(bvid)
  if (index > -1) {
    selectedBvids.value.splice(index, 1)
  } else if (selectedBvids.value.length < 5) {
    selectedBvids.value.push(bvid)
  } else {
    ElMessage.warning('最多选择5个视频')
  }
}

// ========== 单视频分析 ==========
const analyzeVideo = async (video) => {
  if (selectedVideo.value?.bvid === video.bvid && commentStats.value) return

  selectedVideo.value = video
  analyzing.value = true
  commentStats.value = null
  topComments.value = []
  wordcloudData.value = []
  commentList.value = []
  commentPage.value = 1

  disposeCharts()

  try {
    const [statsRes, topRes, wcRes] = await Promise.all([
      getCommentStats(video.bvid),
      getTopComments(video.bvid, 10),
      getCommentWordcloud(video.bvid, { top_k: 50 })
    ])

    commentStats.value = statsRes
    topComments.value = topRes.items || []
    wordcloudData.value = wcRes.words || []

    analyzing.value = false
    await nextTick()
    renderPieChart()
    renderWordcloudChart()

    await loadCommentList()
  } catch (e) {
    analyzing.value = false
    ElMessage.error('分析失败: ' + e.message)
  }
}

const loadCommentList = async () => {
  if (!selectedVideo.value) return
  loadingComments.value = true
  try {
    const params = {
      page: commentPage.value,
      page_size: commentPageSize.value,
      sort_by: commentSortBy.value
    }
    if (commentSentimentFilter.value) params.sentiment = commentSentimentFilter.value

    const res = await getCommentList(selectedVideo.value.bvid, params)
    commentList.value = res.items || []
    commentTotal.value = res.total || 0
  } catch (e) {
    console.error('加载评论失败', e)
  } finally {
    loadingComments.value = false
  }
}

// ========== 多视频对比 ==========
const startCompare = async () => {
  if (selectedBvids.value.length < 2) {
    ElMessage.warning('请至少选择2个视频')
    return
  }

  analyzing.value = true
  compareResult.value = null
  disposeCharts()

  try {
    const res = await compareComments(selectedBvids.value)
    compareResult.value = res

    analyzing.value = false
    await nextTick()
    renderCompareBarChart()
    renderCompareRadarChart()
  } catch (e) {
    analyzing.value = false
    ElMessage.error('对比失败: ' + e.message)
  }
}

// ========== 导出 ==========
const handleExport = () => {
  if (!selectedVideo.value) return
  const url = getCommentExportUrl(selectedVideo.value.bvid, commentSentimentFilter.value)
  window.open(url, '_blank')
}

// ========== 图表方法 ==========
const disposeCharts = () => {
  pieChart?.dispose()
  wordcloudChart?.dispose()
  compareBarChart?.dispose()
  compareRadarChart?.dispose()
  pieChart = null
  wordcloudChart = null
  compareBarChart = null
  compareRadarChart = null
}

const renderPieChart = () => {
  if (!pieChartRef.value || !commentStats.value) return
  pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 11, formatter: '{b}\n{d}%' },
      data: [
        { value: commentStats.value.positive_count, name: '正面', itemStyle: { color: '#00B578' } },
        { value: commentStats.value.neutral_count, name: '中性', itemStyle: { color: '#9499A0' } },
        { value: commentStats.value.negative_count, name: '负面', itemStyle: { color: '#F56C6C' } }
      ]
    }]
  })
}

const renderWordcloudChart = () => {
  if (!wordcloudChartRef.value || wordcloudData.value.length === 0) return
  wordcloudChart = echarts.init(wordcloudChartRef.value)
  const colorMap = { positive: '#00B578', neutral: '#9499A0', negative: '#F56C6C' }
  wordcloudChart.setOption({
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [12, 40],
      rotationRange: [-45, 45],
      gridSize: 8,
      textStyle: {
        color: (params) => colorMap[params.data.sentiment] || '#61666D'
      },
      data: wordcloudData.value
    }]
  })
}

const renderCompareBarChart = () => {
  if (!compareBarChartRef.value || !compareResult.value) return
  compareBarChart = echarts.init(compareBarChartRef.value)
  const videos = compareResult.value.videos
  compareBarChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['正面', '中性', '负面'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: videos.map(v => v.title.slice(0, 10) + '...'), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '评论数' },
    series: [
      { name: '正面', type: 'bar', stack: 'total', itemStyle: { color: '#00B578' }, data: videos.map(v => v.positive_count) },
      { name: '中性', type: 'bar', stack: 'total', itemStyle: { color: '#9499A0' }, data: videos.map(v => v.neutral_count) },
      { name: '负面', type: 'bar', stack: 'total', itemStyle: { color: '#F56C6C' }, data: videos.map(v => v.negative_count) }
    ]
  })
}

const renderCompareRadarChart = () => {
  if (!compareRadarChartRef.value || !compareResult.value) return
  compareRadarChart = echarts.init(compareRadarChartRef.value)
  const videos = compareResult.value.videos
  const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#9499A0']
  compareRadarChart.setOption({
    tooltip: {},
    legend: { data: videos.map(v => v.title.slice(0, 8)), bottom: 0, type: 'scroll' },
    radar: {
      indicator: [
        { name: '正面率', max: 100 },
        { name: '平均分', max: 1 },
        { name: '平均赞', max: Math.max(...videos.map(v => v.avg_like_count)) * 1.2 || 100 },
        { name: '评论数', max: Math.max(...videos.map(v => v.comment_count)) * 1.2 || 100 }
      ],
      radius: '60%'
    },
    series: [{
      type: 'radar',
      data: videos.map((v, i) => ({
        name: v.title.slice(0, 8),
        value: [v.positive_rate, v.avg_sentiment_score, v.avg_like_count, v.comment_count],
        lineStyle: { color: colors[i] },
        itemStyle: { color: colors[i] }
      }))
    }]
  })
}

// ========== 工具方法 ==========
const getSentimentTagType = (sentiment) => {
  const map = { positive: 'success', neutral: 'info', negative: 'danger' }
  return map[sentiment] || 'info'
}

const getSentimentText = (sentiment) => {
  const map = { positive: '正面为主', neutral: '中性为主', negative: '负面为主' }
  return map[sentiment] || '未知'
}

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

const handleResize = () => {
  pieChart?.resize()
  wordcloudChart?.resize()
  compareBarChart?.resize()
  compareRadarChart?.resize()
}

// ========== 模式切换监听 ==========
watch(analysisMode, (newMode) => {
  if (newMode === 'single') {
    selectedBvids.value = []
    compareResult.value = null
  } else {
    selectedVideo.value = null
    commentStats.value = null
  }
  disposeCharts()
})

// ========== 生命周期 ==========
onMounted(() => {
  loadCategories()
  loadVideos()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  disposeCharts()
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.comments-container {
  height: calc(100vh - 60px - 48px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

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

.main-content {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 20px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

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

.video-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 12px;
  background: var(--bg-white);
  border-radius: 12px;
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
  transition: all 0.2s;
  border: 2px solid transparent;
  position: relative;
}

.video-item:hover {
  background: var(--bg-gray);
  transform: translateY(-1px);
}

.video-item.is-selected,
.video-item.is-checked {
  border-color: var(--bili-blue);
  background: #E6F7FF;
}

.video-checkbox {
  flex-shrink: 0;
}

.video-cover {
  width: 80px;
  height: 50px;
  object-fit: cover;
  border-radius: 6px;
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
  align-items: center;
  gap: 8px;
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

.pagination-wrapper {
  padding-top: 12px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.compare-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  margin-top: 12px;
}

.selected-count {
  font-size: 13px;
  color: var(--text-secondary);
}

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

.selected-video-card {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-white);
  border-radius: 12px;
  margin-bottom: 16px;
  border: 1px solid var(--border-light);
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.card-cover {
  width: 120px;
  height: 75px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-meta .author {
  font-size: 13px;
  color: var(--text-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.stat-card.positive { color: var(--color-success); }
.stat-card.neutral { color: var(--text-secondary); }
.stat-card.negative { color: var(--color-error); }

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: inherit;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.chart-card {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 4px solid var(--bili-blue);
  line-height: 1;
}

.chart-container {
  height: 240px;
}

.section-card {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  padding-left: 8px;
  border-left: 4px solid var(--bili-blue);
  line-height: 1;
}

.section-filters {
  display: flex;
  gap: 8px;
}

.top-comments-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-comment-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  transition: background 0.2s;
}

.top-comment-item:hover {
  background: var(--bg-gray);
}

.top-comment-item .rank {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: var(--bg-gray);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  flex-shrink: 0;
  color: var(--text-secondary);
}

.top-comment-item .rank.top-3 {
  background: var(--bili-blue);
  color: white;
}

.comment-content {
  flex: 1;
  min-width: 0;
}

.comment-text {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.6;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
}

.comment-item {
  padding: 16px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  transition: background 0.2s;
}

.comment-item:hover {
  background: var(--bg-gray);
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.comment-body {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.6;
  margin-bottom: 8px;
}

.comment-footer {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.comments-pagination {
  padding-top: 16px;
  display: flex;
  justify-content: center;
}

.positive-text { color: var(--color-success); }
.neutral-text { color: var(--text-secondary); }
.negative-text { color: var(--color-error); }

.keywords-compare {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.keywords-column {
  padding: 16px;
  background: var(--bg-gray-light);
  border-radius: 12px;
}

.column-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .main-content {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  .left-panel { max-height: 300px; }
}
</style>
