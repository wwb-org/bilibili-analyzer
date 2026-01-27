"""
视频数据API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

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
