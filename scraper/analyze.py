# -*- coding: utf-8 -*-
"""
analyze.py - 収集した案件をClaudeに分析させる

使い方:
  python analyze.py                      # 全案件を分析
  python analyze.py --top 5              # 上位5件に絞る
  python analyze.py --question "単価が高い順に教えて"  # 自由質問

APIキーの設定:
  環境変数 ANTHROPIC_API_KEY に設定するか、
  このスクリプトと同じフォルダに .env ファイルを作成して
      ANTHROPIC_API_KEY=sk-ant-...
  と書いてください。
"""

import os
import sys
import json
import argparse

# .env ファイルから APIキーを読み込む（python-dotenv不要）
def _load_dotenv():
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

JOBS_FILE = os.path.join(os.path.dirname(__file__), "output", "jobs.json")

DEFAULT_QUESTION = """
就労継続支援B型事業所の利用者（障害のある方）が取り組む案件として、
以下の観点で分析・評価してください。

1. **おすすめ案件TOP3**
   - 理由（難易度・単価・継続性など）

2. **各案件の一言コメント**
   - 難易度（★1〜5）
   - 向いている人

3. **全体的な傾向と注意点**
   - 今回の案件全体を通じて気になる点

わかりやすく、支援員が利用者に説明しやすい言葉でお願いします。
"""


def load_jobs() -> list[dict]:
    if not os.path.exists(JOBS_FILE):
        print(f"[ERROR] jobs.json が見つかりません: {JOBS_FILE}")
        print("先にバッチファイルで案件収集を実行してください。")
        sys.exit(1)

    with open(JOBS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    jobs = list(data.values()) if isinstance(data, dict) else data
    if not jobs:
        print("[ERROR] 案件データが空です。先に収集を実行してください。")
        sys.exit(1)
    return jobs


def format_jobs(jobs: list[dict]) -> str:
    lines = []
    for i, job in enumerate(jobs, 1):
        title    = job.get("title", "（不明）")
        url      = job.get("url", "")
        price    = job.get("price", "—")
        source   = job.get("source", "")
        keywords = ", ".join(job.get("matched_keywords", []))
        b_reason = job.get("b_reason", "")

        lines.append(
            f"【案件{i}】{title}\n"
            f"  出典: {source} | 単価: {price}\n"
            f"  キーワード: {keywords} | 適合理由: {b_reason}\n"
            f"  URL: {url}"
        )
    return "\n\n".join(lines)


def analyze(question: str, top: int | None = None):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY が設定されていません。")
        print()
        print("設定方法:")
        print("  scraper/.env ファイルを作成して以下を記入してください:")
        print("    ANTHROPIC_API_KEY=sk-ant-xxxxxx...")
        print()
        print("  APIキーはこちらで取得できます:")
        print("  https://console.anthropic.com/")
        sys.exit(1)

    import anthropic

    jobs = load_jobs()
    if top:
        jobs = jobs[:top]

    jobs_text = format_jobs(jobs)
    total = len(jobs)

    print(f"案件数: {total} 件をClaudeに送信しています...")
    print("-" * 50)

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""以下は就労継続支援B型事業所向けに収集した在宅PC作業の案件リストです（全{total}件）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{jobs_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{question}"""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=(
            "あなたは就労継続支援B型事業所の支援員のアシスタントです。"
            "障害のある利用者が安心して取り組める在宅PC作業案件を選定・評価する専門家として回答してください。"
        ),
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print("\n" + "-" * 50)
    print("分析完了。")


def main():
    parser = argparse.ArgumentParser(description="収集案件をClaudeで分析する")
    parser.add_argument("--top",      type=int, default=None, help="分析する件数（上位N件）")
    parser.add_argument("--question", type=str, default=None, help="Claudeへの質問（省略時はデフォルト分析）")
    args = parser.parse_args()

    question = args.question if args.question else DEFAULT_QUESTION
    analyze(question=question, top=args.top)


if __name__ == "__main__":
    main()
