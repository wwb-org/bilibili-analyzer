"""
热词分析API

提供热词分析相关的接口，包括：
- 热词概览统计
- 热词词云数据
- 热词排行榜
- 热词详情
- 热词对比分析
- 分区热词对比
- 热词数据导出
"""
import json
import csv
import io
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import Video
from app.models.warehouse import DwdKeywordDaily, DwsKeywordStats


router = APIRouter()


# ==================== 响应模型 ====================

class KeywordOverview(BaseModel):
    """热词概览统计"""
    total_keywords: int
    total_frequency: int
    top_keyword: Optional[dict] = None
    new_keywords: int
    source_distribution: dict


class WordcloudItem(BaseModel):
    """词云数据项"""
    name: str
    value: int
    source: str


class WordcloudResponse(BaseModel):
    """词云数据响应"""
    words: List[WordcloudItem]


class RankingItem(BaseModel):
    """排行榜数据项"""
    rank: int
    word: str
    total_frequency: int
    title_frequency: int
    comment_frequency: int
    danmaku_frequency: int
    video_count: int
    trend: str  # up, down, stable
    rank_change: int
    heat_score: float


class RankingResponse(BaseModel):
    """排行榜响应"""
    items: List[RankingItem]
    total: int
    page: int
    page_size: int


class TrendPoint(BaseModel):
    """趋势数据点"""
    date: str
    frequency: int


class CategoryDistItem(BaseModel):
    """分区分布项"""
    category: str
    frequency: int


class RelatedVideo(BaseModel):
    """关联视频"""
    bvid: str
    title: str
    cover_url: Optional[str] = None
    play_count: int


class KeywordDetail(BaseModel):
    """热词详情"""
    word: str
    current_rank: int
    total_frequency: int
    source_distribution: dict
    category_distribution: List[CategoryDistItem]
    trend: List[TrendPoint]
    avg_sentiment: Optional[float] = None
    related_videos: List[RelatedVideo]


class CompareRequest(BaseModel):
    """热词对比请求"""
    words: List[str]
    days: int = 7
    category: Optional[str] = None


class CompareTrendPoint(BaseModel):
    """对比趋势数据点"""
    date: str
    frequencies: dict


class CompareResponse(BaseModel):
    """热词对比响应"""
    words: List[str]
    trends: List[CompareTrendPoint]


class CategoryKeyword(BaseModel):
    """分区热词"""
    word: str
    frequency: int
    rank: int


class CategoryCompareItem(BaseModel):
    """分区热词对比项"""
    category: str
    keywords: List[CategoryKeyword]


class CategoryCompareResponse(BaseModel):
    """分区热词对比响应"""
    categories: List[CategoryCompareItem]


# ==================== 辅助函数 ====================

def get_default_date_range(days: int = 7):
    """获取默认日期范围"""
    end_date = date.today() - timedelta(days=1)  # 昨天
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


# ==================== API接口 ====================

