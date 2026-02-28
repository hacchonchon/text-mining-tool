"""
app.py - テキストマイニングツール GUI
"""
from __future__ import annotations
import os
import platform
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import analyzer

_DEFAULT_POS = ['名詞', '動詞', '形容詞']
_ALL_POS     = ['名詞', '動詞', '形容詞', '副詞']
_IS_MACOS    = platform.system() == 'Darwin'
_FONT_BODY   = ('Hiragino Sans', 12) if _IS_MACOS else ('TkDefaultFont', 12)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('テキストマイニングツール')
        self.geometry('860x780')
        self.minsize(640, 620)
        self.resizable(True, True)

        self._file_paths: list[str] = []
        self._running = False

        self._build_ui()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ===== ファイル選択 =====
        file_frame = ttk.LabelFrame(self, text='ファイル選択（.txt / .xlsx / .xls）', padding=8)
        file_frame.pack(fill='x', padx=12, pady=(12, 4))

        self._file_label = ttk.Label(file_frame, text='（未選択）', foreground='gray')
        self._file_label.pack(side='left', fill='x', expand=True)

        ttk.Button(file_frame, text='クリア',           command=self._clear_files).pack(side='right', padx=(4, 0))
        ttk.Button(file_frame, text='ファイルを開く…', command=self._open_files).pack(side='right')

        # ===== テキスト入力 =====
        text_frame = ttk.LabelFrame(
            self, text='テキスト入力（直接入力 または ファイル読み込み後に自動表示）', padding=8
        )
        text_frame.pack(fill='both', expand=True, padx=12, pady=4)

        self._text_input = tk.Text(
            text_frame, height=10, wrap='word', font=_FONT_BODY, undo=True,
        )
        scroll_txt = ttk.Scrollbar(text_frame, command=self._text_input.yview)
        self._text_input.configure(yscrollcommand=scroll_txt.set)
        scroll_txt.pack(side='right', fill='y')
        self._text_input.pack(fill='both', expand=True)

        # ===== 解析オプション =====
        opt_frame = ttk.LabelFrame(self, text='解析オプション', padding=8)
        opt_frame.pack(fill='x', padx=12, pady=4)

        # 品詞フィルター
        pos_row = ttk.Frame(opt_frame)
        pos_row.pack(fill='x')
        ttk.Label(pos_row, text='品詞フィルター:').pack(side='left')
        self._pos_vars: dict[str, tk.BooleanVar] = {}
        for pos in _ALL_POS:
            var = tk.BooleanVar(value=(pos in _DEFAULT_POS))
            self._pos_vars[pos] = var
            ttk.Checkbutton(pos_row, text=pos, variable=var).pack(side='left', padx=6)

        # 数値オプション
        num_row = ttk.Frame(opt_frame)
        num_row.pack(fill='x', pady=(6, 0))
        ttk.Label(num_row, text='最小出現回数:').pack(side='left')
        self._min_freq = tk.IntVar(value=2)
        ttk.Spinbox(num_row, from_=1, to=100, textvariable=self._min_freq, width=5).pack(side='left', padx=(4, 16))
        ttk.Label(num_row, text='最小共起回数:').pack(side='left')
        self._min_cooc = tk.IntVar(value=2)
        ttk.Spinbox(num_row, from_=1, to=100, textvariable=self._min_cooc, width=5).pack(side='left', padx=4)

        # ストップワード
        sw_row = ttk.Frame(opt_frame)
        sw_row.pack(fill='x', pady=(6, 0))
        ttk.Label(sw_row, text='除外語（スペース区切り）:').pack(side='left')
        self._sw_entry = ttk.Entry(sw_row)
        self._sw_entry.pack(side='left', fill='x', expand=True, padx=(4, 0))

        # ===== 分析ボタン・プログレスバー =====
        run_frame = ttk.Frame(self)
        run_frame.pack(fill='x', padx=12, pady=6)

        self._analyze_btn = ttk.Button(run_frame, text='  分析する  ', command=self._start_analyze)
        self._analyze_btn.pack(side='left')

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            run_frame, variable=self._progress_var, maximum=100, length=400,
        )
        self._progress_bar.pack(side='left', padx=10, fill='x', expand=True)

        self._status_label = ttk.Label(run_frame, text='', width=24)
        self._status_label.pack(side='left')

        # ===== 結果エリア =====
        result_outer = ttk.LabelFrame(self, text='分析結果', padding=8)
        result_outer.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        self._stats_label = ttk.Label(result_outer, text='')
        self._stats_label.pack(anchor='w', pady=(0, 6))

        tables_frame = ttk.Frame(result_outer)
        tables_frame.pack(fill='both', expand=True)

        # 頻出単語テーブル
        freq_frame = ttk.LabelFrame(tables_frame, text='頻出単語 TOP 30', padding=4)
        freq_frame.pack(side='left', fill='both', expand=True, padx=(0, 6))

        self._freq_tree = ttk.Treeview(
            freq_frame, columns=('rank', 'word', 'count'), show='headings', height=14,
        )
        self._freq_tree.heading('rank',  text='順位')
        self._freq_tree.heading('word',  text='単語')
        self._freq_tree.heading('count', text='出現回数')
        self._freq_tree.column('rank',  width=48, anchor='center')
        self._freq_tree.column('word',  width=130)
        self._freq_tree.column('count', width=72, anchor='center')
        freq_sb = ttk.Scrollbar(freq_frame, command=self._freq_tree.yview)
        self._freq_tree.configure(yscrollcommand=freq_sb.set)
        freq_sb.pack(side='right', fill='y')
        self._freq_tree.pack(fill='both', expand=True)

        # 共起ペアテーブル
        cooc_frame = ttk.LabelFrame(tables_frame, text='共起ペア TOP 30', padding=4)
        cooc_frame.pack(side='left', fill='both', expand=True)

        self._cooc_tree = ttk.Treeview(
            cooc_frame, columns=('word_a', 'word_b', 'count'), show='headings', height=14,
        )
        self._cooc_tree.heading('word_a', text='単語 A')
        self._cooc_tree.heading('word_b', text='単語 B')
        self._cooc_tree.heading('count',  text='共起回数')
        self._cooc_tree.column('word_a', width=110)
        self._cooc_tree.column('word_b', width=110)
        self._cooc_tree.column('count',  width=72, anchor='center')
        cooc_sb = ttk.Scrollbar(cooc_frame, command=self._cooc_tree.yview)
        self._cooc_tree.configure(yscrollcommand=cooc_sb.set)
        cooc_sb.pack(side='right', fill='y')
        self._cooc_tree.pack(fill='both', expand=True)

    # ------------------------------------------------------------------
    # ファイル操作
    # ------------------------------------------------------------------

    def _open_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title='ファイルを選択',
            filetypes=[
                ('対応ファイル', '*.txt *.xlsx *.xls'),
                ('テキスト',    '*.txt'),
                ('Excel',       '*.xlsx *.xls'),
                ('すべて',      '*.*'),
            ],
        )
        if not paths:
            return

        self._file_paths = list(paths)
        names = ', '.join(os.path.basename(p) for p in self._file_paths)
        self._file_label.configure(text=names, foreground='black')

        # .txt 1 ファイルのみのとき内容をテキストエリアにプレビュー
        if len(self._file_paths) == 1 and self._file_paths[0].lower().endswith('.txt'):
            try:
                content = analyzer.load_text_file(self._file_paths[0])
                self._text_input.delete('1.0', 'end')
                self._text_input.insert('1.0', content)
            except ValueError:
                pass  # プレビュー失敗はサイレント

    def _clear_files(self) -> None:
        self._file_paths = []
        self._file_label.configure(text='（未選択）', foreground='gray')
        self._text_input.delete('1.0', 'end')

    # ------------------------------------------------------------------
    # 分析
    # ------------------------------------------------------------------

    def _start_analyze(self) -> None:
        if self._running:
            return

        pos_filters = [pos for pos, var in self._pos_vars.items() if var.get()]
        if not pos_filters:
            messagebox.showwarning('設定エラー', '品詞フィルターを 1 つ以上選択してください。')
            return

        stopwords = set(self._sw_entry.get().split())

        # ファイル未選択ならテキストエリアの内容を一時ファイルに保存して使う
        tmp_path: str | None = None
        if self._file_paths:
            file_paths = self._file_paths
        else:
            text = self._text_input.get('1.0', 'end').strip()
            if not text:
                messagebox.showwarning(
                    '入力エラー', 'テキストを入力するか、ファイルを選択してください。'
                )
                return
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', encoding='utf-8', delete=False
            )
            tmp.write(text)
            tmp.close()
            file_paths = [tmp.name]
            tmp_path   = tmp.name

        self._running = True
        self._analyze_btn.configure(state='disabled')
        self._progress_var.set(0)
        self._status_label.configure(text='')
        self._clear_results()

        def progress_cb(pct: int, msg: str) -> None:
            self.after(0, lambda p=pct: self._progress_var.set(p))
            self.after(0, lambda m=msg: self._status_label.configure(text=m))

        def run() -> None:
            try:
                result = analyzer.analyze(
                    file_paths   = file_paths,
                    stopwords    = stopwords,
                    pos_filters  = pos_filters,
                    min_word_freq  = self._min_freq.get(),
                    min_cooc_count = self._min_cooc.get(),
                    progress_cb  = progress_cb,
                )
                self.after(0, lambda r=result: self._show_results(r))
            except ValueError as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror('エラー', err))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror('予期しないエラー', err))
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                self.after(0, self._on_analyze_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_analyze_done(self) -> None:
        self._running = False
        self._analyze_btn.configure(state='normal')

    def _clear_results(self) -> None:
        self._stats_label.configure(text='')
        self._freq_tree.delete(*self._freq_tree.get_children())
        self._cooc_tree.delete(*self._cooc_tree.get_children())

    def _show_results(self, result: dict) -> None:
        self._stats_label.configure(
            text=(
                f"文数: {result['sentence_count']}　"
                f"総トークン数: {result['total_tokens']}　"
                f"ユニーク語数: {result['unique_words']}　"
                f"頻出語（フィルター後）: {len(result['frequencies'])} 語"
            )
        )

        top_words = sorted(result['frequencies'].items(), key=lambda x: x[1], reverse=True)[:30]
        for rank, (word, count) in enumerate(top_words, 1):
            self._freq_tree.insert('', 'end', values=(rank, word, count))

        top_pairs = sorted(result['cooccurrence'].items(), key=lambda x: x[1], reverse=True)[:30]
        for (w_a, w_b), count in top_pairs:
            self._cooc_tree.insert('', 'end', values=(w_a, w_b, count))

        self._status_label.configure(text='分析完了')
        self._progress_var.set(100)


# ------------------------------------------------------------------
# エントリーポイント
# ------------------------------------------------------------------

def main() -> None:
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
