/*
 Navicat Premium Dump SQL

 Source Server         : localhost_3306
 Source Server Type    : MySQL
 Source Server Version : 80043 (8.0.43)
 Source Host           : localhost:3306
 Source Schema         : bilibili_analyzer

 Target Server Type    : MySQL
 Target Server Version : 80043 (8.0.43)
 File Encoding         : 65001

 Date: 19/01/2026 21:08:46
*/

CREATE DATABASE IF NOT EXISTS bilibili_analyzer DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE bilibili_analyzer;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for comments
-- ----------------------------
DROP TABLE IF EXISTS `comments`;
CREATE TABLE `comments`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rpid` bigint NULL DEFAULT NULL,
  `video_id` bigint NOT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `sentiment_score` float NULL DEFAULT NULL,
  `like_count` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `idx_rpid`(`rpid` ASC) USING BTREE,
  INDEX `ix_comments_video_id`(`video_id` ASC) USING BTREE,
  INDEX `ix_comments_id`(`id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 127 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for crawl_logs
-- ----------------------------
DROP TABLE IF EXISTS `crawl_logs`;
CREATE TABLE `crawl_logs`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_count` int NULL DEFAULT NULL,
  `comment_count` int NULL DEFAULT NULL,
  `error_msg` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `started_at` datetime NULL DEFAULT NULL,
  `finished_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_crawl_logs_id`(`id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for danmakus
-- ----------------------------
DROP TABLE IF EXISTS `danmakus`;
CREATE TABLE `danmakus`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `video_id` bigint NOT NULL,
  `content` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `send_time` float NULL DEFAULT NULL,
  `color` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_danmakus_video_id`(`video_id` ASC) USING BTREE,
  INDEX `ix_danmakus_id`(`id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dwd_comment_daily
