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
          <el-autocomplete
            v-model="searchKeyword"
            :fetch-suggestions="fetchSearchSuggestions"
            placeholder="搜索热词（全局）"
            clearable
            :trigger-on-focus="false"
            :debounce="300"
            @select="handleSearchSelect"
            @clear="handleSearchDebounce"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #default="{ item }">
              <div class="search-suggestion-item">
                <span class="suggestion-word">{{ item.word }}</span>
                <span class="suggestion-freq">{{ formatNumber(item.total_frequency) }}</span>
                <span class="suggestion-trend" :class="item.trend">
                  <el-icon v-if="item.trend === 'up'" :size="12"><Top /></el-icon>
                  <el-icon v-else-if="item.trend === 'down'" :size="12"><Bottom /></el-icon>
                  <el-icon v-else :size="12"><Minus /></el-icon>
                </span>
              </div>
            </template>
          </el-autocomplete>
        </el-form-item>
      </el-form>
    </div>

    <!-- 数据新鲜度 -->
    <div class="data-freshness" v-if="overviewStats.stat_date">
      <span class="freshness-text">
        数据截至: {{ overviewStats.stat_date }}
        <span v-if="overviewStats.data_days"> | 已积累 {{ overviewStats.data_days }} 天数据</span>
      </span>
      <span v-if="isDataStale" class="stale-warning">
        数据已超过3天未更新，建议执行新的采集任务
      </span>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
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

        <div class="content-row">
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
            <div class="ranking-actions">
              <el-select v-model="orderBy" size="small" @change="loadRanking">
                <el-option label="频次最高" value="frequency" />
                <el-option label="趋势最热" value="trend" />
                <el-option label="热度最高" value="heat" />
              </el-select>
              <el-button size="small" @click="openCompareDialog">趋势对比</el-button>
            </div>
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
    </div>

    <!-- 分区全景 -->
    <div class="category-landscape" v-if="categoryCompareData.length > 0">
      <div class="action-card">
        <div class="section-header">
          <span class="section-title">分区全景</span>
          <span class="section-tip">查看各分区热词格局，发现跨区机会</span>
        </div>
        <div class="category-tabs">
          <span
            v-for="cat in categoryCompareData"
            :key="cat.category"
            class="category-tab"
            :class="{ active: selectedCategory === cat.category }"
            @click="handleCategorySelect(cat.category)"
          >
            {{ cat.category }}
          </span>
        </div>
        <div class="category-legend">
          <span class="legend-item"><span class="legend-dot" style="background:#00A1D6"></span>普通热词</span>
          <span class="legend-item"><span class="legend-dot" style="background:#409EFF"></span>跨区热词</span>
          <span class="legend-item"><span class="legend-dot" style="background:#E6A23C"></span>独有热词</span>
        </div>
        <div ref="categoryBarCompareRef" class="category-bar-chart" v-loading="loadingCategoryCompare"></div>
      </div>
    </div>

    <!-- 热词详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="热词详情"
      size="520px"
      :destroy-on-close="false"
      @opened="onDrawerOpened"
      @close="onDrawerClose"
    >
      <!-- 加载中状态 -->
      <div v-if="loadingDetail" class="drawer-loading">
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

        <!-- 关联热词 -->
        <div class="related-keywords" v-if="keywordDetail.related_keywords?.length > 0">
          <div class="section-title">关联热词</div>
          <div class="section-tip" style="margin-bottom:8px;font-size:12px;color:var(--text-secondary)">基于视频共现分析</div>
          <div class="keyword-tags">
            <el-tag
              v-for="rk in keywordDetail.related_keywords"
              :key="rk.word"
              class="related-tag"
              effect="plain"
              @click="selectKeyword(rk.word)"
              style="cursor:pointer;margin:4px"
            >
              {{ rk.word }} ({{ rk.co_occurrence }})
            </el-tag>
          </div>
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

        <!-- 贡献视频 -->
        <div class="chart-card">
          <div class="chart-title">贡献视频 TOP10（样例估算）</div>
          <el-table
            :data="contributorVideos"
            size="small"
            stripe
            max-height="320"
            v-loading="loadingContributors"
            empty-text="暂无样例贡献视频"
          >
            <el-table-column prop="title" label="视频" min-width="180" show-overflow-tooltip />
            <el-table-column prop="estimated_contribution" label="贡献值" width="90">
              <template #default="{ row }">{{ row.estimated_contribution.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column prop="play_increment" label="播放增量" width="90" />
            <el-table-column prop="comment_increment" label="评论增量" width="90" />
            <el-table-column label="互动率" width="90">
              <template #default="{ row }">{{ (row.interaction_rate * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="primary" link @click="goToVideo(row.bvid)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-drawer>

    <!-- 实用洞察 -->
    <div class="actionable-content">
      <div class="action-card">
        <div class="section-header">
          <span class="section-title">异动榜</span>
          <span class="section-tip">基于当前周期与上一统计日对比</span>
        </div>
        <div v-if="!loadingMovers && !moversData.previous_date" class="data-hint">
          数据积累不足2天，异动分析需要至少2个统计日的数据才能生效，请先完成多次采集与ETL
        </div>
        <div class="action-grid" v-loading="loadingMovers">
          <div class="action-list">
            <div class="action-list-title">爆发词 TOP10</div>
            <div
              v-for="item in moversData.rising"
              :key="`r-${item.word}`"
              class="action-item rise"
              @click="selectKeyword(item.word)"
            >
              <span class="action-word">{{ item.word }}</span>
              <span v-if="item.is_new" class="action-tag new-tag">新</span>
              <span class="action-metric">{{ formatSignedDelta(item.change_abs) }}（{{ formatRatePercent(item.change_rate) }}）</span>
            </div>
            <el-empty v-if="!loadingMovers && moversData.rising.length === 0" description="暂无爆发词" :image-size="48" />
          </div>
          <div class="action-list">
            <div class="action-list-title">下滑词 TOP10</div>
            <div
              v-for="item in moversData.falling"
              :key="`f-${item.word}`"
              class="action-item fall"
              @click="selectKeyword(item.word)"
            >
              <span class="action-word">{{ item.word }}</span>
              <span v-if="item.is_new" class="action-tag new-tag">新</span>
              <span class="action-metric">{{ formatSignedDelta(item.change_abs) }}（{{ formatRatePercent(item.change_rate) }}）</span>
            </div>
            <el-empty v-if="!loadingMovers && moversData.falling.length === 0" description="暂无下滑词" :image-size="48" />
          </div>
        </div>
      </div>

      <div class="action-card">
        <div class="section-header">
          <span class="section-title">机会榜 / 风险榜</span>
          <span class="section-tip">综合增长、情感、互动样本占比</span>
        </div>
        <div class="action-grid" v-loading="loadingOpportunityRisk">
          <div class="action-list">
            <div class="action-list-title">机会词 TOP10</div>
            <div
              v-for="item in opportunityRiskData.opportunities"
              :key="`o-${item.word}`"
              class="action-item opportunity"
              @click="selectKeyword(item.word)"
            >
              <span class="action-word">{{ item.word }}</span>
              <span class="action-metric">{{ item.score.toFixed(2) }}</span>
            </div>
            <el-empty v-if="!loadingOpportunityRisk && opportunityRiskData.opportunities.length === 0" description="暂无机会词" :image-size="48" />
          </div>
          <div class="action-list">
            <div class="action-list-title">风险词 TOP10</div>
            <div
              v-for="item in opportunityRiskData.risks"
              :key="`k-${item.word}`"
              class="action-item risk"
              @click="selectKeyword(item.word)"
            >
              <span class="action-word">{{ item.word }}</span>
              <span class="action-metric">{{ item.score.toFixed(2) }}</span>
            </div>
            <el-empty v-if="!loadingOpportunityRisk && opportunityRiskData.risks.length === 0" description="暂无风险词" :image-size="48" />
          </div>
        </div>
      </div>

      <!-- 选题建议 -->
      <div class="action-card" v-loading="loadingSuggestions">
        <div class="section-header">
          <span class="section-title">选题建议</span>
          <span class="section-tip">基于热词趋势、竞争度、情感综合分析</span>
        </div>
        <div class="suggestions-grid" v-if="suggestionsData.length > 0">
          <div
            v-for="item in suggestionsData"
            :key="item.word"
            class="suggestion-card"
            @click="selectKeyword(item.word)"
          >
            <div class="suggestion-header">
              <span class="suggestion-word">{{ item.word }}</span>
              <span class="suggestion-score">{{ item.opportunity_score.toFixed(2) }}</span>
            </div>
            <div class="suggestion-tags">
              <el-tag
                size="small"
                :type="item.competition === 'low' ? 'success' : item.competition === 'medium' ? 'warning' : 'danger'"
              >
                {{ item.competition === 'low' ? '低竞争' : item.competition === 'medium' ? '中竞争' : '高竞争' }}
              </el-tag>
              <el-tag size="small" :type="item.trend_direction === 'rising' ? 'success' : item.trend_direction === 'falling' ? 'danger' : 'info'">
                {{ item.trend_direction === 'rising' ? '上升' : item.trend_direction === 'falling' ? '下降' : '平稳' }}
              </el-tag>
            </div>
            <div class="suggestion-text">{{ item.suggestion_text }}</div>
            <div class="suggestion-gaps" v-if="item.category_gaps.length > 0">
              <span class="gap-label">分区缺口:</span>
              <el-tag v-for="gap in item.category_gaps" :key="gap.category" size="small" type="warning" effect="plain">
                {{ gap.category }}
              </el-tag>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!loadingSuggestions" description="暂无选题建议" :image-size="48" />
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
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download, Top, Bottom, Minus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import {
  getKeywordOverview,
  getKeywordWordcloud,
  getKeywordRanking,
  getKeywordMovers,
  getKeywordOpportunityRisk,
  getKeywordDetail,
  getKeywordContributors,
  compareKeywords,
  exportKeywords,
  getCategoryCompare,
  getContentSuggestions
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
const loadingMovers = ref(false)
const loadingOpportunityRisk = ref(false)
const loadingContributors = ref(false)
const loadingCategoryCompare = ref(false)
const loadingSuggestions = ref(false)

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
  source_distribution: { title: 0, comment: 0, danmaku: 0 },
  stat_date: null,
  data_days: 0
})

