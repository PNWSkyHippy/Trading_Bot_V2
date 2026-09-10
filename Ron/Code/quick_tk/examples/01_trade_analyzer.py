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

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)

from quick_tk import QuickApp, ToolView


def ensure_sample_database(db_path: str = "sample_trades.db") -> str:
    """Generates a realistic SQLite trade database if it doesn't already exist."""
    full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), db_path))
    conn = sqlite3.connect(full_path)
    cur = conn.cursor()
    """    cur.execute(
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT,
            symbol TEXT,
            asset_class TEXT,
            direction TEXT,
            status TEXT,
            entry_time TEXT,
            exit_time TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity INTEGER,
            position_value REAL,
            stop_loss REAL,
            take_profit REAL.
            pnl REAL,
            pnl_pct REAL,
            exit_reason TEXT,
            signal_score REAL,
             indicators_json TEXT,
            broker TEXT,
            strategy_name TEXT,
            is_overight BOOL,
            broker_order_id INTEGER,
            tp_hit_count INTEGER,
            stop_order_id INTEGER,
            tp_order_id INTEGER,
            entry_timeframe INTEGER,
            fees_paid REAL,
            mfe_pct REAL,
            mae_pct REAL,
            partial_pnl REAL,
            partial_fees_paid REAL,
            partial_exit_count REAL,
            event_id INTEGER
        )
    )
    """
    cur.execute("SELECT COUNT(*) FROM trades")
    if cur.fetchone()[0] == 0:
        symbols = ["ES", "MES", "NQ", "MNQ", "CL", "GC"]
        strategies = ["Breakout", "Mean Reversion", "Trend Scalp", "VWAP Bounce", "Opening Range"]
        start_dt = datetime(2026, 1, 1)

        trades = []
        for i in range(150):
            sym = random.choice(symbols)
            strat = random.choice(strategies)
            cnt = random.choice([1, 2, 4, 5, 10])
            dt = (start_dt + timedelta(days=random.randint(0, 180), hours=random.randint(9, 16), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
            win = random.random() < 0.62
            if win:
                pnl = round(random.uniform(50.0, 1250.0), 2)
                outcome = "WIN"
            else:
                pnl = round(random.uniform(-750.0, -25.0), 2)
                outcome = "LOSS"
            entry = round(random.uniform(2000, 5500), 2)
            exit_p = round(entry + (pnl / (cnt * 5)), 2)
            dur = random.randint(3, 180)
            trades.append((dt, sym, strat, cnt, entry, exit_p, pnl, outcome, dur))

        cur.executemany(
            INSERT INTO trades (trade_date, symbol, strategy, contracts, entry_price, exit_price, pnl, outcome, duration_mins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        , trades)
        conn.commit()
    conn.close()
    return full_path


class TradeAnalyzerTool(ToolView):
    title = "Trade Analyzer"
    description = "Query SQLite trades DB, filter strategies, compute metrics, and export reports"

    def build_ui(self):
        # Top-level horizontal split: Left Form (320px) / Right Results
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Form Panel
        sample_db = ensure_sample_database()
        self.form = self.add_form("Filter Criteria", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.form.add_file_picker("db_path", "SQLite Database", default=sample_db, mode="open", filetypes=[("SQLite DB", "*.db")])
        self.form.add_dropdown("strategy", "Strategy Filter", ["ALL", "Breakout", "Mean Reversion", "Trend Scalp", "VWAP Bounce", "Opening Range"], default="ALL")
        self.form.add_dropdown("symbol", "Symbol", ["ALL", "ES", "MES", "NQ", "MNQ", "CL", "GC"], default="ALL")
        self.form.add_number("min_pnl", "Minimum PnL ($)", default=-1000, min_val=-5000, max_val=10000, step=50, is_float=True)
        self.form.add_radio("outcome", "Trade Outcome", ["ALL", "WIN", "LOSS"], default="ALL")
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

        # Initial run
        self.on_analyze(self.form.get_values())

    def on_reset(self, _=None):
        self.form.clear()
        self.form.set_values({
            "strategy": "ALL",
            "symbol": "ALL",
            "outcome": "ALL",
            "min_pnl": -1000,
            "sort_by": "Date (Newest)",
        })
        self.on_analyze(self.form.get_values())

    def on_analyze(self, values: dict):
        """Fetches from SQLite database with applied filters and updates UI."""
        db_path = values.get("db_path", "")
        if not os.path.exists(db_path):
            self.set_status("Database file not found.")
            return

        def _query_worker():
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            query = "SELECT id, trade_date, symbol, strategy, contracts, pnl, outcome, duration_mins FROM trades WHERE 1=1"
            params = []

            if values.get("strategy") and values["strategy"] != "ALL":
                query += " AND strategy = ?"
                params.append(values["strategy"])

            if values.get("symbol") and values["symbol"] != "ALL":
                query += " AND symbol = ?"
                params.append(values["symbol"])

            if values.get("outcome") and values["outcome"] != "ALL":
                query += " AND outcome = ?"
                params.append(values["outcome"])

            min_pnl = values.get("min_pnl", -999999)
            query += " AND pnl >= ?"
            params.append(min_pnl)

            sort = values.get("sort_by", "Date (Newest)")
            if sort == "Date (Newest)":
                query += " ORDER BY trade_date DESC"
            elif sort == "PnL (Highest)":
                query += " ORDER BY pnl DESC"
            elif sort == "PnL (Lowest)":
                query += " ORDER BY pnl ASC"
            elif sort == "Duration":
                query += " ORDER BY duration_mins DESC"

            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()

            # Calculate metrics
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


if __name__ == "__main__":
    app = QuickApp(title="Trade Analyzer Utility", size=(1080, 700))
    app.set_single_tool(TradeAnalyzerTool)
    app.run()
