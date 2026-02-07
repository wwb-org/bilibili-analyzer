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
      </div>
    </div>

    <!-- 实用洞察 -->
    <div class="actionable-content">
      <div class="action-card">
        <div class="section-header">
          <span class="section-title">异动榜</span>
          <span class="section-tip">基于当前周期与上一统计日对比</span>
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
              <span class="action-metric">+{{ (item.change_rate * 100).toFixed(0) }}%</span>
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
              <span class="action-metric">{{ (item.change_rate * 100).toFixed(0) }}%</span>
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

      <div class="action-card">
        <div class="section-header">
          <span class="section-title">预警订阅</span>
          <el-button type="primary" size="small" @click="saveAlertSubscription" :loading="savingSubscription">保存配置</el-button>
        </div>

        <el-form :inline="true" class="alert-form">
          <el-form-item label="启用">
            <el-switch v-model="alertSubscription.enabled" />
          </el-form-item>
          <el-form-item label="最低频次">
            <el-input-number v-model="alertSubscription.min_frequency" :min="1" :max="10000" size="small" />
          </el-form-item>
          <el-form-item label="增长阈值">
            <el-input-number v-model="alertSubscription.growth_threshold" :min="0" :max="100" :step="0.1" :precision="2" size="small" />
          </el-form-item>
          <el-form-item label="机会情感阈值">
            <el-input-number v-model="alertSubscription.opportunity_sentiment_threshold" :min="0" :max="1" :step="0.05" :precision="2" size="small" />
          </el-form-item>
          <el-form-item label="风险情感阈值">
            <el-input-number v-model="alertSubscription.negative_sentiment_threshold" :min="0" :max="1" :step="0.05" :precision="2" size="small" />
          </el-form-item>
          <el-form-item label="高互动阈值">
            <el-input-number v-model="alertSubscription.interaction_threshold" :min="0" :max="1" :step="0.01" :precision="2" size="small" />
          </el-form-item>
          <el-form-item label="命中条数">
            <el-input-number v-model="alertSubscription.top_k" :min="1" :max="100" size="small" />
          </el-form-item>
        </el-form>

        <div class="section-header">
          <span class="section-title">预警命中</span>
          <el-button size="small" @click="loadAlertHits" :loading="loadingAlertHits">刷新命中</el-button>
        </div>
        <el-table :data="alertHits" size="small" stripe max-height="320" v-loading="loadingAlertHits" empty-text="当前无命中">
          <el-table-column prop="word" label="热词" min-width="120" />
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <el-tag :type="row.alert_type === 'risk' ? 'danger' : 'success'" size="small">
                {{ row.alert_type === 'risk' ? '风险' : '机会' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="涨幅" width="90">
            <template #default="{ row }">{{ (row.change_rate * 100).toFixed(0) }}%</template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
        </el-table>
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
  getKeywordAlertSubscription,
  updateKeywordAlertSubscription,
  getKeywordAlertHits,
  compareKeywords,
  exportKeywords
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
const loadingAlertHits = ref(false)
const savingSubscription = ref(false)

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
const contributorVideos = ref([])

// P0 洞察
const moversData = reactive({
  rising: [],
  falling: []
})
const opportunityRiskData = reactive({
  opportunities: [],
  risks: []
})
const alertSubscription = reactive({
  enabled: true,
  min_frequency: 20,
  growth_threshold: 1,
  opportunity_sentiment_threshold: 0.6,
  negative_sentiment_threshold: 0.4,
  interaction_threshold: 0.05,
  top_k: 10
})
const alertHits = ref([])

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

const loadMovers = async () => {
  loadingMovers.value = true
  try {
    const params = {
      ...getFilterParams(),
      top_k: 10,
      min_frequency: alertSubscription.min_frequency
    }
    const res = await getKeywordMovers(params)
    moversData.rising = res.rising || []
    moversData.falling = res.falling || []
  } catch (e) {
    console.error('获取异动榜失败', e)
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
      min_frequency: alertSubscription.min_frequency,
      interaction_threshold: alertSubscription.interaction_threshold
    }
    const res = await getKeywordOpportunityRisk(params)
    opportunityRiskData.opportunities = res.opportunities || []
    opportunityRiskData.risks = res.risks || []
  } catch (e) {
    console.error('获取机会/风险榜失败', e)
  } finally {
    loadingOpportunityRisk.value = false
  }
}

const loadAlertSubscription = async () => {
  try {
    const res = await getKeywordAlertSubscription()
    Object.assign(alertSubscription, res || {})
  } catch (e) {
    console.error('获取预警配置失败', e)
  }
}

const saveAlertSubscription = async () => {
  savingSubscription.value = true
  try {
    const payload = {
      enabled: alertSubscription.enabled,
      min_frequency: alertSubscription.min_frequency,
      growth_threshold: alertSubscription.growth_threshold,
      opportunity_sentiment_threshold: alertSubscription.opportunity_sentiment_threshold,
      negative_sentiment_threshold: alertSubscription.negative_sentiment_threshold,
      interaction_threshold: alertSubscription.interaction_threshold,
      top_k: alertSubscription.top_k
    }
    const res = await updateKeywordAlertSubscription(payload)
    Object.assign(alertSubscription, res || {})
    ElMessage.success('预警配置已保存')
    await Promise.all([loadMovers(), loadOpportunityRisk(), loadAlertHits()])
  } catch (e) {
    ElMessage.error('保存预警配置失败')
  } finally {
    savingSubscription.value = false
  }
}

const loadAlertHits = async () => {
  loadingAlertHits.value = true
  try {
    const params = { ...getFilterParams() }
    const res = await getKeywordAlertHits(params)
    alertHits.value = res.hits || []
  } catch (e) {
    console.error('获取预警命中失败', e)
  } finally {
    loadingAlertHits.value = false
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
    loadAlertHits()
  ])
  loading.value = false
}

// ========== 详情 ==========
const selectKeyword = async (word) => {
  if (selectedWord.value === word) return
  selectedWord.value = word
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
  wordcloudChart?.resize()
  sourcePieChart?.resize()
  trendLineChart?.resize()
  categoryBarChart?.resize()
  compareChart?.resize()
}

// ========== 导出 ==========
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
  if (selectedWord.value && !compareWords.value.includes(selectedWord.value)) {
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
  await loadAlertSubscription()
  await loadAllData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  wordcloudChart?.dispose()
  disposeDetailCharts()
  compareChart?.dispose()
  if (searchTimer) clearTimeout(searchTimer)
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

/* 实用洞察 */
.actionable-content {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  .main-content {
    grid-template-columns: 1fr;
  }

  .action-grid {
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
