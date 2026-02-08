"""
管理员API
"""
import re
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from pydantic import BaseModel, field_validator

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, CrawlLog, UserRole, Video, Comment, Danmaku
from app.models.warehouse import (
    DwdVideoSnapshot, DwdCommentDaily, DwdKeywordDaily,
    DwsStatsDaily, DwsCategoryDaily, DwsSentimentDaily,
    DwsVideoTrend, DwsKeywordStats,
)
from app.etl.scheduler import etl_scheduler
from app.services.crawl_service import CrawlService

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


class CrawlLogResponse(BaseModel):
    id: int
    task_name: str
    status: str
    video_count: int
    comment_count: int = 0
    danmaku_count: int = 0
    error_msg: str | None
    started_at: datetime | None
    finished_at: datetime | None

    class Config:
        from_attributes = True


class CrawlStartRequest(BaseModel):
    """采集任务请求"""
    max_videos: int = 50
    comments_per_video: int = 100
    danmakus_per_video: int = 500


class BatchCrawlRequest(BaseModel):
    """批量采集请求"""
    bvids: List[str]
    comments_per_video: int = 100
    danmakus_per_video: int = 500

    @field_validator('bvids')
    @classmethod
    def validate_bvids(cls, v):
        if not v:
            raise ValueError('BVID列表不能为空')
        if len(v) > 50:
            raise ValueError('单次最多采集50个视频')
        # 验证BVID格式
        pattern = re.compile(r'^BV[a-zA-Z0-9]{10}$')
        invalid = [bvid for bvid in v if not pattern.match(bvid)]
        if invalid:
            raise ValueError(f'无效的BVID格式: {invalid[:3]}')
        # 去重
        return list(set(v))


class ETLRunRequest(BaseModel):
    """ETL执行请求"""
    stat_date: Optional[date] = None


class ETLBackfillRequest(BaseModel):
    """ETL回填请求"""
    start_date: date
    end_date: date


@router.post("/crawl/start")
def start_crawl(
    request: CrawlStartRequest = CrawlStartRequest(),
    background_tasks: BackgroundTasks = None,
    admin: User = Depends(require_admin)
):
    """
    手动触发数据采集

    在后台执行采集任务，立即返回任务启动状态
    """
    def run_crawl_task():
        """后台采集任务"""
        service = CrawlService()
        service.crawl_popular_videos(
            max_videos=request.max_videos,
            comments_per_video=request.comments_per_video,
            danmakus_per_video=request.danmakus_per_video
        )

    background_tasks.add_task(run_crawl_task)

    return {
        "message": "采集任务已启动",
        "config": {
            "max_videos": request.max_videos,
            "comments_per_video": request.comments_per_video,
            "danmakus_per_video": request.danmakus_per_video
        },
        "status": "running"
    }


@router.get("/crawl/status")
def get_crawl_status(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """获取最近一次采集任务的状态"""
    latest_log = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).first()

    if not latest_log:
        return {"status": "no_task", "message": "暂无采集记录"}

    return {
        "id": latest_log.id,
        "task_name": latest_log.task_name,
        "status": latest_log.status,
        "video_count": latest_log.video_count or 0,
        "comment_count": latest_log.comment_count or 0,
        "danmaku_count": latest_log.danmaku_count or 0,
        "started_at": latest_log.started_at.isoformat() if latest_log.started_at else None,
        "finished_at": latest_log.finished_at.isoformat() if latest_log.finished_at else None,
        "error_msg": latest_log.error_msg
    }


