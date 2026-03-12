<template>
  <div class="home-container">

    <!-- 顶部标题 + 时钟 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">数据概览</h2>
        <span class="page-desc">B站视频内容趋势分析系统</span>
      </div>
      <div class="header-right">
        <span v-if="homeStore.isFresh" class="cache-hint">
          数据更新于 {{ ageText }} ·
          <span class="cache-refresh" @click="handleRefresh">重新加载</span>
        </span>
        <div class="live-clock">
          <span class="clock-time">{{ clockTime }}</span>
          <span class="clock-date">{{ clockDate }}</span>
        </div>
      </div>
    </div>

    <!-- 核心指标条 -->
    <div class="metrics-strip">
      <div v-for="card in metricCards" :key="card.key" class="metric-item">
        <div class="metric-accent" :style="{ background: card.color }"></div>
        <div class="metric-inner">
          <div class="metric-val">{{ card.display }}</div>
          <div class="metric-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- S1: 内容竞争地图 -->
    <div class="card">
      <div class="card-header-line">
        <div class="section-num">01</div>
        <h3 class="card-title">内容竞争地图</h3>
        <span class="card-desc">X=播放量 &nbsp;Y=互动率 &nbsp;大小=评论数 &nbsp;颜色=互动热度</span>
        <div class="quadrant-legend">
          <span class="ql-item ql-hot">爆款</span>
          <span class="ql-item ql-potential">潜力视频</span>
          <span class="ql-item ql-clickbait">标题党</span>
          <span class="ql-item ql-normal">普通</span>
        </div>
      </div>
      <div ref="bubbleRef" class="chart-xl"></div>
    </div>

    <!-- S2 趋势视频监控 -->
    <div class="row-single">
      <!-- S2 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">02</div>
          <h3 class="card-title">趋势视频监控</h3>
          <span class="card-desc">热度排行榜 · 来自数仓 dws_video_trend</span>
          <el-tag v-if="trendIsFallback" size="small" type="warning">热门播放榜（ETL执行后显示趋势）</el-tag>
        </div>
        <div class="trend-list">
          <div v-if="!trendVideos.length" class="empty-tip">暂无视频数据</div>
          <a
            v-for="(v, i) in trendVideos"
            :key="v.bvid"
            :href="`https://www.bilibili.com/video/${v.bvid}`"
            target="_blank"
            class="trend-item"
          >
            <span class="trend-rank" :class="rankClass(i)">{{ i + 1 }}</span>
            <div class="trend-info">
              <div class="trend-title">{{ v.title || v.bvid }}</div>
              <div class="trend-meta">
                <el-tag v-if="v.category" size="small" type="info">{{ v.category }}</el-tag>
                <span v-if="v.heat_score > 0" class="trend-heat">热度 {{ v.heat_score.toFixed(1) }}</span>
                <span v-else-if="v.play_count" class="trend-heat">▶ {{ formatLarge(v.play_count) }}</span>
              </div>
            </div>
            <div class="trend-growth" :class="v.play_trend > 0 ? 'pos' : v.play_trend < 0 ? 'neg' : 'neutral'">
              <template v-if="v.heat_score > 0">
                {{ v.play_trend >= 0 ? '↑' : '↓' }}{{ Math.abs(v.play_trend).toFixed(0) }}%
              </template>
              <template v-else>-</template>
            </div>
          </a>
        </div>
      </div>
    </div>

    <!-- S3 内容生命周期 + S4 分类内容表现 -->
    <div class="row-dual">
      <!-- S3 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">03</div>
          <h3 class="card-title">内容生命周期分析</h3>
          <span class="card-desc">发布后N天的平均播放量走势</span>
        </div>
        <div ref="lifecycleRef" class="chart-area"></div>
      </div>

      <!-- S4 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">04</div>
          <h3 class="card-title">分类内容表现</h3>
          <span class="card-desc">各分区播放量 · 互动率 · 来自 dws_category_daily</span>
        </div>
        <div ref="categoryRef" class="chart-area"></div>
      </div>
    </div>

    <!-- S5 评论情绪分析 + S6 热点关键词 -->
    <div class="row-dual">
      <!-- S5 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">05</div>
          <h3 class="card-title">评论情绪分析</h3>
          <span class="card-desc">情绪分布 · 趋势 · 来自 dws_sentiment_daily</span>
        </div>
        <div class="s5-inner">
          <div ref="sentPieRef" class="s5-pie"></div>
          <div ref="sentTrendRef" class="s5-trend"></div>
        </div>
      </div>

      <!-- S6 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">06</div>
          <h3 class="card-title">热点关键词趋势</h3>
          <span class="card-desc">高频词云 · 来自 keywords 表</span>
        </div>
        <div ref="wordcloudRef" class="chart-area"></div>
      </div>
    </div>

    <!-- S7 发布时间热力图 + S8 内容机会发现 -->
    <div class="row-dual">
      <!-- S7 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">07</div>
          <h3 class="card-title">发布时间效率分析</h3>
          <span class="card-desc">何时发布更容易上热门（7×24 热力矩阵）</span>
        </div>
        <div ref="heatmapRef" class="chart-area"></div>
      </div>

      <!-- S8 -->
      <div class="card">
        <div class="card-header-line">
          <div class="section-num">08</div>
          <h3 class="card-title">内容机会发现</h3>
          <span class="card-desc">高互动低播放 · 被平台低估的潜力视频</span>
        </div>
        <div class="opp-list">
          <div v-if="!opportunities.length" class="empty-tip">暂无机会视频数据</div>
          <a
            v-for="v in opportunities"
            :key="v.bvid"
            :href="`https://www.bilibili.com/video/${v.bvid}`"
            target="_blank"
            class="opp-item"
          >
            <div class="opp-info">
              <div class="opp-title">{{ v.title }}</div>
              <div class="opp-meta">
                <el-tag size="small" type="info">{{ v.category }}</el-tag>
                <span class="opp-play">▶ {{ formatLarge(v.play_count) }}</span>
              </div>
            </div>
            <div class="opp-rate">
              <div class="opp-rate-val">{{ v.interaction_rate?.toFixed(1) }}%</div>
              <div class="opp-rate-label">互动率</div>
            </div>
          </a>
        </div>
      </div>
    </div>

    <!-- S9 UP主影响力排行榜 -->
    <div class="card">
      <div class="card-header-line">
        <div class="section-num">09</div>
        <h3 class="card-title">UP主影响力排行榜</h3>
        <span class="card-desc">综合评分 = 播放量×0.5 + 点赞数×0.3 + 评论数×0.2</span>
      </div>
      <div v-if="!authors.length" class="empty-tip" style="padding:20px 0">暂无数据</div>
      <div v-else class="author-grid">
        <div
          v-for="(a, i) in authors"
          :key="a.author_id"
          class="author-card"
          :class="{ 'author-top3': i < 3 }"
        >
          <div class="author-rank" :class="rankClass(i)">{{ i + 1 }}</div>
          <div class="author-name">{{ a.author_name }}</div>
          <div class="author-stats">
            <div class="author-stat">
              <div class="author-stat-val">{{ formatLarge(a.total_play) }}</div>
              <div class="author-stat-label">总播放</div>
            </div>
            <div class="author-stat">
              <div class="author-stat-val">{{ a.video_count }}</div>
              <div class="author-stat-label">视频数</div>
            </div>
            <div class="author-stat">
              <div class="author-stat-val" style="color:var(--bili-blue)">{{ formatLarge(a.influence_score) }}</div>
              <div class="author-stat-label">影响力</div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import {
  getOverview, getVideoScatter, getKeywords, getPublishHeatmap,
  getTopVideos,
  getDwVideoTrends, getDwCategories,
  getDwSentiment, getDwSentimentTrends,
  getLifecycle, getOpportunities, getAuthorRanking,
} from '@/api/statistics'
import { useHomeStore } from '@/store/home'

