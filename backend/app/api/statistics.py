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
from sqlalchemy import func, case
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Video, Comment, Keyword
from app.models.warehouse import (
    DwdVideoSnapshot,
    DwdKeywordDaily,
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
    comment_count: int = 0


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
    title: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
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
    """获取热词数据（优先从DWD层查询）"""
    # 优先从 dwd_keyword_daily 查询（有数据）
    try:
        latest_date = db.query(func.max(DwdKeywordDaily.stat_date)).scalar()
        if latest_date:
            query = db.query(
                DwdKeywordDaily.word,
                func.sum(DwdKeywordDaily.frequency).label("total_freq")
            ).filter(DwdKeywordDaily.stat_date == latest_date)
            if category:
                query = query.filter(DwdKeywordDaily.category == category)
            rows = query.group_by(DwdKeywordDaily.word).order_by(
                func.sum(DwdKeywordDaily.frequency).desc()
            ).limit(limit).all()
            if rows:
                return [KeywordItem(word=r.word, frequency=r.total_freq) for r in rows]
    except Exception:
        pass

    # 降级：从旧 keywords 表查询
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
        "new_videos": "new_videos",
        "new_comments": "new_comments",
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
            avg_interaction_rate=c.avg_interaction_rate,
            comment_count=c.comment_count or 0,
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

    从 dws_video_trend 表查询，自动回退到最新有数据的日期。
    若趋势表为空，降级返回播放量 TOP N 的视频。
    """
    if stat_date is None:
        # 优先取最新有数据的日期，避免死写"昨天"导致空结果
        latest = db.query(func.max(DwsVideoTrend.trend_date)).scalar()
        stat_date = latest if latest else (date.today() - timedelta(days=1))

    # 确定排序字段
    order_column = DwsVideoTrend.rank_by_heat if order_by == "heat_score" else DwsVideoTrend.rank_by_play

    trends = db.query(DwsVideoTrend, Video).outerjoin(
        Video, DwsVideoTrend.bvid == Video.bvid
    ).filter(
        DwsVideoTrend.trend_date == stat_date
    ).order_by(order_column).limit(limit).all()

    # 降级：趋势表无数据时返回播放量 TOP N 视频，play_trend 标为 0
    if not trends:
        videos = db.query(Video).filter(
            Video.play_count > 0
        ).order_by(Video.play_count.desc()).limit(limit).all()
        return [
            VideoTrendItem(
                bvid=v.bvid,
                title=v.title[:30] if v.title else v.bvid,
                category=v.category,
                cover_url=v.cover_url,
                heat_score=0.0,
                play_trend=0.0,
                like_trend=0.0,
                rank_by_heat=i + 1,
                rank_by_play=i + 1,
            )
            for i, v in enumerate(videos)
        ]

    return [
        VideoTrendItem(
            bvid=t.bvid,
            title=v.title[:30] if v and v.title else t.bvid,
            category=v.category if v else None,
            cover_url=v.cover_url if v else None,
            heat_score=t.heat_score,
            play_trend=t.play_trend,
            like_trend=t.like_trend,
            rank_by_heat=t.rank_by_heat,
            rank_by_play=t.rank_by_play,
        )
        for t, v in trends
    ]


@router.get("/crawl-trends")
def get_crawl_trends(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """
    按采集时间统计每日视频数和总播放量（不依赖 ETL）

    不限定日期下限，取全部采集记录按天聚合后返回最近 days 天的数据点。
    只要有爬取数据即可展示，无需等待 ETL。
    """
    # 优先用 created_at（采集时间），fallback 到 publish_time（发布时间）
    date_expr = func.date(func.coalesce(Video.created_at, Video.publish_time))

    rows = db.query(
        date_expr.label('date'),
        func.count(Video.id).label('video_count'),
        func.sum(Video.play_count).label('total_play'),
    ).filter(
        func.coalesce(Video.created_at, Video.publish_time) != None,
    ).group_by(date_expr).order_by(date_expr).all()

    data = [
        {
            'date': str(r.date),
            'video_count': r.video_count,
            'total_play': int(r.total_play or 0),
        }
        for r in rows
        if r.date is not None
    ]
    # 只取最后 days 个数据点
    return {'data': data[-days:]}


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


# ==================== 特色可视化接口 ====================

@router.get("/publish-heatmap")
def get_publish_heatmap(db: Session = Depends(get_db)):
    """
    发布时段热力图
    返回每个 (星期, 小时) 组合的视频数量，用于绘制 7×24 热力矩阵
    """
    rows = db.query(
        func.dayofweek(Video.publish_time).label('dow'),
        func.hour(Video.publish_time).label('hour'),
        func.count(Video.id).label('cnt')
    ).filter(Video.publish_time != None).group_by('dow', 'hour').all()

    # MySQL DAYOFWEEK: 1=Sunday...7=Saturday, 转换为 0=Mon...6=Sun
    dow_map = {1: 6, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5}
    data = [
        {'weekday': dow_map.get(r.dow, 0), 'hour': r.hour, 'count': r.cnt}
        for r in rows
    ]
    return {'data': data}


@router.get("/video-scatter")
def get_video_scatter(
    limit: int = Query(300, ge=50, le=500),
    db: Session = Depends(get_db)
):
    """
    视频生态散点数据
    返回视频的互动率、播放量、弹幕数、分区，用于气泡散点图
    """
    videos = db.query(Video).filter(
        Video.play_count > 1000,
        Video.category != None
    ).order_by(Video.play_count.desc()).limit(limit).all()

    result = []
    for v in videos:
        if not v.play_count:
            continue
        interaction = round(
            ((v.like_count or 0) + (v.coin_count or 0) + (v.favorite_count or 0))
            / v.play_count * 100, 3
        )
        result.append({
            'bvid': v.bvid,
            'title': v.title[:30] if v.title else '',
            'category': v.category or '其他',
            'play_count': v.play_count,
            'interaction_rate': interaction,
            'danmaku_count': v.danmaku_count or 0,
            'comment_count': v.comment_count or 0,
            'duration': round((v.duration or 0) / 60, 1),
        })
    return {'videos': result}


# ==================== 新增特色分析接口 ====================

@router.get("/lifecycle")
def get_lifecycle(db: Session = Depends(get_db)):
    """
    视频生命周期分析

    按发布后天数聚合平均播放量，揭示视频热度随时间的衰减规律
    """
    rows = db.query(
        func.datediff(func.now(), Video.publish_time).label('age_days'),
        func.avg(Video.play_count).label('avg_play'),
        func.count(Video.id).label('video_count'),
    ).filter(
        Video.publish_time != None,
        Video.play_count > 1000,
        func.datediff(func.now(), Video.publish_time).between(0, 30),
    ).group_by('age_days').order_by('age_days').all()

    return {
        'data': [
            {
                'day': int(r.age_days),
                'avg_play': round(float(r.avg_play or 0)),
                'video_count': r.video_count,
            }
            for r in rows if r.age_days is not None
        ]
    }


@router.get("/opportunities")
def get_opportunities(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    内容机会发现

    找出高互动低播放的潜力视频（播放量低于均值50%但互动率高）
    """
    avg_play = db.query(func.avg(Video.play_count)).filter(
        Video.play_count > 0
    ).scalar() or 0
    avg_play = float(avg_play)

    videos = db.query(Video).filter(
        Video.play_count > 500,
        Video.play_count < avg_play * 0.5,
        Video.like_count > 0,
        Video.category != None,
    ).order_by(
        ((Video.like_count + Video.coin_count + Video.favorite_count) / Video.play_count).desc()
    ).limit(limit).all()

    result = []
    for v in videos:
        if not v.play_count:
            continue
        interaction = round(
            ((v.like_count or 0) + (v.coin_count or 0) + (v.favorite_count or 0))
            / v.play_count * 100, 2
        )
        result.append({
            'bvid': v.bvid,
            'title': v.title[:40] if v.title else '',
            'category': v.category or '其他',
            'play_count': v.play_count,
            'interaction_rate': interaction,
            'comment_count': v.comment_count or 0,
            'cover_url': v.cover_url,
        })

    return {'videos': result, 'avg_play': round(avg_play)}


@router.get("/author-ranking")
def get_author_ranking(
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    UP主影响力排行榜

    综合评分公式：播放量×0.5 + 点赞数×0.3 + 评论数×0.2
    """
    rows = db.query(
        Video.author_name,
        Video.author_id,
        func.count(Video.id).label('video_count'),
        func.sum(Video.play_count).label('total_play'),
        func.sum(Video.like_count).label('total_like'),
        func.sum(Video.comment_count).label('total_comment'),
        func.avg(Video.play_count).label('avg_play'),
    ).filter(
        Video.author_id != None,
        Video.author_name != None,
        Video.play_count > 0,
    ).group_by(Video.author_id, Video.author_name).all()

    results = []
    for r in rows:
        total_play = int(r.total_play or 0)
        total_like = int(r.total_like or 0)
        total_comment = int(r.total_comment or 0)
        score = total_play * 0.5 + total_like * 0.3 + total_comment * 0.2
        results.append({
            'author_name': r.author_name,
            'author_id': r.author_id,
            'video_count': r.video_count,
            'total_play': total_play,
            'total_like': total_like,
            'total_comment': total_comment,
            'avg_play': round(float(r.avg_play or 0)),
            'influence_score': round(score),
        })

    results.sort(key=lambda x: x['influence_score'], reverse=True)
    return {'authors': results[:limit]}


@router.get("/dw/sentiment-trends")
def get_dw_sentiment_trends(
    days: int = Query(14, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    情感趋势数据（多日）

    从 dws_sentiment_daily 查询多日情感分布变化，用于趋势折线图
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    sentiments = db.query(DwsSentimentDaily).filter(
        DwsSentimentDaily.stat_date >= start_date,
        DwsSentimentDaily.stat_date <= end_date,
        DwsSentimentDaily.category == "all",
    ).order_by(DwsSentimentDaily.stat_date).all()

    return {
        'data': [
            {
                'date': str(s.stat_date),
                'positive': s.positive_count,
                'neutral': s.neutral_count,
                'negative': s.negative_count,
                'positive_rate': round((s.positive_rate or 0) * 100, 1),
            }
            for s in sentiments
        ]
    }
