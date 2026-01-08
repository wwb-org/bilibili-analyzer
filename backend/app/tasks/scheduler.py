"""
定时任务调度
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.models import Video, Comment, CrawlLog
from app.services.crawler import BilibiliCrawler
from app.services.analyzer import DataAnalyzer


scheduler = BackgroundScheduler()


def crawl_popular_videos():
    """采集热门视频定时任务"""
    db = SessionLocal()
    crawler = BilibiliCrawler()

    log = CrawlLog(
        task_name="crawl_popular_videos",
        status="running",
        started_at=datetime.now()
    )
    db.add(log)
    db.commit()

    try:
        video_count = 0

        # 采集前5页热门视频
        for page in range(1, 6):
            videos = crawler.get_popular_videos(page=page)
            if not videos:
                continue

            for raw_video in videos:
                video_data = crawler.parse_video_data(raw_video)

                # 检查是否已存在
                existing = db.query(Video).filter(
                    Video.bvid == video_data['bvid']
                ).first()

                if existing:
                    # 更新数据
                    for key, value in video_data.items():
                        if value is not None:
                            setattr(existing, key, value)
                else:
                    # 新增
                    video = Video(**video_data)
                    if video_data.get('publish_time'):
                        video.publish_time = datetime.fromtimestamp(video_data['publish_time'])
                    db.add(video)
                    video_count += 1

            db.commit()

        # 更新热词
        analyzer = DataAnalyzer(db)
        analyzer.update_keywords()

        log.status = "success"
        log.video_count = video_count
        log.finished_at = datetime.now()
        db.commit()

        print(f"[{datetime.now()}] 采集完成，新增 {video_count} 条视频")

    except Exception as e:
        log.status = "failed"
        log.error_msg = str(e)
        log.finished_at = datetime.now()
        db.commit()
        print(f"[{datetime.now()}] 采集失败: {e}")

    finally:
        db.close()


def init_scheduler():
    """初始化定时任务"""
    # 每10分钟采集一次热门视频
    scheduler.add_job(
        crawl_popular_videos,
        trigger=IntervalTrigger(minutes=10),
        id='crawl_popular_videos',
        replace_existing=True
    )

    scheduler.start()
    print("定时任务调度器已启动")


def shutdown_scheduler():
    """关闭定时任务"""
    scheduler.shutdown()
