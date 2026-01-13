"""
统计分析API

包含两套接口：
1. 原始接口：直接查询原始表（/overview, /categories 等）
2. 数仓优化接口：查询预聚合表（/dw/overview, /dw/categories 等）
"""
from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Video, Comment, Keyword
from app.models.warehouse import (
    DwdVideoSnapshot,
    DwsStatsDaily,
    DwsCategoryDaily,
    DwsSentimentDaily,
    DwsVideoTrend,
)

router = APIRouter()


# ==================== 响应模型 ====================

class OverviewResponse(BaseModel):
    total_videos: int
    total_play_count: int
    total_like_count: int
    total_comment_count: int
    avg_play_count: float
    avg_like_count: float


class DwOverviewResponse(BaseModel):
    """数仓优化版总览响应"""
    stat_date: str
    total_videos: int
    total_play_count: int
    total_like_count: int
    total_comment_count: int
    avg_play_count: float
    avg_like_count: float
    new_videos: int
    new_comments: int
    play_increment: int


class CategoryStats(BaseModel):
    category: str
    count: int
    play_count: int


class DwCategoryStats(BaseModel):
    """数仓优化版分区统计"""
    category: str
    video_count: int
    total_play_count: int
    avg_play_count: float
    avg_interaction_rate: float


class KeywordItem(BaseModel):
    word: str
    frequency: int


class TrendPoint(BaseModel):
    date: str
    value: int


class SentimentStats(BaseModel):
    positive: int
    neutral: int
    negative: int


class DwSentimentStats(BaseModel):
    """数仓优化版情感统计"""
    positive: int
    neutral: int
    negative: int
    positive_rate: float
    avg_score: float


class VideoTrendItem(BaseModel):
    """视频热度趋势"""
    bvid: str
    heat_score: float
    play_trend: float
    like_trend: float
    rank_by_heat: int
    rank_by_play: int


class VideoHistoryPoint(BaseModel):
    """视频历史数据点"""
    date: str
    play_count: int
    like_count: int
    play_increment: int
    interaction_rate: float


# ==================== 原始接口（直接查询原始表） ====================

@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """获取总览统计数据（原始版本）"""
    query = db.query(Video)

    if start_date:
        query = query.filter(Video.publish_time >= start_date)
    if end_date:
        query = query.filter(Video.publish_time <= end_date)

    result = query.with_entities(
        func.count(Video.id).label('total'),
        func.sum(Video.play_count).label('play'),
        func.sum(Video.like_count).label('like'),
        func.sum(Video.comment_count).label('comment'),
        func.avg(Video.play_count).label('avg_play'),
        func.avg(Video.like_count).label('avg_like')
    ).first()

    return OverviewResponse(
        total_videos=result.total or 0,
        total_play_count=result.play or 0,
        total_like_count=result.like or 0,
        total_comment_count=result.comment or 0,
        avg_play_count=float(result.avg_play or 0),
        avg_like_count=float(result.avg_like or 0)
    )


@router.get("/categories", response_model=List[CategoryStats])
def get_category_stats(db: Session = Depends(get_db)):
    """获取分区统计（原始版本）"""
    result = db.query(
        Video.category,
        func.count(Video.id).label('count'),
        func.sum(Video.play_count).label('play_count')
    ).group_by(Video.category).all()

    return [
        CategoryStats(
            category=r.category or "未分类",
            count=r.count,
            play_count=r.play_count or 0
        ) for r in result
    ]


