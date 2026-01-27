"""
Kafka 服务模块

提供：
- KafkaProducer: 发送弹幕数据到 Kafka
- 与 Spark Streaming 配合实现实时流处理
"""

import json
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_DANMAKU = "live-danmaku-topic"

# 标记 Kafka 是否可用
_kafka_available = False
_producer = None

try:
    from kafka import KafkaProducer
    _kafka_available = True
except ImportError:
    logger.warning("kafka-python 未安装，Kafka 功能禁用")


def get_kafka_producer():
    """获取 Kafka Producer 单例"""
    global _producer

    if not _kafka_available:
        return None

    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                acks='all',
                retries=3,
            )
            logger.info(f"Kafka Producer 已连接: {KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Kafka Producer 连接失败: {e}")
            return None

    return _producer


def send_danmaku_to_kafka(
    room_id: int,
    content: str,
    user_name: str,
    user_id: int,
    sentiment_score: float,
    sentiment_label: str,
    timestamp: Optional[datetime] = None,
):
    """
    发送弹幕数据到 Kafka

    Args:
        room_id: 直播间 ID
        content: 弹幕内容
        user_name: 用户名
        user_id: 用户 ID
        sentiment_score: 情感分数 (0-1)
        sentiment_label: 情感标签 (positive/neutral/negative)
        timestamp: 时间戳
    """
    producer = get_kafka_producer()
    if producer is None:
        return False

    if timestamp is None:
        timestamp = datetime.now()

    message = {
        "room_id": room_id,
        "content": content,
        "user_name": user_name,
        "user_id": user_id,
        "timestamp": timestamp.isoformat(),
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "msg_type": "danmaku",
    }

    try:
        future = producer.send(KAFKA_TOPIC_DANMAKU, value=message)
        # 非阻塞发送，不等待确认
        # future.get(timeout=1)  # 如需同步确认可取消注释
        return True
    except Exception as e:
        logger.error(f"发送弹幕到 Kafka 失败: {e}")
        return False


def send_gift_to_kafka(
    room_id: int,
    gift_name: str,
    gift_count: int,
    user_name: str,
    user_id: int,
    price: float,
    timestamp: Optional[datetime] = None,
):
    """发送礼物数据到 Kafka"""
    producer = get_kafka_producer()
    if producer is None:
        return False

    if timestamp is None:
        timestamp = datetime.now()

    message = {
        "room_id": room_id,
        "gift_name": gift_name,
        "gift_count": gift_count,
        "user_name": user_name,
        "user_id": user_id,
        "price": price,
        "timestamp": timestamp.isoformat(),
        "msg_type": "gift",
    }

    try:
        producer.send(KAFKA_TOPIC_DANMAKU, value=message)
        return True
    except Exception as e:
        logger.error(f"发送礼物到 Kafka 失败: {e}")
        return False


def close_kafka_producer():
    """关闭 Kafka Producer"""
    global _producer
    if _producer is not None:
        _producer.close()
        _producer = None
        logger.info("Kafka Producer 已关闭")


def is_kafka_available() -> bool:
    """检查 Kafka 是否可用"""
    return _kafka_available and get_kafka_producer() is not None
