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
from typing import Dict, List, Optional, Set
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, Video
from app.models.warehouse import DwdKeywordDaily, DwdVideoSnapshot, DwsKeywordStats


router = APIRouter()


# ==================== 响应模型 ====================

class KeywordOverview(BaseModel):
    """热词概览统计"""
    total_keywords: int
    total_frequency: int
    top_keyword: Optional[dict] = None
    new_keywords: int
    source_distribution: dict
    stat_date: Optional[str] = None
    data_days: int = 0


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


class RelatedKeywordItem(BaseModel):
    """关联热词"""
    word: str
    co_occurrence: int
    heat_score: Optional[float] = None


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
    related_keywords: List[RelatedKeywordItem] = []


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
    cross_category_count: int = 1
    is_niche: bool = False


class CategoryCompareItem(BaseModel):
    """分区热词对比项"""
    category: str
    keywords: List[CategoryKeyword]


class CategoryCompareResponse(BaseModel):
    """分区热词对比响应"""
    categories: List[CategoryCompareItem]


class MoverItem(BaseModel):
    """异动项"""
    word: str
    current_frequency: int
    previous_frequency: int
    change_abs: int
    change_rate: float
    heat_score: float
    avg_sentiment: Optional[float] = None
    is_new: bool = False


class MoversResponse(BaseModel):
    """异动榜响应"""
    stat_date: str
    previous_date: Optional[str] = None
    rising: List[MoverItem]
    falling: List[MoverItem]


class OpportunityRiskItem(BaseModel):
    """机会/风险项"""
    word: str
    score: float
    current_frequency: int
    change_rate: float
    avg_sentiment: Optional[float] = None
    heat_score: float
    high_interaction_ratio: float


class OpportunityRiskResponse(BaseModel):
    """机会/风险响应"""
    stat_date: str
    opportunities: List[OpportunityRiskItem]
    risks: List[OpportunityRiskItem]


class ContributorVideoItem(BaseModel):
    """热词贡献视频项"""
    bvid: str
    title: str
    cover_url: Optional[str] = None
    category: Optional[str] = None
    play_count: int
    comment_count: int
    play_increment: int
    comment_increment: int
    interaction_rate: float
    estimated_contribution: float


class KeywordContributorsResponse(BaseModel):
    """热词贡献视频响应"""
    word: str
    stat_date: str
    items: List[ContributorVideoItem]


class CategoryGap(BaseModel):
    """分区缺口"""
    category: str
    gap_level: str  # high, medium, low


class ContentSuggestionItem(BaseModel):
    """选题建议项"""
    word: str
    opportunity_score: float
    competition: str  # low, medium, high
    trend_direction: str  # rising, stable, falling
    avg_sentiment: Optional[float] = None
    video_count: int = 0
    category_gaps: List[CategoryGap] = []
    suggestion_text: str = ""
    example_videos: List[RelatedVideo] = []


class ContentSuggestionsResponse(BaseModel):
    """选题建议响应"""
    stat_date: str
    suggestions: List[ContentSuggestionItem]


# ==================== 辅助函数 ====================

def get_default_date_range(days: int = 7):
    """获取默认日期范围"""
    end_date = date.today() - timedelta(days=1)  # 昨天
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def get_latest_data_date(db: Session) -> Optional[date]:
    """获取DWD热词表中的最新统计日期"""
    return db.query(func.max(DwdKeywordDaily.stat_date)).scalar()


def resolve_date_range(
    db: Session,
    start_date: Optional[date],
    end_date: Optional[date],
    days: int = 7
):
    """解析日期范围：默认最近N天（截至最新数据日）"""
    if start_date and end_date:
        return start_date, end_date

    latest_data_date = get_latest_data_date(db)
    if latest_data_date:
        end_date = latest_data_date
        start_date = end_date - timedelta(days=max(days, 1) - 1)
        return start_date, end_date

    # 无数据时回退到原有默认口径（截至昨天）
    if not start_date or not end_date:
        return get_default_date_range(days=days)
    return start_date, end_date


def get_latest_stat_date(db: Session, start_date: date, end_date: date) -> Optional[date]:
    """获取日期范围内最新统计日期（来自DWD）"""
    return db.query(func.max(DwdKeywordDaily.stat_date)).filter(
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date <= end_date
    ).scalar()


def parse_sample_bvids(sample_bvids: Optional[str]) -> Set[str]:
    """解析样例视频BVID列表"""
    if not sample_bvids:
        return set()
    try:
        values = json.loads(sample_bvids)
        if isinstance(values, list):
            return {str(v) for v in values if v}
    except Exception:
        return set()
    return set()


