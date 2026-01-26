"""
测试 Kafka 生产者和 Spark Streaming 数据流
发送测试数据到 Kafka，验证 Spark Streaming 是否正常处理
"""
import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.kafka_producer import get_kafka_producer


def send_test_video_data(producer, count=5):
    """发送测试视频数据"""
    print(f"\n发送 {count} 条测试视频数据...")
    for i in range(count):
        video_data = {
            "bvid": f"BV1test{i:03d}",
            "title": f"测试视频 {i+1}",
            "category": "测试分区",
            "author_name": f"测试UP主{i+1}",
            "play_count": 1000 + i * 100,
            "like_count": 50 + i * 10,
        }
        success = producer.send_video_data(video_data)
        if success:
            print(f"  ✓ 视频数据已发送: {video_data['bvid']}")
        else:
            print(f"  ✗ 视频数据发送失败: {video_data['bvid']}")
        time.sleep(0.5)


def send_test_comment_data(producer, count=10):
    """发送测试评论数据"""
    print(f"\n发送 {count} 条测试评论数据...")
    sentiments = [0.8, 0.6, 0.5, 0.3, 0.9, 0.7, 0.4, 0.2, 0.85, 0.55]
    for i in range(count):
        comment_data = {
            "video_id": 1,
            "content": f"这是测试评论 {i+1}",
            "user_name": f"测试用户{i+1}",
            "sentiment_score": sentiments[i % len(sentiments)],
        }
        success = producer.send_comment_data(comment_data)
        if success:
            print(f"  ✓ 评论数据已发送: 情感分数 {comment_data['sentiment_score']}")
        else:
            print(f"  ✗ 评论数据发送失败")
        time.sleep(0.3)


def send_test_danmaku_data(producer, count=15):
    """发送测试弹幕数据"""
    print(f"\n发送 {count} 条测试弹幕数据...")
    for i in range(count):
        danmaku_data = {
            "video_id": 1,
            "content": f"测试弹幕 {i+1}",
            "send_time": float(i * 10),
        }
        success = producer.send_danmaku_data(danmaku_data)
        if success:
            print(f"  ✓ 弹幕数据已发送: {danmaku_data['content']}")
        else:
            print(f"  ✗ 弹幕数据发送失败")
        time.sleep(0.2)


if __name__ == "__main__":
    print("=" * 60)
    print("Kafka 生产者测试脚本")
    print("=" * 60)

    # 获取 Kafka 生产者
    producer = get_kafka_producer("localhost:9092")

    try:
        # 发送测试数据
        send_test_video_data(producer, count=5)
        send_test_comment_data(producer, count=10)
        send_test_danmaku_data(producer, count=15)

        print("\n" + "=" * 60)
        print("所有测试数据已发送完成！")
        print("请检查 Spark Streaming 控制台输出，验证数据是否被正常处理。")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
    finally:
        producer.close()
