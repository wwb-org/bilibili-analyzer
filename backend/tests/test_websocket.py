"""
测试 WebSocket 端点
用法:
  1. 先启动后端: python main.py
  2. 再运行测试: python tests/test_websocket.py <直播间ID>
"""
import sys
import asyncio
import websockets
import json


async def test_websocket(room_id: int):
    """测试 WebSocket 连接"""
    uri = f"ws://localhost:8000/api/live/ws/{room_id}"

    print(f"正在连接 {uri} ...")

    try:
        async with websockets.connect(uri) as ws:
            print("连接成功！等待消息...\n")

            while True:
                message = await ws.recv()
                data = json.loads(message)

                msg_type = data.get("type", "unknown")
                msg_data = data.get("data", {})

                if msg_type == "status":
                    print(f"[状态] {msg_data.get('message')}")

                elif msg_type == "danmaku":
                    # 显示弹幕和情感分析结果
                    sentiment_label = msg_data.get('sentiment_label', 'unknown')
                    sentiment_score = msg_data.get('sentiment_score', 0)
                    label_emoji = {"positive": "+", "neutral": "=", "negative": "-"}.get(sentiment_label, "?")
                    print(f"[弹幕][{label_emoji}{sentiment_score:.2f}] {msg_data.get('user_name')}: {msg_data.get('content')}")

                elif msg_type == "gift":
                    print(f"[礼物] {msg_data.get('user_name')} 送出 {msg_data.get('gift_name')} x{msg_data.get('gift_count')}")

                elif msg_type == "interact":
                    action = msg_data.get("action")
                    if action == "enter":
                        print(f"[进场] {msg_data.get('user_name')} 进入直播间")
                    elif action == "like":
                        print(f"[点赞] {msg_data.get('user_name')} 点赞了")

                elif msg_type == "stats":
                    # 统计数据（每5秒更新）
                    dist = msg_data.get('sentiment_dist', {})
                    print(f"\n--- 统计 ---")
                    print(f"弹幕: {msg_data.get('total_danmaku')} | 礼物: {msg_data.get('total_gift')} | 速率: {msg_data.get('danmaku_rate')}/min")
                    print(f"情感: 正面{dist.get('positive',0)} 中性{dist.get('neutral',0)} 负面{dist.get('negative',0)} | 均值: {msg_data.get('avg_sentiment', 0):.3f}")
                    print("------------\n")

                elif msg_type == "wordcloud":
                    # 词云数据（每10秒更新）
                    words = msg_data[:10] if isinstance(msg_data, list) else []
                    if words:
                        top_words = " | ".join([f"{w['name']}({w['value']})" for w in words])
                        print(f"[词云] TOP10: {top_words}\n")

                else:
                    print(f"[{msg_type}] {msg_data}")

    except websockets.exceptions.ConnectionClosed:
        print("\n连接已关闭")
    except Exception as e:
        print(f"\n连接错误: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_websocket.py <直播间ID>")
        print("示例: python test_websocket.py 22066694")
        print("\n注意: 需要先启动后端服务 (python main.py)")
        sys.exit(1)

    room_id = int(sys.argv[1])

    try:
        asyncio.run(test_websocket(room_id))
    except KeyboardInterrupt:
        print("\n测试结束")
