"""
Redis 客户端工具
用于存储直播弹幕实时数据
"""
import redis
import json
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""

    def __init__(self, url: str = None):
        """
        初始化 Redis 客户端

        Args:
            url: Redis 连接 URL
        """
        self.url = url or settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """连接到 Redis"""
        try:
            self.client = redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.client.ping()
            logger.info(f"Redis 客户端已连接: {self.url}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            self.client = None

    def set_live_danmaku_stats(self, room_id: int, stats: Dict[str, Any], expire: int = 3600):
        """
        存储直播间弹幕统计数据

        Args:
            room_id: 直播间ID
            stats: 统计数据
            expire: 过期时间（秒），默认1小时
        """
        if not self.client:
            return False

        try:
            key = f"live:stats:{room_id}"
            self.client.setex(key, expire, json.dumps(stats, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"存储直播统计失败: {e}")
            return False

    def get_live_danmaku_stats(self, room_id: int) -> Optional[Dict[str, Any]]:
        """
        获取直播间弹幕统计数据

        Args:
            room_id: 直播间ID

        Returns:
            统计数据字典，不存在返回 None
        """
        if not self.client:
            return None

        try:
            key = f"live:stats:{room_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取直播统计失败: {e}")
            return None

    def add_live_danmaku(self, room_id: int, danmaku: Dict[str, Any], max_count: int = 1000):
        """
        添加直播弹幕到列表（保留最新的N条）

        Args:
            room_id: 直播间ID
            danmaku: 弹幕数据
            max_count: 最大保留数量
        """
        if not self.client:
            return False

        try:
            key = f"live:danmaku:{room_id}"
            # 添加到列表头部
            self.client.lpush(key, json.dumps(danmaku, ensure_ascii=False))
            # 保留最新的 max_count 条
            self.client.ltrim(key, 0, max_count - 1)
            # 设置过期时间（1小时）
            self.client.expire(key, 3600)
            return True
        except Exception as e:
            logger.error(f"添加直播弹幕失败: {e}")
            return False

    def get_live_danmaku_list(self, room_id: int, start: int = 0, end: int = 99) -> List[Dict[str, Any]]:
        """
        获取直播间弹幕列表

        Args:
            room_id: 直播间ID
            start: 起始索引
            end: 结束索引

        Returns:
            弹幕列表
        """
        if not self.client:
            return []

        try:
            key = f"live:danmaku:{room_id}"
            data_list = self.client.lrange(key, start, end)
            return [json.loads(data) for data in data_list]
        except Exception as e:
            logger.error(f"获取直播弹幕列表失败: {e}")
            return []

    def set_live_wordcloud(self, room_id: int, wordcloud: List[Dict[str, Any]], expire: int = 600):
        """
        存储直播间词云数据

        Args:
            room_id: 直播间ID
            wordcloud: 词云数据
            expire: 过期时间（秒），默认10分钟
        """
        if not self.client:
            return False

        try:
            key = f"live:wordcloud:{room_id}"
            self.client.setex(key, expire, json.dumps(wordcloud, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"存储词云数据失败: {e}")
            return False

    def get_live_wordcloud(self, room_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        获取直播间词云数据

        Args:
            room_id: 直播间ID

        Returns:
            词云数据列表
        """
        if not self.client:
            return None

        try:
            key = f"live:wordcloud:{room_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取词云数据失败: {e}")
            return None

    def close(self):
        """关闭 Redis 连接"""
        if self.client:
            self.client.close()
            logger.info("Redis 客户端已关闭")


# 全局 Redis 客户端实例（单例模式）
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    获取 Redis 客户端实例（单例）

    Returns:
        Redis 客户端实例
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
