"""
用户认证API
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import requests as http_requests

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    oauth2_scheme
)
from app.core.config import settings
from app.models import User

router = APIRouter()


# Pydantic模型
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: Optional[datetime] = None
    bilibili_uid: Optional[int] = None
    bilibili_name: Optional[str] = None
    bilibili_avatar: Optional[str] = None
    bilibili_sign: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class BindBilibiliRequest(BaseModel):
    uid: int


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 验证新密码长度
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度不能少于6位"
        )

    # 更新密码
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()

    return {"message": "密码修改成功"}


@router.put("/bind-bilibili")
def bind_bilibili(
    data: BindBilibiliRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """绑定B站账号"""
    try:
        resp = http_requests.get(
            f"https://api.bilibili.com/x/space/acc/info?mid={data.uid}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
            },
            timeout=10,
        )
        result = resp.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求B站API失败，请稍后重试")

    if result.get("code") != 0:
        raise HTTPException(status_code=400, detail=f"B站UID无效或获取信息失败: {result.get('message', '未知错误')}")

    info = result["data"]
    current_user.bilibili_uid = data.uid
    current_user.bilibili_name = info.get("name", "")
    current_user.bilibili_avatar = info.get("face", "")
    current_user.bilibili_sign = info.get("sign", "")
    db.commit()
    db.refresh(current_user)

    return UserResponse.from_orm(current_user) if hasattr(UserResponse, 'from_orm') else UserResponse.model_validate(current_user)


@router.delete("/unbind-bilibili")
def unbind_bilibili(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """解绑B站账号"""
    current_user.bilibili_uid = None
    current_user.bilibili_name = None
    current_user.bilibili_avatar = None
    current_user.bilibili_sign = None
    db.commit()

    return {"message": "已解绑B站账号"}
