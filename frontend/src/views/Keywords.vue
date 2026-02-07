<template>
  <div class="keywords-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">热词分析</h2>
        <span class="page-desc">多维度热词分析，追踪热词趋势变化</span>
      </div>
      <div class="header-right">
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-section">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
            @change="handleFilterChange"
          />
        </el-form-item>
        <el-form-item label="分区">
          <el-select
            v-model="filters.category"
            placeholder="全部分区"
            clearable
            @change="handleFilterChange"
          >
            <el-option
              v-for="cat in categoryOptions"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select
            v-model="filters.source"
            placeholder="全部来源"
            clearable
            @change="handleFilterChange"
          >
            <el-option label="全部来源" value="" />
            <el-option label="视频标题" value="title" />
            <el-option label="用户评论" value="comment" />
            <el-option label="弹幕内容" value="danmaku" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索热词"
            clearable
            @input="handleSearchDebounce"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：热词概览区 -->
      <div class="left-panel">
        <!-- 统计卡片 -->
        <div class="stats-grid" v-loading="loadingOverview">
          <div class="stat-card">
            <div class="stat-value">{{ overviewStats.total_keywords }}</div>
            <div class="stat-label">热词总数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ formatNumber(overviewStats.total_frequency) }}</div>
            <div class="stat-label">总提及次数</div>
          </div>
          <div class="stat-card highlight">
            <div class="stat-value">{{ overviewStats.top_keyword?.word || '-' }}</div>
            <div class="stat-label">TOP1热词</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ overviewStats.new_keywords }}</div>
            <div class="stat-label">新增热词</div>
          </div>
        </div>

        <!-- 来源分布 -->
        <div class="source-dist" v-if="overviewStats.source_distribution">
          <div class="dist-item">
            <span class="dist-label">
              <span class="dot title"></span>标题
            </span>
            <span class="dist-value">{{ formatNumber(overviewStats.source_distribution.title) }}</span>
          </div>
          <div class="dist-item">
            <span class="dist-label">
              <span class="dot comment"></span>评论
            </span>
            <span class="dist-value">{{ formatNumber(overviewStats.source_distribution.comment) }}</span>
          </div>
          <div class="dist-item">
            <span class="dist-label">
              <span class="dot danmaku"></span>弹幕
            </span>
            <span class="dist-value">{{ formatNumber(overviewStats.source_distribution.danmaku) }}</span>
          </div>
        </div>

        <!-- 词云区域 -->
        <div class="wordcloud-section">
          <div class="section-header">
            <span class="section-title">热词词云</span>
            <span class="section-tip">点击词语查看详情</span>
          </div>
          <div ref="wordcloudRef" class="wordcloud-chart" v-loading="loadingWordcloud"></div>
        </div>

        <!-- 热词排行榜 -->
        <div class="ranking-section">
          <div class="section-header">
            <span class="section-title">热词排行榜</span>
            <el-select v-model="orderBy" size="small" @change="loadRanking">
              <el-option label="频次最高" value="frequency" />
              <el-option label="趋势最热" value="trend" />
              <el-option label="热度最高" value="heat" />
            </el-select>
          </div>
          <div class="ranking-list" v-loading="loadingRanking">
            <div
              v-for="(item, index) in rankingData"
              :key="item.word"
              class="ranking-item"
              :class="{ 'is-selected': selectedWord === item.word }"
              @click="selectKeyword(item.word)"
            >
              <span class="rank" :class="getRankClass(index)">{{ index + 1 }}</span>
              <span class="word">{{ item.word }}</span>
              <span class="frequency">{{ formatNumber(item.total_frequency) }}</span>
              <span class="trend" :class="item.trend">
                <el-icon v-if="item.trend === 'up'"><Top /></el-icon>
                <el-icon v-else-if="item.trend === 'down'"><Bottom /></el-icon>
                <el-icon v-else><Minus /></el-icon>
              </span>
            </div>
            <el-empty v-if="!loadingRanking && rankingData.length === 0" description="暂无数据" :image-size="60" />
          </div>
          <div class="ranking-pagination" v-if="rankingTotal > pageSize">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="rankingTotal"
              layout="prev, pager, next"
              small
              @current-change="loadRanking"
            />
          </div>
        </div>
      </div>

      <!-- 右侧：热词详情区 -->
      <div class="right-panel">
        <!-- 未选择状态 -->
        <div v-if="!selectedWord && !loadingDetail" class="empty-state">
          <el-empty description="点击左侧热词查看详情" :image-size="150" />
        </div>

        <!-- 加载中状态 -->
        <div v-else-if="loadingDetail" class="loading-state">
          <el-skeleton :rows="10" animated />
        </div>

        <!-- 详情内容 -->
        <div v-else-if="keywordDetail" class="detail-content">
          <!-- 热词信息卡片 -->
          <div class="keyword-info-card">
            <div class="keyword-word">{{ keywordDetail.word }}</div>
            <div class="keyword-stats">
              <div class="stat-item">
                <span class="label">当前排名</span>
                <span class="value rank">第 {{ keywordDetail.current_rank }} 名</span>
              </div>
              <div class="stat-item">
                <span class="label">总频次</span>
                <span class="value">{{ formatNumber(keywordDetail.total_frequency) }}</span>
              </div>
              <div class="stat-item" v-if="keywordDetail.avg_sentiment">
                <span class="label">情感均分</span>
                <span class="value" :class="getSentimentClass(keywordDetail.avg_sentiment)">
                  {{ keywordDetail.avg_sentiment.toFixed(2) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 来源分布饼图 -->
          <div class="chart-card">
            <div class="chart-title">来源分布</div>
            <div ref="sourcePieRef" class="chart-container"></div>
          </div>

          <!-- 频次趋势折线图 -->
          <div class="chart-card">
            <div class="chart-title">频次趋势</div>
            <div ref="trendLineRef" class="chart-container"></div>
          </div>

          <!-- 分区分布 -->
          <div class="chart-card" v-if="keywordDetail.category_distribution?.length > 0">
            <div class="chart-title">分区分布</div>
            <div ref="categoryBarRef" class="chart-container"></div>
          </div>

          <!-- 关联视频 -->
          <div class="related-videos" v-if="keywordDetail.related_videos?.length > 0">
            <div class="section-title">关联视频</div>
            <div class="video-list">
              <div
                v-for="video in keywordDetail.related_videos"
                :key="video.bvid"
                class="video-item"
                @click="goToVideo(video.bvid)"
              >
                <img :src="video.cover_url" class="video-cover" alt="cover" />
                <div class="video-info">
                  <div class="video-title" :title="video.title">{{ video.title }}</div>
                  <div class="video-meta">{{ formatNumber(video.play_count) }} 播放</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 热词对比弹窗 -->
    <el-dialog v-model="compareDialogVisible" title="热词趋势对比" width="800px">
      <div class="compare-content">
        <div class="compare-words">
          <el-tag
            v-for="word in compareWords"
            :key="word"
            closable
            @close="removeCompareWord(word)"
          >
            {{ word }}
          </el-tag>
          <el-input
            v-if="compareWords.length < 5"
            v-model="newCompareWord"
            size="small"
            placeholder="添加热词"
            style="width: 120px"
            @keyup.enter="addCompareWord"
          />
        </div>
        <div ref="compareChartRef" class="compare-chart" v-loading="loadingCompare"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download, Top, Bottom, Minus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import {
  getKeywordOverview,
  getKeywordWordcloud,
  getKeywordRanking,
  getKeywordDetail,
  compareKeywords,
  getExportUrl
} from '@/api/keywords'
import { getCategories } from '@/api/videos'

const router = useRouter()

// ========== 状态 ==========
const loading = ref(false)
const loadingOverview = ref(false)
const loadingWordcloud = ref(false)
const loadingRanking = ref(false)
const loadingDetail = ref(false)
const loadingCompare = ref(false)

// 筛选条件
const dateRange = ref([])
const filters = reactive({
  category: '',
  source: ''
})
const searchKeyword = ref('')
const orderBy = ref('frequency')
const categoryOptions = ref([])

// 日期快捷选项
const dateShortcuts = [
  { text: '最近7天', value: () => {
    const end = new Date()
    const start = new Date()
    start.setTime(start.getTime() - 7 * 24 * 3600 * 1000)
    return [start, end]
  }},
  { text: '最近30天', value: () => {
    const end = new Date()
    const start = new Date()
    start.setTime(start.getTime() - 30 * 24 * 3600 * 1000)
    return [start, end]
  }}
]

// 数据
const overviewStats = reactive({
  total_keywords: 0,
  total_frequency: 0,
  top_keyword: null,
  new_keywords: 0,
  source_distribution: { title: 0, comment: 0, danmaku: 0 }
})

const wordcloudData = ref([])
const rankingData = ref([])
const rankingTotal = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 详情
const selectedWord = ref('')
const keywordDetail = ref(null)

// 对比
const compareDialogVisible = ref(false)
const compareWords = ref([])
const newCompareWord = ref('')

// 图表引用
const wordcloudRef = ref(null)
const sourcePieRef = ref(null)
const trendLineRef = ref(null)
const categoryBarRef = ref(null)
const compareChartRef = ref(null)

let wordcloudChart = null
let sourcePieChart = null
let trendLineChart = null
let categoryBarChart = null
let compareChart = null
let searchTimer = null

// ========== 方法 ==========
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toString()
}

const getRankClass = (index) => {
  if (index === 0) return 'gold'
  if (index === 1) return 'silver'
  if (index === 2) return 'bronze'
  return ''
}

const getSentimentClass = (score) => {
  if (score >= 0.6) return 'positive'
  if (score <= 0.4) return 'negative'
  return 'neutral'
}

const handleSearchDebounce = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadRanking()
  }, 300)
}

