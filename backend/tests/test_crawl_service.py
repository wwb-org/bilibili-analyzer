"""
测试采集服务层（带情感分析）

用法：
    cd backend
    python tests/test_crawl_service.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.crawl_service import CrawlService


def main():
    print("="*60)
    print("测试采集服务层（带情感分析和日志）")
    print("="*60)

    service = CrawlService()

    # 采集5个视频，每个视频50条评论
    # 这样可以快速测试情感分析功能
    stats = service.crawl_popular_videos(max_videos=50, comments_per_video=50)

    print("\n" + "="*60)
    print("采集统计")
    print("="*60)
    print(f"视频已爬取: {stats['videos_crawled']}")
    print(f"视频已保存: {stats['videos_saved']}")
    print(f"评论已保存: {stats['comments_saved']}")

    if stats['errors']:
        print(f"\n错误数量: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"  - {error}")

    print("\n提示：可以查看数据库中的 crawl_logs 表查看采集日志")


if __name__ == "__main__":
    main()
