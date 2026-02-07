"""
评论分析 API
"""
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional
import csv
import io

import jieba
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Comment, Video
from app.services.emotion import EMOTION_LABELS, EmotionAnalyzer
from app.services.nlp import NLPAnalyzer

router = APIRouter()

# 使用统一停用词
STOPWORDS = NLPAnalyzer.STOP_WORDS
EMOTION_QUERY_REGEX = (
    "^(admiration|amusement|anger|annoyance|approval|caring|confusion|"
    "curiosity|desire|disappointment|disapproval|disgust|embarrassment|"
    "excitement|fear|gratitude|grief|joy|love|nervousness|optimism|"
    "pride|realization|relief|remorse|sadness|surprise|neutral)$"
)


def get_sentiment_label(score: Optional[float]) -> Optional[str]:
    """根据情感分数计算情感标签"""
    if score is None:
        return None
    if score > 0.6:
        return "positive"
    if score < 0.4:
        return "negative"
    return "neutral"


def get_dominant_sentiment(positive: int, neutral: int, negative: int) -> str:
    """获取主导情感类型"""
    if positive >= neutral and positive >= negative:
        return "positive"
    if negative >= neutral and negative >= positive:
        return "negative"
    return "neutral"


def apply_sentiment_filter(query, sentiment: Optional[str]):
    if sentiment == "positive":
        return query.filter(Comment.sentiment_score > 0.6)
    if sentiment == "negative":
        return query.filter(Comment.sentiment_score < 0.4)
    if sentiment == "neutral":
        return query.filter(Comment.sentiment_score >= 0.4, Comment.sentiment_score <= 0.6)
    return query


def apply_emotion_filter(query, emotion: Optional[str]):
    if emotion:
        return query.filter(Comment.emotion_label == emotion)
    return query


def normalize_emotion_scores(raw_scores: Optional[dict]) -> Dict[str, float]:
    scores = {label: 0.0 for label in EMOTION_LABELS}
    if not isinstance(raw_scores, dict):
        return scores
    for key, value in raw_scores.items():
        label = EmotionAnalyzer.normalize_emotion_label(str(key))
        if not label:
            continue
        try:
            scores[label] = float(value)
        except (TypeError, ValueError):
            continue
    return scores


def build_emotion_distribution(comments: List[Comment], total_count: int) -> Dict[str, Dict]:
    counts = {label: 0 for label in EMOTION_LABELS}
    for comment in comments:
        label = EmotionAnalyzer.normalize_emotion_label(comment.emotion_label or "")
        if not label:
            sentiment = get_sentiment_label(getattr(comment, "sentiment_score", None))
            if sentiment == "positive":
                label = "joy"
            elif sentiment == "negative":
                label = "anger"
            else:
                label = "neutral"
        counts[label] += 1

    rates = {
        key: round((value / total_count * 100), 1) if total_count else 0.0
        for key, value in counts.items()
    }

    dominant = max(counts, key=counts.get) if total_count > 0 else None
    return {"counts": counts, "rates": rates, "dominant": dominant}


# ==================== 响应模型 ====================

class SentimentSummary(BaseModel):
    """情感摘要"""
    positive: int
    neutral: int
    negative: int
    dominant: str


class EmotionDistribution(BaseModel):
    """细粒度情绪分布"""
    counts: Dict[str, int]
    rates: Dict[str, float]
    dominant: Optional[str] = None


class VideoWithCommentSummary(BaseModel):
    """带评论摘要的视频"""
    bvid: str
    title: str
    cover_url: Optional[str]
    category: Optional[str]
    author_name: Optional[str]
    comment_count: int
    sentiment_summary: SentimentSummary


class VideoListWithCommentsResponse(BaseModel):
    """视频列表响应（含评论摘要）"""
    total: int
    items: List[VideoWithCommentSummary]


class CommentStatsResponse(BaseModel):
    """评论统计响应"""
    total_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    positive_rate: float
    neutral_rate: float
    negative_rate: float
    avg_sentiment_score: float
    avg_like_count: float
    emotion_distribution: EmotionDistribution = Field(default_factory=lambda: EmotionDistribution(
        counts={label: 0 for label in EMOTION_LABELS},
        rates={label: 0.0 for label in EMOTION_LABELS},
        dominant=None,
    ))


class CommentItem(BaseModel):
    """评论项"""
    id: int
    rpid: Optional[int]
    content: str
    user_name: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    emotion_label: Optional[str]
    emotion_scores: Optional[Dict[str, float]]
    like_count: int
    created_at: Optional[datetime]