const wordcloudData = ref([])
const rankingData = ref([])
const rankingTotal = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 详情
const selectedWord = ref('')
const keywordDetail = ref(null)
const contributorVideos = ref([])
const detailDrawerVisible = ref(false)

// P0 洞察
const moversData = reactive({
  rising: [],
  falling: [],
  previous_date: null
})
const opportunityRiskData = reactive({
  opportunities: [],
  risks: []
})

// 分区全景
const categoryCompareData = ref([])
const selectedCategory = ref('')

// 选题建议
const suggestionsData = ref([])

// 搜索建议
const searchSuggestions = ref([])

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
const categoryBarCompareRef = ref(null)

let wordcloudChart = null
let categoryBarCompareChart = null
let sourcePieChart = null
let trendLineChart = null
let categoryBarChart = null
let compareChart = null
let searchTimer = null
let resizeTimer = null

// ========== 方法 ==========
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toString()
}

const formatSignedDelta = (value) => {
  const num = Number(value || 0)
  const abs = Math.abs(num)
  const text = formatNumber(abs)
  if (num > 0) return `+${text}`
  if (num < 0) return `-${text}`
  return text
}

const formatRatePercent = (rate) => {
  return `${(Number(rate || 0) * 100).toFixed(0)}%`
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

const isDataStale = ref(false)
const checkDataFreshness = () => {
  if (!overviewStats.stat_date) {
    isDataStale.value = false
    return
  }
  const statDate = new Date(overviewStats.stat_date)
  const now = new Date()
  const diffDays = Math.floor((now - statDate) / (24 * 3600 * 1000))
  isDataStale.value = diffDays > 3
}

const getTrendDays = () => {
  if (dateRange.value?.length === 2) {
    const start = new Date(dateRange.value[0])
    const end = new Date(dateRange.value[1])
    const diff = Math.floor((end - start) / (24 * 3600 * 1000)) + 1
    return Math.max(1, Math.min(diff, 30))
  }
  return 7
}

const handleSearchDebounce = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadRanking()
  }, 300)
}

