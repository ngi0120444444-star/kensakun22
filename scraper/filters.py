"""
filters.py - キーワードフィルタリング＋B型適合判定
案件タイトルをキーワードリストで照合し、さらにB型事業所利用者向けかを判定する
"""

# ── 収集キーワード（いずれかを含む案件を対象とする） ─────────────────────────
KEYWORDS = [
    "データ入力",
    "テキスト入力",
    "文字起こし",
    "転記",
    "アノテーション",
    "タグ付け",
    "画像確認",
    "テキスト校正",
    "入力作業",
    "リスト作成",
]

# ── B型不適合：除外キーワード（タイトルに含まれていたら除外） ─────────────────
# 専門スキル・常勤・高報酬案件を除外する
EXCLUDE_KEYWORDS = [
    # 技術・開発系
    "エンジニア", "開発", "プログラム", "コーディング", "実装",
    "Python", "Java", "PHP", "Ruby", "Swift", "Kotlin", "React", "Vue",
    "システム", "データベース", "SQL", "API", "インフラ", "クラウド",
    "機械学習", "AI", "ディープラーニング", "LLM",
    "デバッグ", "テスト設計", "QA", "品質管理",
    "設計", "アーキテクチャ",
    # 管理・高度業務
    "ディレクター", "プロデューサー", "プロジェクトマネージャー", "PM",
    "コンサル", "マーケティング", "営業", "人事", "経理",
    "編集長", "チーフ", "リーダー", "マネージャー",
    # 雇用形態・勤務条件
    "週5日", "週4日", "週3日", "週3以上", "週4以上", "常駐", "正社員", "業務委託（常勤）",
    # 高度ライティング・編集
    "要約", "記事校閲", "校閲", "ライター", "編集",
    # 成人・特殊コンテンツ
    "成人向け", "アダルト", "18禁",
    # 資格・経験必須
    "資格必須", "経験必須", "実務経験",
]

# ── B型不適合：除外URLパターン ────────────────────────────────────────────────
EXCLUDE_URL_PATTERNS = [
    "tech-agent.lancers.jp",    # ランサーズのエンジニア専門サイト
    "onsite.lancers.jp",        # ランサーズの常勤求人（サブドメイン型）
    "lancers.jp/onsite/",       # ランサーズの常勤求人（パス型）
]

# ── B型適合：優遇キーワード（含まれていると適合度UP） ────────────────────────
PREFER_KEYWORDS = [
    "初心者", "初心者OK", "未経験", "未経験OK", "未経験歓迎",
    "在宅", "リモート", "テレワーク", "自宅",
    "簡単", "かんたん", "コツコツ", "単純", "繰り返し",
    "主婦", "ママ", "副業", "隙間時間",
    "タスク",
]


def match_keywords(title: str) -> list[str]:
    """タイトルにマッチする収集キーワードのリストを返す。"""
    return [kw for kw in KEYWORDS if kw in title]


def is_b_suitable(job: dict) -> tuple[bool, str]:
    """
    B型事業所利用者に適した案件かを判定する。

    Returns:
        (適合フラグ, 除外理由または適合理由)
    """
    title = job.get("title", "")
    url   = job.get("url", "")
    price = job.get("price", "")

    # ① URLパターンで除外
    for pat in EXCLUDE_URL_PATTERNS:
        if pat in url:
            return False, f"除外URL: {pat}"

    # ② タイトルの除外キーワードで除外
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return False, f"除外キーワード: {kw}"

    # ③ 単価チェック：月額20万円超 → 常勤・高スキル案件とみなして除外
    #    「〇〇万」「¥〇〇万」「〇〇万〜〇〇万」などを検出
    import re
    # 「¥ 30万」「30万」「30万 〜 40万」など最初に出てくる万円数値を取得
    man = re.search(r'[\¥￥]?\s*(\d+)\s*万', price)
    if man and int(man.group(1)) >= 20:
        return False, f"高額月給: {price}"

    # ④ 適合
    matched_prefer = [kw for kw in PREFER_KEYWORDS if kw in title]
    reason = "適合" + (f"（{', '.join(matched_prefer)}）" if matched_prefer else "")
    return True, reason


def filter_jobs(jobs: list[dict]) -> list[dict]:
    """
    案件リストをフィルタリングして返す。
    各案件に matched_keywords / b_suitable / b_reason を付与する。
    収集キーワードにマッチし、かつB型適合と判定された案件のみ返す。
    """
    result = []
    for job in jobs:
        matched = match_keywords(job.get("title", ""))
        if not matched:
            continue

        suitable, reason = is_b_suitable(job)
        if not suitable:
            continue

        job = dict(job)
        job["matched_keywords"] = matched
        job["b_suitable"] = suitable
        job["b_reason"] = reason
        result.append(job)
    return result
