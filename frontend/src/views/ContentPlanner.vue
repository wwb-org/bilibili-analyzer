<template>
  <div class="planner-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">内容策划助手</h2>
        <span class="page-desc">基于历史爆款数据，分析高流量视频的共同特征</span>
      </div>
    </div>

    <!-- 分区选择器 -->
    <div class="filter-bar">
      <el-select
        v-model="selectedCategory"
        placeholder="选择视频分区"
        style="width: 200px"
        @change="onCategoryChange"
      >
        <el-option
          v-for="cat in categories"
          :key="cat"
          :label="cat"
          :value="cat"
        />
      </el-select>
      <el-button
        type="primary"
        :loading="loading"
        :disabled="!selectedCategory"
        @click="runAnalysis"
      >
        <el-icon><DataAnalysis /></el-icon>
        开始分析
      </el-button>
    </div>

    <!-- 无分区提示 -->
    <div v-if="!selectedCategory && !loading" class="empty-hint">
      <el-icon class="hint-icon"><Promotion /></el-icon>
      <p>选择一个分区，分析该分区的爆款内容特征</p>
    </div>

    <template v-if="analysisReady">
      <!-- 第一行：爆款特征 + 关键词 -->
      <div class="analysis-row">
        <!-- 爆款特征 -->
        <div class="card feature-card">
          <div class="card-header">
            <h3 class="card-title"><el-icon><Trophy /></el-icon> 爆款特征</h3>
            <el-tag type="warning" size="small">{{ selectedCategory }}</el-tag>
          </div>

          <div class="feature-stats">
            <div class="stat-item">
              <span class="stat-label">爆款门槛</span>
              <span class="stat-value primary">{{ formatNum(features.viral_threshold) }}</span>
              <span class="stat-unit">播放量</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最优标题长度</span>
              <span class="stat-value">{{ features.title_length?.viral?.p25 }}~{{ features.title_length?.viral?.p75 }}</span>
              <span class="stat-unit">字</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">爆款互动率</span>
              <span class="stat-value primary">{{ features.interaction_rate?.viral_avg }}%</span>
              <span class="stat-unit">均值</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">普通视频互动率</span>
              <span class="stat-value">{{ features.interaction_rate?.all_avg }}%</span>
              <span class="stat-unit">均值</span>
            </div>
          </div>

          <div class="publish-advice">
            <div class="advice-item">
              <el-icon><Clock /></el-icon>
              <span>最佳发布时段：
                <strong v-if="features.best_publish_hours?.length">
                  {{ features.best_publish_hours.map(h => h + ':00').join('、') }}
                </strong>
                <span v-else class="no-data">暂无数据</span>
              </span>
            </div>
            <div class="advice-item">
              <el-icon><Calendar /></el-icon>
              <span>最佳发布日：
                <strong v-if="features.best_publish_weekdays?.length">
                  {{ features.best_publish_weekdays.join('、') }}
                </strong>
                <span v-else class="no-data">暂无数据</span>
              </span>
            </div>
          </div>

          <!-- 发布时段分布 -->
          <div class="hour-chart-wrap">
            <div class="chart-label">24小时发布分布</div>
            <div class="hour-bars">
              <div
                v-for="h in 24"
                :key="h"
                class="hour-bar-col"
                :title="`${h-1}:00 — ${hourDist[h-1] || 0} 个爆款`"
              >
                <div
                  class="hour-bar"
                  :style="{ height: barHeight(hourDist[h-1] || 0) + 'px' }"
                  :class="{ 'is-best': features.best_publish_hours?.includes(h-1) }"
                ></div>
                <span class="hour-label" v-if="(h-1) % 6 === 0">{{ h-1 }}h</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 爆款关键词 -->
        <div class="card keyword-card">
          <div class="card-header">
            <h3 class="card-title"><el-icon><PriceTag /></el-icon> 爆款关键词</h3>
            <span class="card-desc">点击关键词插入标题输入框</span>
          </div>
          <div v-if="keywords.length" class="keyword-cloud">
            <span
              v-for="kw in keywords"
              :key="kw.word"
              class="kw-tag"
              :class="kwLevel(kw.heat_score)"
              @click="insertKeyword(kw.word)"
            >
              {{ kw.word }}
              <small v-if="kw.frequency_trend > 0" class="trend-up">↑</small>
              <small v-else-if="kw.frequency_trend < 0" class="trend-down">↓</small>
            </span>
          </div>
          <div v-else class="empty-block">暂无关键词数据</div>
        </div>
      </div>

      <!-- 第二行：标题建议 -->
      <div class="card suggestions-card">
        <div class="card-header">
          <h3 class="card-title"><el-icon><EditPen /></el-icon> 标题建议</h3>
          <div class="card-actions">
            <span class="card-desc">基于爆款模式自动生成，点击标题复制</span>
            <el-button size="small" text @click="refreshSuggestions" :loading="suggestionsLoading">
              <el-icon><Refresh /></el-icon> 换一批
            </el-button>
          </div>
        </div>
        <div v-if="suggestions.length" class="suggestion-list">
          <div
            v-for="(s, idx) in suggestions"
            :key="idx"
            class="suggestion-item"
            @click="copyTitle(s.title)"
          >
            <span class="suggestion-index">{{ idx + 1 }}</span>
            <div class="suggestion-content">
              <span class="suggestion-title">{{ s.title }}</span>
              <div class="suggestion-meta">
                <el-tag size="small" type="info">{{ s.pattern }}</el-tag>
                <span class="hit-rate">该结构爆款命中率 {{ s.pattern_hit_rate }}%</span>
              </div>
            </div>
            <el-icon class="copy-icon"><DocumentCopy /></el-icon>
          </div>
        </div>
        <div v-else-if="suggestionsLoading" class="empty-block">生成中...</div>
        <div v-else class="empty-block">暂无建议，数据不足时请先采集更多视频</div>
      </div>

      <!-- 第三行：标题评分 -->
      <div class="card score-card">
        <div class="card-header">
          <h3 class="card-title"><el-icon><Star /></el-icon> 标题评分</h3>
          <span class="card-desc">输入你的标题，系统从关键词热度、长度、结构三个维度打分</span>
        </div>
        <div class="score-input-row">
          <el-input
            v-model="inputTitle"
            placeholder="输入你想要的标题..."
            class="title-input"
            maxlength="100"
            show-word-limit
            @keyup.enter="doScore"
          />
          <el-button type="primary" @click="doScore" :loading="scoreLoading">评分</el-button>
        </div>

        <div v-if="scoreResult" class="score-result">
          <!-- 总分 -->
          <div class="total-score-wrap">
            <el-progress
              type="circle"
              :percentage="scoreResult.total_score"
              :color="scoreColor(scoreResult.total_score)"
              :width="100"
            >
              <template #default>
                <span class="score-center">{{ scoreResult.total_score }}</span>
              </template>
            </el-progress>
            <div class="score-label">综合得分</div>
          </div>

          <!-- 分项 -->
          <div class="score-breakdown">
            <div class="score-dim">
              <div class="dim-label">关键词热度</div>
              <el-progress
                :percentage="Math.round(scoreResult.keyword_score / scoreResult.keyword_max * 100)"
                :color="'#00A1D6'"
                :stroke-width="10"
              />
              <span class="dim-value">{{ scoreResult.keyword_score }}/{{ scoreResult.keyword_max }}</span>
            </div>
            <div class="score-dim">
              <div class="dim-label">标题长度</div>
              <el-progress
                :percentage="Math.round(scoreResult.length_score / scoreResult.length_max * 100)"
                :color="'#00B578'"
                :stroke-width="10"
              />
              <span class="dim-value">{{ scoreResult.length_score }}/{{ scoreResult.length_max }}</span>
            </div>
            <div class="score-dim">
              <div class="dim-label">结构模式</div>
              <el-progress
                :percentage="Math.round(scoreResult.structure_score / scoreResult.structure_max * 100)"
                :color="'#FF9736'"
                :stroke-width="10"
              />
              <span class="dim-value">{{ scoreResult.structure_score }}/{{ scoreResult.structure_max }}</span>
            </div>
          </div>

          <!-- 详情标签 -->
          <div class="score-detail">
            <div v-if="scoreResult.matched_keywords?.length" class="detail-row">
              <span class="detail-label">命中热词：</span>
              <el-tag v-for="w in scoreResult.matched_keywords" :key="w" size="small" type="success" class="detail-tag">{{ w }}</el-tag>
            </div>
            <div v-if="scoreResult.matched_patterns?.length" class="detail-row">
              <span class="detail-label">命中结构：</span>
              <el-tag v-for="p in scoreResult.matched_patterns" :key="p" size="small" type="warning" class="detail-tag">{{ p }}</el-tag>
            </div>
            <div class="detail-row">
              <span class="detail-label">最优字数：</span>
              <span>{{ scoreResult.optimal_length?.min }}~{{ scoreResult.optimal_length?.max }} 字（当前 {{ scoreResult.current_length }} 字）</span>
            </div>
          </div>

          <!-- 改进建议 -->
          <div class="suggestions-box">
            <div class="suggestions-title">改进建议</div>
            <div v-for="(s, i) in scoreResult.suggestions" :key="i" class="suggestion-tip">
              <el-icon><InfoFilled /></el-icon>
              {{ s }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis, Promotion, Trophy, PriceTag, EditPen, Star,
  Clock, Calendar, Refresh, DocumentCopy, InfoFilled
} from '@element-plus/icons-vue'
import {
  getCategories,
  getCategoryAnalysis,
  getViralKeywords,
  getTitleSuggestions,
  scoreTitle,
} from '@/api/content_planner'
import { useContentPlannerStore } from '@/store/contentPlanner'

