"""
analyzer.py - 日本語テキスト解析モジュール
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from janome.tokenizer import Tokenizer

_tokenizer = None


def _get_tokenizer() -> Tokenizer:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = Tokenizer()
    return _tokenizer


def load_text_file(path: str) -> str:
    for encoding in ['utf-8', 'utf-8-sig', 'shift-jis', 'cp932', 'euc-jp']:
        try:
            with open(path, encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(
        f"ファイルの読み込みに失敗しました: {Path(path).name}\n"
        "文字コードを UTF-8 または Shift-JIS にして再試行してください。"
    )


def load_excel_file(path: str) -> str:
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Excelファイルの読み込みに失敗しました: {Path(path).name}\n{e}")

    texts = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and cell.value.strip():
                    texts.append(cell.value.strip())
    wb.close()

    if not texts:
        raise ValueError(f"Excelファイルにテキストが見つかりません: {Path(path).name}")
    return '\n'.join(texts)


def load_files(file_paths: list) -> str:
    texts = []
    for path in file_paths:
        ext = Path(path).suffix.lower()
        if ext == '.txt':
            texts.append(load_text_file(path))
        elif ext in ('.xlsx', '.xls'):
            texts.append(load_excel_file(path))
        else:
            raise ValueError(
                f"対応していないファイル形式です: {Path(path).name}\n"
                "(.txt / .xlsx / .xls のみ対応しています)"
            )
    return '\n'.join(texts)


def split_into_sentences(text: str) -> list:
    sentences = re.split(r'[。！？\n]+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 3]


def _is_valid_word(surface: str, pos_main: str, pos_sub: str,
                   pos_filters: list, stopwords: set) -> bool:
    if pos_main not in pos_filters:
        return False
    if pos_main == '名詞' and pos_sub in ('数', '接尾', '非自立', '代名詞'):
        return False
    if pos_main == '動詞' and pos_sub == '非自立':
        return False
    if len(surface) < 2:
        return False
    if surface in stopwords:
        return False
    if re.match(r'^[0-9０-９]+$', surface):
        return False
    return True


def _get_base_form(token) -> str:
    parts = token.part_of_speech.split(',')
    base = parts[6] if len(parts) > 6 and parts[6] != '*' else token.surface
    return base


def _process_sentences(sentences: list, stopwords: set, pos_filters: list,
                        progress_cb=None) -> tuple:
    tokenizer = _get_tokenizer()
    all_tokens = []
    pair_counts = defaultdict(int)
    n = len(sentences)
    step = max(1, n // 40)

    for i, sentence in enumerate(sentences):
        sent_unique = []
        seen = set()

        for token in tokenizer.tokenize(sentence):
            parts    = token.part_of_speech.split(',')
            pos_main = parts[0]
            pos_sub  = parts[1] if len(parts) > 1 else ''
            base     = _get_base_form(token)
            if not _is_valid_word(base, pos_main, pos_sub, pos_filters, stopwords):
                continue
            all_tokens.append(base)
            if base not in seen:
                sent_unique.append(base)
                seen.add(base)

        for j in range(len(sent_unique)):
            for k in range(j + 1, len(sent_unique)):
                pair = tuple(sorted([sent_unique[j], sent_unique[k]]))
                pair_counts[pair] += 1

        if progress_cb and (i % step == 0 or i == n - 1):
            pct = 10 + int((i + 1) / n * 48)
            progress_cb(pct, '形態素解析・共起計算中…  {} / {} 文'.format(i + 1, n))

    return all_tokens, dict(pair_counts)


def analyze(file_paths: list, stopwords: set, pos_filters: list,
            min_word_freq: int = 2, min_cooc_count: int = 2,
            progress_cb=None) -> dict:
    def report(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)

    report(2, 'ファイルを読み込んでいます…')
    text = load_files(file_paths)

    if not text.strip():
        raise ValueError("ファイルにテキストが含まれていません。")

    report(8, 'テキストを文に分割しています…')
    sentences = split_into_sentences(text)

    if not sentences:
        raise ValueError("文が見つかりませんでした。テキストを確認してください。")

    report(10, '形態素解析・共起計算を開始します（{} 文）…'.format(len(sentences)))
    all_tokens, pair_counts = _process_sentences(
        sentences, stopwords, pos_filters, progress_cb=progress_cb
    )

    if not all_tokens:
        raise ValueError(
            "単語が抽出できませんでした。\n"
            "・品詞フィルターの設定を確認してください\n"
            "・最小出現回数を下げてみてください"
        )

    report(60, '出現頻度を集計しています…')
    counter      = Counter(all_tokens)
    frequencies  = {w: c for w, c in counter.items() if c >= min_word_freq}
    cooccurrence = {p: c for p, c in pair_counts.items() if c >= min_cooc_count}

    return {
        'frequencies':    frequencies,
        'cooccurrence':   cooccurrence,
        'total_tokens':   len(all_tokens),
        'unique_words':   len(counter),
        'sentence_count': len(sentences),
    }