def aggregate_keyword_rows(rows: List[DwdKeywordDaily]) -> Dict[str, Dict]:
    """按词聚合DWD明细"""
    word_map: Dict[str, Dict] = {}

    for row in rows:
        data = word_map.setdefault(row.word, {
            "word": row.word,
            "title_frequency": 0,
            "comment_frequency": 0,
            "danmaku_frequency": 0,
            "total_frequency": 0,
            "video_count": 0,
            "category_distribution": {},
            "sample_bvids": set(),
            "sentiments": []
        })

        freq = row.frequency or 0
        if row.source == "title":
            data["title_frequency"] += freq
        elif row.source == "comment":
            data["comment_frequency"] += freq
        elif row.source == "danmaku":
            data["danmaku_frequency"] += freq

        data["total_frequency"] += freq
        data["video_count"] = max(data["video_count"], row.video_count or 0)

        if row.category:
            data["category_distribution"][row.category] = (
                data["category_distribution"].get(row.category, 0) + freq
            )

        if row.avg_sentiment is not None and row.source == "comment":
            data["sentiments"].append(row.avg_sentiment)

        data["sample_bvids"].update(parse_sample_bvids(row.sample_bvids))

    for data in word_map.values():
        sentiments = data.pop("sentiments")
        data["avg_sentiment"] = (
            sum(sentiments) / len(sentiments) if sentiments else None
        )

    return word_map


def get_filtered_rows(
    db: Session,
    stat_date: date,
    category: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    words: Optional[List[str]] = None
) -> List[DwdKeywordDaily]:
    """查询指定日期下的明细行（支持筛选）"""
    query = db.query(DwdKeywordDaily).filter(
        DwdKeywordDaily.stat_date == stat_date
    )

    if category:
        query = query.filter(DwdKeywordDaily.category == category)
    if source:
        query = query.filter(DwdKeywordDaily.source == source)
    if search:
        query = query.filter(DwdKeywordDaily.word.like(f"%{search}%"))
    if words:
        query = query.filter(DwdKeywordDaily.word.in_(words))

    return query.all()


def get_dws_map(db: Session, stat_date: date, words: List[str]) -> Dict[str, DwsKeywordStats]:
    """批量获取DWS指标映射"""
    if not words:
        return {}
    stats = db.query(DwsKeywordStats).filter(
        DwsKeywordStats.stat_date == stat_date,
        DwsKeywordStats.word.in_(words)
    ).all()
    return {s.word: s for s in stats}


def get_previous_stat_date(db: Session, start_date: date, latest_date: date) -> Optional[date]:
    """获取范围内最新日期的前一个可用统计日"""
    return db.query(func.max(DwdKeywordDaily.stat_date)).filter(
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date < latest_date
    ).scalar()


def calc_change_rate(current_value: int, previous_value: int) -> float:
    """计算变化率（小数），previous=0 时按 100% 处理"""
    if previous_value > 0:
        return (current_value - previous_value) / previous_value
    return 1.0 if current_value > 0 else 0.0


def clamp(value: float, min_value: float, max_value: float) -> float:
    """限制数值范围"""
    return max(min_value, min(max_value, value))


def get_snapshot_map(db: Session, snapshot_date: date, bvids: List[str]) -> Dict[str, DwdVideoSnapshot]:
    """批量查询视频快照映射"""
    if not bvids:
        return {}
    rows = db.query(DwdVideoSnapshot).filter(
        DwdVideoSnapshot.snapshot_date == snapshot_date,
        DwdVideoSnapshot.bvid.in_(bvids)
    ).all()
    return {row.bvid: row for row in rows}