const plannerStore = useContentPlannerStore()

const categories = ref([])
const selectedCategory = ref('')
const loading = ref(false)
const suggestionsLoading = ref(false)
const scoreLoading = ref(false)
const analysisReady = ref(false)

const features = ref({})
const keywords = ref([])
const suggestions = ref([])
const scoreResult = ref(null)
const inputTitle = ref('')

const hourDist = computed(() => {
  const dist = features.value.hour_distribution || {}
  return Array.from({ length: 24 }, (_, i) => dist[String(i)] || 0)
})

const maxHourCount = computed(() => Math.max(...hourDist.value, 1))

const barHeight = (count) => Math.max(2, Math.round((count / maxHourCount.value) * 48))

const formatNum = (n) => {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return String(n)
}

const kwLevel = (heat) => {
  if (heat >= 0.7) return 'kw-hot'
  if (heat >= 0.4) return 'kw-warm'
  return 'kw-cool'
}

const scoreColor = (score) => {
  if (score >= 80) return '#00B578'
  if (score >= 60) return '#FF9736'
  return '#F56C6C'
}

// ========== 缓存存取 ==========
const saveToStore = () => {
  plannerStore.selectedCategory = selectedCategory.value
  plannerStore.categories = categories.value
  plannerStore.analysisReady = analysisReady.value
  plannerStore.features = features.value
  plannerStore.keywords = keywords.value
  plannerStore.suggestions = suggestions.value
  plannerStore.inputTitle = inputTitle.value
  plannerStore.scoreResult = scoreResult.value
  plannerStore.cachedAt = Date.now()
}

