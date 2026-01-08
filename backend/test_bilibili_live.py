"""
B站直播弹幕连接测试脚本（bilibili-api）
用法:
  python test_bilibili_live.py <直播间ID> [--client aiohttp|curl_cffi] [--impersonate chrome131] [--proxy http://...]
示例:
  python test_bilibili_live.py 21452505 --client aiohttp
  python test_bilibili_live.py 21452505 --client curl_cffi --impersonate chrome131
  python test_bilibili_live.py 21452505 --client curl_cffi --impersonate chrome131 --proxy http://127.0.0.1:7890
"""

import argparse
import asyncio
from datetime import datetime

from bilibili_api import live, select_client, request_settings


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def safe_get(d: dict, path: str, default=None):
    """
    从嵌套 dict 安全取值：
    path 形如 "data.info.1"
    """
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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("room_id", type=int, help="直播间ID（短号/房间号均可，库会尝试获取真实房间号）")
    parser.add_argument("--client", choices=["aiohttp", "curl_cffi"], default="aiohttp",
                        help="请求库选择：aiohttp（默认）或 curl_cffi（更抗风控，需装 curl_cffi）")
    parser.add_argument("--impersonate", default=None,
                        help='仅 curl_cffi 生效：例如 chrome131（值参考 curl_cffi 文档）')
    parser.add_argument("--proxy", default=None, help="代理，例如 http://127.0.0.1:7890")
    args = parser.parse_args()

    # 1) 选择请求库（很关键：httpx 在该项目中标注为不支持 WebSocket）
    # README: 支持库优先级 curl_cffi > aiohttp > httpx，且 httpx 不支持 WebSocket :contentReference[oaicite:3]{index=3}
    select_client(args.client)

    # 2) 可选：curl_cffi 伪装浏览器指纹（README 示例）
    # request_settings.set("impersonate", "chrome131") :contentReference[oaicite:4]{index=4}
    if args.client == "curl_cffi" and args.impersonate:
        request_settings.set("impersonate", args.impersonate)

    # 3) 可选：代理（README 示例）
    if args.proxy:
        request_settings.set_proxy(args.proxy)

    room = live.LiveDanmaku(args.room_id)

    @room.on("DANMU_MSG")
    async def on_danmaku(event):
        # 兼容不同结构：优先按常见 info 格式取
        raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
        info = safe_get(raw, "data.info", [])
        content = info[1] if isinstance(info, list) and len(info) > 1 else safe_get(raw, "data.data.msg", "")
        user_name = ""
        if isinstance(info, list) and len(info) > 2 and isinstance(info[2], list) and len(info[2]) > 1:
            user_name = info[2][1]
        if not user_name:
            user_name = safe_get(raw, "data.data.uname", "未知用户")
        print(f"[{now_ts()}] [弹幕] {user_name}: {content}")

    @room.on("SEND_GIFT")
    async def on_gift(event):
        raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
        data = safe_get(raw, "data.data", {}) or safe_get(raw, "data", {}) or {}
        gift_name = data.get("giftName", "未知礼物")
        user_name = data.get("uname", "未知用户")
        num = data.get("num", 1)
        print(f"[{now_ts()}] [礼物] {user_name} 送出 {gift_name} x{num}")

    @room.on("INTERACT_WORD")
    async def on_enter(event):
        raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
        data = safe_get(raw, "data.data", {}) or safe_get(raw, "data", {}) or {}
        user_name = data.get("uname", "未知用户")
        print(f"[{now_ts()}] [进场] {user_name} 进入直播间")

    @room.on("LIKE_INFO_V3_CLICK")
    async def on_like(event):
        raw = event if isinstance(event, dict) else getattr(event, "data", {}) or {}
        data = safe_get(raw, "data.data", {}) or safe_get(raw, "data", {}) or {}
        user_name = data.get("uname", "未知用户")
        print(f"[{now_ts()}] [点赞] {user_name} 点赞了")

    print(f"\n正在连接直播间 {args.room_id} ...")
    print("开始监听弹幕... (按 Ctrl+C 退出)\n")

    # connect() 会常驻运行直到断开/退出
    await room.connect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
