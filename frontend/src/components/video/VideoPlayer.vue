<template>
  <div class="player-container">
    <iframe
      :src="playerUrl"
      scrolling="no"
      border="0"
      frameborder="no"
      framespacing="0"
      allowfullscreen="true"
      class="player-iframe"
    ></iframe>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bvid: {
    type: String,
    required: true
  },
  autoplay: {
    type: Boolean,
    default: false
  },
  danmaku: {
    type: Boolean,
    default: true
  },
  startTime: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  }
})

const playerUrl = computed(() => {
  const params = new URLSearchParams({
    bvid: props.bvid,
    autoplay: props.autoplay ? '1' : '0',
    danmaku: props.danmaku ? '1' : '0'
  })

  if (props.startTime > 0) {
    params.append('t', props.startTime.toString())
  }
  if (props.page > 1) {
    params.append('p', props.page.toString())
  }

  return `//player.bilibili.com/player.html?${params.toString()}`
})
</script>

<style scoped>
.player-container {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.player-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