const homeStore = useHomeStore()

// ====== 时钟 ======
const clockTime = ref('')
const clockDate = ref('')
let clockTimer = null
const tickClock = () => {
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  clockTime.value = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  clockDate.value = `${now.getFullYear()}.${pad(now.getMonth()+1)}.${pad(now.getDate())}`
}

// ====== 缓存状态 ======
// 依赖 clockTime 每秒自动刷新显示
const ageText = computed(() => {
  clockTime.value // 建立对时钟的响应式依赖，每秒更新
  if (!homeStore.cachedAt) return ''
  const mins = Math.floor((Date.now() - homeStore.cachedAt) / 60000)
  return mins < 1 ? '刚刚' : `${mins} 分钟前`
})
const handleRefresh = () => {
  homeStore.cachedAt = null
  loadAll()
}

// ====== 数字动画 ======
const nums = ref({ videos: 0, play: 0, comments: 0, likes: 0, avg: 0 })
const animTo = (key, target, ms = 1200) => {
  const t0 = Date.now()
  const tick = () => {
    const p = Math.min((Date.now()-t0)/ms, 1)
    nums.value[key] = Math.round(target * (1 - Math.pow(1-p, 3)))
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}
const formatLarge = n => {
  if (!n) return '0'
  if (n >= 1e8) return (n/1e8).toFixed(1)+'亿'
  if (n >= 1e4) return (n/1e4).toFixed(1)+'万'
  return n.toLocaleString()
}
const metricCards = computed(() => [
  { key:'videos',   label:'视频总数', color:'#00A1D6', display: nums.value.videos.toLocaleString()+'个' },
  { key:'play',     label:'总播放量', color:'#00B578', display: formatLarge(nums.value.play) },
  { key:'comments', label:'总评论数', color:'#FF9736', display: formatLarge(nums.value.comments) },
  { key:'likes',    label:'总点赞数', color:'#FB7299', display: formatLarge(nums.value.likes) },
  { key:'avg',      label:'均播放量', color:'#7B68EE', display: formatLarge(nums.value.avg) },
])
const rankClass = i => ['rank-gold','rank-silver','rank-bronze'][i] || ''

// ====== 分区颜色 ======
const CATEGORY_COLORS = {
  '游戏':'#00A1D6','生活':'#00B578','鬼畜':'#FB7299','娱乐':'#FF9736',
  '音乐':'#7B68EE','动画':'#F56C6C','科技':'#36CFC9','影视':'#FFC53D',
  '知识':'#52C41A','美食':'#FF85C2','舞蹈':'#B37FEB','时尚':'#FF7875',
  '汽车':'#69B1FF','运动':'#95DE64','其他':'#9499A0',
}
const WC_COLORS = ['#00A1D6','#00B578','#FB7299','#FF9736','#7B68EE','#36CFC9','#FFC53D','#F56C6C']

// ====== 数据 ======
const trendVideos = ref([])
const trendIsFallback = ref(false)
const opportunities = ref([])
const authors = ref([])

// ====== Chart refs & instances ======
const bubbleRef    = ref(null)
const lifecycleRef = ref(null)
const categoryRef  = ref(null)
const sentPieRef   = ref(null)
const sentTrendRef = ref(null)
const wordcloudRef = ref(null)
const heatmapRef   = ref(null)

let bubbleChart    = null
let lifecycleChart = null
let categoryChart  = null
let sentPieChart   = null
let sentTrendChart = null
let wordcloudChart = null
let heatmapChart   = null

// ===========================
// S1: 内容竞争地图（气泡图）
// ===========================
const initBubble = (videos) => {
  if (!bubbleRef.value || !videos.length) return
  if (!bubbleChart) bubbleChart = echarts.init(bubbleRef.value)

  // 计算中位数用于四象限划分
  const sortedPlay = [...videos].sort((a, b) => a.play_count - b.play_count)
  const sortedIR   = [...videos].sort((a, b) => a.interaction_rate - b.interaction_rate)
  const midX = sortedPlay[Math.floor(sortedPlay.length / 2)]?.play_count || 0
  const midY = sortedIR[Math.floor(sortedIR.length / 2)]?.interaction_rate || 0
  const maxIR = sortedIR[sortedIR.length - 1]?.interaction_rate || 1

  // 合并为单一 series，使用 visualMap 蓝粉渐变
  const allData = videos.map(v => [
    v.play_count,
    v.interaction_rate,
    v.comment_count || 1,
    v.title,
    v.category || '其他',
  ])

  bubbleChart.setOption({
    tooltip: {
      formatter: p => {
        const [x, y, c, t, cat] = p.data
        return `<b>${t}</b><br/>分区 ${cat}<br/>播放量 ${formatLarge(x)}<br/>互动率 ${y.toFixed(2)}%<br/>评论数 ${formatLarge(c)}`
      },
    },
    visualMap: {
      show: false,
      dimension: 1,
      min: 0,
      max: maxIR,
      inRange: {
        color: ['#00A1D6', '#8BC7E8', '#D4A5C0', '#FB7299'],
      },
    },
    grid: { top: 32, right: 16, bottom: 32, left: 60 },
    xAxis: {
      name: '播放量', nameTextStyle: { color:'#9499A0', fontSize:11 },
      axisLabel: { color:'#9499A0', fontSize:10, formatter: v => formatLarge(v) },
      splitLine: { lineStyle: { color:'#F4F4F4' } },
    },
    yAxis: {
      name: '互动率(%)', nameTextStyle: { color:'#9499A0', fontSize:11 },
      axisLabel: { color:'#9499A0', fontSize:10 },
      splitLine: { lineStyle: { color:'#F4F4F4' } },
    },
    graphic: [
      { type:'text', left:'74%', top:8,     style:{ text:'🔥 爆款区',   fill:'#FB7299', fontSize:11, fontWeight:'bold' } },
      { type:'text', left:'4%',  top:8,     style:{ text:'🌱 潜力视频', fill:'#00B578', fontSize:11, fontWeight:'bold' } },
      { type:'text', left:'74%', bottom:36, style:{ text:'📢 标题党',   fill:'#FF9736', fontSize:11, fontWeight:'bold' } },
      { type:'text', left:'4%',  bottom:36, style:{ text:'😐 普通',     fill:'#9499A0', fontSize:11 } },
    ],
    series: [{
      type: 'scatter',
      data: allData,
      symbolSize: d => Math.max(8, Math.min(40, Math.sqrt(d[2] || 50) * 0.7)),
      itemStyle: {
        opacity: 0.78,
        borderColor: '#fff',
        borderWidth: 1,
      },
      emphasis: {
        itemStyle: { opacity: 1, borderWidth: 2 },
      },
      markLine: {
        silent: true,
        lineStyle: { color: '#E7E7E7', type: 'dashed', width: 1 },
        data: [{ xAxis: midX }, { yAxis: midY }],
        label: { show: false },
      },
    }],
    animationDuration: 800,
  })
}

// ===========================
// S3: 内容生命周期（面积图）
// ===========================
const initLifecycle = (data) => {
  if (!lifecycleRef.value || !data.length) return
  if (!lifecycleChart) lifecycleChart = echarts.init(lifecycleRef.value)

  const maxPlay = Math.max(...data.map(d => d.avg_play))
  const peakDay = data.find(d => d.avg_play === maxPlay)

  lifecycleChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: p => `发布后第 ${p[0].axisValue} 天<br/>平均播放量 ${formatLarge(p[0].value)}`,
    },
    grid: { top: 24, right: 16, bottom: 28, left: 60 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.day + '天'),
      axisLabel: { color:'#9499A0', fontSize:10, interval: 4 },
      axisLine: { lineStyle: { color:'#E7E7E7' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color:'#9499A0', fontSize:10, formatter: v => formatLarge(v) },
      splitLine: { lineStyle: { color:'#F4F4F4' } },
    },
    series: [{
      type: 'line', smooth: true,
      data: data.map(d => d.avg_play),
      itemStyle: { color: '#7B68EE' },
      areaStyle: { color: 'rgba(123,104,238,0.1)' },
      symbol: 'none',
      markPoint: peakDay ? {
        data: [{ value: formatLarge(peakDay.avg_play), xAxis: data.indexOf(peakDay), yAxis: peakDay.avg_play }],
        label: { fontSize: 10 },
        itemStyle: { color: '#7B68EE' },
        symbolSize: 40,
      } : undefined,
    }],
    animationDuration: 700,
  })
}

