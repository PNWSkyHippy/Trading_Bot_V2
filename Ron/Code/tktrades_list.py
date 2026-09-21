"""
Trade Analyzer Tool - SQLite Trade Filtering and Reporting GUI
Demonstrates FormPanel, DataTable, StatGrid, and SQLite data integration.
"""

import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from quick_tk import QuickApp, ToolView
from quick_tk.core.forms import FormPanel
from typing import Any, cast
# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)
from local_functions import length_time ,hours_mins, update_tuple
from quick_tk import QuickApp, ToolView




class TradeAnalyzerTool(ToolView):  # pyright: ignore[reportGeneralTypeIssues]
    title = "Trade Analyzer"
    description = "Query SQLite trades DB, filter strategies, compute metrics, and export reports"

    def build_ui(self):
        
        self.db_path = 'c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db'
        self.debug_win: tk.Toplevel | None = None
        self.debug_console = None
        # Top-level horizontal split: Left Form (320px) / Right Results
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left 
        self.form = self.add_form("Filter Criteria", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.debug_var = self.form.add_checkbox("Debug", "Debug", default=False, on_change=self.open_debug_window)
        self.bind_all("<Control-d>", self.open_debug_window)
        self.form.add_file_picker("db_path", "SQLite Database", default='c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db', mode="open", filetypes=[("SQLite DB", "*.db")])
        self.form.add_dropdown("strategy", "Strategy Filter", ["ALL", "Breakout", "Mean Reversion", "Trend Scalp", "VWAP Bounce", "Opening Range"], default="ALL")
        self.form.add_dropdown("symbol", "Symbol", ["ALL", "ES", "MES", "NQ", "MNQ", "CL", "GC"], default="ALL")
        self.form.add_number("min_pnl", "Minimum PnL ($)", default=-1000, min_val=-5000, max_val=10000, step=50, is_float=True)
        self.form.add_radio("status", "Trade Outcome", ["ALL", "WIN", "LOSS"], default="ALL")
        self.form.add_dropdown("sort_by", "Sort Order", ["Date (Newest)", "PnL (Highest)", "PnL (Lowest)", "Duration"], default="Date (Newest)")

        self.form.add_button("Run Analysis", callback=self.on_analyze, variant="primary")
        self.form.add_button("Reset Filters", callback=self.on_reset, variant="default")

        # 2. Right Container: StatGrid + DataTable
        right_box = ttk.Frame(self, style="TFrame")
        right_box.grid(row=0, column=1, sticky="nsew")
        right_box.columnconfigure(0, weight=1)
        right_box.rowconfigure(0, weight=0)
        right_box.rowconfigure(1, weight=1)

        # Stat KPI Badges
        self.stats = self.add_stat_grid(columns=4, parent=right_box)
        self.stats.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Data Table
        self.table = self.add_data_table(
            columns=["ID", "Date/Time", "Symbol", "Strategy", "Contracts", "PnL ($)", "Outcome", "Duration (m)"],
            parent=right_box,
            enable_search=True,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")
#        self.open_debug_window(state=True)
        # Initial run
        self.on_analyze(self.form.get_values())

    def on_reset(self, _=None):
        self.form.clear()
        self.form.set_values({
            "strategy": "ALL",
            "symbol": "ALL",
            "status": "ALL",
            "min_pnl": -1000,
            "sort_by": "Date (Newest)",
        })
        self.on_analyze(self.form.get_values())

    def on_analyze(self, values: dict):
        """Fetches from SQLite database with applied filters and updates UI."""
        self.db_path = values.get("db_path", "")
        if self.debug_console is not None:
            self.debug_console.write(f"DB Path: {self.db_path}\n\n")
        if not os.path.exists(self.db_path):
            self.set_status("Database file not found.")
            if self.debug_console is not None:
                self.debug_console.write(f"File not found DB Path: {self.db_path}\n\n")
            return
        def _query_worker():
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            query = "SELECT id, entry_time, symbol, strategy_name, quantity, pnl, status, exit_time FROM trades WHERE 1=1"
            params = []
            
            if self.debug_console is not None:
                self.debug_console.write(f"In Query: query =  {query}\n\n")

            if values.get("strategy_name") and values["strategy_name"] != "ALL":
                query += " AND strategy_name = ?"
                params.append(values["strategy_name"])

            if values.get("symbol") and values["symbol"] != "ALL":
                query += " AND symbol = ?"
                params.append(values["symbol"])

            if values.get("status") and values["status"] != "ALL":
                query += " AND status = ?"
                params.append(values["status"])

            min_pnl = values.get("min_pnl", -999999)
            query += " AND pnl >= ?"
            params.append(min_pnl)

            sort = values.get("sort_by", "Date (Newest)")
            if sort == "Date (Newest)":
                query += " ORDER BY entry_time DESC"
            elif sort == "PnL (Highest)":
                query += " ORDER BY pnl DESC"
            elif sort == "PnL (Lowest)":
                query += " ORDER BY pnl ASC"
            elif sort == "Duration":
                query += " ORDER BY exit_time DESC"
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()
            cnt = 1
            tmins = 0
            # Calculate metrics
            for i in range(0,len(rows)):
                days, hours, mins, seconds = length_time(rows[i][1], rows[i][7])
                hours,mins = hours_mins(days, hours, mins, seconds)
#                temp = list(rows[i])
#                temp[7] = f'{hours}h:{mins}'
                # Convert back to tuple
                rows[i]= update_tuple(rows[i], 7,f'{hours}h:{mins}' )
            total_trades = len(rows)
            if total_trades > 0:
                pnls = [r[5] for r in rows]
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p <= 0]
                total_pnl = sum(pnls)
                win_rate = (len(wins) / total_trades) * 100
                biggest_win = max(pnls) if pnls else 0
                biggest_loss = min(pnls) if pnls else 0
                gross_win = sum(wins) if wins else 0
                gross_loss = abs(sum(losses)) if losses else 0
                profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 99.9
            else:
                total_pnl = win_rate = biggest_win = biggest_loss = profit_factor = 0

            return {
                "rows": rows,
                "metrics": {
                    "Total PnL": (f"${total_pnl:,.2f}", "success" if total_pnl >= 0 else "danger"),
                    "Win Rate": (f"{win_rate:.1f}%", "success" if win_rate >= 50 else "warning"),
                    "Profit Factor": (f"{profit_factor:.2f}", "success" if profit_factor >= 1.5 else "info"),
                    "Biggest Win": (f"${biggest_win:,.2f}", "success"),
                    "Biggest Loss": (f"${biggest_loss:,.2f}", "danger"),
                    "Total Trades": (f"{total_trades}", "info"),
                }
            }

        def _on_done(res):
            self.stats.set_metrics(res["metrics"])
            # Format row data
            formatted_rows = [
                [r[0], r[1], r[2], r[3], r[4], f"${r[5]:,.2f}", r[6], f"{r[7]}m"]
                for r in res["rows"]
            ]
            self.table.set_data(formatted_rows)
            self.set_status(f"Loaded {len(formatted_rows)} trades.")

        # Run via async task runner so large DB queries never lock UI
        self.run_async(_query_worker, on_done=_on_done, status_msg="Querying SQLite Database...")

    def close_debug_window(self):
        if self.debug_win is not None:
            self.debug_win.destroy()

        self.debug_win = None
        self.debug_console = None
        self.debug_var.set(False)
        
    def open_debug_window(self, state=None):
        win = self.debug_win

        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()
            if state == False:
                self.close_debug_window()
            return


        win = tk.Toplevel(self.app.root)
        win.title("Debug Data")
        win.geometry("520x520")
        self.debug_win = win
        win.protocol("WM_DELETE_WINDOW", self.close_debug_window)
        # This is a text console, not a form/input panel.
        self.debug_console = self.add_console(
            "Trades  List Tracer Debug Data",
            parent=cast(tk.Widget, win),
        )
        self.debug_console.pack(fill="both", expand=True, padx=8, pady=8)

        # Avoid holding references to widgets after the user closes the window.
        win.protocol("WM_DELETE_WINDOW", self.close_debug_window)
    
if __name__ == "__main__":
    app = QuickApp(title="Trade Analyzer Utility", size=(1080, 700))
    app.set_single_tool(TradeAnalyzerTool)
    app.run()
