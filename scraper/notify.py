"""
notify.py - LINE Notify 通知モジュール
新着案件をLINEに送信する

セットアップ:
  1. https://notify-bot.line.me/ja/ でトークンを発行
  2. scraper/.env に LINE_NOTIFY_TOKEN=xxxx を追加
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"


def _get_token() -> Optional[str]:
    """環境変数または .env ファイルから LINE_NOTIFY_TOKEN を取得する。"""
    token = os.environ.get("LINE_NOTIFY_TOKEN", "")
    if token:
        return token

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("LINE_NOTIFY_TOKEN="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "ここにトークンを貼り付け":
                        return value
    return None


def send(message: str) -> bool:
    """
    LINEにメッセージを送信する。

    Args:
        message: 送信するテキスト（最大1000文字）
    Returns:
        True: 送信成功 / False: 失敗（トークン未設定 or エラー）
    """
    token = _get_token()
    if not token:
        logger.debug("[LINE] LINE_NOTIFY_TOKEN が未設定のためスキップ")
        return False

    try:
        resp = requests.post(
            LINE_NOTIFY_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={"message": message},
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("[LINE] 通知送信成功")
            return True
        else:
            logger.warning(f"[LINE] 送信失敗: HTTP {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        logger.warning(f"[LINE] 送信エラー: {e}")
        return False


def notify_new_jobs(new_jobs: list[dict]) -> bool:
    """
    新着案件をまとめてLINEに通知する。

    Args:
        new_jobs: 新規追加された案件リスト
    Returns:
        True: 送信成功 / False: 失敗
    """
    if not new_jobs:
        return False

    count = len(new_jobs)
    lines = [f"\n【新着案件 {count}件】"]

    for i, job in enumerate(new_jobs[:5], 1):  # 最大5件表示
        title = job.get("title", "（タイトルなし）")[:30]
        price = job.get("price", "—")
        source = job.get("source", "")
        lines.append(f"\n{i}. {title}")
        lines.append(f"   {price}  [{source}]")

    if count > 5:
        lines.append(f"\n...他 {count - 5} 件")

    lines.append("\n詳細はHTMLレポートを確認してください。")

    message = "".join(lines)
    return send(message)
