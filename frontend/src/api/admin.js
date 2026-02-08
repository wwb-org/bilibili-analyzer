import api from './index'

/**
 * 获取用户列表
 */
export const getUsers = () => {
  return api.get('/admin/users')
}

/**
 * 获取采集日志
 * @param {number} limit - 返回记录数
 */
export const getCrawlLogs = (limit = 20) => {
  return api.get('/admin/crawl/logs', { params: { limit } })
}

/**
 * 启动采集任务
 * @param {Object} config - 采集配置
 * @param {number} config.max_videos - 最大采集视频数
 * @param {number} config.comments_per_video - 每视频评论数
 */
export const startCrawl = (config = {}) => {
  return api.post('/admin/crawl/start', config)
}

/**
 * 批量采集指定视频
 * @param {Object} config - 采集配置
 * @param {string[]} config.bvids - BVID列表
 * @param {number} config.comments_per_video - 每视频评论数
 * @param {number} config.danmakus_per_video - 每视频弹幕数
 */
export const startBatchCrawl = (config) => {
  return api.post('/admin/crawl/batch', config)
}

/**
 * 获取采集状态
 */
export const getCrawlStatus = () => {
  return api.get('/admin/crawl/status')
}

/**
 * 获取 ETL 调度器状态
 */
export const getETLStatus = () => {
  return api.get('/admin/etl/status')
}

/**
 * 手动执行 ETL（异步）
 * @param {string} stat_date - 统计日期 (YYYY-MM-DD)
 */
export const runETL = (stat_date = null) => {
  return api.post('/admin/etl/run', { stat_date })
}

/**
 * 手动执行 ETL（同步，等待完成）
 * @param {string} stat_date - 统计日期 (YYYY-MM-DD)
 */
export const runETLSync = (stat_date = null) => {
  return api.post('/admin/etl/run-sync', { stat_date })
}

/**
 * 历史数据回填
 * @param {string} start_date - 开始日期
 * @param {string} end_date - 结束日期
 */
export const backfillETL = (start_date, end_date) => {
  return api.post('/admin/etl/backfill', { start_date, end_date })
}

/**
 * 启动 ETL 调度器
 */
export const startETLScheduler = () => {
  return api.post('/admin/etl/scheduler/start')
}

/**
 * 停止 ETL 调度器
 */
export const stopETLScheduler = () => {
  return api.post('/admin/etl/scheduler/stop')
}

/**
 * 获取服务状态（Kafka、Redis）
 */
export const getServicesStatus = () => {
  return api.get('/live/status/services')
}

// ==================== B站Cookie管理 ====================

/**
 * 获取B站Cookie状态
 * 返回当前Cookie的验证状态和用户信息
 */
export const getBilibiliStatus = () => {
  return api.get('/admin/bilibili/status')
}

/**
 * 验证B站Cookie
 * @param {string} cookie - Cookie字符串
 */
export const verifyBilibiliCookie = (cookie) => {
  return api.post('/admin/bilibili/verify', { cookie })
}

/**
 * 更新B站Cookie
 * 验证Cookie有效后保存到.env文件
 * @param {string} cookie - Cookie字符串
 */
export const updateBilibiliCookie = (cookie) => {
  return api.post('/admin/bilibili/cookie', { cookie })
}

// ==================== 数据概览 ====================

/**
 * 获取数据概览（ODS/DWD/DWS 三层按日期统计）
 */
export const getDataOverview = () => {
  return api.get('/admin/data-overview')
}
