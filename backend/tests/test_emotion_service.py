"""
测试细粒度情绪分析核心逻辑（轻量版）

用法：
  cd backend
  python tests/test_emotion_service.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.emotion import EmotionAnalyzer


def main():
    print("=" * 60)
    print("测试 EmotionAnalyzer 核心逻辑")
    print("=" * 60)

    scores = {
        "joy": 0.5,
        "surprise": 0.1,
        "neutral": 0.2,
        "nervousness": 0.05,
        "curiosity": 0.05,
        "anger": 0.05,
        "sadness": 0.03,
        "disgust": 0.02,
    }

    # positive_prob = joy(0.5) = 0.5
    # neutral_prob = surprise(0.1) + neutral(0.2) + curiosity(0.05) = 0.35
    # score = 0.5 + 0.5 * 0.35 = 0.675
    sentiment_score = EmotionAnalyzer.build_sentiment_score(scores)
    print(f"兼容情感分: {sentiment_score}")
    assert abs(sentiment_score - 0.675) < 1e-6, "兼容情感分计算异常"

    sentiment_label = EmotionAnalyzer.sentiment_label_from_score(sentiment_score)
    print(f"兼容情感标签: {sentiment_label}")
    assert sentiment_label == "positive", "兼容情感标签计算异常"

    top = EmotionAnalyzer.top_emotions(scores, top_k=3)
    print(f"TOP3 情绪: {top}")
    assert list(top.keys())[0] == "joy", "TOP 情绪排序异常"

    mapped_label = EmotionAnalyzer.normalize_emotion_label("label_1")
    print(f"label_1 映射: {mapped_label}")
    assert mapped_label == "nervousness", "模型标签索引映射异常（label_1）"

    mapped_label2 = EmotionAnalyzer.normalize_emotion_label("label_6")
    print(f"label_6 映射: {mapped_label2}")
    assert mapped_label2 == "surprise", "模型标签索引映射异常（label_6）"

    empty_result = EmotionAnalyzer().analyze_emotion("")
    print(f"空文本兜底: emotion={empty_result.emotion_label}, score={empty_result.sentiment_score}")
    assert empty_result.emotion_label == "neutral", "空文本兜底异常"

    print("测试通过")


if __name__ == "__main__":
    main()
