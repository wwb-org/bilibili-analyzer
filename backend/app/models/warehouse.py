"""
数据仓库模型定义

DWD层（明细数据层）：
- DwdVideoSnapshot: 视频每日快照
- DwdCommentDaily: 评论每日增量
- DwdKeywordDaily: 热词每日明细

DWS层（汇总数据层）：
- DwsStatsDaily: 每日全局统计
- DwsCategoryDaily: 每日分区统计
- DwsSentimentDaily: 每日情感统计
- DwsVideoTrend: 视频热度趋势
- DwsKeywordStats: 热词聚合统计
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime, Date, UniqueConstraint, Index
from app.core.database import Base


# ==================== DWD层（明细数据层） ====================

class DwdVideoSnapshot(Base):
    """
    视频每日快照表

    用途：保留视频统计数据的每日快照，追踪热度变化
    数据来源：videos 表
    更新频率：每日
    """
    __tablename__ = "dwd_video_snapshot"

    id = Column(BigInteger, primary_key=True, index=True)

    # 快照日期（分区键）
    snapshot_date = Column(Date, nullable=False, index=True)

    # 视频基础信息
    video_id = Column(BigInteger, nullable=False, index=True)
    bvid = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), index=True)
    author_id = Column(BigInteger)
    author_name = Column(String(100))

    # 当日统计数据（快照值）
    play_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    coin_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    danmaku_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # 衍生指标（ETL时计算）
    interaction_rate = Column(Float, default=0)  # 互动率 = (like+coin+share+favorite) / play
    like_rate = Column(Float, default=0)         # 点赞率 = like / play

    # 增量指标（与前一天比较）
    play_increment = Column(Integer, default=0)      # 播放增量
    like_increment = Column(Integer, default=0)      # 点赞增量
    comment_increment = Column(Integer, default=0)   # 评论增量

    # 元数据
    publish_time = Column(DateTime)
    duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('video_id', 'snapshot_date', name='uk_video_snapshot_date'),
        Index('idx_category_date', 'category', 'snapshot_date'),
        Index('idx_play_count_date', 'snapshot_date', 'play_count'),
    )


class DwdCommentDaily(Base):
    """
    评论每日增量表

    用途：记录每日新增评论及其情感分析结果
    数据来源：comments 表
    更新频率：每日
    """
    __tablename__ = "dwd_comment_daily"

    id = Column(BigInteger, primary_key=True, index=True)

    # 统计日期
    stat_date = Column(Date, nullable=False, index=True)

    # 评论信息
    comment_id = Column(BigInteger, nullable=False, index=True)
    rpid = Column(BigInteger, nullable=True)  # B站评论ID，可能为空
    video_id = Column(BigInteger, nullable=False, index=True)
    bvid = Column(String(20))
    category = Column(String(50), index=True)  # 视频分区（冗余）
    content = Column(Text)
    user_name = Column(String(100))

    # 情感分析
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))  # positive/neutral/negative

    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('comment_id', 'stat_date', name='uk_comment_daily_date'),
        Index('idx_sentiment_date', 'stat_date', 'sentiment_label'),
        Index('idx_category_date_comment', 'stat_date', 'category'),
    )


# ==================== DWS层（汇总数据层） ====================

class DwsStatsDaily(Base):
    """
    每日全局统计表

    用途：预聚合每日全局统计数据，优化 /overview 和 /trends 接口
    数据来源：dwd_video_snapshot, dwd_comment_daily
    更新频率：每日
    """
    __tablename__ = "dws_stats_daily"

    id = Column(Integer, primary_key=True, index=True)

    # 统计日期
    stat_date = Column(Date, nullable=False, unique=True, index=True)

    # 累计指标（截至当日）
    total_videos = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_play_count = Column(BigInteger, default=0)
    total_like_count = Column(BigInteger, default=0)
    total_coin_count = Column(BigInteger, default=0)
    total_danmaku_count = Column(BigInteger, default=0)

    # 当日新增
    new_videos = Column(Integer, default=0)
    new_comments = Column(Integer, default=0)

    # 当日播放增量（所有视频播放量之和的增长）
    play_increment = Column(BigInteger, default=0)
    like_increment = Column(BigInteger, default=0)

    # 平均值
    avg_play_count = Column(Float, default=0)
    avg_like_count = Column(Float, default=0)
    avg_interaction_rate = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DwsCategoryDaily(Base):
    """
    每日分区统计表

    用途：预聚合每日分区统计，优化 /categories 接口
    数据来源：dwd_video_snapshot
    更新频率：每日
    """
    __tablename__ = "dws_category_daily"

    id = Column(Integer, primary_key=True, index=True)

    stat_date = Column(Date, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)

    # 视频数量
    video_count = Column(Integer, default=0)
    new_video_count = Column(Integer, default=0)

    # 播放统计
    total_play_count = Column(BigInteger, default=0)
    avg_play_count = Column(Float, default=0)
    play_increment = Column(BigInteger, default=0)

    # 互动统计
    total_like_count = Column(BigInteger, default=0)
    total_coin_count = Column(BigInteger, default=0)
    avg_interaction_rate = Column(Float, default=0)

    # 评论统计
    comment_count = Column(Integer, default=0)
    new_comment_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('stat_date', 'category', name='uk_category_daily_date'),
    )


class DwsSentimentDaily(Base):
    """
    每日情感统计表

    用途：预聚合情感分布，优化 /sentiment 接口
    数据来源：dwd_comment_daily
    更新频率：每日
    """
    __tablename__ = "dws_sentiment_daily"

    id = Column(Integer, primary_key=True, index=True)

    stat_date = Column(Date, nullable=False, index=True)
    category = Column(String(50), default='all')  # 分区，'all'表示全局

    # 情感分布
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    # 情感占比
    positive_rate = Column(Float, default=0)
    neutral_rate = Column(Float, default=0)
    negative_rate = Column(Float, default=0)

    # 平均情感分
    avg_sentiment_score = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('stat_date', 'category', name='uk_sentiment_daily_date'),
    )


class DwsVideoTrend(Base):
    """
    视频热度趋势表

    用途：追踪单个视频的热度变化趋势
    数据来源：dwd_video_snapshot
    更新频率：每日
    """
    __tablename__ = "dws_video_trend"

    id = Column(BigInteger, primary_key=True, index=True)

    video_id = Column(BigInteger, nullable=False, index=True)
    bvid = Column(String(20), nullable=False, index=True)

    # 趋势区间
    trend_date = Column(Date, nullable=False, index=True)  # 趋势计算日期
    trend_days = Column(Integer, default=7)  # 趋势周期（默认7天）

    # 趋势指标
    play_trend = Column(Float, default=0)   # 播放增长率
    like_trend = Column(Float, default=0)   # 点赞增长率
    heat_score = Column(Float, default=0)   # 综合热度分

    # 排名
    rank_by_play = Column(Integer, default=0)
    rank_by_heat = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('video_id', 'trend_date', name='uk_video_trend_date'),
        Index('idx_heat_score_date', 'trend_date', 'heat_score'),
    )


# ==================== DWD层 - 热词分析 ====================

class DwdKeywordDaily(Base):
    """
    热词每日明细表

    用途：记录每日热词的详细信息，区分不同来源
    数据来源：videos.title, comments.content, danmakus.content
    更新频率：每日
    """
    __tablename__ = "dwd_keyword_daily"

    id = Column(BigInteger, primary_key=True, index=True)

    # 统计日期
    stat_date = Column(Date, nullable=False, index=True)

    # 热词信息
    word = Column(String(50), nullable=False, index=True)
    source = Column(String(20), nullable=False)  # title, comment, danmaku
    category = Column(String(50), index=True)  # 视频分区（可选）

    # 统计指标
    frequency = Column(Integer, default=0)  # 当日频次
    video_count = Column(Integer, default=0)  # 关联视频数
    avg_sentiment = Column(Float)  # 平均情感分（评论来源时有效）

    # 示例视频（JSON数组，最多5个BVID）
    sample_bvids = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('word', 'stat_date', 'source', 'category', name='uk_keyword_daily'),
        Index('idx_keyword_date_freq', 'stat_date', 'frequency'),
        Index('idx_keyword_source', 'stat_date', 'source'),
    )


class DwsKeywordStats(Base):
    """
    热词聚合统计表

    用途：预聚合热词统计，优化热词分析查询
    数据来源：dwd_keyword_daily
    更新频率：每日
    """
    __tablename__ = "dws_keyword_stats"

    id = Column(Integer, primary_key=True, index=True)

    # 统计日期
    stat_date = Column(Date, nullable=False, index=True)

    # 热词
    word = Column(String(50), nullable=False, index=True)

    # 各来源频次
    title_frequency = Column(Integer, default=0)  # 标题来源频次
    comment_frequency = Column(Integer, default=0)  # 评论来源频次
    danmaku_frequency = Column(Integer, default=0)  # 弹幕来源频次
    total_frequency = Column(Integer, default=0)  # 总频次

    # 聚合统计
    video_count = Column(Integer, default=0)  # 关联视频总数
    category_distribution = Column(Text)  # 分区分布（JSON格式）
    avg_sentiment = Column(Float)  # 平均情感分

    # 趋势指标
    frequency_trend = Column(Float, default=0)  # 7日频次变化率
    rank_change = Column(Integer, default=0)  # 排名变化（正数上升，负数下降）
    heat_score = Column(Float, default=0)  # 综合热度分

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('word', 'stat_date', name='uk_keyword_stats'),
        Index('idx_keyword_stats_freq', 'stat_date', 'total_frequency'),
        Index('idx_keyword_stats_heat', 'stat_date', 'heat_score'),
    )
