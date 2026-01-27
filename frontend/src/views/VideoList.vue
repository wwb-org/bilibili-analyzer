<template>
  <div class="video-list-container">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">视频数据</h2>
        <span class="page-desc">全网视频趋势监控</span>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="Refresh" circle @click="handleRefresh" :loading="loading" />
      </div>
    </div>

    <!-- 统计面板 -->
    <VideoStatsPanel :stats="statsData" :loading="statsLoading" />

    <!-- 筛选区域 -->
    <div class="filter-section">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item>
          <el-input
            v-model="filters.keyword"
            placeholder="搜索视频标题"
            clearable
            prefix-icon="Search"
            @keyup.enter="handleSearch"
            class="search-input"
          />
        </el-form-item>

        <el-form-item>
          <el-select v-model="filters.category" placeholder="全部分区" clearable class="filter-select" @change="handleFilterChange">
            <el-option label="全部分区" value="" />
            <el-option label="游戏" value="游戏" />
            <el-option label="生活" value="生活" />
            <el-option label="科技" value="科技" />
            <el-option label="娱乐" value="娱乐" />
            <el-option label="动画" value="动画" />
            <el-option label="音乐" value="音乐" />
            <el-option label="影视" value="影视" />
            <el-option label="知识" value="知识" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-radio-group v-model="filters.order_by" @change="fetchVideos" class="sort-radio">
            <el-radio-button label="play_count">播放最高</el-radio-button>
            <el-radio-button label="like_count">最受喜欢</el-radio-button>
            <el-radio-button label="publish_time">最新发布</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 对比模式开关 -->
        <el-form-item class="compare-switch-item">
          <div class="compare-switch-wrapper">
            <span class="switch-label">对比模式</span>
            <el-switch v-model="compareMode" @change="handleCompareModeChange" />
          </div>
        </el-form-item>
      </el-form>

      <!-- 对比操作栏 -->
      <div v-if="compareMode" class="compare-toolbar">
        <span class="selected-count">已选择 {{ selectedBvids.length }} / 5 个视频</span>
        <el-button
          type="primary"
          :disabled="selectedBvids.length < 2"
          @click="showCompareDialog"
        >
          开始对比
        </el-button>
        <el-button @click="clearSelection">清空选择</el-button>
      </div>
    </div>

    <!-- 视频网格 -->
    <div class="video-content" v-loading="loading">
      <!-- 空状态 -->
      <el-empty
        v-if="!loading && videos.length === 0"
        description="暂无符合条件的视频"
        :image-size="200"
      />

      <!-- 视频卡片网格 -->
      <div v-else class="video-grid">
        <VideoCard
          v-for="video in videos"
          :key="video.bvid"
          :video="video"
          :compare-mode="compareMode"
          :selected="selectedBvids.includes(video.bvid)"
          @click="handleCardClick"
          @select="handleVideoSelect"
        />
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[12, 20, 24, 40]"
        layout="total, prev, pager, next, jumper"
        background
        @size-change="fetchVideos"
        @current-change="fetchVideos"
      />
    </div>

    <!-- 视频详情弹窗 -->
    <VideoDetailDialog
      v-model="detailVisible"
      :bvid="selectedBvid"
    />

    <!-- 视频对比弹窗 -->
    <VideoCompareDialog
      v-model="compareDialogVisible"
      :bvids="selectedBvids"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import VideoCard from '@/components/video/VideoCard.vue'
import VideoDetailDialog from '@/components/video/VideoDetailDialog.vue'
import VideoStatsPanel from '@/components/video/VideoStatsPanel.vue'
import VideoCompareDialog from '@/components/video/VideoCompareDialog.vue'
import { getVideos, getVideosStats } from '@/api/videos'

const loading = ref(false)
const videos = ref([])

// 统计数据
const statsLoading = ref(false)
const statsData = ref({
  total_videos: 0,
  total_play_count: 0,
  avg_play_count: 0,
  avg_interaction_rate: 0,
  sentiment_distribution: { positive: 0, neutral: 0, negative: 0 },
  category_distribution: []
})

const filters = reactive({
  keyword: '',
  category: '',
  order_by: 'play_count'
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 详情弹窗状态
const detailVisible = ref(false)
const selectedBvid = ref('')

// 对比模式状态
const compareMode = ref(false)
const selectedBvids = ref([])
const compareDialogVisible = ref(false)

// 获取统计数据
const fetchStats = async () => {
  statsLoading.value = true
  try {
    const res = await getVideosStats({
      keyword: filters.keyword || undefined,
      category: filters.category || undefined
    })
    statsData.value = res
  } catch (error) {
    console.error('获取统计数据失败:', error)
  } finally {
    statsLoading.value = false
  }
}

const fetchVideos = async () => {
  loading.value = true
  try {
    const res = await getVideos({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: filters.keyword || undefined,
      category: filters.category || undefined,
      order_by: filters.order_by
    })
    videos.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('获取视频列表失败')
  } finally {
    loading.value = false
  }
}

// 刷新所有数据
const handleRefresh = () => {
  fetchVideos()
  fetchStats()
}

// 筛选条件变化时同时更新统计
const handleFilterChange = () => {
  pagination.page = 1
  fetchVideos()
  fetchStats()
}

const handleSearch = () => {
  pagination.page = 1
  fetchVideos()
  fetchStats()
}

const handleCardClick = (bvid) => {
  selectedBvid.value = bvid
  detailVisible.value = true
}

// 对比模式相关方法
const handleCompareModeChange = (val) => {
  if (!val) {
    selectedBvids.value = []
  }
}

const handleVideoSelect = (bvid, checked) => {
  if (checked) {
    if (selectedBvids.value.length >= 5) {
      ElMessage.warning('最多只能选择5个视频进行对比')
      return
    }
    if (!selectedBvids.value.includes(bvid)) {
      selectedBvids.value.push(bvid)
    }
  } else {
    const index = selectedBvids.value.indexOf(bvid)
    if (index > -1) {
      selectedBvids.value.splice(index, 1)
    }
  }
}

const showCompareDialog = () => {
  if (selectedBvids.value.length < 2) {
    ElMessage.warning('请至少选择2个视频进行对比')
    return
  }
  compareDialogVisible.value = true
}

const clearSelection = () => {
  selectedBvids.value = []
}

onMounted(() => {
  fetchVideos()
  fetchStats()
})
</script>

<style scoped>
.video-list-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
}

/* 顶部样式 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 筛选区样式 */
.filter-section {
  margin-bottom: 24px;
  background: var(--bg-white);
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 0;
}

.filter-form .el-form-item {
  margin: 0;
}

.search-input {
  width: 300px;
}

.filter-select {
  width: 160px;
}

/* 对比模式开关 */
.compare-switch-item {
  margin-left: auto !important;
}

.compare-switch-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: var(--bg-gray-light);
  border-radius: 6px;
}

.switch-label {
  font-size: 13px;
  color: var(--text-regular);
}

/* 对比操作栏 */
.compare-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.selected-count {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 视频网格样式 */
.video-content {
  min-height: 400px;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

/* 响应式调整 */
@media (min-width: 1920px) {
  .video-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}

@media (min-width: 1400px) and (max-width: 1919px) {
  .video-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (min-width: 1100px) and (max-width: 1399px) {
  .video-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1099px) {
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .video-grid {
    grid-template-columns: 1fr;
  }

  .filter-form {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .compare-switch-item {
    margin-left: 0 !important;
  }
}

/* 分页样式 */
.pagination-wrapper {
  margin-top: 40px;
  display: flex;
  justify-content: center;
}
</style>