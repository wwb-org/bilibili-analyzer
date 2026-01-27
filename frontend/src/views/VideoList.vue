<template>
  <div class="video-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>视频数据</span>
          <el-button type="primary" size="small" @click="fetchVideos">刷新</el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索视频标题" clearable />
        </el-form-item>
        <el-form-item label="分区">
          <el-select v-model="filters.category" placeholder="全部分区" clearable>
            <el-option label="全部" value="" />
            <el-option label="游戏" value="游戏" />
            <el-option label="生活" value="生活" />
            <el-option label="科技" value="科技" />
            <el-option label="娱乐" value="娱乐" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>

      <!-- 视频列表 -->
      <el-table :data="videos" v-loading="loading" stripe>
        <el-table-column prop="bvid" label="BV号" width="130" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="author_name" label="UP主" width="120" />
        <el-table-column prop="category" label="分区" width="80" />
        <el-table-column prop="play_count" label="播放量" width="100">
          <template #default="{ row }">
            {{ formatNumber(row.play_count) }}
          </template>
        </el-table-column>
        <el-table-column prop="like_count" label="点赞" width="80">
          <template #default="{ row }">
            {{ formatNumber(row.like_count) }}
          </template>
        </el-table-column>
        <el-table-column prop="comment_count" label="评论" width="80" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchVideos"
        @current-change="fetchVideos"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api'

const loading = ref(false)
const videos = ref([])

const filters = reactive({
  keyword: '',
  category: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

const fetchVideos = async () => {
  loading.value = true
  try {
    const res = await request.get('/videos', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        keyword: filters.keyword || undefined,
        category: filters.category || undefined
      }
    })
    // 响应拦截器已经返回 response.data，所以直接取 items
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

const viewDetail = (row) => {
  ElMessage.info(`查看视频详情: ${row.bvid}`)
}

onMounted(() => {
  fetchVideos()
})
</script>

<style scoped>
.video-list-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-bottom: 20px;
}
</style>
