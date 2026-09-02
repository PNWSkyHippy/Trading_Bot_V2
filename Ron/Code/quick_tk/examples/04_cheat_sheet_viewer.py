"""
Python Syntax & Cheat Sheet Viewer Tool
Demonstrates hierarchical topic browsing, ConsolePanel syntax highlighting, and method references.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView

TOPIC_DATA = {
    "Lists": {
        "summary": "Ordered, mutable sequences of heterogeneous items.",
        "methods": [
            ("append(x)", "Adds an item to the end of the list."),
            ("extend(iterable)", "Appends all elements from another iterable."),
            ("insert(i, x)", "Inserts item x at index i."),
            ("pop([i])", "Removes and returns item at index i (default last)."),
            ("remove(x)", "Removes first occurrence of value x."),
            ("sort(key=None, reverse=False)", "Sorts items in-place."),
            ("reverse()", "Reverses elements in-place."),
        ],
        "code": """# Python Lists Examples

# 1. Creating and Appending
fruits = ["apple", "banana", "cherry"]
fruits.append("dragonfruit")

# 2. List Slicing & Comprehensions
squares = [x ** 2 for x in range(10) if x % 2 == 0]
print("Even squares:", squares)

# 3. Sorting with Custom Key
words = ["python", "tkinter", "oop", "gui"]
words.sort(key=len, reverse=True)
print("Sorted by length:", words)
"""
    },
    "Dictionaries": {
        "summary": "Key-value associative mappings with fast O(1) average hash lookup.",
        "methods": [
            ("get(key, default)", "Safely retrieve value without KeyError."),
            ("keys()", "Returns a view of all dictionary keys."),
            ("values()", "Returns a view of all dictionary values."),
            ("items()", "Returns (key, value) pairs as iterable tuples."),
            ("update(dict2)", "Merges another dictionary into current one."),
            ("pop(key, default)", "Removes key and returns its value."),
            ("setdefault(k, d)", "Inserts key with default value if not present."),
        ],
        "code": """# Python Dictionaries Examples

# 1. Initialization and Safe Access
trade = {
    "symbol": "ES",
    "contracts": 2,
    "entry": 5240.25,
    "pnl": 350.0
}
strategy = trade.get("strategy", "Standard Breakout")

# 2. Iterating items
for key, value in trade.items():
    print(f"{key.upper()}: {value}")

# 3. Dictionary Comprehension
multipliers = {sym: mult for sym, mult in [("ES", 50), ("NQ", 20), ("MES", 5)]}
print("Tick Multipliers:", multipliers)
"""
    },
    "Lists of Dictionaries": {
        "summary": "Common data structure for tabular records, SQLite results, and JSON APIs.",
        "methods": [
            ("Filtering", "Using list comprehensions: [r for r in rows if r['pnl'] > 100]"),
            ("Sorting", "Using sorted(rows, key=lambda x: x['pnl'], reverse=True)"),
            ("Extracting Column", "[r['symbol'] for r in rows]"),
            ("Aggregating", "sum(r['pnl'] for r in rows)"),
        ],
        "code": """# Lists of Dictionaries (Tabular Data Pattern)

trades = [
    {"id": 1, "symbol": "ES", "strategy": "Breakout", "pnl": 450.0},
    {"id": 2, "symbol": "NQ", "strategy": "Scalp", "pnl": -125.0},
    {"id": 3, "symbol": "MES", "strategy": "Breakout", "pnl": 220.0},
]

# 1. Filter only winning trades
winners = [t for t in trades if t["pnl"] > 0]

# 2. Sort by highest PnL
sorted_trades = sorted(trades, key=lambda x: x["pnl"], reverse=True)

