"""
热度预测服务
使用 XGBoost 预测视频 7 天后的播放量
"""
import os
import pickle
import logging
from typing import Dict
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Video
from app.ml.features import FeatureExtractor

logger = logging.getLogger(__name__)

# 模型文件路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "ml_models" / "xgboost_predictor.pkl"


class HotPredictor:
    """视频热度预测器"""

    def __init__(self):
        self.model = None
        self.feature_names = FeatureExtractor.get_feature_names()
        self._load_model()

    def _load_model(self):
        """加载预训练模型"""
        if MODEL_PATH.exists():
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info("XGBoost 模型加载成功")
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                self.model = None
        else:
            logger.warning(f"模型文件不存在: {MODEL_PATH}")

    def reload_model(self):
        """重新加载模型"""
        self._load_model()

    def is_ready(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None

    def predict_by_video(self, video: Video) -> Dict:
        """
        根据视频对象预测热度

        Args:
            video: Video ORM 对象

        Returns:
            预测结果字典
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "模型未加载，请先训练模型"
            }

        features = FeatureExtractor.extract_features(video)
        return self._predict(features, video.bvid, video.title)

    def predict_by_bvid(self, bvid: str, db: Session) -> Dict:
        """
        根据 BVID 预测热度

        Args:
            bvid: 视频 BV 号
            db: 数据库会话

        Returns:
            预测结果字典
        """
        video = db.query(Video).filter(Video.bvid == bvid).first()
        if not video:
            return {
                "success": False,
                "error": f"视频不存在: {bvid}"
            }

        return self.predict_by_video(video)

    def predict_by_params(self, params: Dict) -> Dict:
        """
        根据前端参数预测热度（手动输入模式）

        Args:
            params: 包含视频特征的参数字典

        Returns:
            预测结果字典
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "模型未加载，请先训练模型"
            }

        features = FeatureExtractor.extract_features_from_dict(params)
        return self._predict(features, "manual", "手动输入")

    def _predict(self, features: Dict[str, float], bvid: str, title: str) -> Dict:
        """
        执行预测

        Args:
            features: 特征字典
            bvid: 视频 BV 号
            title: 视频标题

        Returns:
            预测结果字典
        """
        try:
            X = FeatureExtractor.features_to_array(features)

            # 预测 7 天后的播放量
            predicted_play = float(self.model.predict(X)[0])

            # 计算增长量和增长率
            current_play = features['current_play_count']
            play_increment = predicted_play - current_play
            growth_rate = (play_increment / current_play) * 100 if current_play > 0 else 0

            # 获取特征重要性
            feature_importance = self._get_feature_importance()

            # 热度等级判断
            heat_level = self._calculate_heat_level(growth_rate)

            return {
                "success": True,
                "bvid": bvid,
                "title": title,
                "current_play_count": int(current_play),
                "predicted_play_count": int(max(predicted_play, current_play)),
                "play_increment": int(play_increment),
                "growth_rate": round(growth_rate, 2),
                "heat_level": heat_level,
                "prediction_days": 7,
                "feature_importance": feature_importance,
                "features_used": {k: round(v, 6) if isinstance(v, float) else v for k, v in features.items()},
                "predicted_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"预测失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_ready():
            return {}

        try:
            importance = self.model.feature_importances_
            return {
                name: round(float(imp), 4)
                for name, imp in zip(self.feature_names, importance)
            }
        except Exception:
            return {}

    def _calculate_heat_level(self, growth_rate: float) -> str:
        """
        根据增长率判断热度等级

        Args:
            growth_rate: 增长率百分比

        Returns:
            热度等级: 'hot', 'rising', 'normal', 'cold'
        """
        if growth_rate >= 100:
            return "hot"       # 爆款潜力
        elif growth_rate >= 30:
            return "rising"    # 上升趋势
        elif growth_rate >= 0:
            return "normal"    # 正常表现
        else:
            return "cold"      # 热度下降

    def get_model_info(self) -> Dict:
        """获取模型信息"""
        if not self.is_ready():
            return {
                "loaded": False,
                "message": "模型未加载"
            }

        return {
            "loaded": True,
            "model_type": "XGBoost Regressor",
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "model_path": str(MODEL_PATH),
            "feature_importance": self._get_feature_importance()
        }


# 全局单例
hot_predictor = HotPredictor()
