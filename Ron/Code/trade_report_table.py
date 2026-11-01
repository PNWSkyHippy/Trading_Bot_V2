"""A text-backed report table: Tk Text supports a color for each value.

Keep raw values separate from display strings so sorting and CSV stay numeric.
This is deliberately local to the trade reports; other QuickTk tables stay as-is.
"""
import tkinter as tk
from tkinter import ttk

from local_functions import chkstr_isnum


class TradeReportTable(ttk.Frame):
    def __init__(self, parent, columns):
        super().__init__(parent)
        self.columns = list(columns)
        self._raw_data = []
        self.visible_rows = []
        self._sort_reverse = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text="Filter:").grid(row=0, column=0)
        self._search_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self._search_var).grid(row=0, column=1, sticky="ew", padx=8)
        self.count = ttk.Label(controls)
        self.count.grid(row=0, column=2)
        self._search_var.trace_add("write", lambda *_: self._apply_search())
        options = dict(wrap="none", font=("Consolas", 10), background="#181825",
                       foreground="#cdd6f4", borderwidth=0, padx=6, cursor="arrow")
        self.header = tk.Text(self, height=1, **options)
        self.header.grid(row=1, column=0, sticky="ew")
        self.text = tk.Text(self, **options)
        self.text.grid(row=2, column=0, sticky="nsew")
        self.text.tag_configure("positive", foreground="#00c000")
        self.text.tag_configure("negative", foreground="#ff3030")
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        vertical.grid(row=2, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self._xview)
        horizontal.grid(row=3, column=0, sticky="ew")
        self.text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    def _xview(self, *args):
        self.header.xview(*args)
        self.text.xview(*args)

    @staticmethod
    def cell(column, value):
        """Match the legacy report's exclusions, precision and sign colors."""
        if value is None:
            return "", ""
        if column in ("trade_id", "exit_reason", "entry_time", "exit_time"):
            return str(value).replace("\n", " ").replace("\t", " "), ""
        if chkstr_isnum(value) == "float":
            number = float(value)
            return f"{number:.6f}", "positive" if number >= 0 else "negative"
        return str(value).replace("\n", " ").replace("\t", " "), ""

    def set_data(self, rows):
        self._raw_data = [list(row) for row in rows]
        # Measure once across the report, so filtering doesn't shift columns.
        self.widths = [max([len(column)] + [len(self.cell(column, row[i])[0])
                       for row in rows]) + 3 for i, column in enumerate(self.columns)]
        self.header.configure(state="normal")
        self.header.delete("1.0", "end")
        for i, column in enumerate(self.columns):
            tag = f"heading_{i}"
            self.header.tag_configure(tag, foreground="#c040d0")
            self.header.tag_bind(tag, "<Button-1>", lambda event, c=column: self._sort_column(c))
            self.header.insert("end", column.ljust(self.widths[i]), (tag,))
        self.header.configure(state="disabled")
        self._apply_search()

    def _sort_column(self, column):
        index = self.columns.index(column)
        def key(row):
            try:
                return (0, float(row[index]))
            except (TypeError, ValueError):
                return (1, str(row[index]).lower())
        reverse = self._sort_reverse.get(column, False)
        self._raw_data.sort(key=key, reverse=reverse)
        self._sort_reverse[column] = not reverse
        self._apply_search()

    def _apply_search(self):
        query = self._search_var.get().strip().lower()
        self.visible_rows = [row for row in self._raw_data
                             if not query or any(query in str(v).lower() for v in row)]
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for row in self.visible_rows:
            for i, (column, value) in enumerate(zip(self.columns, row)):
                display, tag = self.cell(column, value)
                self.text.insert("end", display, (tag,) if tag else ())
                self.text.insert("end", " " * (self.widths[i] - len(display)))
            self.text.insert("end", "\n")
        self.text.configure(state="disabled")
        self.count.configure(text=f"{len(self.visible_rows):,} rows")
        self._xview("moveto", 0)
