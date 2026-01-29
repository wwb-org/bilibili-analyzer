<template>
  <div class="danmaku-list" :class="{ 'is-simple': simple }">
    <div v-loading="loading" class="danmaku-content">
      <!-- 空状态 -->
      <el-empty v-if="!loading && danmakus.length === 0" description="暂无弹幕" :image-size="simple ? 60 : 100" />

      <!-- 弹幕列表 -->
      <div v-else class="danmaku-items">
        <div v-for="danmaku in danmakus" :key="danmaku.id" class="danmaku-item">
          <span class="danmaku-time">{{ formatTime(danmaku.send_time) }}</span>
          <span class="danmaku-text" :style="{ color: danmaku.color || 'inherit' }">
            {{ danmaku.content }}
          </span>
        </div>
      </div>

      <!-- 加载更多 -->
      <div v-if="hasMore && !loading" class="load-more" @click="loadMore">
        加载更多
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getVideoDanmakus } from '@/api/videos'

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
const danmakus = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50

const hasMore = ref(false)

const fetchDanmakus = async (append = false) => {
  if (!props.bvid) return

  loading.value = true
  try {
    const res = await getVideoDanmakus(props.bvid, {
      page: currentPage.value,
      page_size: pageSize
    })
    if (append) {
      danmakus.value = [...danmakus.value, ...(res.items || [])]
    } else {
      danmakus.value = res.items || []
    }
    total.value = res.total || 0
    hasMore.value = danmakus.value.length < total.value
  } catch (error) {
    console.error('获取弹幕失败:', error)
    if (!append) {
      danmakus.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
  }
}

const loadMore = () => {
  currentPage.value++
  fetchDanmakus(true)
}

const formatTime = (seconds) => {
  if (!seconds && seconds !== 0) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 监听 bvid 变化，重新加载弹幕
watch(() => props.bvid, (newVal) => {
  if (newVal) {
    currentPage.value = 1
    fetchDanmakus()
  }
}, { immediate: true })
</script>

<style scoped>
.danmaku-list {
  margin-top: 0;
}

.danmaku-content {
  min-height: 100px;
}

.danmaku-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.danmaku-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  font-size: 13px;
}

.danmaku-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-gray-light);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.danmaku-text {
  flex: 1;
  word-break: break-word;
  line-height: 1.4;
  color: var(--text-regular);
}

.load-more {
  text-align: center;
  padding: 12px;
  color: var(--bili-blue);
  cursor: pointer;
  font-size: 13px;
}

.load-more:hover {
  color: var(--bili-blue-hover);
}
</style>