const restoreFromStore = () => {
  selectedCategory.value = plannerStore.selectedCategory
  categories.value = plannerStore.categories
  analysisReady.value = plannerStore.analysisReady
  features.value = plannerStore.features
  keywords.value = plannerStore.keywords
  suggestions.value = plannerStore.suggestions
  inputTitle.value = plannerStore.inputTitle
  scoreResult.value = plannerStore.scoreResult
}

onMounted(async () => {
  if (plannerStore.isFresh && plannerStore.categories.length > 0) {
    restoreFromStore()
  } else {
    try {
      const res = await getCategories()
      categories.value = res.categories || []
    } catch {
      categories.value = []
    }
  }
})

onBeforeUnmount(() => {
  saveToStore()
})

const onCategoryChange = () => {
  analysisReady.value = false
  features.value = {}
  keywords.value = []
  suggestions.value = []
  scoreResult.value = null
}

const runAnalysis = async () => {
  if (!selectedCategory.value) return
  loading.value = true
  analysisReady.value = false

  try {
    const [featRes, kwRes] = await Promise.all([
      getCategoryAnalysis(selectedCategory.value),
      getViralKeywords(selectedCategory.value),
    ])
    features.value = featRes
    keywords.value = kwRes.keywords || []
    analysisReady.value = true

    // 异步加载标题建议
    loadSuggestions()
  } catch (e) {
    ElMessage.error('分析失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

const loadSuggestions = async () => {
  suggestionsLoading.value = true
  try {
    const res = await getTitleSuggestions(selectedCategory.value, 5)
    suggestions.value = res.suggestions || []
  } catch {
    suggestions.value = []
  } finally {
    suggestionsLoading.value = false
  }
}

const refreshSuggestions = () => loadSuggestions()

const copyTitle = async (title) => {
  try {
    await navigator.clipboard.writeText(title)
    ElMessage.success('已复制到剪贴板')
  } catch {
    inputTitle.value = title
    ElMessage.info('已填入评分输入框')
  }
}

const insertKeyword = (word) => {
  inputTitle.value = inputTitle.value ? inputTitle.value + word : word
}

const doScore = async () => {
  if (!inputTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择分区')
    return
  }
  scoreLoading.value = true
  try {
    const res = await scoreTitle(inputTitle.value, selectedCategory.value)
    scoreResult.value = res
  } catch {
    ElMessage.error('评分失败')
  } finally {
    scoreLoading.value = false
  }
}
</script>

<style scoped>
.planner-container {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.empty-hint {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-secondary);
}

.hint-icon {
  font-size: 48px;
  color: var(--text-placeholder);
  margin-bottom: 12px;
}

/* 卡片 */
.card {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  padding: 20px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-desc {
  font-size: 12px;
  color: var(--text-placeholder);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 第一行布局 */
.analysis-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 0;
}

/* 爆款特征 */
.feature-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 10px 14px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-value.primary {
  color: var(--bili-blue);
}

.stat-unit {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 4px;
}

.publish-advice {
  margin-bottom: 14px;
}

.advice-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-regular);
  margin-bottom: 6px;
}

.no-data {
  color: var(--text-placeholder);
  font-size: 12px;
}

.hour-chart-wrap {
  margin-top: 8px;
}

.chart-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.hour-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 56px;
}

.hour-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.hour-bar {
  width: 100%;
  background: var(--bg-gray);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  transition: background 0.2s;
}

.hour-bar.is-best {
  background: var(--bili-blue);
}

.hour-label {
  font-size: 9px;
  color: var(--text-placeholder);
  margin-top: 2px;
}

/* 关键词云 */
.keyword-card {
  display: flex;
  flex-direction: column;
}

.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}