@router.get("/crawl/logs", response_model=List[CrawlLogResponse])
def get_crawl_logs(
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """获取采集日志"""
    logs = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(limit).all()
    return logs


@router.post("/crawl/batch")
def start_batch_crawl(
    request: BatchCrawlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    批量采集指定视频

    输入BVID列表，后台采集视频详情、评论、弹幕
    单次最多支持50个视频
    """
    # 创建日志记录（用于追踪任务状态）
    log = CrawlLog(
        task_name=f'批量采集({len(request.bvids)}个视频)',
        status='running',
        started_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    task_id = log.id

    def run_batch_crawl_task():
        """后台批量采集任务"""
        service = CrawlService()
        service.crawl_batch_videos(
            bvids=request.bvids,
            comments_per_video=request.comments_per_video,
            danmakus_per_video=request.danmakus_per_video,
            log_id=task_id
        )

    background_tasks.add_task(run_batch_crawl_task)

    return {
        "message": "批量采集任务已启动",
        "task_id": task_id,
        "config": {
            "bvids_count": len(request.bvids),
            "comments_per_video": request.comments_per_video,
            "danmakus_per_video": request.danmakus_per_video
        },
        "status": "running"
    }


@router.get("/users")
def get_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """获取用户列表"""
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "role": u.role} for u in users]


# ==================== ETL管理接口 ====================

@router.get("/etl/status")
def get_etl_status(admin: User = Depends(require_admin)):
    """
    获取ETL调度器状态

    返回调度器运行状态和定时任务信息
    """
    return etl_scheduler.get_status()


@router.post("/etl/run")
def run_etl(
    request: ETLRunRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin)
):
    """
    手动执行ETL

    立即执行一次ETL任务，可指定统计日期
    默认处理昨日数据
    """
    stat_date = request.stat_date

    # 在后台执行ETL
    background_tasks.add_task(etl_scheduler.run_daily_etl, stat_date)

    return {
        "message": "ETL任务已提交",
        "stat_date": str(stat_date) if stat_date else "昨日",
        "status": "running"
    }


@router.post("/etl/run-sync")
def run_etl_sync(
    request: ETLRunRequest,
    admin: User = Depends(require_admin)
):
    """
    同步执行ETL

    立即执行ETL任务并等待完成，返回执行结果
    注意：可能耗时较长
    """
    try:
        results = etl_scheduler.run_daily_etl(request.stat_date)
        return {
            "message": "ETL执行完成",
            "stat_date": str(request.stat_date) if request.stat_date else "昨日",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL执行失败: {str(e)}")


@router.post("/etl/backfill")
def run_etl_backfill(
    request: ETLBackfillRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin)
):
    """
    历史数据回填

    批量执行指定日期范围的ETL任务
    """
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    # 计算天数
    days = (request.end_date - request.start_date).days + 1
    if days > 90:
        raise HTTPException(status_code=400, detail="回填范围不能超过90天")

    # 在后台执行回填
    background_tasks.add_task(etl_scheduler.backfill, request.start_date, request.end_date)

    return {
        "message": "回填任务已提交",
        "start_date": str(request.start_date),
        "end_date": str(request.end_date),
        "total_days": days,
        "status": "running"
    }


@router.post("/etl/scheduler/start")
def start_etl_scheduler(admin: User = Depends(require_admin)):
    """启动ETL调度器"""
    etl_scheduler.start()
    return {"message": "ETL调度器已启动", "status": etl_scheduler.get_status()}


@router.post("/etl/scheduler/stop")
def stop_etl_scheduler(admin: User = Depends(require_admin)):
    """停止ETL调度器"""
    etl_scheduler.stop()
    return {"message": "ETL调度器已停止", "status": etl_scheduler.get_status()}


# ==================== B站Cookie管理接口 ====================

class BilibiliCookieRequest(BaseModel):
    """Cookie更新请求"""
    cookie: str


@router.get("/bilibili/status")
def get_bilibili_status(admin: User = Depends(require_admin)):
    """
    获取B站Cookie状态

    返回当前Cookie的验证状态和用户信息
    """
    from app.services.bilibili_auth import get_cookie_status
    return get_cookie_status()


@router.post("/bilibili/verify")
def verify_bilibili_cookie(
    request: BilibiliCookieRequest,
    admin: User = Depends(require_admin)
):
    """
    验证B站Cookie有效性

    仅验证Cookie，不保存
    """
    from app.services.bilibili_auth import validate_cookie
    return validate_cookie(request.cookie)


@router.post("/bilibili/cookie")
def update_bilibili_cookie(
    request: BilibiliCookieRequest,
    admin: User = Depends(require_admin)
):
    """
    更新B站Cookie

    验证Cookie有效后保存到.env文件
    """
    from app.services.bilibili_auth import validate_cookie, update_cookie_in_env
    from app.core.config import reload_settings

    # 先验证Cookie
    result = validate_cookie(request.cookie)

    if not result.get("valid") or not result.get("logged_in"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Cookie无效或已过期")
        )

    # 保存到.env文件
    if not update_cookie_in_env(request.cookie):
        raise HTTPException(status_code=500, detail="保存Cookie失败")

    # 重新加载配置
    reload_settings()

    return {
        "message": "Cookie更新成功",
        "username": result.get("username"),
        "uid": result.get("uid")
    }


# ==================== 数据概览接口 ====================

@router.get("/data-overview")
def get_data_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    数据概览：展示 ODS / DWD / DWS 三层数据的按日期统计

    帮助管理员了解已采集哪些数据、哪些已整理、哪些未处理。
    """
    # ---------- ODS 层汇总 ----------
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    total_comments = db.query(func.count(Comment.id)).scalar() or 0
    total_danmakus = db.query(func.count(Danmaku.id)).scalar() or 0

    earliest_date = db.query(func.min(func.date(Video.created_at))).scalar()
    latest_date = db.query(func.max(func.date(Video.created_at))).scalar()

    # ---------- ODS 按日期统计 ----------
    video_date_col = func.date(Video.created_at)
    ods_video_counts = dict(
        db.query(video_date_col, func.count(Video.id))
        .group_by(video_date_col).all()
    )
    comment_date_col = func.date(Comment.created_at)
    ods_comment_counts = dict(
        db.query(comment_date_col, func.count(Comment.id))
        .group_by(comment_date_col).all()
    )
    danmaku_date_col = func.date(Danmaku.created_at)
    ods_danmaku_counts = dict(
        db.query(danmaku_date_col, func.count(Danmaku.id))
        .group_by(danmaku_date_col).all()
    )

    # ---------- DWD 按日期统计 ----------
    dwd_snapshot_counts = dict(
        db.query(
            DwdVideoSnapshot.snapshot_date,
            func.count(DwdVideoSnapshot.id)
        ).group_by(DwdVideoSnapshot.snapshot_date).all()
    )
    dwd_comment_counts = dict(
        db.query(
            DwdCommentDaily.stat_date,
            func.count(DwdCommentDaily.id)
        ).group_by(DwdCommentDaily.stat_date).all()
    )
    dwd_keyword_counts = dict(
        db.query(
            DwdKeywordDaily.stat_date,
            func.count(DwdKeywordDaily.id)
        ).group_by(DwdKeywordDaily.stat_date).all()
    )

    # ---------- DWS 已有日期集合 ----------
    dws_stats_dates = {
        row[0] for row in
        db.query(DwsStatsDaily.stat_date).all()
    }
    dws_category_dates = {
        row[0] for row in
        db.query(func.distinct(DwsCategoryDaily.stat_date)).all()
    }
    dws_sentiment_dates = {
        row[0] for row in
        db.query(func.distinct(DwsSentimentDaily.stat_date)).all()
    }
    dws_video_trend_dates = {
        row[0] for row in
        db.query(func.distinct(DwsVideoTrend.trend_date)).all()
    }
    dws_keyword_stats_dates = {
        row[0] for row in
        db.query(func.distinct(DwsKeywordStats.stat_date)).all()
    }

    # ---------- 合并所有日期 ----------
    all_dates = set()
    for d in ods_video_counts:
        all_dates.add(d)
    for d in ods_comment_counts:
        all_dates.add(d)
    for d in ods_danmaku_counts:
        all_dates.add(d)
    for d in dwd_snapshot_counts:
        all_dates.add(d)
    for d in dwd_comment_counts:
        all_dates.add(d)
    for d in dwd_keyword_counts:
        all_dates.add(d)
    all_dates.update(dws_stats_dates)
    all_dates.update(dws_category_dates)
    all_dates.update(dws_sentiment_dates)
    all_dates.update(dws_video_trend_dates)
    all_dates.update(dws_keyword_stats_dates)

    # ---------- 构建每日明细 ----------
    daily_details = []
    for d in sorted(all_dates, reverse=True):
        ods_v = ods_video_counts.get(d, 0)
        ods_c = ods_comment_counts.get(d, 0)
        ods_d = ods_danmaku_counts.get(d, 0)

        dwd_snap = dwd_snapshot_counts.get(d, 0)
        dwd_comm = dwd_comment_counts.get(d, 0)
        dwd_kw = dwd_keyword_counts.get(d, 0)

        has_stats = d in dws_stats_dates
        has_category = d in dws_category_dates
        has_sentiment = d in dws_sentiment_dates
        has_trend = d in dws_video_trend_dates
        has_kw_stats = d in dws_keyword_stats_dates

        # 判断 ETL 状态
        dwd_done = dwd_snap > 0 or dwd_comm > 0 or dwd_kw > 0
        dws_done = has_stats and has_category and has_sentiment and has_trend and has_kw_stats
        if dwd_done and dws_done:
            etl_status = "complete"
        elif dwd_done or has_stats or has_category or has_sentiment or has_trend or has_kw_stats:
            etl_status = "partial"
        else:
            etl_status = "missing"

        daily_details.append({
            "date": str(d),
            "ods_videos": ods_v,
            "ods_comments": ods_c,
            "ods_danmakus": ods_d,
            "dwd_video_snapshot": dwd_snap,
            "dwd_comment_daily": dwd_comm,
            "dwd_keyword_daily": dwd_kw,
            "dws_stats": has_stats,
            "dws_category": has_category,
            "dws_sentiment": has_sentiment,
            "dws_video_trend": has_trend,
            "dws_keyword_stats": has_kw_stats,
            "etl_status": etl_status,
        })

    return {
        "ods": {
            "videos": total_videos,
            "comments": total_comments,
            "danmakus": total_danmakus,
            "earliest_date": str(earliest_date) if earliest_date else None,
            "latest_date": str(latest_date) if latest_date else None,
        },
        "daily_details": daily_details,
    }
