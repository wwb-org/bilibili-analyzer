<template>
  <div class="video-card" :class="{ 'is-selected': selected, 'compare-mode': compareMode }" @click="handleClick">
    <!-- 对比模式勾选标识 -->
    <div v-if="compareMode" class="select-indicator" :class="{ 'is-checked': isChecked }">
      <div class="check-icon">
        <el-icon v-if="isChecked"><Check /></el-icon>
      </div>
    </div>

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
      <!-- 对比模式遮罩 -->
      <div v-if="compareMode && isChecked" class="select-overlay">
        <span class="select-badge">已选择</span>
      </div>
    </div>
    <div class="video-info">
      <div class="video-title" :title="video.title">{{ video.title }}</div>
      <div class="video-meta">
        <span class="author">{{ video.author_name || '未知UP主' }}</span>
        <span class="publish-time" v-if="video.publish_time">
          <el-icon><Clock /></el-icon>
          {{ formatPublishTime(video.publish_time) }}
        </span>
      </div>
      <div class="video-stats">
        <span class="stat-item">
          <el-icon><VideoPlay /></el-icon>
          {{ formatNumber(video.play_count) }}
        </span>
        <span class="stat-item">
          <el-icon><Star /></el-icon>
          {{ formatNumber(video.like_count) }}
        </span>
      </div>
      <!-- 分析标签行 -->
      <div class="analysis-tags">
        <span class="tag interaction-tag">
          互动 {{ interactionRate }}%
        </span>
        <span class="tag sentiment-tag" :class="`sentiment-${sentimentLabel}`">
          {{ sentimentEmoji }} {{ sentimentText }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Picture, PictureFilled, VideoPlay, Star, Check, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  video: {
    type: Object,
    required: true
  },
  compareMode: {
    type: Boolean,
    default: false
  },
  selected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'select'])

const isChecked = ref(props.selected)

// 监听外部 selected 变化
watch(() => props.selected, (val) => {
  isChecked.value = val
})

const handleClick = () => {
  if (props.compareMode) {
    // 对比模式下，点击卡片切换选中状态
    isChecked.value = !isChecked.value
    emit('select', props.video.bvid, isChecked.value)
  } else {
    emit('click', props.video.bvid)
  }
}

// 计算互动率
const interactionRate = computed(() => {
  const { play_count, like_count, coin_count, favorite_count, share_count } = props.video
  if (!play_count || play_count === 0) return '0.0'
  const rate = ((like_count || 0) + (coin_count || 0) + (favorite_count || 0) + (share_count || 0)) / play_count * 100
  return rate.toFixed(1)
})

// 情感标签（基于视频的评论情感，这里用互动率近似判断热度/好评度）
// 实际应该从后端获取，这里先用互动率作为参考
const sentimentLabel = computed(() => {
  const rate = parseFloat(interactionRate.value)
  if (rate >= 8) return 'positive'
  if (rate <= 3) return 'negative'
  return 'neutral'
})

const sentimentEmoji = computed(() => {
  const map = {
    positive: '😊',
    neutral: '😐',
    negative: '😔'
  }
  return map[sentimentLabel.value]
})

const sentimentText = computed(() => {
  const map = {
    positive: '热门',
    neutral: '一般',
    negative: '冷门'
  }
  return map[sentimentLabel.value]
})

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

// 格式化发布时间
const formatPublishTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  if (days < 30) return `${Math.floor(days / 7)}周前`
  if (days < 365) return `${Math.floor(days / 30)}个月前`
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.video-card {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
  position: relative;
}

.video-card:hover {
  transform: translateY(-4px);
  border-color: var(--bili-blue);
}

.video-card.is-selected {
  border-color: var(--bili-blue);
  box-shadow: 0 0 0 2px rgba(0, 161, 214, 0.2);
}

/* 对比模式样式 */
.video-card.compare-mode {
  cursor: pointer;
}

.video-card.compare-mode:hover {
  transform: translateY(-2px);
}

/* 选中标识 */
.select-indicator {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
}

.check-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid var(--border-regular);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.select-indicator.is-checked .check-icon {
  background: var(--bili-blue);
  border-color: var(--bili-blue);
  color: #fff;
}

.check-icon .el-icon {
  font-size: 14px;
  font-weight: bold;
}

/* 选中遮罩 */
.select-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 161, 214, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.select-badge {
  background: var(--bili-blue);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 12px;
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
  margin-bottom: 6px;
}

.author {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.publish-time {
  display: flex;
  align-items: center;
  gap: 2px;
}

.publish-time .el-icon {
  font-size: 12px;
}

.video-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-item .el-icon {
  font-size: 14px;
}

/* 分析标签 */
.analysis-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.interaction-tag {
  background: rgba(0, 161, 214, 0.1);
  color: var(--bili-blue);
}

.sentiment-tag {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sentiment-positive {
  background: rgba(0, 181, 120, 0.1);
  color: var(--color-success);
}

.sentiment-neutral {
  background: rgba(148, 153, 160, 0.1);
  color: var(--text-secondary);
}

.sentiment-negative {
  background: rgba(245, 108, 108, 0.1);
  color: var(--color-error);
}
</style>