const handleFilterChange = () => {
  loadAllData()
}

const refreshData = () => {
  loadAllData()
}

// ========== 数据加载 ==========
const loadCategories = async () => {
  try {
    const res = await getCategories()
    categoryOptions.value = res || []
  } catch (e) {
    console.error('获取分区失败', e)
  }
}

const getFilterParams = () => {
  const params = {}
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  if (filters.category) params.category = filters.category
  if (filters.source) params.source = filters.source
  return params
}

const loadOverview = async () => {
  loadingOverview.value = true
  try {
    const res = await getKeywordOverview(getFilterParams())
    Object.assign(overviewStats, res)
  } catch (e) {
    console.error('获取概览失败', e)
  } finally {
    loadingOverview.value = false
  }
}

const loadWordcloud = async () => {
  loadingWordcloud.value = true
  try {
    const params = { ...getFilterParams(), top_k: 100 }
    const res = await getKeywordWordcloud(params)
    wordcloudData.value = res.words || []
    await nextTick()
    renderWordcloud()
  } catch (e) {
    console.error('获取词云失败', e)
  } finally {
    loadingWordcloud.value = false
  }
}

const loadRanking = async () => {
  loadingRanking.value = true
  try {
    const params = {
      ...getFilterParams(),
      order_by: orderBy.value,
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchKeyword.value) params.search = searchKeyword.value

    const res = await getKeywordRanking(params)
    rankingData.value = res.items || []
    rankingTotal.value = res.total || 0
  } catch (e) {
    console.error('获取排行榜失败', e)
  } finally {
    loadingRanking.value = false
  }
}

