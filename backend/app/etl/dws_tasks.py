"""
DWS层ETL任务

包含：
- StatsDailyETL: 每日全局统计ETL
- CategoryDailyETL: 每日分区统计ETL
- SentimentDailyETL: 每日情感统计ETL
- VideoTrendETL: 视频热度趋势ETL
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.etl.base import ETLTask
from app.models.warehouse import (
    DwdVideoSnapshot,
    DwdCommentDaily,
    DwsStatsDaily,
    DwsCategoryDaily,
    DwsSentimentDaily,
    DwsVideoTrend,
)


class StatsDailyETL(ETLTask):
    """
    每日全局统计ETL

    功能：预聚合每日全局统计数据
    数据流：dwd_video_snapshot, dwd_comment_daily → dws_stats_daily
    """

    def extract(self, stat_date: date) -> Dict:
        """从DWD层抽取当日数据"""
        snapshots = self.db.query(DwdVideoSnapshot).filter(
            DwdVideoSnapshot.snapshot_date == stat_date
        ).all()

        comments = self.db.query(DwdCommentDaily).filter(
            DwdCommentDaily.stat_date == stat_date
        ).all()

        return {"snapshots": snapshots, "comments": comments}

    def transform(self, data: Dict) -> Dict:
        """聚合计算"""
        snapshots = data["snapshots"]
        comments = data["comments"]

        if not snapshots:
            return None

        # 累计指标
        total_play = sum(s.play_count or 0 for s in snapshots)
        total_like = sum(s.like_count or 0 for s in snapshots)
        total_coin = sum(s.coin_count or 0 for s in snapshots)
        total_danmaku = sum(s.danmaku_count or 0 for s in snapshots)
        total_comments = sum(s.comment_count or 0 for s in snapshots)

        # 增量指标
        play_increment = sum(s.play_increment or 0 for s in snapshots)
        like_increment = sum(s.like_increment or 0 for s in snapshots)
        new_comments = len(comments)

        # 新视频：播放增量等于播放总数的视频（首次记录）
        new_videos = len([s for s in snapshots if s.play_increment == s.play_count and s.play_count > 0])

        # 平均值
        video_count = len(snapshots)
        avg_play = self._safe_divide(total_play, video_count)
        avg_like = self._safe_divide(total_like, video_count)
        avg_interaction = self._safe_divide(
            sum(s.interaction_rate or 0 for s in snapshots),
            video_count
        )

        return {
            "total_videos": video_count,
            "total_comments": total_comments,
            "total_play_count": total_play,
            "total_like_count": total_like,
            "total_coin_count": total_coin,
            "total_danmaku_count": total_danmaku,
            "new_videos": new_videos,
            "new_comments": new_comments,
            "play_increment": play_increment,
            "like_increment": like_increment,
            "avg_play_count": round(avg_play, 2),
            "avg_like_count": round(avg_like, 2),
            "avg_interaction_rate": round(avg_interaction, 6)
        }

    def load(self, data: Dict, stat_date: date) -> int:
        """写入每日全局统计表"""
        if not data:
            return 0

        existing = self.db.query(DwsStatsDaily).filter(
            DwsStatsDaily.stat_date == stat_date
        ).first()

        if existing:
            # 更新
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            # 新增
            stats = DwsStatsDaily(stat_date=stat_date, **data)
            self.db.add(stats)

        return 1


class CategoryDailyETL(ETLTask):
    """
    每日分区统计ETL

    功能：预聚合每日分区统计
    数据流：dwd_video_snapshot → dws_category_daily
    """

    def extract(self, stat_date: date) -> List:
        """按分区分组抽取"""
        result = self.db.query(
            DwdVideoSnapshot.category,
            func.count(DwdVideoSnapshot.id).label('count'),
            func.sum(DwdVideoSnapshot.play_count).label('play'),
            func.sum(DwdVideoSnapshot.like_count).label('like'),
            func.sum(DwdVideoSnapshot.coin_count).label('coin'),
            func.sum(DwdVideoSnapshot.play_increment).label('play_inc'),
            func.avg(DwdVideoSnapshot.interaction_rate).label('avg_rate'),
            func.sum(DwdVideoSnapshot.comment_count).label('comments')
        ).filter(
            DwdVideoSnapshot.snapshot_date == stat_date
        ).group_by(DwdVideoSnapshot.category).all()

        return result

    def transform(self, data: List) -> List[Dict]:
        """格式化"""
        return [{
            "category": r.category or "未分类",
            "video_count": r.count,
            "total_play_count": r.play or 0,
            "avg_play_count": round(self._safe_divide(r.play or 0, r.count), 2),
            "play_increment": r.play_inc or 0,
            "total_like_count": r.like or 0,
            "total_coin_count": r.coin or 0,
            "avg_interaction_rate": round(r.avg_rate or 0, 6),
            "comment_count": r.comments or 0
        } for r in data]

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入每日分区统计表"""
        count = 0
        for item in data:
            category = item.pop("category")

            existing = self.db.query(DwsCategoryDaily).filter(
                DwsCategoryDaily.stat_date == stat_date,
                DwsCategoryDaily.category == category
            ).first()

            if existing:
                for key, value in item.items():
                    setattr(existing, key, value)
            else:
                cat_stats = DwsCategoryDaily(
                    stat_date=stat_date,
                    category=category,
                    **item
                )
                self.db.add(cat_stats)

            count += 1

        return count