class CommentListResponse(BaseModel):
    """评论列表响应"""
    total: int
    items: List[CommentItem]


class WordcloudItem(BaseModel):
    """词云项"""
    name: str
    value: int
    sentiment: Optional[str] = None
    emotion: Optional[str] = None


class WordcloudResponse(BaseModel):
    """词云响应"""
    words: List[WordcloudItem]


class TopCommentItem(BaseModel):
    """高赞评论项"""
    id: int
    content: str
    user_name: Optional[str]
    sentiment_label: Optional[str]
    emotion_label: Optional[str]
    like_count: int


class TopCommentsResponse(BaseModel):
    """高赞评论响应"""
    items: List[TopCommentItem]


class CompareVideoItem(BaseModel):
    """对比视频项"""
    bvid: str
    title: str
    cover_url: Optional[str]
    comment_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    positive_rate: float
    neutral_rate: float
    negative_rate: float
    avg_sentiment_score: float
    avg_like_count: float
    top_keywords: List[WordcloudItem]


class CompareRequest(BaseModel):
    """对比请求"""
    bvids: List[str]


class CompareResponse(BaseModel):
    """对比响应"""
    videos: List[CompareVideoItem]


# ==================== API接口 ====================

@router.get("/videos", response_model=VideoListWithCommentsResponse)
def get_videos_with_comment_summary(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    order_by: str = Query("comment_count", regex="^(comment_count|positive_count|negative_count)$"),
    db: Session = Depends(get_db),
):
    """获取视频列表（含评论统计摘要）"""
    query = db.query(Video)

    if category:
        query = query.filter(Video.category == category)
    if keyword:
        query = query.filter(Video.title.contains(keyword))

    query = query.filter(Video.comment_count > 0)
    total = query.count()

    if order_by == "comment_count":
        query = query.order_by(Video.comment_count.desc())
    elif order_by == "positive_count":
        subq = db.query(
            Comment.video_id,
            func.count(Comment.id).label("cnt"),
        ).filter(
            Comment.sentiment_score > 0.6,
        ).group_by(Comment.video_id).subquery()
        query = query.outerjoin(
            subq,
            Video.id == subq.c.video_id,
        ).order_by(
            func.coalesce(subq.c.cnt, 0).desc(),
            Video.comment_count.desc(),
        )
    elif order_by == "negative_count":
        subq = db.query(
            Comment.video_id,
            func.count(Comment.id).label("cnt"),
        ).filter(
            Comment.sentiment_score < 0.4,
        ).group_by(Comment.video_id).subquery()
        query = query.outerjoin(
            subq,
            Video.id == subq.c.video_id,
        ).order_by(
            func.coalesce(subq.c.cnt, 0).desc(),
            Video.comment_count.desc(),
        )

    offset = (page - 1) * page_size
    videos = query.offset(offset).limit(page_size).all()

    items = []
    for video in videos:
        positive = db.query(Comment).filter(
            Comment.video_id == video.id,
            Comment.sentiment_score > 0.6,
        ).count()
        negative = db.query(Comment).filter(
            Comment.video_id == video.id,
            Comment.sentiment_score < 0.4,
        ).count()
        neutral = db.query(Comment).filter(
            Comment.video_id == video.id,
            Comment.sentiment_score >= 0.4,
            Comment.sentiment_score <= 0.6,
        ).count()

        items.append(VideoWithCommentSummary(
            bvid=video.bvid,
            title=video.title,
            cover_url=video.cover_url,
            category=video.category,
            author_name=video.author_name,
            comment_count=positive + neutral + negative,
            sentiment_summary=SentimentSummary(
                positive=positive,
                neutral=neutral,
                negative=negative,
                dominant=get_dominant_sentiment(positive, neutral, negative),
            ),
        ))

    return {"total": total, "items": items}


