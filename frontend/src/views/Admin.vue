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
      <div class="status-card" :class="{ 'is-online': bilibiliStatus.valid && bilibiliStatus.logged_in }">
        <el-icon class="status-icon"><User /></el-icon>
        <div class="status-info">
          <span class="status-name">B站账号</span>
          <span class="status-text" v-if="bilibiliStatus.valid && bilibiliStatus.logged_in">
            {{ bilibiliStatus.username || '已登录' }}
          </span>
          <span class="status-text" v-else-if="bilibiliStatus.configured">
            Cookie已过期
          </span>
          <span class="status-text" v-else>未配置</span>
        </div>
        <el-button
          size="small"
          type="primary"
          text
          class="status-action"
          @click="showCookieDialog = true"
        >
          <el-icon><Setting /></el-icon>
        </el-button>
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
          <span class="panel-subtitle">采集B站视频及评论数据</span>
        </div>
      </div>
      <div class="panel-body">
        <!-- Tab切换 -->
        <el-tabs v-model="crawlTab" class="crawl-tabs">
          <!-- Tab 1: 热门采集 -->
          <el-tab-pane label="热门视频采集" name="popular">
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
          </el-tab-pane>

          <!-- Tab 2: 批量采集 -->
          <el-tab-pane label="批量指定采集" name="batch">
            <div class="batch-crawl-section">
              <!-- BVID输入区 -->
              <div class="bvid-input-area">
                <div class="input-header">
                  <span class="input-label">输入视频BVID（每行一个，最多50个）</span>
                  <el-button text type="primary" size="small" @click="handleParseBvids">
                    <el-icon><Check /></el-icon>
                    解析验证
                  </el-button>
                </div>
                <el-input
                  v-model="batchCrawlForm.bvidText"
                  type="textarea"
                  :rows="6"
                  placeholder="BV1xx4y1c7mX
BV1yy4y1c7mY
BV1zz4y1c7mZ
...
支持粘贴B站视频链接，会自动提取BVID"
                />
              </div>

              <!-- 解析结果预览 -->
              <div class="bvid-preview" v-if="parsedBvids.valid.length > 0 || parsedBvids.invalid.length > 0">
                <div class="preview-stats">
                  <el-tag type="success" size="small">有效: {{ parsedBvids.valid.length }}</el-tag>
                  <el-tag type="danger" size="small" v-if="parsedBvids.invalid.length > 0">
                    无效: {{ parsedBvids.invalid.length }}
                  </el-tag>
                </div>
                <div class="preview-list" v-if="parsedBvids.valid.length > 0">
                  <el-tag
                    v-for="bvid in parsedBvids.valid.slice(0, 10)"
                    :key="bvid"
                    size="small"
                    closable
                    @close="handleRemoveBvid(bvid)"
                  >
                    {{ bvid }}
                  </el-tag>
                  <span v-if="parsedBvids.valid.length > 10" class="more-hint">
                    ...等{{ parsedBvids.valid.length }}个
                  </span>
                </div>
                <div class="invalid-hint" v-if="parsedBvids.invalid.length > 0">
                  <el-text type="danger" size="small">
                    无效格式: {{ parsedBvids.invalid.slice(0, 3).join(', ') }}
                    {{ parsedBvids.invalid.length > 3 ? '...' : '' }}
                  </el-text>
                </div>
              </div>

              <!-- 采集参数配置 -->
              <el-form :inline="true" :model="batchCrawlForm" class="batch-config">
                <el-form-item label="每视频评论数">
                  <el-input-number
                    v-model="batchCrawlForm.comments_per_video"
                    :min="0"
                    :max="200"
                    :step="20"
                    controls-position="right"
                  />
                </el-form-item>
                <el-form-item label="每视频弹幕数">
                  <el-input-number
                    v-model="batchCrawlForm.danmakus_per_video"
                    :min="0"
                    :max="1000"
                    :step="100"
                    controls-position="right"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="batchCrawlLoading"
                    :disabled="parsedBvids.valid.length === 0"
                    @click="handleStartBatchCrawl"
                  >
                    <el-icon><VideoPlay /></el-icon>
                    启动批量采集
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>

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

    <!-- Cookie管理对话框 -->
    <el-dialog v-model="showCookieDialog" title="管理B站Cookie" width="560px">
      <div class="cookie-dialog-content">
        <!-- 当前状态 -->
        <div class="cookie-status">
          <span class="cookie-status-label">当前状态：</span>
          <el-tag
            v-if="bilibiliStatus.valid && bilibiliStatus.logged_in"
            type="success"
            size="small"
          >
            已登录 - {{ bilibiliStatus.username }}
          </el-tag>
          <el-tag v-else-if="bilibiliStatus.configured" type="danger" size="small">
            Cookie已过期
          </el-tag>
          <el-tag v-else type="info" size="small">未配置</el-tag>
        </div>

        <!-- Cookie输入 -->
        <div class="cookie-input-section">
          <div class="cookie-input-label">
            <span>Cookie字符串：</span>
            <el-link
              type="primary"
              :underline="false"
              href="https://www.bilibili.com"
              target="_blank"
            >
              如何获取Cookie?
            </el-link>
          </div>
          <el-input
            v-model="cookieForm.cookie"
            type="textarea"
            :rows="5"
            placeholder="请粘贴从浏览器复制的Cookie字符串，需包含SESSDATA字段"
          />
        </div>

        <!-- 验证结果 -->
        <div class="cookie-verify-section" v-if="cookieVerifyResult">
          <div class="verify-result" :class="{ 'is-success': cookieVerifyResult.valid }">
            <el-icon v-if="cookieVerifyResult.valid"><CircleCheck /></el-icon>
            <el-icon v-else><CircleClose /></el-icon>
            <span v-if="cookieVerifyResult.valid && cookieVerifyResult.logged_in">
              验证成功：{{ cookieVerifyResult.username }} (UID: {{ cookieVerifyResult.uid }})
            </span>
            <span v-else>{{ cookieVerifyResult.message }}</span>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="cookie-dialog-footer">
          <el-button @click="handleVerifyCookie" :loading="cookieVerifying">
            <el-icon><Search /></el-icon>
            验证
          </el-button>
          <div class="footer-right">
            <el-button @click="showCookieDialog = false">取消</el-button>
            <el-button
              type="primary"
              @click="handleSaveCookie"
              :loading="cookieSaving"
              :disabled="!cookieVerifyResult?.valid || !cookieVerifyResult?.logged_in"
            >
              保存
            </el-button>
          </div>
        </div>
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
  User,
  Setting,
  Search,
  CircleCheck,
  CircleClose,
  Check
} from '@element-plus/icons-vue'
import {
  getUsers,
  getCrawlLogs,
  startCrawl,
  startBatchCrawl,
  getETLStatus,
  runETL,
  backfillETL,
  startETLScheduler,
  stopETLScheduler,
  getServicesStatus,
  getBilibiliStatus,
  verifyBilibiliCookie,
  updateBilibiliCookie
} from '@/api/admin'

