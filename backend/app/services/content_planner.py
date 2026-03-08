"""
爆款内容策划服务

纯算法实现，分析历史爆款数据，提供：
1. 分区爆款特征分析
2. 爆款关键词推荐
3. 标题模板生成（基于模式提取+关键词填槽）
4. 标题评分
"""
import re
import json
import math
import random
import logging
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.models import Video
from app.models.warehouse import DwsKeywordStats
from app.services.nlp import NLPAnalyzer

logger = logging.getLogger(__name__)

nlp = NLPAnalyzer()

# 爆款标题情感词库
VIRAL_EMOTION_WORDS = ['震惊', '绝了', '太强', '建议收藏', '必看', '牛', '炸', '惊艳',
                       '无语', '离谱', '绝绝子', '破防', '封神', '顶级', '硬核', '神级']

# 标题结构模式（regex → 模板）
TITLE_PATTERNS = [
    {
        'name': '数量型',
        'regex': r'\d+\s*[个种款条类型张]',
        'template': '{n}个{kw1}，{kw2}必看',
        'numbers': [3, 5, 7, 10],
    },
    {
        'name': '疑问型',
        'regex': r'[？?！!]$',
        'template': '为什么{kw1}会{kw2}？',
    },
    {
        'name': '教程型',
        'regex': r'^(如何|怎么|教你|学会|手把手)',
        'template': '如何{kw1}，{kw2}的正确方式',
    },
    {
        'name': '对比型',
        'regex': r'(vs|VS|对比|区别|还是|哪个好)',
        'template': '{kw1}VS{kw2}，差距竟然这么大',
    },
    {
        'name': '情感型',
        'regex': '(' + '|'.join(VIRAL_EMOTION_WORDS) + ')',
        'template': '{kw1}{emotion}！{kw2}的隐藏技巧',
    },
]


def _get_viral_threshold(videos: List[Video]) -> float:
    """计算爆款播放量门槛（p90）"""
    if not videos:
        return 0
    counts = sorted([v.play_count for v in videos if v.play_count], reverse=True)
    idx = max(0, int(len(counts) * 0.1) - 1)
    return counts[idx] if counts else 0


def analyze_category_features(category: str, db: Session) -> Dict:
    """
    分析某分区的爆款特征

    返回：最优标题字数区间、最佳发布时段、互动率基准、爆款播放量门槛
    """
    query = db.query(Video).filter(Video.category == category, Video.play_count > 0)
    all_videos = query.all()

    if not all_videos:
        return {"error": "该分区暂无数据", "category": category}

    total = len(all_videos)
    viral_threshold = _get_viral_threshold(all_videos)
    viral_videos = [v for v in all_videos if v.play_count >= viral_threshold]

    # 标题字数分析
    all_lengths = [len(v.title) for v in all_videos if v.title]
    viral_lengths = [len(v.title) for v in viral_videos if v.title]

    def length_stats(lengths):
        if not lengths:
            return {}
        lengths.sort()
        n = len(lengths)
        return {
            'avg': round(sum(lengths) / n, 1),
            'p25': lengths[int(n * 0.25)],
            'p75': lengths[int(n * 0.75)],
        }

    # 发布时段分析（爆款视频）
    hour_counter = Counter()
    weekday_counter = Counter()
    for v in viral_videos:
        if v.publish_time:
            hour_counter[v.publish_time.hour] += 1
            weekday_counter[v.publish_time.weekday()] += 1

    best_hours = [h for h, _ in hour_counter.most_common(3)]
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    best_weekdays = [weekday_names[w] for w, _ in weekday_counter.most_common(2)]

    # 互动率基准
    def avg_interaction(videos):
        rates = []
        for v in videos:
            if v.play_count and v.play_count > 0:
                r = (v.like_count + v.coin_count + (v.favorite_count or 0)) / v.play_count
                rates.append(r)
        return round(sum(rates) / len(rates) * 100, 2) if rates else 0

    # 小时分布（用于图表，返回24小时分布）
    hour_distribution = {str(h): hour_counter.get(h, 0) for h in range(24)}

    return {
        'category': category,
        'total_videos': total,
        'viral_count': len(viral_videos),
        'viral_threshold': int(viral_threshold),
        'title_length': {
            'all': length_stats(all_lengths),
            'viral': length_stats(viral_lengths),
        },
        'best_publish_hours': best_hours,
        'best_publish_weekdays': best_weekdays,
        'hour_distribution': hour_distribution,
        'interaction_rate': {
            'all_avg': avg_interaction(all_videos),
            'viral_avg': avg_interaction(viral_videos),
        },
    }


