<template>
  <div class="admin-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">系统管理</h1>
      <p class="page-desc">管理员专属功能：数据采集、ETL调度、系统状态监控</p>
    </div>

    <!-- 服务状态卡片 -->
    <div class="status-grid">
      <div class="status-card is-online">
        <el-icon class="status-icon"><Connection /></el-icon>
        <div class="status-info">
          <span class="status-name">MySQL</span>
          <span class="status-text">已连接</span>
        </div>
      </div>
      <div class="status-card" :class="{ 'is-online': bilibiliLoggedIn }">
        <el-icon class="status-icon"><User /></el-icon>
        <div class="status-info">
          <span class="status-name">B站账号</span>
          <span class="status-text">{{ bilibiliLoggedIn ? '已登录' : '未登录' }}</span>
        </div>
      </div>
      <div class="status-card" :class="{ 'is-online': redisStatus }">
        <el-icon class="status-icon"><DataLine /></el-icon>
        <div class="status-info">
          <span class="status-name">Redis</span>
          <span class="status-text">{{ redisStatus ? '已连接' : '未连接' }}</span>
        </div>
      </div>
      <div class="status-card" :class="{ 'is-online': kafkaStatus }">
        <el-icon class="status-icon"><Message /></el-icon>
        <div class="status-info">
          <span class="status-name">Kafka</span>
          <span class="status-text">{{ kafkaStatus ? '已连接' : '未连接' }}</span>
        </div>
      </div>
      <div class="status-card" :class="{ 'is-online': etlStatus.is_running }">
        <el-icon class="status-icon"><Timer /></el-icon>
        <div class="status-info">
          <span class="status-name">ETL 调度器</span>
          <span class="status-text">{{ etlStatus.is_running ? '运行中' : '已停止' }}</span>
        </div>
      </div>
    </div>

    <!-- 数据采集模块 -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title-group">
          <h3 class="panel-title">数据采集</h3>
          <span class="panel-subtitle">采集B站热门视频及评论数据</span>
        </div>
      </div>
      <div class="panel-body">
        <div class="crawl-config">
          <el-form :inline="true" :model="crawlConfig">
            <el-form-item label="采集视频数">
              <el-input-number
                v-model="crawlConfig.max_videos"
                :min="10"
                :max="200"
                :step="10"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="每视频评论数">
              <el-input-number
                v-model="crawlConfig.comments_per_video"
                :min="20"
                :max="200"
                :step="20"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="每视频弹幕数">
              <el-input-number
                v-model="crawlConfig.danmakus_per_video"
                :min="0"
                :max="1000"
                :step="100"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="crawlLoading"
                @click="handleStartCrawl"
              >
                <el-icon><VideoPlay /></el-icon>
                启动采集任务
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 采集日志表格 -->
        <div class="log-section">
          <div class="section-header">
            <span class="section-title">最近采集日志</span>
            <el-button text type="primary" @click="fetchCrawlLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
          <el-table :data="crawlLogs" stripe style="width: 100%" v-loading="logsLoading">
            <el-table-column prop="started_at" label="开始时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.started_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="task_name" label="任务名称" min-width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="video_count" label="视频数" width="100" />
            <el-table-column prop="comment_count" label="评论数" width="100" />
            <el-table-column prop="danmaku_count" label="弹幕数" width="100" />
            <el-table-column prop="error_msg" label="错误信息" min-width="150" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </div>

    <!-- ETL 调度管理模块 -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title-group">
          <h3 class="panel-title">ETL 调度管理</h3>
          <span class="panel-subtitle">数据仓库 ETL 任务调度</span>
        </div>
      </div>
      <div class="panel-body">
        <div class="etl-actions">
          <el-button
            :type="etlStatus.is_running ? 'danger' : 'success'"
            @click="toggleETLScheduler"
          >
            <el-icon>
              <VideoPause v-if="etlStatus.is_running" />
              <VideoPlay v-else />
            </el-icon>
            {{ etlStatus.is_running ? '停止调度器' : '启动调度器' }}
          </el-button>
          <el-button @click="handleRunETL">
            <el-icon><CaretRight /></el-icon>
            手动执行 ETL
          </el-button>
          <el-button @click="showBackfillDialog = true">
            <el-icon><Clock /></el-icon>
            历史回填
          </el-button>
        </div>

        <div class="etl-info" v-if="etlStatus.jobs && etlStatus.jobs.length > 0">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="调度状态">
              <el-tag :type="etlStatus.is_running ? 'success' : 'info'" size="small">
                {{ etlStatus.is_running ? '运行中' : '已停止' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="下次执行时间">
              {{ etlStatus.jobs[0]?.next_run_time || '未知' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </div>

    <!-- 用户管理模块 -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title-group">
          <h3 class="panel-title">用户管理</h3>
          <span class="panel-subtitle">系统用户列表</span>
        </div>
      </div>
      <div class="panel-body">
        <el-table :data="users" stripe style="width: 100%" v-loading="usersLoading">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="username" label="用户名" width="150" />
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                {{ row.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 历史回填对话框 -->
    <el-dialog v-model="showBackfillDialog" title="历史数据回填" width="420px">
      <el-form :model="backfillForm" label-width="100px">
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="backfillForm.start_date"
            type="date"
            placeholder="选择开始日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="backfillForm.end_date"
            type="date"
            placeholder="选择结束日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBackfillDialog = false">取消</el-button>
        <el-button type="primary" @click="handleBackfill" :loading="backfillLoading">
          开始回填
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection,
  DataLine,
  Message,
  Timer,
  VideoPlay,
  VideoPause,
  Refresh,
  CaretRight,
  Clock,
  User
} from '@element-plus/icons-vue'
import {
  getUsers,
  getCrawlLogs,
  startCrawl,
  getETLStatus,
  runETL,
  backfillETL,
  startETLScheduler,
  stopETLScheduler,
  getServicesStatus
} from '@/api/admin'

// ========== 状态 ==========
const redisStatus = ref(false)
const kafkaStatus = ref(false)
const bilibiliLoggedIn = ref(false)
const etlStatus = ref({ is_running: false, jobs: [] })

const crawlConfig = reactive({
  max_videos: 50,
  comments_per_video: 100,
  danmakus_per_video: 500
})
const crawlLoading = ref(false)
const crawlLogs = ref([])
const logsLoading = ref(false)

const users = ref([])
const usersLoading = ref(false)

const showBackfillDialog = ref(false)
const backfillLoading = ref(false)
const backfillForm = reactive({
  start_date: null,
  end_date: null
})

// ========== 方法 ==========
const fetchServicesStatus = async () => {
  try {
    const res = await getServicesStatus()
    kafkaStatus.value = res.kafka?.available || false
    redisStatus.value = res.redis?.available || false
    bilibiliLoggedIn.value = res.bilibili?.logged_in || false
  } catch (e) {
    console.error('获取服务状态失败', e)
  }
}

const fetchETLStatus = async () => {
  try {
    const res = await getETLStatus()
    etlStatus.value = res
  } catch (e) {
    console.error('获取ETL状态失败', e)
  }
}

const fetchCrawlLogs = async () => {
  logsLoading.value = true
  try {
    crawlLogs.value = await getCrawlLogs(20)
  } catch (e) {
    console.error('获取采集日志失败', e)
  } finally {
    logsLoading.value = false
  }
}

const fetchUsers = async () => {
  usersLoading.value = true
  try {
    users.value = await getUsers()
  } catch (e) {
    console.error('获取用户列表失败', e)
  } finally {
    usersLoading.value = false
  }
}

const handleStartCrawl = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要启动采集任务吗？将采集 ${crawlConfig.max_videos} 个视频，每个视频 ${crawlConfig.comments_per_video} 条评论、${crawlConfig.danmakus_per_video} 条弹幕。`,
      '确认启动',
      { type: 'info' }
    )

    crawlLoading.value = true
    await startCrawl(crawlConfig)
    ElMessage.success('采集任务已启动，请稍后刷新日志查看进度')

    // 延迟刷新日志
    setTimeout(fetchCrawlLogs, 3000)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('启动采集失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    crawlLoading.value = false
  }
}

const toggleETLScheduler = async () => {
  try {
    if (etlStatus.value.is_running) {
      await stopETLScheduler()
      ElMessage.success('ETL 调度器已停止')
    } else {
      await startETLScheduler()
      ElMessage.success('ETL 调度器已启动')
    }
    await fetchETLStatus()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  }
}

const handleRunETL = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要手动执行 ETL 吗？将处理昨日数据。',
      '确认执行',
      { type: 'info' }
    )

    await runETL()
    ElMessage.success('ETL 任务已提交执行')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('执行失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

const handleBackfill = async () => {
  if (!backfillForm.start_date || !backfillForm.end_date) {
    ElMessage.warning('请选择日期范围')
    return
  }

  try {
    backfillLoading.value = true
    const startDate = formatDate(backfillForm.start_date)
    const endDate = formatDate(backfillForm.end_date)

    await backfillETL(startDate, endDate)
    ElMessage.success('回填任务已提交')
    showBackfillDialog.value = false
  } catch (e) {
    ElMessage.error('回填失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    backfillLoading.value = false
  }
}

// ========== 工具函数 ==========
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const formatDate = (date) => {
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const getStatusType = (status) => {
  const map = { running: 'warning', success: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { running: '执行中', success: '成功', failed: '失败' }
  return map[status] || status
}

// ========== 生命周期 ==========
onMounted(() => {
  fetchServicesStatus()
  fetchETLStatus()
  fetchCrawlLogs()
  fetchUsers()
})
</script>

<style scoped>
.admin-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* 页面标题 */
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

/* 服务状态卡片 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.status-card {
  background: var(--bg-white);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-icon {
  font-size: 28px;
  color: var(--text-secondary);
}

.status-card.is-online .status-icon {
  color: var(--color-success);
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-name {
  font-size: 14px;
  color: var(--text-regular);
  font-weight: 500;
}

.status-text {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 面板样式 */
.panel {
  background: var(--bg-white);
  border-radius: 12px;
  border: 1px solid var(--border-light);
  margin-bottom: 24px;
}

.panel-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
}

.panel-title-group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.panel-subtitle {
  font-size: 14px;
  color: var(--text-placeholder);
}

.panel-body {
  padding: 24px;
}

/* 采集配置 */
.crawl-config {
  margin-bottom: 24px;
}

.crawl-config .el-form-item {
  margin-bottom: 0;
  margin-right: 24px;
}

/* 日志区域 */
.log-section {
  margin-top: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-regular);
}

/* ETL 操作区 */
.etl-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.etl-info {
  margin-top: 8px;
}

/* 响应式适配 */
@media (max-width: 1400px) {
  .status-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1000px) {
  .status-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .crawl-config .el-form--inline .el-form-item {
    display: block;
    margin-bottom: 12px;
  }

  .etl-actions {
    flex-wrap: wrap;
  }
}
</style>
