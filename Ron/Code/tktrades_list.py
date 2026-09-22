"""
Trade Analyzer Tool - SQLite Trade Filtering and Reporting GUI
Demonstrates FormPanel, DataTable, StatGrid, and SQLite data integration.
"""

import os
import sqlite3
import sys
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import cast

from quick_tk import QuickApp, ToolView

# Add parent directory and scratch root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRATCH_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, SCRATCH_DIR)
sys.path.insert(0, BASE_DIR)
import argparse
import copy
import csv
import re

from tkcalendar import DateEntry

from local_functions import (
    STAT_LABEL_VALUE_RE,
    Timed,
    chkstr_isnum,
    clean_ansi,
    colorize,
    date_check,
    hours_mins,
    length_time,
    update_tuple,
)


class TradeAnalyzerTool(ToolView):  # pyright: ignore[reportGeneralTypeIssues]
    title = "Trade Analyzer"
    description = (
        "Query SQLite trades DB, filter strategies, compute metrics, and export reports"
    )

    def build_ui(self):
        self.trades_list, self.main_values = self.main_loop()
        #        sys.stderr.write(f"{self.main_values.keys()}\n\n")
        #        sys.stderr.flush()
        self.rows = []
        self.key_list = []
        self.key_list1 = []
        self.key_list2 = []
        self.key_list3 = []
        self.key_list4 = []
        self.key_list5 = []
        self.db_path_var = "c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db"
        #        self.db_path.set('c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db')
        self.db_path = ""
        self.debug_win: tk.Toplevel | None = None
        self.debug_console = None
        # Top-level horizontal split: Left Form (320px) / Right Results
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left
        self.form = self.add_form("Filter Criteria", parent=self)
        self.form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.db_path_var = self.form.add_file_picker(
            "db_path",
            "SQLite Database",
            default="c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db",
            mode="open",
            filetypes=[("SQLite DB", "*.db")],
        )
        self.key_list = self.main_values["hdr_list"]

        self.start_date_entry = self.form.add_custom_widget(
            name="start_date",
            label="Start Date",
            widget_factory=lambda parent: DateEntry(
                parent,
                width=12,
                date_pattern="yyyy-mm-dd",
            ),
            get_value_fn=lambda widget: datetime.combine(
                widget.get_date(),
                datetime.min.time(),
            ).isoformat(timespec="microseconds"),
            set_value_fn=lambda widget, value: widget.set_date(
                datetime.fromisoformat(value).date()
                if isinstance(value, str)
                else value
            ),
        )

        self.end_date_entry = self.form.add_custom_widget(
            name="end_date",
            label="End Date",
            widget_factory=lambda parent: DateEntry(
                parent,
                width=12,
                date_pattern="yyyy-mm-dd",
            ),
            get_value_fn=lambda widget: datetime.combine(
                widget.get_date(),
                datetime.max.time(),
            ).isoformat(timespec="microseconds"),
            set_value_fn=lambda widget, value: widget.set_date(
                datetime.fromisoformat(value).date()
                if isinstance(value, str)
                else value
            ),
        )

        self.keys_id = self.form.add_multi_select(
            name="keys",
            label="Search Keys (Max 5)",
            options=self.key_list,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )
        self.list1_id = self.form.add_multi_select(
            name="list1",
            label="Search Keys 1 values",
            options=self.key_list1,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )
        self.list2_id = self.form.add_multi_select(
            name="list2",
            label="Search Keyss 2 values",
            options=self.key_list2,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )
        self.list3_id = self.form.add_multi_select(
            name="keys3",
            label="Search Keys 3 values",
            options=self.key_list3,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )
        self.list4_id = self.form.add_multi_select(
            name="list4",
            label="Search Keys 4 values",
            options=self.key_list4,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )
        self.list5_id = self.form.add_multi_select(
            name="list5",
            label="Search Keys 5 values",
            options=self.key_list5,
            default=["strategy_name"],
            placeholder="Select keys...",
            max_display=3,
        )

        self.form.add_dropdown(
            "sort_by",
            "Sort Order",
            ["Date (Newest)", "PnL (Highest)", "PnL (Lowest)", "Duration"],
            default="Date (Newest)",
        )

        self.form.add_button(
            "Run Analysis", callback=self.on_analyze, variant="primary"
        )
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
        self.setup_menus()
        # Data Table
        self.table = self.add_data_table(
            columns=[
                "ID",
                "Date/Time",
                "Symbol",
                "Strategy",
                "Contracts",
                "PnL ($)",
                "Outcome",
                "Duration (m)",
            ],
            parent=right_box,
            enable_search=True,
            enable_export_csv=True,
        )
        self.table.grid(row=1, column=0, sticky="nsew")
        # Initial run
        self.on_analyze(self.form.get_values())

    def setup_menus(self):
        # 1. FILE MENU (Fluent Chained Style)
        file_menu = self.menu("File")
        file_menu.add_command(
            label="Save Report to 💾 <Ctrl-s>", command=self.on_save_report
        )
        self.bind_all("<Control-s>", self.on_save_report)

        file_menu.add_separator()
        file_menu.add_item("Exit Application <Alt-F4>", command=self.app.root.quit)
        self.bind_all("<Alt-F4>", lambda _event: self.app.root.quit())
        self.bind_all("<Control-p>", lambda _event: self.app.root.quit())
        # 3. VIEW MENU (With Toggle Checkboxes and Radio Groups)
        view_menu = self.menu("View")
        self.debug_var = view_menu.add_toggle(
            "Debug", default=False, on_toggle=self.open_debug_window
        )
        self.bind_all("<Control-d>", self.open_debug_window)
        self.rev_sort = view_menu.add_toggle(
            "Rev Sort", default=False, on_toggle=self.open_sort_reverse
        )
        self.ext_id = view_menu.add_toggle(
            "Extended ID", default=False, on_toggle=self.open_ext_id
        )
        self.and_res = view_menu.add_toggle(
            "AND results", default=False, on_toggle=self.open_and_results
        )
        self.csv_out = view_menu.add_toggle(
            "CSV Output", default=False, on_toggle=self.open_csv_results
        )

    def on_reset(self, _=None):
        self.form.clear()
        self.form.set_values(
            {
                "strategy": "ALL",
                "symbol": "ALL",
                "status": "ALL",
                "min_pnl": -1000,
                "sort_by": "Date (Newest)",
            }
        )
        self.on_analyze(self.form.get_values())

    def on_analyze(self, values: dict):
        """Fetch from SQLite with the form filters and update the UI."""
        if self.debug_console is not None:
            self.debug_console.write(
                f"StartDate: {values.get('start_date', 'None')} - End Date: {values.get('end_date', 'None')}\n\n"
            )
        self.db_path = values.get("db_path_var", "")
        self.db_path = "c:/Users/Linda/Trading_Bot_v2/data/trading_bot.db"
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
            # Calculate metrics
            tot_mins = 0
            for i in range(len(rows)):
                # for each row replace duration column with xxh:yym
                days, hours, mins, seconds = length_time(rows[i][1], rows[i][7])
                hours, mins = hours_mins(days, hours, mins, seconds)
                # Convert back to tuple
                rows[i] = update_tuple(rows[i], 7, f"{hours}h:{mins}")
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
                "query": query,
                "params": params,
                "metrics": {
                    "Total PnL": (
                        f"${total_pnl:,.2f}",
                        "success" if total_pnl >= 0 else "danger",
                    ),
                    "Win Rate": (
                        f"{win_rate:.1f}%",
                        "success" if win_rate >= 50 else "warning",
                    ),
                    "Profit Factor": (
                        f"{profit_factor:.2f}",
                        "success" if profit_factor >= 1.5 else "info",
                    ),
                    "Biggest Win": (f"${biggest_win:,.2f}", "success"),
                    "Biggest Loss": (f"${biggest_loss:,.2f}", "danger"),
                    "Total Trades": (f"{total_trades}", "info"),
                },
            }

        def _on_done(res):
            self.rows = res["rows"]
            if self.debug_console is not None:
                self.debug_console.write(f"Query: {res['query']}\n")
                self.debug_console.write(f"Parameters: {res['params']}\n")
            self.stats.set_metrics(res["metrics"])
            # Format row data
            formatted_rows = [
                [r[0], r[1], r[2], r[3], r[4], f"${r[5]:,.2f}", r[6], f"{r[7]}m"]
                for r in res["rows"]
            ]
            self.table.set_data(formatted_rows)
            self.set_status(f"Loaded {len(formatted_rows)} trades.")
            if self.debug_console is not None:
                self.debug_console.write(f"Loaded {len(formatted_rows)} trades.\n\n")

        def _on_error(error):
            self.set_status("Analysis failed.")
            if self.debug_console is not None:
                self.debug_console.write(f"Analysis failed: {error}\n\n")

        # Run via async task runner so large DB queries never lock UI
        self.run_async(
            _query_worker,
            on_done=_on_done,
            on_error=_on_error,
            status_msg="Querying SQLite Database...",
        )

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
            if state is False:
                self.close_debug_window()
            return

        win = tk.Toplevel(self.app.root)
        win.title("Debug Data")
        win.geometry("520x520")
        self.debug_win = win

        self.debug_console = self.add_console(
            "Trades List Tracer Debug Data",
            parent=cast(tk.Widget, win),
        )
        self.debug_console.pack(fill="both", expand=True, padx=8, pady=8)
        win.protocol("WM_DELETE_WINDOW", self.close_debug_window)

    def open_sort_reverse(self, state=None):
        pass

    def open_ext_id(self, state=None):
        pass

    def open_and_results(self, state=None):
        pass

    def open_csv_results(self, state=None):
        pass

    def on_save_report(self, state=None):
        pass

    def main_loop(self):
        tot_mins_list = []
        # Standard library approach to handle Windows initialization safely
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            stdout_handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE

            console_mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(stdout_handle, ctypes.byref(console_mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(
                    stdout_handle,
                    console_mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                )

        DEF_OUTFIELDS = {
            "trade_id": "ID",
            "entry_time": "Entry",
            "exit_time": "Exit",
            "symbol": "Symbol",
            "direction": "Direct",
            "entry_price": "EntryPrice",
            "exit_price": "ExitPrice",
            "pnl": "PNL",
        }

        ALL_OUTFIELDS = {
            "trade_id": "ID",
            "symbol": "Symbol",
            "asset_class": "Asset",
            "direction": "Direct",
            "status": "Status",
            "entry_time": "EntryTime",
            "exit_time": "ExitTime",
            "entry_price": "EntryPrice",
            "exit_price": "ExitPrice",
            "quantity": "Quantity",
            "position_value": "PosVal",
            "stop_loss": "topLoss",
            "take_profit": "TakeProf",
            "pnl": "PnL",
            "pnl_pct": "PnLPct",
            "exit_reason": "ExitReas",
            "signal_score": "SigScore",
            "indicators_json": "IndJSON",
            "broker": "Broker",
            "strategy_name": "Strat",
            "is_overnight": "OverNite",
            "broker_order_id": "BrokerID",
            "tp_hit_count": "TPHitCnt",
            "stop_order_id": "StopID",
            "tp_order_id": "TPId",
            "entry_timeframe": "EnterTFrm",
            "fees_paid": "FeesPd",
            "mfe_pct": "MfePct",
            "mae_pct": "MaePct",
            "partial_pnl": "PartPnL",
            "partial_fees_paid": "ParFeePd",
            "partial_exit_count": "ParExtCnt",
            "event_id": "EventId",
        }

        output_file = ""
        is_sorted = False
        default_key_list = [
            "strategy_name",
            "symbol",
            "exit_reason",
            "quantity",
            "broker_order_id",
        ]
        # Connect to DB and load the trades table into the trades_list dictionary

        def wide_formatter(prog):
            return argparse.RawDescriptionHelpFormatter(
                prog,
                width=110,
                max_help_position=46,
            )

        parser = argparse.ArgumentParser(
            description="List PnL based on search criteria",
            epilog="""\
Usage examples:
  trades_list.py -k strategy_name -1 emt
  trades_list.py -k strategy_name,symbol -1 emt -2 ESU6
  trades_list.py -k entry_price -1 ">=40000"
  trades_list.py -k strategy_name -1 ALL -o report.txt
  trades_list.py -N
""",
            formatter_class=wide_formatter,
        )

        parser.add_argument(
            "-o",
            "--outfile",
            metavar="",
            help="\tpath and name of output file",
        )
        parser.add_argument(
            "-op",
            "--open",
            action="store_true",
            help="List open trades instead of closed",
        )
        parser.add_argument(
            "-csv",
            "--csv",
            action="store_true",
            help="\tuse to have output file be a csv",
        )

        parser.add_argument(
            "-1",
            "--list1",
            metavar="",
            help="ALL or comma-separated values for the first key; numeric values also accept !=, <, >,"
            "<=, >= (quote these in PowerShell)",
        )
        parser.add_argument(
            "-2",
            "--list2",
            metavar="",
            help="ALL or a <Comma separated list of values found in second provided key>",
        )
        parser.add_argument(
            "-3",
            "--list3",
            metavar="",
            help="ALL or a <Comma separated list of values found in third provided key>",
        )
        parser.add_argument(
            "-4",
            "--list4",
            metavar="",
            help="ALL or a <Comma separated list of values found in fourth provided key>",
        )
        parser.add_argument(
            "-5",
            "--list5",
            metavar="",
            help="ALL or a <Comma separated list of values found in fifth provided key>",
        )
        parser.add_argument(
            "-s",
            "--start",
            metavar="",
            help="Starting date and time. Format YYYY:MM:DDTHH:MM T being a literal T",
        )
        parser.add_argument(
            "-e",
            "--end",
            metavar="",
            help="Ending date and time. Format YYYY:MM:DDTHH:MM T being a literal T",
        )
        parser.add_argument(
            "-k",
            "--key",
            metavar="",
            help="ALL or a <Comma separated list of DB table keys to index and search>",
        )
        parser.add_argument(
            "-of",
            "--outfields",
            metavar="",
            help="ALL or a <Comma separated list of DB table output fields to display",
        )
        parser.add_argument(
            "-sk",
            "--sort-keys",
            metavar="",
            help="<Comma separated list of DB table keys to sort results. one entry per key from -k>",
        )
        parser.add_argument(
            "-R",
            "--Reverse",
            action="store_true",
            help="If given, sort order is reversed",
        )
        parser.add_argument(
            "-N",
            "--Names",
            action="store_true",
            help="If given, prints a list of all trade table key names you can use",
        )
        parser.add_argument(
            "-A",
            "--and",
            dest="and_filter",
            action="store_true",
            help="If given with multiple --key values, require trades to match ALL selected key/value "
            "filters at once (e.g. symbol=MSFT AND direction=long) instead of printing a separate breakdown per key",
        )
        parser.add_argument(
            "-E",
            "--Ext",
            action="store_true",
            help="Exxtended Trade Id , default is shortened Id (Useful when you need the full trade Id for a lookup)",
        )

        args = parser.parse_args()
        global csv_true
        global extended

        csv_true = args.csv if args.csv else False
        extended = args.Ext if args.Ext else False

        mode = "open" if args.open else "closed"
        is_sorted = args.sort_keys if args.sort_keys else False
        rev_sort = args.Reverse if args.Reverse else False

        conn = connect()
        if mode == "closed":
            try:
                trades_list = get_closed_trades(conn)
                conn.close()
            except sqlite3.OperationalError as e:
                print(f"Database error: {e}")
                conn.close()
                sys.exit(1)
        else:
            try:
                trades_list = get_open_trades(conn)
                conn.close()
            except sqlite3.OperationalError as e:
                print(f"Database error: {e}")
                conn.close()
                sys.exit(1)

        if not trades_list:
            print("No closed trades found.") if (mode == "closed") else print(
                "No open trades found."
            )

            conn.close()
            return

        hdr_list = build_hdr_list(trades_list)

        if args.Names:
            print_col_headers(trades_list)
            sys.exit(2)
        DEF_START_DATE = "1980-01-01T00:00"
        DEF_END_DATE = "4050-01-01T00:00"

        start_date = args.start if args.start else DEF_START_DATE
        end_date = args.end if args.end else DEF_END_DATE

        if args.start and (not date_check(start_date)):
            print("Invalid start date. use format YYYY-MM-DDTHH:MM")
            sys.exit(4)

        if args.end and (not date_check(end_date)):
            print("Invalid end date. use format YYYY-MM-DDTHH:MM")
            sys.exit(4)

        date_range_given = start_date != DEF_START_DATE or end_date != DEF_END_DATE

        output_file = args.outfile
        if csv_true:
            try:
                output_file, extension = output_file.split(".")
            except:
                pass

        # Build a list of list options skipping those not given
        list_values = [
            args.list1.split(",") if args.list1 else [],
            args.list2.split(",") if args.list2 else [],
            args.list3.split(",") if args.list3 else [],
            args.list4.split(",") if args.list4 else [],
            args.list5.split(",") if args.list5 else [],
        ]

        key_list = args.key.split(",") if args.key else []

        if len(key_list) > 5:
            print("\nError: maximum of 5 keys is supported.\n")
            sys.exit(1)

        output_fields = args.outfields.split(",") if args.outfields else False

        output_dict = {}
        if not output_fields:
            output_dict = DEF_OUTFIELDS
        else:
            for outpt in output_fields:
                if outpt not in hdr_list:
                    print(
                        f"\nError: {outpt} is not a valid entry. please run with -N to see a list of valid choices\n"
                    )
                    sys.exit()
            for fields in output_fields:
                for key_name, descr in ALL_OUTFIELDS.items():
                    if key_name == fields:
                        output_dict[key_name] = descr
                        continue

        sort_list = args.sort_keys.split(",") if args.sort_keys else []

        if len(sort_list) > 5:
            print("\nError: maximum of 5 sort keys is supported.\n")
            sys.exit(1)
        # Verify every key value input is valid
        if date_range_given and (not any(list_values)):
            for j in range(5):
                list_values[j].append("ALL")

        if date_range_given and len(key_list) < 1:
            key_list = default_key_list

        if ((not len(list_values)) or (not len(key_list))) and (not date_range_given):
            parser.print_help()
            parser.exit(
                2,
                "\nError: provide --key key1,key2,... and at least one --list option per key given.\n",
            )

        for key_name in key_list:
            if key_name not in hdr_list:
                print(
                    f"\nError: {key_name} is not a valid entry. please run with -N to see a list of valid choices\n"
                )
                sys.exit()

        for sort_name in sort_list:
            if sort_name not in hdr_list:
                print(
                    f"\nError: {sort_name} is not a valid entry. please run with -N to see a list of valid choices\n"
                )
                sys.exit()
        ttrades_list = []
        for i in range(len(key_list)):
            ttrades_list.append(copy.deepcopy(trades_list))
        if is_sorted:
            for i in range(min(len(key_list), len(sort_list))):
                for trade in ttrades_list[i]:
                    try:
                        if chkstr_isnum(trade[sort_list[i]]) == "float":
                            trade[sort_list[i]] = float(trade[sort_list[i]])
                        elif chkstr_isnum(trade[sort_list[i]]) == "int":
                            trade[sort_list[i]] = int(trade[sort_list[i]])
                    except ValueError:
                        pass
                try:
                    if rev_sort:
                        ttrades_list[i].sort(
                            key=lambda r: (
                                isinstance(r[sort_list[i]], str),
                                r[sort_list[i]],
                            ),
                            reverse=True,
                        )
                    else:
                        ttrades_list[i].sort(
                            key=lambda r: (
                                isinstance(r[sort_list[i]], str),
                                r[sort_list[i]],
                            ),
                            reverse=False,
                        )
                except ValueError:
                    None

        if (not args.Names) and (len(key_list) < 1):
            print("\nError: Please provide at least 1 key , separated by a ,   \n")
            sys.exit()

        # -A/--and: one combined report where a trade must match every selected
        # key/value filter at once (symbol=MSFT AND direction=long), instead of
        # the default independent per-key breakdown below.
        for trade in trades_list:
            # for each row replace duration column with xxh:yym
            days, hours, mins, seconds = length_time(
                trade["entry_time"], trade["exit_time"]
            )
            hours, mins = hours_mins(days, hours, mins, seconds)
            tot_mins_list.append((hours * 60) + mins)
            trade["tot_mins"] = (hours * 60) + mins
            # Convert back to tuple
        if args.and_filter and len(key_list) > 1:
            combined_list = []
            for trade in trades_list:
                matches_all = True
                for key_name, selected in zip(key_list, list_values):
                    if not selected:
                        continue
                    if selected[0] == "ALL":
                        continue
                    if not value_in_selected(trade[key_name], selected):
                        matches_all = False
                        break
                if matches_all:
                    combined_list.append(copy.deepcopy(trade))

            if is_sorted:
                for sort_key in reversed(sort_list):
                    for trade in combined_list:
                        try:
                            if chkstr_isnum(trade[sort_key]) == "float":
                                trade[sort_key] = float(trade[sort_key])
                            elif chkstr_isnum(trade[sort_key]) == "int":
                                trade[sort_key] = int(trade[sort_key])
                        except ValueError:
                            pass
                    try:
                        combined_list.sort(
                            key=lambda r: (isinstance(r[sort_key], str), r[sort_key]),
                            reverse=rev_sort,
                        )
                    except ValueError:
                        None

            label_parts = [
                f"{key_name}={','.join(selected)}"
                for key_name, selected in zip(key_list, list_values)
                if selected
            ]
            combined_label = " & ".join(label_parts) if label_parts else "ALL"
            print_group_summary(
                combined_label,
                combined_list,
                "ALL",
                output_file,
                start_date,
                end_date,
                output_dict,
            )
            return

        # Build one generic list of grouped trade dictionaries
        dict_of_trades = []

        for idx, key_name in enumerate(key_list):
            grouped_trades = {}
            for trade in ttrades_list[idx]:
                group_value = trade[key_name]
                grouped_trades.setdefault(group_value, []).append(copy.deepcopy(trade))

            dict_of_trades.append(
                {
                    "key": key_name,
                    "selected": (list_values[idx] if idx < len(list_values) else []),
                    "groups": grouped_trades,
                }
            )

        for trade_group in dict_of_trades:
            key_name = trade_group["key"]
            selected_values = trade_group["selected"]
            grouped_trades = trade_group["groups"]

            for (
                group_name,
                trade_list,
            ) in grouped_trades.items():
                if not selected_values:
                    continue

                if selected_values[0] == "ALL" or value_in_selected(
                    group_name, selected_values
                ):
                    print_group_summary(
                        group_name,
                        trade_list,
                        key_name,
                        output_file,
                        start_date,
                        end_date,
                        output_dict,
                    )

        main_values = {
            "dict_of_ttrades": dict_of_trades,
            "selected_values": selected_values,
            "output_file": output_file,
            "is_sorted": is_sorted,
            "dict_of_trades": dict_of_trades,
            "DEF_OUTFIELDS": DEF_OUTFIELDS,
            "ALL_OUTFIELDS": ALL_OUTFIELDS,
            "sort_list": sort_list,
            "output_dict": output_dict,
            "output_fields": output_fields,
            "output_file": output_file,
            "is_sorted": is_sorted,
            "default_key_list": default_key_list,
            "csv_true": csv_true,
            "extended": extended,
            "args": args,
            "is_sorted": is_sorted,
            "rev_sort": rev_sort,
            "mode": mode,
            "hdr_list": hdr_list,
            "Names": args.Names,
            "start_date": start_date,
            "end_date": end_date,
            "date_range_given": date_range_given,
            "output_file": output_file,
            "list_values": list_values,
            "key_list": key_list,
            "tot_mins_list": tot_mins_list,
        }

        return (trades_list, main_values)


extended = False
csv_true = False

EQUALSTR = "=" * 175 + "\n"
BL_EQUALSTR = colorize(EQUALSTR, "blue")
# Find path to the trading bot DB
if os.name == "nt":
    DB_PATH = os.path.join(
        os.path.dirname(__file__),
        "..\\..",
        "data",
        "trading_bot.db",
    )
else:
    DB_PATH = os.path.join(
        os.path.dirname(__file__),
        "../..",
        "data",
        "trading_bot.db",
    )
# End Globals


def print_outfile(text, output_file):
    """
    Print to Stdout or file name provided. Backwards compatible wrapper.
    If output_file is provided, text is appended to that file.
    Otherwise text is printed to stdout.
    """
    if output_file:
        clean_text = clean_ansi(text)
        try:
            if csv_true:
                with open(
                    output_file + ".csv",
                    "a",
                    newline="",
                ) as csvfile:
                    spamwriter = csv.writer(
                        csvfile,
                        delimiter=",",
                        quotechar=" ",
                        quoting=csv.QUOTE_MINIMAL,
                    )
                    for line in clean_text.splitlines():
                        stripped = line.strip()
                        if not stripped or set(stripped) == {"="}:
                            spamwriter.writerow([])
                        elif stripped.count(":") >= 2:
                            # summary lines like "Total Trades: 54   Total P&L: -1320.00 ..."
                            pairs = STAT_LABEL_VALUE_RE.findall(stripped)
                            row = [
                                part.strip()
                                for label, value in pairs
                                for part in (
                                    label,
                                    value,
                                )
                            ]
                            spamwriter.writerow(row or stripped.split())
                        else:
                            spamwriter.writerow(stripped.split())
            else:
                with open(
                    output_file,
                    "a",
                    encoding="utf-8",
                ) as file:
                    file.write(clean_text)
        except OSError as e:
            print(f"Error writing to output file: {e}")
            sys.exit(1)
    else:
        print(text, end="")


def connect():
    """Open  up the database or quit if cant"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT 1 FROM trades LIMIT 1")
    except sqlite3.OperationalError as e:
        print(f"Database error: {DB_PATH}: {e}")
        sys.exit()
    return conn


def get_closed_trades(conn):
    """Read from he database using SQL"""
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC",
        ("closed",),
    )
    return [dict(r) for r in c.fetchall()]


def get_open_trades(conn):
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC",
        ("open",),
    )
    return [dict(r) for r in c.fetchall()]


@Timed
def proc_dict(
    loc_trade_list, strat_name, ikey, output_file, start_date, end_date, output_dict
):
    """Process the provided dictionary of trades"""
    # Initialize Locals
    col_pnl = ""
    total_pnl = 0
    tot_winners = 0
    tot_losers = 0
    trade_count = -1
    tot_wins = 0.0
    tot_losses = 0.0
    max_win = 0.0
    max_loss = 0.0
    avg_wins = 0.0
    passes = 1
    avg_loss = 1000000000.0
    # One entry per symbol processed by this proc_dict call:
    # {"AAPL": 12.50, "MSFT": -3.25, ...}
    sym_total_pnl = {}
    field_lens = {}
    # Search the dict for Key  provided
    trade_count = 0
    tot_fees = 0
    for trade in loc_trade_list:
        t_sli = 38 if extended else 20
        t_idx = -len(trade["trade_id"]) if extended else -16
        #       for my_idx, my_key in trade.items():
        #           field_lens[my_idx] =  len(str(my_key)) + 4
        break  # only look at one record
    for trade_dict in loc_trade_list:
        entry_time = trade_dict["entry_time"] or ""
        exit_time = trade_dict["exit_time"] or ""
        if entry_time[0:16] >= start_date and exit_time[0:16] <= end_date:
            if (
                ikey == "ALL"
                or trade_dict.get(ikey, "None") == strat_name
                or strat_name == "ALL"
            ):
                tot_fees += trade_dict["fees_paid"]
                symbol = trade_dict["symbol"]
                trade_pnl = float(trade_dict["pnl"] or 0.0)
                sym_total_pnl[symbol] = sym_total_pnl.get(symbol, 0.0) + trade_pnl
                #  entry contains strat were after total the PnL
                total_pnl += trade_pnl
                # Running total the number of wins or losses and trace the total of each
                if trade_pnl >= 0:
                    tot_winners += 1
                    tot_wins += trade_pnl
                else:
                    tot_losers += 1
                    tot_losses += trade_pnl
                # Track the biggst win and biggest loss
                if max_win < trade_pnl:
                    max_win = trade_pnl
                if max_loss > trade_pnl:
                    max_loss = trade_pnl
                # Track the number of trades processed
                trade_count += 1
                if trade_pnl < 0:
                    col_pnl = colorize(
                        f"{trade_pnl:<20.2f}",
                        "red",
                    )
                else:
                    col_pnl = colorize(
                        f"{trade_pnl:<20.2f}",
                        "green",
                    )

                head_str = ""
                tail_str = ""
                for key, idx in output_dict.items():
                    #                   key_len = field_lens[key]
                    if key == "trade_id" and extended:
                        head_str += f"{key[t_idx:]:<{t_sli}}"
                    elif key == "exit_reason":
                        head_str += f"{key:<27}"
                    else:
                        head_str += f"{key:<20}"
                    if key == "trade_id":
                        tail_str += f"{trade_dict[key][t_idx:]:{t_sli}}"
                    elif key == "exit_reason":
                        tail_str += f"{trade_dict[key]:<27}"
                    elif key == "entry_time" or key == "exit_time":
                        tail_str += f"{trade_dict[key][0:16]:<20}"
                    elif chkstr_isnum(trade_dict[key]) == "float":
                        if float(trade_dict[key]) >= 0:
                            stii = float(trade_dict[key])
                            stii2 = colorize(f"{stii:<20.6f}", "green")
                            tail_str += f"{stii2}"
                        else:
                            stii = float(trade_dict[key])
                            stii2 = colorize(f"{stii:<20.6f}", "red")
                            tail_str += f"{stii2}"
                    #                             tail_str += f'{colorize({float(trade_dict[key]):<20.6f}}, "red")'
                    else:
                        tail_str += f"{trade_dict[key]:<20}"
                head_str += "\n"
                tail_str += "\n"

                if passes == 1:
                    print_outfile(
                        f"List of {colorize(strat_name, 'red')} Trades\n",
                        output_file,
                    )
                    print_outfile(BL_EQUALSTR, output_file)
                    print_outfile(
                        colorize(f"{head_str}", "magenta"),
                        output_file,
                    )
                    print_outfile(BL_EQUALSTR, output_file)
                    passes += 1

                print_outfile(tail_str, output_file)

    # Select the best and worst complete symbol totals after every matching
    # trade has been accumulated. This also works when every symbol is a loss
    # or every symbol is a profit, without relying on sentinel values.
    # Print  Tttle , header graphics and column headers

    if sym_total_pnl:
        high_symbol, high_total = max(
            sym_total_pnl.items(),
            key=lambda item: item[1],
        )
        low_symbol, low_total = min(
            sym_total_pnl.items(),
            key=lambda item: item[1],
        )
        high_sym = {
            "symbol": high_symbol,
            "total": high_total,
        }
        low_sym = {
            "symbol": low_symbol,
            "total": low_total,
        }
    else:
        high_sym = {
            "symbol": "None",
            "total": 0.0,
        }
        low_sym = {"symbol": "None", "total": 0.0}

    # Prevent div by zero excetions then calculate avg wins and losses
    if tot_winners == 0:
        avg_wins = -1
    else:
        avg_wins = tot_wins / tot_winners
    if tot_losers == 0:
        avg_loss = -1
    else:
        avg_loss = tot_losses / tot_losers
    if trade_count == 0:
        trade_count = -1
    # Prepare our return dictionary of results
    ret_dict = {}
    ret_dict["loss_pct"] = colorize(
        f"{(tot_losers / trade_count) * 100:.0f}",
        "red",
    )
    ret_dict["win_pct"] = colorize(
        f"{(tot_winners / trade_count) * 100:>3.0f}",
        "green",
    )
    ret_dict["trade_count"] = f"{trade_count:<14}"

    # Properly color the Tot PnL red for neg, green for pos
    if total_pnl >= 0:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<19.2f}", "green")
    else:
        ret_dict["total_pnl"] = colorize(f"{total_pnl:<19.2f}", "red")

    ret_dict["max_win"] = colorize(f"{max_win:<14.2f}", "green")
    ret_dict["max_loss"] = colorize(f"{max_loss:>3.2f}", "red")
    ret_dict["avg_wins"] = colorize(f"{avg_wins:<14.2f}", "green")
    ret_dict["avg_loss"] = colorize(f"{avg_loss:<19.2f}", "red")
    ret_dict["tot_wins"] = colorize(f"{tot_winners:>3}", "green")
    ret_dict["tot_losers"] = colorize(f"{tot_losers:<11}", "red")
    ret_dict["tot_fees"] = colorize(f"{tot_fees:<9.2f}", "red")
    ret_dict["high_sym"] = high_sym
    ret_dict["low_sym"] = low_sym
    # Pass back our pre color formatted dictionary of results
    return ret_dict


# ...existing code...
def print_col_headers(trades_lst):
    """
    Prints the list of column headers in the trades table given switch -N
    """
    if not trades_lst:
        return

    final_list = ""
    local_counter = 1

    # Use only one row's keys; all rows have the same columns
    headers = list(trades_lst[0].keys())

    for my_key in headers:
        final_list += f"{my_key:<20}"

        if local_counter % 5 == 0:
            print(f"{colorize(final_list, 'blue')}")
            final_list = ""

        local_counter += 1
    # If num of columns not divisible by 5 print the remaining odd headers
    if final_list:
        print(f"{colorize(final_list, 'blue')}")


# ...existing code...


def tk_build_hdr_list(trades_lst2):
    """Collect unique column header names from all rows, preserving order."""
    # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)
    seen = set()
    headers = []

    for key in trades_lst2:
        if key not in seen:
            seen.add(key)
            headers.append(key)

    return headers


def build_hdr_list(trades_lst2):
    """Collect unique column header names from all rows, preserving order."""
    # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)
    seen = set()
    headers = []

    for row in trades_lst2:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)

    return headers


"""Collect unique column header names from all rows, preserving order."""
# (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)


def format_group_summary(res_dict):
    """color and format the results dictionary"""
    lhigh_tot = colorize(
        f"{res_dict['high_sym']['total']:.2f}",
        "green",
    )
    llow_tot = colorize(
        f"{res_dict['low_sym']['total']:.2f}",
        "red",
    )
    lhigh_sym = colorize(
        f"{res_dict['high_sym']['symbol']}",
        "cyan",
    )
    llow_sym = colorize(f"{res_dict['low_sym']['symbol']}", "cyan")

    return (
        f"{'Total Trades:':>16} {res_dict['trade_count']}    {'Total P&L:':<13}   {res_dict['total_pnl']}"
        f"{'Max Win:':<10} {res_dict['max_win']}"
        f"{'Max Loss:':>10}{'':<5}{res_dict['max_loss']}\n"
        f"{'Avg Win:':>16} {res_dict['avg_wins']}     {'Avg Loss:':<13}  {res_dict['avg_loss']}"
        f"{'':<4}W/L: {res_dict['tot_wins']}/{res_dict['tot_losers']}{'':<6}W/L%:{'':<5}{res_dict['win_pct']}"
        f"%/{res_dict['loss_pct']}%\n"
        f"{'High Sym:':>16} {lhigh_sym:>10} ({lhigh_tot:>16})"
        f"{'Low Sym:':>13} {llow_sym} ({llow_tot}){'Tot. Fees:':>19} {res_dict['tot_fees']}\n"
    )


def numeric_value(value):
    """
    Return a number only when the whole value is a plain integer or decimal.

    This deliberately leaves dates/times, IDs, and mixed letter/number values
    as text. Numeric values returned directly by sqlite are accepted too.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    value_text = str(value).strip()
    if not re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)",
        value_text,
    ):
        return None
    return float(value_text)


