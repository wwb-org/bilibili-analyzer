"""
统计分析API
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Video, Comment, Keyword

router = APIRouter()


class OverviewResponse(BaseModel):
    total_videos: int
    total_play_count: int
    total_like_count: int
    total_comment_count: int
    avg_play_count: float
    avg_like_count: float


class CategoryStats(BaseModel):
    category: str
    count: int
    play_count: int


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


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """获取总览统计数据"""
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
    """获取分区统计"""
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
    """获取趋势数据"""
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
    """获取情感分析统计"""
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
