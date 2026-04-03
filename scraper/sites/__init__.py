"""
sites/__init__.py - スクレイパープラグインレジストリ
新しいサイトを追加する場合は、ここに登録するだけでrun.pyから使えるようになる。

追加方法:
  1. sites/newsite.py を作成し、fetch_jobs() -> list[dict] を実装する
  2. 下記 REGISTRY に { "サイト名": モジュール } を追加する

各スクレイパーが返す dict の共通フィールド:
  - title    (str)  : 案件タイトル
  - url      (str)  : 案件URL（重複チェックのキー）
  - price    (str)  : 単価・報酬（テキスト）
  - posted_at (str) : 掲載日（テキスト）
  - category (str)  : カテゴリ
  - source   (str)  : サイト識別子（例: "crowdworks"）
"""

from sites import crowdworks, lancers

REGISTRY: dict[str, object] = {
    "crowdworks": crowdworks,
    "lancers": lancers,
}


def get_scraper(site_name: str):
    """
    サイト名からスクレイパーモジュールを返す。
    未登録のサイト名は ValueError を送出する。
    """
    if site_name not in REGISTRY:
        available = ", ".join(REGISTRY.keys())
        raise ValueError(f"未対応のサイト: '{site_name}'。利用可能: {available}")
    return REGISTRY[site_name]
