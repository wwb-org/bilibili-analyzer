"""
DWD层ETL任务

包含：
- VideoSnapshotETL: 视频快照ETL
- CommentDailyETL: 评论每日增量ETL
"""
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.etl.base import ETLTask
from app.models.models import Video, Comment
from app.models.warehouse import DwdVideoSnapshot, DwdCommentDaily


class VideoSnapshotETL(ETLTask):
    """
    视频快照ETL

    功能：每日执行，保存视频统计数据快照
    数据流：videos → dwd_video_snapshot
    """

    def extract(self, stat_date: date) -> List[Video]:
        """从videos表抽取当前所有视频数据"""
        videos = self.db.query(Video).all()
        return videos

    def transform(self, videos: List[Video]) -> List[Dict]:
        """计算衍生指标"""
        result = []
        for video in videos:
            play = video.play_count or 0

            # 计算互动率：(点赞+投币+分享+收藏) / 播放量
            interaction = (
                (video.like_count or 0) +
                (video.coin_count or 0) +
                (video.share_count or 0) +
                (video.favorite_count or 0)
            )
            interaction_rate = self._safe_divide(interaction, play)
            like_rate = self._safe_divide(video.like_count or 0, play)

            result.append({
                "video": video,
                "interaction_rate": round(interaction_rate, 6),
                "like_rate": round(like_rate, 6)
            })

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入快照表，计算增量"""
        yesterday = stat_date - timedelta(days=1)
        count = 0

        for item in data:
            video = item["video"]

            # 查询昨日快照，计算增量
            yesterday_snapshot = self.db.query(DwdVideoSnapshot).filter(
                DwdVideoSnapshot.video_id == video.id,
                DwdVideoSnapshot.snapshot_date == yesterday
            ).first()

            play_increment = 0
            like_increment = 0
            comment_increment = 0

            if yesterday_snapshot:
                play_increment = (video.play_count or 0) - (yesterday_snapshot.play_count or 0)
                like_increment = (video.like_count or 0) - (yesterday_snapshot.like_count or 0)
                comment_increment = (video.comment_count or 0) - (yesterday_snapshot.comment_count or 0)

            # 检查今日是否已存在
            existing = self.db.query(DwdVideoSnapshot).filter(
                DwdVideoSnapshot.video_id == video.id,
                DwdVideoSnapshot.snapshot_date == stat_date
            ).first()

            if existing:
                # 更新已存在的快照
                existing.play_count = video.play_count
                existing.like_count = video.like_count
                existing.coin_count = video.coin_count
                existing.share_count = video.share_count
                existing.favorite_count = video.favorite_count
                existing.danmaku_count = video.danmaku_count
                existing.comment_count = video.comment_count
                existing.interaction_rate = item["interaction_rate"]
                existing.like_rate = item["like_rate"]
                existing.play_increment = play_increment
                existing.like_increment = like_increment
                existing.comment_increment = comment_increment
            else:
                # 新增快照
                snapshot = DwdVideoSnapshot(
                    snapshot_date=stat_date,
                    video_id=video.id,
                    bvid=video.bvid,
                    title=video.title,
                    category=video.category,
                    author_id=video.author_id,
                    author_name=video.author_name,
                    play_count=video.play_count,
                    like_count=video.like_count,
                    coin_count=video.coin_count,
                    share_count=video.share_count,
                    favorite_count=video.favorite_count,
                    danmaku_count=video.danmaku_count,
                    comment_count=video.comment_count,
                    interaction_rate=item["interaction_rate"],
                    like_rate=item["like_rate"],
                    play_increment=play_increment,
                    like_increment=like_increment,
                    comment_increment=comment_increment,
                    publish_time=video.publish_time,
                    duration=video.duration
                )
                self.db.add(snapshot)

            count += 1

        return count


class CommentDailyETL(ETLTask):
    """
    评论每日增量ETL

    功能：记录每日新增评论及其情感分析结果
    数据流：comments → dwd_comment_daily
    """

    def extract(self, stat_date: date) -> List[Comment]:
        """抽取当日新增评论"""
        start_dt = datetime.combine(stat_date, datetime.min.time())
        end_dt = datetime.combine(stat_date, datetime.max.time())

        comments = self.db.query(Comment).filter(
            Comment.created_at >= start_dt,
            Comment.created_at <= end_dt
        ).all()

        return comments

    def transform(self, comments: List[Comment]) -> List[Dict]:
        """转换情感标签"""
        result = []
        for comment in comments:
            score = comment.sentiment_score or 0.5

            # 情感分类阈值
            if score >= 0.6:
                label = "positive"
            elif score <= 0.4:
                label = "negative"
            else:
                label = "neutral"

            result.append({
                "comment": comment,
                "sentiment_label": label
            })

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入评论每日增量表"""
        count = 0

        for item in data:
            comment = item["comment"]

            # 查询视频分区
            video = self.db.query(Video).filter(Video.id == comment.video_id).first()

            # 检查是否已存在
            existing = self.db.query(DwdCommentDaily).filter(
                DwdCommentDaily.comment_id == comment.id,
                DwdCommentDaily.stat_date == stat_date
            ).first()

            if not existing:
                daily = DwdCommentDaily(
                    stat_date=stat_date,
                    comment_id=comment.id,
                    rpid=comment.rpid,
                    video_id=comment.video_id,
                    bvid=video.bvid if video else None,
                    category=video.category if video else None,
                    content=comment.content,
                    user_name=comment.user_name,
                    sentiment_score=comment.sentiment_score,
                    sentiment_label=item["sentiment_label"],
                    like_count=comment.like_count
                )
                self.db.add(daily)
                count += 1

        return count