const handleFilterChange = () => {
  currentPage.value = 1
  selectedWord.value = ''
  keywordDetail.value = null
  contributorVideos.value = []
  detailDrawerVisible.value = false
  disposeDetailCharts()
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
    checkDataFreshness()
  } catch (e) {
    console.error('获取概览失败', e)
    ElMessage.warning('获取概览数据失败')
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
    ElMessage.warning('获取词云数据失败')
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
    ElMessage.warning('获取排行榜失败')
  } finally {
    loadingRanking.value = false
  }
}

const loadMovers = async () => {
  loadingMovers.value = true
  try {
    const params = {
      ...getFilterParams(),
      top_k: 10,
      min_frequency: 20
    }
    const res = await getKeywordMovers(params)
    moversData.rising = res.rising || []
    moversData.falling = res.falling || []
    moversData.previous_date = res.previous_date || null
  } catch (e) {
    console.error('获取异动榜失败', e)
    ElMessage.warning('获取异动数据失败')
  } finally {
    loadingMovers.value = false
  }
}

const loadOpportunityRisk = async () => {
  loadingOpportunityRisk.value = true
  try {
    const params = {
      ...getFilterParams(),
      top_k: 10,
      min_frequency: 20,
      interaction_threshold: 0.05
    }
    const res = await getKeywordOpportunityRisk(params)
    opportunityRiskData.opportunities = res.opportunities || []
    opportunityRiskData.risks = res.risks || []
  } catch (e) {
    console.error('获取机会/风险榜失败', e)
    ElMessage.warning('获取机会/风险数据失败')
  } finally {
    loadingOpportunityRisk.value = false
  }
}

