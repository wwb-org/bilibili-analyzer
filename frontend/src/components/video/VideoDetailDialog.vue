<template>
  <el-drawer
    v-model="visible"
    :title="null"
    :with-header="false"
    size="520px"
    direction="rtl"
    :close-on-click-modal="true"
    class="video-detail-drawer"
    destroy-on-close
    @close="handleClose"
  >
    <div v-loading="loading" class="detail-container">
      <template v-if="videoDetail">
        <!-- 固定区域：头部 + 播放器 + 数据 -->
        <div class="fixed-section">
          <!-- 头部信息 -->
          <div class="detail-header">
            <h2 class="video-title" :title="videoDetail.title">{{ videoDetail.title }}</h2>
            <div class="header-meta">
              <span class="meta-tag channel">{{ videoDetail.category || '全部分区' }}</span>
              <span class="meta-time">{{ formatDate(videoDetail.publish_time) }}</span>
            </div>
          </div>

          <!-- 播放器 -->
          <div class="player-wrapper">
            <VideoPlayer :bvid="bvid" />
          </div>

          <!-- UP主信息 + B站链接 -->
          <div class="uploader-row">
            <div class="uploader-info">
              <el-avatar :size="32" :src="videoDetail.author_face" class="uploader-avatar">
                {{ videoDetail.author_name?.charAt(0) }}
              </el-avatar>
              <span class="uploader-name">{{ videoDetail.author_name || '未知UP主' }}</span>
            </div>
            <a :href="'https://www.bilibili.com/video/' + videoDetail.bvid" target="_blank" class="bili-link">
              前往B站 <el-icon><TopRight /></el-icon>
            </a>
          </div>

          <!-- 数据统计 -->
          <div class="stats-grid">
            <div class="stat-item main">
              <div class="stat-icon"><el-icon><VideoPlay /></el-icon></div>
              <div class="stat-content">
                <div class="stat-num">{{ formatNumber(videoDetail.play_count) }}</div>
                <div class="stat-label">播放</div>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.like_count) }}</div>
              <div class="stat-label">点赞</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.coin_count) }}</div>
              <div class="stat-label">投币</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.favorite_count || 0) }}</div>
              <div class="stat-label">收藏</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.share_count) }}</div>
              <div class="stat-label">分享</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">{{ formatNumber(videoDetail.danmaku_count) }}</div>
              <div class="stat-label">弹幕</div>
            </div>
          </div>

          <!-- 视频简介 -->
          <div class="desc-panel">
            <h3 class="panel-title">简介</h3>
            <div class="desc-content" :class="{ 'expanded': isDescExpanded }">
              {{ videoDetail.description || '暂无简介' }}
            </div>
            <div v-if="videoDetail.description && videoDetail.description.length > 60"
                 class="desc-toggle"
                 @click="isDescExpanded = !isDescExpanded">
              {{ isDescExpanded ? '收起' : '展开' }}
            </div>
          </div>
        </div>

        <!-- 下半部分：评论区（可滚动） -->
        <div class="comments-section">
          <div class="comments-header">
            <h3 class="panel-title">评论区</h3>
          </div>
          <div class="comments-scroll">
            <CommentList :bvid="bvid" :simple="true" />
          </div>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { VideoPlay, TopRight } from '@element-plus/icons-vue'
import VideoPlayer from './VideoPlayer.vue'
import CommentList from './CommentList.vue'
import { getVideoDetail } from '@/api/videos'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  bvid: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const videoDetail = ref(null)
const isDescExpanded = ref(false)

const fetchVideoDetail = async () => {
  if (!props.bvid) return

  loading.value = true
  try {
    const res = await getVideoDetail(props.bvid)
    videoDetail.value = res
  } catch (error) {
    console.error('获取视频详情失败:', error)
    videoDetail.value = null
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  videoDetail.value = null
  isDescExpanded.value = false
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

const formatDate = (date) => {
  if (!date) return '未知'
  return new Date(date).toLocaleDateString('zh-CN') + ' ' + new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

watch(() => props.bvid, (newVal) => {
  if (newVal && props.modelValue) {
    fetchVideoDetail()
  }
})

watch(() => props.modelValue, (newVal) => {
  if (newVal && props.bvid) {
    fetchVideoDetail()
  }
})
</script>

<style scoped>
/* Drawer 全局样式 */
:global(.video-detail-drawer) {
  --el-drawer-padding-primary: 0;
}

:global(.video-detail-drawer .el-drawer__body) {
  padding: 0;
  overflow: hidden;
}

/* 容器 */
.detail-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-white);
}

/* 固定区域 */
.fixed-section {
  flex-shrink: 0;
  padding: 20px;
  border-bottom: 1px solid var(--border-light);
}

/* 头部 */
.detail-header {
  margin-bottom: 12px;
}

.video-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-tag {
  color: var(--bili-pink);
  background: rgba(251, 114, 153, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 播放器 */
.player-wrapper {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

/* UP主行 */
.uploader-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  margin-bottom: 12px;
}

.uploader-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uploader-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.bili-link {
  font-size: 12px;
  color: var(--bili-blue);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 2px;
  transition: color 0.2s;
}

.bili-link:hover {
  color: var(--bili-blue-hover);
}

/* 数据统计网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
  padding: 10px 4px;
  background: var(--bg-gray-light);
  border-radius: 6px;
}

.stat-item.main {
  grid-column: span 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  background: var(--bili-blue-light);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bili-blue);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.stat-item.main .stat-num {
  font-size: 20px;
  color: var(--bili-blue);
}

.stat-num {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* 简介 */
.desc-panel {
  margin-bottom: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 6px 0;
  color: var(--text-primary);
}

.desc-content {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-regular);
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.desc-content.expanded {
  -webkit-line-clamp: unset;
}

.desc-toggle {
  font-size: 12px;
  color: var(--bili-blue);
  cursor: pointer;
  margin-top: 4px;
}

/* 评论区 */
.comments-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 20px 20px;
}

.comments-header {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.comments-header .panel-title {
  margin: 0;
}

.comments-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

/* 滚动条样式 */
.comments-scroll::-webkit-scrollbar {
  width: 4px;
}

.comments-scroll::-webkit-scrollbar-track {
  background: var(--bg-gray-light);
  border-radius: 2px;
}

.comments-scroll::-webkit-scrollbar-thumb {
  background: var(--border-regular);
  border-radius: 2px;
}

.comments-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
