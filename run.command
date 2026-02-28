#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    echo "【エラー】venv フォルダが見つかりません。先に setup.command を実行してください。"
    read -p "Enterキーで閉じます..."
    exit 1
fi
venv/bin/python app.py
