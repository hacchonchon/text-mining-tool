#!/bin/bash
cd "$(dirname "$0")"
echo "========================================"
echo "  テキストマイニングツール セットアップ"
echo "========================================"
echo ""
if ! command -v python3.11 &>/dev/null; then
    echo "【エラー】python3.11 が見つかりません。"
    echo "brew install python@3.11 を実行してください。"
    read -p "Enterキーで閉じます..."
    exit 1
fi
if [ ! -d "venv" ]; then
    echo "仮想環境を作成しています..."
    python3.11 -m venv venv
fi
echo "ライブラリをインストールしています（数分かかる場合があります）..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt
echo ""
echo "========================================"
echo "  セットアップ完了！"
echo "  run.command をダブルクリックして起動してください。"
echo "========================================"
read -p "Enterキーで閉じます..."
