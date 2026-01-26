"""
测试直播弹幕 → Kafka → Spark Streaming → Redis 完整数据流

使用方法：
1. 启动 Docker 服务：docker compose up -d
2. 启动 Spark Streaming：
   docker exec -it bilibili-analyzer-spark-master bash
   cd /opt/spark/streaming
   /opt/spark/bin/spark-submit \
     --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,mysql:mysql-connector-java:8.0.33 \
     spark_streaming.py
3. 运行本测试脚本：python test_live_kafka_redis.py <直播间ID>
"""
import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.live_client import BiliLiveClient
from app.services.nlp import NLPAnalyzer
from app.services.kafka_producer import get_kafka_producer
from app.core.redis_client import get_redis_client


class LiveKafkaRedisTest:
    """直播弹幕 Kafka Redis 测试"""

    def __init__(self, room_id: int):
        self.room_id = room_id
        self.client = None
        self.nlp = NLPAnalyzer()
        self.kafka_producer = get_kafka_producer()
        self.redis_client = get_redis_client()
        self.danmaku_count = 0

    async def on_danmaku(self, msg):
        """处理弹幕消息"""
        self.danmaku_count += 1

        # 情感分析
        sentiment_score = self.nlp.analyze_sentiment(msg.content)
        if sentiment_score >= 0.6:
            sentiment_label = "positive"
        elif sentiment_score <= 0.4:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # 发送到 Kafka
        live_danmaku_data = {
            "room_id": self.room_id,
            "content": msg.content,
            "user_name": msg.user_name,
            "user_id": msg.user_id,
            "timestamp": msg.timestamp.isoformat(),
            "sentiment_score": round(sentiment_score, 3),
            "sentiment_label": sentiment_label,
        }

        success = self.kafka_producer.send_live_danmaku_data(live_danmaku_data)

        # 打印弹幕信息
        sentiment_emoji = "+" if sentiment_label == "positive" else ("=" if sentiment_label == "neutral" else "-")
        print(f"[弹幕 #{self.danmaku_count}][{sentiment_emoji}{sentiment_score:.2f}] {msg.user_name}: {msg.content}")
        print(f"  → Kafka: {'✓' if success else '✗'}")

    async def check_redis_data(self):
        """定期检查 Redis 中的数据"""
        while True:
            await asyncio.sleep(10)  # 每10秒检查一次

            print("\n" + "=" * 60)
            print(f"[Redis 检查] 直播间 {self.room_id}")

            # 检查统计数据
            stats = self.redis_client.get_live_danmaku_stats(self.room_id)
            if stats:
                print(f"  统计数据:")
                print(f"    - 总弹幕数: {stats.get('total_danmaku', 0)}")
                print(f"    - 平均情感分: {stats.get('avg_sentiment', 0):.3f}")
                print(f"    - 情感分布: {stats.get('sentiment_dist', {})}")
            else:
                print("  统计数据: 暂无")

            # 检查弹幕列表
            danmaku_list = self.redis_client.get_live_danmaku_list(self.room_id, 0, 4)
            if danmaku_list:
                print(f"  最新弹幕 (前5条):")
                for i, danmaku in enumerate(danmaku_list, 1):
                    print(f"    {i}. [{danmaku.get('sentiment_label')}] {danmaku.get('user_name')}: {danmaku.get('content')}")
            else:
                print("  弹幕列表: 暂无")

            print("=" * 60 + "\n")

    async def run(self):
        """运行测试"""
        print(f"开始测试直播间 {self.room_id} 的数据流...")
        print(f"数据流: 直播弹幕 → Kafka → Spark Streaming → Redis\n")

        # 打印连接信息
        print(f"Redis 连接: {self.redis_client.url}")
        print(f"Kafka 连接: {self.kafka_producer.bootstrap_servers}\n")

        # 创建直播客户端
        self.client = BiliLiveClient(
            self.room_id,
            client="aiohttp",
            proxy="http://127.0.0.1:7897"  # 如果不需要代理，可以设置为 None
        )

        # 注册弹幕回调
        self.client.on_danmaku(self.on_danmaku)

        # 启动 Redis 检查任务
        redis_task = asyncio.create_task(self.check_redis_data())

        try:
            # 连接直播间
            print(f"正在连接直播间 {self.room_id}...")
            await self.client.connect()
        except KeyboardInterrupt:
            print("\n\n测试已停止")
        finally:
            redis_task.cancel()
            await self.client.disconnect()
            self.kafka_producer.close()
            self.redis_client.close()

            print(f"\n测试总结:")
            print(f"  - 接收弹幕数: {self.danmaku_count}")
            print(f"  - 直播间ID: {self.room_id}")


def main():
    if len(sys.argv) < 2:
        print("用法: python test_live_kafka_redis.py <直播间ID>")
        print("示例: python test_live_kafka_redis.py 22625027")
        sys.exit(1)

    room_id = int(sys.argv[1])
    test = LiveKafkaRedisTest(room_id)

    try:
        asyncio.run(test.run())
    except KeyboardInterrupt:
        print("\n测试已停止")


if __name__ == "__main__":
    main()
