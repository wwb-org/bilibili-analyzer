"""
历史评论细粒度情绪回填脚本

用法:
  cd backend
  python scripts/backfill_comment_emotion.py --batch-size 200
  python scripts/backfill_comment_emotion.py --batch-size 200 --force-all
  python scripts/backfill_comment_emotion.py --bvid BV1xx411c7mD
  python scripts/backfill_comment_emotion.py --start-id 1 --end-id 50000
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Comment, Video
from app.services.emotion import EmotionAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="历史评论细粒度情绪回填脚本")
    parser.add_argument("--batch-size", type=int, default=200, help="每批处理数量，默认 200")
    parser.add_argument("--bvid", type=str, default=None, help="只回填指定 BVID")
    parser.add_argument("--start-id", type=int, default=None, help="起始评论 ID（包含）")
    parser.add_argument("--end-id", type=int, default=None, help="结束评论 ID（包含）")
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="覆盖重算全部命中评论（默认仅处理 emotion_label 为空的记录）",
    )
    return parser


def build_base_query(
    db: Session,
    bvid: str | None,
    start_id: int | None,
    end_id: int | None,
    force_all: bool = False,
):
    query = db.query(Comment)
    if bvid:
        query = query.join(Video, Video.id == Comment.video_id).filter(Video.bvid == bvid)
    if start_id is not None:
        query = query.filter(Comment.id >= start_id)
    if end_id is not None:
        query = query.filter(Comment.id <= end_id)

    if not force_all:
        query = query.filter(Comment.emotion_label.is_(None))
    return query


def run_backfill(
    db: Session,
    batch_size: int,
    bvid: str | None = None,
    start_id: int | None = None,
    end_id: int | None = None,
    force_all: bool = False,
):
    analyzer = EmotionAnalyzer()

    base_query = build_base_query(db, bvid, start_id, end_id, force_all=force_all)
    total = base_query.count()
    if total == 0:
        print("没有需要回填的评论记录。")
        return

    print(f"待回填评论总数: {total}")
    print(f"回填模式: {'覆盖重算全部命中记录' if force_all else '仅补齐 emotion_label 为空记录'}")
    start_at = time.time()

    processed = 0
    success = 0
    failed = 0
    last_id = 0

    while True:
        batch_query = build_base_query(
            db,
            bvid,
            start_id,
            end_id,
            force_all=force_all,
        ).filter(Comment.id > last_id)
        comments = batch_query.order_by(Comment.id.asc()).limit(batch_size).all()
        if not comments:
            break

        for comment in comments:
            last_id = comment.id
            processed += 1

            retry = 0
            updated = False
            while retry < 2 and not updated:
                try:
                    result = analyzer.analyze_emotion(comment.content or "")
                    comment.sentiment_score = result.sentiment_score
                    comment.emotion_label = result.emotion_label
                    comment.emotion_scores_json = result.emotion_scores
                    comment.emotion_model_version = result.model_version
                    comment.emotion_analyzed_at = result.analyzed_at
                    updated = True
                except Exception as exc:
                    retry += 1
                    if retry >= 2:
                        failed += 1
                        print(f"[WARN] 评论ID={comment.id} 回填失败: {exc}")

            if updated:
                success += 1

        db.commit()
        progress = round(processed / total * 100, 2)
        print(
            f"[进度] {processed}/{total} ({progress}%) | 成功={success} 失败={failed}"
        )

    elapsed = time.time() - start_at
    qps = round(success / elapsed, 2) if elapsed > 0 else 0
    print("=" * 60)
    print("回填完成")
    print(f"总数: {total}")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    print(f"耗时: {round(elapsed, 2)} 秒")
    print(f"平均吞吐: {qps} 条/秒")


def main():
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        run_backfill(
            db=db,
            batch_size=max(args.batch_size, 1),
            bvid=args.bvid,
            start_id=args.start_id,
            end_id=args.end_id,
            force_all=args.force_all,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
