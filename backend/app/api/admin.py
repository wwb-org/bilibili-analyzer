"""
管理员API
"""
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, CrawlLog, UserRole
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
