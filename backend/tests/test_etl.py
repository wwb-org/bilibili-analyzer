"""
数据仓库ETL测试脚本

用法：
    cd backend
    python tests/test_etl.py

功能：
    1. 测试ETL任务执行
    2. 验证数仓表数据
"""
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.etl.scheduler import etl_scheduler
from app.models.warehouse import (
    DwdVideoSnapshot,
    DwdCommentDaily,
    DwsStatsDaily,
    DwsCategoryDaily,
    DwsSentimentDaily,
    DwsVideoTrend,
)


def test_etl():
    """测试ETL执行"""
    print("=" * 60)
    print("数据仓库ETL测试")
    print("=" * 60)

    # 使用今天作为统计日期（测试用）
    stat_date = date.today()
    print(f"\n统计日期: {stat_date}")

    try:
        # 执行ETL
        print("\n正在执行ETL任务...")
        results = etl_scheduler.run_daily_etl(stat_date)

        print("\n执行结果:")
        for result in results:
            print(f"  - {result['task']}: 处理 {result['records_processed']} 条记录, 耗时 {result['duration']:.2f}秒")

        # 验证数据
        print("\n验证数仓表数据:")
        db = SessionLocal()

        try:
            # DWD层
            snapshot_count = db.query(DwdVideoSnapshot).filter(
                DwdVideoSnapshot.snapshot_date == stat_date
            ).count()
            print(f"  - dwd_video_snapshot: {snapshot_count} 条")

            comment_count = db.query(DwdCommentDaily).filter(
                DwdCommentDaily.stat_date == stat_date
            ).count()
            print(f"  - dwd_comment_daily: {comment_count} 条")

            # DWS层
            stats = db.query(DwsStatsDaily).filter(
                DwsStatsDaily.stat_date == stat_date
            ).first()
            if stats:
                print(f"  - dws_stats_daily: 视频数={stats.total_videos}, 播放量={stats.total_play_count}")
            else:
                print(f"  - dws_stats_daily: 无数据")

            category_count = db.query(DwsCategoryDaily).filter(
                DwsCategoryDaily.stat_date == stat_date
            ).count()
            print(f"  - dws_category_daily: {category_count} 个分区")

            sentiment = db.query(DwsSentimentDaily).filter(
                DwsSentimentDaily.stat_date == stat_date,
                DwsSentimentDaily.category == 'all'
            ).first()
            if sentiment:
                print(f"  - dws_sentiment_daily: 正面={sentiment.positive_count}, 中性={sentiment.neutral_count}, 负面={sentiment.negative_count}")
            else:
                print(f"  - dws_sentiment_daily: 无数据")

            trend_count = db.query(DwsVideoTrend).filter(
                DwsVideoTrend.trend_date == stat_date
            ).count()
            print(f"  - dws_video_trend: {trend_count} 条")

        finally:
            db.close()

        print("\n" + "=" * 60)
        print("ETL测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\nETL执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_etl()
    sys.exit(0 if success else 1)