// ========== 状态 ==========
const redisStatus = ref(false)
const kafkaStatus = ref(false)
const bilibiliStatus = ref({
  configured: false,
  valid: false,
  logged_in: false,
  username: '',
  message: ''
})
const etlStatus = ref({ is_running: false, jobs: [] })

const crawlConfig = reactive({
  max_videos: 50,
  comments_per_video: 100,
  danmakus_per_video: 500
})
const crawlLoading = ref(false)
const crawlLogs = ref([])
const logsLoading = ref(false)
const crawlTab = ref('popular')

// 批量采集
const batchCrawlForm = reactive({
  bvidText: '',
  comments_per_video: 100,
  danmakus_per_video: 500
})
const batchCrawlLoading = ref(false)
const parsedBvids = reactive({
  valid: [],
  invalid: []
})

const users = ref([])
const usersLoading = ref(false)

const showBackfillDialog = ref(false)
const backfillLoading = ref(false)
const backfillForm = reactive({
  start_date: null,
  end_date: null
})

// Cookie管理
const showCookieDialog = ref(false)
const cookieVerifying = ref(false)
const cookieSaving = ref(false)
const cookieForm = reactive({
  cookie: ''
})
const cookieVerifyResult = ref(null)

// ========== 方法 ==========
const fetchServicesStatus = async () => {
  try {
    const res = await getServicesStatus()
    kafkaStatus.value = res.kafka?.available || false
    redisStatus.value = res.redis?.available || false
  } catch (e) {
    console.error('获取服务状态失败', e)
  }
}

