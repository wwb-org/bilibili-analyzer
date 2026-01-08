"""
视频数据API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Video

router = APIRouter()


class VideoResponse(BaseModel):
    id: int
    bvid: str
    title: str
    category: Optional[str]
    author_name: Optional[str]
    play_count: int
    like_count: int
    coin_count: int
    share_count: int
    danmaku_count: int
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="视频不存在")
    return video
