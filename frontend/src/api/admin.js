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
