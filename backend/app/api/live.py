"""
直播弹幕分析 API

提供：
- WebSocket 端点：实时接收直播弹幕
- HTTP 端点：获取直播间信息
"""
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from app.services.live_client import (
    BiliLiveClient,
    DanmakuMessage,
    GiftMessage,
    InteractMessage,
)

router = APIRouter()


class LiveConnectionManager:
    """
    直播间连接管理器

    管理多个用户连接到同一直播间的场景：
    - 复用 B 站连接（同一直播间只建立一个连接）
    - 广播消息给所有观看该直播间的用户
    """

    def __init__(self):
        # room_id -> Set[WebSocket] 前端连接
        self._connections: Dict[int, Set[WebSocket]] = {}
        # room_id -> BiliLiveClient B站连接
        self._clients: Dict[int, BiliLiveClient] = {}
        # room_id -> asyncio.Task 连接任务
        self._tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        """用户连接到直播间"""
        await websocket.accept()

        if room_id not in self._connections:
            self._connections[room_id] = set()

        self._connections[room_id].add(websocket)

        # 如果是第一个用户，创建 B 站连接
        if room_id not in self._clients:
            await self._create_bili_client(room_id)

        # 发送连接成功消息
        await websocket.send_json({
            "type": "status",
            "data": {
                "status": "connected",
                "room_id": room_id,
                "message": "连接成功"
            }
        })

    async def disconnect(self, room_id: int, websocket: WebSocket):
        """用户断开连接"""
        if room_id in self._connections:
            self._connections[room_id].discard(websocket)

            # 如果没有用户了，关闭 B 站连接
            if not self._connections[room_id]:
                await self._close_bili_client(room_id)
                del self._connections[room_id]

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
        """广播弹幕消息"""
        message = {
            "type": "danmaku",
            "data": {
                "content": msg.content,
                "user_name": msg.user_name,
                "user_id": msg.user_id,
                "timestamp": msg.timestamp.isoformat(),
            }
        }
        await self._broadcast(room_id, message)

    async def _broadcast_gift(self, room_id: int, msg: GiftMessage):
        """广播礼物消息"""
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
