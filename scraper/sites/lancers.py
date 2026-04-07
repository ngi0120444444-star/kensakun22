"""
sites/lancers.py - ランサーズ スクレイパー
https://www.lancers.jp の案件一覧を requests + BeautifulSoup で取得する

取得ページ:
  https://www.lancers.jp/work/search?keyword=キーワード&sort=new&open=1&page={n}
"""

import time
import random
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.lancers.jp"
SEARCH_URL = BASE_URL + "/work/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
}

WAIT_MIN = 2.0
WAIT_MAX = 3.5

# フィルタリング前に取得するキーワード（空にすると全案件取得）
SEARCH_KEYWORDS = [
    # PC作業系
    "データ入力", "テキスト入力", "文字起こし", "転記",
    "アノテーション", "タグ付け", "画像確認", "テキスト校正",
    "入力作業", "リスト作成",
    # 未経験・初心者歓迎（これらのタイトルの案件も収集）
    "未経験歓迎", "初心者歓迎",
]


def _wait():
    time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))


def _fetch_page(
    keyword: str = "",
    page: int = 1,
    session: Optional[requests.Session] = None,
) -> Optional[BeautifulSoup]:
    params = {
        "sort": "new",
        "open": "1",
        "page": page,
    }
    if keyword:
        params["keyword"] = keyword

    requester = session or requests
    try:
        resp = requester.get(SEARCH_URL, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"[lancers] ページ取得失敗 keyword={keyword!r} page={page}: {e}")
        return None


def _parse_price(price_el) -> str:
    """price要素から単価テキストを組み立てる。"""
    if not price_el:
        return "—"
    numbers = [n.get_text(strip=True) for n in price_el.select(".p-search-job-media__number")]
    units = [u.get_text(strip=True) for u in price_el.select(".c-media__job-unit")]

    parts = []
    for i, num in enumerate(numbers):
        parts.append(num)
        if i < len(units):
            parts.append(units[i])
    return "".join(parts).strip() or price_el.get_text(strip=True).strip() or "—"


def _parse_item(item) -> Optional[dict]:
    """1件の案件カード（li.p-search-job-media）をパースする。"""
    # タイトル & URL
    title_el = item.select_one("a.p-search-job-media__title")
    if not title_el:
        return None

    # タグ（NEW等）を除いたタイトルテキストを取得
    for tag in title_el.select("ul.p-search-job-media__tags"):
        tag.decompose()
    title = title_el.get_text(strip=True)
    href = title_el.get("href", "")
    url = href if href.startswith("http") else BASE_URL + href

    if not title or not href:
        return None

    # 単価・報酬
    price_el = item.select_one("span.p-search-job-media__price")
    price = _parse_price(price_el)

    # 仕事タイプ（プロジェクト / タスク / コンペ / 求人）
    work_type_el = item.select_one("span.c-badge__text")
    work_type = work_type_el.get_text(strip=True) if work_type_el else "—"

    # カテゴリ
    cat_el = item.select_one("ul.p-search-job__divisions li a")
    category = cat_el.get_text(strip=True) if cat_el else "—"

    # 掲載状態（募集中・残り日数）
    time_text_el = item.select_one(".p-search-job-media__time-text")
    remaining_el = item.select_one(".p-search-job-media__time-remaining")
    status = time_text_el.get_text(strip=True) if time_text_el else ""
    remaining = remaining_el.get_text(strip=True) if remaining_el else ""
    posted_at = f"{status} {remaining}".strip() or "—"

    return {
        "title": title,
        "url": url,
        "price": f"{price}（{work_type}）" if work_type != "—" else price,
        "posted_at": posted_at,
        "category": category,
        "source": "lancers",
    }


def _parse_jobs(soup: BeautifulSoup) -> list[dict]:
    items = soup.select("li.p-search-job-media, div.p-search-job-media")
    if not items:
        # 検索結果ゼロか、セレクタ変更かを区別する
        no_result_el = soup.select_one("[class*='no-result'], [class*='empty'], .p-search-job__empty")
        result_count_el = soup.find(string=lambda t: t and "件の仕事が見つかりました" in t)
        if no_result_el or (result_count_el and "0 件" in result_count_el):
            logger.debug("[lancers] 検索結果0件")
        else:
            logger.warning("[lancers] 案件カードが見つかりません（セレクタ変更の可能性あり）")
        return []

    jobs = []
    for item in items:
        try:
            job = _parse_item(item)
            if job:
                jobs.append(job)
        except Exception as e:
            logger.warning(f"[lancers] パースエラー（スキップ）: {e}")
    return jobs


def fetch_jobs(max_pages: int = 1) -> list[dict]:
    """
    ランサーズから案件を収集して返す。
    各キーワードで検索して重複を除去したリストを返す。

    Args:
        max_pages: 各キーワードあたりの取得ページ数（デフォルト1）
    """
    all_jobs: dict[str, dict] = {}  # url -> job（重複除去）
    session = requests.Session()

    for keyword in SEARCH_KEYWORDS:
        for page in range(1, max_pages + 1):
            logger.info(f"[lancers] keyword={keyword!r} page={page} を取得中...")
            soup = _fetch_page(keyword=keyword, page=page, session=session)
            if soup is None:
                break

            jobs = _parse_jobs(soup)
            new_count = 0
            for job in jobs:
                if job["url"] not in all_jobs:
                    all_jobs[job["url"]] = job
                    new_count += 1

            logger.info(f"[lancers]   → {len(jobs)} 件取得（新規 {new_count} 件）")

            if page < max_pages:
                _wait()

        _wait()  # キーワード間のウェイト

    return list(all_jobs.values())