def value_in_selected(actual, selected):
    """
    Compare a DB value against one or more CLI-supplied strings.

    argparse always supplies strings. Plain numeric values are compared as
    numbers for every field, while dates/times, IDs, and mixed values stay as
    text. A selected numeric value may start with !=, <=, >=, <, or >.
    With no operator, equality is the default.
    """
    actual_str = str(actual)
    actual_num = numeric_value(actual)

    for val in selected:
        val = val.strip()
        for op in ("!=", "<=", ">=", "<", ">"):
            if val.startswith(op):
                if actual_num is None:
                    break
                bound = numeric_value(val[len(op) :])
                if bound is None:
                    break
                if op == "!=" and actual_num != bound:
                    return True
                if op == "<=" and actual_num <= bound:
                    return True
                if op == ">=" and actual_num >= bound:
                    return True
                if op == "<" and actual_num < bound:
                    return True
                if op == ">" and actual_num > bound:
                    return True
                break
        else:
            if actual_str == val:
                return True
            selected_num = numeric_value(val)
            if actual_num is not None and selected_num is not None:
                if actual_num == selected_num:
                    return True
    return False


def print_group_summary(
    group_name,
    trade_list,
    key,
    output_file,
    start_date,
    end_date,
    output_dict,
):
    """Print this groups summary list"""
    res_dict = proc_dict(
        trade_list,
        group_name,
        key,
        output_file,
        start_date,
        end_date,
        output_dict,
    )
    if int(res_dict["trade_count"]) >= 1:
        print_outfile(BL_EQUALSTR, output_file)
        print_outfile(
            format_group_summary(res_dict),
            output_file,
        )
        print_outfile(BL_EQUALSTR + "\n\n", output_file)


if __name__ == "__main__":
    app = QuickApp(title="Trade Analyzer Utility", size=(1080, 700))
    app.set_single_tool(TradeAnalyzerTool)
    app.run()
