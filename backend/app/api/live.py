"""
直播弹幕分析 API

提供：
- WebSocket 端点：实时接收直播弹幕
- HTTP 端点：获取直播间信息
- NLP 分析：弹幕情感分析、词云生成
"""
import asyncio
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

router = APIRouter()


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

    async def connect(self, room_id: int, websocket: WebSocket):
        """用户连接到直播间"""
        await websocket.accept()

        if room_id not in self._connections:
            self._connections[room_id] = set()

        self._connections[room_id].add(websocket)

        # 如果是第一个用户，创建 B 站连接和统计
        if room_id not in self._clients:
            self._stats[room_id] = LiveRoomStats()
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

    async def _create_bili_client(self, room_id: int):
        """创建 B 站直播连接"""
        client = BiliLiveClient(room_id, client="aiohttp")

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
        sentiment_score = self._nlp.analyze_sentiment(msg.content)
        if sentiment_score >= 0.6:
            sentiment_label = "positive"
        elif sentiment_score <= 0.4:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # 更新统计
        if room_id in self._stats:
            self._stats[room_id].add_danmaku(msg.content, sentiment_score, sentiment_label)

        message = {
            "type": "danmaku",
            "data": {
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

        message = {
            "type": "gift",
            "data": {
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
        stats_interval = 5  # 统计广播间隔（秒）
        wordcloud_interval = 10  # 词云广播间隔（秒）
        last_wordcloud_time = datetime.now()

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

                # 每 10 秒广播词云
                now = datetime.now()
                if (now - last_wordcloud_time).total_seconds() >= wordcloud_interval:
                    last_wordcloud_time = now
                    if stats.recent_danmakus:
                        wordcloud_data = self._nlp.get_word_cloud_data(
                            list(stats.recent_danmakus), top_k=50
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
