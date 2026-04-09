USE bilibili_analyzer;

ALTER TABLE `comments`
  ADD COLUMN `emotion_label` varchar(32) NULL DEFAULT NULL COMMENT 'GoEmotions 28类主情绪' AFTER `sentiment_score`,
  ADD COLUMN `emotion_scores_json` json NULL COMMENT 'GoEmotions 28类情绪概率分布' AFTER `emotion_label`,
  ADD COLUMN `emotion_model_version` varchar(128) NULL DEFAULT NULL COMMENT '情绪模型版本' AFTER `emotion_scores_json`,
  ADD COLUMN `emotion_analyzed_at` datetime NULL DEFAULT NULL COMMENT '情绪分析时间' AFTER `emotion_model_version`;

ALTER TABLE `comments`
  ADD INDEX `idx_comments_emotion_label` (`emotion_label`),
  ADD INDEX `idx_comments_video_emotion` (`video_id`, `emotion_label`);

