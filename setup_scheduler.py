"""
setup_scheduler.py - Windowsタスクスケジューラへの自動実行登録

実行方法（コマンドプロンプトで管理者権限不要）:
  python setup_scheduler.py

登録されるタスク:
  - タスク名: 就労B型_案件収集
  - 実行時刻: 毎朝 9:00
  - 実行内容: 全サイト（ランサーズ＋クラウドワークス）から案件を収集

削除方法:
  python setup_scheduler.py --delete
"""

import subprocess
import sys
import os
import argparse


TASK_NAME = "就労B型_案件収集"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(SCRIPT_DIR, "scraper")
RUN_PY = os.path.join(SCRAPER_DIR, "run.py")


def get_python_path() -> str:
    """現在のPythonインタープリタのパスを返す。"""
    return sys.executable


def register_task(hour: int = 9, minute: int = 0):
    """タスクスケジューラに毎日の実行タスクを登録する。"""
    python = get_python_path()
    # PLAYWRIGHT_BROWSERS_PATH を設定してcrowdworksが動くようにする
    playwright_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "ms-playwright"
    )

    # バッチファイル経由で環境変数を設定してから実行
    bat_path = os.path.join(SCRIPT_DIR, "_scheduler_run.bat")
    bat_content = (
        "@echo off\n"
        f"set PLAYWRIGHT_BROWSERS_PATH={playwright_path}\n"
        f"cd /d \"{SCRAPER_DIR}\"\n"
        f"\"{python}\" \"{RUN_PY}\" --all --pages 2\n"
    )
    with open(bat_path, "w", encoding="cp932") as f:
        f.write(bat_content)

    time_str = f"{hour:02d}:{minute:02d}"
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", f'"{bat_path}"',
        "/SC", "DAILY",
        "/ST", time_str,
        "/F",           # 既存タスクを上書き
        "/RL", "HIGHEST",  # 最高権限
    ]

    print(f"タスク登録中: {TASK_NAME}")
    print(f"  実行時刻: 毎日 {time_str}")
    print(f"  実行スクリプト: {bat_path}")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp932")
    if result.returncode == 0:
        print("✓ タスクスケジューラへの登録が完了しました！")
        print(f"  毎日 {time_str} に自動実行されます。")
        print(f"  確認: タスクスケジューラ → タスクスケジューラライブラリ → {TASK_NAME}")
    else:
        print(f"✗ 登録失敗: {result.stderr or result.stdout}")
        sys.exit(1)


def delete_task():
    """登録済みタスクを削除する。"""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp932")
    if result.returncode == 0:
        print(f"✓ タスク「{TASK_NAME}」を削除しました。")
    else:
        print(f"✗ 削除失敗（未登録の可能性あり）: {result.stderr or result.stdout}")


def show_task():
    """登録済みタスクの状態を表示する。"""
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp932")
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"タスク「{TASK_NAME}」は未登録です。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="タスクスケジューラ設定ツール")
    parser.add_argument("--delete", action="store_true", help="登録済みタスクを削除する")
    parser.add_argument("--status", action="store_true", help="登録状態を確認する")
    parser.add_argument("--hour", type=int, default=9, help="実行時刻（時）デフォルト: 9")
    parser.add_argument("--minute", type=int, default=0, help="実行時刻（分）デフォルト: 0")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    elif args.status:
        show_task()
    else:
        register_task(hour=args.hour, minute=args.minute)
