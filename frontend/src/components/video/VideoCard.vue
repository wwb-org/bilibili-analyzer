<template>
  <div class="video-card" @click="handleClick">
    <div class="cover-wrapper">
      <el-image
        :src="video.cover_url"
        lazy
        fit="cover"
        class="video-cover"
      >
        <template #placeholder>
          <div class="cover-placeholder">
            <el-icon :size="24"><Picture /></el-icon>
          </div>
        </template>
        <template #error>
          <div class="cover-error">
            <el-icon :size="24"><PictureFilled /></el-icon>
          </div>
        </template>
      </el-image>
      <div class="duration" v-if="video.duration">{{ formatDuration(video.duration) }}</div>
    </div>
    <div class="video-info">
      <div class="video-title" :title="video.title">{{ video.title }}</div>
      <div class="video-meta">
        <span class="author">{{ video.author_name || '未知UP主' }}</span>
        <div class="stats">
          <span class="stat-item">
            <el-icon><VideoPlay /></el-icon>
            {{ formatNumber(video.play_count) }}
          </span>
          <span class="stat-item">
            <el-icon><Star /></el-icon>
            {{ formatNumber(video.like_count) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Picture, PictureFilled, VideoPlay, Star } from '@element-plus/icons-vue'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click', props.video.bvid)
}

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

const formatDuration = (seconds) => {
  if (!seconds) return ''
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.video-card {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s;
}

.video-card:hover {
  transform: translateY(-4px);
  border-color: var(--bili-blue);
}

.cover-wrapper {
  position: relative;
  width: 100%;
}

.video-cover {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: block;
  background: var(--bg-gray);
}

.cover-placeholder,
.cover-error {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-gray);
  color: var(--text-secondary);
}

.duration {
  position: absolute;
  right: 8px;
  bottom: 8px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
}

.video-info {
  padding: 12px;
}

.video-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
  min-height: 40px;
}

.video-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-secondary);
}

.author {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stats {
  display: flex;
  gap: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-item .el-icon {
  font-size: 14px;
}
</style>