const loadCategoryCompare = async () => {
  loadingCategoryCompare.value = true
  try {
    const params = { top_k: 10 }
    const res = await getCategoryCompare(params)
    categoryCompareData.value = res.categories || []
    if (categoryCompareData.value.length > 0 && !selectedCategory.value) {
      selectedCategory.value = categoryCompareData.value[0].category
    }
    await nextTick()
    renderCategoryBarCompare()
  } catch (e) {
    console.error('获取分区全景失败', e)
  } finally {
    loadingCategoryCompare.value = false
  }
}

const loadSuggestions = async () => {
  loadingSuggestions.value = true
  try {
    const params = {
      ...getFilterParams(),
      top_k: 5,
      min_frequency: 20
    }
    const res = await getContentSuggestions(params)
    suggestionsData.value = res.suggestions || []
  } catch (e) {
    console.error('获取选题建议失败', e)
  } finally {
    loadingSuggestions.value = false
  }
}

const loadAllData = async () => {
  loading.value = true
  await Promise.all([
    loadOverview(),
    loadWordcloud(),
    loadRanking(),
    loadMovers(),
    loadOpportunityRisk(),
    loadCategoryCompare(),
    loadSuggestions()
  ])
  loading.value = false
}

// ========== 详情 ==========
const selectKeyword = async (word) => {
  if (selectedWord.value === word) {
    detailDrawerVisible.value = true
    return
  }
  selectedWord.value = word
  detailDrawerVisible.value = true
  loadingDetail.value = true
  contributorVideos.value = []
  disposeDetailCharts()

  try {
    const detailParams = { days: getTrendDays() }
    if (filters.category) detailParams.category = filters.category
    const res = await getKeywordDetail(word, detailParams)
    keywordDetail.value = res
    await loadContributors(word)
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

const onDrawerOpened = () => {
  if (keywordDetail.value && !loadingDetail.value) {
    nextTick(() => {
      disposeDetailCharts()
      renderDetailCharts()
    })
  }
}

const onDrawerClose = () => {
  selectedWord.value = ''
  keywordDetail.value = null
  contributorVideos.value = []
  disposeDetailCharts()
}

const renderWordcloud = () => {
  if (wordcloudChart) wordcloudChart.dispose()
  if (!wordcloudRef.value || wordcloudData.value.length === 0) {
    wordcloudChart = null
    return
  }

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
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    wordcloudChart?.resize()
    sourcePieChart?.resize()
    trendLineChart?.resize()
    categoryBarChart?.resize()
    compareChart?.resize()
    categoryBarCompareChart?.resize()
  }, 200)
}

