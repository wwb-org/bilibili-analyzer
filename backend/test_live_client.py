"""
测试 BiliLiveClient 封装
用法: python test_live_client.py <直播间ID>
"""
import sys
import asyncio
sys.path.insert(0, ".")

from app.services.live_client import (
    BiliLiveClient,
    DanmakuMessage,
    GiftMessage,
    InteractMessage,
)


def on_danmaku(msg: DanmakuMessage):
    """弹幕回调"""
    print(f"[弹幕] {msg.user_name}: {msg.content}")


def on_gift(msg: GiftMessage):
    """礼物回调"""
    print(f"[礼物] {msg.user_name} 送出 {msg.gift_name} x{msg.gift_count}")


def on_interact(msg: InteractMessage):
    """互动回调"""
    if msg.action == "enter":
        print(f"[进场] {msg.user_name} 进入直播间")
    elif msg.action == "like":
        print(f"[点赞] {msg.user_name} 点赞了")


async def main():
    if len(sys.argv) < 2:
        print("用法: python test_live_client.py <直播间ID>")
        print("示例: python test_live_client.py 21452505")
        sys.exit(1)

    room_id = int(sys.argv[1])

    # 创建客户端并注册回调
    client = BiliLiveClient(room_id, client="aiohttp")
    client.on_danmaku(on_danmaku)
    client.on_gift(on_gift)
    client.on_interact(on_interact)

    print(f"正在连接直播间 {room_id}...")
    print("按 Ctrl+C 退出\n")

    await client.connect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
