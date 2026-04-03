"""
storage.py - JSON保存・読み込み
output/jobs.json への保存と重複チェック（URLベース）
将来的にSupabase等のDBへ差し替えやすいよう、関数インターフェースを統一
"""

import json
import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
JOBS_FILE = os.path.join(OUTPUT_DIR, "jobs.json")


def _load_raw() -> dict:
    """jobs.json を読み込み、{url: job} の辞書で返す。ファイルがなければ空辞書。"""
    if not os.path.exists(JOBS_FILE):
        return {}
    try:
        with open(JOBS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # リスト形式の古いデータにも対応
        if isinstance(data, list):
            return {job["url"]: job for job in data if "url" in job}
        return data
    except (json.JSONDecodeError, KeyError):
        return {}


def load_jobs() -> list[dict]:
    """保存済み案件をリスト形式で返す。"""
    return list(_load_raw().values())


def save_jobs(new_jobs: list[dict]) -> dict:
    """
    新しい案件を既存データにマージして保存する。
    URL重複は既存データを保持（上書きしない）。

    Returns:
        {"added": int, "skipped": int} - 追加件数とスキップ件数
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    existing = _load_raw()

    added = 0
    skipped = 0
    fetched_at = datetime.now().isoformat(timespec="seconds")

    for job in new_jobs:
        url = job.get("url", "")
        if not url:
            skipped += 1
            continue
        if url in existing:
            skipped += 1
        else:
            job = dict(job)
            job["fetched_at"] = fetched_at
            existing[url] = job
            added += 1

    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return {"added": added, "skipped": skipped}