// ========== 导出 ==========

// 分区全景图表
const renderCategoryBarCompare = () => {
  if (categoryBarCompareChart) categoryBarCompareChart.dispose()
  if (!categoryBarCompareRef.value) return

  const catData = categoryCompareData.value.find(c => c.category === selectedCategory.value)
  if (!catData || !catData.keywords?.length) {
    categoryBarCompareChart = null
    return
  }

  categoryBarCompareChart = echarts.init(categoryBarCompareRef.value)
  const keywords = catData.keywords.slice(0, 10)

  categoryBarCompareChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const d = params[0]
        const kw = keywords[d.dataIndex]
        let tip = `${d.name}: ${d.value}`
        if (kw.is_niche) tip += '<br/><span style="color:#E6A23C">独有热词</span>'
        else if (kw.cross_category_count >= 3) tip += `<br/><span style="color:#409EFF">跨${kw.cross_category_count}个分区</span>`
        return tip
      }
    },
    grid: { left: '3%', right: '8%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'value', name: '频次' },
    yAxis: {
      type: 'category',
      data: keywords.map(k => k.word).reverse(),
      axisLabel: { fontSize: 12 }
    },
    series: [{
      type: 'bar',
      data: keywords.map(k => ({
        value: k.frequency,
        itemStyle: {
          color: k.is_niche ? '#E6A23C' : (k.cross_category_count >= 3 ? '#409EFF' : '#00A1D6'),
          borderRadius: [0, 4, 4, 0]
        }
      })).reverse()
    }]
  })

  categoryBarCompareChart.on('click', (params) => {
    const kw = keywords[keywords.length - 1 - params.dataIndex]
    if (kw) selectKeyword(kw.word)
  })
}

const handleCategorySelect = (cat) => {
  selectedCategory.value = cat
  nextTick(() => renderCategoryBarCompare())
}

// 搜索建议
const fetchSearchSuggestions = async (queryString, cb) => {
  if (!queryString || queryString.length < 1) {
    cb([])
    return
  }
  try {
    const params = {
      ...getFilterParams(),
      search: queryString,
      page: 1,
      page_size: 10,
      order_by: 'frequency'
    }
    const res = await getKeywordRanking(params)
    cb((res.items || []).map(item => ({
      ...item,
      value: item.word
    })))
  } catch (e) {
    cb([])
  }
}

const handleSearchSelect = (item) => {
  selectKeyword(item.word)
}

