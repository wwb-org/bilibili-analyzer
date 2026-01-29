"""
相似视频推荐服务
基于 TF-IDF + 多维度相似性计算
"""
import os
import pickle
import logging
from typing import Dict, List, Optional
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
import jieba

from app.models import Video

logger = logging.getLogger(__name__)

# 模型文件路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTORIZER_PATH = BASE_DIR / "ml_models" / "tfidf_vectorizer.pkl"
MATRIX_PATH = BASE_DIR / "ml_models" / "tfidf_matrix.pkl"
VIDEO_INDEX_PATH = BASE_DIR / "ml_models" / "video_index.pkl"


class VideoRecommender:
    """视频相似推荐器"""

    # 停用词
    STOP_WORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
        '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
        '着', '没有', '看', '好', '这', '那', '吗', '什么', '他', '她',
        '们', '这个', '那个', '真的', '可以', '其实', '怎么', '为什么',
        '啊', '哈哈', '视频', 'bilibili', 'B站', '哔哩哔哩'
    }

    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.video_index: Dict[str, int] = {}   # bvid -> matrix_index
        self.index_video: Dict[int, str] = {}   # matrix_index -> bvid
        self._load_models()

    def _load_models(self):
        """加载预训练模型"""
        try:
            if VECTORIZER_PATH.exists():
                with open(VECTORIZER_PATH, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                logger.info("TF-IDF vectorizer 加载成功")

            if MATRIX_PATH.exists():
                with open(MATRIX_PATH, 'rb') as f:
                    self.tfidf_matrix = pickle.load(f)
                logger.info("TF-IDF matrix 加载成功")

            if VIDEO_INDEX_PATH.exists():
                with open(VIDEO_INDEX_PATH, 'rb') as f:
                    self.video_index = pickle.load(f)
                    self.index_video = {v: k for k, v in self.video_index.items()}
                logger.info(f"视频索引加载成功，共 {len(self.video_index)} 个视频")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")

    def reload_models(self):
        """重新加载模型"""
        self._load_models()

    def is_ready(self) -> bool:
        """检查模型是否已加载"""
        return all([
            self.vectorizer is not None,
            self.tfidf_matrix is not None,
            len(self.video_index) > 0
        ])

    def _tokenize(self, text: str) -> str:
        """中文分词"""
        words = jieba.cut(text)
        return ' '.join([w for w in words if w.strip() and w not in self.STOP_WORDS])

    def recommend_by_bvid(
        self,
        bvid: str,
        db: Session,
        top_k: int = 10,
        include_same_category: bool = True,
        include_same_author: bool = False
    ) -> Dict:
        """
        根据 BVID 推荐相似视频

        Args:
            bvid: 目标视频 BV 号
            db: 数据库会话
            top_k: 返回数量
            include_same_category: 是否优先同分区
            include_same_author: 是否包含同作者

        Returns:
            推荐结果字典
        """
        # 查询目标视频
        target_video = db.query(Video).filter(Video.bvid == bvid).first()
        if not target_video:
            return {
                "success": False,
                "error": f"视频不存在: {bvid}"
            }

        # 如果模型未加载，使用简单推荐
        if not self.is_ready():
            return self._simple_recommend(target_video, db, top_k)

        # TF-IDF 推荐
        return self._tfidf_recommend(
            target_video, db, top_k,
            include_same_category, include_same_author
        )

    def _tfidf_recommend(
        self,
        target_video: Video,
        db: Session,
        top_k: int,
        include_same_category: bool,
        include_same_author: bool
    ) -> Dict:
        """基于 TF-IDF 的推荐"""
        bvid = target_video.bvid

        # 检查视频是否在索引中
        if bvid not in self.video_index:
            # 实时计算新视频的 TF-IDF 向量
            text = self._tokenize(target_video.title or "")
            target_vector = self.vectorizer.transform([text])
        else:
            idx = self.video_index[bvid]
            target_vector = self.tfidf_matrix[idx]

        # 计算余弦相似度
        similarities = cosine_similarity(target_vector, self.tfidf_matrix).flatten()

        # 获取相似度排名
        similar_indices = similarities.argsort()[::-1]

        # 查询候选视频
        candidates = []
        for idx in similar_indices:
            if len(candidates) >= top_k * 3:  # 多取一些用于过滤
                break

            candidate_bvid = self.index_video.get(idx)
            if not candidate_bvid or candidate_bvid == bvid:
                continue

            similarity_score = float(similarities[idx])
            if similarity_score < 0.01:  # 相似度过低的跳过
                continue

            candidates.append({
                "bvid": candidate_bvid,
                "title_similarity": similarity_score
            })

        # 获取完整视频信息
        candidate_bvids = [c["bvid"] for c in candidates]
        videos = db.query(Video).filter(Video.bvid.in_(candidate_bvids)).all()
        video_map = {v.bvid: v for v in videos}

        # 多维度评分
        results = []
        for candidate in candidates:
            video = video_map.get(candidate["bvid"])
            if not video:
                continue

            # 排除同作者（如果需要）
            if not include_same_author and video.author_id == target_video.author_id:
                continue

            # 计算综合相似度分数
            score = self._calculate_multi_score(
                target_video, video, candidate["title_similarity"],
                include_same_category
            )

            results.append({
                "bvid": video.bvid,
                "title": video.title,
                "cover_url": video.cover_url,
                "author_name": video.author_name,
                "category": video.category,
                "play_count": video.play_count or 0,
                "like_count": video.like_count or 0,
                "similarity_score": round(score, 4),
                "title_similarity": round(candidate["title_similarity"], 4),
                "same_category": video.category == target_video.category,
                "same_author": video.author_id == target_video.author_id
            })

        # 按综合分数排序
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:top_k]

        return {
            "success": True,
            "target": {
                "bvid": bvid,
                "title": target_video.title,
                "category": target_video.category,
                "author_name": target_video.author_name
            },
            "recommendations": results,
            "total": len(results),
            "method": "tfidf_multi_score"
        }

    def _calculate_multi_score(
        self,
        target: Video,
        candidate: Video,
        title_similarity: float,
        include_same_category: bool
    ) -> float:
        """
        计算多维度综合相似分数

        权重分配:
        - 标题相似度: 50%
        - 分区匹配: 20%
        - 互动率相似度: 15%
        - 时长相似度: 10%
        - 热度加成: 5%
        """
        score = title_similarity * 0.5

        # 分区匹配加成
        if include_same_category and candidate.category == target.category:
            score += 0.2

        # 互动率相似度
        target_rate = self._calc_interaction_rate(target)
        candidate_rate = self._calc_interaction_rate(candidate)
        rate_diff = abs(target_rate - candidate_rate)
        rate_similarity = max(0, 1 - rate_diff * 10)  # 差异越小越相似
        score += rate_similarity * 0.15

        # 时长相似度
        if target.duration and candidate.duration:
            duration_ratio = min(target.duration, candidate.duration) / max(target.duration, candidate.duration)
            score += duration_ratio * 0.1

        # 热度加成（播放量较高的适当加分）
        if candidate.play_count and candidate.play_count > 10000:
            heat_bonus = min(0.05, np.log10(candidate.play_count) / 100)
            score += heat_bonus

        return score

    def _calc_interaction_rate(self, video: Video) -> float:
        """计算互动率"""
        play = max(video.play_count or 1, 1)
        interactions = (video.like_count or 0) + (video.coin_count or 0) + (video.favorite_count or 0)
        return interactions / play

    def _simple_recommend(self, target_video: Video, db: Session, top_k: int) -> Dict:
        """
        简单推荐（模型未加载时的备用方案）
        基于分区和热度推荐
        """
        results = []

        # 优先同分区
        if target_video.category:
            same_category = db.query(Video).filter(
                Video.bvid != target_video.bvid,
                Video.category == target_video.category
            ).order_by(Video.play_count.desc()).limit(top_k).all()

            for video in same_category:
                results.append({
                    "bvid": video.bvid,
                    "title": video.title,
                    "cover_url": video.cover_url,
                    "author_name": video.author_name,
                    "category": video.category,
                    "play_count": video.play_count or 0,
                    "like_count": video.like_count or 0,
                    "similarity_score": 0.5,
                    "title_similarity": 0.0,
                    "same_category": True,
                    "same_author": video.author_id == target_video.author_id
                })

        # 补充热门视频
        if len(results) < top_k:
            existing_bvids = {r["bvid"] for r in results}
            existing_bvids.add(target_video.bvid)

            hot_videos = db.query(Video).filter(
                Video.bvid.notin_(existing_bvids)
            ).order_by(Video.play_count.desc()).limit(top_k - len(results)).all()

            for video in hot_videos:
                results.append({
                    "bvid": video.bvid,
                    "title": video.title,
                    "cover_url": video.cover_url,
                    "author_name": video.author_name,
                    "category": video.category,
                    "play_count": video.play_count or 0,
                    "like_count": video.like_count or 0,
                    "similarity_score": 0.3,
                    "title_similarity": 0.0,
                    "same_category": video.category == target_video.category,
                    "same_author": video.author_id == target_video.author_id
                })

        return {
            "success": True,
            "target": {
                "bvid": target_video.bvid,
                "title": target_video.title,
                "category": target_video.category,
                "author_name": target_video.author_name
            },
            "recommendations": results[:top_k],
            "total": len(results[:top_k]),
            "method": "simple_category_based"
        }

    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "loaded": self.is_ready(),
            "video_count": len(self.video_index),
            "vectorizer_path": str(VECTORIZER_PATH),
            "matrix_path": str(MATRIX_PATH)
        }


# 全局单例
video_recommender = VideoRecommender()