@router.get("/overview", response_model=KeywordOverview)
def get_keyword_overview(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取热词概览统计

    Args:
        start_date: 开始日期
        end_date: 结束日期
        category: 分区筛选
        source: 来源筛选 (title/comment/danmaku)
    """
    if not start_date or not end_date:
        start_date, end_date = get_default_date_range()

    # 构建查询条件
    query = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date >= start_date,
        DwsKeywordStats.stat_date <= end_date
    )

    # 获取最新日期的数据用于统计
    latest_date = db.query(func.max(DwsKeywordStats.stat_date)).filter(
        DwsKeywordStats.stat_date <= end_date
    ).scalar()

    if not latest_date:
        return KeywordOverview(
            total_keywords=0,
            total_frequency=0,
            top_keyword=None,
            new_keywords=0,
            source_distribution={"title": 0, "comment": 0, "danmaku": 0}
        )

    # 查询最新日期的统计
    latest_stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == latest_date
    ).all()

    # 计算统计指标
    total_keywords = len(latest_stats)
    total_frequency = sum(s.total_frequency for s in latest_stats)

    # TOP1热词
    top_keyword = None
    if latest_stats:
        top = max(latest_stats, key=lambda x: x.total_frequency)
        top_keyword = {"word": top.word, "frequency": top.total_frequency}

    # 来源分布
    source_distribution = {
        "title": sum(s.title_frequency for s in latest_stats),
        "comment": sum(s.comment_frequency for s in latest_stats),
        "danmaku": sum(s.danmaku_frequency for s in latest_stats)
    }

    # 新增热词（排名变化 > 0 且之前不存在）
    new_keywords = len([s for s in latest_stats if s.rank_change > 10])

    return KeywordOverview(
        total_keywords=total_keywords,
        total_frequency=total_frequency,
        top_keyword=top_keyword,
        new_keywords=new_keywords,
        source_distribution=source_distribution
    )


@router.get("/wordcloud", response_model=WordcloudResponse)
def get_keyword_wordcloud(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    top_k: int = Query(100, ge=10, le=500),
    db: Session = Depends(get_db)
):
    """
    获取热词词云数据

    Args:
        start_date: 开始日期
        end_date: 结束日期
        category: 分区筛选
        source: 来源筛选 (title/comment/danmaku)
        top_k: 返回数量
    """
    if not start_date or not end_date:
        start_date, end_date = get_default_date_range()

    # 获取最新日期
    latest_date = db.query(func.max(DwsKeywordStats.stat_date)).filter(
        DwsKeywordStats.stat_date <= end_date
    ).scalar()

    if not latest_date:
        return WordcloudResponse(words=[])

    # 查询热词统计
    query = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == latest_date
    )

    stats = query.order_by(DwsKeywordStats.total_frequency.desc()).limit(top_k).all()

    # 构建词云数据
    words = []
    for s in stats:
        # 确定主要来源
        max_source = "title"
        max_freq = s.title_frequency
        if s.comment_frequency > max_freq:
            max_source = "comment"
            max_freq = s.comment_frequency
        if s.danmaku_frequency > max_freq:
            max_source = "danmaku"

        # 如果指定了来源筛选
        if source:
            if source == "title":
                freq = s.title_frequency
            elif source == "comment":
                freq = s.comment_frequency
            elif source == "danmaku":
                freq = s.danmaku_frequency
            else:
                freq = s.total_frequency
            if freq == 0:
                continue
        else:
            freq = s.total_frequency

        words.append(WordcloudItem(
            name=s.word,
            value=freq,
            source=max_source
        ))

    return WordcloudResponse(words=words)


@router.get("/ranking", response_model=RankingResponse)
def get_keyword_ranking(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    order_by: str = Query("frequency", regex="^(frequency|trend|heat)$"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """
    获取热词排行榜

    Args:
        start_date: 开始日期
        end_date: 结束日期
        category: 分区筛选
        source: 来源筛选
        order_by: 排序方式 (frequency/trend/heat)
        search: 搜索关键词
        page: 页码
        page_size: 每页数量
    """
    if not start_date or not end_date:
        start_date, end_date = get_default_date_range()

    # 获取最新日期
    latest_date = db.query(func.max(DwsKeywordStats.stat_date)).filter(
        DwsKeywordStats.stat_date <= end_date
    ).scalar()

    if not latest_date:
        return RankingResponse(items=[], total=0, page=page, page_size=page_size)

    # 构建查询
    query = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == latest_date
    )

    # 搜索过滤
    if search:
        query = query.filter(DwsKeywordStats.word.like(f"%{search}%"))

    # 排序
    if order_by == "frequency":
        query = query.order_by(DwsKeywordStats.total_frequency.desc())
    elif order_by == "trend":
        query = query.order_by(DwsKeywordStats.frequency_trend.desc())
    elif order_by == "heat":
        query = query.order_by(DwsKeywordStats.heat_score.desc())

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    stats = query.offset(offset).limit(page_size).all()

    # 构建响应
    items = []
    for i, s in enumerate(stats):
        # 确定趋势方向
        if s.rank_change > 0:
            trend = "up"
        elif s.rank_change < 0:
            trend = "down"
        else:
            trend = "stable"

        items.append(RankingItem(
            rank=offset + i + 1,
            word=s.word,
            total_frequency=s.total_frequency,
            title_frequency=s.title_frequency,
            comment_frequency=s.comment_frequency,
            danmaku_frequency=s.danmaku_frequency,
            video_count=s.video_count,
            trend=trend,
            rank_change=s.rank_change,
            heat_score=s.heat_score
        ))

    return RankingResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{word}/detail", response_model=KeywordDetail)
def get_keyword_detail(
    word: str,
    days: int = Query(7, ge=1, le=30),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取热词详情

    Args:
        word: 热词
        days: 趋势天数
        category: 分区筛选
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    # 获取最新统计
    latest_stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.word == word,
        DwsKeywordStats.stat_date <= end_date
    ).order_by(DwsKeywordStats.stat_date.desc()).first()

    if not latest_stats:
        raise HTTPException(status_code=404, detail=f"热词 '{word}' 不存在")

    # 计算当前排名
    rank_count = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == latest_stats.stat_date,
        DwsKeywordStats.total_frequency > latest_stats.total_frequency
    ).count()
    current_rank = rank_count + 1

    # 来源分布
    source_distribution = {
        "title": latest_stats.title_frequency,
        "comment": latest_stats.comment_frequency,
        "danmaku": latest_stats.danmaku_frequency
    }

    # 分区分布
    category_distribution = []
    if latest_stats.category_distribution:
        try:
            cat_dist = json.loads(latest_stats.category_distribution)
            category_distribution = [
                CategoryDistItem(category=k, frequency=v)
                for k, v in sorted(cat_dist.items(), key=lambda x: x[1], reverse=True)
            ]
        except:
            pass

    # 趋势数据
    trend_stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.word == word,
        DwsKeywordStats.stat_date >= start_date,
        DwsKeywordStats.stat_date <= end_date
    ).order_by(DwsKeywordStats.stat_date).all()

    trend = [
        TrendPoint(date=str(s.stat_date), frequency=s.total_frequency)
        for s in trend_stats
    ]

    # 关联视频（从DWD层获取）
    related_videos = []
    dwd_records = db.query(DwdKeywordDaily).filter(
        DwdKeywordDaily.word == word,
        DwdKeywordDaily.stat_date == latest_stats.stat_date
    ).all()

    bvid_set = set()
    for record in dwd_records:
        if record.sample_bvids:
            try:
                bvids = json.loads(record.sample_bvids)
                bvid_set.update(bvids)
            except:
                pass

    # 查询视频信息
    if bvid_set:
        videos = db.query(Video).filter(Video.bvid.in_(list(bvid_set)[:10])).all()
        related_videos = [
            RelatedVideo(
                bvid=v.bvid,
                title=v.title,
                cover_url=v.cover_url,
                play_count=v.play_count or 0
            )
            for v in videos
        ]

    return KeywordDetail(
        word=word,
        current_rank=current_rank,
        total_frequency=latest_stats.total_frequency,
        source_distribution=source_distribution,
        category_distribution=category_distribution,
        trend=trend,
        avg_sentiment=latest_stats.avg_sentiment,
        related_videos=related_videos
    )


@router.post("/compare", response_model=CompareResponse)
def compare_keywords(
    request: CompareRequest,
    db: Session = Depends(get_db)
):
    """
    热词趋势对比

    Args:
        request: 对比请求，包含词列表和天数
    """
    if len(request.words) > 5:
        raise HTTPException(status_code=400, detail="最多支持5个热词对比")

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=request.days - 1)

    # 查询各词的趋势数据
    stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.word.in_(request.words),
        DwsKeywordStats.stat_date >= start_date,
        DwsKeywordStats.stat_date <= end_date
    ).all()

    # 按日期组织数据
    date_data = {}
    for s in stats:
        date_str = str(s.stat_date)
        if date_str not in date_data:
            date_data[date_str] = {}
        date_data[date_str][s.word] = s.total_frequency

    # 构建趋势数据
    trends = []
    for d in sorted(date_data.keys()):
        frequencies = {w: date_data[d].get(w, 0) for w in request.words}
        trends.append(CompareTrendPoint(date=d, frequencies=frequencies))

    return CompareResponse(words=request.words, trends=trends)


@router.get("/category-compare", response_model=CategoryCompareResponse)
def compare_category_keywords(
    stat_date: Optional[date] = None,
    top_k: int = Query(10, ge=5, le=50),
    db: Session = Depends(get_db)
):
    """
    分区热词对比

    Args:
        stat_date: 统计日期，默认昨天
        top_k: 每分区返回热词数
    """
    if not stat_date:
        stat_date = date.today() - timedelta(days=1)

    # 从DWD层按分区聚合
    results = db.query(
        DwdKeywordDaily.category,
        DwdKeywordDaily.word,
        func.sum(DwdKeywordDaily.frequency).label("total_freq")
    ).filter(
        DwdKeywordDaily.stat_date == stat_date,
        DwdKeywordDaily.category.isnot(None)
    ).group_by(
        DwdKeywordDaily.category,
        DwdKeywordDaily.word
    ).all()

    # 按分区分组
    category_data = {}
    for r in results:
        if r.category not in category_data:
            category_data[r.category] = []
        category_data[r.category].append({
            "word": r.word,
            "frequency": r.total_freq
        })

    # 排序并取TopK
    categories = []
    for cat, keywords in category_data.items():
        sorted_keywords = sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:top_k]
        categories.append(CategoryCompareItem(
            category=cat,
            keywords=[
                CategoryKeyword(word=k["word"], frequency=k["frequency"], rank=i + 1)
                for i, k in enumerate(sorted_keywords)
            ]
        ))

    # 按分区名排序
    categories.sort(key=lambda x: x.category)

    return CategoryCompareResponse(categories=categories)


@router.get("/export")
def export_keywords(
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    top_k: int = Query(500, ge=10, le=2000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    导出热词数据

    Args:
        format: 导出格式 (csv/json)
        start_date: 开始日期
        end_date: 结束日期
        category: 分区筛选
        source: 来源筛选
        top_k: 导出数量
    """
    if not start_date or not end_date:
        start_date, end_date = get_default_date_range()

    # 获取最新日期
    latest_date = db.query(func.max(DwsKeywordStats.stat_date)).filter(
        DwsKeywordStats.stat_date <= end_date
    ).scalar()

    if not latest_date:
        raise HTTPException(status_code=404, detail="无可导出数据")

    # 查询数据
    stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == latest_date
    ).order_by(
        DwsKeywordStats.total_frequency.desc()
    ).limit(top_k).all()

    if format == "csv":
        # 生成CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "排名", "热词", "总频次", "标题频次", "评论频次", "弹幕频次",
            "关联视频数", "热度分", "趋势变化"
        ])
        for i, s in enumerate(stats):
            writer.writerow([
                i + 1, s.word, s.total_frequency, s.title_frequency,
                s.comment_frequency, s.danmaku_frequency, s.video_count,
                round(s.heat_score, 4), s.rank_change
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=keywords_{latest_date}.csv"
            }
        )
    else:
        # JSON格式
        data = [
            {
                "rank": i + 1,
                "word": s.word,
                "total_frequency": s.total_frequency,
                "title_frequency": s.title_frequency,
                "comment_frequency": s.comment_frequency,
                "danmaku_frequency": s.danmaku_frequency,
                "video_count": s.video_count,
                "heat_score": round(s.heat_score, 4),
                "rank_change": s.rank_change
            }
            for i, s in enumerate(stats)
        ]
        return {"stat_date": str(latest_date), "keywords": data}
