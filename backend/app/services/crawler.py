"""
B站数据采集服务
"""
import time
import random
import requests
from typing import List, Dict, Optional
from functools import wraps
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import Video, Comment
from app.core.database import SessionLocal


class BilibiliCrawler:
    """B站数据采集器"""

    BASE_URL = "https://api.bilibili.com"

    def __init__(self, cookie: str = ""):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        }
        if cookie:
            self.session.headers['Cookie'] = cookie

    @staticmethod
    def rate_limit(interval: float = 2.0):
        """频率限制装饰器"""
        def decorator(func):
            last_call = [0]

            @wraps(func)
            def wrapper(*args, **kwargs):
                elapsed = time.time() - last_call[0]
                if elapsed < interval:
                    sleep_time = interval - elapsed + random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
                result = func(*args, **kwargs)
                last_call[0] = time.time()
                return result
            return wrapper
        return decorator

    @rate_limit(interval=2.0)
    def get_popular_videos(self, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """获取热门视频列表"""
        url = f"{self.BASE_URL}/x/web-interface/popular"
        params = {'ps': page_size, 'pn': page}

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == 0:
                return data['data']['list']
            return None
        except Exception as e:
            print(f"获取热门视频失败: {e}")
            return None

    @rate_limit(interval=2.0)
    def get_video_detail(self, bvid: str) -> Optional[Dict]:
        """获取视频详情"""
        url = f"{self.BASE_URL}/x/web-interface/view"
        params = {'bvid': bvid}

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == 0:
                return data['data']
            return None
        except Exception as e:
            print(f"获取视频详情失败: {e}")
            return None

    @rate_limit(interval=2.0)
    def get_video_comments(self, oid: int, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """获取视频评论"""
        url = f"{self.BASE_URL}/x/v2/reply"
        params = {
            'type': 1,
            'oid': oid,
            'pn': page,
            'ps': page_size,
            'sort': 2  # 按热度排序
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == 0 and data['data']['replies']:
                return data['data']['replies']
            return None
        except Exception as e:
            print(f"获取评论失败: {e}")
            return None

    @rate_limit(interval=2.0)
    def get_ranking(self, rid: int = 0) -> Optional[List[Dict]]:
        """获取排行榜
        rid: 分区ID，0为全站
        """
        url = f"{self.BASE_URL}/x/web-interface/ranking/v2"
        params = {'rid': rid, 'type': 'all'}

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == 0:
                return data['data']['list']
            return None
        except Exception as e:
            print(f"获取排行榜失败: {e}")
            return None

    def parse_video_data(self, raw_data: Dict) -> Dict:
        """解析视频数据为统一格式"""
        stat = raw_data.get('stat', {})
        owner = raw_data.get('owner', {})

        return {
            'bvid': raw_data.get('bvid'),
            'title': raw_data.get('title'),
            'description': raw_data.get('desc', ''),
            'category': raw_data.get('tname', ''),
            'author_id': owner.get('mid'),
            'author_name': owner.get('name'),
            'play_count': stat.get('view', 0),
            'like_count': stat.get('like', 0),
            'coin_count': stat.get('coin', 0),
            'share_count': stat.get('share', 0),
            'favorite_count': stat.get('favorite', 0),
            'danmaku_count': stat.get('danmaku', 0),
            'comment_count': stat.get('reply', 0),
            'publish_time': raw_data.get('pubdate'),
            'duration': raw_data.get('duration'),
            'cover_url': raw_data.get('pic')
        }

    def save_video(self, video_data: Dict, db: Session) -> Optional[Video]:
        """保存视频数据到数据库"""
        try:
            # 检查视频是否已存在
            existing = db.query(Video).filter(Video.bvid == video_data['bvid']).first()
            if existing:
                # 更新统计数据
                existing.play_count = video_data['play_count']
                existing.like_count = video_data['like_count']
                existing.coin_count = video_data['coin_count']
                existing.share_count = video_data['share_count']
                existing.favorite_count = video_data['favorite_count']
                existing.danmaku_count = video_data['danmaku_count']
                existing.comment_count = video_data['comment_count']
                db.commit()
                db.refresh(existing)
                return existing

            # 转换时间戳为 datetime
            publish_time = None
            if video_data.get('publish_time'):
                publish_time = datetime.fromtimestamp(video_data['publish_time'])

            # 创建新视频记录
            video = Video(
                bvid=video_data['bvid'],
                title=video_data['title'],
                description=video_data.get('description', ''),
                category=video_data.get('category'),
                author_id=video_data.get('author_id'),
                author_name=video_data.get('author_name'),
                play_count=video_data.get('play_count', 0),
                like_count=video_data.get('like_count', 0),
                coin_count=video_data.get('coin_count', 0),
                share_count=video_data.get('share_count', 0),
                favorite_count=video_data.get('favorite_count', 0),
                danmaku_count=video_data.get('danmaku_count', 0),
                comment_count=video_data.get('comment_count', 0),
                publish_time=publish_time,
                duration=video_data.get('duration'),
                cover_url=video_data.get('cover_url')
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            return video

        except IntegrityError:
            db.rollback()
            print(f"视频 {video_data['bvid']} 已存在")
            return None
        except Exception as e:
            db.rollback()
            print(f"保存视频失败: {e}")
            return None

    def save_comments(self, comments_data: List[Dict], video_id: int, db: Session) -> int:
        """保存评论数据到数据库"""
        saved_count = 0
        try:
            for comment_raw in comments_data:
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

                # 创建评论记录（暂不做情感分析）
                comment = Comment(
                    rpid=rpid,
                    video_id=video_id,
                    content=content,
                    user_name=user_name,
                    like_count=like_count
                )
                db.add(comment)
                saved_count += 1

            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            print(f"保存评论失败: {e}")
            return saved_count

    def crawl_once(self, max_videos: int = 10, comments_per_video: int = 100) -> Dict:
        """单次采集流程

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

        try:
            print(f"\n开始采集，目标: {max_videos} 个视频")

            # 获取热门视频列表
            videos = self.get_popular_videos(page=1, page_size=max_videos)
            if not videos:
                print("获取热门视频失败")
                return stats

            print(f"获取到 {len(videos)} 个热门视频")

            # 遍历每个视频
            for i, video_raw in enumerate(videos[:max_videos], 1):
                try:
                    bvid = video_raw.get('bvid')
                    print(f"\n[{i}/{max_videos}] 处理视频: {bvid}")

                    # 获取视频详情
                    detail = self.get_video_detail(bvid)
                    if not detail:
                        stats['errors'].append(f"{bvid}: 获取详情失败")
                        continue

                    # 解析并保存视频数据
                    video_data = self.parse_video_data(detail)
                    video = self.save_video(video_data, db)

                    if video:
                        stats['videos_saved'] += 1
                        print(f"  [OK] 视频已保存: {video.title[:30]}")

                        # 获取并保存评论
                        oid = detail.get('aid')
                        if oid:
                            # 分批获取评论
                            page_size = 20
                            total_pages = (comments_per_video + page_size - 1) // page_size

                            for page in range(1, total_pages + 1):
                                comments = self.get_video_comments(oid, page=page, page_size=page_size)
                                if comments:
                                    count = self.save_comments(comments, video.id, db)
                                    stats['comments_saved'] += count

                            print(f"  [OK] 评论已保存: {stats['comments_saved']} 条")

                    stats['videos_crawled'] += 1

                except Exception as e:
                    error_msg = f"{bvid}: {str(e)}"
                    stats['errors'].append(error_msg)
                    print(f"  [FAIL] 错误: {e}")

            print(f"\n采集完成！")
            print(f"  视频: {stats['videos_saved']}/{stats['videos_crawled']}")
            print(f"  评论: {stats['comments_saved']}")

            return stats

        except Exception as e:
            print(f"采集过程出错: {e}")
            stats['errors'].append(f"全局错误: {str(e)}")
            return stats
        finally:
            db.close()
