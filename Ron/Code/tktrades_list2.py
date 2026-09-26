"""Trade Analyzer: the existing CLI report engine inside a QuickTk shell.

Run without --gui for the traditional terminal report. Add --gui to edit the
same options on screen and keep running reports until you close the app.
See ../Docs/tktrades_gui_guide.md for examples and a map of this file.
"""

import argparse
import contextlib
import copy
import csv
import io
import os
import re
import sqlite3
import sys
import tkinter as tk
import json
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from quick_tk import QuickApp, ToolView
from quick_tk.core.forms import (
    MultiSelectDropdown,
)
from tkcalendar import DateEntry
from local_functions import (
    STAT_LABEL_VALUE_RE,
    Timed,
    chkstr_isnum,
    clean_ansi,
    colorize,
    date_check,
)

# Constants stay global; report settings and results belong to each tool instance.
DB_PATH = str(
    Path(__file__).resolve().parents[2]
    / "data"
    / "trading_bot.db"
)
EQUALSTR = "=" * 175 + "\n"
BL_EQUALSTR = colorize(EQUALSTR, "blue")


class TradeAnalyzerTool(ToolView):
    title = "Trade Analyzer"
    description = "Filter your trades and open independent report windows"

    # 1. GUI setup and controls. These collect options; they do not calculate P&L.
    def initialize_report_state(self, args):
        """Set up the non-widget state. The CLI calls this without creating Tk.

        self.args holds the options (the same names argparse uses). main_loop
        turns these into self.key_list, self.start_date, and other working values.
        Tk variables only hold what is currently displayed in the controls.
        """
        self.args = copy.copy(args)
        self.gui_mode = args.gui
        self.reports = []
        self.current_report = None
        self.run_number = 0
        self.hdr_list = []
        self.trades_list = []

    def build_ui(self):
        """Build controls only; opening the GUI does not run a report."""
        self.initialize_report_state(
            self.app.report_args
        )
        self.option_vars = {}
        self.key_vars = []
        self.value_vars = []
        self.sort_vars = []
        self.key_boxes = []
        self.value_boxes = []
        self.available_trades = []
        self.table_names = []
        self.sort_boxes = []
        body = self._main_container
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # The old sample-data panel is now a field/value reference for our DB.
        left = ttk.LabelFrame(
            body,
            text="Database fields and values",
            padding=10,
        )
        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 12),
        )
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        ttk.Label(
            left,
            text="Choose a field to see its values.",
        ).grid(sticky="w")
        self.inspect_var = tk.StringVar(
            value="strategy_name"
        )
        self.inspect_box = ttk.Combobox(
            left,
            textvariable=self.inspect_var,
            state="readonly",
            width=27,
        )
        self.inspect_box.grid(
            row=1, column=0, sticky="ew", pady=6
        )
        self.inspect_box.bind(
            "<<ComboboxSelected>>",
            self.refresh_values,
        )
        ttk.Label(
            left,
            text="Select values, then add them to a filter.",
        ).grid(row=2, column=0, sticky="w")
        value_frame = ttk.Frame(left)
        value_frame.grid(
            row=3, column=0, sticky="nsew"
        )
        value_frame.rowconfigure(0, weight=1)
        value_frame.columnconfigure(0, weight=1)
        self.available_values = tk.Listbox(
            value_frame,
            selectmode="extended",
            exportselection=False,
        )
        self.available_values.grid(
            row=0, column=0, sticky="nsew"
        )
        scroll = ttk.Scrollbar(
            value_frame,
            orient="vertical",
            command=self.available_values.yview,
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.available_values.configure(
            yscrollcommand=scroll.set
        )
        self.target_filter = tk.StringVar(
            value="1"
        )
        ttk.Combobox(
            left,
            textvariable=self.target_filter,
            values=["1", "2", "3", "4", "5"],
            state="readonly",
            width=5,
        ).grid(
            row=4, column=0, sticky="w", pady=6
        )
        ttk.Button(
            left,
            text="Use selected values in filter",
            command=self.use_selected_values,
        ).grid(row=5, column=0, sticky="ew")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        # Tabs keep all five filters usable on a normal-height laptop screen.
        options_pages = ttk.Notebook(right)
        options_pages.grid(
            row=0, column=0, sticky="nsew"
        )
        settings = ttk.Frame(
            options_pages, padding=10
        )
        options_pages.add(
            settings,
            text="Database, dates and output",
        )
        ttk.Label(settings, text="Table").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )
        self.table_box = ttk.Combobox(
            settings, state="readonly", width=32
        )
        self.table_box.grid(
            row=0, column=1, sticky="ew", pady=4
        )
        self.table_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.load_database_fields(),
        )
        settings.columnconfigure(1, weight=1)
        for row, (name, label) in enumerate(
            [
                ("db", "Trades database"),
                (
                    "ssh_host",
                    "SSH host (blank = local)",
                ),
                ("ssh_user", "SSH user"),
                ("ssh_port", "SSH port"),
                ("ssh_db", "Remote SQLite path"),
                ("start", "Start date / time"),
                ("end", "End date / time"),
                ("outfields", "Output fields"),
                (
                    "outfile",
                    "Optional output file",
                ),
            ],
            start=1,  # Row 0 belongs to the table selector.
        ):
            ttk.Label(settings, text=label).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=4,
            )
            var = tk.StringVar()
            self.option_vars[name] = var
            ttk.Entry(
                settings, textvariable=var
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=4,
            )
            if name == "db":
                command, label = (
                    self.choose_database,
                    "Browse...",
                )
            elif name in (
                "ssh_host",
                "ssh_user",
                "ssh_port",
                "ssh_db",
            ):
                command, label = (
                    lambda: None,
                    "",
                )
            elif name in ("start", "end"):
                command, label = (
                    lambda n=name: self.choose_date(
                        n
                    ),
                    "Calendar...",
                )
            elif name == "outfields":
                command, label = (
                    self.choose_output_fields,
                    "Choose...",
                )
            else:
                command, label = (
                    self.choose_output_file,
                    "Browse...",
                )
            if label:
                ttk.Button(
                    settings,
                    text=label,
                    command=command,
                ).grid(
                    row=row, column=2, padx=(8, 0)
                )
        ttk.Label(
            settings,
            text="Leave SSH host blank for local. For VPS mode, enter host/user/remote DB path. The program runs one read-only SSH query per report; it does not copy the DB.",
            wraplength=630,
        ).grid(
            row=row + 1,  # Keep the help below all fields, including dates.
            column=0,
            columnspan=3,
            sticky="w",
            pady=6,
        )
        ttk.Button(
            settings,
            text="Load database fields / refresh values",
            command=self.load_database_fields,
        ).grid(
            row=row + 2,
            column=0,
            columnspan=3,
            sticky="w",
        )

        filters = ttk.Frame(
            options_pages, padding=10
        )
        options_pages.insert(
            0,
            filters,
            text="Search keys (maximum 5)",
        )
        options_pages.select(filters)
        filters.columnconfigure(2, weight=1)
        self.keys_selector = MultiSelectDropdown(
            filters,
            options=[],
            placeholder="Choose up to 5 search keys...",
            max_display=5,
            theme=self.theme,
            on_change=self.select_search_keys,
        )
        self.keys_selector.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(0, 8),
        )
        for col, label in enumerate(
            [
                "#",
                "Search key",
                "Available values / editable comparison",
                "Sort field",
            ]
        ):
            ttk.Label(filters, text=label).grid(
                row=1,
                column=col,
                sticky="w",
                padx=4,
            )
        for i in range(5):
            ttk.Label(
                filters, text=str(i + 1)
            ).grid(row=i + 2, column=0, padx=4)
            key_var, value_var, sort_var = (
                tk.StringVar(),
                tk.StringVar(),
                tk.StringVar(),
            )
            self.key_vars.append(key_var)
            self.value_vars.append(value_var)
            self.sort_vars.append(sort_var)
            key_box = ttk.Combobox(
                filters,
                textvariable=key_var,
                width=19,
                state="readonly",
            )
            key_box.grid(
                row=i + 2,
                column=1,
                padx=4,
                pady=4,
                sticky="ew",
            )
            key_box.bind(
                "<<ComboboxSelected>>",
                lambda event, n=i: self.inspect_filter(
                    n
                ),
            )
            self.key_boxes.append(key_box)
            value_frame = ttk.Frame(filters)
            value_frame.grid(
                row=i + 2,
                column=2,
                padx=4,
                pady=3,
                sticky="ew",
            )
            value_frame.columnconfigure(
                0, weight=1
            )
            value_box = MultiSelectDropdown(
                value_frame,
                options=["ALL"],
                default=["ALL"],
                theme=self.theme,
                placeholder="Choose values...",
                on_change=lambda values, n=i: self.select_filter_values(
                    n, values
                ),
            )
            value_box.grid(
                row=0, column=0, sticky="ew"
            )
            self.value_boxes.append(value_box)
            value_var.trace_add(
                "write",
                lambda *args, n=i: self.sync_value_checks(
                    n
                ),
            )
            ttk.Entry(
                value_frame,
                textvariable=value_var,
            ).grid(
                row=1,
                column=0,
                sticky="ew",
                pady=(2, 0),
            )
            sort_box = ttk.Combobox(
                filters,
                textvariable=sort_var,
                width=18,
                state="readonly",
            )
            sort_box.grid(
                row=i + 2,
                column=3,
                padx=4,
                sticky="ew",
            )
            self.sort_boxes.append(sort_box)
        ttk.Label(
            filters,
            text="Blank key = unused row. Blank values = ALL. Each active key opens a report window. AND joins the filters into one report.",
            wraplength=640,
        ).grid(
            row=7,
            column=0,
            columnspan=4,
            sticky="w",
            pady=6,
        )

        switches = ttk.Frame(right)
        switches.grid(
            row=1, column=0, sticky="ew"
        )
        view_menu = tk.Menu(
            self.app._menu_bar, tearoff=False
        )
        self.app._menu_bar.add_cascade(
            label="View", menu=view_menu
        )
        for i, (name, label) in enumerate(
            [
                ("open", "Open trades"),
                ("Reverse", "Reverse sort"),
                ("Ext", "Extended trade IDs"),
                ("and_filter", "AND filters"),
                ("csv", "CSV output file"),
                (
                    "Names",
                    "Show field names only (-N)",
                ),
            ]
        ):
            var = tk.BooleanVar()
            self.option_vars[name] = var
            ttk.Checkbutton(
                switches, text=label, variable=var
            ).grid(
                row=i // 3,
                column=i % 3,
                sticky="w",
                padx=6,
                pady=4,
            )
            view_menu.add_checkbutton(
                label=label, variable=var
            )
        actions = ttk.Frame(right)
        actions.grid(
            row=2, column=0, sticky="ew", pady=10
        )
        ttk.Button(
            actions,
            text="Run report",
            command=self.on_analyze,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Reset filters",
            command=self.on_reset,
        ).pack(side="left", padx=8)
        ttk.Button(
            actions,
            text="Show field names",
            command=self.show_field_names,
        ).pack(side="left")
        self.status_var = tk.StringVar(
            value="Ready. Choose options, then Run report."
        )
        ttk.Label(
            right,
            textvariable=self.status_var,
            wraplength=640,
        ).grid(row=3, column=0, sticky="nw")
        self.apply_options_to_controls(self.args)
        self.load_database_fields()

    def apply_options_to_controls(self, args):
        """Use startup arguments (or defaults on Reset) to fill the widgets."""
        for name, var in self.option_vars.items():
            value = getattr(args, name)
            var.set(
                value if value is not None else ""
            )
        keys = (
            args.key or "strategy_name"
        ).split(",")
        if keys == ["ALL"]:
            keys = [
                "strategy_name",
                "symbol",
                "exit_reason",
                "quantity",
                "broker_order_id",
            ]
        sorts = (args.sort_keys or "").split(",")
        for i in range(5):
            self.key_vars[i].set(
                keys[i].strip()
                if i < len(keys)
                else ""
            )
            self.value_vars[i].set(
                getattr(args, f"list{i+1}")
                or (
                    "ALL" if i < len(keys) else ""
                )
            )
            self.sort_vars[i].set(
                sorts[i].strip()
                if i < len(sorts)
                else ""
            )

    def on_reset(self):
        """Reset the next report's options; existing windows keep their results."""
        args = self.make_parser().parse_args(
            ["--gui"]
        )
        args.db = self.option_vars["db"].get()
        self.apply_options_to_controls(args)
        self.populate_filter_choices()
        self.status_var.set(
            "Filters reset. Existing reports are unchanged."
        )

    @staticmethod
    def quote_identifier(name):
        """Quote a table or column name selected from sqlite metadata."""
        if not name:
            raise ValueError(
                "Choose a database table first."
            )
        return (
            '"'
            + str(name).replace('"', '""')
            + '"'
        )

    def choose_database(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose trades database",
            filetypes=[
                (
                    "SQLite database",
                    "*.db *.sqlite *.sqlite3",
                ),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.option_vars["db"].set(path)
            self.load_database_fields()

    def choose_output_file(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Choose report output name",
            defaultextension=".txt",
            filetypes=[
                ("Text", "*.txt"),
                ("CSV", "*.csv"),
            ],
        )
        if path:
            self.option_vars["outfile"].set(path)

    def choose_date(self, name):
        """Calendar fills a date; the entry still lets you edit hours/minutes."""
        win = tk.Toplevel(self)
        win.title("Choose " + name + " date")
        calendar = DateEntry(
            win, date_pattern="yyyy-mm-dd"
        )
        calendar.pack(padx=15, pady=15)
        old = self.option_vars[name].get()
        if old:
            try:
                calendar.set_date(
                    datetime.fromisoformat(
                        old
                    ).date()
                )
            except ValueError:
                pass

        def use_date():
            time = (
                "00:00"
                if name == "start"
                else "23:59"
            )
            self.option_vars[name].set(
                calendar.get_date().isoformat()
                + "T"
                + time
            )
            win.destroy()

        ttk.Button(
            win, text="Use date", command=use_date
        ).pack(pady=(0, 15))

    def load_database_fields(self):
        """Read column names even when the trades table has no rows."""
        self.args.db = self.option_vars[
            "db"
        ].get()
        try:
            conn = self.connect()
            try:
                self.table_names = getattr(
                    self,
                    "remote_table_names",
                    None,
                ) or [
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    )
                ]
                selected_table = (
                    self.option_vars.get("table")
                )
                selected_table = (
                    selected_table.get()
                    if selected_table
                    else self.args.table
                )
                if (
                    selected_table
                    not in self.table_names
                ):
                    selected_table = (
                        "trades"
                        if "trades"
                        in self.table_names
                        else (
                            self.table_names[0]
                            if self.table_names
                            else ""
                        )
                    )
                self.args.table = selected_table
                self.table_box.configure(
                    values=self.table_names
                )
                self.table_box.set(selected_table)
                self.hdr_list = [
                    col[1]
                    for col in conn.execute(
                        f"PRAGMA table_info({self.quote_identifier(selected_table)})"
                    )
                ]
                # These are choices only. main_loop rereads trades for each report.
                self.available_trades = [
                    dict(row)
                    for row in conn.execute(
                        f"SELECT * FROM {self.quote_identifier(selected_table)}"
                    )
                ]
            finally:
                conn.close()
            for box in (
                self.key_boxes + self.sort_boxes
            ):
                box.configure(
                    values=[""] + self.hdr_list
                )
            self.inspect_box.configure(
                values=self.hdr_list
            )
            if (
                self.inspect_var.get()
                not in self.hdr_list
            ):
                self.inspect_var.set(
                    self.hdr_list[0]
                    if self.hdr_list
                    else ""
                )
            self.populate_filter_choices()
            self.refresh_values()
        except (
            sqlite3.Error,
            OSError,
            ValueError,
        ) as exc:
            self.hdr_list = []
            self.available_trades = []
            self.table_names = []
            self.populate_filter_choices()
            for box in (
                self.key_boxes
                + self.sort_boxes
                + [self.inspect_box]
            ):
                box.configure(values=[])
            self.available_values.delete(0, "end")
            self.status_var.set(
                f"Could not read database: {exc}. Choose a database to continue."
            )

    def values_for_field(self, field):
        """Build dropdown choices from the loaded trade dictionaries in memory."""
        return sorted(
            {
                str(trade.get(field))
                for trade in self.available_trades
            },
            key=str.casefold,
        )

    def populate_filter_choices(self):
        """Each of the five value dropdowns follows its own selected field."""
        if (
            self.keys_selector.options
            != self.hdr_list
        ):
            self.keys_selector.set_options(
                self.hdr_list
            )
        # Keep the key popup open so several fields can be checked in one visit.
        active = [
            var.get() for var in self.key_vars
        ]
        for (
            key,
            var,
        ) in (
            self.keys_selector.selected_vars.items()
        ):
            var.set(key in active)
        self.keys_selector._update_summary()
        for key, value, box in zip(
            self.key_vars,
            self.value_vars,
            self.value_boxes,
        ):
            options = (
                ["ALL"]
                + [
                    item
                    for item in self.values_for_field(
                        key.get()
                    )
                    if item != "ALL"
                ]
                if key.get() in self.hdr_list
                else ["ALL"]
            )
            box.set_options(
                options,
                default=[
                    item.strip()
                    for item in value.get().split(
                        ","
                    )
                ],
            )

    def sync_value_checks(self, index):
        """Typing a comparison also clears any old ALL checkmark in the popup."""
        selected = [
            item.strip()
            for item in self.value_vars[index]
            .get()
            .split(",")
        ]
        box = self.value_boxes[index]
        for (
            value,
            var,
        ) in box.selected_vars.items():
            var.set(value in selected)
        box._update_summary()

    def select_search_keys(self, selected):
        """Keep selection order, so list1 belongs to key1 and so on.

        Existing fields keep their values and sort settings when a field before
        them is removed. Newly selected fields start with ALL values.
        """
        previous = [
            (k.get(), v.get(), s.get())
            for k, v, s in zip(
                self.key_vars,
                self.value_vars,
                self.sort_vars,
            )
            if k.get()
        ]
        if len(selected) > 5:
            self.keys_selector.set_options(
                self.hdr_list,
                default=[
                    k for k, v, s in previous
                ],
            )
            self.status_var.set(
                "Choose no more than five search keys."
            )
            return
        ordered = [
            item
            for item in previous
            if item[0] in selected
        ]
        ordered += [
            (key, "ALL", "")
            for key in selected
            if key
            not in [item[0] for item in ordered]
        ]
        for i in range(5):
            key, value, sort = (
                ordered[i]
                if i < len(ordered)
                else ("", "", "")
            )
            self.key_vars[i].set(key)
            self.value_vars[i].set(value)
            self.sort_vars[i].set(sort)
        self.populate_filter_choices()

    def select_filter_values(self, index, values):
        # If a specific value is checked while ALL was selected, use specifics.
        # Checking ALL after specific values switches back to the whole field.
        previous = (
            self.value_vars[index]
            .get()
            .split(",")
        )
        if "ALL" in values and len(values) > 1:
            values = (
                [
                    item
                    for item in values
                    if item != "ALL"
                ]
                if "ALL" in previous
                else ["ALL"]
            )
        self.value_vars[index].set(
            ",".join(values) or "ALL"
        )
        box = self.value_boxes[index]
        for (
            value,
            var,
        ) in box.selected_vars.items():
            var.set(value in values)
        box._update_summary()

    def refresh_values(self, event=None):
        self.available_values.delete(0, "end")
        field = self.inspect_var.get()
        if field not in self.hdr_list:
            return
        values = self.values_for_field(field)
        for value in values:
            self.available_values.insert(
                "end", value
            )
        self.status_var.set(
            f"Loaded {len(self.hdr_list)} fields. {len(values)} distinct values for {field} (all trades)."
        )

    def inspect_filter(self, index):
        key = self.key_vars[index].get()
        if key:
            self.inspect_var.set(key)
            self.target_filter.set(str(index + 1))
            self.value_vars[index].set("ALL")
            self.populate_filter_choices()
            self.refresh_values()
        else:
            self.populate_filter_choices()

    def use_selected_values(self):
        index = int(self.target_filter.get()) - 1
        values = [
            self.available_values.get(i)
            for i in self.available_values.curselection()
        ]
        if values:
            self.key_vars[index].set(
                self.inspect_var.get()
            )
            self.value_vars[index].set(
                ",".join(values)
            )
            self.populate_filter_choices()

    def choose_output_fields(self):
        win = tk.Toplevel(self)
        win.title(
            "Select output columns (Ctrl-click for more than one)"
        )
        choices = tk.Listbox(
            win,
            selectmode="extended",
            exportselection=False,
            width=40,
            height=22,
        )
        choices.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )
        selected = (
            self.option_vars["outfields"]
            .get()
            .split(",")
        )
        for i, field in enumerate(self.hdr_list):
            choices.insert("end", field)
            if field in selected or selected == [
                "ALL"
            ]:
                choices.selection_set(i)

        def use_fields():
            self.option_vars["outfields"].set(
                ",".join(
                    choices.get(i)
                    for i in choices.curselection()
                )
            )
            win.destroy()

        ttk.Button(
            win,
            text="Use selected columns (none = defaults)",
            command=use_fields,
        ).pack(pady=10)

    def show_field_names(self):
        self.load_database_fields()
        messagebox.showinfo(
            "Available trade fields",
            "\n".join(self.hdr_list)
            or "No database fields available.",
            parent=self,
        )

    def read_controls(self):
        """Copy widgets into the same option object the CLI supplies.

        Keep each key, values, and sort field together when skipping blank rows.
        A blank sort slot uses that row's search key when another row is sorted.
        """
        for name, var in self.option_vars.items():
            value = var.get()
            setattr(
                self.args,
                name,
                (
                    value.strip() or None
                    if isinstance(value, str)
                    else value
                ),
            )
        if hasattr(self, "table_box"):
            self.args.table = self.table_box.get()
        if not self.args.db:
            raise ValueError(
                "Choose a trades database first."
            )
        active = [
            (k.get(), v.get(), s.get())
            for k, v, s in zip(
                self.key_vars,
                self.value_vars,
                self.sort_vars,
            )
            if k.get()
        ]
        if not active and not self.args.Names:
            raise ValueError(
                "Choose at least one search key."
            )
        self.args.key = ",".join(
            k for k, v, s in active
        )
        self.args.sort_keys = (
            ",".join(s or k for k, v, s in active)
            if any(s for k, v, s in active)
            else None
        )
        for i in range(5):
            setattr(
                self.args,
                f"list{i+1}",
                (
                    (
                        active[i][1].strip()
                        or "ALL"
                    )
                    if i < len(active)
                    else None
                ),
            )

    def on_analyze(self):
        """Run repeatedly without reparsing argv or letting sys.exit close Tk.

        The old validation prints a message before exiting. Catch that exit here
        and show its message in a dialog. The CLI keeps its original exit behavior.
        """
        messages = io.StringIO()
        try:
            self.read_controls()
            if self.args.Names:
                self.show_field_names()
                return
            with (
                contextlib.redirect_stdout(
                    messages
                ),
                contextlib.redirect_stderr(
                    messages
                ),
            ):
                self.main_loop()
            self.run_number += 1
            for report in self.reports:
                self.open_report_window(report)
            # Open all windows first, so a bad output folder cannot hide results.
            for report in self.reports:
                # GUI files are new snapshots; CLI output keeps its append behavior.
                if (
                    self.args.outfile
                    or self.args.csv
                ):
                    folder = (
                        Path(self.args.outfile)
                        .expanduser()
                        .parent
                        if self.args.outfile
                        else Path.cwd()
                    )
                    stem = (
                        Path(
                            self.args.outfile
                        ).stem
                        if self.args.outfile
                        else "trades"
                    )
                    self.write_report_file(
                        report,
                        folder,
                        stem,
                        self.args.csv,
                    )
            count = sum(
                len(report["rows"])
                for report in self.reports
            )
            self.status_var.set(
                f"Run {self.run_number}: opened {len(self.reports)} report window(s), {count} report rows. "
                + clean_ansi(
                    messages.getvalue()
                ).strip()
            )
        except (
            SystemExit,
            sqlite3.Error,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            detail = (
                clean_ansi(
                    messages.getvalue()
                ).strip()
                or str(exc)
                or "Please check the report options."
            )
            self.status_var.set(
                "Report could not finish. "
                + detail[-500:]
            )
            messagebox.showerror(
                "Report options / database",
                detail,
                parent=self,
            )

    def begin_report(self, title, columns):
        """One result bucket per key, not per strategy/symbol group.

        proc_dict adds rows only after its existing filter/date check succeeds.
        print_outfile adds the legacy formatted text to this same bucket.
        """
        if self.gui_mode:
            self.current_report = {
                "title": title,
                "columns": list(columns),
                "rows": [],
                "text": [],
                "extended": self.extended,
            }
            self.reports.append(
                self.current_report
            )

    def write_report_file(
        self,
        report,
        folder,
        stem="trades",
        as_csv=True,
        rows=None,
    ):
        """Use exclusive creation: even a filename collision cannot overwrite.

        rows may be the window's current sorted/filtered table. Otherwise export
        the original report rows. CSV comes from real cells, not split text.
        """
        safe_title = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            report["title"],
        )
        stamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )
        suffix = ".csv" if as_csv else ".txt"
        base = f"{stem}_{safe_title}_{stamp}"
        number = 0
        while True:
            path = Path(folder) / (
                base
                + (f"_{number}" if number else "")
                + suffix
            )
            try:
                stream = path.open(
                    "x",
                    newline="",
                    encoding=(
                        "utf-8-sig"
                        if as_csv
                        else "utf-8"
                    ),
                )
                break
            except FileExistsError:
                number += 1
        with stream:
            if as_csv:
                writer = csv.writer(stream)
                writer.writerow(report["columns"])
                if rows is None:
                    rows = [
                        [
                            row.get(key)
                            for key in report[
                                "columns"
                            ]
                        ]
                        for row in report["rows"]
                    ]
                writer.writerows(rows)
            else:
                stream.write(
                    "".join(report["text"])
                )
        return path

    def open_report_window(self, report):
        """Keep this window's data in its own widgets and callback closures."""
        win = tk.Toplevel(self)
        win.title(
            f"Run {self.run_number} — {report['title']}"
        )
        win.geometry("1150x700")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        bar = ttk.Frame(win, padding=8)
        bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            bar,
            text=f"{report['title']}: {len(report['rows'])} trades. Click a column heading to sort.",
        ).pack(side="left")
        pages = ttk.Notebook(win)
        pages.grid(row=1, column=0, sticky="nsew")
        table = self.add_data_table(
            columns=report["columns"],
            parent=pages,
            enable_search=True,
            enable_export_csv=False,
        )
        table_rows = []
        for row in report["rows"]:
            cells = []
            for key in report["columns"]:
                value = row.get(key)
                if (
                    key == "trade_id"
                    and not report["extended"]
                    and value is not None
                ):
                    value = str(value)[-16:]
                cells.append(
                    "" if value is None else value
                )
            table_rows.append(cells)
        table.set_data(table_rows)
        pages.add(table, text="Sortable trades")
        text_frame = ttk.Frame(pages)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        text = tk.Text(
            text_frame,
            wrap="none",
            font=("Consolas", 10),
        )
        text.grid(row=0, column=0, sticky="nsew")
        for orient, row, col, command in [
            ("vertical", 0, 1, text.yview),
            ("horizontal", 1, 0, text.xview),
        ]:
            scroll = ttk.Scrollbar(
                text_frame,
                orient=orient,
                command=command,
            )
            scroll.grid(
                row=row,
                column=col,
                sticky=(
                    "ns"
                    if orient == "vertical"
                    else "ew"
                ),
            )
            text.configure(
                **{
                    (
                        "yscrollcommand"
                        if orient == "vertical"
                        else "xscrollcommand"
                    ): scroll.set
                }
            )
        text.insert(
            "1.0",
            "".join(report["text"])
            or "No trades matched these filters.",
        )
        text.configure(state="disabled")
        pages.add(
            text_frame,
            text="Original report and summaries",
        )

        def export(as_csv):
            folder = filedialog.askdirectory(
                parent=win,
                title="Choose export folder (a unique filename is created)",
            )
            if not folder:
                return
            try:
                # Export what is visible, in the order the user chose by sorting.
                visible = [
                    table.tree.item(
                        item, "values"
                    )
                    for item in table.tree.get_children()
                ]
                path = self.write_report_file(
                    report,
                    folder,
                    as_csv=as_csv,
                    rows=visible,
                )
                messagebox.showinfo(
                    "Report saved",
                    str(path),
                    parent=win,
                )
            except OSError as exc:
                messagebox.showerror(
                    "Could not save report",
                    str(exc),
                    parent=win,
                )

        ttk.Button(
            bar,
            text="Export visible CSV",
            command=lambda: export(True),
        ).pack(side="right")
        ttk.Button(
            bar,
            text="Save original text",
            command=lambda: export(False),
        ).pack(side="right", padx=8)
        return win

    # 2. The argument list and the original report loop.
    # Both startup modes reach this same calculation/grouping code.
    @staticmethod
    def make_parser():
        """One option list for both startup modes. Parsing never starts a report."""

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
            help="Starting date and time. Format YYYY-MM-DDTHH:MM T being a literal T",
        )
        parser.add_argument(
            "-e",
            "--end",
            metavar="",
            help="Ending date and time. Format YYYY-MM-DDTHH:MM T being a literal T",
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
            help="Extended Trade Id , default is shortened Id (Useful when you need the full trade Id for a lookup)",
        )

        parser.add_argument(
            "--gui",
            action="store_true",
            help="Open the graphical report builder",
        )
        parser.add_argument(
            "--db",
            default=DB_PATH,
            help="Path to the trades SQLite database",
        )
        parser.add_argument(
            "--table",
            default="trades",
            help="SQLite table to report",
        )
        parser.add_argument(
            "--ssh-host",
            help="SSH host for a remote SQLite read",
        )
        parser.add_argument(
            "--ssh-user",
            help="SSH user for the remote SQLite read",
        )
        parser.add_argument(
            "--ssh-port",
            type=int,
            default=22,
            help="SSH port",
        )
        parser.add_argument(
            "--ssh-db",
            help="SQLite path on the SSH host",
        )
        return parser

    def main_loop(self):
        """Run the old reporting steps with the settings already stored on self.

        The CLI stores parsed options in self.args. The Run button updates the
        same options first. Neither path needs to parse the command line again.
        Reset per-run results here so a second run cannot inherit old trades.
        """
        self.reports = []
        self.current_report = None
        self.trades_list = []
        self.dict_of_trades = []
        # Standard library approach to handle Windows initialization safely
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            stdout_handle = kernel32.GetStdHandle(
                -11
            )  # STD_OUTPUT_HANDLE

            console_mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(
                stdout_handle,
                ctypes.byref(console_mode),
            ):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = (
                    0x0004
                )
                kernel32.SetConsoleMode(
                    stdout_handle,
                    console_mode.value
                    | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                )

        self.DEF_OUTFIELDS = {
            "trade_id": "ID",
            "entry_time": "Entry",
            "exit_time": "Exit",
            "symbol": "Symbol",
            "direction": "Direct",
            "entry_price": "EntryPrice",
            "exit_price": "ExitPrice",
            "pnl": "PNL",
        }

        self.ALL_OUTFIELDS = {
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

        self.output_file = ""
        self.is_sorted = False
        self.default_key_list = [
            "strategy_name",
            "symbol",
            "exit_reason",
            "quantity",
            "broker_order_id",
        ]
        # Connect to DB and load the trades table into the trades_list dictionary

        args = self.args

        self.csv_true = (
            args.csv if args.csv else False
        )
        self.extended = (
            args.Ext if args.Ext else False
        )

        self.mode = (
            "open" if args.open else "closed"
        )
        self.is_sorted = (
            args.sort_keys
            if args.sort_keys
            else False
        )
        self.rev_sort = (
            args.Reverse
            if args.Reverse
            else False
        )

        conn = self.connect()
        try:
            # Read schema separately: an empty trades table still has fields.
            self.hdr_list = [
                col[1]
                for col in conn.execute(
                    f"PRAGMA table_info({self.quote_identifier(args.table)})"
                )
            ]
            if not self.is_trade_table():
                self.trades_list = []
            elif self.mode == "closed":
                self.trades_list = (
                    self.get_closed_trades(conn)
                )
            else:
                self.trades_list = (
                    self.get_open_trades(conn)
                )
        finally:
            conn.close()

        if args.Names:
            self.print_col_headers(
                [dict.fromkeys(self.hdr_list)]
            )
            sys.exit(2)

        if (
            not self.trades_list
            and self.is_trade_table()
        ):
            (
                print("No closed trades found.")
                if (self.mode == "closed")
                else print(
                    "No open trades found."
                )
            )

            if not self.gui_mode:
                return
        DEF_START_DATE = "1980-01-01T00:00"
        DEF_END_DATE = "4050-01-01T00:00"

        self.start_date = (
            args.start
            if args.start
            else DEF_START_DATE
        )
        self.end_date = (
            args.end if args.end else DEF_END_DATE
        )

        if args.start and (
            not date_check(self.start_date)
        ):
            print(
                "Invalid start date. use format YYYY-MM-DDTHH:MM"
            )
            sys.exit(4)

        if args.end and (
            not date_check(self.end_date)
        ):
            print(
                "Invalid end date. use format YYYY-MM-DDTHH:MM"
            )
            sys.exit(4)

        if self.start_date > self.end_date:
            raise ValueError(
                "The start date must be before the end date."
            )

        self.date_range_given = (
            self.start_date != DEF_START_DATE
            or self.end_date != DEF_END_DATE
        )

        self.output_file = args.outfile
        if (
            self.csv_true
            and not self.output_file
            and not self.gui_mode
        ):
            self.output_file = (
                "trades_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
            )
        if self.csv_true and self.output_file:
            self.output_file = os.path.splitext(
                self.output_file
            )[0]

        # Build a list of list options skipping those not given
        self.list_values = [
            (
                args.list1.split(",")
                if args.list1
                else []
            ),
            (
                args.list2.split(",")
                if args.list2
                else []
            ),
            (
                args.list3.split(",")
                if args.list3
                else []
            ),
            (
                args.list4.split(",")
                if args.list4
                else []
            ),
            (
                args.list5.split(",")
                if args.list5
                else []
            ),
        ]

        self.key_list = (
            [
                key.strip()
                for key in args.key.split(",")
            ]
            if args.key
            else []
        )
        if self.key_list == ["ALL"]:
            self.key_list = self.default_key_list[
                :
            ]

        if len(self.key_list) > 5:
            print(
                "\nError: maximum of 5 keys is supported.\n"
            )
            sys.exit(1)

        self.output_fields = (
            [
                key.strip()
                for key in args.outfields.split(
                    ","
                )
            ]
            if args.outfields
            else False
        )

        if self.output_fields == ["ALL"]:
            self.output_fields = self.hdr_list[:]

        self.output_dict = {}
        if not self.output_fields:
            self.output_dict = self.DEF_OUTFIELDS
        else:
            for outpt in self.output_fields:
                if outpt not in self.hdr_list:
                    print(
                        f"\nError: {outpt} is not a valid entry. please run with -N to see a list of valid choices\n"
                    )
                    sys.exit()
            for field in self.output_fields:
                self.output_dict[field] = (
                    self.ALL_OUTFIELDS.get(
                        field, field
                    )
                )

        self.sort_list = (
            [
                key.strip()
                for key in args.sort_keys.split(
                    ","
                )
            ]
            if args.sort_keys
            else []
        )

        if len(self.sort_list) > 5:
            print(
                "\nError: maximum of 5 sort keys is supported.\n"
            )
            sys.exit(1)
        # Verify every key value input is valid
        if self.date_range_given and (
            not any(self.list_values)
        ):
            for j in range(5):
                self.list_values[j].append("ALL")

        if (
            self.date_range_given
            and len(self.key_list) < 1
        ):
            self.key_list = self.default_key_list

        if (
            (not len(self.list_values))
            or (not len(self.key_list))
        ) and (not self.date_range_given):
            self.make_parser().print_help()
            self.make_parser().exit(
                2,
                "\nError: provide --key key1,key2,... and at least one --list option per key given.\n",
            )

        for key_name in self.key_list:
            if key_name not in self.hdr_list:
                print(
                    f"\nError: {key_name} is not a valid entry. please run with -N to see a list of valid choices\n"
                )
                sys.exit()

        for sort_name in self.sort_list:
            if sort_name not in self.hdr_list:
                print(
                    f"\nError: {sort_name} is not a valid entry. please run with -N to see a list of valid choices\n"
                )
                sys.exit()
        ttrades_list = []
        for i in range(len(self.key_list)):
            ttrades_list.append(
                copy.deepcopy(self.trades_list)
            )
        if self.is_sorted:
            for i in range(
                min(
                    len(self.key_list),
                    len(self.sort_list),
                )
            ):
                for trade in ttrades_list[i]:
                    try:
                        if (
                            chkstr_isnum(
                                trade[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                            )
                            == "float"
                        ):
                            trade[
                                self.sort_list[i]
                            ] = float(
                                trade[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                            )
                        elif (
                            chkstr_isnum(
                                trade[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                            )
                            == "int"
                        ):
                            trade[
                                self.sort_list[i]
                            ] = int(
                                trade[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                            )
                    except (
                        ValueError,
                        TypeError,
                    ):
                        pass
                try:
                    if self.rev_sort:
                        ttrades_list[i].sort(
                            key=lambda r: (
                                r[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                                is None,
                                isinstance(
                                    r[
                                        self.sort_list[
                                            i
                                        ]
                                    ],
                                    str,
                                ),
                                r[
                                    self.sort_list[
                                        i
                                    ]
                                ],
                            ),
                            reverse=True,
                        )
                    else:
                        ttrades_list[i].sort(
                            key=lambda r: (
                                r[
                                    self.sort_list[
                                        i
                                    ]
                                ]
                                is None,
                                isinstance(
                                    r[
                                        self.sort_list[
                                            i
                                        ]
                                    ],
                                    str,
                                ),
                                r[
                                    self.sort_list[
                                        i
                                    ]
                                ],
                            ),
                            reverse=False,
                        )
                except ValueError:
                    pass

        if (not args.Names) and (
            len(self.key_list) < 1
        ):
            print(
                "\nError: Please provide at least 1 key , separated by a ,   \n"
            )
            sys.exit()

        if not self.is_trade_table():
            conn = self.connect()
            try:
                self.trades_list = [
                    dict(row)
                    for row in conn.execute(
                        f"SELECT * FROM {self.quote_identifier(args.table)}"
                    )
                ]
            finally:
                conn.close()
            self.run_generic_table_report()
            return self.reports

        # -A/--and: one combined report where a trade must match every selected
        # key/value filter at once (symbol=MSFT AND direction=long), instead of
        # the default independent per-key breakdown below.
        if (
            args.and_filter
            and len(self.key_list) > 1
        ):
            combined_list = []
            for trade in self.trades_list:
                matches_all = True
                for key_name, selected in zip(
                    self.key_list,
                    self.list_values,
                ):
                    if not selected:
                        continue
                    if selected[0] == "ALL":
                        continue
                    if not self.value_in_selected(
                        trade[key_name], selected
                    ):
                        matches_all = False
                        break
                if matches_all:
                    combined_list.append(
                        copy.deepcopy(trade)
                    )

            if self.is_sorted:
                for sort_key in reversed(
                    self.sort_list
                ):
                    for trade in combined_list:
                        try:
                            if (
                                chkstr_isnum(
                                    trade[
                                        sort_key
                                    ]
                                )
                                == "float"
                            ):
                                trade[
                                    sort_key
                                ] = float(
                                    trade[
                                        sort_key
                                    ]
                                )
                            elif (
                                chkstr_isnum(
                                    trade[
                                        sort_key
                                    ]
                                )
                                == "int"
                            ):
                                trade[
                                    sort_key
                                ] = int(
                                    trade[
                                        sort_key
                                    ]
                                )
                        except (
                            ValueError,
                            TypeError,
                        ):
                            pass
                    try:
                        combined_list.sort(
                            key=lambda r: (
                                r[sort_key]
                                is None,
                                isinstance(
                                    r[sort_key],
                                    str,
                                ),
                                r[sort_key],
                            ),
                            reverse=self.rev_sort,
                        )
                    except (
                        ValueError,
                        TypeError,
                    ):
                        pass

            label_parts = [
                f"{key_name}={','.join(selected)}"
                for key_name, selected in zip(
                    self.key_list,
                    self.list_values,
                )
                if selected
            ]
            combined_label = (
                " & ".join(label_parts)
                if label_parts
                else "ALL"
            )
            self.begin_report(
                "AND filters", self.output_dict
            )
            res_dict = self.print_group_summary(
                combined_label,
                combined_list,
                "ALL",
                self.output_file,
                self.start_date,
                self.end_date,
                self.output_dict,
            )
            return

        # Build one generic list of grouped trade dictionaries
        self.dict_of_trades = []

        for idx, key_name in enumerate(
            self.key_list
        ):
            grouped_trades = {}
            for trade in ttrades_list[idx]:
                group_value = trade[key_name]
                grouped_trades.setdefault(
                    group_value, []
                ).append(copy.deepcopy(trade))

            self.dict_of_trades.append(
                {
                    "key": key_name,
                    "selected": (
                        self.list_values[idx]
                        if idx
                        < len(self.list_values)
                        else []
                    ),
                    "groups": grouped_trades,
                }
            )

        for trade_group in self.dict_of_trades:
            self.begin_report(
                trade_group["key"],
                self.output_dict,
            )
            key_name = trade_group["key"]
            selected_values = trade_group[
                "selected"
            ]
            grouped_trades = trade_group["groups"]

            for (
                group_name,
                trade_list,
            ) in grouped_trades.items():
                if not selected_values:
                    continue

                if selected_values[
                    0
                ] == "ALL" or self.value_in_selected(
                    group_name, selected_values
                ):
                    res_dict = (
                        self.print_group_summary(
                            group_name,
                            trade_list,
                            key_name,
                            self.output_file,
                            self.start_date,
                            self.end_date,
                            self.output_dict,
                        )
                    )
        return self.reports

    def is_trade_table(self):
        """Trade summaries require the fields they calculate, not a table name."""
        return {
            "trade_id",
            "entry_time",
            "exit_time",
            "symbol",
            "pnl",
            "fees_paid",
        }.issubset(self.hdr_list)

    def run_generic_table_report(self):
        """Filter any selected SQLite table and send it to the same report window."""
        rows = [
            dict(row) for row in self.trades_list
        ]
        active = [
            (key, values)
            for key, values in zip(
                self.key_list, self.list_values
            )
            if key
        ]
        if not active:
            active = (
                [(self.hdr_list[0], ["ALL"])]
                if self.hdr_list
                else []
            )
        for key, selected in active:
            if selected and selected[0] != "ALL":
                rows = [
                    row
                    for row in rows
                    if self.value_in_selected(
                        row.get(key), selected
                    )
                ]
        for sort_key in reversed(self.sort_list):
            if sort_key in self.hdr_list:
                rows.sort(
                    key=lambda row: (
                        row.get(sort_key) is None,
                        row.get(sort_key),
                    ),
                    reverse=self.rev_sort,
                )
        columns = (
            self.output_fields
            if self.output_fields
            else self.hdr_list
        )
        self.output_dict = {
            column: column
            for column in columns
            if column in self.hdr_list
        }
        self.begin_report(
            f"{self.args.table} table",
            self.output_dict,
        )
        if self.current_report is not None:
            self.current_report["rows"].extend(
                rows
            )
            self.current_report["text"].append(
                f"Table: {self.args.table}\nRows: {len(rows)}\nColumns: {', '.join(columns)}\n"
            )
        elif rows:
            print(
                f"Table: {self.args.table}\nRows: {len(rows)}"
            )
            print("\t".join(columns))
            for row in rows:
                print(
                    "\t".join(
                        (
                            ""
                            if row.get(column)
                            is None
                            else str(
                                row.get(column)
                            )
                        )
                        for column in columns
                    )
                )

    # 3. Original report helpers, now class methods.
    # Function arguments/counters stay local; shared options use self.
    def print_outfile(self, text, output_file):
        """
        Print to Stdout or file name provided. Backwards compatible wrapper.
        If output_file is provided, text is appended to that file.
        Otherwise text is printed to stdout.
        """
        if self.gui_mode:
            self.current_report["text"].append(
                clean_ansi(text)
            )
            return text
        if output_file:
            clean_text = clean_ansi(text)
            try:
                if self.csv_true:
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
                        for (
                            line
                        ) in (
                            clean_text.splitlines()
                        ):
                            stripped = (
                                line.strip()
                            )
                            if (
                                not stripped
                                or set(stripped)
                                == {"="}
                            ):
                                spamwriter.writerow(
                                    []
                                )
                            elif (
                                stripped.count(
                                    ":"
                                )
                                >= 2
                            ):
                                # summary lines like "Total Trades: 54   Total P&L: -1320.00 ..."
                                pairs = STAT_LABEL_VALUE_RE.findall(
                                    stripped
                                )
                                row = [
                                    part.strip()
                                    for label, value in pairs
                                    for part in (
                                        label,
                                        value,
                                    )
                                ]
                                spamwriter.writerow(
                                    row
                                    or stripped.split()
                                )
                            else:
                                spamwriter.writerow(
                                    stripped.split()
                                )
                else:
                    with open(
                        output_file,
                        "a",
                        encoding="utf-8",
                    ) as file:
                        file.write(clean_text)
                        return clean_text
            except OSError as e:
                print(
                    f"Error writing to output file: {e}"
                )
                sys.exit(1)
        else:
            print(text, end="")
            return text

    def connect(self):
        """Open a local DB, or read a remote DB through one SSH command.

        SQLite itself cannot use an SSH tunnel to a file. In remote mode the
        SSH session runs a tiny read-only Python query remotely and returns the
        schema plus rows as JSON. We load that response into a temporary,
        in-memory SQLite database, so the existing report code stays unchanged.
        The VPS database is never copied to disk and the SSH process exits as
        soon as this connection is closed.
        """
        if self.args.ssh_host:
            if not self.args.ssh_db:
                raise ValueError(
                    "Remote mode needs --ssh-db, the SQLite path on the VPS."
                )
            script = (
                "import sqlite3,json,sys; "
                "p,t=sys.argv[1:]; q='\"'+t.replace('\"','\"\"')+'\"'; "
                "c=sqlite3.connect('file:'+p+'?mode=ro',uri=True); "
                "tables=[x[0] for x in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name\")]; "
                "cols=[x[1] for x in c.execute('PRAGMA table_info('+q+')')]; "
                "rows=[list(r) for r in c.execute('SELECT * FROM '+q)]; "
                "print(json.dumps({'tables':tables,'columns':cols,'rows':rows}))"
            )
            command = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=15",
                "-p",
                str(self.args.ssh_port or 22),
                f"{self.args.ssh_user + '@' if self.args.ssh_user else ''}{self.args.ssh_host}",
                # SSH passes this through the Linux shell. Quote the complete
                # remote command so Bash leaves the Python code and paths alone.
                # After python -c, argv must contain just the DB path and table;
                # an extra '--' here would become a third Python argument.
                shlex.join(["python3", "-c", script, self.args.ssh_db, self.args.table]),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode:
                detail = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "SSH query failed"
                )
                raise sqlite3.OperationalError(
                    detail
                )
            try:
                payload = json.loads(
                    result.stdout
                )
                columns = payload["columns"]
                rows = payload["rows"]
                self.remote_table_names = (
                    payload.get(
                        "tables",
                        [self.args.table],
                    )
                )
            except (
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                raise sqlite3.OperationalError(
                    f"SSH returned invalid database data: {exc}"
                ) from exc
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            safe_columns = [
                '"'
                + str(col).replace('"', '""')
                + '"'
                for col in columns
            ]
            conn.execute(
                "CREATE TABLE trades ("
                + ",".join(
                    col + " BLOB"
                    for col in safe_columns
                )
                + ")"
            )
            if rows:
                marks = ",".join(
                    "?" for _ in columns
                )
                conn.executemany(
                    "INSERT INTO trades VALUES ("
                    + marks
                    + ")",
                    rows,
                )
                conn.commit()
            return conn
        path = (
            Path(self.args.db)
            .expanduser()
            .resolve()
        )
        self.remote_table_names = []
        conn = sqlite3.connect(
            path.as_uri() + "?mode=ro", uri=True
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                f"SELECT 1 FROM {self.quote_identifier(self.args.table)} LIMIT 1"
            )
        except sqlite3.Error:
            conn.close()
            raise
        return conn

    def get_closed_trades(self, conn):
        """Read from he database using SQL"""
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC",
            ("closed",),
        )
        return [dict(r) for r in c.fetchall()]

    def get_open_trades(self, conn):
        c = conn.cursor()
        c.execute(
            "SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC",
            ("open",),
        )
        return [dict(r) for r in c.fetchall()]

    @Timed
    def proc_dict(
        self,
        loc_trade_list,
        strat_name,
        ikey,
        output_file,
        start_date,
        end_date,
        output_dict,
    ):
        """Calculate one group's totals and format its trade lines.

        Keep the arithmetic here shared by CLI and GUI. The only GUI addition
        is saving each accepted row; a separate query must not recalculate it.
        """
        # Initialize Locals
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
        # Search the dict for Key  provided
        trade_count = 0
        tot_fees = 0
        for trade in loc_trade_list:
            t_sli = 38 if self.extended else 20
            t_idx = (
                -len(trade["trade_id"])
                if self.extended
                else -16
            )
            #       for my_idx, my_key in trade.items():
            #           field_lens[my_idx] =  len(str(my_key)) + 4
            break  # only look at one record
        for trade_dict in loc_trade_list:
            entry_time = (
                trade_dict["entry_time"] or ""
            )
            exit_time = (
                trade_dict["exit_time"] or ""
            )
            if (
                entry_time[0:16] >= start_date
                and exit_time[0:16] <= end_date
                and (
                    ikey == "ALL"
                    or trade_dict.get(
                        ikey, "None"
                    )
                    == strat_name
                    or strat_name == "ALL"
                )
            ):
                if self.gui_mode:
                    self.current_report[
                        "rows"
                    ].append(dict(trade_dict))
                tot_fees += (
                    trade_dict["fees_paid"] or 0
                )
                symbol = trade_dict["symbol"]

                trade_pnl = float(
                    trade_dict["pnl"] or 0.0
                )
                sym_total_pnl[symbol] = (
                    sym_total_pnl.get(symbol, 0.0)
                    + trade_pnl
                )
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
                max_win = max(max_win, trade_pnl)
                max_loss = min(
                    max_loss, trade_pnl
                )
                # Track the number of trades processed
                trade_count += 1
                if trade_pnl < 0:
                    colorize(
                        f"{trade_pnl:<20.2f}",
                        "red",
                    )
                else:
                    colorize(
                        f"{trade_pnl:<20.2f}",
                        "green",
                    )
                head_str = ""
                tail_str = ""
                for key in output_dict:
                    #                   key_len = field_lens[key]
                    if (
                        key == "trade_id"
                        and self.extended
                    ):
                        head_str += f"{key[t_idx:]:<{t_sli}}"
                    elif key == "exit_reason":
                        head_str += f"{key:<27}"
                    else:
                        head_str += f"{key:<20}"
                    if key == "trade_id":
                        tail_str += f"{trade_dict[key][t_idx:]:{t_sli}}"
                    elif key == "exit_reason":
                        tail_str += f"{str(trade_dict[key] or ''):<27}"
                    elif (
                        key == "entry_time"
                        or key == "exit_time"
                    ):
                        tail_str += f"{(trade_dict[key] or "")[0:16]:<20}"
                    elif trade_dict[key] is None:
                        tail_str += f"{'':<20}"
                    elif (
                        chkstr_isnum(
                            trade_dict[key]
                        )
                        == "float"
                    ):
                        if (
                            float(trade_dict[key])
                            >= 0
                        ):
                            stii = float(
                                trade_dict[key]
                            )
                            stii2 = colorize(
                                f"{stii:<20.6f}",
                                "green",
                            )
                            tail_str += f"{stii2}"
                        else:
                            stii = float(
                                trade_dict[key]
                            )
                            stii2 = colorize(
                                f"{stii:<20.6f}",
                                "red",
                            )
                            tail_str += f"{stii2}"
                    #                             tail_str += f'{colorize({float(trade_dict[key]):<20.6f}}, "red")'
                    else:
                        tail_str += f"{str(trade_dict[key]) if trade_dict[key] is not None else '':<20}"
                head_str += "\n"
                tail_str += "\n"

                if passes == 1:
                    self.print_outfile(
                        f"List of {colorize(strat_name, 'red')} Trades\n",
                        output_file,
                    )
                    self.print_outfile(
                        BL_EQUALSTR, output_file
                    )
                    self.print_outfile(
                        colorize(
                            f"{head_str}",
                            "magenta",
                        ),
                        output_file,
                    )
                    self.print_outfile(
                        BL_EQUALSTR, output_file
                    )
                    passes += 1

                self.print_outfile(
                    tail_str, output_file
                )

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
            low_sym = {
                "symbol": "None",
                "total": 0.0,
            }

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
        ret_dict["trade_count"] = (
            f"{trade_count:<14}"
        )

        # Properly color the Tot PnL red for neg, green for pos
        if total_pnl >= 0:
            ret_dict["total_pnl"] = colorize(
                f"{total_pnl:<19.2f}", "green"
            )
        else:
            ret_dict["total_pnl"] = colorize(
                f"{total_pnl:<19.2f}", "red"
            )

        ret_dict["max_win"] = colorize(
            f"{max_win:<14.2f}", "green"
        )
        ret_dict["max_loss"] = colorize(
            f"{max_loss:>3.2f}", "red"
        )
        ret_dict["avg_wins"] = colorize(
            f"{avg_wins:<14.2f}", "green"
        )
        ret_dict["avg_loss"] = colorize(
            f"{avg_loss:<19.2f}", "red"
        )
        ret_dict["tot_wins"] = colorize(
            f"{tot_winners:>3}", "green"
        )
        ret_dict["tot_losers"] = colorize(
            f"{tot_losers:<11}", "red"
        )
        ret_dict["tot_fees"] = colorize(
            f"{tot_fees:<9.2f}", "red"
        )
        ret_dict["high_sym"] = high_sym
        ret_dict["low_sym"] = low_sym
        # Pass back our pre color formatted dictionary of results
        return ret_dict

    # ...existing code...
    def print_col_headers(self, trades_lst):
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
                print(
                    f"{colorize(final_list, 'blue')}"
                )
                final_list = ""

            local_counter += 1
        # If num of columns not divisible by 5 print the remaining odd headers
        if final_list:
            print(
                f"{colorize(final_list, 'blue')}"
            )

    # ...existing code...

    def tk_build_hdr_list(self, trades_lst2):
        """Collect unique column header names from all rows, preserving order."""
        # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)
        seen = set()
        headers = []

        for key in trades_lst2:
            if key not in seen:
                seen.add(key)
                headers.append(key)

        return headers

    def build_hdr_list(self, trades_lst2):
        """Collect unique column header names from all rows, preserving order."""
        # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)
        seen = set()
        headers = []

        for row in trades_lst2:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    headers.append(key)

        return headers

    """Collect unique column header names from all rows, preserving order."""
    # (Previous bug: returned repeated list due to nested loop — fixed by using single comprehension)

    def format_group_summary(self, res_dict):
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
        llow_sym = colorize(
            f"{res_dict['low_sym']['symbol']}",
            "cyan",
        )

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

    def numeric_value(self, value):
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

    def value_in_selected(self, actual, selected):
        """
        Compare a DB value against one or more CLI-supplied strings.

        argparse always supplies strings. Plain numeric values are compared as
        numbers for every field, while dates/times, IDs, and mixed values stay as
        text. A selected numeric value may start with !=, <=, >=, <, or >.
        With no operator, equality is the default.
        """
        actual_str = str(actual)
        actual_num = self.numeric_value(actual)

        for val in selected:
            val = val.strip()
            for op in (
                "!=",
                "<=",
                ">=",
                "<",
                ">",
            ):
                if val.startswith(op):
                    if actual_num is None:
                        break
                    bound = self.numeric_value(
                        val[len(op) :]
                    )
                    if bound is None:
                        break
                    if (
                        op == "!="
                        and actual_num != bound
                    ):
                        return True
                    if (
                        op == "<="
                        and actual_num <= bound
                    ):
                        return True
                    if (
                        op == ">="
                        and actual_num >= bound
                    ):
                        return True
                    if (
                        op == "<"
                        and actual_num < bound
                    ):
                        return True
                    if (
                        op == ">"
                        and actual_num > bound
                    ):
                        return True
                    break
            else:
                if actual_str == val:
                    return True
                selected_num = self.numeric_value(
                    val
                )
                if (
                    actual_num is not None
                    and selected_num is not None
                ) and (
                    actual_num == selected_num
                ):
                    return True
        return False

    def print_group_summary(
        self,
        group_name,
        trade_list,
        key,
        output_file,
        start_date,
        end_date,
        output_dict,
    ):
        """Print this groups summary list"""
        res_dict = self.proc_dict(
            trade_list,
            group_name,
            key,
            output_file,
            start_date,
            end_date,
            output_dict,
        )
        if int(res_dict["trade_count"]) >= 1:
            self.print_outfile(
                BL_EQUALSTR, output_file
            )
            self.print_outfile(
                self.format_group_summary(
                    res_dict
                ),
                output_file,
            )
            self.print_outfile(
                BL_EQUALSTR + "\n\n", output_file
            )
        return res_dict


def main(argv=None):
    """Choose a startup path before creating any window.

    A CLI-only instance does not initialize the ttk.Frame base, because the
    reporting methods need no widgets. Only --gui constructs a QuickApp.
    """
    args = TradeAnalyzerTool.make_parser().parse_args(
        argv
    )
    if args.gui:
        if (
            args.key
            and len(args.key.split(",")) > 5
        ):
            TradeAnalyzerTool.make_parser().error(
                "maximum of 5 keys is supported"
            )
        if (
            args.sort_keys
            and len(args.sort_keys.split(",")) > 5
        ):
            TradeAnalyzerTool.make_parser().error(
                "maximum of 5 sort keys is supported"
            )
        app = QuickApp(
            title="Trade Analyzer Utility",
            size=(1250, 900),
        )
        app.report_args = args
        app.set_single_tool(TradeAnalyzerTool)
        app.run()
    else:
        tool = TradeAnalyzerTool.__new__(
            TradeAnalyzerTool
        )
        tool.initialize_report_state(args)
        try:
            tool.main_loop()
        except (
            sqlite3.Error,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            print(
                f"Report error: {exc}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())