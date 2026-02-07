"""
热词分析 P0 功能测试脚本

用法：
    cd backend
    python tests/test_keywords_actionable.py

说明：
    该脚本依赖本地数据库已有热词ETL数据。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models import User
from app.api.keywords import (
    get_keyword_movers,
    get_keyword_opportunity_risk,
    get_keyword_contributors,
    get_alert_subscription,
    update_alert_subscription,
    AlertSubscriptionUpdate,
)


def main():
    print("=" * 70)
    print("热词分析 P0 功能测试")
    print("=" * 70)

    db = SessionLocal()
    try:
        print("\n[1] 测试异动榜接口...")
        movers = get_keyword_movers(db=db, top_k=5, min_frequency=1)
        print(f"  统计日期: {movers.stat_date or '无'}")
        print(f"  爆发词数量: {len(movers.rising)}")
        print(f"  下滑词数量: {len(movers.falling)}")

        print("\n[2] 测试机会/风险榜接口...")
        opp_risk = get_keyword_opportunity_risk(
            db=db,
            top_k=5,
            min_frequency=1,
            interaction_threshold=0.05
        )
        print(f"  机会词数量: {len(opp_risk.opportunities)}")
        print(f"  风险词数量: {len(opp_risk.risks)}")

        test_word = None
        if opp_risk.opportunities:
            test_word = opp_risk.opportunities[0].word
        elif movers.rising:
            test_word = movers.rising[0].word

        if test_word:
            print(f"\n[3] 测试贡献视频接口，热词: {test_word}")
            contributors = get_keyword_contributors(word=test_word, db=db, limit=5)
            print(f"  贡献视频数量: {len(contributors.items)}")
        else:
            print("\n[3] 跳过贡献视频测试（当前无可用热词）")

        user = db.query(User).first()
        if not user:
            print("\n[4] 跳过预警订阅测试（当前无用户）")
            return

        print(f"\n[4] 测试预警订阅接口，用户: {user.username}")
        sub = get_alert_subscription(db=db, current_user=user)
        print(f"  当前配置: enabled={sub.enabled}, min_frequency={sub.min_frequency}")

        updated = update_alert_subscription(
            payload=AlertSubscriptionUpdate(
                enabled=sub.enabled,
                min_frequency=sub.min_frequency,
                growth_threshold=sub.growth_threshold,
                opportunity_sentiment_threshold=sub.opportunity_sentiment_threshold,
                negative_sentiment_threshold=sub.negative_sentiment_threshold,
                interaction_threshold=sub.interaction_threshold,
                top_k=sub.top_k,
            ),
            db=db,
            current_user=user
        )
        print(f"  更新后配置: enabled={updated.enabled}, top_k={updated.top_k}")

        print("\n测试完成。")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
