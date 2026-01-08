"""
数据分析服务
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Video, Comment, Keyword
from app.services.nlp import NLPAnalyzer


class DataAnalyzer:
    """数据分析器"""

    def __init__(self, db: Session):
        self.db = db
        self.nlp = NLPAnalyzer()

    def analyze_video_titles(self, days: int = 7) -> List[Dict]:
        """
        分析视频标题热词
        """
        start_date = datetime.now() - timedelta(days=days)
        videos = self.db.query(Video).filter(
            Video.publish_time >= start_date
        ).all()

        titles = [v.title for v in videos]
        return self.nlp.get_word_cloud_data(titles, top_k=100)

    def analyze_comments_sentiment(self, video_id: Optional[int] = None) -> Dict:
        """
        分析评论情感分布
        """
        query = self.db.query(Comment)
        if video_id:
            query = query.filter(Comment.video_id == video_id)

        comments = query.limit(1000).all()
        texts = [c.content for c in comments]

        return self.nlp.batch_sentiment_analysis(texts)

    def get_category_distribution(self) -> List[Dict]:
        """
        获取分区分布
        """
        result = self.db.query(
            Video.category,
            func.count(Video.id).label('count'),
            func.sum(Video.play_count).label('total_play')
        ).group_by(Video.category).all()

        return [
            {
                'category': r.category or '未知',
                'count': r.count,
                'total_play': r.total_play or 0
            }
            for r in result
        ]

    def get_daily_trends(self, days: int = 7, metric: str = 'video_count') -> List[Dict]:
        """
        获取每日趋势
        """
        start_date = datetime.now() - timedelta(days=days)

        if metric == 'video_count':
            result = self.db.query(
                func.date(Video.publish_time).label('date'),
                func.count(Video.id).label('value')
            ).filter(
                Video.publish_time >= start_date
            ).group_by(func.date(Video.publish_time)).all()
        else:
            column = getattr(Video, metric, Video.play_count)
            result = self.db.query(
                func.date(Video.publish_time).label('date'),
                func.sum(column).label('value')
            ).filter(
                Video.publish_time >= start_date
            ).group_by(func.date(Video.publish_time)).all()

        return [{'date': str(r.date), 'value': r.value or 0} for r in result]

    def update_keywords(self, category: Optional[str] = None):
        """
        更新热词统计表
        """
        query = self.db.query(Video)
        if category:
            query = query.filter(Video.category == category)

        videos = query.all()
        titles = [v.title for v in videos]

        keywords_data = self.nlp.extract_keywords_tfidf(titles, top_k=200)

        # 清除旧数据
        if category:
            self.db.query(Keyword).filter(Keyword.category == category).delete()
        else:
            self.db.query(Keyword).delete()

        # 插入新数据
        for word, freq in keywords_data:
            keyword = Keyword(
                word=word,
                frequency=freq,
                category=category,
                stat_date=datetime.now()
            )
            self.db.add(keyword)

        self.db.commit()
