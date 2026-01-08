"""
NLP分析服务
"""
import jieba
import jieba.analyse
from snownlp import SnowNLP
from typing import List, Dict, Tuple
from collections import Counter


class NLPAnalyzer:
    """NLP分析器"""

    # 停用词列表
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就',
        '不', '人', '都', '一', '一个', '上', '也', '很',
        '到', '说', '要', '去', '你', '会', '着', '没有',
        '看', '好', '自己', '这', '啊', '吗', '什么', '哈哈',
        '视频', 'bilibili', 'B站', '哔哩哔哩'
    }

    def __init__(self):
        # 加载自定义词典（如需要）
        # jieba.load_userdict("custom_dict.txt")
        pass

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
        从多个文本中提取热词（词频统计）
        """
        all_words = []
        for text in texts:
            words = jieba.cut(text)
            words = [w for w in words if len(w) > 1 and w not in self.STOP_WORDS]
            all_words.extend(words)

        word_count = Counter(all_words)
        return word_count.most_common(top_k)

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