// ===========================
// S4: 分类内容表现（水平柱图）
// ===========================
const initCategory = (cats) => {
  if (!categoryRef.value || !cats.length) return
  if (!categoryChart) categoryChart = echarts.init(categoryRef.value)

  const sorted = [...cats].sort((a, b) => b.avg_interaction_rate - a.avg_interaction_rate).slice(0, 12)
  const names  = sorted.map(c => c.category)
  const plays  = sorted.map(c => Math.round(c.avg_play_count))
  const rates  = sorted.map(c => parseFloat(c.avg_interaction_rate?.toFixed(2) || 0))

  categoryChart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].axisValue}<br/>均播放 ${formatLarge(p[0].value)}<br/>互动率 ${p[1]?.value}%`,
    },
    legend: {
      data: ['均播放量', '互动率(%)'],
      bottom: 0, itemWidth: 12, itemHeight: 8,
      textStyle: { fontSize: 11, color: '#61666D' },
    },
    grid: { top: 12, right: 56, bottom: 44, left: 60 },
    xAxis: [
      {
        type: 'value', name: '均播放量',
        nameTextStyle: { color:'#9499A0', fontSize:10 },
        axisLabel: { color:'#9499A0', fontSize:10, formatter: v => formatLarge(v) },
        splitLine: { lineStyle: { color:'#F4F4F4' } },
      },
      {
        type: 'value', name: '互动率(%)',
        nameTextStyle: { color:'#9499A0', fontSize:10 },
        axisLabel: { color:'#9499A0', fontSize:10 },
        splitLine: { show: false },
      },
    ],
    yAxis: {
      type: 'category', data: names,
      axisLabel: { color:'#61666D', fontSize:11 },
    },
    series: [
      {
        name: '均播放量', type: 'bar', xAxisIndex: 0,
        data: plays,
        itemStyle: { color: '#00A1D6', borderRadius: [0,3,3,0] },
        barMaxWidth: 14,
      },
      {
        name: '互动率(%)', type: 'scatter', xAxisIndex: 1,
        data: rates,
        symbolSize: 8,
        itemStyle: { color: '#FB7299' },
      },
    ],
    animationDuration: 600,
  })
}

// ===========================
// S5: 情绪饼图
// ===========================
const initSentimentPie = (sentiment) => {
  if (!sentPieRef.value) return
  if (!sentPieChart) sentPieChart = echarts.init(sentPieRef.value)

  const total = (sentiment.positive || 0) + (sentiment.neutral || 0) + (sentiment.negative || 0)
  const posRate = total ? ((sentiment.positive / total) * 100).toFixed(1) : '0.0'

  sentPieChart.setOption({
    tooltip: { formatter: p => `${p.name}: ${p.value} (${p.percent}%)` },
    graphic: [{
      type: 'text', left: 'center', top: 'middle',
      style: { text: posRate + '%\n正面', fill: '#18191C', fontSize: 13, fontWeight: 'bold', textAlign: 'center' },
    }],
    series: [{
      type: 'pie', radius: ['48%', '68%'],
      center: ['50%', '50%'],
      label: { show: true, fontSize: 11, formatter: '{b}\n{d}%' },
      labelLine: { length: 6, length2: 8 },
      data: [
        { name: '正面', value: sentiment.positive || 0, itemStyle: { color: '#00B578' } },
        { name: '中性', value: sentiment.neutral  || 0, itemStyle: { color: '#9499A0' } },
        { name: '负面', value: sentiment.negative || 0, itemStyle: { color: '#F56C6C' } },
      ],
    }],
    animationDuration: 600,
  })
}

// ===========================
// S5: 情绪趋势折线
// ===========================
const initSentimentTrend = (data) => {
  if (!sentTrendRef.value || !data.length) return
  if (!sentTrendChart) sentTrendChart = echarts.init(sentTrendRef.value)

  sentTrendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: p => `${p[0].axisValue}<br/>正面率 ${p[0].value}%`,
    },
    grid: { top: 16, right: 12, bottom: 28, left: 44 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date.slice(5)),
      axisLabel: { color:'#9499A0', fontSize:10 },
      axisLine: { lineStyle: { color:'#E7E7E7' } },
    },
    yAxis: {
      type: 'value', min: 0, max: 100,
      axisLabel: { color:'#9499A0', fontSize:10, formatter: v => v + '%' },
      splitLine: { lineStyle: { color:'#F4F4F4' } },
    },
    series: [{
      type: 'line', smooth: true,
      data: data.map(d => d.positive_rate),
      itemStyle: { color: '#00B578' },
      areaStyle: { color: 'rgba(0,181,120,0.1)' },
      symbol: 'none',
    }],
    animationDuration: 500,
  })
}

// ===========================
// S6: 热词词云
// ===========================
const initWordcloud = (keywords) => {
  if (!wordcloudRef.value || !keywords.length) return
  if (!wordcloudChart) wordcloudChart = echarts.init(wordcloudRef.value)

  wordcloudChart.setOption({
    tooltip: { formatter: p => `${p.name}: ${p.value}次` },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center', top: 'center',
      width: '90%', height: '90%',
      sizeRange: [12, 40],
      rotationRange: [-30, 30],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      data: keywords.slice(0, 100).map(k => ({
        name: k.word,
        value: k.frequency,
      })),
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => WC_COLORS[Math.floor(Math.random() * WC_COLORS.length)],
      },
      emphasis: { textStyle: { opacity: 0.9 } },
    }],
  })
}

// ===========================
// S7: 发布时间热力图
// ===========================
const WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']
const HOURS    = Array.from({ length:24 }, (_, i) => i + 'h')
const initHeatmap = (raw) => {
  if (!heatmapRef.value || !raw.length) return
  if (!heatmapChart) heatmapChart = echarts.init(heatmapRef.value)

  const matrix = {}
  let maxVal = 0
  raw.forEach(d => {
    const key = `${d.weekday}-${d.hour}`
    matrix[key] = d.count
    if (d.count > maxVal) maxVal = d.count
  })
  const data = []
  for (let w = 0; w < 7; w++) {
    for (let h = 0; h < 24; h++) {
      data.push([h, w, matrix[`${w}-${h}`] || 0])
    }
  }

  heatmapChart.setOption({
    tooltip: { formatter: p => `${WEEKDAYS[p.data[1]]} ${p.data[0]}:00<br/>视频数：${p.data[2]}` },
    grid: { top: 8, right: 60, bottom: 28, left: 44 },
    xAxis: {
      type: 'category', data: HOURS,
      axisLabel: { color:'#9499A0', fontSize:10 },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category', data: WEEKDAYS,
      axisLabel: { color:'#9499A0', fontSize:11 },
      splitArea: { show: true },
    },
    visualMap: {
      min: 0, max: maxVal || 1,
      calculable: true, orient: 'vertical', right: 0, top: 'center',
      inRange: { color: ['#F4F4F4','#B3E5FC','#0288D1','#00A1D6'] },
      textStyle: { color:'#9499A0', fontSize:10 },
    },
    series: [{
      type: 'heatmap', data,
      label: { show: false },
      emphasis: { itemStyle: { borderColor:'#00A1D6', borderWidth:1 } },
    }],
    animationDuration: 600,
  })
}

// ====== 加载所有数据 ======
const loadAll = async () => {
  const [
    ovRes, scatterRes, trendRes,
    lifecycleRes, catRes,
    sentRes, sentTrendRes,
    kwRes, hmRes,
    opRes, authorRes,
  ] = await Promise.allSettled([
    getOverview(),
    getVideoScatter(400),
    getDwVideoTrends(10),
    getLifecycle(),
    getDwCategories(),
    getDwSentiment(),
    getDwSentimentTrends(14),
    getKeywords(100),
    getPublishHeatmap(),
    getOpportunities(8),
    getAuthorRanking(12),
  ])

  // 指标卡
  if (ovRes.status === 'fulfilled') {
    const d = ovRes.value
    homeStore.overview = d
    animTo('videos',   d.total_videos    || 0)
    animTo('play',     d.total_play_count || 0)
    animTo('comments', d.total_comment_count || 0)
    animTo('likes',    d.total_like_count || 0)
    animTo('avg',      Math.round(d.avg_play_count || 0))
  }

  // S1 气泡散点
  if (scatterRes.status === 'fulfilled') {
    const videos = scatterRes.value?.videos || []
    homeStore.scatter = videos
    await nextTick()
    initBubble(videos)
  }

  // S2 趋势视频榜单：先尝试 DW 接口，失败或为空则降级为普通热门榜
  if (trendRes.status === 'fulfilled') {
    const list = Array.isArray(trendRes.value) ? trendRes.value : []
    if (list.length) {
      trendVideos.value = list
      trendIsFallback.value = list[0]?.heat_score === 0
    }
  }
  // DW 接口失败 → 降级调用普通 top-videos
  if (!trendVideos.value.length) {
    try {
      const fallback = await getTopVideos(10)
      const list = Array.isArray(fallback) ? fallback : (fallback?.videos || [])
      trendVideos.value = list.map((v, i) => ({
        bvid: v.bvid,
        title: v.title,
        category: v.category,
        play_count: v.play_count,
        heat_score: 0,
        play_trend: 0,
        like_trend: 0,
        rank_by_heat: i + 1,
        rank_by_play: i + 1,
      }))
      trendIsFallback.value = true
    } catch { /* ignore */ }
  }
  homeStore.trendVideos = trendVideos.value
  homeStore.trendIsFallback = trendIsFallback.value

  // S3 生命周期
  if (lifecycleRes.status === 'fulfilled') {
    const d = lifecycleRes.value?.data || []
    homeStore.lifecycle = d
    if (d.length) { await nextTick(); initLifecycle(d) }
  }

  // S4 分类表现
  if (catRes.status === 'fulfilled') {
    const cats = Array.isArray(catRes.value) ? catRes.value : []
    homeStore.categories = cats
    if (cats.length) { await nextTick(); initCategory(cats) }
  }

  // S5 情绪
  if (sentRes.status === 'fulfilled') {
    homeStore.sentiment = sentRes.value || {}
    await nextTick()
    initSentimentPie(sentRes.value || {})
  }
  if (sentTrendRes.status === 'fulfilled') {
    const d = sentTrendRes.value?.data || []
    homeStore.sentimentTrend = d
    if (d.length) { await nextTick(); initSentimentTrend(d) }
  }

  // S6 词云
  if (kwRes.status === 'fulfilled') {
    const kws = Array.isArray(kwRes.value) ? kwRes.value : (kwRes.value?.keywords || [])
    homeStore.keywords = kws
    if (kws.length) { await nextTick(); initWordcloud(kws) }
  }

  // S7 热力图
  if (hmRes.status === 'fulfilled') {
    const d = hmRes.value?.data || []
    homeStore.heatmap = d
    if (d.length) { await nextTick(); initHeatmap(d) }
  }

  // S8 机会视频
  if (opRes.status === 'fulfilled') {
    opportunities.value = opRes.value?.videos || []
    homeStore.opportunities = opportunities.value
  }

  // S9 UP主排行
  if (authorRes.status === 'fulfilled') {
    authors.value = authorRes.value?.authors || []
    homeStore.authors = authors.value
  }

  homeStore.cachedAt = Date.now()
}

// ====== 从缓存渲染（无需请求接口）======
const renderAll = async () => {
  const s = homeStore
  if (s.overview) {
    const d = s.overview
    animTo('videos',   d.total_videos    || 0)
    animTo('play',     d.total_play_count || 0)
    animTo('comments', d.total_comment_count || 0)
    animTo('likes',    d.total_like_count || 0)
    animTo('avg',      Math.round(d.avg_play_count || 0))
  }
  trendVideos.value   = s.trendVideos
  trendIsFallback.value = s.trendIsFallback
  opportunities.value = s.opportunities
  authors.value       = s.authors

  await nextTick()
  if (s.scatter.length)        initBubble(s.scatter)
  if (s.lifecycle.length)      initLifecycle(s.lifecycle)
  if (s.categories.length)     initCategory(s.categories)
  if (s.sentiment)             initSentimentPie(s.sentiment)
  if (s.sentimentTrend.length) initSentimentTrend(s.sentimentTrend)
  if (s.keywords.length)       initWordcloud(s.keywords)
  if (s.heatmap.length)        initHeatmap(s.heatmap)
}

const handleResize = () => {
  bubbleChart?.resize()
  lifecycleChart?.resize()
  categoryChart?.resize()
  sentPieChart?.resize()
  sentTrendChart?.resize()
  wordcloudChart?.resize()
  heatmapChart?.resize()
}

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 1000)
  window.addEventListener('resize', handleResize)
  await nextTick()
  if (homeStore.isFresh) {
    renderAll()
  } else {
    loadAll()
  }
})

onUnmounted(() => {
  clearInterval(clockTimer)
  window.removeEventListener('resize', handleResize)
  bubbleChart?.dispose()
  lifecycleChart?.dispose()
  categoryChart?.dispose()
  sentPieChart?.dispose()
  sentTrendChart?.dispose()
  wordcloudChart?.dispose()
  heatmapChart?.dispose()
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* 顶部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px;
}
.page-desc {
  font-size: 13px;
  color: var(--text-secondary);
}
.live-clock { text-align: right; }
.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.cache-hint {
  font-size: 12px;
  color: var(--text-placeholder);
}
.cache-refresh {
  color: var(--bili-blue);
  cursor: pointer;
}
.cache-refresh:hover { text-decoration: underline; }
.clock-time {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
  line-height: 1;
}
.clock-date {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

/* 指标条 */
.metrics-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.metric-item {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  display: flex;
  overflow: hidden;
  transition: border-color 0.2s;
}
.metric-item:hover { border-color: var(--bili-blue); }
.metric-accent { width: 4px; flex-shrink: 0; }
.metric-inner { padding: 14px 14px 12px; flex: 1; }
.metric-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.metric-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

/* 通用卡片 */
.card {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
}
.card-header-line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.section-num {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--bili-blue);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.card-desc {
  font-size: 12px;
  color: var(--text-placeholder);
  margin-left: auto;
}

/* 四象限图例 */
.quadrant-legend {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.ql-item {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}
.ql-hot       { background: rgba(0,161,214,0.1); color: #00A1D6; }
.ql-potential { background: rgba(0,181,120,0.1); color: #00B578; }
.ql-clickbait { background: rgba(255,151,54,0.1); color: #FF9736; }
.ql-normal    { background: var(--bg-gray); color: #9499A0; }

/* 图表尺寸 */
.chart-xl   { height: 360px; width: 100%; }
.chart-area { height: 280px; width: 100%; }

/* 双列 */
.row-dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}
.row-single {
  margin-bottom: 16px;
}

/* S2 趋势列表 */
.trend-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}
.trend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-gray-light);
  text-decoration: none;
  transition: background 0.15s;
  border: 1px solid transparent;
}
.trend-item:hover { background: #EDF7FC; border-color: #B3E5FC; }
.trend-rank {
  width: 22px; height: 22px;
  border-radius: 4px;
  background: #E7E7E7;
  color: var(--text-regular);
  font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.rank-gold   { background: rgba(212,136,6,0.85);  color: #fff; }
.rank-silver { background: rgba(140,140,140,0.85); color: #fff; }
.rank-bronze { background: rgba(180,80,30,0.85);   color: #fff; }

.trend-info { flex: 1; min-width: 0; }
.trend-title {
  font-size: 13px; font-weight: 500; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.trend-meta { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.trend-heat { font-size: 11px; color: var(--text-secondary); }
.trend-growth {
  font-size: 13px; font-weight: 600; flex-shrink: 0;
}
.trend-growth.pos     { color: #00B578; }
.trend-growth.neg     { color: #F56C6C; }
.trend-growth.neutral { color: #9499A0; }

/* S5 情绪双图 */
.s5-inner {
  display: flex;
  gap: 12px;
  height: 240px;
}
.s5-pie   { flex: 0 0 200px; }
.s5-trend { flex: 1; min-width: 0; }

/* S8 机会列表 */
.opp-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}
.opp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  text-decoration: none;
  transition: border-color 0.15s;
}
.opp-item:hover { border-color: var(--bili-blue); }
.opp-info { flex: 1; min-width: 0; }
.opp-title {
  font-size: 13px; font-weight: 500; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.opp-meta { display: flex; align-items: center; gap: 8px; margin-top: 3px; }
.opp-play  { font-size: 11px; color: var(--text-secondary); }
.opp-rate  { text-align: center; flex-shrink: 0; }
.opp-rate-val   { font-size: 14px; font-weight: 700; color: #FB7299; }
.opp-rate-label { font-size: 10px; color: var(--text-secondary); }

/* S9 UP主排行 */
.author-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}
.author-card {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 12px;
  position: relative;
  transition: border-color 0.2s;
}
.author-card:hover { border-color: var(--bili-blue); }
.author-top3 { border-color: #B3E5FC; }
.author-rank {
  position: absolute; top: 8px; right: 8px;
  width: 20px; height: 20px; border-radius: 4px;
  background: #E7E7E7; color: var(--text-regular);
  font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.author-name {
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 10px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  padding-right: 24px;
}
.author-stats { display: flex; gap: 8px; }
.author-stat { flex: 1; text-align: center; }
.author-stat-val   { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.author-stat-label { font-size: 10px; color: var(--text-secondary); margin-top: 2px; }

.empty-tip {
  text-align: center;
  color: var(--text-placeholder);
  font-size: 13px;
  padding: 40px 0;
}
</style>
