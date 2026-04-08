"""
run.py - エントリポイント
使用例:
  python run.py                       # デフォルト: lancers（requests版）
  python run.py --site lancers        # ランサーズのみ
  python run.py --site crowdworks     # クラウドワークスのみ（Playwright必要）
  python run.py --all                 # 全サイト実行
  python run.py --pages 3             # 取得ページ数を指定
"""

import sys
import os
import argparse
import logging

# scraper/ ディレクトリをパスに追加（直接実行用）
sys.path.insert(0, os.path.dirname(__file__))

from sites import get_scraper, REGISTRY
from filters import filter_jobs
from storage import save_jobs, load_jobs
from report import generate_report
from notify import notify_new_jobs


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="就労継続支援B型向け PC作業案件 自動収集スクリプト"
    )
    site_group = parser.add_mutually_exclusive_group()
    site_group.add_argument(
        "--site",
        default="lancers",
        help=f"収集対象サイト（デフォルト: lancers）。選択肢: {', '.join(REGISTRY.keys())}",
    )
    site_group.add_argument(
        "--all",
        action="store_true",
        help="登録済み全サイトを順番に実行する",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="取得ページ数（デフォルト: 1）",
    )
    return parser.parse_args()


def run_site(site_name: str, pages: int, logger: logging.Logger) -> dict:
    """1サイトの収集→フィルタ→保存を実行して結果を返す。"""
    logger.info(f"  ▶ {site_name} 開始")

    try:
        scraper = get_scraper(site_name)
    except ValueError as e:
        logger.error(str(e))
        return {"fetched": 0, "matched": 0, "added": 0}

    # 収集
    try:
        jobs = scraper.fetch_jobs(max_pages=pages)
    except Exception as e:
        logger.error(f"  [{site_name}] 収集エラー: {e}")
        jobs = []

    logger.info(f"  [{site_name}] 取得: {len(jobs)} 件")

    if not jobs:
        logger.warning(f"  [{site_name}] 取得0件。サイト構造変更の可能性あり")

    # フィルタ
    matched = filter_jobs(jobs)
    logger.info(f"  [{site_name}] マッチ: {len(matched)} 件")

    if matched:
        kw_summary: dict[str, int] = {}
        for job in matched:
            for kw in job.get("matched_keywords", []):
                kw_summary[kw] = kw_summary.get(kw, 0) + 1
        for kw, count in sorted(kw_summary.items(), key=lambda x: -x[1]):
            logger.info(f"           「{kw}」: {count} 件")

    # 保存（新規追加分を特定するため保存前後でURLセットを比較）
    before_urls = {j["url"] for j in load_jobs()}
    result = save_jobs(matched)
    logger.info(
        f"  [{site_name}] 新規追加: {result['added']} 件  "
        f"スキップ(重複): {result['skipped']} 件"
    )

    # 新規追加された案件を取得（LINE通知用）
    newly_added = [j for j in matched if j["url"] not in before_urls]

    return {
        "fetched": len(jobs),
        "matched": len(matched),
        "added": result["added"],
        "new_jobs": newly_added,
    }


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    args = parse_args()

    sites = list(REGISTRY.keys()) if args.all else [args.site]

    logger.info("=" * 55)
    logger.info(f"対象サイト: {', '.join(sites)}  取得ページ数: {args.pages}")
    logger.info("=" * 55)

    total_fetched = total_matched = total_added = 0

    all_new_jobs = []

    for i, site_name in enumerate(sites):
        if i > 0:
            logger.info("-" * 55)
        result = run_site(site_name, args.pages, logger)
        total_fetched += result["fetched"]
        total_matched += result["matched"]
        total_added += result["added"]
        all_new_jobs.extend(result.get("new_jobs", []))

    # HTMLレポート生成（全サイト完了後に1回だけ）
    logger.info("=" * 55)
    logger.info("【レポート生成】output/index.html を更新中...")
    total_saved = generate_report()
    output_path = os.path.join(os.path.dirname(__file__), "output", "index.html")
    logger.info(f"  → 生成完了（累計 {total_saved} 件）")
    logger.info(f"  → {os.path.abspath(output_path)}")

    logger.info("=" * 55)
    logger.info(
        f"完了: 取得 {total_fetched} 件 → マッチ {total_matched} 件 → "
        f"新規保存 {total_added} 件（累計 {total_saved} 件）"
    )
    logger.info("=" * 55)

    # LINE通知（新規案件がある場合のみ）
    if all_new_jobs:
        logger.info(f"【LINE通知】新着 {len(all_new_jobs)} 件を送信中...")
        notify_new_jobs(all_new_jobs)


if __name__ == "__main__":
    main()