class SentimentDailyETL(ETLTask):
    """
    每日情感统计ETL

    功能：预聚合情感分布
    数据流：dwd_comment_daily → dws_sentiment_daily
    """

    def extract(self, stat_date: date) -> Dict:
        """抽取评论情感数据"""
        # 全局统计
        global_result = self.db.query(
            DwdCommentDaily.sentiment_label,
            func.count(DwdCommentDaily.id).label('count'),
            func.avg(DwdCommentDaily.sentiment_score).label('avg_score')
        ).filter(
            DwdCommentDaily.stat_date == stat_date
        ).group_by(DwdCommentDaily.sentiment_label).all()

        # 分区统计
        category_result = self.db.query(
            DwdCommentDaily.category,
            DwdCommentDaily.sentiment_label,
            func.count(DwdCommentDaily.id).label('count'),
            func.avg(DwdCommentDaily.sentiment_score).label('avg_score')
        ).filter(
            DwdCommentDaily.stat_date == stat_date
        ).group_by(
            DwdCommentDaily.category,
            DwdCommentDaily.sentiment_label
        ).all()

        return {"global": global_result, "category": category_result}

    def transform(self, data: Dict) -> List[Dict]:
        """聚合情感分布"""
        result = []

        # 处理全局
        global_data = {
            "category": "all",
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "total": 0,
            "avg_score": 0.5
        }
        scores = []
        for r in data["global"]:
            if r.sentiment_label == "positive":
                global_data["positive"] = r.count
            elif r.sentiment_label == "neutral":
                global_data["neutral"] = r.count
            elif r.sentiment_label == "negative":
                global_data["negative"] = r.count
            global_data["total"] += r.count
            if r.avg_score:
                scores.append(r.avg_score * r.count)

        if global_data["total"] > 0 and scores:
            global_data["avg_score"] = sum(scores) / global_data["total"]
        result.append(global_data)

        # 处理分区
        category_dict = defaultdict(lambda: {
            "positive": 0, "neutral": 0, "negative": 0,
            "total": 0, "scores": []
        })

        for r in data["category"]:
            cat = r.category or "未分类"
            if r.sentiment_label == "positive":
                category_dict[cat]["positive"] = r.count
            elif r.sentiment_label == "neutral":
                category_dict[cat]["neutral"] = r.count
            elif r.sentiment_label == "negative":
                category_dict[cat]["negative"] = r.count
            category_dict[cat]["total"] += r.count
            if r.avg_score:
                category_dict[cat]["scores"].append(r.avg_score * r.count)

        for cat, cat_data in category_dict.items():
            avg_score = 0.5
            if cat_data["total"] > 0 and cat_data["scores"]:
                avg_score = sum(cat_data["scores"]) / cat_data["total"]
            result.append({
                "category": cat,
                "positive": cat_data["positive"],
                "neutral": cat_data["neutral"],
                "negative": cat_data["negative"],
                "total": cat_data["total"],
                "avg_score": avg_score
            })

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入每日情感统计表"""
        count = 0
        for item in data:
            category = item["category"]
            total = item["total"]

            existing = self.db.query(DwsSentimentDaily).filter(
                DwsSentimentDaily.stat_date == stat_date,
                DwsSentimentDaily.category == category
            ).first()

            sentiment_data = {
                "positive_count": item["positive"],
                "neutral_count": item["neutral"],
                "negative_count": item["negative"],
                "total_count": total,
                "positive_rate": round(self._safe_divide(item["positive"], total), 4),
                "neutral_rate": round(self._safe_divide(item["neutral"], total), 4),
                "negative_rate": round(self._safe_divide(item["negative"], total), 4),
                "avg_sentiment_score": round(item.get("avg_score", 0.5), 4)
            }

            if existing:
                for key, value in sentiment_data.items():
                    setattr(existing, key, value)
            else:
                sentiment = DwsSentimentDaily(
                    stat_date=stat_date,
                    category=category,
                    **sentiment_data
                )
                self.db.add(sentiment)

            count += 1

        return count


class VideoTrendETL(ETLTask):
    """
    视频热度趋势ETL

    功能：追踪单个视频的热度变化趋势
    数据流：dwd_video_snapshot → dws_video_trend
    """

    def __init__(self, db: Session, trend_days: int = 7):
        super().__init__(db)
        self.trend_days = trend_days

    def extract(self, stat_date: date) -> List:
        """抽取最近N天的视频快照"""
        start_date = stat_date - timedelta(days=self.trend_days)

        videos = self.db.query(
            DwdVideoSnapshot.video_id,
            DwdVideoSnapshot.bvid,
            DwdVideoSnapshot.snapshot_date,
            DwdVideoSnapshot.play_count,
            DwdVideoSnapshot.like_count,
            DwdVideoSnapshot.interaction_rate
        ).filter(
            DwdVideoSnapshot.snapshot_date >= start_date,
            DwdVideoSnapshot.snapshot_date <= stat_date
        ).order_by(
            DwdVideoSnapshot.video_id,
            DwdVideoSnapshot.snapshot_date
        ).all()

        return videos

    def transform(self, data: List) -> List[Dict]:
        """计算趋势指标"""
        # 按视频分组
        video_data = defaultdict(list)
        for r in data:
            video_data[r.video_id].append({
                "bvid": r.bvid,
                "date": r.snapshot_date,
                "play": r.play_count or 0,
                "like": r.like_count or 0,
                "rate": r.interaction_rate or 0
            })

        result = []
        for video_id, snapshots in video_data.items():
            if len(snapshots) < 2:
                continue

            # 排序
            snapshots.sort(key=lambda x: x["date"])
            first = snapshots[0]
            last = snapshots[-1]

            # 计算增长率
            play_trend = self._safe_divide(last["play"] - first["play"], first["play"])
            like_trend = self._safe_divide(last["like"] - first["like"], first["like"])

            # 综合热度分 = 播放增长 * 0.5 + 点赞增长 * 0.3 + 平均互动率 * 0.2
            avg_rate = sum(s["rate"] for s in snapshots) / len(snapshots)
            heat_score = play_trend * 0.5 + like_trend * 0.3 + avg_rate * 100 * 0.2

            result.append({
                "video_id": video_id,
                "bvid": last["bvid"],
                "play_trend": round(play_trend, 4),
                "like_trend": round(like_trend, 4),
                "heat_score": round(heat_score, 4)
            })

        # 计算排名
        result.sort(key=lambda x: x["heat_score"], reverse=True)
        for i, item in enumerate(result):
            item["rank_by_heat"] = i + 1

        result.sort(key=lambda x: x["play_trend"], reverse=True)
        for i, item in enumerate(result):
            item["rank_by_play"] = i + 1

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入视频热度趋势表"""
        count = 0
        for item in data:
            existing = self.db.query(DwsVideoTrend).filter(
                DwsVideoTrend.video_id == item["video_id"],
                DwsVideoTrend.trend_date == stat_date
            ).first()

            trend_data = {
                "play_trend": item["play_trend"],
                "like_trend": item["like_trend"],
                "heat_score": item["heat_score"],
                "rank_by_play": item["rank_by_play"],
                "rank_by_heat": item["rank_by_heat"]
            }

            if existing:
                for key, value in trend_data.items():
                    setattr(existing, key, value)
            else:
                trend = DwsVideoTrend(
                    video_id=item["video_id"],
                    bvid=item["bvid"],
                    trend_date=stat_date,
                    trend_days=self.trend_days,
                    **trend_data
                )
                self.db.add(trend)

            count += 1

        return count