// ========== 导出（原有） ==========
const handleExport = async () => {
  try {
    const params = {
      format: 'csv',
      ...getFilterParams(),
      top_k: 500
    }
    const blob = await exportKeywords(params)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `keywords_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const loadContributors = async (word) => {
  loadingContributors.value = true
  try {
    const params = {
      ...getFilterParams(),
      limit: 10
    }
    const res = await getKeywordContributors(word, params)
    contributorVideos.value = res.items || []
  } catch (e) {
    contributorVideos.value = []
    console.error('获取贡献视频失败', e)
  } finally {
    loadingContributors.value = false
  }
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
  if (compareWords.value.length < 2) {
    compareChart?.dispose()
    compareChart = null
    return
  }
  loadingCompare.value = true
  try {
    const payload = { words: compareWords.value, days: getTrendDays() }
    if (filters.category) payload.category = filters.category
    const res = await compareKeywords(payload)
    await nextTick()
    renderCompareChart(res)
  } catch (e) {
    ElMessage.error('对比失败')
  } finally {
    loadingCompare.value = false
  }
}

const openCompareDialog = () => {
  compareDialogVisible.value = true
  if (selectedWord.value && !compareWords.value.includes(selectedWord.value) && compareWords.value.length < 5) {
    compareWords.value.push(selectedWord.value)
  }
  loadCompareData()
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
  categoryBarCompareChart?.dispose()
  if (searchTimer) clearTimeout(searchTimer)
  if (resizeTimer) clearTimeout(resizeTimer)
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

/* 数据新鲜度 */
.data-freshness {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--bg-white);
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 12px;
}

.freshness-text {
  color: var(--text-secondary);
}

.stale-warning {
  color: #E6A23C;
  font-weight: 500;
}

/* 搜索建议 */
.search-suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.search-suggestion-item .suggestion-word {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.search-suggestion-item .suggestion-freq {
  font-size: 12px;
  color: var(--text-secondary);
}

.search-suggestion-item .suggestion-trend {
  width: 16px;
}

.search-suggestion-item .suggestion-trend.up { color: #00B578; }
.search-suggestion-item .suggestion-trend.down { color: #F56C6C; }
.search-suggestion-item .suggestion-trend.stable { color: var(--text-secondary); }

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
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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

/* 词云 + 排行榜 并排 */
.content-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
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

.ranking-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

/* 抽屉内部 */
.drawer-loading {
  padding: 20px;
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

/* 关联热词 */
.related-keywords {
  background: var(--bg-gray-light);
  padding: 16px;
  border-radius: 8px;
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.related-tag:hover {
  background: rgba(0, 161, 214, 0.1);
  border-color: #00A1D6;
  color: #00A1D6;
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

/* 实用洞察 */
.actionable-content {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 分区全景 */
.category-landscape {
  margin-top: 16px;
}

.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.category-tab {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-gray-light);
  cursor: pointer;
  transition: all 0.15s;
}

.category-tab:hover {
  color: var(--text-primary);
  background: var(--bg-gray);
}

.category-tab.active {
  color: #fff;
  background: #00A1D6;
}

.category-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.category-bar-chart {
  height: 280px;
}

.action-card {
  background: var(--bg-white);
  border-radius: 8px;
  padding: 16px;
}

.action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.data-hint {
  font-size: 13px;
  color: #E6A23C;
  background: #FDF6EC;
  border: 1px solid #FAECD8;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.action-list {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 12px;
}

.action-list-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.action-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 6px;
  transition: background 0.15s;
}

.action-item:hover {
  background: var(--bg-white);
}

.action-item.rise .action-metric,
.action-item.opportunity .action-metric {
  color: #00B578;
}

.action-item.fall .action-metric,
.action-item.risk .action-metric {
  color: #F56C6C;
}

.action-word {
  font-size: 13px;
  color: var(--text-primary);
}

.action-metric {
  font-size: 12px;
  font-weight: 500;
}

.action-tag.new-tag {
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: #00A1D6;
  padding: 1px 6px;
  border-radius: 3px;
}

/* 选题建议 */
.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.suggestion-card {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.suggestion-card:hover {
  border-color: #00A1D6;
  box-shadow: 0 2px 8px rgba(0, 161, 214, 0.1);
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.suggestion-header .suggestion-word {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.suggestion-score {
  font-size: 13px;
  font-weight: 500;
  color: #00B578;
}

.suggestion-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.suggestion-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 6px;
}

.suggestion-gaps {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.gap-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.alert-form {
  margin-bottom: 12px;
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
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-row {
    grid-template-columns: 1fr;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
