<template>
  <div class="comment-list" :class="{ 'is-simple': simple }">
    <div class="comment-header" v-if="!simple">
      <span class="comment-title">评论区</span>
      <span class="comment-count" v-if="total > 0">共 {{ total }} 条</span>
    </div>

    <div v-loading="loading" class="comment-content">
      <!-- 空状态 -->
      <el-empty v-if="!loading && comments.length === 0" description="暂无评论" :image-size="simple ? 60 : 100" />

      <!-- 评论列表 -->
      <div v-else class="comment-items">
        <div v-for="comment in comments" :key="comment.id" class="comment-item">
          <div class="comment-user">
            <span class="user-name">{{ comment.user_name || '匿名用户' }}</span>
            <el-tag
              v-if="comment.sentiment_label"
              :type="getSentimentType(comment.sentiment_label)"
              size="small"
              class="sentiment-tag"
              effect="plain"
            >
              {{ getSentimentText(comment.sentiment_label) }}
            </el-tag>
          </div>
          <div class="comment-text">{{ comment.content }}</div>
          <div class="comment-footer">
            <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
            <span class="comment-like" v-if="comment.like_count > 0">
              <el-icon><Star /></el-icon>
              {{ comment.like_count }}
            </span>
          </div>
        </div>
      </div>

      <!-- 分页 (简单模式下不显示) -->
      <el-pagination
        v-if="!simple && total > pageSize"
        v-model:current-page="currentPage"
        :total="total"
        :page-size="pageSize"
        layout="prev, pager, next"
        @current-change="handlePageChange"
        class="comment-pagination"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Star } from '@element-plus/icons-vue'
import { getVideoComments } from '@/api/videos'

const props = defineProps({
  bvid: {
    type: String,
    required: true
  },
  simple: {
    type: Boolean,
    default: false
  }
})

const loading = ref(false)
const comments = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = props.simple ? 20 : 10 // Load more initially in simple mode as we scroll

const fetchComments = async () => {
  if (!props.bvid) return

  loading.value = true
  try {
    const res = await getVideoComments(props.bvid, {
      page: currentPage.value,
      page_size: pageSize
    })
    comments.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    console.error('获取评论失败:', error)
    comments.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handlePageChange = () => {
  fetchComments()
}

const getSentimentType = (label) => {
  const types = {
    positive: 'success',
    neutral: 'info',
    negative: 'danger'
  }
  return types[label] || 'info'
}

const getSentimentText = (label) => {
  const texts = {
    positive: '正面',
    neutral: '中性',
    negative: '负面'
  }
  return texts[label] || '未知'
}

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleDateString('zh-CN')
}

// 监听 bvid 变化，重新加载评论
watch(() => props.bvid, (newVal) => {
  if (newVal) {
    currentPage.value = 1
    fetchComments()
  }
}, { immediate: true })
</script>

<style scoped>
.comment-list {
  margin-top: 20px;
}

.comment-list.is-simple {
  margin-top: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.comment-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.comment-count {
  font-size: 13px;
  color: var(--text-secondary);
}

.comment-content {
  min-height: 100px;
}

.comment-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-item {
  padding: 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
}

.is-simple .comment-item {
  padding: 10px;
  background: var(--bg-white);
  border: 1px solid var(--border-light);
}

.comment-user {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-regular);
}

.sentiment-tag {
  height: 20px;
  padding: 0 4px;
  font-size: 10px;
}

.comment-text {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.5;
  word-break: break-word;
}

.is-simple .comment-text {
  font-size: 13px;
}

.comment-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.comment-like {
  display: flex;
  align-items: center;
  gap: 4px;
}

.comment-pagination {
  margin-top: 16px;
  justify-content: center;
}
</style>