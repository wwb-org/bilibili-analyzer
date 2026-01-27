"""
视频数据API
"""
from typing import List, Optional
from datetime import datetime
from collections import Counter
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import jieba

from app.core.database import get_db
from app.models import Video, Comment, Danmaku

router = APIRouter()


class VideoResponse(BaseModel):
    id: int
    bvid: str
    title: str
    description: Optional[str] = None
    category: Optional[str]
    author_name: Optional[str]
    author_face: Optional[str] = None
    play_count: int
    like_count: int
    coin_count: int
    share_count: int
    favorite_count: int = 0
    danmaku_count: int
    comment_count: int = 0
    duration: Optional[int] = None
    publish_time: Optional[datetime]
    cover_url: Optional[str]

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    total: int
    items: List[VideoResponse]


@router.get("", response_model=VideoListResponse)
def get_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    order_by: str = Query("play_count", regex="^(play_count|like_count|publish_time)$"),
    db: Session = Depends(get_db)
):
    """获取视频列表（支持分页、筛选、排序）"""
    query = db.query(Video)

    # 筛选条件
    if category:
        query = query.filter(Video.category == category)
    if keyword:
        query = query.filter(Video.title.contains(keyword))
    if start_date:
        query = query.filter(Video.publish_time >= start_date)
    if end_date:
        query = query.filter(Video.publish_time <= end_date)

    # 总数
    total = query.count()

    # 排序
    order_column = getattr(Video, order_by)
    query = query.order_by(order_column.desc())

    # 分页
    offset = (page - 1) * page_size
    videos = query.offset(offset).limit(page_size).all()

    return {"total": total, "items": videos}


# ==================== 统计接口（需放在 /{bvid} 之前）====================

# 停用词列表
STOPWORDS = set([
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '这', '那', '吗', '什么', '他', '她', '它', '们', '这个', '那个', '啊', '呢',
    '吧', '哦', '嗯', '呀', '哈', '哈哈', '哈哈哈', '嘿', '喂', '诶', '哎',
    '可以', '怎么', '为什么', '真的', '其实', '但是', '还是', '如果', '因为',
    '所以', '或者', '而且', '虽然', '然后', '感觉', '觉得', '知道', '应该',
    '真是', '太', '最', '更', '非常', '比较', '已经', '还', '又', '再', '只',
    '没', '被', '把', '给', '让', '从', '向', '对', '于', '与', '等', '能',
    '可能', '可', '想', '来', '去', '过', '得', '起', '完', '出', '回', '下',
])


class VideoStatsResponse(BaseModel):
    """视频统计响应"""
    total_videos: int
    total_play_count: int
    avg_play_count: float
    avg_interaction_rate: float
    sentiment_distribution: dict
    category_distribution: List[dict]


class InteractionRates(BaseModel):
    """互动率"""
    like_rate: float
    coin_rate: float
    favorite_rate: float
    share_rate: float


class SentimentStats(BaseModel):
    """情感统计"""
    positive: int
    neutral: int
    negative: int
    avg_score: float


class KeywordItem(BaseModel):
    """关键词项"""
    word: str
    count: int


class VideoAnalysisResponse(BaseModel):
    """视频分析响应"""
    interaction_rates: InteractionRates
    sentiment_stats: SentimentStats
    danmaku_keywords: List[KeywordItem]


class VideoCompareItem(BaseModel):
    """视频对比项"""
    bvid: str
    title: str
    cover_url: Optional[str]
    play_count: int
    like_count: int
    coin_count: int
    favorite_count: int
    share_count: int
    like_rate: float
    coin_rate: float
    favorite_rate: float
    share_rate: float
    sentiment: dict


class VideoCompareRequest(BaseModel):
    """视频对比请求"""
    bvids: List[str]


class VideoCompareResponse(BaseModel):
    """视频对比响应"""
    videos: List[VideoCompareItem]