.kw-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.kw-tag:hover {
  opacity: 0.75;
}

.kw-hot {
  background: #FEF0F0;
  color: #F56C6C;
  font-weight: 500;
  font-size: 14px;
}

.kw-warm {
  background: #FFF3E0;
  color: var(--color-warning);
}

.kw-cool {
  background: var(--bg-gray);
  color: var(--text-regular);
  font-size: 12px;
}

.trend-up {
  color: #F56C6C;
}

.trend-down {
  color: #00B578;
}

/* 标题建议 */
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--bg-gray-light);
  cursor: pointer;
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: var(--bg-gray);
}

.suggestion-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bili-blue);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.suggestion-content {
  flex: 1;
  min-width: 0;
}

.suggestion-title {
  display: block;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hit-rate {
  font-size: 12px;
  color: var(--text-secondary);
}

.copy-icon {
  color: var(--text-placeholder);
  font-size: 16px;
  flex-shrink: 0;
}

/* 标题评分 */
.score-input-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.title-input {
  flex: 1;
}

.score-result {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.total-score-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.score-center {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.score-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.score-breakdown {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 200px;
}

.score-dim {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dim-label {
  width: 80px;
  font-size: 13px;
  color: var(--text-regular);
  flex-shrink: 0;
}

.dim-value {
  width: 50px;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: right;
  flex-shrink: 0;
}

.score-detail {
  flex: 1;
  min-width: 180px;
}

.detail-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-regular);
}

.detail-label {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.detail-tag {
  margin: 0;
}

.suggestions-box {
  background: var(--bg-gray-light);
  border-radius: 8px;
  padding: 12px 16px;
  min-width: 200px;
}

.suggestions-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
  margin-bottom: 8px;
}

.suggestion-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  color: var(--text-regular);
  margin-bottom: 6px;
}

.suggestion-tip .el-icon {
  color: var(--bili-blue);
  margin-top: 2px;
  flex-shrink: 0;
}

.empty-block {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
