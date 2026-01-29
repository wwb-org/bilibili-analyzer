"""
热词分析ETL任务

包含：
- KeywordDailyETL: 热词每日明细ETL（DWD层）
- KeywordStatsETL: 热词聚合统计ETL（DWS层）
"""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from sqlalchemy import func, and_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.etl.base import ETLTask
from app.models.models import Video, Comment, Danmaku
from app.models.warehouse import DwdKeywordDaily, DwsKeywordStats
from app.services.nlp import NLPAnalyzer


class KeywordDailyETL(ETLTask):
    """
    热词每日明细ETL

    功能：从视频标题、评论、弹幕中提取热词
    数据流：videos, comments, danmakus → dwd_keyword_daily
    """

    def __init__(self, db: Session, top_k: int = 200):
        super().__init__(db)
        self.top_k = top_k
        self.nlp = NLPAnalyzer()

    def extract(self, stat_date: date) -> Dict:
        """
        抽取文本数据（全量模式）

        全量模式：统计截至 stat_date 的所有历史数据
        适合数据量不大、采集不规律的场景
        """
        # 构建截止时间（包含 stat_date 当天）
        end_dt = datetime.combine(stat_date, datetime.max.time())

        # 获取所有视频（截至 stat_date）
        videos = self.db.query(Video).filter(
            Video.created_at <= end_dt
        ).all()

        # 获取所有评论（截至 stat_date，包含情感分数）
        comments = self.db.query(
            Comment.content,
            Comment.video_id,
            Comment.sentiment_score
        ).filter(
            Comment.created_at <= end_dt
        ).all()

        # 获取所有弹幕（截至 stat_date）
        danmakus = self.db.query(
            Danmaku.content,
            Danmaku.video_id
        ).filter(
            Danmaku.created_at <= end_dt
        ).all()

        # 构建视频ID到分区的映射
        video_category_map = {v.id: v.category for v in videos}
        video_bvid_map = {v.id: v.bvid for v in videos}

        return {
            "videos": videos,
            "comments": comments,
            "danmakus": danmakus,
            "video_category_map": video_category_map,
            "video_bvid_map": video_bvid_map
        }

    def transform(self, data: Dict) -> List[Dict]:
        """提取并聚合热词"""
        videos = data["videos"]
        comments = data["comments"]
        danmakus = data["danmakus"]
        video_category_map = data["video_category_map"]
        video_bvid_map = data["video_bvid_map"]

        result = []

        # 1. 处理视频标题热词
        title_keywords = self._extract_title_keywords(videos)
        result.extend(title_keywords)

        # 2. 处理评论热词
        comment_keywords = self._extract_comment_keywords(
            comments, video_category_map, video_bvid_map
        )
        result.extend(comment_keywords)

        # 3. 处理弹幕热词
        danmaku_keywords = self._extract_danmaku_keywords(
            danmakus, video_category_map, video_bvid_map
        )
        result.extend(danmaku_keywords)

        return result

    def _extract_title_keywords(self, videos: List) -> List[Dict]:
        """从视频标题提取热词"""
        # 按分区分组
        category_titles = defaultdict(list)
        category_videos = defaultdict(list)

        for video in videos:
            category = video.category or "未分类"
            category_titles[category].append(video.title)
            category_videos[category].append(video.bvid)

        result = []
        for category, titles in category_titles.items():
            keywords = self.nlp.extract_keywords_tfidf(titles, self.top_k)
            bvids = category_videos[category]

            for word, frequency in keywords:
                # 找出包含该词的视频作为样例
                sample_bvids = []
                for i, title in enumerate(titles):
                    if word in title and len(sample_bvids) < 5:
                        sample_bvids.append(bvids[i])

                result.append({
                    "word": word,
                    "source": "title",
                    "category": category,
                    "frequency": frequency,
                    "video_count": len([t for t in titles if word in t]),
                    "avg_sentiment": None,
                    "sample_bvids": sample_bvids
                })

        return result

    def _extract_comment_keywords(
        self,
        comments: List,
        video_category_map: Dict,
        video_bvid_map: Dict
    ) -> List[Dict]:
        """从评论提取热词"""
        # 按分区分组
        category_comments = defaultdict(list)
        category_sentiments = defaultdict(list)
        category_bvids = defaultdict(set)

        for comment in comments:
            category = video_category_map.get(comment.video_id, "未分类")
            if comment.content:
                category_comments[category].append(comment.content)
                if comment.sentiment_score is not None:
                    category_sentiments[category].append(comment.sentiment_score)
                bvid = video_bvid_map.get(comment.video_id)
                if bvid:
                    category_bvids[category].add(bvid)

        result = []
        for category, contents in category_comments.items():
            keywords = self.nlp.extract_keywords_tfidf(contents, self.top_k)
            sentiments = category_sentiments.get(category, [])
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None
            bvids = list(category_bvids.get(category, set()))[:5]

            for word, frequency in keywords:
                result.append({
                    "word": word,
                    "source": "comment",
                    "category": category,
                    "frequency": frequency,
                    "video_count": len(bvids),
                    "avg_sentiment": avg_sentiment,
                    "sample_bvids": bvids
                })

        return result

    def _extract_danmaku_keywords(
        self,
        danmakus: List,
        video_category_map: Dict,
        video_bvid_map: Dict
    ) -> List[Dict]:
        """从弹幕提取热词"""
        # 按分区分组
        category_danmakus = defaultdict(list)
        category_bvids = defaultdict(set)

        for danmaku in danmakus:
            category = video_category_map.get(danmaku.video_id, "未分类")
            if danmaku.content:
                category_danmakus[category].append(danmaku.content)
                bvid = video_bvid_map.get(danmaku.video_id)
                if bvid:
                    category_bvids[category].add(bvid)

        result = []
        for category, contents in category_danmakus.items():
            keywords = self.nlp.extract_keywords_tfidf(contents, self.top_k)
            bvids = list(category_bvids.get(category, set()))[:5]

            for word, frequency in keywords:
                result.append({
                    "word": word,
                    "source": "danmaku",
                    "category": category,
                    "frequency": frequency,
                    "video_count": len(bvids),
                    "avg_sentiment": None,
                    "sample_bvids": bvids
                })

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入热词每日明细表"""
        # 先删除当日旧数据
        self.db.query(DwdKeywordDaily).filter(
            DwdKeywordDaily.stat_date == stat_date
        ).delete(synchronize_session=False)

        # 去重合并，避免同一 (word, source, category) 重复写入导致唯一键冲突
        merged: Dict[tuple, Dict[str, Any]] = {}
        for item in data:
            key = (item["word"], item["source"], item["category"])
            if key not in merged:
                merged[key] = {
                    "frequency": item["frequency"],
                    "video_count": item["video_count"],
                    "avg_sentiment_sum": item["avg_sentiment"] or 0.0,
                    "avg_sentiment_count": 1 if item["avg_sentiment"] is not None else 0,
                    "sample_bvids": set(item["sample_bvids"]),
                }
                continue

            current = merged[key]
            current["frequency"] = max(current["frequency"], item["frequency"])
            current["video_count"] = max(current["video_count"], item["video_count"])
            if item["avg_sentiment"] is not None:
                current["avg_sentiment_sum"] += item["avg_sentiment"]
                current["avg_sentiment_count"] += 1
            current["sample_bvids"].update(item["sample_bvids"])

        if not merged:
            return 0

        rows = []
        now = datetime.utcnow()
        for (word, source, category), current in merged.items():
            avg_sentiment = None
            if current["avg_sentiment_count"] > 0:
                avg_sentiment = current["avg_sentiment_sum"] / current["avg_sentiment_count"]
            rows.append({
                "stat_date": stat_date,
                "word": word,
                "source": source,
                "category": category,
                "frequency": current["frequency"],
                "video_count": current["video_count"],
                "avg_sentiment": avg_sentiment,
                "sample_bvids": json.dumps(list(current["sample_bvids"])[:5], ensure_ascii=False),
                "created_at": now,
            })

        stmt = mysql_insert(DwdKeywordDaily.__table__).values(rows)
        stmt = stmt.on_duplicate_key_update(
            frequency=stmt.inserted.frequency,
            video_count=stmt.inserted.video_count,
            avg_sentiment=stmt.inserted.avg_sentiment,
            sample_bvids=stmt.inserted.sample_bvids,
            created_at=stmt.inserted.created_at,
        )
        self.db.execute(stmt)

        return len(rows)


class KeywordStatsETL(ETLTask):
    """
    热词聚合统计ETL

    功能：聚合各来源热词统计，计算趋势指标
    数据流：dwd_keyword_daily → dws_keyword_stats
    """

    def __init__(self, db: Session, trend_days: int = 7):
        super().__init__(db)
        self.trend_days = trend_days

    def extract(self, stat_date: date) -> List:
        """从DWD层抽取当日热词数据"""
        keywords = self.db.query(DwdKeywordDaily).filter(
            DwdKeywordDaily.stat_date == stat_date
        ).all()
        return keywords

    def transform(self, data: List) -> List[Dict]:
        """聚合热词统计"""
        # 按词聚合
        word_stats = defaultdict(lambda: {
            "title_frequency": 0,
            "comment_frequency": 0,
            "danmaku_frequency": 0,
            "total_frequency": 0,
            "video_count": 0,
            "category_distribution": defaultdict(int),
            "sentiments": [],
            "sample_bvids": set()
        })

        for kw in data:
            word = kw.word
            stats = word_stats[word]

            # 累加各来源频次
            if kw.source == "title":
                stats["title_frequency"] += kw.frequency
            elif kw.source == "comment":
                stats["comment_frequency"] += kw.frequency
            elif kw.source == "danmaku":
                stats["danmaku_frequency"] += kw.frequency

            stats["total_frequency"] += kw.frequency
            stats["video_count"] += kw.video_count or 0

            # 分区分布
            if kw.category:
                stats["category_distribution"][kw.category] += kw.frequency

            # 情感分数
            if kw.avg_sentiment is not None:
                stats["sentiments"].append(kw.avg_sentiment)

            # 示例视频
            if kw.sample_bvids:
                try:
                    bvids = json.loads(kw.sample_bvids)
                    stats["sample_bvids"].update(bvids)
                except:
                    pass

        # 转换为列表
        result = []
        for word, stats in word_stats.items():
            avg_sentiment = None
            if stats["sentiments"]:
                avg_sentiment = sum(stats["sentiments"]) / len(stats["sentiments"])

            result.append({
                "word": word,
                "title_frequency": stats["title_frequency"],
                "comment_frequency": stats["comment_frequency"],
                "danmaku_frequency": stats["danmaku_frequency"],
                "total_frequency": stats["total_frequency"],
                "video_count": stats["video_count"],
                "category_distribution": dict(stats["category_distribution"]),
                "avg_sentiment": avg_sentiment
            })

        # 按总频次排序，计算热度分
        result.sort(key=lambda x: x["total_frequency"], reverse=True)
        max_freq = result[0]["total_frequency"] if result else 1
        for i, item in enumerate(result):
            # 热度分 = 归一化频次 * 0.7 + 来源多样性 * 0.3
            normalized_freq = item["total_frequency"] / max_freq
            source_diversity = sum([
                1 if item["title_frequency"] > 0 else 0,
                1 if item["comment_frequency"] > 0 else 0,
                1 if item["danmaku_frequency"] > 0 else 0
            ]) / 3
            item["heat_score"] = round(normalized_freq * 0.7 + source_diversity * 0.3, 4)

        return result

    def load(self, data: List[Dict], stat_date: date) -> int:
        """写入热词聚合统计表"""
        # 获取前一天的排名用于计算变化
        prev_date = stat_date - timedelta(days=1)
        prev_rankings = {}
        prev_stats = self.db.query(DwsKeywordStats).filter(
            DwsKeywordStats.stat_date == prev_date
        ).all()
        for i, ps in enumerate(sorted(prev_stats, key=lambda x: x.total_frequency, reverse=True)):
            prev_rankings[ps.word] = i + 1

        # 获取7天前的数据用于计算趋势
        week_ago = stat_date - timedelta(days=self.trend_days)
        week_ago_stats = {}
        prev_week = self.db.query(DwsKeywordStats).filter(
            DwsKeywordStats.stat_date == week_ago
        ).all()
        for ps in prev_week:
            week_ago_stats[ps.word] = ps.total_frequency

        # 先删除当日旧数据
        self.db.query(DwsKeywordStats).filter(
            DwsKeywordStats.stat_date == stat_date
        ).delete(synchronize_session=False)

        if not data:
            return 0

        rows = []
        now = datetime.utcnow()
        for i, item in enumerate(data):
            current_rank = i + 1
            prev_rank = prev_rankings.get(item["word"], current_rank)
            rank_change = prev_rank - current_rank  # 正数表示上升

            # 计算频次趋势
            prev_freq = week_ago_stats.get(item["word"], 0)
            frequency_trend = 0
            if prev_freq > 0:
                frequency_trend = (item["total_frequency"] - prev_freq) / prev_freq
            rows.append({
                "stat_date": stat_date,
                "word": item["word"],
                "title_frequency": item["title_frequency"],
                "comment_frequency": item["comment_frequency"],
                "danmaku_frequency": item["danmaku_frequency"],
                "total_frequency": item["total_frequency"],
                "video_count": item["video_count"],
                "category_distribution": json.dumps(
                    item["category_distribution"], ensure_ascii=False
                ),
                "avg_sentiment": item["avg_sentiment"],
                "frequency_trend": round(frequency_trend, 4),
                "rank_change": rank_change,
                "heat_score": item["heat_score"],
                "created_at": now,
            })

        stmt = mysql_insert(DwsKeywordStats.__table__).values(rows)
        stmt = stmt.on_duplicate_key_update(
            title_frequency=stmt.inserted.title_frequency,
            comment_frequency=stmt.inserted.comment_frequency,
            danmaku_frequency=stmt.inserted.danmaku_frequency,
            total_frequency=stmt.inserted.total_frequency,
            video_count=stmt.inserted.video_count,
            category_distribution=stmt.inserted.category_distribution,
            avg_sentiment=stmt.inserted.avg_sentiment,
            frequency_trend=stmt.inserted.frequency_trend,
            rank_change=stmt.inserted.rank_change,
            heat_score=stmt.inserted.heat_score,
            created_at=stmt.inserted.created_at,
        )
        self.db.execute(stmt)

        return len(rows)


def run_keyword_etl(db: Session, stat_date: date) -> Dict:
    """
    执行完整的热词ETL流程

    Args:
        db: 数据库会话
        stat_date: 统计日期

    Returns:
        执行结果
    """
    results = {}

    # 1. 执行DWD层ETL
    dwd_etl = KeywordDailyETL(db)
    results["dwd"] = dwd_etl.run(stat_date)

    # 2. 执行DWS层ETL
    dws_etl = KeywordStatsETL(db)
    results["dws"] = dws_etl.run(stat_date)

    return results
