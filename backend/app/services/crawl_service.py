"""
采集服务层
封装完整的采集业务逻辑，集成情感分析和日志记录
"""
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.crawler import BilibiliCrawler
from app.services.nlp import NLPAnalyzer
from app.models.models import Video, Comment, CrawlLog
from app.core.database import SessionLocal


class CrawlService:
    """采集服务"""

    def __init__(self, enable_kafka: bool = False):
        self.crawler = BilibiliCrawler(enable_kafka=enable_kafka)
        self.nlp = NLPAnalyzer()

    def _get_sentiment_label(self, score: float) -> str:
        """根据情感分数获取标签"""
        if score >= 0.6:
            return 'positive'
        elif score <= 0.4:
            return 'negative'
        else:
            return 'neutral'

    def crawl_popular_videos(
        self,
        max_videos: int = 50,
        comments_per_video: int = 100
    ) -> Dict:
        """
        采集热门视频（带情感分析和日志记录）

        Args:
            max_videos: 最多采集视频数
            comments_per_video: 每个视频采集评论数

        Returns:
            采集统计信息
        """
        db = SessionLocal()
        stats = {
            'videos_crawled': 0,
            'videos_saved': 0,
            'comments_saved': 0,
            'errors': []
        }

        # 创建采集日志
        log = CrawlLog(
            task_name='采集热门视频',
            status='running',
            started_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()

        try:
            print(f"\n[采集任务] 开始采集热门视频，目标: {max_videos} 个")

            # 获取热门视频列表
            videos = self.crawler.get_popular_videos(page=1, page_size=max_videos)
            if not videos:
                raise Exception("获取热门视频失败")

            print(f"[采集任务] 获取到 {len(videos)} 个热门视频")

            # 遍历每个视频
            for i, video_raw in enumerate(videos[:max_videos], 1):
                try:
                    bvid = video_raw.get('bvid')
                    print(f"\n[{i}/{max_videos}] 处理视频: {bvid}")

                    # 获取视频详情
                    detail = self.crawler.get_video_detail(bvid)
                    if not detail:
                        stats['errors'].append(f"{bvid}: 获取详情失败")
                        continue

                    # 解析并保存视频
                    video_data = self.crawler.parse_video_data(detail)
                    video = self.crawler.save_video(video_data, db)

                    if video:
                        stats['videos_saved'] += 1
                        print(f"  [OK] 视频已保存")

                        # 采集并分析评论
                        oid = detail.get('aid')
                        if oid:
                            comment_count = self._crawl_and_analyze_comments(
                                video.id, oid, comments_per_video, db
                            )
                            stats['comments_saved'] += comment_count
                            print(f"  [OK] 评论已保存: {comment_count} 条")

                    stats['videos_crawled'] += 1

                except Exception as e:
                    error_msg = f"{bvid}: {str(e)}"
                    stats['errors'].append(error_msg)
                    print(f"  [FAIL] 错误: {e}")

            # 更新日志状态
            log.status = 'success'
            log.video_count = stats['videos_saved']
            log.comment_count = stats['comments_saved']
            log.finished_at = datetime.utcnow()
            db.commit()

            print(f"\n[采集任务] 完成！视频: {stats['videos_saved']}, 评论: {stats['comments_saved']}")
            return stats

        except Exception as e:
            # 记录失败
            log.status = 'failed'
            log.error_msg = str(e)
            log.finished_at = datetime.utcnow()
            db.commit()

            stats['errors'].append(f"全局错误: {str(e)}")
            print(f"[采集任务] 失败: {e}")
            return stats

        finally:
            db.close()

    def _crawl_and_analyze_comments(
        self,
        video_id: int,
        oid: int,
        max_comments: int,
        db: Session
    ) -> int:
        """
        采集评论并进行情感分析

        Args:
            video_id: 视频数据库ID
            oid: B站视频aid
            max_comments: 最多采集评论数
            db: 数据库会话

        Returns:
            保存的评论数量
        """
        saved_count = 0
        page_size = 20
        total_pages = (max_comments + page_size - 1) // page_size

        try:
            for page in range(1, total_pages + 1):
                comments_raw = self.crawler.get_video_comments(oid, page=page, page_size=page_size)
                if not comments_raw:
                    break

                for comment_raw in comments_raw:
                    rpid = comment_raw.get('rpid')  # B站评论ID
                    content = comment_raw.get('content', {}).get('message', '')
                    user_name = comment_raw.get('member', {}).get('uname', '')
                    like_count = comment_raw.get('like', 0)

                    if not content or not rpid:
                        continue

                    # 检查评论是否已存在（去重）
                    existing = db.query(Comment).filter(Comment.rpid == rpid).first()
                    if existing:
                        continue

                    # 情感分析
                    sentiment_score = self.nlp.analyze_sentiment(content)
                    sentiment_label = self._get_sentiment_label(sentiment_score)

                    # 创建评论记录
                    comment = Comment(
                        rpid=rpid,
                        video_id=video_id,
                        content=content,
                        user_name=user_name,
                        sentiment_score=sentiment_score,
                        like_count=like_count
                    )
                    db.add(comment)
                    saved_count += 1

                    # 每20条提交一次
                    if saved_count % 20 == 0:
                        db.commit()

            # 最后提交剩余的
            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            print(f"    [WARN] 评论采集部分失败: {e}")
            return saved_count
