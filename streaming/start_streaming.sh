#!/usr/bin/env bash
set -euo pipefail

mkdir -p /tmp/ivy2

/opt/spark/bin/spark-submit \
  --conf spark.jars.ivy=/tmp/ivy2 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,mysql:mysql-connector-java:8.0.33 \
  /opt/spark/streaming/spark_streaming.py
