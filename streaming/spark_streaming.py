"""
Spark Structured Streaming 实时弹幕处理

数据流：Kafka -> Spark -> Redis

功能：
1. 消费 live-danmaku-topic 的弹幕数据
2. 5秒微批次窗口聚合统计
3. 结果写入 Redis 供前端查询
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, count, avg, sum as spark_sum,
    when, lit, collect_list, struct, to_json, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    FloatType, TimestampType, LongType
)
import redis
import json


# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = "kafka:9094"
KAFKA_TOPIC = "live-danmaku-topic"

# Redis 配置
REDIS_HOST = "redis"
REDIS_PORT = 6379


def get_redis_client():
    """获取 Redis 客户端"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# 弹幕消息 Schema
danmaku_schema = StructType([
    StructField("room_id", IntegerType(), True),
    StructField("content", StringType(), True),
    StructField("user_name", StringType(), True),
    StructField("user_id", LongType(), True),
    StructField("timestamp", StringType(), True),
    StructField("sentiment_score", FloatType(), True),
    StructField("sentiment_label", StringType(), True),
    StructField("msg_type", StringType(), True),  # danmaku, gift, interact
])


def write_stats_to_redis(batch_df, batch_id):
    """
    将统计结果写入 Redis

    Redis Key:
    - live:stats:{room_id} - 统计数据 (Hash)
    - live:stats:{room_id}:history - 历史趋势 (List)
    """
    if batch_df.isEmpty():
        return

    redis_client = get_redis_client()

    # 收集统计数据
    stats = batch_df.collect()

    for row in stats:
        room_id = row["room_id"]
        key = f"live:stats:{room_id}"
        history_key = f"live:stats:{room_id}:history"

        stats_data = {
            "total_danmaku": int(row["total_danmaku"]),
            "positive_count": int(row["positive_count"]),
            "neutral_count": int(row["neutral_count"]),
            "negative_count": int(row["negative_count"]),
            "avg_sentiment": float(row["avg_sentiment"]) if row["avg_sentiment"] else 0.0,
            "window_start": str(row["window_start"]),
            "window_end": str(row["window_end"]),
            "updated_at": str(row["updated_at"])
        }

        # 更新当前统计
        redis_client.hset(key, mapping=stats_data)
        redis_client.expire(key, 3600)  # 1小时过期

        # 追加历史记录（保留最近100条）
        redis_client.lpush(history_key, json.dumps(stats_data))
        redis_client.ltrim(history_key, 0, 99)
        redis_client.expire(history_key, 3600)

    print(f"[Batch {batch_id}] 写入 {len(stats)} 个房间的统计数据到 Redis")


def main():
    """主函数"""
    print("=" * 60)
    print("启动 Spark Structured Streaming 弹幕处理")
    print("=" * 60)

    # 创建 Spark Session
    spark = SparkSession.builder \
        .appName("BilibiliDanmakuStreaming") \
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    print(f"Kafka Server: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")

    # 从 Kafka 读取流数据
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    # 解析 JSON 消息
    parsed_df = df.select(
        from_json(col("value").cast("string"), danmaku_schema).alias("data"),
        col("timestamp").alias("kafka_timestamp")
    ).select("data.*", "kafka_timestamp")

    # 只处理弹幕消息
    danmaku_df = parsed_df.filter(col("msg_type") == "danmaku")

    # 添加情感分类列
    classified_df = danmaku_df.withColumn(
        "sentiment_class",
        when(col("sentiment_score") > 0.6, "positive")
        .when(col("sentiment_score") < 0.4, "negative")
        .otherwise("neutral")
    )

    # 5秒窗口聚合统计
    stats_df = classified_df \
        .withWatermark("kafka_timestamp", "10 seconds") \
        .groupBy(
            col("room_id"),
            window(col("kafka_timestamp"), "5 seconds")
        ) \
        .agg(
            count("*").alias("total_danmaku"),
            avg("sentiment_score").alias("avg_sentiment"),
            spark_sum(when(col("sentiment_class") == "positive", 1).otherwise(0)).alias("positive_count"),
            spark_sum(when(col("sentiment_class") == "neutral", 1).otherwise(0)).alias("neutral_count"),
            spark_sum(when(col("sentiment_class") == "negative", 1).otherwise(0)).alias("negative_count")
        ) \
        .select(
            col("room_id"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("total_danmaku"),
            col("avg_sentiment"),
            col("positive_count"),
            col("neutral_count"),
            col("negative_count"),
            current_timestamp().alias("updated_at")
        )

    # 输出到 Redis
    query = stats_df.writeStream \
        .outputMode("update") \
        .foreachBatch(write_stats_to_redis) \
        .trigger(processingTime="5 seconds") \
        .start()

    print("Streaming 已启动，等待数据...")
    print("按 Ctrl+C 停止")

    query.awaitTermination()


if __name__ == "__main__":
    main()