def get_viral_keywords(category: str, db: Session, top_k: int = 20) -> List[Dict]:
    """
    获取分区爆款关键词

    策略：查询 dws_keyword_stats，过滤含该分区的词，按 heat_score 排序
    """
    # 获取最近一天有数据的日期
    latest = db.query(func.max(DwsKeywordStats.stat_date)).scalar()
    if not latest:
        # 回退：直接从视频标题提取
        return _extract_keywords_from_titles(category, db, top_k)

    # 查询该分区相关关键词
    rows = (
        db.query(DwsKeywordStats)
        .filter(DwsKeywordStats.stat_date == latest)
        .order_by(desc(DwsKeywordStats.heat_score))
        .limit(200)
        .all()
    )

    result = []
    for row in rows:
        # 过滤分区：category_distribution 是 JSON，检查是否含目标分区
        if category and row.category_distribution:
            try:
                dist = json.loads(row.category_distribution)
                if category not in dist:
                    continue
            except Exception:
                pass

        result.append({
            'word': row.word,
            'heat_score': round(row.heat_score or 0, 2),
            'total_frequency': row.total_frequency or 0,
            'title_frequency': row.title_frequency or 0,
            'frequency_trend': round(row.frequency_trend or 0, 1),
            'video_count': row.video_count or 0,
        })

        if len(result) >= top_k:
            break

    # 不足则补充从标题提取
    if len(result) < 5:
        result = _extract_keywords_from_titles(category, db, top_k)

    return result


def _extract_keywords_from_titles(category: str, db: Session, top_k: int) -> List[Dict]:
    """回退方案：直接从标题提取关键词（当数仓无数据时）"""
    videos = (
        db.query(Video)
        .filter(Video.category == category, Video.play_count > 0)
        .order_by(desc(Video.play_count))
        .limit(200)
        .all()
    )
    titles = [v.title for v in videos if v.title]
    if not titles:
        return []

    kw_scores = nlp.extract_keywords_tfidf(titles, top_k=top_k)
    return [
        {'word': w, 'heat_score': round(s / 100, 2), 'total_frequency': s,
         'title_frequency': s, 'frequency_trend': 0, 'video_count': 0}
        for w, s in kw_scores
    ]


def generate_title_suggestions(category: str, db: Session, num: int = 5) -> List[Dict]:
    """
    生成标题建议

    步骤：
    1. 获取该分区爆款视频标题
    2. 统计各模式出现频次，取 TOP 模式
    3. 获取热词
    4. 用热词填充模板，生成建议
    """
    # 获取爆款视频
    all_videos = (
        db.query(Video)
        .filter(Video.category == category, Video.play_count > 0)
        .order_by(desc(Video.play_count))
        .all()
    )
    if not all_videos:
        return []

    viral_threshold = _get_viral_threshold(all_videos)
    viral_videos = [v for v in all_videos if v.play_count >= viral_threshold]
    viral_titles = [v.title for v in viral_videos if v.title]

    # 统计各模式命中次数
    pattern_hits = Counter()
    for title in viral_titles:
        for p in TITLE_PATTERNS:
            if re.search(p['regex'], title):
                pattern_hits[p['name']] += 1

    # 按命中率排序，取前几种模式
    top_patterns = [
        p for p in TITLE_PATTERNS
        if pattern_hits.get(p['name'], 0) > 0
    ]
    top_patterns.sort(key=lambda p: pattern_hits.get(p['name'], 0), reverse=True)

    # 若没有任何模式命中，使用全部模式
    if not top_patterns:
        top_patterns = TITLE_PATTERNS

    # 获取热词
    keywords = get_viral_keywords(category, db, top_k=30)
    kw_words = [k['word'] for k in keywords if len(k['word']) >= 2]

    if len(kw_words) < 2:
        return []

    suggestions = []
    used_patterns = set()

    for pattern in top_patterns:
        if len(suggestions) >= num:
            break
        if pattern['name'] in used_patterns:
            continue

        kw_sample = random.sample(kw_words, min(3, len(kw_words)))
        kw1 = kw_sample[0]
        kw2 = kw_sample[1] if len(kw_sample) > 1 else kw1

        template = pattern['template']
        emotion = random.choice(VIRAL_EMOTION_WORDS)
        n = random.choice(pattern.get('numbers', [5]))

        title = (template
                 .replace('{kw1}', kw1)
                 .replace('{kw2}', kw2)
                 .replace('{emotion}', emotion)
                 .replace('{n}', str(n)))

        suggestions.append({
            'title': title,
            'pattern': pattern['name'],
            'pattern_hit_rate': round(
                pattern_hits.get(pattern['name'], 0) / max(len(viral_titles), 1) * 100, 1
            ),
            'keywords_used': [kw1, kw2],
        })
        used_patterns.add(pattern['name'])

    # 补足数量（若模式不够，随机组合）
    while len(suggestions) < num and len(kw_words) >= 2:
        kw1, kw2 = random.sample(kw_words, 2)
        template = random.choice(TITLE_PATTERNS)
        emotion = random.choice(VIRAL_EMOTION_WORDS)
        n = random.choice(template.get('numbers', [5]))
        title = (template['template']
                 .replace('{kw1}', kw1)
                 .replace('{kw2}', kw2)
                 .replace('{emotion}', emotion)
                 .replace('{n}', str(n)))
        suggestions.append({
            'title': title,
            'pattern': template['name'],
            'pattern_hit_rate': round(
                pattern_hits.get(template['name'], 0) / max(len(viral_titles), 1) * 100, 1
            ),
            'keywords_used': [kw1, kw2],
        })

        if len(suggestions) >= num:
            break

    return suggestions[:num]


