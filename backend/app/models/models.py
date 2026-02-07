"""
数据模型定义
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime, Boolean, UniqueConstraint
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Video(Base):
    """视频表"""
    __tablename__ = "videos"

    id = Column(BigInteger, primary_key=True, index=True)
    bvid = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)
    author_id = Column(BigInteger, index=True)
    author_name = Column(String(100))
    play_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    coin_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    danmaku_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    publish_time = Column(DateTime)
    duration = Column(Integer)  # 视频时长（秒）
    cover_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class Comment(Base):
    """评论表"""
    __tablename__ = "comments"

    id = Column(BigInteger, primary_key=True, index=True)
    rpid = Column(BigInteger, unique=True, index=True)  # B站评论ID，用于去重
    video_id = Column(BigInteger, index=True, nullable=False)
    content = Column(Text, nullable=False)
    user_name = Column(String(100))
    sentiment_score = Column(Float)  # 情感分数 0-1
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Danmaku(Base):
    """弹幕表"""
    __tablename__ = "danmakus"

    id = Column(BigInteger, primary_key=True, index=True)
    video_id = Column(BigInteger, index=True, nullable=False)
    content = Column(String(500), nullable=False)
    send_time = Column(Float)  # 视频内时间点
    color = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class Keyword(Base):
    """热词统计表"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), index=True, nullable=False)
    frequency = Column(Integer, default=0)
    category = Column(String(50))
    stat_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrawlLog(Base):
    """采集日志表"""
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False)
    status = Column(String(20))  # running, success, failed
    video_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    danmaku_count = Column(Integer, default=0)
    error_msg = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)


class KeywordAlertSubscription(Base):
    """热词预警订阅配置"""
    __tablename__ = "keyword_alert_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    enabled = Column(Boolean, default=True)

    # 触发阈值
    min_frequency = Column(Integer, default=20)
    growth_threshold = Column(Float, default=1.0)  # 频次涨幅阈值（1.0=100%）
    opportunity_sentiment_threshold = Column(Float, default=0.6)
    negative_sentiment_threshold = Column(Float, default=0.4)
    interaction_threshold = Column(Float, default=0.05)
    top_k = Column(Integer, default=10)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', name='uk_keyword_alert_subscriptions_user'),
    )