@router.get("/stats", response_model=VideoStatsResponse)
def get_videos_stats(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取视频统计数据（根据筛选条件）"""
    query = db.query(Video)

    # 筛选条件
    if category:
        query = query.filter(Video.category == category)
    if keyword:
        query = query.filter(Video.title.contains(keyword))

    # 获取视频列表
    videos = query.all()
    total_videos = len(videos)

    if total_videos == 0:
        return VideoStatsResponse(
            total_videos=0,
            total_play_count=0,
            avg_play_count=0,
            avg_interaction_rate=0,
            sentiment_distribution={"positive": 0, "neutral": 0, "negative": 0},
            category_distribution=[]
        )

    # 统计计算
    total_play = sum(v.play_count or 0 for v in videos)
    avg_play = total_play / total_videos

    # 计算平均互动率
    interaction_rates = []
    for v in videos:
        if v.play_count and v.play_count > 0:
            rate = ((v.like_count or 0) + (v.coin_count or 0) +
                    (v.favorite_count or 0) + (v.share_count or 0)) / v.play_count * 100
            interaction_rates.append(rate)
    avg_interaction_rate = sum(interaction_rates) / len(interaction_rates) if interaction_rates else 0

    # 情感分布（统计所有视频的评论）
    video_ids = [v.id for v in videos]
    positive_count = db.query(Comment).filter(
        Comment.video_id.in_(video_ids),
        Comment.sentiment_score > 0.6
    ).count()
    negative_count = db.query(Comment).filter(
        Comment.video_id.in_(video_ids),
        Comment.sentiment_score < 0.4
    ).count()
    neutral_count = db.query(Comment).filter(
        Comment.video_id.in_(video_ids),
        Comment.sentiment_score >= 0.4,
        Comment.sentiment_score <= 0.6
    ).count()

    # 分区分布
    category_stats = db.query(
        Video.category,
        func.count(Video.id).label('count')
    ).filter(Video.id.in_(video_ids)).group_by(Video.category).all()

    category_distribution = [
        {"category": c.category or "未分类", "count": c.count}
        for c in category_stats
    ]

    return VideoStatsResponse(
        total_videos=total_videos,
        total_play_count=total_play,
        avg_play_count=round(avg_play, 2),
        avg_interaction_rate=round(avg_interaction_rate, 2),
        sentiment_distribution={
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count
        },
        category_distribution=category_distribution
    )


@router.post("/compare", response_model=VideoCompareResponse)
def compare_videos(request: VideoCompareRequest, db: Session = Depends(get_db)):
    """多视频对比"""
    if len(request.bvids) > 5:
        raise HTTPException(status_code=400, detail="最多支持5个视频对比")

    result = []
    for bvid in request.bvids:
        video = db.query(Video).filter(Video.bvid == bvid).first()
        if not video:
            continue

        # 计算互动率
        play_count = video.play_count or 1
        like_rate = ((video.like_count or 0) / play_count) * 100
        coin_rate = ((video.coin_count or 0) / play_count) * 100
        favorite_rate = ((video.favorite_count or 0) / play_count) * 100
        share_rate = ((video.share_count or 0) / play_count) * 100

        # 评论情感统计
        comments = db.query(Comment).filter(Comment.video_id == video.id).all()
        total_comments = len(comments)
        positive = sum(1 for c in comments if c.sentiment_score and c.sentiment_score > 0.6)
        negative = sum(1 for c in comments if c.sentiment_score and c.sentiment_score < 0.4)
        neutral = total_comments - positive - negative

        # 计算百分比
        if total_comments > 0:
            positive_pct = round(positive / total_comments * 100, 1)
            neutral_pct = round(neutral / total_comments * 100, 1)
            negative_pct = round(negative / total_comments * 100, 1)
        else:
            positive_pct = neutral_pct = negative_pct = 0

        result.append(VideoCompareItem(
            bvid=video.bvid,
            title=video.title,
            cover_url=video.cover_url,
            play_count=video.play_count or 0,
            like_count=video.like_count or 0,
            coin_count=video.coin_count or 0,
            favorite_count=video.favorite_count or 0,
            share_count=video.share_count or 0,
            like_rate=round(like_rate, 2),
            coin_rate=round(coin_rate, 2),
            favorite_rate=round(favorite_rate, 2),
            share_rate=round(share_rate, 2),
            sentiment={
                "positive": positive_pct,
                "neutral": neutral_pct,
                "negative": negative_pct
            }
        ))

    return VideoCompareResponse(videos=result)


# ==================== 详情接口 ====================

@router.get("/{bvid}", response_model=VideoResponse)
def get_video_detail(bvid: str, db: Session = Depends(get_db)):
    """获取视频详情"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return video


class CommentResponse(BaseModel):
    id: int
    rpid: Optional[int]
    content: str
    user_name: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    like_count: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    total: int
    items: List[CommentResponse]


def get_sentiment_label(score: Optional[float]) -> Optional[str]:
    """根据情感分数计算情感标签"""
    if score is None:
        return None
    if score > 0.6:
        return "positive"
    elif score < 0.4:
        return "negative"
    else:
        return "neutral"


@router.get("/{bvid}/comments", response_model=CommentListResponse)
def get_video_comments(
    bvid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(like_count|created_at)$"),
    db: Session = Depends(get_db)
):
    """获取视频评论列表"""
    # 查询视频
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 查询评论
    query = db.query(Comment).filter(Comment.video_id == video.id)

    # 总数
    total = query.count()

    # 排序
    order_column = getattr(Comment, sort_by)
    query = query.order_by(order_column.desc())

    # 分页
    offset = (page - 1) * page_size
    comments = query.offset(offset).limit(page_size).all()

    # 添加情感标签
    items = []
    for comment in comments:
        item = CommentResponse(
            id=comment.id,
            rpid=comment.rpid,
            content=comment.content,
            user_name=comment.user_name,
            sentiment_score=comment.sentiment_score,
            sentiment_label=get_sentiment_label(comment.sentiment_score),
            like_count=comment.like_count or 0,
            created_at=comment.created_at
        )
        items.append(item)

    return {"total": total, "items": items}


class DanmakuResponse(BaseModel):
    id: int
    content: str
    send_time: Optional[float]
    color: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class DanmakuListResponse(BaseModel):
    total: int
    items: List[DanmakuResponse]


@router.get("/{bvid}/danmakus", response_model=DanmakuListResponse)
def get_video_danmakus(
    bvid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取视频弹幕列表"""
    # 查询视频
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 查询弹幕
    query = db.query(Danmaku).filter(Danmaku.video_id == video.id)

    # 总数
    total = query.count()

    # 按视频时间点排序
    query = query.order_by(Danmaku.send_time.asc())

    # 分页
    offset = (page - 1) * page_size
    danmakus = query.offset(offset).limit(page_size).all()

    return {"total": total, "items": danmakus}


@router.get("/{bvid}/analysis", response_model=VideoAnalysisResponse)
def get_video_analysis(bvid: str, db: Session = Depends(get_db)):
    """获取单个视频的分析数据"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    # 计算互动率
    play_count = video.play_count or 1  # 避免除以0
    like_rate = ((video.like_count or 0) / play_count) * 100
    coin_rate = ((video.coin_count or 0) / play_count) * 100
    favorite_rate = ((video.favorite_count or 0) / play_count) * 100
    share_rate = ((video.share_count or 0) / play_count) * 100

    # 评论情感统计
    comments = db.query(Comment).filter(Comment.video_id == video.id).all()
    positive = sum(1 for c in comments if c.sentiment_score and c.sentiment_score > 0.6)
    negative = sum(1 for c in comments if c.sentiment_score and c.sentiment_score < 0.4)
    neutral = len(comments) - positive - negative

    scores = [c.sentiment_score for c in comments if c.sentiment_score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.5

    # 弹幕关键词提取
    danmakus = db.query(Danmaku.content).filter(Danmaku.video_id == video.id).all()
    all_words = []
    for d in danmakus:
        if d.content:
            words = jieba.cut(d.content)
            for word in words:
                word = word.strip()
                if len(word) >= 2 and word not in STOPWORDS:
                    all_words.append(word)

    word_counts = Counter(all_words)
    top_keywords = [
        KeywordItem(word=word, count=count)
        for word, count in word_counts.most_common(30)
    ]

    return VideoAnalysisResponse(
        interaction_rates=InteractionRates(
            like_rate=round(like_rate, 2),
            coin_rate=round(coin_rate, 2),
            favorite_rate=round(favorite_rate, 2),
            share_rate=round(share_rate, 2)
        ),
        sentiment_stats=SentimentStats(
            positive=positive,
            neutral=neutral,
            negative=negative,
            avg_score=round(avg_score, 3)
        ),
        danmaku_keywords=top_keywords
    )