const fetchBilibiliStatus = async () => {
  try {
    const res = await getBilibiliStatus()
    bilibiliStatus.value = res
  } catch (e) {
    console.error('获取B站状态失败', e)
    bilibiliStatus.value = {
      configured: false,
      valid: false,
      logged_in: false,
      message: '获取状态失败'
    }
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

// ========== 批量采集方法 ==========
const handleParseBvids = () => {
  const text = batchCrawlForm.bvidText.trim()
  if (!text) {
    ElMessage.warning('请输入BVID')
    return
  }

  // BVID正则
  const bvidPattern = /BV[a-zA-Z0-9]{10}/g

  // 提取所有匹配的BVID
  const matches = text.match(bvidPattern) || []
  const uniqueBvids = [...new Set(matches)]

  // 按行分割，找出无法识别的行
  const lines = text.split(/[\n,;，；]/).map(l => l.trim()).filter(l => l)
  const invalid = []

  for (const line of lines) {
    const found = line.match(bvidPattern)
    if (!found && line && !line.startsWith('#')) {
      invalid.push(line.length > 20 ? line.slice(0, 20) + '...' : line)
    }
  }

  parsedBvids.valid = uniqueBvids
  parsedBvids.invalid = [...new Set(invalid)]

  if (parsedBvids.valid.length === 0) {
    ElMessage.warning('未识别到有效的BVID')
  } else {
    ElMessage.success(`识别到 ${parsedBvids.valid.length} 个有效BVID`)
  }
}

const handleRemoveBvid = (bvid) => {
  const index = parsedBvids.valid.indexOf(bvid)
  if (index > -1) {
    parsedBvids.valid.splice(index, 1)
  }
}

const handleStartBatchCrawl = async () => {
  if (parsedBvids.valid.length === 0) {
    ElMessage.warning('请先解析BVID')
    return
  }

  if (parsedBvids.valid.length > 50) {
    ElMessage.warning('单次最多采集50个视频')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要采集 ${parsedBvids.valid.length} 个视频吗？\n每个视频将采集 ${batchCrawlForm.comments_per_video} 条评论、${batchCrawlForm.danmakus_per_video} 条弹幕。\n预计耗时约 ${Math.ceil(parsedBvids.valid.length * 8 / 60)} 分钟。`,
      '确认采集',
      { type: 'info' }
    )

    batchCrawlLoading.value = true

    await startBatchCrawl({
      bvids: parsedBvids.valid,
      comments_per_video: batchCrawlForm.comments_per_video,
      danmakus_per_video: batchCrawlForm.danmakus_per_video
    })

    ElMessage.success('批量采集任务已启动，请稍后刷新日志查看进度')

    // 清空输入
    batchCrawlForm.bvidText = ''
    parsedBvids.valid = []
    parsedBvids.invalid = []

    // 延迟刷新日志
    setTimeout(fetchCrawlLogs, 3000)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('启动采集失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    batchCrawlLoading.value = false
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

// ========== Cookie管理方法 ==========
const handleVerifyCookie = async () => {
  if (!cookieForm.cookie.trim()) {
    ElMessage.warning('请输入Cookie')
    return
  }

  cookieVerifying.value = true
  cookieVerifyResult.value = null

  try {
    const res = await verifyBilibiliCookie(cookieForm.cookie.trim())
    cookieVerifyResult.value = res
  } catch (e) {
    cookieVerifyResult.value = {
      valid: false,
      logged_in: false,
      message: e.response?.data?.detail || '验证失败'
    }
  } finally {
    cookieVerifying.value = false
  }
}

const handleSaveCookie = async () => {
  if (!cookieVerifyResult.value?.valid || !cookieVerifyResult.value?.logged_in) {
    ElMessage.warning('请先验证Cookie')
    return
  }

  cookieSaving.value = true

  try {
    await updateBilibiliCookie(cookieForm.cookie.trim())
    ElMessage.success('Cookie保存成功')
    showCookieDialog.value = false
    // 重置表单
    cookieForm.cookie = ''
    cookieVerifyResult.value = null
    // 刷新状态
    await fetchBilibiliStatus()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    cookieSaving.value = false
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
  fetchBilibiliStatus()
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

/* 批量采集样式 */
.crawl-tabs {
  margin-bottom: 16px;
}

.batch-crawl-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bvid-input-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-label {
  font-size: 14px;
  color: var(--text-regular);
}

.bvid-preview {
  padding: 12px 16px;
  background: var(--bg-gray-light);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-stats {
  display: flex;
  gap: 8px;
}

.preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.more-hint {
  font-size: 12px;
  color: var(--text-secondary);
  align-self: center;
}

.invalid-hint {
  margin-top: 4px;
}

.batch-config {
  margin-top: 8px;
}

.batch-config .el-form-item {
  margin-bottom: 0;
  margin-right: 24px;
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

/* 状态卡片操作按钮 */
.status-action {
  margin-left: auto;
  padding: 4px;
}

/* Cookie对话框 */
.cookie-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.cookie-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cookie-status-label {
  font-size: 14px;
  color: var(--text-regular);
}

.cookie-input-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cookie-input-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: var(--text-regular);
}

.cookie-verify-section {
  margin-top: 4px;
}

.verify-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.verify-result.is-success {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.verify-result .el-icon {
  font-size: 16px;
}

.cookie-dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-right {
  display: flex;
  gap: 12px;
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
