"""
特征工程模块
负责从视频数据提取和转换预测所需的特征
"""
from typing import Dict, List
from datetime import datetime
import numpy as np


class FeatureExtractor:
    """特征提取器"""

    # 分区编码映射
    CATEGORY_ENCODING = {
        '游戏': 0, '生活': 1, '鬼畜': 2, '娱乐': 3, '音乐': 4,
        '动画': 5, '科技': 6, '影视': 7, '知识': 8, '美食': 9,
        '舞蹈': 10, '时尚': 11, '汽车': 12, '运动': 13, '动物圈': 14,
        '番剧': 15, '国创': 16, '电影': 17, '电视剧': 18, '纪录片': 19,
    }

    # 特征名称列表
    FEATURE_NAMES = [
        'like_rate', 'coin_rate', 'favorite_rate', 'share_rate',
        'danmaku_rate', 'comment_rate', 'interaction_rate',
        'publish_hour', 'publish_weekday', 'video_age_days',
        'title_length', 'has_description', 'duration_minutes',
        'category_code', 'current_play_count'
    ]

    @classmethod
    def extract_features(cls, video) -> Dict[str, float]:
        """
        从视频 ORM 对象提取特征

        Args:
            video: Video ORM 对象

        Returns:
            特征字典
        """
        play_count = max(video.play_count or 1, 1)  # 避免除零

        # 基础互动率特征
        like_rate = (video.like_count or 0) / play_count
        coin_rate = (video.coin_count or 0) / play_count
        favorite_rate = (video.favorite_count or 0) / play_count
        share_rate = (video.share_count or 0) / play_count
        danmaku_rate = (video.danmaku_count or 0) / play_count
        comment_rate = (video.comment_count or 0) / play_count

        # 综合互动率
        interaction_rate = like_rate + coin_rate + favorite_rate + share_rate

        # 时间特征
        publish_hour = 12
        publish_weekday = 0
        video_age_days = 30

        if video.publish_time:
            publish_hour = video.publish_time.hour
            publish_weekday = video.publish_time.weekday()
            video_age_days = max((datetime.now() - video.publish_time).days, 1)

        # 内容特征
        title_length = len(video.title) if video.title else 0
        has_description = 1 if video.description else 0
        duration_minutes = (video.duration or 0) / 60

        # 分区编码
        category_code = cls.CATEGORY_ENCODING.get(video.category, -1)

        return {
            'like_rate': like_rate,
            'coin_rate': coin_rate,
            'favorite_rate': favorite_rate,
            'share_rate': share_rate,
            'danmaku_rate': danmaku_rate,
            'comment_rate': comment_rate,
            'interaction_rate': interaction_rate,
            'publish_hour': publish_hour,
            'publish_weekday': publish_weekday,
            'video_age_days': video_age_days,
            'title_length': title_length,
            'has_description': has_description,
            'duration_minutes': duration_minutes,
            'category_code': category_code,
            'current_play_count': play_count,
        }

    @classmethod
    def extract_features_from_dict(cls, data: Dict) -> Dict[str, float]:
        """
        从字典数据提取特征（用于前端输入）

        Args:
            data: 包含视频信息的字典

        Returns:
            特征字典
        """
        play_count = max(data.get('play_count', 1), 1)

        like_rate = data.get('like_count', 0) / play_count
        coin_rate = data.get('coin_count', 0) / play_count
        favorite_rate = data.get('favorite_count', 0) / play_count
        share_rate = data.get('share_count', 0) / play_count
        danmaku_rate = data.get('danmaku_count', 0) / play_count
        comment_rate = data.get('comment_count', 0) / play_count

        return {
            'like_rate': like_rate,
            'coin_rate': coin_rate,
            'favorite_rate': favorite_rate,
            'share_rate': share_rate,
            'danmaku_rate': danmaku_rate,
            'comment_rate': comment_rate,
            'interaction_rate': like_rate + coin_rate + favorite_rate + share_rate,
            'publish_hour': data.get('publish_hour', 12),
            'publish_weekday': data.get('publish_weekday', 0),
            'video_age_days': max(data.get('video_age_days', 30), 1),
            'title_length': data.get('title_length', 20),
            'has_description': data.get('has_description', 1),
            'duration_minutes': data.get('duration_minutes', 5),
            'category_code': cls.CATEGORY_ENCODING.get(data.get('category', ''), -1),
            'current_play_count': play_count,
        }

    @classmethod
    def get_feature_names(cls) -> List[str]:
        """获取特征名称列表"""
        return cls.FEATURE_NAMES.copy()

    @classmethod
    def features_to_array(cls, features: Dict[str, float]) -> np.ndarray:
        """将特征字典转换为模型输入数组"""
        return np.array([[features.get(name, 0) for name in cls.FEATURE_NAMES]])

    @classmethod
    def get_feature_name_mapping(cls) -> Dict[str, str]:
        """获取特征名称到中文的映射"""
        return {
            'like_rate': '点赞率',
            'coin_rate': '投币率',
            'favorite_rate': '收藏率',
            'share_rate': '分享率',
            'danmaku_rate': '弹幕率',
            'comment_rate': '评论率',
            'interaction_rate': '综合互动率',
            'publish_hour': '发布时间',
            'publish_weekday': '发布星期',
            'video_age_days': '视频天数',
            'title_length': '标题长度',
            'has_description': '有描述',
            'duration_minutes': '视频时长',
            'category_code': '分区',
            'current_play_count': '当前播放量'
        }
