-- B站视频内容趋势分析系统 数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS bilibili_analyzer DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE bilibili_analyzer;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 视频表
CREATE TABLE IF NOT EXISTS videos (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    bvid VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    author_id BIGINT,
    author_name VARCHAR(100),
    play_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    coin_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,
    danmaku_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    publish_time DATETIME,
    duration INT,
    cover_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_bvid (bvid),
    INDEX idx_category (category),
    INDEX idx_author_id (author_id),
    INDEX idx_publish_time (publish_time),
    INDEX idx_play_count (play_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 评论表
CREATE TABLE IF NOT EXISTS comments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    video_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    user_name VARCHAR(100),
    sentiment_score FLOAT,
    like_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_id (video_id),
    INDEX idx_sentiment (sentiment_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 弹幕表
CREATE TABLE IF NOT EXISTS danmakus (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    video_id BIGINT NOT NULL,
    content VARCHAR(500) NOT NULL,
    send_time FLOAT,
    color VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_id (video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 热词统计表
CREATE TABLE IF NOT EXISTS keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(50) NOT NULL,
    frequency INT DEFAULT 0,
    category VARCHAR(50),
    stat_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_word (word),
    INDEX idx_stat_date (stat_date),
    INDEX idx_frequency (frequency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 采集日志表
CREATE TABLE IF NOT EXISTS crawl_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    status VARCHAR(20),
    video_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    error_msg TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入默认管理员账号 (密码: admin123)
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.Xqt8F.qAu', 'admin')
ON DUPLICATE KEY UPDATE username=username;


-- ==================== 数据仓库表 ====================

-- DWD层：视频每日快照表
CREATE TABLE IF NOT EXISTS dwd_video_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    video_id BIGINT NOT NULL,
    bvid VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    author_id BIGINT,
    author_name VARCHAR(100),
    play_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    coin_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,
    danmaku_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    interaction_rate FLOAT DEFAULT 0,
    like_rate FLOAT DEFAULT 0,
    play_increment INT DEFAULT 0,
    like_increment INT DEFAULT 0,
    comment_increment INT DEFAULT 0,
    publish_time DATETIME,
    duration INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_video_snapshot_date (video_id, snapshot_date),
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_bvid (bvid),
    INDEX idx_category_date (category, snapshot_date),
    INDEX idx_play_count_date (snapshot_date, play_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频每日快照表';

-- DWD层：评论每日增量表
CREATE TABLE IF NOT EXISTS dwd_comment_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL,
    comment_id BIGINT NOT NULL,
    rpid BIGINT NOT NULL,
    video_id BIGINT NOT NULL,
    bvid VARCHAR(20),
    category VARCHAR(50),
    content TEXT,
    user_name VARCHAR(100),
    sentiment_score FLOAT,
    sentiment_label VARCHAR(20),
    like_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_comment_daily_date (comment_id, stat_date),
    INDEX idx_stat_date (stat_date),
    INDEX idx_video_id (video_id),
    INDEX idx_sentiment_date (stat_date, sentiment_label),
    INDEX idx_category_date_comment (stat_date, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论每日增量表';

-- DWS层：每日全局统计表
CREATE TABLE IF NOT EXISTS dws_stats_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,
    total_videos INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    total_play_count BIGINT DEFAULT 0,
    total_like_count BIGINT DEFAULT 0,
    total_coin_count BIGINT DEFAULT 0,
    total_danmaku_count BIGINT DEFAULT 0,
    new_videos INT DEFAULT 0,
    new_comments INT DEFAULT 0,
    play_increment BIGINT DEFAULT 0,
    like_increment BIGINT DEFAULT 0,
    avg_play_count FLOAT DEFAULT 0,
    avg_like_count FLOAT DEFAULT 0,
    avg_interaction_rate FLOAT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日全局统计表';

-- DWS层：每日分区统计表
CREATE TABLE IF NOT EXISTS dws_category_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    video_count INT DEFAULT 0,
    new_video_count INT DEFAULT 0,
    total_play_count BIGINT DEFAULT 0,
    avg_play_count FLOAT DEFAULT 0,
    play_increment BIGINT DEFAULT 0,
    total_like_count BIGINT DEFAULT 0,
    total_coin_count BIGINT DEFAULT 0,
    avg_interaction_rate FLOAT DEFAULT 0,
    comment_count INT DEFAULT 0,
    new_comment_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_category_daily_date (stat_date, category),
    INDEX idx_stat_date (stat_date),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日分区统计表';

-- DWS层：每日情感统计表
CREATE TABLE IF NOT EXISTS dws_sentiment_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL,
    category VARCHAR(50) DEFAULT 'all',
    positive_count INT DEFAULT 0,
    neutral_count INT DEFAULT 0,
    negative_count INT DEFAULT 0,
    total_count INT DEFAULT 0,
    positive_rate FLOAT DEFAULT 0,
    neutral_rate FLOAT DEFAULT 0,
    negative_rate FLOAT DEFAULT 0,
    avg_sentiment_score FLOAT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sentiment_daily_date (stat_date, category),
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日情感统计表';

-- DWS层：视频热度趋势表
CREATE TABLE IF NOT EXISTS dws_video_trend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    video_id BIGINT NOT NULL,
    bvid VARCHAR(20) NOT NULL,
    trend_date DATE NOT NULL,
    trend_days INT DEFAULT 7,
    play_trend FLOAT DEFAULT 0,
    like_trend FLOAT DEFAULT 0,
    heat_score FLOAT DEFAULT 0,
    rank_by_play INT DEFAULT 0,
    rank_by_heat INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_video_trend_date (video_id, trend_date),
    INDEX idx_trend_date (trend_date),
    INDEX idx_bvid (bvid),
    INDEX idx_heat_score_date (trend_date, heat_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频热度趋势表';
