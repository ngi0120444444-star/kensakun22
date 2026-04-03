# -*- coding: utf-8 -*-
import os

python_exe = r"C:\Users\USER\AppData\Local\Python\bin\python.exe"
script     = r"C:\Users\USER\Desktop\検索\scraper\run.py"
output     = r"C:\Users\USER\Desktop\検索\scraper\output\index.html"
desktop    = r"C:\Users\USER\Desktop"

files = {
    "ランサーズ収集.bat":        f'@echo off\r\n"{python_exe}" "{script}" --site lancers\r\npause\r\n',
    "クラウドワークス収集.bat":  f'@echo off\r\n"{python_exe}" "{script}" --site crowdworks\r\npause\r\n',
    "全サイト収集.bat":          f'@echo off\r\n"{python_exe}" "{script}" --all\r\npause\r\n',
    "結果を開く.bat":            f'@echo off\r\nstart "" "{output}"\r\n',
}

for name, content in files.items():
    path = os.path.join(desktop, name)
    with open(path, "w", encoding="cp932") as f:
        f.write(content)
    print(f"OK: {name}")