-- ----------------------------
DROP TABLE IF EXISTS `dwd_comment_daily`;
CREATE TABLE `dwd_comment_daily`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL,
  `comment_id` bigint NOT NULL,
  `rpid` bigint NULL DEFAULT NULL,
  `video_id` bigint NOT NULL,
  `bvid` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `user_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `sentiment_score` float NULL DEFAULT NULL,
  `sentiment_label` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `like_count` int NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_comment_daily_date`(`comment_id` ASC, `stat_date` ASC) USING BTREE,
  INDEX `idx_stat_date`(`stat_date` ASC) USING BTREE,
  INDEX `idx_video_id`(`video_id` ASC) USING BTREE,
  INDEX `idx_sentiment_date`(`stat_date` ASC, `sentiment_label` ASC) USING BTREE,
  INDEX `idx_category_date_comment`(`stat_date` ASC, `category` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 88 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '评论每日增量表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dwd_video_snapshot
-- ----------------------------
DROP TABLE IF EXISTS `dwd_video_snapshot`;
CREATE TABLE `dwd_video_snapshot`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `snapshot_date` date NOT NULL,
  `video_id` bigint NOT NULL,
  `bvid` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `author_id` bigint NULL DEFAULT NULL,
  `author_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `play_count` int NULL DEFAULT 0,
  `like_count` int NULL DEFAULT 0,
  `coin_count` int NULL DEFAULT 0,
  `share_count` int NULL DEFAULT 0,
  `favorite_count` int NULL DEFAULT 0,
  `danmaku_count` int NULL DEFAULT 0,
  `comment_count` int NULL DEFAULT 0,
  `interaction_rate` float NULL DEFAULT 0,
  `like_rate` float NULL DEFAULT 0,
  `play_increment` int NULL DEFAULT 0,
  `like_increment` int NULL DEFAULT 0,
  `comment_increment` int NULL DEFAULT 0,
  `publish_time` datetime NULL DEFAULT NULL,
  `duration` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_video_snapshot_date`(`video_id` ASC, `snapshot_date` ASC) USING BTREE,
  INDEX `idx_snapshot_date`(`snapshot_date` ASC) USING BTREE,
  INDEX `idx_bvid`(`bvid` ASC) USING BTREE,
  INDEX `idx_category_date`(`category` ASC, `snapshot_date` ASC) USING BTREE,
  INDEX `idx_play_count_date`(`snapshot_date` ASC, `play_count` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 30 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '视频每日快照表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dws_category_daily
-- ----------------------------
DROP TABLE IF EXISTS `dws_category_daily`;
CREATE TABLE `dws_category_daily`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `video_count` int NULL DEFAULT 0,
  `new_video_count` int NULL DEFAULT 0,
  `total_play_count` bigint NULL DEFAULT 0,
  `avg_play_count` float NULL DEFAULT 0,
  `play_increment` bigint NULL DEFAULT 0,
  `total_like_count` bigint NULL DEFAULT 0,
  `total_coin_count` bigint NULL DEFAULT 0,
  `avg_interaction_rate` float NULL DEFAULT 0,
  `comment_count` int NULL DEFAULT 0,
  `new_comment_count` int NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_category_daily_date`(`stat_date` ASC, `category` ASC) USING BTREE,
  INDEX `idx_stat_date`(`stat_date` ASC) USING BTREE,
  INDEX `idx_category`(`category` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '每日分区统计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dws_sentiment_daily
-- ----------------------------
DROP TABLE IF EXISTS `dws_sentiment_daily`;
CREATE TABLE `dws_sentiment_daily`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'all',
  `positive_count` int NULL DEFAULT 0,
  `neutral_count` int NULL DEFAULT 0,
  `negative_count` int NULL DEFAULT 0,
  `total_count` int NULL DEFAULT 0,
  `positive_rate` float NULL DEFAULT 0,
  `neutral_rate` float NULL DEFAULT 0,
  `negative_rate` float NULL DEFAULT 0,
  `avg_sentiment_score` float NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_sentiment_daily_date`(`stat_date` ASC, `category` ASC) USING BTREE,
  INDEX `idx_stat_date`(`stat_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '每日情感统计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dws_stats_daily
-- ----------------------------
DROP TABLE IF EXISTS `dws_stats_daily`;
CREATE TABLE `dws_stats_daily`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL,
  `total_videos` int NULL DEFAULT 0,
  `total_comments` int NULL DEFAULT 0,
  `total_play_count` bigint NULL DEFAULT 0,
  `total_like_count` bigint NULL DEFAULT 0,
  `total_coin_count` bigint NULL DEFAULT 0,
  `total_danmaku_count` bigint NULL DEFAULT 0,
  `new_videos` int NULL DEFAULT 0,
  `new_comments` int NULL DEFAULT 0,
  `play_increment` bigint NULL DEFAULT 0,
  `like_increment` bigint NULL DEFAULT 0,
  `avg_play_count` float NULL DEFAULT 0,
  `avg_like_count` float NULL DEFAULT 0,
  `avg_interaction_rate` float NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `stat_date`(`stat_date` ASC) USING BTREE,
  INDEX `idx_stat_date`(`stat_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '每日全局统计表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for dws_video_trend
-- ----------------------------
DROP TABLE IF EXISTS `dws_video_trend`;
CREATE TABLE `dws_video_trend`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `video_id` bigint NOT NULL,
  `bvid` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `trend_date` date NOT NULL,
  `trend_days` int NULL DEFAULT 7,
  `play_trend` float NULL DEFAULT 0,
  `like_trend` float NULL DEFAULT 0,
  `heat_score` float NULL DEFAULT 0,
  `rank_by_play` int NULL DEFAULT 0,
  `rank_by_heat` int NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_video_trend_date`(`video_id` ASC, `trend_date` ASC) USING BTREE,
  INDEX `idx_trend_date`(`trend_date` ASC) USING BTREE,
  INDEX `idx_bvid`(`bvid` ASC) USING BTREE,
  INDEX `idx_heat_score_date`(`trend_date` ASC, `heat_score` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '视频热度趋势表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for keywords
-- ----------------------------
DROP TABLE IF EXISTS `keywords`;
CREATE TABLE `keywords`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `word` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `frequency` int NULL DEFAULT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `stat_date` datetime NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `ix_keywords_id`(`id` ASC) USING BTREE,
  INDEX `ix_keywords_stat_date`(`stat_date` ASC) USING BTREE,
  INDEX `ix_keywords_word`(`word` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for keyword_alert_subscriptions
-- ----------------------------
DROP TABLE IF EXISTS `keyword_alert_subscriptions`;
CREATE TABLE `keyword_alert_subscriptions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `enabled` tinyint(1) NULL DEFAULT 1,
  `min_frequency` int NULL DEFAULT 20,
  `growth_threshold` float NULL DEFAULT 1,
  `opportunity_sentiment_threshold` float NULL DEFAULT 0.6,
  `negative_sentiment_threshold` float NULL DEFAULT 0.4,
  `interaction_threshold` float NULL DEFAULT 0.05,
  `top_k` int NULL DEFAULT 10,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_keyword_alert_subscriptions_user`(`user_id` ASC) USING BTREE,
  INDEX `ix_keyword_alert_subscriptions_user_id`(`user_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `ix_users_username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `ix_users_email`(`email` ASC) USING BTREE,
  INDEX `ix_users_id`(`id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for videos
-- ----------------------------
DROP TABLE IF EXISTS `videos`;
CREATE TABLE `videos`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `bvid` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `author_id` bigint NULL DEFAULT NULL,
  `author_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `play_count` int NULL DEFAULT NULL,
  `like_count` int NULL DEFAULT NULL,
  `coin_count` int NULL DEFAULT NULL,
  `share_count` int NULL DEFAULT NULL,
  `favorite_count` int NULL DEFAULT NULL,
  `danmaku_count` int NULL DEFAULT NULL,
  `comment_count` int NULL DEFAULT NULL,
  `publish_time` datetime NULL DEFAULT NULL,
  `duration` int NULL DEFAULT NULL,
  `cover_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `ix_videos_bvid`(`bvid` ASC) USING BTREE,
  INDEX `ix_videos_id`(`id` ASC) USING BTREE,
  INDEX `ix_videos_author_id`(`author_id` ASC) USING BTREE,
  INDEX `ix_videos_category`(`category` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 30 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
