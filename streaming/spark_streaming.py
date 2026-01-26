"""
Spark Streaming 实时数据处理
从 Kafka 读取视频、评论、弹幕数据，进行实时处理和聚合
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, sum as spark_sum, avg
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, TimestampType
import os
import redis
import json
from datetime import datetime

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "bilibili_analyzer")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# 创建 Spark Session
spark = SparkSession.builder \
    .appName("BilibiliStreamingAnalyzer") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,mysql:mysql-connector-java:8.0.33") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 定义数据 Schema
video_schema = StructType([
    StructField("bvid", StringType(), True),
    StructField("title", StringType(), True),
    StructField("category", StringType(), True),
    StructField("author_name", StringType(), True),
    StructField("play_count", IntegerType(), True),
    StructField("like_count", IntegerType(), True),
    StructField("timestamp", TimestampType(), True)
])

comment_schema = StructType([
    StructField("video_id", IntegerType(), True),
    StructField("content", StringType(), True),
    StructField("user_name", StringType(), True),
    StructField("sentiment_score", FloatType(), True),
    StructField("timestamp", TimestampType(), True)
])

danmaku_schema = StructType([
    StructField("video_id", IntegerType(), True),
    StructField("content", StringType(), True),
    StructField("send_time", FloatType(), True),
    StructField("timestamp", TimestampType(), True)
])

live_danmaku_schema = StructType([
    StructField("room_id", IntegerType(), True),
    StructField("content", StringType(), True),
    StructField("user_name", StringType(), True),
    StructField("user_id", IntegerType(), True),
    StructField("sentiment_score", FloatType(), True),
    StructField("sentiment_label", StringType(), True),
    StructField("timestamp", StringType(), True)
])


def process_video_stream():
    """处理视频数据流"""
    video_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "video-topic") \
        .option("startingOffsets", "latest") \
        .load()

    # 解析 JSON 数据
    video_data = video_df.select(
        from_json(col("value").cast("string"), video_schema).alias("data")
    ).select("data.*")

    # 实时统计：每5分钟的视频数量和播放量
    video_stats = video_data \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window("timestamp", "5 minutes"),
            "category"
        ) \
        .agg(
            count("bvid").alias("video_count"),
            spark_sum("play_count").alias("total_plays"),
            avg("like_count").alias("avg_likes")
        )

    # 输出到控制台（用于调试）
    query = video_stats.writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    return query


def process_comment_stream():
    """处理评论数据流"""
    comment_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "comment-topic") \
        .option("startingOffsets", "latest") \
        .load()

    # 解析 JSON 数据
    comment_data = comment_df.select(
        from_json(col("value").cast("string"), comment_schema).alias("data")
    ).select("data.*")

    # 实时统计：每5分钟的评论情感分析
    comment_stats = comment_data \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(window("timestamp", "5 minutes")) \
        .agg(
            count("*").alias("comment_count"),
            avg("sentiment_score").alias("avg_sentiment")
        )

    # 输出到控制台
    query = comment_stats.writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    return query


def process_danmaku_stream():
    """处理弹幕数据流"""
    danmaku_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "danmaku-topic") \
        .option("startingOffsets", "latest") \
        .load()

    # 解析 JSON 数据
    danmaku_data = danmaku_df.select(
        from_json(col("value").cast("string"), danmaku_schema).alias("data")
    ).select("data.*")

    # 实时统计：每5分钟的弹幕数量
    danmaku_stats = danmaku_data \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(window("timestamp", "5 minutes")) \
        .agg(count("*").alias("danmaku_count"))

    # 输出到控制台
    query = danmaku_stats.writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .start()

    return query


def write_to_redis(batch_df, batch_id):
    """
    将直播弹幕数据批量写入 Redis

    Args:
        batch_df: Spark DataFrame 批次
        batch_id: 批次ID
    """
    try:
        # 连接 Redis
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )

        # 收集数据到 Driver
        rows = batch_df.collect()

        if not rows:
            return

        print(f"[Batch {batch_id}] 处理 {len(rows)} 条直播弹幕")

        # 按房间ID分组
        room_data = {}
        for row in rows:
            room_id = row.room_id
            if room_id not in room_data:
                room_data[room_id] = {
                    "danmaku_list": [],
                    "total_count": 0,
                    "sentiment_sum": 0.0,
                    "sentiment_dist": {"positive": 0, "neutral": 0, "negative": 0}
                }

            # 弹幕数据
            danmaku = {
                "content": row.content,
                "user_name": row.user_name,
                "user_id": row.user_id,
                "sentiment_score": row.sentiment_score,
                "sentiment_label": row.sentiment_label,
                "timestamp": row.timestamp
            }

            room_data[room_id]["danmaku_list"].append(danmaku)
            room_data[room_id]["total_count"] += 1
            room_data[room_id]["sentiment_sum"] += row.sentiment_score
            room_data[room_id]["sentiment_dist"][row.sentiment_label] += 1

        # 写入 Redis
        for room_id, data in room_data.items():
            # 1. 添加弹幕到列表（保留最新1000条）
            for danmaku in data["danmaku_list"]:
                redis_client.lpush(
                    f"live:danmaku:{room_id}",
                    json.dumps(danmaku, ensure_ascii=False)
                )
            redis_client.ltrim(f"live:danmaku:{room_id}", 0, 999)
            redis_client.expire(f"live:danmaku:{room_id}", 3600)

            # 2. 更新统计数据（累加）
            stats_key = f"live:stats:{room_id}"
            existing_stats = redis_client.get(stats_key)

            if existing_stats:
                stats = json.loads(existing_stats)
                stats["total_danmaku"] += data["total_count"]
                stats["sentiment_sum"] += data["sentiment_sum"]
                for label, count in data["sentiment_dist"].items():
                    stats["sentiment_dist"][label] += count
            else:
                stats = {
                    "total_danmaku": data["total_count"],
                    "sentiment_sum": data["sentiment_sum"],
                    "sentiment_dist": data["sentiment_dist"],
                    "start_time": datetime.now().isoformat()
                }

            # 计算平均情感分
            if stats["total_danmaku"] > 0:
                stats["avg_sentiment"] = round(stats["sentiment_sum"] / stats["total_danmaku"], 3)
            else:
                stats["avg_sentiment"] = 0.5

            redis_client.setex(stats_key, 3600, json.dumps(stats, ensure_ascii=False))

        print(f"[Batch {batch_id}] 已写入 Redis，涉及 {len(room_data)} 个直播间")

    except Exception as e:
        print(f"[Batch {batch_id}] 写入 Redis 失败: {e}")


def process_live_danmaku_stream():
    """处理直播弹幕数据流"""
    live_danmaku_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "live-danmaku-topic") \
        .option("startingOffsets", "latest") \
        .load()

    # 解析 JSON 数据
    live_danmaku_data = live_danmaku_df.select(
        from_json(col("value").cast("string"), live_danmaku_schema).alias("data")
    ).select("data.*")

    # 写入 Redis（使用 foreachBatch）
    query = live_danmaku_data.writeStream \
        .foreachBatch(write_to_redis) \
        .outputMode("append") \
        .start()

    return query


if __name__ == "__main__":
    print("启动 Spark Streaming...")
    print(f"Kafka 服务器: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Redis 服务器: {REDIS_HOST}:{REDIS_PORT}")

    # 启动所有流处理任务
    video_query = process_video_stream()
    comment_query = process_comment_stream()
    danmaku_query = process_danmaku_stream()
    live_danmaku_query = process_live_danmaku_stream()

    print("所有流处理任务已启动，等待数据...")

    # 等待所有查询完成
    spark.streams.awaitAnyTermination()
