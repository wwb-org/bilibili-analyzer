"""
管理员API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User, CrawlLog, UserRole

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
