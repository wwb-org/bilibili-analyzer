"""
爆款内容策划 API
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Video
from app.services import content_planner as planner

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取有数据的分区列表"""
    rows = db.query(Video.category).filter(
        Video.category != None, Video.category != ''
    ).distinct().all()
    return {"categories": sorted([r[0] for r in rows if r[0]])}


@router.get("/category-analysis")
def get_category_analysis(
    category: str = Query(..., description="视频分区"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析某分区的爆款特征"""
    result = planner.analyze_category_features(category, db)
    return result


@router.get("/keywords")
def get_viral_keywords(
    category: str = Query(..., description="视频分区"),
    top_k: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取分区爆款关键词推荐"""
    keywords = planner.get_viral_keywords(category, db, top_k)
    return {"category": category, "keywords": keywords, "total": len(keywords)}


@router.get("/title-suggestions")
def get_title_suggestions(
    category: str = Query(..., description="视频分区"),
    num: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成标题建议"""
    suggestions = planner.generate_title_suggestions(category, db, num)
    return {"category": category, "suggestions": suggestions}


class ScoreTitleRequest(BaseModel):
    title: str
    category: str


@router.post("/score-title")
def score_title(
    data: ScoreTitleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """对标题进行评分"""
    result = planner.score_title(data.title, data.category, db)
    return result
