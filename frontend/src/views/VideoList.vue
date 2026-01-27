<template>
  <div class="video-list-container">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">视频数据</h2>
        <span class="page-desc">全网视频趋势监控</span>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="Refresh" circle @click="fetchVideos" :loading="loading" />
      </div>
    </div>

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
          <el-select v-model="filters.category" placeholder="全部分区" clearable class="filter-select">
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
      </el-form>
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
          @click="handleCardClick"
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import VideoCard from '@/components/video/VideoCard.vue'
import VideoDetailDialog from '@/components/video/VideoDetailDialog.vue'
import { getVideos } from '@/api/videos'

const loading = ref(false)
const videos = ref([])

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

const handleSearch = () => {
  pagination.page = 1
  fetchVideos()
}

const handleCardClick = (bvid) => {
  selectedBvid.value = bvid
  detailVisible.value = true
}

onMounted(() => {
  fetchVideos()
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
}

/* 分页样式 */
.pagination-wrapper {
  margin-top: 40px;
  display: flex;
  justify-content: center;
}
</style>