def build_keyword_insights(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    min_frequency: int = 0,
    interaction_threshold: float = 0.05,
) -> Dict:
    """构建热词洞察基础数据（异动/机会/风险复用）"""
    start_date, end_date = resolve_date_range(db, start_date, end_date)
    latest_date = get_latest_stat_date(db, start_date, end_date)
    if not latest_date:
        return {
            "latest_date": None,
            "previous_date": None,
            "items": []
        }

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source
    )
    latest_map = aggregate_keyword_rows(latest_rows)

    previous_date = get_previous_stat_date(db, start_date, latest_date)
    previous_map: Dict[str, Dict] = {}
    if previous_date:
        previous_rows = get_filtered_rows(
            db=db,
            stat_date=previous_date,
            category=category,
            source=source
        )
        previous_map = aggregate_keyword_rows(previous_rows)

    words = list(latest_map.keys())
    dws_map = get_dws_map(db, latest_date, words)

    # 批量加载样例视频快照，用于计算高互动占比
    all_bvids: Set[str] = set()
    for item in latest_map.values():
        all_bvids.update(item.get("sample_bvids", set()))
    snapshot_map = get_snapshot_map(db, latest_date, list(all_bvids))

    items = []
    for word, current in latest_map.items():
        current_frequency = current["total_frequency"]
        if current_frequency < min_frequency:
            continue

        previous_frequency = previous_map.get(word, {}).get("total_frequency", 0)
        is_new = previous_frequency == 0 and current_frequency > 0
        change_abs = current_frequency - previous_frequency
        change_rate = calc_change_rate(current_frequency, previous_frequency)
        dws = dws_map.get(word)
        heat_score = dws.heat_score if dws else 0.0
        avg_sentiment = current.get("avg_sentiment")
        sentiment_value = avg_sentiment if avg_sentiment is not None else 0.5

        sample_bvids = list(current.get("sample_bvids", set()))
        high_interaction_count = 0
        snapshot_count = 0
        for bvid in sample_bvids:
            snapshot = snapshot_map.get(bvid)
            if not snapshot:
                continue
            snapshot_count += 1
            if (snapshot.interaction_rate or 0) >= interaction_threshold:
                high_interaction_count += 1
        high_interaction_ratio = (
            high_interaction_count / snapshot_count
            if snapshot_count > 0 else 0.0
        )

        # 机会分：增长 + 热度 + 正向情感 + 高互动样本占比
        normalized_growth = clamp(change_rate, 0, 3) / 3
        opportunity_score = (
            normalized_growth * 0.45
            + clamp(heat_score, 0, 1) * 0.25
            + clamp((sentiment_value - 0.5) * 2, 0, 1) * 0.20
            + high_interaction_ratio * 0.10
        )

        # 风险分：增长 + 负向情感 + 低互动样本占比 + 词热度
        risk_score = (
            normalized_growth * 0.40
            + clamp((0.5 - sentiment_value) * 2, 0, 1) * 0.35
            + (1 - high_interaction_ratio) * 0.15
            + clamp(heat_score, 0, 1) * 0.10
        )

        items.append({
            "word": word,
            "current_frequency": current_frequency,
            "previous_frequency": previous_frequency,
            "is_new": is_new,
            "change_abs": change_abs,
            "change_rate": change_rate,
            "heat_score": heat_score,
            "avg_sentiment": avg_sentiment,
            "high_interaction_ratio": high_interaction_ratio,
            "opportunity_score": round(opportunity_score, 4),
            "risk_score": round(risk_score, 4),
        })

    return {
        "latest_date": latest_date,
        "previous_date": previous_date,
        "items": items
    }


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
    start_date, end_date = resolve_date_range(db, start_date, end_date)

    latest_date = get_latest_stat_date(db, start_date, end_date)

    if not latest_date:
        return KeywordOverview(
            total_keywords=0,
            total_frequency=0,
            top_keyword=None,
            new_keywords=0,
            source_distribution={"title": 0, "comment": 0, "danmaku": 0},
            stat_date=None,
            data_days=0
        )

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source
    )
    word_map = aggregate_keyword_rows(latest_rows)
    latest_words = set(word_map.keys())

    total_keywords = len(word_map)
    total_frequency = sum(item["total_frequency"] for item in word_map.values())

    top_keyword = None
    if word_map:
        top = max(word_map.values(), key=lambda x: x["total_frequency"])
        top_keyword = {"word": top["word"], "frequency": top["total_frequency"]}

    source_distribution = {
        "title": sum(item["title_frequency"] for item in word_map.values()),
        "comment": sum(item["comment_frequency"] for item in word_map.values()),
        "danmaku": sum(item["danmaku_frequency"] for item in word_map.values())
    }

    # 新增热词：最新日出现，且在范围内历史日期未出现
    history_query = db.query(DwdKeywordDaily.word).distinct().filter(
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date < latest_date
    )
    if category:
        history_query = history_query.filter(DwdKeywordDaily.category == category)
    if source:
        history_query = history_query.filter(DwdKeywordDaily.source == source)
    history_words = {word for (word,) in history_query.all()}
    new_keywords = len(latest_words - history_words)

    # 统计日期范围内有数据的天数
    data_days = db.query(func.count(func.distinct(DwdKeywordDaily.stat_date))).filter(
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date <= end_date
    ).scalar() or 0

    return KeywordOverview(
        total_keywords=total_keywords,
        total_frequency=total_frequency,
        top_keyword=top_keyword,
        new_keywords=new_keywords,
        source_distribution=source_distribution,
        stat_date=str(latest_date),
        data_days=data_days
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
    start_date, end_date = resolve_date_range(db, start_date, end_date)

    latest_date = get_latest_stat_date(db, start_date, end_date)

    if not latest_date:
        return WordcloudResponse(words=[])

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source
    )
    word_map = aggregate_keyword_rows(latest_rows)
    stats = sorted(
        word_map.values(),
        key=lambda x: x["total_frequency"],
        reverse=True
    )[:top_k]

    # 构建词云数据
    words = []
    for s in stats:
        # 确定主要来源
        max_source = "title"
        max_freq = s["title_frequency"]
        if s["comment_frequency"] > max_freq:
            max_source = "comment"
            max_freq = s["comment_frequency"]
        if s["danmaku_frequency"] > max_freq:
            max_source = "danmaku"

        freq = s["total_frequency"]

        words.append(WordcloudItem(
            name=s["word"],
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
    start_date, end_date = resolve_date_range(db, start_date, end_date)

    latest_date = get_latest_stat_date(db, start_date, end_date)

    if not latest_date:
        return RankingResponse(items=[], total=0, page=page, page_size=page_size)

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source,
        search=search
    )
    word_map = aggregate_keyword_rows(latest_rows)
    words = list(word_map.keys())
    dws_map = get_dws_map(db, latest_date, words)

    stats = list(word_map.values())
    if order_by == "frequency":
        stats.sort(key=lambda x: x["total_frequency"], reverse=True)
    elif order_by == "trend":
        stats.sort(
            key=lambda x: dws_map.get(x["word"]).frequency_trend if dws_map.get(x["word"]) else 0,
            reverse=True
        )
    elif order_by == "heat":
        stats.sort(
            key=lambda x: dws_map.get(x["word"]).heat_score if dws_map.get(x["word"]) else 0,
            reverse=True
        )

    total = len(stats)
    offset = (page - 1) * page_size
    page_items = stats[offset:offset + page_size]

    # 构建响应
    items = []
    for i, s in enumerate(page_items):
        dws = dws_map.get(s["word"])
        rank_change = dws.rank_change if dws else 0
        heat_score = dws.heat_score if dws else 0

        # 确定趋势方向
        if rank_change > 0:
            trend = "up"
        elif rank_change < 0:
            trend = "down"
        else:
            trend = "stable"

        items.append(RankingItem(
            rank=offset + i + 1,
            word=s["word"],
            total_frequency=s["total_frequency"],
            title_frequency=s["title_frequency"],
            comment_frequency=s["comment_frequency"],
            danmaku_frequency=s["danmaku_frequency"],
            video_count=s["video_count"],
            trend=trend,
            rank_change=rank_change,
            heat_score=heat_score
        ))

    return RankingResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/movers", response_model=MoversResponse)
def get_keyword_movers(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    top_k: int = Query(10, ge=1, le=100),
    min_frequency: int = Query(20, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    获取热词异动榜（爆发/下滑）
    """
    insight = build_keyword_insights(
        db=db,
        start_date=start_date,
        end_date=end_date,
        category=category,
        source=source,
        min_frequency=min_frequency,
    )

    latest_date = insight["latest_date"]
    if not latest_date:
        return MoversResponse(stat_date="", previous_date=None, rising=[], falling=[])

    items = insight["items"]
    rising = sorted(
        [item for item in items if item["change_abs"] > 0],
        key=lambda x: (x["change_rate"], x["change_abs"]),
        reverse=True
    )[:top_k]
    falling = sorted(
        [item for item in items if item["change_abs"] < 0],
        key=lambda x: (x["change_rate"], x["change_abs"])
    )[:top_k]

    return MoversResponse(
        stat_date=str(latest_date),
        previous_date=str(insight["previous_date"]) if insight["previous_date"] else None,
        rising=[
            MoverItem(
                word=item["word"],
                current_frequency=item["current_frequency"],
                previous_frequency=item["previous_frequency"],
                change_abs=item["change_abs"],
                change_rate=round(item["change_rate"], 4),
                heat_score=round(item["heat_score"], 4),
                avg_sentiment=item["avg_sentiment"],
                is_new=item["is_new"],
            )
            for item in rising
        ],
        falling=[
            MoverItem(
                word=item["word"],
                current_frequency=item["current_frequency"],
                previous_frequency=item["previous_frequency"],
                change_abs=item["change_abs"],
                change_rate=round(item["change_rate"], 4),
                heat_score=round(item["heat_score"], 4),
                avg_sentiment=item["avg_sentiment"],
                is_new=item["is_new"],
            )
            for item in falling
        ]
    )


@router.get("/opportunity-risk", response_model=OpportunityRiskResponse)
def get_keyword_opportunity_risk(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    top_k: int = Query(10, ge=1, le=100),
    min_frequency: int = Query(20, ge=1, le=10000),
    interaction_threshold: float = Query(0.05, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    获取热词机会榜/风险榜
    """
    insight = build_keyword_insights(
        db=db,
        start_date=start_date,
        end_date=end_date,
        category=category,
        source=source,
        min_frequency=min_frequency,
        interaction_threshold=interaction_threshold,
    )
    latest_date = insight["latest_date"]
    if not latest_date:
        return OpportunityRiskResponse(stat_date="", opportunities=[], risks=[])

    items = insight["items"]
    opportunities = sorted(items, key=lambda x: x["opportunity_score"], reverse=True)[:top_k]
    risks = sorted(items, key=lambda x: x["risk_score"], reverse=True)[:top_k]

    return OpportunityRiskResponse(
        stat_date=str(latest_date),
        opportunities=[
            OpportunityRiskItem(
                word=item["word"],
                score=item["opportunity_score"],
                current_frequency=item["current_frequency"],
                change_rate=round(item["change_rate"], 4),
                avg_sentiment=item["avg_sentiment"],
                heat_score=round(item["heat_score"], 4),
                high_interaction_ratio=round(item["high_interaction_ratio"], 4),
            )
            for item in opportunities
        ],
        risks=[
            OpportunityRiskItem(
                word=item["word"],
                score=item["risk_score"],
                current_frequency=item["current_frequency"],
                change_rate=round(item["change_rate"], 4),
                avg_sentiment=item["avg_sentiment"],
                heat_score=round(item["heat_score"], 4),
                high_interaction_ratio=round(item["high_interaction_ratio"], 4),
            )
            for item in risks
        ]
    )


@router.get("/content-suggestions", response_model=ContentSuggestionsResponse)
def get_content_suggestions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    top_k: int = Query(5, ge=1, le=10),
    min_frequency: int = Query(20, ge=1, le=10000),
    interaction_threshold: float = Query(0.05, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    内容选题建议：基于机会词生成可操作的选题建议
    """
    insight = build_keyword_insights(
        db=db,
        start_date=start_date,
        end_date=end_date,
        category=category,
        source=source,
        min_frequency=min_frequency,
        interaction_threshold=interaction_threshold,
    )
    latest_date = insight["latest_date"]
    if not latest_date:
        return ContentSuggestionsResponse(stat_date="", suggestions=[])

    # 按机会分排序取 TOP
    items = sorted(insight["items"], key=lambda x: x["opportunity_score"], reverse=True)[:top_k]
    words = [item["word"] for item in items]

    # 获取 DWS 趋势数据
    dws_map = get_dws_map(db, latest_date, words)

    # 获取分区分布（用于分析分区缺口）
    all_category_rows = db.query(
        DwdKeywordDaily.word,
        DwdKeywordDaily.category,
        func.sum(DwdKeywordDaily.frequency).label("freq")
    ).filter(
        DwdKeywordDaily.stat_date == latest_date,
        DwdKeywordDaily.word.in_(words),
        DwdKeywordDaily.category.isnot(None)
    ).group_by(
        DwdKeywordDaily.word,
        DwdKeywordDaily.category
    ).all()

    # 构建词→分区频次映射
    word_cat_freq: Dict[str, Dict[str, int]] = {}
    for row in all_category_rows:
        word_cat_freq.setdefault(row.word, {})[row.category] = row.freq or 0

    # 获取所有分区列表
    all_categories = db.query(DwdKeywordDaily.category).filter(
        DwdKeywordDaily.stat_date == latest_date,
        DwdKeywordDaily.category.isnot(None)
    ).distinct().all()
    all_cat_names = [c[0] for c in all_categories]

    # 获取样例视频
    all_bvids: Set[str] = set()
    kw_rows = db.query(DwdKeywordDaily).filter(
        DwdKeywordDaily.stat_date == latest_date,
        DwdKeywordDaily.word.in_(words)
    ).all()
    word_bvids: Dict[str, Set[str]] = {}
    for row in kw_rows:
        bvids = parse_sample_bvids(row.sample_bvids)
        word_bvids.setdefault(row.word, set()).update(bvids)
        all_bvids.update(bvids)

    video_map = {}
    if all_bvids:
        videos = db.query(Video).filter(Video.bvid.in_(list(all_bvids))).all()
        video_map = {v.bvid: v for v in videos}

    # 构建建议
    suggestions = []
    for item in items:
        word = item["word"]
        dws = dws_map.get(word)

        # 竞争度
        video_count = 0
        bvids = word_bvids.get(word, set())
        if bvids:
            video_count = len(bvids)
        if video_count <= 5:
            competition = "low"
        elif video_count <= 20:
            competition = "medium"
        else:
            competition = "high"

        # 趋势方向
        freq_trend = dws.frequency_trend if dws else 0
        if freq_trend and freq_trend > 0.1:
            trend_direction = "rising"
        elif freq_trend and freq_trend < -0.1:
            trend_direction = "falling"
        else:
            trend_direction = "stable"

        # 分区缺口分析
        cat_freqs = word_cat_freq.get(word, {})
        max_cat_freq = int(max(cat_freqs.values())) if cat_freqs else 0
        category_gaps = []
        for cat_name in all_cat_names:
            cat_freq = cat_freqs.get(cat_name, 0)
            if max_cat_freq > 0 and cat_freq < max_cat_freq * 0.2:
                category_gaps.append(CategoryGap(
                    category=cat_name,
                    gap_level="high" if cat_freq == 0 else "medium"
                ))
        category_gaps = category_gaps[:3]  # 最多3个缺口

        # 生成建议文本
        suggestion_text = _generate_suggestion_text(
            word, competition, trend_direction,
            item.get("avg_sentiment"), category_gaps
        )

        # 参考视频
        example_videos = []
        for bvid in list(bvids)[:3]:
            v = video_map.get(bvid)
            if v:
                example_videos.append(RelatedVideo(
                    bvid=v.bvid,
                    title=v.title,
                    cover_url=v.cover_url,
                    play_count=v.play_count or 0
                ))

        suggestions.append(ContentSuggestionItem(
            word=word,
            opportunity_score=round(item["opportunity_score"], 4),
            competition=competition,
            trend_direction=trend_direction,
            avg_sentiment=item.get("avg_sentiment"),
            video_count=video_count,
            category_gaps=category_gaps,
            suggestion_text=suggestion_text,
            example_videos=example_videos
        ))

    return ContentSuggestionsResponse(
        stat_date=str(latest_date),
        suggestions=suggestions
    )


def _generate_suggestion_text(
    word: str,
    competition: str,
    trend_direction: str,
    avg_sentiment: Optional[float],
    category_gaps: List[CategoryGap]
) -> str:
    """基于规则模板生成选题建议文本"""
    if competition == "low" and trend_direction == "rising":
        return f"蓝海选题：「{word}」正在升温且竞争较少，建议尽快切入"

    high_gaps = [g for g in category_gaps if g.gap_level == "high"]
    if high_gaps:
        gap_cats = "、".join(g.category for g in high_gaps[:2])
        return f"跨区机会：「{word}」在{gap_cats}分区几乎空白，可差异化切入"

    if avg_sentiment is not None and avg_sentiment > 0.6:
        return f"高互动选题：「{word}」相关内容观众反馈积极，互动率高"

    if trend_direction == "rising":
        return f"上升趋势：「{word}」热度持续上升，值得关注"

    if competition == "low":
        return f"低竞争选题：「{word}」当前覆盖视频较少，存在内容缺口"

    return f"热门选题：「{word}」热度较高，可结合差异化角度切入"


@router.get("/{word}/contributors", response_model=KeywordContributorsResponse)
def get_keyword_contributors(
    word: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取热词贡献视频（样例估算）
    """
    start_date, end_date = resolve_date_range(db, start_date, end_date)
    latest_date = get_latest_stat_date(db, start_date, end_date)
    if not latest_date:
        raise HTTPException(status_code=404, detail="无可用热词数据")

    rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source,
        words=[word]
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"热词 '{word}' 不存在")

    contribution_map: Dict[str, Dict] = {}
    for row in rows:
        bvids = list(parse_sample_bvids(row.sample_bvids))
        if not bvids:
            continue
        unit = (row.frequency or 0) / max(len(bvids), 1)
        for bvid in bvids:
            item = contribution_map.setdefault(bvid, {"estimated_contribution": 0.0})
            item["estimated_contribution"] += unit

    if not contribution_map:
        return KeywordContributorsResponse(word=word, stat_date=str(latest_date), items=[])

    bvids = list(contribution_map.keys())
    videos = db.query(Video).filter(Video.bvid.in_(bvids)).all()
    video_map = {video.bvid: video for video in videos}
    snapshot_map = get_snapshot_map(db, latest_date, bvids)

    items = []
    for bvid, info in contribution_map.items():
        video = video_map.get(bvid)
        if not video:
            continue
        snapshot = snapshot_map.get(bvid)
        items.append(ContributorVideoItem(
            bvid=bvid,
            title=video.title,
            cover_url=video.cover_url,
            category=video.category,
            play_count=video.play_count or 0,
            comment_count=video.comment_count or 0,
            play_increment=(snapshot.play_increment if snapshot else 0) or 0,
            comment_increment=(snapshot.comment_increment if snapshot else 0) or 0,
            interaction_rate=(snapshot.interaction_rate if snapshot else 0.0) or 0.0,
            estimated_contribution=round(info["estimated_contribution"], 2),
        ))

    items.sort(key=lambda x: x.estimated_contribution, reverse=True)
    return KeywordContributorsResponse(
        word=word,
        stat_date=str(latest_date),
        items=items[:limit]
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
    latest_data_date = get_latest_data_date(db)
    end_date = latest_data_date or (date.today() - timedelta(days=1))
    start_date = end_date - timedelta(days=days - 1)

    latest_date_query = db.query(func.max(DwdKeywordDaily.stat_date)).filter(
        DwdKeywordDaily.word == word,
        DwdKeywordDaily.stat_date <= end_date
    )
    if category:
        latest_date_query = latest_date_query.filter(DwdKeywordDaily.category == category)
    latest_date = latest_date_query.scalar()

    if not latest_date:
        raise HTTPException(status_code=404, detail=f"热词 '{word}' 不存在")

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        words=[word]
    )
    latest_word_map = aggregate_keyword_rows(latest_rows)
    latest_word = latest_word_map.get(word)
    if not latest_word:
        raise HTTPException(status_code=404, detail=f"热词 '{word}' 不存在")

    # 计算当前排名（同筛选口径）
    all_rows = get_filtered_rows(db=db, stat_date=latest_date, category=category)
    all_word_map = aggregate_keyword_rows(all_rows)
    sorted_words = sorted(all_word_map.values(), key=lambda x: x["total_frequency"], reverse=True)
    current_rank = next(
        (idx + 1 for idx, item in enumerate(sorted_words) if item["word"] == word),
        len(sorted_words) + 1
    )

    source_distribution = {
        "title": latest_word["title_frequency"],
        "comment": latest_word["comment_frequency"],
        "danmaku": latest_word["danmaku_frequency"]
    }

    category_distribution = [
        CategoryDistItem(category=k, frequency=v)
        for k, v in sorted(
            latest_word["category_distribution"].items(),
            key=lambda x: x[1],
            reverse=True
        )
    ]

    # 趋势数据（同筛选口径）
    trend_query = db.query(
        DwdKeywordDaily.stat_date,
        func.sum(DwdKeywordDaily.frequency).label("frequency")
    ).filter(
        DwdKeywordDaily.word == word,
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date <= end_date
    )
    if category:
        trend_query = trend_query.filter(DwdKeywordDaily.category == category)

    trend_stats = trend_query.group_by(DwdKeywordDaily.stat_date).order_by(DwdKeywordDaily.stat_date).all()
    trend = [TrendPoint(date=str(s.stat_date), frequency=s.frequency or 0) for s in trend_stats]

    # 关联视频（从DWD层获取）
    related_videos = []
    dwd_records = db.query(DwdKeywordDaily).filter(
        DwdKeywordDaily.word == word,
        DwdKeywordDaily.stat_date == latest_date
    )
    if category:
        dwd_records = dwd_records.filter(DwdKeywordDaily.category == category)
    dwd_records = dwd_records.all()

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

    # 关联热词：基于 sample_bvids 共现分析
    related_keywords = []
    if bvid_set:
        all_kw_rows = db.query(DwdKeywordDaily).filter(
            DwdKeywordDaily.stat_date == latest_date,
            DwdKeywordDaily.word != word
        ).all()

        co_occurrence: Dict[str, int] = {}
        for row in all_kw_rows:
            row_bvids = parse_sample_bvids(row.sample_bvids)
            overlap = bvid_set & row_bvids
            if overlap:
                co_occurrence[row.word] = co_occurrence.get(row.word, 0) + len(overlap)

        if co_occurrence:
            # 获取热度分
            co_words = list(co_occurrence.keys())
            co_dws_map = get_dws_map(db, latest_date, co_words)
            sorted_co = sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)[:10]
            related_keywords = [
                RelatedKeywordItem(
                    word=w,
                    co_occurrence=cnt,
                    heat_score=round(co_dws_map[w].heat_score, 4) if co_dws_map.get(w) else None
                )
                for w, cnt in sorted_co
            ]

    return KeywordDetail(
        word=word,
        current_rank=current_rank,
        total_frequency=latest_word["total_frequency"],
        source_distribution=source_distribution,
        category_distribution=category_distribution,
        trend=trend,
        avg_sentiment=latest_word["avg_sentiment"],
        related_videos=related_videos,
        related_keywords=related_keywords
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

    latest_data_date = get_latest_data_date(db)
    end_date = latest_data_date or (date.today() - timedelta(days=1))
    start_date = end_date - timedelta(days=request.days - 1)

    query = db.query(
        DwdKeywordDaily.stat_date,
        DwdKeywordDaily.word,
        func.sum(DwdKeywordDaily.frequency).label("frequency")
    ).filter(
        DwdKeywordDaily.word.in_(request.words),
        DwdKeywordDaily.stat_date >= start_date,
        DwdKeywordDaily.stat_date <= end_date
    )
    if request.category:
        query = query.filter(DwdKeywordDaily.category == request.category)

    stats = query.group_by(DwdKeywordDaily.stat_date, DwdKeywordDaily.word).all()

    date_data: Dict[str, Dict[str, int]] = {}
    for s in stats:
        date_str = str(s.stat_date)
        if date_str not in date_data:
            date_data[date_str] = {}
        date_data[date_str][s.word] = s.frequency or 0

    # 固定输出连续日期，缺失补0
    trends = []
    current = start_date
    while current <= end_date:
        d = str(current)
        freq_map = date_data.get(d, {})
        frequencies = {w: freq_map.get(w, 0) for w in request.words}
        trends.append(CompareTrendPoint(date=d, frequencies=frequencies))
        current += timedelta(days=1)

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
        stat_date: 统计日期，默认最新数据日
        top_k: 每分区返回热词数
    """
    if not stat_date:
        stat_date = get_latest_data_date(db) or (date.today() - timedelta(days=1))

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

    # 统计每个词出现在几个分区
    word_category_count: Dict[str, int] = {}
    for cat, keywords in category_data.items():
        for k in keywords:
            word_category_count[k["word"]] = word_category_count.get(k["word"], 0) + 1

    total_categories = len(category_data)

    # 排序并取TopK
    categories = []
    for cat, keywords in category_data.items():
        sorted_keywords = sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:top_k]
        categories.append(CategoryCompareItem(
            category=cat,
            keywords=[
                CategoryKeyword(
                    word=k["word"],
                    frequency=k["frequency"],
                    rank=i + 1,
                    cross_category_count=word_category_count.get(k["word"], 1),
                    is_niche=word_category_count.get(k["word"], 1) == 1
                )
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
    start_date, end_date = resolve_date_range(db, start_date, end_date)
    latest_date = get_latest_stat_date(db, start_date, end_date)

    if not latest_date:
        raise HTTPException(status_code=404, detail="无可导出数据")

    latest_rows = get_filtered_rows(
        db=db,
        stat_date=latest_date,
        category=category,
        source=source
    )
    word_map = aggregate_keyword_rows(latest_rows)
    words = list(word_map.keys())
    dws_map = get_dws_map(db, latest_date, words)
    stats = sorted(word_map.values(), key=lambda x: x["total_frequency"], reverse=True)[:top_k]

    if format == "csv":
        # 生成CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "排名", "热词", "总频次", "标题频次", "评论频次", "弹幕频次",
            "关联视频数", "热度分", "趋势变化"
        ])
        for i, s in enumerate(stats):
            dws = dws_map.get(s["word"])
            writer.writerow([
                i + 1, s["word"], s["total_frequency"], s["title_frequency"],
                s["comment_frequency"], s["danmaku_frequency"], s["video_count"],
                round((dws.heat_score if dws else 0), 4), (dws.rank_change if dws else 0)
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
                "word": s["word"],
                "total_frequency": s["total_frequency"],
                "title_frequency": s["title_frequency"],
                "comment_frequency": s["comment_frequency"],
                "danmaku_frequency": s["danmaku_frequency"],
                "video_count": s["video_count"],
                "heat_score": round((dws_map.get(s["word"]).heat_score if dws_map.get(s["word"]) else 0), 4),
                "rank_change": (dws_map.get(s["word"]).rank_change if dws_map.get(s["word"]) else 0)
            }
            for i, s in enumerate(stats)
        ]
        return {"stat_date": str(latest_date), "keywords": data}
