"""
ETL调度器

功能：
- 每日凌晨2点自动执行所有ETL任务
- 支持手动触发
- 支持历史数据回填（backfill）
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.etl.dwd_tasks import VideoSnapshotETL, CommentDailyETL
from app.etl.dws_tasks import (
    StatsDailyETL,
    CategoryDailyETL,
    SentimentDailyETL,
    VideoTrendETL,
)
from app.etl.keyword_tasks import KeywordDailyETL, KeywordStatsETL

logger = logging.getLogger(__name__)


class ETLScheduler:
    """
    ETL调度器

    管理所有ETL任务的调度和执行
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def run_daily_etl(self, stat_date: Optional[date] = None) -> List[dict]:
        """
        执行每日ETL任务

        Args:
            stat_date: 统计日期，默认为昨日

        Returns:
            所有任务的执行结果列表
        """
        if stat_date is None:
            stat_date = date.today() - timedelta(days=1)

        db = SessionLocal()
        results = []

        try:
            logger.info(f"=== 开始执行每日ETL，日期: {stat_date} ===")

            # 1. DWD层：视频快照
            logger.info("[1/8] 执行视频快照ETL...")
            task1 = VideoSnapshotETL(db)
            results.append(task1.run(stat_date))

            # 2. DWD层：评论每日增量
            logger.info("[2/8] 执行评论每日增量ETL...")
            task2 = CommentDailyETL(db)
            results.append(task2.run(stat_date))

            # 3. DWS层：全局统计
            logger.info("[3/8] 执行全局统计ETL...")
            task3 = StatsDailyETL(db)
            results.append(task3.run(stat_date))

            # 4. DWS层：分区统计
            logger.info("[4/8] 执行分区统计ETL...")
            task4 = CategoryDailyETL(db)
            results.append(task4.run(stat_date))

            # 5. DWS层：情感统计
            logger.info("[5/8] 执行情感统计ETL...")
            task5 = SentimentDailyETL(db)
            results.append(task5.run(stat_date))

            # 6. DWS层：视频趋势
            logger.info("[6/8] 执行视频趋势ETL...")
            task6 = VideoTrendETL(db)
            results.append(task6.run(stat_date))

            # 7. DWD层：热词明细
            logger.info("[7/8] 执行热词明细ETL...")
            task7 = KeywordDailyETL(db)
            results.append(task7.run(stat_date))

            # 8. DWS层：热词聚合
            logger.info("[8/8] 执行热词聚合ETL...")
            task8 = KeywordStatsETL(db)
            results.append(task8.run(stat_date))

            logger.info(f"=== 每日ETL执行完成，共 {len(results)} 个任务 ===")

        except Exception as e:
            logger.error(f"ETL执行失败: {e}")
            raise

        finally:
            db.close()

        return results

    def backfill(self, start_date: date, end_date: date) -> List[dict]:
        """
        历史数据回填

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            所有任务的执行结果列表
        """
        current = start_date
        all_results = []

        logger.info(f"=== 开始历史回填，从 {start_date} 到 {end_date} ===")

        while current <= end_date:
            logger.info(f"回填日期: {current}")
            try:
                results = self.run_daily_etl(current)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"回填 {current} 失败: {e}")
            current += timedelta(days=1)

        logger.info(f"=== 历史回填完成，共处理 {len(all_results)} 个任务 ===")
        return all_results

    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("ETL调度器已在运行中")
            return

        # 每天凌晨2点执行
        self.scheduler.add_job(
            self.run_daily_etl,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_etl',
            replace_existing=True,
            name='每日ETL任务'
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("ETL调度器已启动，每天凌晨2点执行")

    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("ETL调度器已停止")

    def get_status(self) -> dict:
        """
        获取调度器状态

        Returns:
            调度器状态信息
        """
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None
                })

        return {
            "is_running": self.is_running,
            "jobs": jobs
        }


# 全局实例
etl_scheduler = ETLScheduler()
