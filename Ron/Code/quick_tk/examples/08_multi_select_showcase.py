"""
Multi-Select Dropdown Showcase - Demonstrating compact, uncluttered multi-select controls in QuickTk.
Features:
- Single-row compact dropdown display with smart count summaries.
- Interactive popup with real-time search/filter for large option lists.
- 'All' and 'None' quick selection buttons.
- Mousewheel scrolling.
- Full integration with FormPanel get_values(), set_value(), and clear().
"""

import os
import sys
from tkinter import ttk

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


class MultiSelectShowcase(ToolView):
    title = "Multi-Select Dropdown Showcase"

    def build_ui(self):
        # Configure layout: Left column (form), Right column (results)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Input Form
        self.form = self.add_form("Configuration Parameters", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Watchlist Multi-Select
        self.symbols_dd = self.form.add_multi_select(
            name="symbols",
            label="Target Watchlist (Small List)",
            options=["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD"],
            default=["AAPL", "NVDA", "TSLA"],
            placeholder="Select tickers...",
            max_display=3,
        )

        # Large Option List with Filter
        indicator_list = [
            "SMA (20)", "SMA (50)", "SMA (200)",
            "EMA (9)", "EMA (21)", "EMA (55)",
            "RSI (14)", "Stochastic RSI",
            "MACD (12, 26, 9)", "MACD Histogram",
            "Bollinger Bands (20, 2)", "Keltner Channels",
            "ATR (14)", "Chaikin Money Flow",
            "VWAP (Session)", "VWAP Bands",
            "Volume Profile (POC)", "Delta Volume",
            "SuperTrend (10, 3)", "Ichimoku Cloud"
        ]
        self.indicators_dd = self.form.add_multi_select(
            name="indicators",
            label="Active Indicators (Large List - Try Filtering!)",
            options=indicator_list,
            default=["SMA (20)", "RSI (14)", "VWAP (Session)"],
            placeholder="Select indicators...",
            max_display=2,
        )

        # Export Formats Multi-Select
        self.formats_dd = self.form.add_multi_select(
            name="formats",
            label="Export Targets",
            options=["CSV Spreadsheet", "JSON Payload", "Parquet Table", "SQLite Database", "Excel XLSX"],
            default=["CSV Spreadsheet", "JSON Payload"],
        )

        # Action Buttons
        self.form.add_button_group([
            ("Apply Selection", self.on_run, "primary"),
            ("Select All Indicators", self.on_select_all_indicators, "secondary"),
            ("Reset Defaults", self.on_reset, "secondary")
        ])

        # 2. Right Results Panel: StatGrid + DataTable
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        self.stats = self.add_stat_grid(columns=3, parent=right_box)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.table = self.add_data_table(
            columns=["Category", "Selection Count", "Selected Items"],
            parent=right_box,
            enable_search=True,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")

        # 3. Top Menu Bar
        self.setup_menus()

        # Initial display
        self.on_run(self.form.get_values())

    def setup_menus(self):
        file_menu = self.menu("File")
        file_menu.add_item("Apply Selection", lambda: self.on_run(self.form.get_values()), shortcut="Ctrl+R")
        file_menu.add_separator()
        file_menu.add_item("Exit", self.app.root.quit, shortcut="Alt+F4")

        preset_menu = self.menu("Presets")
        preset_menu.add_item("Select All Indicators", self.on_select_all_indicators)
        preset_menu.add_item("Clear All Indicators", lambda: (self.indicators_dd.clear(), self.on_run(self.form.get_values())))
        preset_menu.add_separator()
        preset_menu.add_item("Reset to Defaults", self.on_reset)

        view_menu = self.menu("View")
        view_menu.add_item("Refresh Table", lambda: self.on_run(self.form.get_values()), shortcut="F5")

    def on_run(self, inputs: dict):
        if not isinstance(inputs, dict):
            inputs = self.form.get_values()
        symbols = inputs.get("symbols", [])
        indicators = inputs.get("indicators", [])
        formats = inputs.get("formats", [])

        self.stats.set_metrics({
            "Watchlist Size": (f"{len(symbols)} tickers", "info"),
            "Active Indicators": (f"{len(indicators)} active", "success" if len(indicators) > 0 else "warning"),
            "Export Formats": (f"{len(formats)} targets", "info"),
        })

        table_rows = [
            ["Watchlist", str(len(symbols)), ", ".join(symbols) if symbols else "(None)"],
            ["Indicators", str(len(indicators)), ", ".join(indicators) if indicators else "(None)"],
            ["Export Targets", str(len(formats)), ", ".join(formats) if formats else "(None)"],
        ]
        self.table.set_data(table_rows)

    def on_select_all_indicators(self):
        self.indicators_dd.select_all()
        self.on_run(self.form.get_values())

    def on_reset(self):
        self.symbols_dd.set(["AAPL", "NVDA", "TSLA"])
        self.indicators_dd.set(["SMA (20)", "RSI (14)", "VWAP (Session)"])
        self.formats_dd.set(["CSV Spreadsheet", "JSON Payload"])
        self.on_run(self.form.get_values())


if __name__ == "__main__":
    app = QuickApp(title="QuickTk Multi-Select Demo", size=(950, 750))
    app.set_single_tool(MultiSelectShowcase)
    app.run()
