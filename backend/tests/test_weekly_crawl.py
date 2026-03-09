"""
每周必看历史数据采集脚本

用法：
    # 采集最近 10 期（快速测试）
    python tests/test_weekly_crawl.py

    # 采集所有期数（全量入库，需要几个小时）
    python tests/test_weekly_crawl.py --all

    # 采集最近 N 期
    python tests/test_weekly_crawl.py --episodes 30

    # 每视频不采评论（最快，只入库视频基础数据）
    python tests/test_weekly_crawl.py --all --no-comments
"""
import sys
import os

# 把 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.crawler import BilibiliCrawler


def main():
    # ====== 参数解析 ======
    args = sys.argv[1:]
    crawl_all = '--all' in args
    no_comments = '--no-comments' in args

    max_episodes = None  # None = 全部
    if not crawl_all:
        max_episodes = 10  # 默认只采最近10期
        for i, arg in enumerate(args):
            if arg == '--episodes' and i + 1 < len(args):
                try:
                    max_episodes = int(args[i + 1])
                except ValueError:
                    pass

    comments_per_video = 0 if no_comments else 20

    # ====== 初始化爬虫 ======
    cookie = getattr(settings, 'BILIBILI_COOKIE', '') or ''
    crawler = BilibiliCrawler(cookie=cookie)

    print("=" * 50)
    print("B站每周必看历史数据采集")
    print("=" * 50)
    if max_episodes:
        print(f"采集期数: 最新 {max_episodes} 期")
    else:
        print("采集期数: 全部（预计 200+ 期）")
    print(f"每视频评论: {comments_per_video} 条")
    if not cookie:
        print("提示: 未配置 Cookie，评论数量会受限")
    print("=" * 50)
    print()

    # ====== 开始采集 ======
    stats = crawler.crawl_weekly_series(
        max_episodes=max_episodes,
        comments_per_video=comments_per_video,
    )

    print()
    print("=" * 50)
    print("采集结果汇总")
    print("=" * 50)
    print(f"  完成期数:   {stats['episodes_done']}")
    print(f"  新增视频:   {stats['videos_saved']}")
    print(f"  已有更新:   {stats['videos_skipped']}")
    print(f"  新增评论:   {stats['comments_saved']}")
    print(f"  错误数量:   {len(stats['errors'])}")
    if stats['errors'][:5]:
        print("  最近错误:")
        for e in stats['errors'][:5]:
            print(f"    - {e}")


if __name__ == '__main__':
    main()
