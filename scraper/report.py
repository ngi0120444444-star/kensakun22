"""
report.py - HTMLレポート生成
output/jobs.json を読み込んで output/index.html を生成する
"""

import os
from datetime import datetime
from storage import load_jobs

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
HTML_FILE = os.path.join(OUTPUT_DIR, "index.html")

_CSS = """
<style>
  body { font-family: sans-serif; margin: 20px; background: #f9f9f9; color: #333; }
  h1 { font-size: 1.4rem; border-bottom: 2px solid #4a90e2; padding-bottom: 6px; }
  p.meta { font-size: 0.85rem; color: #666; }
  table { border-collapse: collapse; width: 100%; background: #fff; }
  th { background: #4a90e2; color: #fff; padding: 8px 10px; text-align: left; font-size: 0.9rem; }
  td { padding: 7px 10px; border-bottom: 1px solid #e0e0e0; font-size: 0.88rem; vertical-align: top; }
  tr:hover td { background: #f0f6ff; }
  a { color: #1a6bb5; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .kw  { display: inline-block; background: #e8f0fe; color: #3a5bb5; border-radius: 3px;
         padding: 1px 5px; margin: 1px; font-size: 0.8rem; }
  .tag { display: inline-block; background: #e6f4ea; color: #276c37; border-radius: 3px;
         padding: 1px 5px; margin: 1px; font-size: 0.8rem; }
  .src { display: inline-block; background: #f3f3f3; color: #666; border-radius: 3px;
         padding: 1px 5px; font-size: 0.75rem; }
  .no-data { color: #999; font-style: italic; }
</style>
"""


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_report() -> int:
    """
    HTMLレポートを生成して output/index.html に保存する。
    Returns: 出力した案件件数
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    jobs = load_jobs()

    # 取得日時の新しい順に並べ替え
    jobs.sort(key=lambda j: j.get("fetched_at", ""), reverse=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for job in jobs:
        title      = _escape(job.get("title", "（タイトルなし）"))
        url        = _escape(job.get("url", "#"))
        price      = _escape(job.get("price", "—"))
        posted_at  = _escape(job.get("posted_at", "—"))
        fetched_at = _escape(job.get("fetched_at", "—"))
        source     = _escape(job.get("source", ""))
        b_reason   = _escape(job.get("b_reason", ""))

        # マッチキーワード
        keywords = job.get("matched_keywords", [])
        kw_html = "".join(f'<span class="kw">{_escape(k)}</span>' for k in keywords)
        if not kw_html:
            kw_html = '<span class="no-data">—</span>'

        # 適合タグ（優遇キーワードがあれば表示）
        prefer_tags = ""
        if b_reason and "（" in b_reason:
            tags = b_reason.split("（")[1].rstrip("）").split(", ")
            prefer_tags = "".join(f'<span class="tag">{_escape(t)}</span>' for t in tags if t)

        # サイトバッジ
        src_html = f'<span class="src">{source}</span>' if source else ""

        rows.append(
            f"<tr>"
            f'<td><a href="{url}" target="_blank" rel="noopener">{title}</a> {src_html}</td>'
            f"<td>{price}</td>"
            f"<td>{posted_at}</td>"
            f"<td>{kw_html}</td>"
            f"<td>{prefer_tags if prefer_tags else '<span class=\"no-data\">—</span>'}</td>"
            f"<td>{fetched_at}</td>"
            f"</tr>"
        )

    table_body = "\n".join(rows) if rows else (
        '<tr><td colspan="6" class="no-data" style="text-align:center">'
        '案件データがありません</td></tr>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>B型向け PC作業案件リスト</title>
  {_CSS}
</head>
<body>
  <h1>就労継続支援B型 PC作業案件リスト</h1>
  <p class="meta">生成日時: {generated_at} &nbsp;|&nbsp; 件数: {len(jobs)}</p>
  <table>
    <thead>
      <tr>
        <th>タイトル</th>
        <th>単価・報酬</th>
        <th>掲載日</th>
        <th>マッチキーワード</th>
        <th>適合ポイント</th>
        <th>取得日時</th>
      </tr>
    </thead>
    <tbody>
      {table_body}
    </tbody>
  </table>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    return len(jobs)
