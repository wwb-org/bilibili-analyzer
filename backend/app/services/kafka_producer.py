"""
Kafka 生产者服务
用于将采集的数据发送到 Kafka topics
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class BilibiliKafkaProducer:
    """B站数据 Kafka 生产者"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        初始化 Kafka 生产者

        Args:
            bootstrap_servers: Kafka 服务器地址
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[KafkaProducer] = None
        self._connect()

    def _connect(self):
        """连接到 Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode('utf-8'),
                acks='all',  # 等待所有副本确认
                retries=3,   # 重试次数
                max_in_flight_requests_per_connection=1  # 保证消息顺序
            )
            logger.info(f"Kafka 生产者已连接: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Kafka 连接失败: {e}")
            self.producer = None

    def send_video_data(self, video_data: Dict[str, Any]) -> bool:
        """
        发送视频数据到 Kafka

        Args:
            video_data: 视频数据字典

        Returns:
            是否发送成功
        """
        if not self.producer:
            logger.warning("Kafka 生产者未连接，跳过发送")
            return False

        try:
            # 添加时间戳
            video_data['timestamp'] = datetime.now().isoformat()

            # 发送到 video-topic
            future = self.producer.send('video-topic', value=video_data)
            future.get(timeout=10)  # 等待发送完成
            logger.debug(f"视频数据已发送: {video_data.get('bvid')}")
            return True
        except KafkaError as e:
            logger.error(f"发送视频数据失败: {e}")
            return False

    def send_comment_data(self, comment_data: Dict[str, Any]) -> bool:
        """
        发送评论数据到 Kafka

        Args:
            comment_data: 评论数据字典

        Returns:
            是否发送成功
        """
        if not self.producer:
            logger.warning("Kafka 生产者未连接，跳过发送")
            return False

        try:
            # 添加时间戳
            comment_data['timestamp'] = datetime.now().isoformat()

            # 发送到 comment-topic
            future = self.producer.send('comment-topic', value=comment_data)
            future.get(timeout=10)
            logger.debug(f"评论数据已发送")
            return True
        except KafkaError as e:
            logger.error(f"发送评论数据失败: {e}")
            return False

    def send_danmaku_data(self, danmaku_data: Dict[str, Any]) -> bool:
        """
        发送弹幕数据到 Kafka

        Args:
            danmaku_data: 弹幕数据字典

        Returns:
            是否发送成功
        """
        if not self.producer:
            logger.warning("Kafka 生产者未连接，跳过发送")
            return False

        try:
            # 添加时间戳
            danmaku_data['timestamp'] = datetime.now().isoformat()

            # 发送到 danmaku-topic
            future = self.producer.send('danmaku-topic', value=danmaku_data)
            future.get(timeout=10)
            logger.debug(f"弹幕数据已发送")
            return True
        except KafkaError as e:
            logger.error(f"发送弹幕数据失败: {e}")
            return False

    def send_live_danmaku_data(self, live_danmaku_data: Dict[str, Any]) -> bool:
        """
        发送直播弹幕数据到 Kafka

        Args:
            live_danmaku_data: 直播弹幕数据字典，包含：
                - room_id: 直播间ID
                - content: 弹幕内容
                - user_name: 用户名
                - user_id: 用户ID
                - sentiment_score: 情感分数
                - sentiment_label: 情感标签
                - timestamp: 时间戳

        Returns:
            是否发送成功
        """
        if not self.producer:
            logger.warning("Kafka 生产者未连接，跳过发送")
            return False

        try:
            # 确保有时间戳
            if 'timestamp' not in live_danmaku_data:
                live_danmaku_data['timestamp'] = datetime.now().isoformat()

            # 发送到 live-danmaku-topic
            future = self.producer.send('live-danmaku-topic', value=live_danmaku_data)
            future.get(timeout=10)
            logger.debug(f"直播弹幕数据已发送: room_id={live_danmaku_data.get('room_id')}")
            return True
        except KafkaError as e:
            logger.error(f"发送直播弹幕数据失败: {e}")
            return False

    def close(self):
        """关闭 Kafka 生产者连接"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka 生产者已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# 全局 Kafka 生产者实例（单例模式）
_kafka_producer: Optional[BilibiliKafkaProducer] = None


def get_kafka_producer(bootstrap_servers: str = "localhost:9092") -> BilibiliKafkaProducer:
    """
    获取 Kafka 生产者实例（单例）

    Args:
        bootstrap_servers: Kafka 服务器地址

    Returns:
        Kafka 生产者实例
    """
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = BilibiliKafkaProducer(bootstrap_servers)
    return _kafka_producer

