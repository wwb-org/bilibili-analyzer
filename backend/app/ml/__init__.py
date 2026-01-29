"""
机器学习模块
包含热度预测和相似推荐功能
"""
from app.ml.features import FeatureExtractor
from app.ml.predictor import HotPredictor, hot_predictor
from app.ml.recommender import VideoRecommender, video_recommender
from app.ml.model_manager import ModelManager, model_manager

__all__ = [
    'FeatureExtractor',
    'HotPredictor',
    'hot_predictor',
    'VideoRecommender',
    'video_recommender',
    'ModelManager',
    'model_manager'
]
