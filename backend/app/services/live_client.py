"""
B站直播弹幕客户端

封装 bilibili-api-python 的直播弹幕功能，提供：
- 连接/断开直播间
- 事件回调机制（弹幕、礼物、进场、点赞、人气值）
- 结构化的事件数据
"""
import asyncio
from datetime import datetime
from typing import Callable, Optional, Any, Dict, List
from dataclasses import dataclass, field

from bilibili_api import live, select_client, request_settings


@dataclass
class DanmakuMessage:
    """弹幕消息"""
    content: str
    user_name: str
    user_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GiftMessage:
    """礼物消息"""
    gift_name: str
    gift_count: int
    user_name: str
    user_id: int = 0
    price: int = 0  # 金瓜子价值
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InteractMessage:
    """互动消息（进场、点赞等）"""
    action: str  # enter, like
    user_name: str
    user_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PopularityMessage:
    """人气值消息"""
    popularity: int
    timestamp: datetime = field(default_factory=datetime.now)


# 回调函数类型
DanmakuCallback = Callable[[DanmakuMessage], Any]
GiftCallback = Callable[[GiftMessage], Any]
InteractCallback = Callable[[InteractMessage], Any]
PopularityCallback = Callable[[PopularityMessage], Any]


def _safe_get(d: dict, path: str, default=None):
    """从嵌套 dict 安全取值，path 形如 'data.info.1'"""
    cur = d
    for p in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(p, default)
        elif isinstance(cur, (list, tuple)):
            try:
                cur = cur[int(p)]
            except Exception:
                return default
        else:
            return default
    return cur


