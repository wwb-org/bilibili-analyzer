"""
NLP分析服务
"""
import os
import logging
from pathlib import Path

import jieba
import jieba.analyse
from snownlp import SnowNLP
from typing import List, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

# 停用词文件路径
STOPWORDS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "stopwords.txt"


def load_stopwords_from_file(filepath: Path) -> set:
    """从文件加载停用词"""
    stopwords = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    stopwords.add(line)
        logger.info(f"从 {filepath} 加载了 {len(stopwords)} 个停用词")
    except Exception as e:
        logger.warning(f"加载停用词文件失败: {e}，将使用内置停用词")
    return stopwords


class NLPAnalyzer:
    """NLP分析器"""

    # 内置停用词（兜底，合并自项目各模块）
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
        '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
        '着', '没有', '看', '好', '自己', '这', '那', '吗', '什么', '他', '她',
        '它', '们', '这个', '那个', '真的', '可以', '其实', '怎么', '为什么',
        '啊', '呢', '吧', '哦', '嗯', '呀', '哈', '哈哈', '哈哈哈', '嘿', '喂',
        '诶', '哎', '但是', '还是', '如果', '因为', '所以', '或者', '而且',
        '虽然', '然后', '感觉', '觉得', '知道', '应该', '真是', '太', '最',
        '更', '非常', '比较', '已经', '还', '又', '再', '只', '没', '被', '把',
        '给', '让', '从', '向', '对', '于', '与', '等', '能', '可能', '可',
        '想', '来', '去', '过', '得', '起', '完', '出', '回', '下', '不是',
        '就是', '不会', '不能', '不要', '不过', '视频', 'bilibili', 'B站', '哔哩哔哩',
    }

    # TF-IDF 提取时允许的词性
    ALLOW_POS = ('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'an', 'eng')
    _STOPWORDS_LOADED = False

    @classmethod
    def ensure_stop_words_loaded(cls) -> set:
        """确保类级停用词已完成加载并同步到 jieba"""
        if cls._STOPWORDS_LOADED:
            return cls.STOP_WORDS

        file_stopwords = load_stopwords_from_file(STOPWORDS_FILE)
        if file_stopwords:
            cls.STOP_WORDS.update(file_stopwords)

        cls._STOPWORDS_LOADED = True

        try:
            jieba.analyse.default_tfidf.stop_words = cls.STOP_WORDS
        except Exception as e:
            logger.warning(f"同步停用词到 jieba TF-IDF 失败: {e}")

        return cls.STOP_WORDS

    def __init__(self):
        self.ensure_stop_words_loaded()
        self.STOP_WORDS = self.__class__.STOP_WORDS

    def extract_keywords(self, text: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        提取关键词
        返回: [(词, 权重), ...]
        """
        keywords = jieba.analyse.extract_tags(
            text,
            topK=top_k,
            withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a')
        )
        # 过滤停用词
        return [(word, weight) for word, weight in keywords if word not in self.STOP_WORDS]

    def extract_keywords_tfidf(self, texts: List[str], top_k: int = 50) -> List[Tuple[str, int]]:
        """
        从多个文本中提取热词（TF-IDF加权 + 词性过滤）
        返回: [(词, 权重分数), ...] 权重为整数，兼容现有调用方
        """
        word_weights: Dict[str, float] = {}

        for text in texts:
            if not text or not text.strip():
                continue
            # 使用 jieba TF-IDF 提取，带词性过滤
            keywords = jieba.analyse.extract_tags(
                text,
                topK=20,
                withWeight=True,
                allowPOS=self.ALLOW_POS
            )
            for word, weight in keywords:
                if len(word) > 1 and word not in self.STOP_WORDS:
                    word_weights[word] = word_weights.get(word, 0) + weight

        # 按聚合权重排序，转为整数分数兼容现有格式
        sorted_words = sorted(word_weights.items(), key=lambda x: x[1], reverse=True)[:top_k]

        if not sorted_words:
            return []

        # 归一化为整数分数（最高权重映射到 100）
        max_weight = sorted_words[0][1]
        result = []
        for word, weight in sorted_words:
            score = int(round(weight / max_weight * 100))
            result.append((word, max(score, 1)))

        return result

    def analyze_sentiment(self, text: str) -> float:
        """
        情感分析
        返回: 0-1 的情感分数，越大越正面
        """
        try:
            s = SnowNLP(text)
            return s.sentiments
        except:
            return 0.5  # 无法分析时返回中性

    def batch_sentiment_analysis(self, texts: List[str]) -> Dict[str, int]:
        """
        批量情感分析
        返回: {'positive': n, 'neutral': n, 'negative': n}
        """
        result = {'positive': 0, 'neutral': 0, 'negative': 0}

        for text in texts:
            score = self.analyze_sentiment(text)
            if score >= 0.6:
                result['positive'] += 1
            elif score <= 0.4:
                result['negative'] += 1
            else:
                result['neutral'] += 1

        return result

    def segment_text(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def get_word_cloud_data(self, texts: List[str], top_k: int = 100) -> List[Dict]:
        """
        生成词云数据
        返回: [{'name': word, 'value': count}, ...]
        """
        keywords = self.extract_keywords_tfidf(texts, top_k)
        return [{'name': word, 'value': count} for word, count in keywords]


NLPAnalyzer.ensure_stop_words_loaded()