const loadAllData = async () => {
  loading.value = true
  await Promise.all([loadOverview(), loadWordcloud(), loadRanking()])
  loading.value = false
}

// ========== 详情 ==========
const selectKeyword = async (word) => {
  if (selectedWord.value === word) return
  selectedWord.value = word
  loadingDetail.value = true
  disposeDetailCharts()

  try {
    const res = await getKeywordDetail(word, { days: 7 })
    keywordDetail.value = res
    await nextTick()
    renderDetailCharts()
  } catch (e) {
    ElMessage.error('获取详情失败')
    keywordDetail.value = null
  } finally {
    loadingDetail.value = false
  }
}

// ========== 图表 ==========
const disposeDetailCharts = () => {
  sourcePieChart?.dispose()
  trendLineChart?.dispose()
  categoryBarChart?.dispose()
  sourcePieChart = null
  trendLineChart = null
  categoryBarChart = null
}

const renderWordcloud = () => {
  if (!wordcloudRef.value || wordcloudData.value.length === 0) return
  if (wordcloudChart) wordcloudChart.dispose()

  wordcloudChart = echarts.init(wordcloudRef.value)
  const colorMap = {
    title: '#00A1D6',
    comment: '#00B578',
    danmaku: '#FF9736'
  }

  wordcloudChart.setOption({
    tooltip: { show: true, formatter: '{b}: {c}' },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [14, 50],
      rotationRange: [-45, 45],
      gridSize: 8,
      textStyle: {
        fontWeight: 'bold',
        color: (params) => colorMap[params.data.source] || '#61666D'
      },
      data: wordcloudData.value
    }]
  })

  wordcloudChart.on('click', (params) => {
    selectKeyword(params.name)
  })
}