class BiliLiveClient:
    """B站直播弹幕客户端"""

    def __init__(
        self,
        room_id: int,
        client: str = "aiohttp",
        proxy: Optional[str] = None,
        impersonate: Optional[str] = None,
    ):
        """
        初始化客户端

        Args:
            room_id: 直播间ID（短号或真实房间号）
            client: HTTP客户端选择，aiohttp 或 curl_cffi
            proxy: 代理地址，如 http://127.0.0.1:7890
            impersonate: curl_cffi 浏览器指纹伪装，如 chrome131
        """
        self.room_id = room_id
        self._client = client
        self._proxy = proxy
        self._impersonate = impersonate

        self._room: Optional[live.LiveDanmaku] = None
        self._is_connected = False
        self._connect_task: Optional[asyncio.Task] = None

        # 回调函数列表
        self._on_danmaku_callbacks: List[DanmakuCallback] = []
        self._on_gift_callbacks: List[GiftCallback] = []
        self._on_interact_callbacks: List[InteractCallback] = []
        self._on_popularity_callbacks: List[PopularityCallback] = []
        self._on_disconnect_callbacks: List[Callable[[], Any]] = []

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    def on_danmaku(self, callback: DanmakuCallback) -> "BiliLiveClient":
        """注册弹幕回调"""
        self._on_danmaku_callbacks.append(callback)
        return self

    def on_gift(self, callback: GiftCallback) -> "BiliLiveClient":
        """注册礼物回调"""
        self._on_gift_callbacks.append(callback)
        return self

    def on_interact(self, callback: InteractCallback) -> "BiliLiveClient":
        """注册互动回调（进场、点赞）"""
        self._on_interact_callbacks.append(callback)
        return self

    def on_popularity(self, callback: PopularityCallback) -> "BiliLiveClient":
        """注册人气值回调"""
        self._on_popularity_callbacks.append(callback)
        return self

    def on_disconnect(self, callback: Callable[[], Any]) -> "BiliLiveClient":
        """注册断开连接回调"""
        self._on_disconnect_callbacks.append(callback)
        return self

    def _setup_client(self):
        """配置请求客户端"""
        select_client(self._client)

        if self._client == "curl_cffi" and self._impersonate:
            request_settings.set("impersonate", self._impersonate)

        if self._proxy:
            request_settings.set_proxy(self._proxy)

    def _setup_event_handlers(self):
        """设置事件处理器"""

        @self._room.on("DANMU_MSG")
        async def handle_danmaku(event):
            msg = self._parse_danmaku(event)
            if msg:
                for callback in self._on_danmaku_callbacks:
                    try:
                        result = callback(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        print(f"[BiliLiveClient] 弹幕回调异常: {e}")

        @self._room.on("SEND_GIFT")
        async def handle_gift(event):
            msg = self._parse_gift(event)
            if msg:
                for callback in self._on_gift_callbacks:
                    try:
                        result = callback(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        print(f"[BiliLiveClient] 礼物回调异常: {e}")

        @self._room.on("INTERACT_WORD")
        async def handle_enter(event):
            msg = self._parse_interact(event, "enter")
            if msg:
                for callback in self._on_interact_callbacks:
                    try:
                        result = callback(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        print(f"[BiliLiveClient] 互动回调异常: {e}")

        @self._room.on("LIKE_INFO_V3_CLICK")
        async def handle_like(event):
            msg = self._parse_interact(event, "like")
            if msg:
                for callback in self._on_interact_callbacks:
                    try:
                        result = callback(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        print(f"[BiliLiveClient] 互动回调异常: {e}")

    def _parse_danmaku(self, event: dict) -> Optional[DanmakuMessage]:
        """解析弹幕事件"""
        try:
            raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
            info = _safe_get(raw, "data.info", [])

            content = ""
            if isinstance(info, list) and len(info) > 1:
                content = info[1]
            if not content:
                content = _safe_get(raw, "data.data.msg", "")

            user_name = ""
            user_id = 0
            if isinstance(info, list) and len(info) > 2 and isinstance(info[2], list):
                if len(info[2]) > 0:
                    user_id = info[2][0] or 0
                if len(info[2]) > 1:
                    user_name = info[2][1] or ""

            if not user_name:
                user_name = _safe_get(raw, "data.data.uname", "未知用户")

            return DanmakuMessage(
                content=content,
                user_name=user_name,
                user_id=user_id,
            )
        except Exception as e:
            print(f"[BiliLiveClient] 解析弹幕失败: {e}")
            return None

    def _parse_gift(self, event: dict) -> Optional[GiftMessage]:
        """解析礼物事件"""
        try:
            raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
            data = _safe_get(raw, "data.data", {}) or _safe_get(raw, "data", {}) or {}

            return GiftMessage(
                gift_name=data.get("giftName", "未知礼物"),
                gift_count=data.get("num", 1),
                user_name=data.get("uname", "未知用户"),
                user_id=data.get("uid", 0),
                price=data.get("price", 0),
            )
        except Exception as e:
            print(f"[BiliLiveClient] 解析礼物失败: {e}")
            return None

    def _parse_interact(self, event: dict, action: str) -> Optional[InteractMessage]:
        """解析互动事件"""
        try:
            raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
            data = _safe_get(raw, "data.data", {}) or _safe_get(raw, "data", {}) or {}

            return InteractMessage(
                action=action,
                user_name=data.get("uname", "未知用户"),
                user_id=data.get("uid", 0),
            )
        except Exception as e:
            print(f"[BiliLiveClient] 解析互动失败: {e}")
            return None

    async def connect(self):
        """连接直播间"""
        if self._is_connected:
            print(f"[BiliLiveClient] 已连接到直播间 {self.room_id}")
            return

        self._setup_client()
        self._room = live.LiveDanmaku(self.room_id)
        self._setup_event_handlers()

        self._is_connected = True
        print(f"[BiliLiveClient] 正在连接直播间 {self.room_id}...")

        try:
            await self._room.connect()
        except Exception as e:
            self._is_connected = False
            print(f"[BiliLiveClient] 连接断开: {e}")
            for callback in self._on_disconnect_callbacks:
                try:
                    result = callback()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as cb_e:
                    print(f"[BiliLiveClient] 断开回调异常: {cb_e}")

    async def disconnect(self):
        """断开连接"""
        if self._room and self._is_connected:
            try:
                await self._room.disconnect()
            except Exception as e:
                print(f"[BiliLiveClient] 断开连接异常: {e}")
            finally:
                self._is_connected = False
                self._room = None
                print(f"[BiliLiveClient] 已断开直播间 {self.room_id}")

    def start(self):
        """启动连接（阻塞方式，用于独立运行）"""
        try:
            asyncio.run(self.connect())
        except KeyboardInterrupt:
            print("\n[BiliLiveClient] 用户中断")


# 便捷函数：快速创建并连接
async def connect_live_room(
    room_id: int,
    on_danmaku: Optional[DanmakuCallback] = None,
    on_gift: Optional[GiftCallback] = None,
    on_interact: Optional[InteractCallback] = None,
    on_popularity: Optional[PopularityCallback] = None,
    client: str = "aiohttp",
    proxy: Optional[str] = None,
) -> BiliLiveClient:
    """
    快速连接直播间

    Args:
        room_id: 直播间ID
        on_danmaku: 弹幕回调
        on_gift: 礼物回调
        on_interact: 互动回调
        on_popularity: 人气值回调
        client: HTTP客户端
        proxy: 代理地址

    Returns:
        BiliLiveClient 实例
    """
    live_client = BiliLiveClient(room_id, client=client, proxy=proxy)

    if on_danmaku:
        live_client.on_danmaku(on_danmaku)
    if on_gift:
        live_client.on_gift(on_gift)
    if on_interact:
        live_client.on_interact(on_interact)
    if on_popularity:
        live_client.on_popularity(on_popularity)

    # 不等待连接完成，返回客户端让调用者控制
    return live_client
