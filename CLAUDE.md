# CLAUDE.md — AI アシスタント向けガイド

## リポジトリ概要

日本語テキストを形態素解析し、単語頻度・共起ネットワークを可視化する **macOS 向けデスクトップツール**。
Tkinter GUI（`app.py`）+ 解析ロジック（`analyzer.py`）の 2 層構成を想定している。

`app.py` は tkinter を使った GUI エントリーポイント。`analyzer.py` を呼び出して結果を表示する。

---

## ファイル構成

```
text-mining-tool/
├── app.py             # GUI エントリーポイント（tkinter）
├── analyzer.py        # 解析コアロジック（形態素解析・共起計算）
├── requirements.txt   # Python 依存ライブラリ
├── setup.command      # macOS 向けセットアップスクリプト（bash）
├── run.command        # macOS 向け起動スクリプト（bash）
└── .gitignore         # venv/, output/, *.png, *.csv, *.json 等を除外
```

### 除外ファイル（`.gitignore`）

| パターン | 理由 |
|---|---|
| `venv/` | Python 仮想環境 |
| `output/` | 解析結果（PNG・CSV など） |
| `*.png`, `*.csv`, `*.json` | 生成物 |
| `__pycache__/`, `*.py[cod]` | コンパイルキャッシュ |

---

## セットアップ手順（macOS）

```bash
# 1. Python 3.11 をインストール（Homebrew）
brew install python@3.11

# 2. セットアップ（venv 作成 + ライブラリインストール）
./setup.command

# 3. アプリ起動
./run.command
```

Linux / Windows での利用時は手動で仮想環境を構築し `pip install -r requirements.txt` を実行する。

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `janome>=0.5.0` | 日本語形態素解析（辞書内包、インストール不要） |
| `wordcloud>=1.9.0` | ワードクラウド生成 |
| `matplotlib>=3.7.0` | グラフ描画 |
| `networkx>=3.1` | 共起ネットワーク構築 |
| `openpyxl>=3.1.0` | Excel ファイル読み込み |
| `pillow>=10.0.0` | 画像処理 |
| `tkinterdnd2>=0.3.0` | Tkinter へのドラッグ&ドロップ対応 |

---

## `analyzer.py` — コアモジュール仕様

### 公開 API

```python
def analyze(
    file_paths: list[str],
    stopwords: set[str],
    pos_filters: list[str],
    min_word_freq: int = 2,
    min_cooc_count: int = 2,
    progress_cb: Callable[[int, str], None] | None = None,
) -> dict:
    ...
```

**戻り値の構造:**

```python
{
    'frequencies':    dict[str, int],   # 単語 → 出現回数（min_word_freq 以上）
    'cooccurrence':   dict[tuple, int], # (word_a, word_b) → 共起回数（min_cooc_count 以上）
    'total_tokens':   int,              # 抽出トークン総数
    'unique_words':   int,              # ユニーク単語数（フィルター前）
    'sentence_count': int,              # 文数
}
```

**`progress_cb(pct: int, msg: str)`:** 進捗コールバック。`pct` は 0–100 の整数。

### 内部関数

| 関数 | 役割 |
|---|---|
| `load_text_file(path)` | TXT 読み込み（UTF-8/Shift-JIS/EUC-JP 自動判定） |
| `load_excel_file(path)` | XLSX/XLS 読み込み（全シート・全セルのテキスト結合） |
| `load_files(file_paths)` | 上記を拡張子で振り分けて結合 |
| `split_into_sentences(text)` | `。！？\n` で分割、3 文字未満の断片を除去 |
| `_is_valid_word(...)` | 品詞・ストップワード・数字・1 文字語を除外 |
| `_get_base_form(token)` | janome トークンから基本形を取得 |
| `_process_sentences(...)` | 形態素解析 + 共起ペア集計のコアループ |
| `_get_tokenizer()` | `Tokenizer` をシングルトンで管理 |

### 品詞フィルター（`pos_filters`）

janome の品詞体系（UniDic に準拠）で指定する。典型的な値:

```python
['名詞', '動詞', '形容詞']
```

`_is_valid_word` 内で以下のサブ品詞は追加除外される:

- 名詞: `数`, `接尾`, `非自立`, `代名詞`
- 動詞: `非自立`

### 対応ファイル形式

- `.txt` — UTF-8, UTF-8-BOM, Shift-JIS, CP932, EUC-JP
- `.xlsx`, `.xls` — Excel（全シート対象）

---

## 開発規約

### コードスタイル

- Python 3.11 以上を前提とする（`from __future__ import annotations` を使用）
- 型ヒントを積極的に使用する
- モジュールは責務単位で分割する（解析ロジックと UI を混在させない）
- エラーメッセージは日本語で、ユーザーへの次アクション（対処法）を含める

### コミットメッセージ

```
<種別>: <変更概要>

# 種別の例
feat:   新機能追加
fix:    バグ修正
refactor: リファクタリング
docs:   ドキュメント変更
chore:  設定・依存関係の変更
```

### ブランチ戦略

- 主幹ブランチ: `master`
- 作業ブランチ: `claude/<説明>-<セッションID>` 形式（AI 作業時）

---

## 既知の問題・TODO

- [x] `app.py`（GUI エントリーポイント）を追加済み。
- [ ] テストコードが存在しない。`analyzer.py` の各関数に対するユニットテスト追加を推奨。
- [ ] Windows / Linux 向けの起動スクリプトが未整備。

---

## よくある質問

**Q: 形態素解析が遅い**
A: janome はピュア Python 実装のため大量テキストで低速になる場合がある。MeCab + python-mecab-ko 等への置き換えを検討する。

**Q: Excel の特定シートだけ読みたい**
A: 現状は全シートを結合する仕様。`load_excel_file` にシート名フィルターを追加することで対応可能。

**Q: ストップワードをファイルで管理したい**
A: `analyzer.py` は `stopwords: set[str]` を引数で受け取るため、呼び出し側（`app.py`）でファイル読み込みを実装する。
