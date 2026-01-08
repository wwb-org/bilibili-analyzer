"""
B站数据采集服务
"""
import time
import random
import requests
from typing import List, Dict, Optional
from functools import wraps


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
