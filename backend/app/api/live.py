"""
直播弹幕分析 API

提供：
- WebSocket 端点：实时接收直播弹幕
- HTTP 端点：获取直播间信息、多房间统计
- NLP 分析：弹幕情感分析、词云生成
- Kafka 集成：弹幕数据发送到 Kafka 供 Spark 处理
"""
import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Dict, Set, Optional, List, Deque
from dataclasses import dataclass, field
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from app.services.live_client import (
    BiliLiveClient,
    DanmakuMessage,
    GiftMessage,
    InteractMessage,
)
from app.services.nlp import NLPAnalyzer
from app.services.kafka_service import (
    send_danmaku_to_kafka,
    send_gift_to_kafka,
    is_kafka_available,
)
from app.services.redis_service import (
    get_room_stats,
    get_room_stats_history,
    get_all_room_stats,
    get_global_wordcloud,
    is_redis_available,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@dataclass
class LiveRoomStats:
    """直播间实时统计"""
    start_time: datetime = field(default_factory=datetime.now)
    total_danmaku: int = 0
    total_gift: int = 0
    sentiment_sum: float = 0.0
    sentiment_dist: Dict[str, int] = field(default_factory=lambda: {
        "positive": 0, "neutral": 0, "negative": 0
    })
    recent_danmakus: Deque[str] = field(default_factory=lambda: deque(maxlen=500))

    @property
    def avg_sentiment(self) -> float:
        """平均情感分"""
        if self.total_danmaku == 0:
            return 0.5
        return self.sentiment_sum / self.total_danmaku

    @property
    def danmaku_rate(self) -> float:
        """弹幕速率（条/分钟）"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        if elapsed <= 0:
            return 0
        return self.total_danmaku / elapsed

    def add_danmaku(self, content: str, sentiment_score: float, sentiment_label: str):
        """记录一条弹幕"""
        self.total_danmaku += 1
        self.sentiment_sum += sentiment_score
        self.sentiment_dist[sentiment_label] += 1
        self.recent_danmakus.append(content)

    def add_gift(self):
        """记录一个礼物"""
        self.total_gift += 1

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_danmaku": self.total_danmaku,
            "total_gift": self.total_gift,
            "danmaku_rate": round(self.danmaku_rate, 1),
            "avg_sentiment": round(self.avg_sentiment, 3),
            "sentiment_dist": self.sentiment_dist.copy(),
        }


class LiveConnectionManager:
    """
    直播间连接管理器

    管理多个用户连接到同一直播间的场景：
    - 复用 B 站连接（同一直播间只建立一个连接）
    - 广播消息给所有观看该直播间的用户
    - NLP 情感分析和词云生成
    """

    def __init__(self):
        # room_id -> Set[WebSocket] 前端连接
        self._connections: Dict[int, Set[WebSocket]] = {}
        # room_id -> BiliLiveClient B站连接
        self._clients: Dict[int, BiliLiveClient] = {}
        # room_id -> asyncio.Task 连接任务
        self._tasks: Dict[int, asyncio.Task] = {}
        # room_id -> LiveRoomStats 统计数据
        self._stats: Dict[int, LiveRoomStats] = {}
        # room_id -> asyncio.Task 统计广播任务
        self._stats_tasks: Dict[int, asyncio.Task] = {}
        # NLP 分析器
        self._nlp = NLPAnalyzer()
        # 统计/词云广播节流（避免高频阻塞）
        self._last_stats_broadcast: Dict[int, datetime] = {}
        self._last_wordcloud_broadcast: Dict[int, datetime] = {}
        self._stats_push_interval = 1.0  # 秒：尽量接近实时
        self._wordcloud_interval = 3.0  # 秒：词云较重，适度刷新

    async def connect(self, room_id: int, websocket: WebSocket):
        """用户连接到直播间"""
        await websocket.accept()

        if room_id not in self._connections:
            self._connections[room_id] = set()

        self._connections[room_id].add(websocket)

        # 如果是第一个用户，创建 B 站连接和统计
        if room_id not in self._clients:
            self._stats[room_id] = LiveRoomStats()
            self._last_stats_broadcast[room_id] = datetime.min
            self._last_wordcloud_broadcast[room_id] = datetime.min
            await self._create_bili_client(room_id)
            # 启动定时广播任务
            self._stats_tasks[room_id] = asyncio.create_task(
                self._periodic_broadcast(room_id)
            )

        # 发送连接成功消息和当前统计
        await websocket.send_json({
            "type": "status",
            "data": {
                "status": "connected",
                "room_id": room_id,
                "message": "连接成功"
            }
        })
        # 发送当前统计数据
        if room_id in self._stats:
            await websocket.send_json({
                "type": "stats",
                "data": self._stats[room_id].to_dict()
            })

    async def disconnect(self, room_id: int, websocket: WebSocket):
        """用户断开连接"""
        if room_id in self._connections:
            self._connections[room_id].discard(websocket)

            # 如果没有用户了，关闭 B 站连接和统计任务
            if not self._connections[room_id]:
                await self._close_bili_client(room_id)
                del self._connections[room_id]
                # 清理统计任务
                if room_id in self._stats_tasks:
                    self._stats_tasks[room_id].cancel()
                    del self._stats_tasks[room_id]
                if room_id in self._stats:
                    del self._stats[room_id]
                if room_id in self._last_stats_broadcast:
                    del self._last_stats_broadcast[room_id]
                if room_id in self._last_wordcloud_broadcast:
                    del self._last_wordcloud_broadcast[room_id]

    async def _create_bili_client(self, room_id: int):
        """创建 B 站直播连接"""
        client = BiliLiveClient(room_id, client="aiohttp", proxy="http://127.0.0.1:7897")

        # 注册回调
        client.on_danmaku(lambda msg: asyncio.create_task(
            self._broadcast_danmaku(room_id, msg)
        ))
        client.on_gift(lambda msg: asyncio.create_task(
            self._broadcast_gift(room_id, msg)
        ))
        client.on_interact(lambda msg: asyncio.create_task(
            self._broadcast_interact(room_id, msg)
        ))

        self._clients[room_id] = client

        # 在后台启动连接
        self._tasks[room_id] = asyncio.create_task(client.connect())

    async def _close_bili_client(self, room_id: int):
        """关闭 B 站直播连接"""
        if room_id in self._tasks:
            self._tasks[room_id].cancel()
            del self._tasks[room_id]

        if room_id in self._clients:
            await self._clients[room_id].disconnect()
            del self._clients[room_id]

    async def _broadcast_danmaku(self, room_id: int, msg: DanmakuMessage):
        """广播弹幕消息（带情感分析）"""
        # 情感分析
        # SnowNLP/分词为同步CPU密集型，放到线程池避免阻塞事件循环
        sentiment_score = await asyncio.to_thread(self._nlp.analyze_sentiment, msg.content)
        if sentiment_score >= 0.6:
            sentiment_label = "positive"
        elif sentiment_score <= 0.4:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # 更新统计
        if room_id in self._stats:
            self._stats[room_id].add_danmaku(msg.content, sentiment_score, sentiment_label)
            # 高频弹幕下按时间节流推送统计，接近实时
            now = datetime.now()
            last = self._last_stats_broadcast.get(room_id, datetime.min)
            if (now - last).total_seconds() >= self._stats_push_interval:
                self._last_stats_broadcast[room_id] = now
                await self._broadcast(room_id, {
                    "type": "stats",
                    "data": self._stats[room_id].to_dict()
                })

        # 发送到 Kafka（供 Spark Streaming 处理）
        send_danmaku_to_kafka(
            room_id=room_id,
            content=msg.content,
            user_name=msg.user_name,
            user_id=msg.user_id,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            timestamp=msg.timestamp,
        )

        message = {
            "type": "danmaku",
            "data": {
                "room_id": room_id,
                "content": msg.content,
                "user_name": msg.user_name,
                "user_id": msg.user_id,
                "timestamp": msg.timestamp.isoformat(),
                "sentiment_score": round(sentiment_score, 3),
                "sentiment_label": sentiment_label,
            }
        }
        await self._broadcast(room_id, message)

    async def _broadcast_gift(self, room_id: int, msg: GiftMessage):
        """广播礼物消息"""
        # 更新统计
        if room_id in self._stats:
            self._stats[room_id].add_gift()

        # 发送到 Kafka
        send_gift_to_kafka(
            room_id=room_id,
            gift_name=msg.gift_name,
            gift_count=msg.gift_count,
            user_name=msg.user_name,
            user_id=msg.user_id,
            price=msg.price,
            timestamp=msg.timestamp,
        )

        message = {
            "type": "gift",
            "data": {
                "room_id": room_id,
                "gift_name": msg.gift_name,
                "gift_count": msg.gift_count,
                "user_name": msg.user_name,
                "user_id": msg.user_id,
                "price": msg.price,
                "timestamp": msg.timestamp.isoformat(),
            }
        }
        await self._broadcast(room_id, message)

    async def _broadcast_interact(self, room_id: int, msg: InteractMessage):
        """广播互动消息"""
        message = {
            "type": "interact",
            "data": {
                "action": msg.action,
                "user_name": msg.user_name,
                "user_id": msg.user_id,
                "timestamp": msg.timestamp.isoformat(),
            }
        }
        await self._broadcast(room_id, message)

    async def _broadcast(self, room_id: int, message: dict):
        """广播消息给房间内所有连接"""
        if room_id not in self._connections:
            return

        disconnected = set()
        for websocket in self._connections[room_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)

        # 移除断开的连接
        for websocket in disconnected:
            self._connections[room_id].discard(websocket)

    def get_room_count(self, room_id: int) -> int:
        """获取房间在线人数"""
        return len(self._connections.get(room_id, set()))

    def get_active_rooms(self) -> list:
        """获取活跃的直播间列表"""
        return list(self._connections.keys())

    async def _periodic_broadcast(self, room_id: int):
        """定时广播统计数据和词云"""
        stats_interval = 1  # 统计广播间隔（秒）

        while True:
            try:
                await asyncio.sleep(stats_interval)

                if room_id not in self._stats:
                    break

                # 广播统计数据
                stats = self._stats[room_id]
                await self._broadcast(room_id, {
                    "type": "stats",
                    "data": stats.to_dict()
                })

                # 词云广播（节流）
                now = datetime.now()
                last_wc = self._last_wordcloud_broadcast.get(room_id, datetime.min)
                if (now - last_wc).total_seconds() >= self._wordcloud_interval:
                    self._last_wordcloud_broadcast[room_id] = now
                    if stats.recent_danmakus:
                        # 词云生成较重，放到线程池避免阻塞事件循环
                        wordcloud_data = await asyncio.to_thread(
                            self._nlp.get_word_cloud_data,
                            list(stats.recent_danmakus),
                            top_k=50,
                        )
                        await self._broadcast(room_id, {
                            "type": "wordcloud",
                            "data": wordcloud_data
                        })

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[LiveAPI] 定时广播异常: {e}")


# 全局连接管理器
manager = LiveConnectionManager()


@router.websocket("/ws/{room_id}")
async def live_websocket(
    websocket: WebSocket,
    room_id: int,
):
    """
    直播弹幕 WebSocket 端点

    连接后自动接收该直播间的弹幕、礼物、互动消息

    消息格式：
    - type: danmaku/gift/interact/status
    - data: 具体数据
    """
    await manager.connect(room_id, websocket)

    try:
        while True:
            # 保持连接，接收客户端消息（如心跳）
            data = await websocket.receive_json()

            # 处理客户端命令
            if data.get("action") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": datetime.now().isoformat()}
                })

    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
    except Exception as e:
        print(f"[LiveAPI] WebSocket 异常: {e}")
        await manager.disconnect(room_id, websocket)


@router.get("/rooms")
async def get_active_rooms():
    """获取当前活跃的直播间列表"""
    rooms = manager.get_active_rooms()
    return {
        "rooms": [
            {"room_id": room_id, "viewers": manager.get_room_count(room_id)}
            for room_id in rooms
        ]
    }


@router.get("/rooms/{room_id}/status")
async def get_room_status(room_id: int):
    """获取直播间连接状态"""
    return {
        "room_id": room_id,
        "connected": room_id in manager._clients,
        "viewers": manager.get_room_count(room_id),
    }


# ==================== 多房间统计 API ====================

@router.get("/multi/stats")
async def get_multi_room_stats():
    """
    获取所有活跃房间的统计数据（由 Spark Streaming 聚合）

    用于多房间对比视图
    """
    # 优先从 Redis 获取 Spark 聚合的数据
    if is_redis_available():
        spark_stats = get_all_room_stats()
        if spark_stats:
            return {
                "source": "spark",
                "rooms": [
                    {"room_id": room_id, **stats}
                    for room_id, stats in spark_stats.items()
                ]
            }

    # 回退：从内存获取实时统计
    rooms = manager.get_active_rooms()
    return {
        "source": "memory",
        "rooms": [
            {
                "room_id": room_id,
                **manager._stats[room_id].to_dict()
            }
            for room_id in rooms
            if room_id in manager._stats
        ]
    }


@router.get("/multi/stats/{room_id}/history")
async def get_room_stats_history_api(room_id: int, limit: int = 50):
    """
    获取单个房间的历史统计数据（用于趋势图）

    由 Spark Streaming 写入 Redis
    """
    if is_redis_available():
        history = get_room_stats_history(room_id, limit)
        if history:
            return {"room_id": room_id, "history": history}

    return {"room_id": room_id, "history": []}


@router.get("/multi/wordcloud")
async def get_global_wordcloud_api():
    """
    获取全局热词（跨房间聚合）

    由 Spark Streaming 聚合所有房间的弹幕生成
    """
    if is_redis_available():
        wordcloud = get_global_wordcloud()
        if wordcloud:
            return {"source": "spark", "data": wordcloud}

    # 回退：从内存聚合所有房间的弹幕
    all_danmakus = []
    for room_id in manager.get_active_rooms():
        if room_id in manager._stats:
            all_danmakus.extend(manager._stats[room_id].recent_danmakus)

    if all_danmakus:
        wordcloud = manager._nlp.get_word_cloud_data(all_danmakus, top_k=50)
        return {"source": "memory", "data": wordcloud}

    return {"source": "none", "data": []}


@router.get("/multi/ranking")
async def get_room_ranking():
    """
    获取房间热度排行

    按弹幕速率排序
    """
    stats = await get_multi_room_stats()
    rooms = stats.get("rooms", [])

    # 按弹幕数排序
    sorted_rooms = sorted(
        rooms,
        key=lambda x: x.get("total_danmaku", 0),
        reverse=True
    )

    return {
        "source": stats.get("source"),
        "ranking": [
            {
                "rank": i + 1,
                "room_id": room.get("room_id"),
                "total_danmaku": room.get("total_danmaku", 0),
                "avg_sentiment": room.get("avg_sentiment", 0.5),
            }
            for i, room in enumerate(sorted_rooms)
        ]
    }


@router.get("/status/services")
async def get_services_status():
    """获取后端服务状态（Kafka、Redis）"""
    return {
        "kafka": {
            "available": is_kafka_available(),
            "topic": "live-danmaku-topic",
        },
        "redis": {
            "available": is_redis_available(),
        },
        "active_rooms": len(manager.get_active_rooms()),
    }