# 3. Compute Total PnL
total_pnl = sum(t["pnl"] for t in trades)
print(f"Total PnL across {len(trades)} trades: ${total_pnl:,.2f}")
"""
    },
    "String Operations & Formatting": {
        "summary": "Immutable character sequences with powerful formatting and manipulation methods.",
        "methods": [
            ("split(sep)", "Splits string by delimiter into a list."),
            ("join(iterable)", "Concatenates iterable of strings with separator."),
            ("strip([chars])", "Trims leading and trailing whitespace/chars."),
            ("replace(old, new)", "Replaces all occurrences of substring."),
            ("startswith(prefix)", "Checks if string starts with given prefix."),
            ("format() / f-strings", "Formatted string interpolation."),
        ],
        "code": """# String Formatting & Methods

# 1. Modern f-string formatting
symbol = "ES"
pnl = 1250.75
status = "PROFIT"
report = f"[{symbol}] Trade Result: ${pnl:+,.2f} ({status})"
print(report)

# 2. Splitting and Joining
raw_csv_line = "2026-08-31,ES,Breakout,2,450.00"
fields = raw_csv_line.split(",")
rejoined = " | ".join(fields)
print(rejoined)
"""
    },
    "OOP Classes & Inheritance": {
        "summary": "Object-Oriented Programming structures encapsulating data and behavior.",
        "methods": [
            ("__init__(self, ...)", "Constructor method for initializing instance attributes."),
            ("self", "Reference to the current instance of the class."),
            ("super().__init__()", "Calls parent class constructor in inheritance."),
            ("@classmethod", "Method bound to the class rather than instance."),
            ("@property", "Decorator for getter/setter encapsulation."),
        ],
        "code": """# Object-Oriented Python Pattern

class BaseUtilityTool:
    def __init__(self, name: str):
        self.name = name

    def execute(self, inputs: dict) -> dict:
        raise NotImplementedError("Subclasses must implement execute()")

class TradeFilterTool(BaseUtilityTool):
    def __init__(self, min_pnl: float = 0.0):
        super().__init__("Trade Filter")
        self.min_pnl = min_pnl

    def execute(self, trades: list) -> list:
        return [t for t in trades if t.get("pnl", 0) >= self.min_pnl]

# Usage
filter_tool = TradeFilterTool(min_pnl=100.0)
print(f"Initialized tool: {filter_tool.name}")
"""
    }
}


class CheatSheetTool(ToolView):
    title = "Python Reference & Cheat Sheet"
    description = "Interactive Python documentation, syntax guide, and method cheat-sheets"

    def build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Topic Browser
        self.form = self.add_form("Topics & Categories", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        topics = list(TOPIC_DATA.keys())
        self.form.add_radio("topic", "Select Category", topics, default=topics[0], horizontal=False, on_change=self.on_topic_selected)
        self.form.add_button("View Quick Guide", callback=self.on_view_clicked, variant="primary")

        # 2. Right Split: Method Table on top + Console Code Viewer on bottom
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        self.method_table = self.add_data_table(
            columns=["Method / Operation", "Description & Usage"],
            parent=right_box,
            enable_search=True,
            enable_export_csv=False,
        )
        self.method_table.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self.console = self.add_console(title="Code Reference & Interactive Examples", parent=right_box)
        self.console.grid(row=1, column=0, sticky="nsew")

        # Load initial topic
        self.on_topic_selected(topics[0])

    def on_view_clicked(self, values: dict):
        self.on_topic_selected(values.get("topic", "Lists"))

    def on_topic_selected(self, topic_name: str):
        data = TOPIC_DATA.get(topic_name)
        if not data:
            return

        # Update methods table
        rows = [[m[0], m[1]] for m in data["methods"]]
        self.method_table.set_data(rows)

        # Update console code view
        self.console.clear()
        self.console.write_heading(f"{topic_name.upper()} REFERENCE")
        self.console.write_line(f"Overview: {data['summary']}\n", "dim")
        self.console.write_code(data["code"])
        self.set_status(f"Displaying {topic_name} guide.")


if __name__ == "__main__":
    app = QuickApp(title="Python Knowledge & Cheat Sheet", size=(1080, 720))
    app.set_single_tool(CheatSheetTool)
    app.run()
