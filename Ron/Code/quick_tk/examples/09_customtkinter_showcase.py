"""
CustomTkinter (CTk) Modern Controls Showcase - QuickTk v1.4.0
Demonstrates:
- Initializing QuickApp with modern CustomTkinter window shell (use_ctk=True).
- FormPanel integration with CTkSwitch, CTkSegmentedButton, CTkSlider, CTkProgressBar, CTkEntry, and CTkTextbox.
- Coexistence with native QuickTk MultiSelectDropdown, StatGrid KPI cards, and DataTable.
- Full extraction via form.get_values() and programmatic updates with form.set_value().
"""

import os
import sys
import time
from tkinter import ttk

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


class CustomTkinterShowcase(ToolView):
    title = "CustomTkinter Modern Controls Showcase"

    def build_ui(self):
        # Configure layout: Left column (form), Right column (results & previews)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Form Panel with CTk Controls
        self.form = self.add_form("Modern Strategy Parameters", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # CTk Entry with Placeholder
        self.form.add_ctk_entry(
            name="strategy_name",
            label="Strategy Title",
            placeholder="e.g. Mean Reversion Scalp v2",
            default="Momentum Alpha",
        )

        # MultiSelect Dropdown (from quick_tk)
        self.symbols_dd = self.form.add_multi_select(
            name="symbols",
            label="Watchlist Symbols",
            options=["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "AMD"],
            default=["AAPL", "NVDA"],
            placeholder="Select tickers...",
            max_display=3,
        )

        # CTk Segmented Button (iOS/Win11 Pill Tabs)
        self.form.add_ctk_segmented(
            name="timeframe",
            label="Execution Timeframe (CTkSegmentedButton)",
            values=["1m", "5m", "15m", "1h", "1D"],
            default="5m",
            on_change=lambda val: self.on_run(),
        )

        # CTk Animated Toggle Switches
        self.form.add_ctk_switch(
            name="paper_trading",
            label="Execution Environment (CTkSwitch)",
            text="Paper Trading Mode (Safety On)",
            default=True,
            on_change=lambda val: self.on_run(),
        )
        self.form.add_ctk_switch(
            name="telegram_alerts",
            label="Notifications",
            text="Send Real-Time Telegram Alerts",
            default=False,
            on_change=lambda val: self.on_run(),
        )

        # CTk Rounded Slider
        self.form.add_ctk_slider(
            name="risk_pct",
            label="Risk Allocation (%) (CTkSlider)",
            from_=0.5,
            to=10.0,
            default=2.5,
            number_of_steps=19,
            on_change=lambda val: self.on_run(),
        )

        # CTk Smooth Progress Bar
        self.prog_bar = self.form.add_ctk_progress(
            name="scan_progress",
            label="Scan Progress Monitor (CTkProgressBar)",
            default=0.45,
        )

        # CTk Multi-Line Textbox
        self.form.add_ctk_textbox(
            name="notes",
            label="Trader Execution Notes (CTkTextbox)",
            default="Observing resistance at 50 EMA. Bracket orders armed.",
            height=70,
        )

        # Action Buttons
        self.form.add_ctk_button(
            label="Apply Parameters",
            callback=self.on_run,
            variant="primary",
        )
        self.form.add_ctk_button(
            label="Simulate 100% Scan (Async Animation)",
            callback=self.simulate_scan,
            variant="success",
        )
        self.form.add_ctk_button(
            label="Reset Defaults",
            callback=self.on_reset,
            variant="secondary",
        )

        # 2. Right Results Panel: StatGrid + DataTable
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        self.stats = self.add_stat_grid(columns=3, parent=right_box)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.table = self.add_data_table(
            columns=[
                "Control Type",
                "Field Name",
                "Extracted Value (form.get_values())",
            ],
            parent=right_box,
            enable_search=True,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")

        # Top Menu Bar
        self.setup_menus()

        # Initial display
        self.on_run()

    def setup_menus(self):
        file_menu = self.menu("File")
        file_menu.add_item(
            "Apply Configuration", lambda: self.on_run(), shortcut="Ctrl+R"
        )
        file_menu.add_separator()
        file_menu.add_item("Exit", self.app.root.quit, shortcut="Alt+F4")

        tools_menu = self.menu("Actions")
        tools_menu.add_item("Simulate Progress Scan", self.simulate_scan)
        tools_menu.add_item("Reset to Defaults", self.on_reset)

    def on_run(self, inputs: dict = None):
        if not isinstance(inputs, dict):
            inputs = self.form.get_values()

        risk = inputs.get("risk_pct", 0.0)
        paper = inputs.get("paper_trading", False)
        tf = inputs.get("timeframe", "5m")
        symbols = inputs.get("symbols", [])

        # Update KPI cards
        self.stats.set_metrics(
            {
                "Mode": (
                    "PAPER" if paper else "LIVE",
                    "success" if paper else "danger",
                ),
                "Timeframe": (tf, "info"),
                "Risk / Trade": (f"{risk:.1f}%", "warning" if risk > 5.0 else "info"),
                "Watchlist": (f"{len(symbols)} tickers", "info"),
            }
        )

        # Update Data Table showing real-time form.get_values()
        table_rows = [
            ["CTkEntry", "strategy_name", str(inputs.get("strategy_name", ""))],
            [
                "MultiSelectDropdown",
                "symbols",
                ", ".join(symbols) if symbols else "(None)",
            ],
            ["CTkSegmentedButton", "timeframe", str(tf)],
            [
                "CTkSwitch",
                "paper_trading",
                f"{paper} (Safety {'Active' if paper else 'Disabled'})",
            ],
            ["CTkSwitch", "telegram_alerts", str(inputs.get("telegram_alerts", False))],
            ["CTkSlider", "risk_pct", f"{risk:.2f}%"],
            [
                "CTkProgressBar",
                "scan_progress",
                f"{float(inputs.get('scan_progress', 0.0)):.1%}",
            ],
            ["CTkTextbox", "notes", str(inputs.get("notes", "")).strip()],
        ]
        self.table.set_data(table_rows)

    def simulate_scan(self, *args):
        """Smoothly animates the CTkProgressBar on a background thread without freezing GUI."""

        def _worker():
            for p in range(0, 101, 5):
                self.prog_bar.set(p / 100.0)
                time.sleep(0.04)
            return True

        def _on_done(res):
            self.on_run()
            self.set_status("Scan complete: 100% processed!")

        self.run_async(
            _worker, on_done=_on_done, status_msg="Running simulation scan..."
        )

    def on_reset(self, *args):
        self.form.clear()
        self.form.set_value("strategy_name", "Momentum Alpha")
        self.form.set_value("symbols", ["AAPL", "NVDA"])
        self.form.set_value("timeframe", "5m")
        self.form.set_value("paper_trading", True)
        self.form.set_value("telegram_alerts", False)
        self.form.set_value("risk_pct", 2.5)
        self.form.set_value("scan_progress", 0.45)
        self.form.set_value(
            "notes", "Observing resistance at 50 EMA. Bracket orders armed."
        )
        self.prog_bar.set(0.45)
        self.on_run()


if __name__ == "__main__":
    # Launch QuickApp with the modern CustomTkinter window shell!
    app = QuickApp(
        title="QuickTk + CustomTkinter Modern Showcase",
        size=(1020, 780),
        theme="Dark Obsidian",
        use_ctk=True,  # <-- Startup option: uses modern CustomTkinter shell!
    )
    app.set_single_tool(CustomTkinterShowcase)
    app.run()
