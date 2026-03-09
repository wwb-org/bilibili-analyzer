"""
B站数据采集服务
"""
import time
import random
import requests
from typing import Any, List, Dict, Optional
from functools import wraps
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import Video, Comment
from app.core.database import SessionLocal
from app.services.emotion import EmotionAnalyzer


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class BilibiliCrawler:
    """B站数据采集器"""

    BASE_URL = "https://api.bilibili.com"

    def __init__(self, cookie: str = ""):
        self.session = requests.Session()
        self.emotion = EmotionAnalyzer()
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
    def get_video_comments_main(
        self,
        oid: int,
        next_cursor: int = 0,
        page_size: int = 20,
        mode: int = 3
    ) -> Optional[Dict]:
        """获取视频评论（新版主评论接口）"""
        url = f"{self.BASE_URL}/x/v2/reply/main"
        params = {
            "type": 1,
            "oid": oid,
            "mode": mode,
            "next": next_cursor,
            "ps": page_size,
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data") or {}
            return None
        except Exception as e:
            print(f"获取评论(main)失败: {e}")
            return None

    @staticmethod
    def parse_comment_user_profile(comment_raw: Dict) -> Dict:
        """从评论原始数据提取用户画像字段"""
        member = comment_raw.get("member") or {}
        level_info = member.get("level_info") or {}
        vip_info = member.get("vip") or {}
        official = member.get("official_verify") or {}
        up_action = comment_raw.get("up_action") or {}
        raw_sex = (member.get("sex") or "").strip()
        if raw_sex not in {"男", "女"}:
            raw_sex = "未知"

        ctime = _to_int(comment_raw.get("ctime"), 0)
        comment_ctime = datetime.fromtimestamp(ctime) if ctime > 0 else None

        return {
            "commenter_mid": _to_int(member.get("mid"), 0) or None,
            "commenter_level": _to_int(level_info.get("current_level"), 0) or None,
            "commenter_sex": raw_sex,
            "commenter_vip_type": _to_int(vip_info.get("vipType"), 0),
            "commenter_is_official": _to_int(official.get("type"), -1) >= 0,
            "reply_count": _to_int(comment_raw.get("rcount"), 0),
            "up_replied": bool(up_action.get("reply")),
            "comment_ctime": comment_ctime,
        }

    @rate_limit(interval=2.0)
    def get_video_danmakus(self, cid: int, max_count: int = 500) -> Optional[List[Dict]]:
        """获取视频弹幕

        Args:
            cid: 视频的cid（从视频详情中获取）
            max_count: 最多返回的弹幕数量

        Returns:
            弹幕列表，每条包含 content, send_time, color
        """
        # B站弹幕API（XML格式）
        url = f"https://comment.bilibili.com/{cid}.xml"

        try:
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'utf-8'

            if resp.status_code != 200:
                print(f"获取弹幕失败: HTTP {resp.status_code}")
                return None

            # 解析XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)

            danmakus = []
            for d in root.findall('d'):
                try:
                    # 弹幕属性格式: 时间,模式,字号,颜色,时间戳,弹幕池,用户hash,弹幕ID
                    attrs = d.get('p', '').split(',')
                    if len(attrs) >= 4:
                        send_time = float(attrs[0])  # 视频内时间点（秒）
                        color = int(attrs[3])  # 颜色（十进制）
                        content = d.text or ''

                        if content.strip():
                            danmakus.append({
                                'content': content,
                                'send_time': send_time,
                                'color': f'#{color:06x}'  # 转为十六进制颜色
                            })
                except (ValueError, IndexError):
                    continue

                if len(danmakus) >= max_count:
                    break

            return danmakus

        except Exception as e:
            print(f"获取弹幕失败: {e}")
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

        # 分区字段优先级：tname > tnamev2 > tname_v2
        # 热门列表API使用 tname/tnamev2，详情API的这些字段可能为空
        category = (raw_data.get('tname', '') or
                    raw_data.get('tnamev2', '') or
                    raw_data.get('tname_v2', ''))

        return {
            'bvid': raw_data.get('bvid'),
            'title': raw_data.get('title'),
            'description': raw_data.get('desc', ''),
            'category': category,
            'author_id': owner.get('mid'),
            'author_name': owner.get('name'),
            'author_face': owner.get('face', ''),
            'play_count': stat.get('view', 0),
            'like_count': stat.get('like', 0),
            'coin_count': stat.get('coin', 0),
            'share_count': stat.get('share', 0),
            'favorite_count': stat.get('favorite', 0),
            'danmaku_count': stat.get('danmaku', 0),
            'comment_count': stat.get('reply', 0),
            'publish_time': raw_data.get('pubdate'),
            'duration': raw_data.get('duration'),
            'cover_url': raw_data.get('pic'),
            'cid': raw_data.get('cid'),  # 用于获取弹幕
            'aid': raw_data.get('aid'),  # 用于获取评论
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

                # 细粒度情绪分析 + 三分类兼容分数
                emotion_result = self.emotion.analyze_emotion(content)
                profile = self.parse_comment_user_profile(comment_raw)

                # 创建评论记录
                comment = Comment(
                    rpid=rpid,
                    video_id=video_id,
                    content=content,
                    user_name=user_name,
                    commenter_mid=profile["commenter_mid"],
                    commenter_level=profile["commenter_level"],
                    commenter_sex=profile["commenter_sex"],
                    commenter_vip_type=profile["commenter_vip_type"],
                    commenter_is_official=profile["commenter_is_official"],
                    sentiment_score=emotion_result.sentiment_score,
                    emotion_label=emotion_result.emotion_label,
                    emotion_scores_json=emotion_result.emotion_scores,
                    emotion_model_version=emotion_result.model_version,
                    emotion_analyzed_at=emotion_result.analyzed_at,
                    like_count=like_count,
                    reply_count=profile["reply_count"],
                    up_replied=profile["up_replied"],
                    comment_ctime=profile["comment_ctime"],
                )
                db.add(comment)
                saved_count += 1

            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            print(f"保存评论失败: {e}")
            return saved_count

    @rate_limit(interval=2.0)
    def get_weekly_series_list(self) -> Optional[List[Dict]]:
        """获取每周必看期数列表"""
        url = f"{self.BASE_URL}/x/web-interface/popular/series/list"
        try:
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            if data['code'] == 0:
                return data['data']['list']
            return None
        except Exception as e:
            print(f"获取每周必看列表失败: {e}")
            return None

    @rate_limit(interval=2.0)
    def get_weekly_series_one(self, number: int) -> Optional[List[Dict]]:
        """获取指定期数的每周必看视频列表"""
        url = f"{self.BASE_URL}/x/web-interface/popular/series/one"
        params = {'number': number}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == 0:
                return data['data']['list']
            return None
        except Exception as e:
            print(f"获取第{number}期每周必看失败: {e}")
            return None

    def crawl_weekly_series(
        self,
        max_episodes: int = 10,
        comments_per_video: int = 20,
        start_episode: int = None,
    ) -> Dict:
        """采集每周必看历史数据

        Args:
            max_episodes: 最多采集期数（从最新期往前，None表示全部）
            comments_per_video: 每视频采集评论数（历史数据建议设小一点）
            start_episode: 从哪期开始（默认最新期）

        Returns:
            采集统计
        """
        db = SessionLocal()
        stats = {
            'episodes_done': 0,
            'videos_saved': 0,
            'videos_skipped': 0,
            'comments_saved': 0,
            'errors': [],
        }

        try:
            # 获取期数列表
            print("正在获取每周必看期数列表...")
            series_list = self.get_weekly_series_list()
            if not series_list:
                print("获取期数列表失败")
                return stats

            # 按期数降序（最新在前）
            series_list = sorted(series_list, key=lambda x: x.get('number', 0), reverse=True)
            total = len(series_list)
            print(f"共发现 {total} 期每周必看")

            # 确定起始期
            if start_episode is not None:
                series_list = [s for s in series_list if s.get('number', 0) <= start_episode]

            # 限制期数
            if max_episodes:
                series_list = series_list[:max_episodes]

            for ep_idx, episode in enumerate(series_list):
                number = episode.get('number')
                subject = episode.get('subject', f'第{number}期')
                print(f"\n[{ep_idx+1}/{len(series_list)}] 采集第{number}期: {subject}")

                videos = self.get_weekly_series_one(number)
                if not videos:
                    print(f"  第{number}期无数据，跳过")
                    stats['errors'].append(f"第{number}期: 获取视频列表失败")
                    continue

                print(f"  本期 {len(videos)} 个视频")

                for v_idx, video_raw in enumerate(videos, 1):
                    bvid = video_raw.get('bvid')
                    try:
                        # 已有视频只更新数据，不重复采集评论
                        existing = db.query(Video).filter(Video.bvid == bvid).first()
                        if existing:
                            video_data = self.parse_video_data(video_raw)
                            existing.play_count = video_data['play_count']
                            existing.like_count = video_data['like_count']
                            existing.coin_count = video_data['coin_count']
                            existing.danmaku_count = video_data['danmaku_count']
                            existing.comment_count = video_data['comment_count']
                            db.commit()
                            stats['videos_skipped'] += 1
                            print(f"  [{v_idx}/{len(videos)}] {bvid} 已存在，更新数据")
                            continue

                        # 获取详情（包含 aid/cid）
                        detail = self.get_video_detail(bvid)
                        if not detail:
                            stats['errors'].append(f"{bvid}: 获取详情失败")
                            continue

                        video_data = self.parse_video_data(detail)
                        video = self.save_video(video_data, db)

                        if video:
                            stats['videos_saved'] += 1
                            print(f"  [{v_idx}/{len(videos)}] {bvid} 保存成功: {video.title[:25]}")

                            # 采集评论（历史数据少采一些）
                            if comments_per_video > 0:
                                oid = detail.get('aid')
                                if oid:
                                    page_size = 20
                                    pages = max(1, comments_per_video // page_size)
                                    for page in range(1, pages + 1):
                                        cmts = self.get_video_comments(oid, page=page, page_size=page_size)
                                        if cmts:
                                            cnt = self.save_comments(cmts, video.id, db)
                                            stats['comments_saved'] += cnt

                    except Exception as e:
                        stats['errors'].append(f"{bvid}: {e}")
                        print(f"  [{v_idx}] {bvid} 处理失败: {e}")

                stats['episodes_done'] += 1
                print(f"  第{number}期完成，累计入库: {stats['videos_saved']} 视频 / {stats['comments_saved']} 评论")

        except Exception as e:
            print(f"全局错误: {e}")
            stats['errors'].append(f"全局错误: {e}")
        finally:
            db.close()

        print(f"\n====== 每周必看采集完成 ======")
        print(f"期数: {stats['episodes_done']} 期")
        print(f"新增视频: {stats['videos_saved']}")
        print(f"已有跳过: {stats['videos_skipped']}")
        print(f"评论: {stats['comments_saved']}")
        if stats['errors']:
            print(f"错误数: {len(stats['errors'])}")
        return stats

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
