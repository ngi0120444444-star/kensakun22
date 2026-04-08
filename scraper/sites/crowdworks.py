"""
sites/crowdworks.py - クラウドワークス スクレイパー
https://crowdworks.jp の案件一覧を Playwright（ヘッドレスブラウザ）で取得する

CrowdWorksはVue.js SPAのため、JavaScriptを実行できるPlaywrightが必要。

初回セットアップ（一度だけ実行）:
  pip install playwright
  playwright install chromium
"""

import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://crowdworks.jp"
SEARCH_URL = BASE_URL + "/public/jobs/search"

WAIT_MIN = 2.0
WAIT_MAX = 3.5


def _wait():
    time.sleep(random.uniform(WAIT_MIN, WAIT_MAX))


def _check_playwright():
    """Playwrightがインストール済みか確認する。"""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _parse_jobs_from_html(html: str) -> list[dict]:
    """
    Playwrightで取得したHTMLをBeautifulSoupでパースして案件リストを返す。

    CrowdWorksのレンダリング後HTML構造（変更された場合はセレクタを修正）:
      案件カード:   li[class*='job_offer'] または article[class*='job_offer']
      タイトル/URL: a[href*='/public/jobs/']
      単価:         [class*='reward'] または [class*='price']
      カテゴリ:     [class*='job_type'] または [class*='category']
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # 案件カード候補セレクタ
    import re as _re

    # CrowdWorks は li タグ（クラスなし）が1案件に対応
    # クラス名にVueのハッシュが付くため class*= で部分一致
    items = [
        li for li in soup.find_all("li")
        if li.find("a", href=_re.compile(r"/public/jobs/\d+"))
    ]

    if not items:
        logger.warning("[crowdworks] 案件カードが見つかりません（サイト構造変更の可能性）")
        return []

    logger.debug(f"[crowdworks] {len(items)} 件のカードを発見")

    for item in items:
        try:
            job = _parse_item(item)
            if job:
                jobs.append(job)
        except Exception as e:
            logger.warning(f"[crowdworks] パースエラー（スキップ）: {e}")

    return jobs


def _parse_item(item) -> Optional[dict]:
    """1件の案件カード（li）をパースする。
    クラス名はVueハッシュ付きのため class*= で部分一致させる。
    例: _titleLinkPc_1i9l4_26 → [class*='titleLink']
    """
    import re as _re

    # ── タイトル & URL ──────────────────────────────────────────
    title_el = (
        item.select_one("[class*='titleLink']")
        or item.find("a", href=_re.compile(r"/public/jobs/\d+"))
    )
    if not title_el:
        return None

    title = title_el.get_text(strip=True)
    href  = title_el.get("href", "")
    # カテゴリリンク等を除外（/public/jobs/数字 のみ）
    if not _re.search(r"/public/jobs/\d+", href):
        return None
    url = href if href.startswith("http") else BASE_URL + href
    if not title:
        return None

    # ── 単価・報酬 ───────────────────────────────────────────────
    # 支払方式: span[class*='paymentLabel'] → "固定報酬制" / "時間単価制"
    # 金額:     b[class*='amountPc']        → "〜5,000円" / "2,000円〜3,000円"
    pay_type_el = item.select_one("[class*='paymentLabel']")
    amount_el   = item.select_one("[class*='amountPc']")
    pay_type = pay_type_el.get_text(strip=True) if pay_type_el else ""
    amount   = amount_el.get_text(strip=True)   if amount_el   else ""
    # 不要な空白・改行を正規化
    amount = _re.sub(r"\s+", "", amount)
    price = f"{pay_type}　{amount}".strip() if (pay_type or amount) else "—"

    # ── 掲載日 ──────────────────────────────────────────────────
    # div[class*='postDatePc'] → "掲載日：2026年03月31日"
    date_el = item.select_one("[class*='postDatePc']")
    if date_el:
        raw = date_el.get_text(strip=True)
        posted_at = raw.replace("掲載日：", "").strip()
    else:
        # フォールバック: 締切日
        limit_el = item.select_one("[class*='absoluteDate']")
        posted_at = limit_el.get_text(strip=True) if limit_el else "—"

    # ── カテゴリ ─────────────────────────────────────────────────
    cat_el = item.find("a", href=_re.compile(r"/public/jobs/category/"))
    category = cat_el.get_text(strip=True) if cat_el else "—"

    return {
        "title":     title,
        "url":       url,
        "price":     price,
        "posted_at": posted_at,
        "category":  category,
        "source":    "crowdworks",
    }


def fetch_jobs(max_pages: int = 1) -> list[dict]:
    """
    クラウドワークスから案件を収集して返す（Playwright使用）。

    Args:
        max_pages: 取得するページ数（デフォルト1）
    """
    if not _check_playwright():
        logger.error(
            "[crowdworks] Playwrightがインストールされていません。\n"
            "  pip install playwright\n"
            "  playwright install chromium\n"
            "を実行してください。"
        )
        return []

    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    all_jobs = []

    with sync_playwright() as p:
        # headless_shell が見つからない場合は通常のChromiumにフォールバック
        import glob as _glob
        _headless = _glob.glob(
            r"C:\Users\USER\AppData\Local\ms-playwright\chromium_headless_shell-*"
            r"\chrome-headless-shell-win64\chrome-headless-shell.exe"
        )
        _chromium = _glob.glob(
            r"C:\Users\USER\AppData\Local\ms-playwright\chromium-*"
            r"\chrome-win64\chrome.exe"
        )
        _exe = (_headless or _chromium or [None])[0]
        launch_opts = {"headless": True}
        if _exe:
            launch_opts["executable_path"] = _exe
            logger.info(f"[crowdworks] ブラウザ: {_exe}")
        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )
        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{SEARCH_URL}?keep_search_form=true&order=new&page={page_num}"
            logger.info(f"[crowdworks] ページ {page_num} を取得中: {url}")

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Vue.jsのレンダリング完了を待つ
                # 案件カードまたは「件数」テキストが表示されるまで待機
                try:
                    page.wait_for_selector(
                        "li[class*='job_offer'], article[class*='job_offer'], "
                        "a[href*='/public/jobs/']",
                        timeout=15000,
                    )
                except PlaywrightTimeout:
                    logger.warning(f"[crowdworks] ページ {page_num}: 案件カードのタイムアウト")

                html = page.content()
                jobs = _parse_jobs_from_html(html)
                logger.info(f"[crowdworks] ページ {page_num}: {len(jobs)} 件取得")
                all_jobs.extend(jobs)

            except PlaywrightTimeout:
                logger.warning(f"[crowdworks] ページ {page_num}: ページロードタイムアウト（スキップ）")
            except Exception as e:
                logger.warning(f"[crowdworks] ページ {page_num}: エラー（スキップ）: {e}")

            if page_num < max_pages:
                _wait()

        context.close()
        browser.close()

    return all_jobs
