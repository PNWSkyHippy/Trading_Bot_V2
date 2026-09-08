"""
Futures Tick & Contract Calculator Tool
Demonstrates real-time slider controls, multi-variable financial math, and interactive DataTable targets.
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

# Futures specifications: Symbol -> (Tick Size, Tick Value $, Full Point Value $)
FUTURES_SPECS = {
    "ES (E-mini S&P 500)": {"tick_size": 0.25, "tick_value": 12.50, "point_value": 50.0},
    "MES (Micro E-mini S&P)": {"tick_size": 0.25, "tick_value": 1.25, "point_value": 5.0},
    "NQ (E-mini Nasdaq 100)": {"tick_size": 0.25, "tick_value": 5.00, "point_value": 20.0},
    "MNQ (Micro E-mini Nasdaq)": {"tick_size": 0.25, "tick_value": 0.50, "point_value": 2.0},
    "YM (E-mini Dow ($5))": {"tick_size": 1.0, "tick_value": 5.00, "point_value": 5.0},
    "MYM (Micro E-mini Dow)": {"tick_size": 1.0, "tick_value": 0.50, "point_value": 0.5},
    "MGC (Micro Gold)": {"tick_size": 0.1, "tick_value": 1.00, "point_value": 10.0},
    "GC (Gold)": {"tick_size": 0.10, "tick_value": 10.00, "point_value": 100.0},
    "RTY (E-mini Russell 2000)": {"tick_size": 0.10, "tick_value": 5.00, "point_value": 50.0},
    "M2K (Micro E-mini Russell)": {"tick_size": 0.10, "tick_value": 0.50, "point_value": 5.0},
}


class FuturesTickCalcTool(ToolView):
    title = "Futures Tick Calculator"
    description = "Calculate ticks, profit targets, stop loss risk, and contract sizing for futures instruments"

    def build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Controls Form
        self.form = self.add_form("Futures Configuration", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        symbols = list(FUTURES_SPECS.keys())
        self.form.add_dropdown("symbol", "Instrument / Future", symbols, default=symbols[0], on_change=self._recalculate)
        self.form.add_slider("contracts", "Number of Contracts", min_val=1, max_val=20, default=2, step=1, on_change=self._recalculate)
        self.form.add_slider("target_profit", "Target Win Amount ($)", min_val=50, max_val=5000, default=500, step=25, on_change=self._recalculate)
        self.form.add_slider("target_loss", "Max Stop Loss ($)", min_val=25, max_val=2500, default=250, step=25, on_change=self._recalculate)
        self.form.add_number("custom_ticks", "Manual Ticks (What-If)", default=16, min_val=1, max_val=500, step=1, on_change=self._recalculate)

        # 2. Right Side: Stat Grid + Target Matrix Table
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        self.stats = self.add_stat_grid(columns=4, parent=right_box)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.table = self.add_data_table(
            columns=["Target Ticks", "Index Points", "Per 1 Contract PnL", "Total PnL (Your Size)", "Win/Loss Multiple"],
            parent=right_box,
            enable_search=False,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")

        # Initial Calculation
        self._recalculate()

    def _recalculate(self, _=None):
        values = self.form.get_values()
        sym_name = values.get("symbol", list(FUTURES_SPECS.keys())[0])
        spec = FUTURES_SPECS.get(sym_name, list(FUTURES_SPECS.values())[0])

        contracts = max(1, int(values.get("contracts", 1)))
        desired_win = float(values.get("target_profit", 500))
        desired_loss = float(values.get("target_loss", 250))
        custom_ticks = int(values.get("custom_ticks", 16))

        tick_val = spec["tick_value"]
        tick_sz = spec["tick_size"]
        val_per_tick_total = tick_val * contracts

        # Ticks needed for target profit
        ticks_for_win = desired_win / val_per_tick_total if val_per_tick_total > 0 else 0
        points_for_win = ticks_for_win * tick_sz

        # Ticks for max loss
        ticks_for_loss = desired_loss / val_per_tick_total if val_per_tick_total > 0 else 0
        points_for_loss = ticks_for_loss * tick_sz

        # What if custom ticks
        custom_pnl = custom_ticks * val_per_tick_total

        # Risk reward
        rr_ratio = desired_win / desired_loss if desired_loss > 0 else 0

        # Update KPI Badges
        self.stats.set_metrics({
            "Ticks Needed for Win": (f"{ticks_for_win:.1f} ticks ({points_for_win:.2f} pts)", "success"),
            "Ticks Allowed for Stop": (f"{ticks_for_loss:.1f} ticks ({points_for_loss:.2f} pts)", "danger"),
            "Dollar / Tick Total": (f"${val_per_tick_total:,.2f}", "primary"),
            "Risk / Reward Ratio": (f"1 : {rr_ratio:.2f}", "success" if rr_ratio >= 2.0 else ("warning" if rr_ratio >= 1.0 else "danger")),
        })

        # Update Target Matrix Table
        tick_steps = [4, 8, 12, 16, 20, 30, 40, 50, 80, 100, custom_ticks]
        tick_steps = sorted(list(set(tick_steps)))

        rows = []
        for t in tick_steps:
            pts = t * tick_sz
            single_pnl = t * tick_val
            total_pnl = t * val_per_tick_total
            is_custom = " (Custom)" if t == custom_ticks else ""
            mult = f"{total_pnl / desired_win:.2f}x Target" if desired_win > 0 else "-"
            rows.append([
                f"{t} ticks{is_custom}",
                f"{pts:.2f} pts",
                f"${single_pnl:,.2f}",
                f"${total_pnl:,.2f}",
                mult
            ])

        self.table.set_data(rows)
        self.set_status(f"Live Updated for {sym_name} ({contracts} contracts)")


if __name__ == "__main__":
    app = QuickApp(title="Futures Tick & Sizing Calculator", size=(1020, 680))
    app.set_single_tool(FuturesTickCalcTool)
    app.run()
