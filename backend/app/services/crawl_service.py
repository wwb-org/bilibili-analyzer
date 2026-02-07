"""
采集服务层
封装完整的采集业务逻辑，集成情感分析和日志记录
"""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.crawler import BilibiliCrawler
from app.models.models import Video, Comment, Danmaku, CrawlLog
from app.core.database import SessionLocal


class CrawlService:
    """采集服务"""

    def __init__(self):
        # 使用动态Cookie初始化爬虫（支持运行时更新）
        from app.services.bilibili_auth import get_current_cookie
        self.crawler = BilibiliCrawler(cookie=get_current_cookie())

    def crawl_popular_videos(
        self,
        max_videos: int = 50,
        comments_per_video: int = 100,
        danmakus_per_video: int = 500
    ) -> Dict:
        """
        采集热门视频（带情感分析和日志记录）

        Args:
            max_videos: 最多采集视频数
            comments_per_video: 每个视频采集评论数
            danmakus_per_video: 每个视频采集弹幕数

        Returns:
            采集统计信息
        """
        db = SessionLocal()
        stats = {
            'videos_crawled': 0,
            'videos_saved': 0,
            'comments_saved': 0,
            'danmakus_saved': 0,
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
            videos = []
            page = 1
            page_size = min(max_videos, 50)
            while len(videos) < max_videos:
                batch = self.crawler.get_popular_videos(page=page, page_size=page_size)
                if not batch:
                    break
                videos.extend(batch)
                if len(batch) < page_size:
                    break
                page += 1

            if not videos:
                raise Exception("获取热门视频失败")

            print(f"[采集任务] 获取到 {len(videos)} 个热门视频")

            # 遍历每个视频
            for i, video_raw in enumerate(videos[:max_videos], 1):
                try:
                    bvid = video_raw.get('bvid')
                    print(f"\n[{i}/{max_videos}] 处理视频: {bvid}")

                    # 从列表数据获取分区信息（详情API不返回分区名）
                    category_from_list = video_raw.get('tname', '') or video_raw.get('tnamev2', '')

                    # 获取视频详情（用于获取cid、aid等）
                    detail = self.crawler.get_video_detail(bvid)
                    if not detail:
                        stats['errors'].append(f"{bvid}: 获取详情失败")
                        continue

                    # 解析视频数据
                    video_data = self.crawler.parse_video_data(detail)

                    # 用列表数据的分区覆盖（详情API的分区字段为空）
                    if category_from_list and not video_data.get('category'):
                        video_data['category'] = category_from_list

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

                        # 采集弹幕
                        cid = detail.get('cid')
                        if cid and danmakus_per_video > 0:
                            danmaku_count = self._crawl_danmakus(
                                video.id, cid, danmakus_per_video, db
                            )
                            stats['danmakus_saved'] += danmaku_count
                            print(f"  [OK] 弹幕已保存: {danmaku_count} 条")

                    stats['videos_crawled'] += 1
                    log.video_count = stats['videos_saved']
                    log.comment_count = stats['comments_saved']
                    log.danmaku_count = stats['danmakus_saved']
                    db.commit()

                except Exception as e:
                    error_msg = f"{bvid}: {str(e)}"
                    stats['errors'].append(error_msg)
                    print(f"  [FAIL] 错误: {e}")
                    log.video_count = stats['videos_saved']
                    log.comment_count = stats['comments_saved']
                    log.danmaku_count = stats['danmakus_saved']
                    db.commit()

            # 更新日志状态
            log.status = 'success'
            log.video_count = stats['videos_saved']
            log.comment_count = stats['comments_saved']
            log.danmaku_count = stats['danmakus_saved']
            log.finished_at = datetime.utcnow()
            db.commit()

            print(f"\n[采集任务] 完成！视频: {stats['videos_saved']}, 评论: {stats['comments_saved']}, 弹幕: {stats['danmakus_saved']}")
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
                    if saved_count >= max_comments:
                        break
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

                    # 细粒度情绪分析 + 三分类兼容分数
                    emotion_result = self.crawler.emotion.analyze_emotion(content)

                    # 创建评论记录
                    comment = Comment(
                        rpid=rpid,
                        video_id=video_id,
                        content=content,
                        user_name=user_name,
                        sentiment_score=emotion_result.sentiment_score,
                        emotion_label=emotion_result.emotion_label,
                        emotion_scores_json=emotion_result.emotion_scores,
                        emotion_model_version=emotion_result.model_version,
                        emotion_analyzed_at=emotion_result.analyzed_at,
                        like_count=like_count
                    )
                    db.add(comment)
                    saved_count += 1

                    # 每20条提交一次
                    if saved_count % 20 == 0:
                        db.commit()

                if saved_count >= max_comments:
                    break

            # 最后提交剩余的
            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            print(f"    [WARN] 评论采集部分失败: {e}")
            return saved_count

    def _crawl_danmakus(
        self,
        video_id: int,
        cid: int,
        max_danmakus: int,
        db: Session
    ) -> int:
        """
        采集视频弹幕

        Args:
            video_id: 视频数据库ID
            cid: B站视频cid
            max_danmakus: 最多采集弹幕数
            db: 数据库会话

        Returns:
            保存的弹幕数量
        """
        saved_count = 0

        try:
            # 获取弹幕
            danmakus_raw = self.crawler.get_video_danmakus(cid, max_count=max_danmakus)
            if not danmakus_raw:
                return 0

            # 获取该视频已有的弹幕内容（用于去重）
            existing_contents = set(
                d[0] for d in db.query(Danmaku.content)
                .filter(Danmaku.video_id == video_id)
                .all()
            )

            for danmaku_raw in danmakus_raw:
                content = danmaku_raw.get('content', '').strip()
                if not content:
                    continue

                # 简单去重：相同内容跳过
                if content in existing_contents:
                    continue

                # 创建弹幕记录
                danmaku = Danmaku(
                    video_id=video_id,
                    content=content,
                    send_time=danmaku_raw.get('send_time'),
                    color=danmaku_raw.get('color')
                )
                db.add(danmaku)
                existing_contents.add(content)
                saved_count += 1

                # 每50条提交一次
                if saved_count % 50 == 0:
                    db.commit()

            # 最后提交剩余的
            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            print(f"    [WARN] 弹幕采集部分失败: {e}")
            return saved_count

    def crawl_batch_videos(
        self,
        bvids: List[str],
        comments_per_video: int = 100,
        danmakus_per_video: int = 500,
        log_id: int = None
    ) -> Dict:
        """
        批量采集指定视频

        Args:
            bvids: 要采集的BVID列表
            comments_per_video: 每个视频采集评论数
            danmakus_per_video: 每个视频采集弹幕数
            log_id: 已创建的日志ID（可选，用于更新进度）

        Returns:
            采集统计信息
        """
        db = SessionLocal()
        stats = {
            'total': len(bvids),
            'videos_crawled': 0,
            'videos_saved': 0,
            'comments_saved': 0,
            'danmakus_saved': 0,
            'errors': [],
            'details': []  # 每个视频的采集结果
        }

        # 获取或创建日志
        log = None
        if log_id:
            log = db.query(CrawlLog).filter(CrawlLog.id == log_id).first()

        if not log:
            log = CrawlLog(
                task_name=f'批量采集({len(bvids)}个视频)',
                status='running',
                started_at=datetime.utcnow()
            )
            db.add(log)
            db.commit()

        try:
            print(f"\n[批量采集] 开始采集 {len(bvids)} 个指定视频")

            for i, bvid in enumerate(bvids, 1):
                video_result = {
                    'bvid': bvid,
                    'status': 'pending',
                    'title': '',
                    'comments': 0,
                    'danmakus': 0,
                    'error': None
                }

                try:
                    print(f"\n[{i}/{len(bvids)}] 处理视频: {bvid}")

                    # 获取视频详情
                    detail = self.crawler.get_video_detail(bvid)
                    if not detail:
                        video_result['status'] = 'failed'
                        video_result['error'] = '获取详情失败(可能视频不存在或已删除)'
                        stats['errors'].append(f"{bvid}: 获取详情失败")
                        stats['details'].append(video_result)
                        continue

                    video_result['title'] = detail.get('title', '')[:50]

                    # 解析并保存视频
                    video_data = self.crawler.parse_video_data(detail)
                    video = self.crawler.save_video(video_data, db)

                    if video:
                        stats['videos_saved'] += 1
                        print(f"  [OK] 视频已保存: {video.title[:30] if video.title else ''}")

                        # 采集并分析评论
                        oid = detail.get('aid')
                        if oid:
                            comment_count = self._crawl_and_analyze_comments(
                                video.id, oid, comments_per_video, db
                            )
                            stats['comments_saved'] += comment_count
                            video_result['comments'] = comment_count
                            print(f"  [OK] 评论已保存: {comment_count} 条")

                        # 采集弹幕
                        cid = detail.get('cid')
                        if cid and danmakus_per_video > 0:
                            danmaku_count = self._crawl_danmakus(
                                video.id, cid, danmakus_per_video, db
                            )
                            stats['danmakus_saved'] += danmaku_count
                            video_result['danmakus'] = danmaku_count
                            print(f"  [OK] 弹幕已保存: {danmaku_count} 条")

                        video_result['status'] = 'success'
                    else:
                        video_result['status'] = 'updated'  # 视频已存在，已更新

                    stats['videos_crawled'] += 1

                    # 实时更新日志
                    log.video_count = stats['videos_saved']
                    log.comment_count = stats['comments_saved']
                    log.danmaku_count = stats['danmakus_saved']
                    db.commit()

                except Exception as e:
                    video_result['status'] = 'failed'
                    video_result['error'] = str(e)
                    stats['errors'].append(f"{bvid}: {str(e)}")
                    print(f"  [FAIL] 错误: {e}")

                stats['details'].append(video_result)

            # 更新日志状态
            log.status = 'success'
            log.video_count = stats['videos_saved']
            log.comment_count = stats['comments_saved']
            log.danmaku_count = stats['danmakus_saved']
            log.finished_at = datetime.utcnow()

            if stats['errors']:
                # 部分失败时记录错误信息
                log.error_msg = f"部分失败({len(stats['errors'])}个): " + '; '.join(stats['errors'][:5])

            db.commit()

            print(f"\n[批量采集] 完成！成功: {stats['videos_saved']}/{stats['total']}, "
                  f"评论: {stats['comments_saved']}, 弹幕: {stats['danmakus_saved']}")
            return stats

        except Exception as e:
            log.status = 'failed'
            log.error_msg = str(e)
            log.finished_at = datetime.utcnow()
            db.commit()

            stats['errors'].append(f"全局错误: {str(e)}")
            print(f"[批量采集] 失败: {e}")
            return stats

        finally:
            db.close()
