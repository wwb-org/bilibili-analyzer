"""
清除所有业务数据（保留用户信息）

清除范围：
  - ODS层：videos, comments, danmakus, keywords, crawl_logs, keyword_alert_subscriptions
  - DWD层：dwd_video_snapshot, dwd_comment_daily, dwd_keyword_daily
  - DWS层：dws_stats_daily, dws_category_daily, dws_sentiment_daily, dws_video_trend, dws_keyword_stats

保留：
  - users 表（用户账号信息）

用法：
  cd backend
  python clear_data.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import SessionLocal

# 需要清除的表（按外键依赖顺序排列，子表在前）
TABLES_TO_CLEAR = [
    # ODS 层（子表先删）
    "comments",
    "danmakus",
    "keywords",
    "crawl_logs",
    "keyword_alert_subscriptions",
    "videos",
    # DWD 层
    "dwd_comment_daily",
    "dwd_video_snapshot",
    "dwd_keyword_daily",
    # DWS 层
    "dws_stats_daily",
    "dws_category_daily",
    "dws_sentiment_daily",
    "dws_video_trend",
    "dws_keyword_stats",
]


def clear_all_data():
    db = SessionLocal()
    try:
        # 临时禁用外键检查
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        for table in TABLES_TO_CLEAR:
            result = db.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
            count = result.scalar()
            db.execute(text(f"TRUNCATE TABLE `{table}`"))
            print(f"  {table}: 清除 {count} 条记录")

        db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.commit()
        print("\n所有业务数据已清除，用户信息已保留。")
    except Exception as e:
        db.rollback()
        print(f"\n清除失败: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    confirm = input("确认清除所有业务数据（用户信息将保留）？输入 yes 确认: ")
    if confirm.strip().lower() != "yes":
        print("已取消。")
        sys.exit(0)

    print("\n开始清除...")
    clear_all_data()
