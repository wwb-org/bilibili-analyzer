"""
细粒度情绪分析服务（GoEmotions 28类）
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 28类情绪标签（GoEmotions 标准）
EMOTION_LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval",
    "caring", "confusion", "curiosity", "desire", "disappointment",
    "disapproval", "disgust", "embarrassment", "excitement", "fear",
    "gratitude", "grief", "joy", "love", "nervousness",
    "optimism", "pride", "realization", "relief", "remorse",
    "sadness", "surprise", "neutral",
]

EMOTION_LABEL_ZH = {
    "admiration": "钦佩",
    "amusement": "愉悦",
    "anger": "愤怒",
    "annoyance": "烦躁",
    "approval": "赞同",
    "caring": "关爱",
    "confusion": "困惑",
    "curiosity": "好奇",
    "desire": "渴望",
    "disappointment": "失望",
    "disapproval": "反对",
    "disgust": "厌恶",
    "embarrassment": "尴尬",
    "excitement": "兴奋",
    "fear": "恐惧",
    "gratitude": "感激",
    "grief": "悲痛",
    "joy": "喜悦",
    "love": "喜爱",
    "nervousness": "紧张",
    "optimism": "乐观",
    "pride": "自豪",
    "realization": "恍然",
    "relief": "释然",
    "remorse": "懊悔",
    "sadness": "悲伤",
    "surprise": "惊讶",
    "neutral": "中性",
}

EMOTION_ALIASES = {
    # === 旧 8 类标签 → 新 28 类标签的兼容映射 ===
    "happy": "joy",
    "angry": "anger",
    "sad": "sadness",
    "surprised": "surprise",
    "disgusted": "disgust",
    "concerned": "nervousness",
    "questioning": "curiosity",
    # 旧模型 label_index 映射（兼容旧数据）
    "label_0": "neutral",
    "label_1": "nervousness",
    "label_2": "joy",
    "label_3": "anger",
    "label_4": "sadness",
    "label_5": "curiosity",
    "label_6": "surprise",
    "label_7": "disgust",
    # 中文同义词
    "钦佩": "admiration",
    "愉悦": "amusement",
    "愤怒": "anger",
    "烦躁": "annoyance",
    "赞同": "approval",
    "关爱": "caring",
    "困惑": "confusion",
    "好奇": "curiosity",
    "渴望": "desire",
    "失望": "disappointment",
    "反对": "disapproval",
    "厌恶": "disgust",
    "尴尬": "embarrassment",
    "兴奋": "excitement",
    "恐惧": "fear",
    "感激": "gratitude",
    "悲痛": "grief",
    "喜悦": "joy",
    "喜爱": "love",
    "紧张": "nervousness",
    "乐观": "optimism",
    "自豪": "pride",
    "恍然": "realization",
    "释然": "relief",
    "懊悔": "remorse",
    "悲伤": "sadness",
    "惊讶": "surprise",
    "中性": "neutral",
    # 旧中文同义词兼容
    "高兴": "joy",
    "开心": "joy",
    "生气": "anger",
    "伤心": "sadness",
    "关切": "caring",
    "疑问": "curiosity",
    "担忧": "nervousness",
}

@dataclass
class EmotionResult:
    emotion_label: str
    emotion_scores: Dict[str, float]
    sentiment_score: float
    sentiment_label: str
    model_version: str
    analyzed_at: datetime


class EmotionAnalyzer:
    """基于 Hugging Face 文本分类模型的 28 类情绪分析器（GoEmotions）"""

    POSITIVE_EMOTIONS = (
        "admiration", "amusement", "approval", "caring", "desire",
        "excitement", "gratitude", "joy", "love", "optimism", "pride",
    )
    NEUTRAL_EMOTIONS = (
        "neutral", "confusion", "curiosity", "realization", "relief", "surprise",
    )
    NEGATIVE_EMOTIONS = (
        "anger", "annoyance", "disappointment", "disapproval", "disgust",
        "embarrassment", "fear", "grief", "nervousness", "remorse", "sadness",
    )

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        max_length: Optional[int] = None,
    ):
        self.model_name = model_name or settings.EMOTION_MODEL_NAME
        self.device = self._resolve_device(device or settings.EMOTION_DEVICE)
        self.max_length = max_length or settings.EMOTION_MAX_LENGTH
        self._classifier = None
        self._load_error: Optional[str] = None
        self._load_lock = threading.Lock()

    @staticmethod
    def _resolve_device(device: str) -> int:
        if isinstance(device, int):
            return device

        value = (device or "cpu").strip().lower()
        if value == "cpu":
            return -1

        if value in {"cuda", "gpu", "auto"}:
            try:
                import torch

                if torch.cuda.is_available():
                    return 0
            except Exception:
                return -1
        return -1

    def _load_classifier(self):
        if self._classifier is not None or self._load_error:
            return

        with self._load_lock:
            if self._classifier is not None or self._load_error:
                return

            try:
                from transformers import pipeline

                self._classifier = pipeline(
                    task="text-classification",
                    model=self.model_name,
                    tokenizer=self.model_name,
                    device=self.device,
                    top_k=None,
                )
                logger.info(
                    "EmotionAnalyzer 模型加载完成: model=%s device=%s",
                    self.model_name,
                    self.device,
                )
            except Exception as exc:
                self._load_error = str(exc)
                logger.warning("EmotionAnalyzer 模型加载失败，使用中性兜底: %s", exc)

    @staticmethod
    def normalize_emotion_label(label: str) -> Optional[str]:
        if not label:
            return None

        key = label.strip().lower()
        if key in EMOTION_LABELS:
            return key
        if key in EMOTION_ALIASES:
            return EMOTION_ALIASES[key]
        return None

    @classmethod
    def sentiment_label_from_score(cls, score: float) -> str:
        if score > 0.6:
            return "positive"
        if score < 0.4:
            return "negative"
        return "neutral"

    @classmethod
    def sentiment_from_emotion(cls, emotion_label: Optional[str]) -> str:
        if emotion_label in cls.POSITIVE_EMOTIONS:
            return "positive"
        if emotion_label in cls.NEUTRAL_EMOTIONS:
            return "neutral"
        if emotion_label in cls.NEGATIVE_EMOTIONS:
            return "negative"
        return "neutral"

    @classmethod
    def build_sentiment_score(cls, emotion_scores: Dict[str, float]) -> float:
        positive_prob = sum(emotion_scores.get(k, 0.0) for k in cls.POSITIVE_EMOTIONS)
        neutral_prob = sum(emotion_scores.get(k, 0.0) for k in cls.NEUTRAL_EMOTIONS)
        score = positive_prob + 0.5 * neutral_prob
        return round(max(0.0, min(1.0, score)), 6)

    @staticmethod
    def top_emotions(
        emotion_scores: Optional[Dict[str, float]],
        top_k: int = 3,
    ) -> Dict[str, float]:
        if not emotion_scores:
            return {}

        sorted_items = sorted(
            emotion_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        return {k: round(v, 6) for k, v in sorted_items[:top_k]}

    @staticmethod
    def _neutral_scores() -> Dict[str, float]:
        return {label: (1.0 if label == "neutral" else 0.0) for label in EMOTION_LABELS}

    def _neutral_result(self) -> EmotionResult:
        scores = self._neutral_scores()
        sentiment_score = self.build_sentiment_score(scores)
        return EmotionResult(
            emotion_label="neutral",
            emotion_scores=scores,
            sentiment_score=sentiment_score,
            sentiment_label=self.sentiment_label_from_score(sentiment_score),
            model_version=self.model_name,
            analyzed_at=datetime.utcnow(),
        )

    def analyze_emotion(self, text: str) -> EmotionResult:
        if not text or not text.strip():
            return self._neutral_result()

        self._load_classifier()
        if self._classifier is None:
            return self._neutral_result()

        try:
            outputs = self._classifier(
                text,
                truncation=True,
                max_length=self.max_length,
            )
            if outputs and isinstance(outputs[0], list):
                outputs = outputs[0]

            scores = {label: 0.0 for label in EMOTION_LABELS}
            for item in outputs:
                label = self.normalize_emotion_label(str(item.get("label", "")))
                if not label:
                    continue
                score = float(item.get("score", 0.0))
                if score > scores[label]:
                    scores[label] = score

            total = sum(scores.values())
            if total <= 0:
                return self._neutral_result()

            normalized = {k: round(v / total, 6) for k, v in scores.items()}
            emotion_label = max(normalized.items(), key=lambda item: item[1])[0]
            sentiment_score = self.build_sentiment_score(normalized)

            return EmotionResult(
                emotion_label=emotion_label,
                emotion_scores=normalized,
                sentiment_score=sentiment_score,
                sentiment_label=self.sentiment_label_from_score(sentiment_score),
                model_version=self.model_name,
                analyzed_at=datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning("EmotionAnalyzer 推理失败，使用中性兜底: %s", exc)
            return self._neutral_result()

    def analyze_batch(self, texts: List[str]) -> List[EmotionResult]:
        return [self.analyze_emotion(text) for text in texts]