@router.get("/keywords", response_model=List[KeywordItem])
def get_keywords(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取热词数据"""
    query = db.query(Keyword)
    if category:
        query = query.filter(Keyword.category == category)

    keywords = query.order_by(Keyword.frequency.desc()).limit(limit).all()
    return [KeywordItem(word=k.word, frequency=k.frequency) for k in keywords]


@router.get("/trends", response_model=List[TrendPoint])
def get_trends(
    days: int = Query(7, ge=1, le=30),
    metric: str = Query("play_count", regex="^(play_count|like_count|video_count)$"),
    db: Session = Depends(get_db)
):
    """获取趋势数据（原始版本）"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 按日期分组统计
    if metric == "video_count":
        result = db.query(
            func.date(Video.publish_time).label('date'),
            func.count(Video.id).label('value')
        ).filter(
            Video.publish_time >= start_date
        ).group_by(func.date(Video.publish_time)).all()
    else:
        result = db.query(
            func.date(Video.publish_time).label('date'),
            func.sum(getattr(Video, metric)).label('value')
        ).filter(
            Video.publish_time >= start_date
        ).group_by(func.date(Video.publish_time)).all()

    return [TrendPoint(date=str(r.date), value=r.value or 0) for r in result]


@router.get("/sentiment", response_model=SentimentStats)
def get_sentiment(db: Session = Depends(get_db)):
    """获取情感分析统计（原始版本）"""
    positive = db.query(Comment).filter(Comment.sentiment_score >= 0.6).count()
    negative = db.query(Comment).filter(Comment.sentiment_score <= 0.4).count()
    neutral = db.query(Comment).filter(
        Comment.sentiment_score > 0.4,
        Comment.sentiment_score < 0.6
    ).count()

    return SentimentStats(positive=positive, neutral=neutral, negative=negative)


@router.get("/top-videos")
def get_top_videos(
    limit: int = Query(10, ge=1, le=50),
    order_by: str = Query("play_count"),
    db: Session = Depends(get_db)
):
    """获取热门视频榜单"""
    order_column = getattr(Video, order_by, Video.play_count)
    videos = db.query(Video).order_by(order_column.desc()).limit(limit).all()
    return videos


# ==================== 数仓优化接口（查询预聚合表） ====================

@router.get("/dw/overview", response_model=DwOverviewResponse)
def get_dw_overview(
    stat_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    获取总览统计数据（数仓优化版本）

    从 dws_stats_daily 表直接查询，响应时间 < 10ms
    """
    if stat_date is None:
        stat_date = date.today() - timedelta(days=1)

    stats = db.query(DwsStatsDaily).filter(
        DwsStatsDaily.stat_date == stat_date
    ).first()

    if not stats:
        return DwOverviewResponse(
            stat_date=str(stat_date),
            total_videos=0,
            total_play_count=0,
            total_like_count=0,
            total_comment_count=0,
            avg_play_count=0,
            avg_like_count=0,
            new_videos=0,
            new_comments=0,
            play_increment=0
        )

    return DwOverviewResponse(
        stat_date=str(stats.stat_date),
        total_videos=stats.total_videos,
        total_play_count=stats.total_play_count,
        total_like_count=stats.total_like_count,
        total_comment_count=stats.total_comments,
        avg_play_count=stats.avg_play_count,
        avg_like_count=stats.avg_like_count,
        new_videos=stats.new_videos,
        new_comments=stats.new_comments,
        play_increment=stats.play_increment
    )


@router.get("/dw/trends", response_model=List[TrendPoint])
def get_dw_trends(
    days: int = Query(7, ge=1, le=30),
    metric: str = Query("play_count"),
    db: Session = Depends(get_db)
):
    """
    获取趋势数据（数仓优化版本）

    从 dws_stats_daily 表范围查询，响应时间 < 20ms
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)

    stats = db.query(DwsStatsDaily).filter(
        DwsStatsDaily.stat_date >= start_date,
        DwsStatsDaily.stat_date <= end_date
    ).order_by(DwsStatsDaily.stat_date).all()

    metric_map = {
        "play_count": "total_play_count",
        "like_count": "total_like_count",
        "video_count": "total_videos",
        "play_increment": "play_increment",
        "new_videos": "new_videos"
    }

    attr = metric_map.get(metric, "total_play_count")

    return [
        TrendPoint(date=str(s.stat_date), value=getattr(s, attr, 0) or 0)
        for s in stats
    ]


@router.get("/dw/categories", response_model=List[DwCategoryStats])
def get_dw_category_stats(
    stat_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    获取分区统计（数仓优化版本）

    从 dws_category_daily 表直接查询，响应时间 < 10ms
    """
    if stat_date is None:
        stat_date = date.today() - timedelta(days=1)

    categories = db.query(DwsCategoryDaily).filter(
        DwsCategoryDaily.stat_date == stat_date
    ).all()

    return [
        DwCategoryStats(
            category=c.category,
            video_count=c.video_count,
            total_play_count=c.total_play_count,
            avg_play_count=c.avg_play_count,
            avg_interaction_rate=c.avg_interaction_rate
        )
        for c in categories
    ]


@router.get("/dw/sentiment", response_model=DwSentimentStats)
def get_dw_sentiment(
    stat_date: Optional[date] = None,
    category: str = "all",
    db: Session = Depends(get_db)
):
    """
    获取情感分析统计（数仓优化版本）

    从 dws_sentiment_daily 表直接查询，响应时间 < 5ms
    """
    if stat_date is None:
        stat_date = date.today() - timedelta(days=1)

    sentiment = db.query(DwsSentimentDaily).filter(
        DwsSentimentDaily.stat_date == stat_date,
        DwsSentimentDaily.category == category
    ).first()

    if not sentiment:
        return DwSentimentStats(
            positive=0,
            neutral=0,
            negative=0,
            positive_rate=0,
            avg_score=0.5
        )

    return DwSentimentStats(
        positive=sentiment.positive_count,
        neutral=sentiment.neutral_count,
        negative=sentiment.negative_count,
        positive_rate=sentiment.positive_rate,
        avg_score=sentiment.avg_sentiment_score
    )


@router.get("/dw/video-trends", response_model=List[VideoTrendItem])
def get_dw_video_trends(
    stat_date: Optional[date] = None,
    limit: int = Query(20, ge=1, le=100),
    order_by: str = Query("heat_score"),
    db: Session = Depends(get_db)
):
    """
    获取视频热度趋势排行

    从 dws_video_trend 表查询，响应时间 < 20ms
    """
    if stat_date is None:
        stat_date = date.today() - timedelta(days=1)

    # 确定排序字段
    if order_by == "heat_score":
        order_column = DwsVideoTrend.rank_by_heat
    else:
        order_column = DwsVideoTrend.rank_by_play

    trends = db.query(DwsVideoTrend).filter(
        DwsVideoTrend.trend_date == stat_date
    ).order_by(order_column).limit(limit).all()

    return [
        VideoTrendItem(
            bvid=t.bvid,
            heat_score=t.heat_score,
            play_trend=t.play_trend,
            like_trend=t.like_trend,
            rank_by_heat=t.rank_by_heat,
            rank_by_play=t.rank_by_play
        )
        for t in trends
    ]


@router.get("/dw/video/{bvid}/history", response_model=List[VideoHistoryPoint])
def get_dw_video_history(
    bvid: str,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    获取单个视频的历史趋势

    从 dwd_video_snapshot 表查询，支持最多90天历史
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    snapshots = db.query(DwdVideoSnapshot).filter(
        DwdVideoSnapshot.bvid == bvid,
        DwdVideoSnapshot.snapshot_date >= start_date
    ).order_by(DwdVideoSnapshot.snapshot_date).all()

    return [
        VideoHistoryPoint(
            date=str(s.snapshot_date),
            play_count=s.play_count or 0,
            like_count=s.like_count or 0,
            play_increment=s.play_increment or 0,
            interaction_rate=s.interaction_rate or 0
        )
        for s in snapshots
    ]