@router.get("/{bvid}/stats", response_model=CommentStatsResponse)
def get_comment_stats(bvid: str, db: Session = Depends(get_db)):
    """获取单视频评论统计"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    comments = db.query(Comment).filter(Comment.video_id == video.id).all()
    total_count = len(comments)

    if total_count == 0:
        return CommentStatsResponse(
            total_count=0,
            positive_count=0,
            neutral_count=0,
            negative_count=0,
            positive_rate=0,
            neutral_rate=0,
            negative_rate=0,
            avg_sentiment_score=0.5,
            avg_like_count=0,
            emotion_distribution=EmotionDistribution(
                counts={label: 0 for label in EMOTION_LABELS},
                rates={label: 0.0 for label in EMOTION_LABELS},
                dominant=None,
            ),
        )

    positive_count = sum(1 for c in comments if c.sentiment_score and c.sentiment_score > 0.6)
    negative_count = sum(1 for c in comments if c.sentiment_score and c.sentiment_score < 0.4)
    neutral_count = total_count - positive_count - negative_count

    positive_rate = round(positive_count / total_count * 100, 1)
    neutral_rate = round(neutral_count / total_count * 100, 1)
    negative_rate = round(negative_count / total_count * 100, 1)

    scores = [c.sentiment_score for c in comments if c.sentiment_score is not None]
    avg_sentiment_score = round(sum(scores) / len(scores), 3) if scores else 0.5

    likes = [c.like_count or 0 for c in comments]
    avg_like_count = round(sum(likes) / len(likes), 1) if likes else 0

    emotion_distribution = build_emotion_distribution(comments, total_count)

    return CommentStatsResponse(
        total_count=total_count,
        positive_count=positive_count,
        neutral_count=neutral_count,
        negative_count=negative_count,
        positive_rate=positive_rate,
        neutral_rate=neutral_rate,
        negative_rate=negative_rate,
        avg_sentiment_score=avg_sentiment_score,
        avg_like_count=avg_like_count,
        emotion_distribution=EmotionDistribution(**emotion_distribution),
    )


@router.get("/{bvid}/list", response_model=CommentListResponse)
def get_comment_list(
    bvid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$"),
    emotion: Optional[str] = Query(None, regex=EMOTION_QUERY_REGEX),
    sort_by: str = Query("like_count", regex="^(like_count|created_at|sentiment_score)$"),
    db: Session = Depends(get_db),
):
    """获取单视频评论列表（支持筛选和排序）"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    query = db.query(Comment).filter(Comment.video_id == video.id)
    query = apply_sentiment_filter(query, sentiment)
    query = apply_emotion_filter(query, emotion)

    total = query.count()

    if sort_by == "sentiment_score":
        query = query.order_by(Comment.sentiment_score.desc())
    else:
        order_column = getattr(Comment, sort_by)
        query = query.order_by(order_column.desc())

    offset = (page - 1) * page_size
    comments = query.offset(offset).limit(page_size).all()

    items = []
    for comment in comments:
        top_scores = EmotionAnalyzer.top_emotions(
            normalize_emotion_scores(comment.emotion_scores_json),
            top_k=3,
        )
        items.append(CommentItem(
            id=comment.id,
            rpid=comment.rpid,
            content=comment.content,
            user_name=comment.user_name,
            sentiment_score=comment.sentiment_score,
            sentiment_label=get_sentiment_label(comment.sentiment_score),
            emotion_label=comment.emotion_label,
            emotion_scores=top_scores if top_scores else None,
            like_count=comment.like_count or 0,
            created_at=comment.created_at,
        ))

    return {"total": total, "items": items}