def score_title(title: str, category: str, db: Session) -> Dict:
    """
    对用户输入的标题进行评分（满分100）

    维度：
    - 关键词热度分（40分）：标题中词语在热词表中的热度均值
    - 长度分（30分）：与该分区爆款标题均值字数的接近程度
    - 结构分（30分）：是否命中爆款模式
    """
    if not title or not title.strip():
        return {'error': '标题不能为空'}

    # 分词
    words = nlp.segment_text(title)
    words = [w for w in words if len(w) >= 2]

    # ===== 1. 关键词热度分（40分） =====
    keywords = get_viral_keywords(category, db, top_k=100)
    kw_map = {k['word']: k['heat_score'] for k in keywords}

    matched_words = [(w, kw_map[w]) for w in words if w in kw_map]
    if matched_words:
        avg_heat = sum(s for _, s in matched_words) / len(matched_words)
        # heat_score 约 0~1，映射到 0~40
        keyword_score = min(40, round(avg_heat * 40))
    else:
        keyword_score = 0

    # ===== 2. 长度分（30分） =====
    # 获取该分区爆款视频的平均标题长度
    all_videos = (
        db.query(Video)
        .filter(Video.category == category, Video.play_count > 0)
        .order_by(desc(Video.play_count))
        .all()
    )
    viral_threshold = _get_viral_threshold(all_videos) if all_videos else 0
    viral_videos = [v for v in all_videos if v.play_count >= viral_threshold]
    viral_lengths = [len(v.title) for v in viral_videos if v.title]

    if viral_lengths:
        avg_viral_len = sum(viral_lengths) / len(viral_lengths)
        p25 = sorted(viral_lengths)[int(len(viral_lengths) * 0.25)]
        p75 = sorted(viral_lengths)[int(len(viral_lengths) * 0.75)]
    else:
        avg_viral_len, p25, p75 = 20, 12, 28  # 默认值

    title_len = len(title)
    if p25 <= title_len <= p75:
        length_score = 30
    else:
        # 高斯衰减：离最优区间越远分越低
        dist = max(0, p25 - title_len) if title_len < p25 else max(0, title_len - p75)
        length_score = max(0, round(30 * math.exp(-dist / 10)))

    # ===== 3. 结构分（30分） =====
    structure_score = 0
    matched_patterns = []
    for p in TITLE_PATTERNS:
        if re.search(p['regex'], title):
            structure_score += 15
            matched_patterns.append(p['name'])
    structure_score = min(30, structure_score)

    total_score = keyword_score + length_score + structure_score

    # ===== 生成改进建议 =====
    suggestions = []
    if keyword_score < 20:
        top_kws = [k['word'] for k in keywords[:5]]
        suggestions.append(f"建议加入热门关键词：{'、'.join(top_kws)}")
    if length_score < 20:
        suggestions.append(f"建议调整标题长度到 {int(p25)}~{int(p75)} 字（当前{title_len}字）")
    if structure_score == 0:
        suggestions.append("建议使用爆款结构：数量型（如「5个...」）、疑问型（以？结尾）或教程型（如何/怎么...）")
    if not suggestions:
        suggestions.append("标题质量不错，继续保持！")

    return {
        'total_score': total_score,
        'keyword_score': keyword_score,
        'keyword_max': 40,
        'length_score': length_score,
        'length_max': 30,
        'structure_score': structure_score,
        'structure_max': 30,
        'matched_keywords': [w for w, _ in matched_words],
        'matched_patterns': matched_patterns,
        'optimal_length': {'min': int(p25), 'max': int(p75), 'avg': round(avg_viral_len, 1)},
        'current_length': title_len,
        'suggestions': suggestions,
    }
