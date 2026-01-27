"""
Redis 客户端模块

提供：
- 直播统计数据读写
- 与 Spark Streaming 结果交互
"""

import json
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Redis 配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# 标记 Redis 是否可用
_redis_available = False
_client = None

try:
    import redis
    _redis_available = True
except ImportError:
    logger.warning("redis 库未安装，Redis 功能禁用")


def get_redis_client():
    """获取 Redis 客户端单例"""
    global _client

    if not _redis_available:
        return None

    if _client is None:
        try:
            _client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
            )
            # 测试连接
            _client.ping()
            logger.info(f"Redis 已连接: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            return None

    return _client


def get_room_stats(room_id: int) -> Optional[Dict[str, Any]]:
    """
    获取直播间统计数据（由 Spark Streaming 写入）

    Returns:
        {
            "total_danmaku": 100,
            "positive_count": 40,
            "neutral_count": 35,
            "negative_count": 25,
            "avg_sentiment": 0.65,
            "window_start": "2024-01-01T12:00:00",
            "window_end": "2024-01-01T12:00:05",
            "updated_at": "2024-01-01T12:00:05"
        }
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        key = f"live:stats:{room_id}"
        data = client.hgetall(key)
        if not data:
            return None

        # 转换数值类型
        return {
            "total_danmaku": int(data.get("total_danmaku", 0)),
            "positive_count": int(data.get("positive_count", 0)),
            "neutral_count": int(data.get("neutral_count", 0)),
            "negative_count": int(data.get("negative_count", 0)),
            "avg_sentiment": float(data.get("avg_sentiment", 0.5)),
            "window_start": data.get("window_start", ""),
            "window_end": data.get("window_end", ""),
            "updated_at": data.get("updated_at", ""),
        }
    except Exception as e:
        logger.error(f"获取房间统计失败: {e}")
        return None


def get_room_stats_history(room_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    获取直播间历史统计数据（趋势图用）

    Returns:
        [{"total_danmaku": 10, "avg_sentiment": 0.65, ...}, ...]
    """
    client = get_redis_client()
    if client is None:
        return []

    try:
        key = f"live:stats:{room_id}:history"
        data = client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in data]
    except Exception as e:
        logger.error(f"获取历史统计失败: {e}")
        return []


def get_all_room_stats() -> Dict[int, Dict[str, Any]]:
    """
    获取所有活跃房间的统计数据（用于房间对比）

    Returns:
        {
            room_id1: {...stats...},
            room_id2: {...stats...},
        }
    """
    client = get_redis_client()
    if client is None:
        return {}

    try:
        # 查找所有 live:stats:* 的 key
        keys = client.keys("live:stats:*")
        result = {}

        for key in keys:
            # 跳过 history 键
            if ":history" in key:
                continue

            # 提取 room_id
            parts = key.split(":")
            if len(parts) == 3:
                room_id = int(parts[2])
                stats = get_room_stats(room_id)
                if stats:
                    result[room_id] = stats

        return result
    except Exception as e:
        logger.error(f"获取所有房间统计失败: {e}")
        return {}


def get_global_wordcloud() -> List[Dict[str, Any]]:
    """
    获取全局热词（跨房间聚合，由 Spark 写入）

    Returns:
        [{"name": "主播", "value": 100}, ...]
    """
    client = get_redis_client()
    if client is None:
        return []

    try:
        key = "live:global:wordcloud"
        data = client.get(key)
        if data:
            return json.loads(data)
        return []
    except Exception as e:
        logger.error(f"获取全局词云失败: {e}")
        return []


def set_room_stats(room_id: int, stats: Dict[str, Any], expire: int = 3600):
    """
    设置直播间统计数据（供本地模式使用）
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        key = f"live:stats:{room_id}"
        client.hset(key, mapping={k: str(v) for k, v in stats.items()})
        client.expire(key, expire)
        return True
    except Exception as e:
        logger.error(f"设置房间统计失败: {e}")
        return False


def is_redis_available() -> bool:
    """检查 Redis 是否可用"""
    return _redis_available and get_redis_client() is not None


def close_redis_client():
    """关闭 Redis 客户端"""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("Redis 客户端已关闭")