@router.get("/{bvid}/wordcloud", response_model=WordcloudResponse)
def get_comment_wordcloud(
    bvid: str,
    top_k: int = Query(50, ge=10, le=100),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$"),
    emotion: Optional[str] = Query(None, regex=EMOTION_QUERY_REGEX),
    db: Session = Depends(get_db),
):
    """获取单视频评论词云"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    query = db.query(Comment).filter(Comment.video_id == video.id)
    query = apply_sentiment_filter(query, sentiment)
    query = apply_emotion_filter(query, emotion)
    comments = query.all()

    word_sentiment_map = {}
    word_emotion_map = {}
    word_counts = Counter()

    for comment in comments:
        if not comment.content:
            continue
        words = jieba.cut(comment.content)
        comment_sentiment = get_sentiment_label(comment.sentiment_score)
        comment_emotion = EmotionAnalyzer.normalize_emotion_label(comment.emotion_label or "")
        if not comment_emotion:
            if comment_sentiment == "positive":
                comment_emotion = "joy"
            elif comment_sentiment == "negative":
                comment_emotion = "anger"
            else:
                comment_emotion = "neutral"

        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in STOPWORDS:
                word_counts[word] += 1

                if word not in word_sentiment_map:
                    word_sentiment_map[word] = {"positive": 0, "neutral": 0, "negative": 0}
                if comment_sentiment:
                    word_sentiment_map[word][comment_sentiment] += 1

                if word not in word_emotion_map:
                    word_emotion_map[word] = {label: 0 for label in EMOTION_LABELS}
                if comment_emotion:
                    word_emotion_map[word][comment_emotion] += 1

    words = []
    for word, count in word_counts.most_common(top_k):
        sentiment_counts = word_sentiment_map.get(word, {})
        dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else None

        emotion_counts = word_emotion_map.get(word, {})
        dominant_emotion = None
        if emotion_counts and any(v > 0 for v in emotion_counts.values()):
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)

        words.append(WordcloudItem(
            name=word,
            value=count,
            sentiment=dominant_sentiment,
            emotion=dominant_emotion,
        ))

    return {"words": words}


@router.get("/{bvid}/top", response_model=TopCommentsResponse)
def get_top_comments(
    bvid: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取单视频高赞评论TOP"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    comments = db.query(Comment).filter(
        Comment.video_id == video.id,
    ).order_by(Comment.like_count.desc()).limit(limit).all()

    items = [
        TopCommentItem(
            id=c.id,
            content=c.content,
            user_name=c.user_name,
            sentiment_label=get_sentiment_label(c.sentiment_score),
            emotion_label=c.emotion_label,
            like_count=c.like_count or 0,
        )
        for c in comments
    ]
    return {"items": items}


@router.post("/compare", response_model=CompareResponse)
def compare_video_comments(request: CompareRequest, db: Session = Depends(get_db)):
    """多视频评论对比"""
    if len(request.bvids) > 5:
        raise HTTPException(status_code=400, detail="最多支持5个视频对比")
    if len(request.bvids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个视频进行对比")

    result = []
    for bvid in request.bvids:
        video = db.query(Video).filter(Video.bvid == bvid).first()
        if not video:
            continue

        comments = db.query(Comment).filter(Comment.video_id == video.id).all()
        total_count = len(comments)

        if total_count == 0:
            result.append(CompareVideoItem(
                bvid=video.bvid,
                title=video.title,
                cover_url=video.cover_url,
                comment_count=0,
                positive_count=0,
                neutral_count=0,
                negative_count=0,
                positive_rate=0,
                neutral_rate=0,
                negative_rate=0,
                avg_sentiment_score=0.5,
                avg_like_count=0,
                top_keywords=[],
            ))
            continue

        positive_count = sum(1 for c in comments if c.sentiment_score and c.sentiment_score > 0.6)
        negative_count = sum(1 for c in comments if c.sentiment_score and c.sentiment_score < 0.4)
        neutral_count = total_count - positive_count - negative_count

        positive_rate = round(positive_count / total_count * 100, 1)
        neutral_rate = round(neutral_count / total_count * 100, 1)
        negative_rate = round(negative_count / total_count * 100, 1)

        scores = [c.sentiment_score for c in comments if c.sentiment_score is not None]
        avg_sentiment_score = round(sum(scores) / len(scores), 3) if scores else 0.5

        likes = [c.like_count or 0 for c in comments]
        avg_like_count = round(sum(likes) / len(likes), 1) if likes else 0

        word_counts = Counter()
        for comment in comments:
            if not comment.content:
                continue
            words = jieba.cut(comment.content)
            for word in words:
                word = word.strip()
                if len(word) >= 2 and word not in STOPWORDS:
                    word_counts[word] += 1

        top_keywords = [
            WordcloudItem(name=word, value=count)
            for word, count in word_counts.most_common(10)
        ]

        result.append(CompareVideoItem(
            bvid=video.bvid,
            title=video.title,
            cover_url=video.cover_url,
            comment_count=total_count,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            positive_rate=positive_rate,
            neutral_rate=neutral_rate,
            negative_rate=negative_rate,
            avg_sentiment_score=avg_sentiment_score,
            avg_like_count=avg_like_count,
            top_keywords=top_keywords,
        ))

    return {"videos": result}


@router.get("/export/csv")
def export_comments_csv(
    bvid: str,
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$"),
    emotion: Optional[str] = Query(None, regex=EMOTION_QUERY_REGEX),
    db: Session = Depends(get_db),
):
    """导出单视频评论为 CSV"""
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    query = db.query(Comment).filter(Comment.video_id == video.id)
    query = apply_sentiment_filter(query, sentiment)
    query = apply_emotion_filter(query, emotion)
    comments = query.order_by(Comment.like_count.desc()).limit(1000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["用户名", "评论内容", "情感分数", "情感标签", "主情绪", "点赞数", "评论时间"])

    for comment in comments:
        writer.writerow([
            comment.user_name or "",
            comment.content or "",
            round(comment.sentiment_score, 3) if comment.sentiment_score is not None else "",
            get_sentiment_label(comment.sentiment_score) or "",
            comment.emotion_label or "",
            comment.like_count or 0,
            comment.created_at.strftime("%Y-%m-%d %H:%M:%S") if comment.created_at else "",
        ])

    output.seek(0)
    bom = "\ufeff"
    content = bom + output.getvalue()

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=comments_{bvid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )
