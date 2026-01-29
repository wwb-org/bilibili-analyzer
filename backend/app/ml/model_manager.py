"""
模型管理器
负责模型训练、保存、加载和更新
"""
import os
import pickle
import logging
from typing import Dict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBRegressor
from sqlalchemy.orm import Session
from sqlalchemy import func
import jieba

from app.models import Video
from app.ml.features import FeatureExtractor

logger = logging.getLogger(__name__)

# 模型目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "ml_models"


class ModelManager:
    """模型管理器"""

    # 停用词（与 recommender 保持一致）
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
        '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
        '着', '没有', '看', '好', '这', '那', '吗', '什么', '他', '她',
        '们', '这个', '那个', '真的', '可以', '其实', '怎么', '为什么',
        '啊', '哈哈', '视频', 'bilibili', 'B站', '哔哩哔哩'
    }

    def __init__(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

    def train_predictor(self, db: Session, test_size: float = 0.2) -> Dict:
        """
        训练热度预测模型

        使用现有视频数据训练 XGBoost 回归模型

        Args:
            db: 数据库会话
            test_size: 测试集比例

        Returns:
            训练结果
        """
        logger.info("开始训练热度预测模型...")

        # 获取视频数据
        videos = db.query(Video).filter(
            Video.play_count > 0,
            Video.publish_time.isnot(None)
        ).all()

        if len(videos) < 100:
            return {
                "success": False,
                "error": f"训练数据不足，需要至少 100 条视频数据，当前只有 {len(videos)} 条"
            }

        # 提取特征和标签
        X_data = []
        y_data = []

        for video in videos:
            features = FeatureExtractor.extract_features(video)
            feature_array = [features[name] for name in FeatureExtractor.get_feature_names()]
            X_data.append(feature_array)

            # 使用当前播放量作为标签
            # 由于没有历史数据，我们用一个简单的增长模型来模拟
            # 实际场景中应该使用 DWD 层的历史快照数据
            base_play = video.play_count
            # 模拟增长：互动率高的视频增长更快
            interaction_rate = features['interaction_rate']
            growth_factor = 1 + interaction_rate * 5 + np.random.uniform(0, 0.5)
            simulated_future_play = int(base_play * growth_factor)
            y_data.append(simulated_future_play)

        X = np.array(X_data)
        y = np.array(y_data)

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        # 训练 XGBoost 模型
        model = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        # 评估
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        # 保存模型
        model_path = MODEL_DIR / "xgboost_predictor.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        logger.info(f"热度预测模型训练完成，R² 分数: train={train_score:.4f}, test={test_score:.4f}")

        return {
            "success": True,
            "model_type": "XGBoost Regressor",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_r2": round(train_score, 4),
            "test_r2": round(test_score, 4),
            "feature_count": len(FeatureExtractor.get_feature_names()),
            "feature_names": FeatureExtractor.get_feature_names(),
            "model_path": str(model_path),
            "trained_at": datetime.now().isoformat()
        }

    def train_predictor_with_history(self, db: Session, test_size: float = 0.2) -> Dict:
        """
        使用历史快照数据训练预测模型（如果 DWD 层数据可用）

        Args:
            db: 数据库会话
            test_size: 测试集比例

        Returns:
            训练结果
        """
        try:
            from app.models.warehouse import DwdVideoSnapshot
        except ImportError:
            logger.warning("DWD 模型未找到，使用简单训练方法")
            return self.train_predictor(db, test_size)

        logger.info("使用历史快照数据训练热度预测模型...")

        # 查询有多天快照的视频
        video_days = db.query(
            DwdVideoSnapshot.bvid,
            func.count(DwdVideoSnapshot.id).label('day_count')
        ).group_by(DwdVideoSnapshot.bvid).having(
            func.count(DwdVideoSnapshot.id) >= 2
        ).all()

        if len(video_days) < 50:
            logger.warning("历史快照数据不足，使用简单训练方法")
            return self.train_predictor(db, test_size)

        # 构建训练数据
        X_data = []
        y_data = []

        for bvid, _ in video_days:
            snapshots = db.query(DwdVideoSnapshot).filter(
                DwdVideoSnapshot.bvid == bvid
            ).order_by(DwdVideoSnapshot.snapshot_date).all()

            if len(snapshots) < 2:
                continue

            # 使用较早的快照作为特征，最新的作为标签
            old_snap = snapshots[0]
            new_snap = snapshots[-1]

            days_diff = (new_snap.snapshot_date - old_snap.snapshot_date).days
            if days_diff < 1:
                continue

            features = self._extract_snapshot_features(old_snap)
            X_data.append([features[name] for name in FeatureExtractor.get_feature_names()])
            y_data.append(new_snap.play_count or 0)

        if len(X_data) < 50:
            logger.warning("有效训练样本不足，使用简单训练方法")
            return self.train_predictor(db, test_size)

        X = np.array(X_data)
        y = np.array(y_data)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        model = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        model_path = MODEL_DIR / "xgboost_predictor.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        return {
            "success": True,
            "model_type": "XGBoost Regressor (History-based)",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_r2": round(train_score, 4),
            "test_r2": round(test_score, 4),
            "model_path": str(model_path),
            "trained_at": datetime.now().isoformat()
        }

    def _extract_snapshot_features(self, snapshot) -> Dict:
        """从快照提取特征"""
        play = max(snapshot.play_count or 1, 1)

        publish_hour = 12
        publish_weekday = 0
        video_age_days = 30

        if snapshot.publish_time:
            publish_hour = snapshot.publish_time.hour
            publish_weekday = snapshot.publish_time.weekday()
            video_age_days = max((snapshot.snapshot_date - snapshot.publish_time.date()).days, 1)

        return {
            'like_rate': (snapshot.like_count or 0) / play,
            'coin_rate': (snapshot.coin_count or 0) / play,
            'favorite_rate': (snapshot.favorite_count or 0) / play,
            'share_rate': (snapshot.share_count or 0) / play,
            'danmaku_rate': (snapshot.danmaku_count or 0) / play,
            'comment_rate': (snapshot.comment_count or 0) / play,
            'interaction_rate': getattr(snapshot, 'interaction_rate', 0) or 0,
            'publish_hour': publish_hour,
            'publish_weekday': publish_weekday,
            'video_age_days': video_age_days,
            'title_length': len(snapshot.title) if snapshot.title else 0,
            'has_description': 0,
            'duration_minutes': (snapshot.duration or 0) / 60,
            'category_code': FeatureExtractor.CATEGORY_ENCODING.get(snapshot.category, -1),
            'current_play_count': play,
        }

    def train_recommender(self, db: Session) -> Dict:
        """
        训练推荐模型（TF-IDF 向量化器）

        Args:
            db: 数据库会话

        Returns:
            训练结果
        """
        logger.info("开始训练推荐模型...")

        # 获取所有视频
        videos = db.query(Video).filter(
            Video.title.isnot(None),
            Video.title != ''
        ).all()

        if len(videos) < 50:
            return {
                "success": False,
                "error": f"训练数据不足，需要至少 50 条视频数据，当前只有 {len(videos)} 条"
            }

        # 分词处理
        def tokenize(text):
            words = jieba.cut(text)
            return ' '.join([w for w in words if w.strip() and w not in self.STOP_WORDS])

        # 构建语料库
        corpus = []
        bvid_list = []
        for video in videos:
            text = tokenize(video.title)
            if text.strip():
                corpus.append(text)
                bvid_list.append(video.bvid)

        if len(corpus) < 50:
            return {
                "success": False,
                "error": "有效语料不足"
            }

        # 训练 TF-IDF
        vectorizer = TfidfVectorizer(max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # 构建索引
        video_index = {bvid: idx for idx, bvid in enumerate(bvid_list)}

        # 保存模型
        vectorizer_path = MODEL_DIR / "tfidf_vectorizer.pkl"
        matrix_path = MODEL_DIR / "tfidf_matrix.pkl"
        index_path = MODEL_DIR / "video_index.pkl"

        with open(vectorizer_path, 'wb') as f:
            pickle.dump(vectorizer, f)
        with open(matrix_path, 'wb') as f:
            pickle.dump(tfidf_matrix, f)
        with open(index_path, 'wb') as f:
            pickle.dump(video_index, f)

        logger.info(f"推荐模型训练完成，共处理 {len(bvid_list)} 个视频")

        return {
            "success": True,
            "model_type": "TF-IDF Vectorizer",
            "video_count": len(bvid_list),
            "vocabulary_size": len(vectorizer.vocabulary_),
            "vectorizer_path": str(vectorizer_path),
            "matrix_path": str(matrix_path),
            "index_path": str(index_path),
            "trained_at": datetime.now().isoformat()
        }

    def train_all(self, db: Session) -> Dict:
        """训练所有模型"""
        results = {
            "predictor": self.train_predictor(db),
            "recommender": self.train_recommender(db),
            "trained_at": datetime.now().isoformat()
        }
        return results

    def get_model_status(self) -> Dict:
        """获取模型状态"""
        predictor_path = MODEL_DIR / "xgboost_predictor.pkl"
        vectorizer_path = MODEL_DIR / "tfidf_vectorizer.pkl"

        return {
            "predictor_exists": predictor_path.exists(),
            "recommender_exists": vectorizer_path.exists(),
            "model_dir": str(MODEL_DIR)
        }


# 全局单例
model_manager = ModelManager()
