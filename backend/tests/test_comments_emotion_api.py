"""
测试评论 API 的细粒度情绪辅助逻辑（轻量版）

用法：
  cd backend
  python tests/test_comments_emotion_api.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.comments import build_emotion_distribution, normalize_emotion_scores


class FakeComment:
    def __init__(self, emotion_label):
        self.emotion_label = emotion_label


def main():
    print("=" * 60)
    print("测试 comments API 细粒度情绪辅助逻辑")
    print("=" * 60)

    comments = [
        FakeComment("joy"),
        FakeComment("joy"),
        FakeComment("anger"),
        FakeComment("neutral"),
        FakeComment("curiosity"),
    ]
    dist = build_emotion_distribution(comments, total_count=len(comments))
    print(f"分布: {dist}")

    assert dist["counts"]["joy"] == 2, "joy 计数异常"
    assert dist["counts"]["anger"] == 1, "anger 计数异常"
    assert dist["dominant"] == "joy", "主导情绪异常"

    raw_scores = {"happy": 0.7, "anger": 0.2, "neutral": 0.1}
    normalized = normalize_emotion_scores(raw_scores)
    print(f"归一化标签: {normalized}")
    assert normalized["joy"] == 0.7, "happy→joy alias 映射异常"
    assert normalized["anger"] == 0.2, "anger 分数异常"

    indexed_scores = {"label_1": 0.5, "label_6": 0.3, "label_0": 0.2}
    normalized2 = normalize_emotion_scores(indexed_scores)
    print(f"索引标签归一化: {normalized2}")
    assert normalized2["nervousness"] == 0.5, "label_1 映射异常"
    assert normalized2["surprise"] == 0.3, "label_6 映射异常"
    assert normalized2["neutral"] == 0.2, "label_0 映射异常"

    print("测试通过")


if __name__ == "__main__":
    main()
