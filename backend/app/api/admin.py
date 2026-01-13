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
    error_msg: str | None

    class Config:
        from_attributes = True


class ETLRunRequest(BaseModel):
    """ETL执行请求"""
    stat_date: Optional[date] = None


class ETLBackfillRequest(BaseModel):
    """ETL回填请求"""
    start_date: date
    end_date: date


@router.post("/crawl/start")
def start_crawl(admin: User = Depends(require_admin)):
    """手动触发数据采集"""
    # TODO: 触发后台采集任务
    return {"message": "采集任务已启动", "task_id": 1}


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