const renderDetailCharts = () => {
  if (!keywordDetail.value) return

  // 来源分布饼图
  if (sourcePieRef.value) {
    sourcePieChart = echarts.init(sourcePieRef.value)
    const dist = keywordDetail.value.source_distribution
    sourcePieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, fontSize: 11, formatter: '{b}\n{d}%' },
        data: [
          { value: dist.title, name: '标题', itemStyle: { color: '#00A1D6' } },
          { value: dist.comment, name: '评论', itemStyle: { color: '#00B578' } },
          { value: dist.danmaku, name: '弹幕', itemStyle: { color: '#FF9736' } }
        ]
      }]
    })
  }

  // 趋势折线图
  if (trendLineRef.value && keywordDetail.value.trend?.length > 0) {
    trendLineChart = echarts.init(trendLineRef.value)
    const trend = keywordDetail.value.trend
    trendLineChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: trend.map(t => t.date.slice(5)),
        axisLabel: { fontSize: 10 }
      },
      yAxis: { type: 'value', name: '频次' },
      series: [{
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3, color: '#00A1D6' },
        itemStyle: { color: '#00A1D6' },
        data: trend.map(t => t.frequency)
      }]
    })
  }

  // 分区分布柱状图
  if (categoryBarRef.value && keywordDetail.value.category_distribution?.length > 0) {
    categoryBarChart = echarts.init(categoryBarRef.value)
    const cats = keywordDetail.value.category_distribution.slice(0, 10)
    categoryBarChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: cats.map(c => c.category),
        axisLabel: { fontSize: 10, rotate: 30 }
      },
      yAxis: { type: 'value', name: '频次' },
      series: [{
        type: 'bar',
        itemStyle: { color: '#00A1D6', borderRadius: [4, 4, 0, 0] },
        data: cats.map(c => c.frequency)
      }]
    })
  }
}

const handleResize = () => {
  wordcloudChart?.resize()
  sourcePieChart?.resize()
  trendLineChart?.resize()
  categoryBarChart?.resize()
  compareChart?.resize()
}

// ========== 导出 ==========
const handleExport = () => {
  const params = {
    format: 'csv',
    ...getFilterParams(),
    top_k: 500
  }
  const url = getExportUrl(params)
  window.open(url, '_blank')
}

// ========== 对比 ==========
const addCompareWord = () => {
  if (newCompareWord.value && compareWords.value.length < 5) {
    if (!compareWords.value.includes(newCompareWord.value)) {
      compareWords.value.push(newCompareWord.value)
    }
    newCompareWord.value = ''
    loadCompareData()
  }
}

const removeCompareWord = (word) => {
  compareWords.value = compareWords.value.filter(w => w !== word)
  loadCompareData()
}

const loadCompareData = async () => {
  if (compareWords.value.length < 2) return
  loadingCompare.value = true
  try {
    const res = await compareKeywords({ words: compareWords.value, days: 7 })
    await nextTick()
    renderCompareChart(res)
  } catch (e) {
    ElMessage.error('对比失败')
  } finally {
    loadingCompare.value = false
  }
}

