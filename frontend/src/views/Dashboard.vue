<template>
  <div class="dashboard">
    <!-- 顶部导航 -->
    <header class="header">
      <h1>B站视频内容趋势分析系统</h1>
      <div class="header-right">
        <span>{{ username }}</span>
        <el-button @click="logout" type="danger" size="small">退出</el-button>
      </div>
    </header>

    <!-- 数据概览卡片 -->
    <div class="overview-cards">
      <el-card v-for="item in overviewData" :key="item.label" class="overview-card">
        <div class="card-value">{{ item.value }}</div>
        <div class="card-label">{{ item.label }}</div>
      </el-card>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card>
            <template #header>热词词云</template>
            <div ref="wordCloudRef" class="chart"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>分区分布</template>
            <div ref="pieChartRef" class="chart"></div>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="16">
          <el-card>
            <template #header>播放量趋势</template>
            <div ref="lineChartRef" class="chart"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <template #header>情感分析</template>
            <div ref="sentimentRef" class="chart"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '用户')

// 图表引用
const wordCloudRef = ref()
const pieChartRef = ref()
const lineChartRef = ref()
const sentimentRef = ref()

// 概览数据
const overviewData = ref([
  { label: '视频总数', value: '0' },
  { label: '总播放量', value: '0' },
  { label: '总点赞数', value: '0' },
  { label: '总评论数', value: '0' }
])

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}

onMounted(() => {
  // TODO: 初始化图表和加载数据
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #fff;
  margin-bottom: 20px;
  border-radius: 4px;
}
.header h1 {
  font-size: 20px;
  color: #333;
}
.overview-cards {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.overview-card {
  flex: 1;
  text-align: center;
}
.card-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}
.card-label {
  color: #666;
  margin-top: 5px;
}
.chart {
  height: 300px;
}
</style>