const renderCompareChart = (data) => {
  if (!compareChartRef.value) return
  if (compareChart) compareChart.dispose()

  compareChart = echarts.init(compareChartRef.value)
  const colors = ['#00A1D6', '#FB7299', '#00B578', '#FF9736', '#9499A0']

  compareChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: data.words, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.trends.map(t => t.date.slice(5))
    },
    yAxis: { type: 'value', name: '频次' },
    series: data.words.map((word, i) => ({
      name: word,
      type: 'line',
      smooth: true,
      itemStyle: { color: colors[i] },
      data: data.trends.map(t => t.frequencies[word] || 0)
    }))
  })
}

// ========== 跳转 ==========
const goToVideo = (bvid) => {
  router.push({ path: '/videos', query: { bvid } })
}

// ========== 生命周期 ==========
onMounted(async () => {
  await loadCategories()
  await loadAllData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  wordcloudChart?.dispose()
  disposeDetailCharts()
  compareChart?.dispose()
})
</script>

<style scoped>
.keywords-container {
  padding: 24px;
  background: var(--bg-gray-light);
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
  gap: 12px;
}

/* 筛选区 */
.filter-section {
  background: var(--bg-white);
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 0;
}

/* 主内容区 */
.main-content {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  background: var(--bg-white);
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.stat-card.highlight {
  background: linear-gradient(135deg, #00A1D6 0%, #00B5E5 100%);
}

.stat-card.highlight .stat-value,
.stat-card.highlight .stat-label {
  color: #fff;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 来源分布 */
.source-dist {
  background: var(--bg-white);
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  justify-content: space-around;
}

.dist-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dist-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.title { background: #00A1D6; }
.dot.comment { background: #00B578; }
.dot.danmaku { background: #FF9736; }

.dist-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 词云区域 */
.wordcloud-section {
  background: var(--bg-white);
  padding: 16px;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.section-tip {
  font-size: 12px;
  color: var(--text-secondary);
}

.wordcloud-chart {
  height: 250px;
}

/* 排行榜 */
.ranking-section {
  background: var(--bg-white);
  padding: 16px;
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.ranking-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}

.ranking-item:hover {
  background: var(--bg-gray-light);
}

.ranking-item.is-selected {
  background: rgba(0, 161, 214, 0.1);
}

.rank {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-gray);
  color: var(--text-secondary);
  margin-right: 12px;
}

.rank.gold { background: #FFD700; color: #fff; }
.rank.silver { background: #C0C0C0; color: #fff; }
.rank.bronze { background: #CD7F32; color: #fff; }

.word {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.frequency {
  font-size: 13px;
  color: var(--text-secondary);
  margin-right: 8px;
}

.trend {
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.trend.up { color: #00B578; }
.trend.down { color: #F56C6C; }
.trend.stable { color: var(--text-secondary); }

.ranking-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

/* 右侧面板 */
.right-panel {
  background: var(--bg-white);
  border-radius: 8px;
  padding: 20px;
  min-height: 600px;
}

.empty-state,
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

/* 详情内容 */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.keyword-info-card {
  background: var(--bg-gray-light);
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.keyword-word {
  font-size: 28px;
  font-weight: 600;
  color: var(--bili-blue);
  margin-bottom: 16px;
}

.keyword-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-item .label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-item .value {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.stat-item .value.rank {
  color: var(--bili-blue);
}

.stat-item .value.positive { color: #00B578; }
.stat-item .value.neutral { color: var(--text-secondary); }
.stat-item .value.negative { color: #F56C6C; }

/* 图表卡片 */
.chart-card {
  background: var(--bg-gray-light);
  padding: 16px;
  border-radius: 8px;
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.chart-container {
  height: 200px;
}

/* 关联视频 */
.related-videos {
  background: var(--bg-gray-light);
  padding: 16px;
  border-radius: 8px;
}

.related-videos .section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-item {
  display: flex;
  gap: 12px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}

.video-item:hover {
  background: var(--bg-white);
}

.video-cover {
  width: 80px;
  height: 50px;
  border-radius: 4px;
  object-fit: cover;
}

.video-info {
  flex: 1;
  overflow: hidden;
}

.video-title {
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 对比弹窗 */
.compare-content {
  padding: 16px 0;
}

.compare-words {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.compare-chart {
  height: 300px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .left-panel {
    order: 2;
  }

  .right-panel {
    order: 1;
    min-height: auto;
  }
}
</style>
