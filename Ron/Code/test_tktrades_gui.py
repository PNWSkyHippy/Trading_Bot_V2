"""Focused checks for the CLI/GUI bridge. Uses only a temporary trades database.

From the repository root, after activating venv312:
    python -m pytest Ron/Code/test_tktrades_gui.py -q
The GUI check creates real Tk widgets, withdraws the windows, and closes them.
"""

import contextlib
import csv
import io
import sqlite3
import sys
import time
import threading
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)
import tktrades_list as current
import trades_list as legacy


def wait_for_report(app, view):
    deadline = time.monotonic() + 10
    while view.report_running and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.01)
    assert not view.report_running, "Report worker did not finish"


def wait_for_database(app, view):
    deadline = time.monotonic() + 10
    while view.database_loading and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.01)
    assert not view.database_loading, "Database worker did not finish"


@pytest.fixture(autouse=True)
def legacy_header_helper(monkeypatch):
    # This checkout's standalone trades_list.py calls a missing build_hdr_list.
    # Supply only that schema lookup in the test, so its original calculations
    # and formatting can serve as a comparison. The old file is never edited.
    monkeypatch.setattr(
        legacy,
        "build_hdr_list",
        lambda rows: (
            list(rows[0]) if rows else []
        ),
        raising=False,
    )


@pytest.fixture
def trades_db(tmp_path):
    path = tmp_path / "trades.db"
    rows = []
    for index, (
        strategy,
        symbol,
        pnl,
        status,
    ) in enumerate(
        [
            ("alpha", "AAA", 100.0, "closed"),
            ("alpha", "BBB", -25.0, "closed"),
            ("beta", "AAA", 50.0, "closed"),
            ("beta", "CCC", None, "open"),
        ]
    ):
        rows.append(
            {
                "trade_id": f"trade-id-with-a-long-prefix-{index}",
                "strategy_name": strategy,
                "symbol": symbol,
                "pnl": pnl,
                "status": status,
                "direction": "long",
                "quantity": index + 1,
                "entry_time": f"2026-09-{18 + index:02d}T10:00:00",
                "exit_time": (
                    f"2026-09-{18 + index:02d}T11:00:00"
                    if status == "closed"
                    else None
                ),
                "entry_price": 10.0,
                "exit_price": (
                    11.0
                    if status == "closed"
                    else None
                ),
                "fees_paid": (
                    1.0
                    if status == "closed"
                    else None
                ),
                "exit_reason": (
                    'target, "filled"'
                    if status == "closed"
                    else None
                ),
                "broker_order_id": f"order-{index}",
            }
        )
    conn = sqlite3.connect(path)
    fields = rows[0]
    definitions = ",".join(
        f'"{key}" {"REAL" if isinstance(value, (int, float)) else "TEXT"}'
        for key, value in fields.items()
    )
    conn.execute(
        f"CREATE TABLE trades ({definitions})"
    )
    placeholders = ",".join("?" for key in fields)
    conn.executemany(
        f"INSERT INTO trades VALUES ({placeholders})",
        [list(row.values()) for row in rows],
    )
    conn.execute(
        "CREATE TABLE signals (name TEXT, score REAL, state TEXT)"
    )
    conn.executemany(
        "INSERT INTO signals VALUES (?, ?, ?)",
        [
            ("alpha", 2.5, "new"),
            ("beta", 8.0, "done"),
        ],
    )
    conn.commit()
    conn.close()
    return path


def report_tool(path, options, gui=False):
    args = current.TradeAnalyzerTool.make_parser().parse_args(
        ["--db", str(path)]
        + (["--gui"] if gui else [])
        + options
    )
    tool = current.TradeAnalyzerTool.__new__(
        current.TradeAnalyzerTool
    )
    tool.initialize_report_state(args)
    return tool


@pytest.mark.parametrize(
    "options",
    [
        ["-k", "strategy_name", "-1", "ALL"],
        [
            "-k",
            "symbol",
            "-1",
            "ALL",
            "-sk",
            "pnl",
            "-R",
            "-of",
            "symbol,pnl",
        ],
        ["-k", "pnl", "-1", ">=50", "-E"],
        [
            "-k",
            "strategy_name,symbol",
            "-1",
            "alpha",
            "-2",
            "AAA",
            "-A",
        ],
        [
            "-k",
            "symbol",
            "-1",
            "ALL",
            "-s",
            "2026-09-19T00:00",
            "-e",
            "2026-09-20T23:59",
        ],
    ],
)
def test_cli_output_matches_unchanged_legacy(
    trades_db, monkeypatch, options
):
    monkeypatch.setattr(
        legacy, "DB_PATH", str(trades_db)
    )
    monkeypatch.setattr(
        sys, "argv", ["trades_list.py"] + options
    )
    before, after = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(before):
        legacy.main()
    with contextlib.redirect_stdout(after):
        report_tool(
            trades_db, options
        ).main_loop()
    assert before.getvalue() == after.getvalue()


@pytest.mark.parametrize("as_csv", [False, True])
def test_cli_file_output_matches_legacy(
    trades_db, tmp_path, monkeypatch, as_csv
):
    old_path, new_path = (
        tmp_path / "old.txt",
        tmp_path / "new.txt",
    )
    options = [
        "-k",
        "strategy_name",
        "-1",
        "ALL",
    ] + (["-csv"] if as_csv else [])
    monkeypatch.setattr(
        legacy, "DB_PATH", str(trades_db)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["trades_list.py"]
        + options
        + ["-o", str(old_path)],
    )
    legacy.main()
    report_tool(
        trades_db, options + ["-o", str(new_path)]
    ).main_loop()
    if as_csv:
        old_path, new_path = old_path.with_suffix(
            ".csv"
        ), new_path.with_suffix(".csv")
    assert (
        old_path.read_bytes()
        == new_path.read_bytes()
    )


def test_reports_repeat_and_exports_never_clobber(
    trades_db, tmp_path
):
    tool = report_tool(
        trades_db,
        [
            "-k",
            "strategy_name,symbol",
            "-1",
            "alpha",
            "-2",
            "AAA",
        ],
        gui=True,
    )
    tool.main_loop()
    first = tool.reports
    assert [
        [row["pnl"] for row in report["rows"]]
        for report in first
    ] == [[-25, 100], [50, 100]]
    tool.args.and_filter = True
    tool.main_loop()
    assert len(tool.reports) == 1
    assert [
        row["pnl"]
        for row in tool.reports[0]["rows"]
    ] == [100]
    assert (
        len(first) == 2
        and len(first[0]["rows"]) == 2
    )
    first[0]["columns"].append("exit_reason")
    paths = [
        tool.write_report_file(first[0], tmp_path)
        for _ in range(2)
    ]
    assert paths[0] != paths[1]
    with paths[0].open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        records = list(csv.reader(stream))
    assert records[3] == []
    assert records[4] == ["Report totals by group (all report rows)"]
    assert records[5] == ["Group", "Metric", "Value"]
    totals = {row[1]: row[2] for row in records[6:]}
    assert int(totals["Total Trades"]) == 2
    assert float(totals["Total P&L"]) == 75
    assert "Avg Win" in totals and "Avg Loss" in totals
    assert "\x1b" not in paths[0].read_text(encoding="utf-8-sig")
    text_path = tool.write_report_file(first[0], tmp_path, as_csv=False)
    assert "Total Trades:" in text_path.read_text()
    assert "Avg Win:" in text_path.read_text()
    assert "\x1b" not in text_path.read_text()
    assert records[1][-1] == 'target, "filled"'


def test_open_nulls_all_columns_and_empty_table(
    trades_db,
):
    tool = report_tool(
        trades_db,
        [
            "-op",
            "-k",
            "symbol",
            "-1",
            "ALL",
            "-of",
            "ALL",
            "-sk",
            "exit_price",
        ],
        gui=True,
    )
    tool.main_loop()
    assert len(tool.reports[0]["rows"]) == 1
    assert (
        tool.reports[0]["rows"][0]["exit_time"]
        is None
    )
    conn = sqlite3.connect(trades_db)
    conn.execute("DELETE FROM trades")
    conn.commit()
    conn.close()
    tool.main_loop()
    assert tool.reports[0]["rows"] == []
    assert "symbol" in tool.hdr_list


def test_generic_table_uses_selected_schema_and_filters(
    trades_db, capsys
):
    tool = report_tool(
        trades_db,
        [
            "--table",
            "signals",
            "-k",
            "score",
            "-1",
            ">=5",
            "-sk",
            "score",
        ],
    )
    tool.main_loop()
    output = capsys.readouterr().out
    assert "Table: signals" in output
    assert "Rows: 1" in output
    assert "beta\t8.0\tdone" in output
    assert "alpha\t2.5\tnew" not in output


def test_generic_table_gui_has_dynamic_columns_and_values(
    trades_db,
):
    app = current.QuickApp(size=(1250, 900))
    app.root.withdraw()
    app.report_args = current.TradeAnalyzerTool.make_parser().parse_args(
        [
            "--gui",
            "--db",
            str(trades_db),
            "--table",
            "signals",
        ]
    )
    try:
        app.set_single_tool(
            current.TradeAnalyzerTool
        )
        view = app._active_view
        app.root.update_idletasks()
        assert view.table_box.get() == "signals"
        assert view.hdr_list == [
            "name",
            "score",
            "state",
        ]
        view.keys_selector.set(["state"])
        assert view.value_boxes[0].options == [
            "ALL",
            "done",
            "new",
        ]
        view.value_boxes[0].set(["done"])
        view.on_analyze()
        wait_for_report(app, view)
        assert len(view.reports) == 1
        assert [
            row["name"]
            for row in view.reports[0]["rows"]
        ] == ["beta"]
    finally:
        app.root.destroy()


def test_bad_path_does_not_create_database(
    tmp_path,
):
    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        report_tool(
            missing, ["-k", "symbol", "-1", "ALL"]
        ).main_loop()
    assert not missing.exists()


def test_ssh_command_quotes_python_and_passes_exact_arguments(tmp_path, monkeypatch):
    # Exercise the actual Python query, including a path and table that require
    # shell quoting. The older test returned canned JSON and missed this bug.
    path = tmp_path / "Linda's report data.db"
    table = "daily report's rows"
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE "daily report\'s rows" (symbol TEXT)')
    conn.execute('INSERT INTO "daily report\'s rows" VALUES (?)', ("AAA",))
    conn.commit()
    conn.close()
    tool = report_tool(path, ["--ssh-host", "vps", "--ssh-db", str(path), "--table", table])
    real_run = current.subprocess.run

    def run_remote_command_locally(command, **kwargs):
        # Decode the POSIX shell command, then run its Python script locally.
        remote = current.shlex.split(command[-1])
        assert remote[:2] == ["python3", "-c"]
        assert remote[3:] == [str(path), table]
        return real_run([sys.executable] + remote[1:], **kwargs)

    monkeypatch.setattr(current.subprocess, "run", run_remote_command_locally)
    conn = tool.connect()
    try:
        assert conn.execute(
            "SELECT symbol FROM " + tool.quote_identifier(table)
        ).fetchone()[0] == "AAA"
        assert table in tool.remote_table_names
    finally:
        conn.close()


def test_remote_query_is_read_only_and_in_memory(
    monkeypatch,
):
    args = current.TradeAnalyzerTool.make_parser().parse_args(
        [
            "--gui",
            "--ssh-host",
            "vps",
            "--ssh-user",
            "linda",
            "--ssh-db",
            "/srv/trades.db",
        ]
    )
    tool = current.TradeAnalyzerTool.__new__(
        current.TradeAnalyzerTool
    )
    tool.initialize_report_state(args)
    calls = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = '{"columns":["symbol","status"],"rows":[["AAA","closed"]]}'

    monkeypatch.setattr(
        current.subprocess,
        "run",
        lambda command, **kwargs: calls.append(
            command
        )
        or Result(),
    )
    conn = tool.connect()
    assert (
        conn.execute(
            "SELECT * FROM trades"
        ).fetchall()[0][0]
        == "AAA"
    )
    conn.close()
    assert calls and "BatchMode=yes" in calls[0]
    assert "scp" not in calls[0]


def test_gui_switches_between_visible_ssh_and_local_settings(trades_db, monkeypatch):
    app = current.QuickApp(size=(1250, 900))
    app.root.withdraw()
    app.report_args = current.TradeAnalyzerTool.make_parser().parse_args(
        ["--gui", "--db", str(trades_db)]
    )
    calls = []

    def remote_result(command, **kwargs):
        calls.append(command)
        return current.subprocess.CompletedProcess(
            command, 0,
            '{"tables":["trades"],"columns":["strategy_name","symbol"],'
            '"rows":[["remote-only","XYZ"]]}', "",
        )

    monkeypatch.setattr(current.subprocess, "run", remote_result)
    try:
        app.set_single_tool(current.TradeAnalyzerTool)
        view = app._active_view
        assert view.values_for_field("strategy_name") == ["alpha", "beta"]
        view.option_vars["ssh_host"].set("vps")
        view.option_vars["ssh_user"].set("ronh")
        view.option_vars["ssh_db"].set("/srv/trades.db")
        view.load_database_fields()
        wait_for_database(app, view)
        assert view.values_for_field("strategy_name") == ["remote-only"]
        assert "ronh@vps" in calls[-1]

        view.option_vars["db"].set("")
        view.read_controls()  # A remote report needs no local database path.
        view.load_database_fields()
        wait_for_database(app, view)
        assert view.values_for_field("strategy_name") == ["remote-only"]

        # Reproduce a failed SSH read, then clear every SSH field and retry local.
        def failed_remote(command, **kwargs):
            return current.subprocess.CompletedProcess(
                command, 255, "", "Host key verification failed."
            )

        monkeypatch.setattr(current.subprocess, "run", failed_remote)
        view.load_database_fields()
        wait_for_database(app, view)
        assert "Host key verification failed" in view.status_var.get()
        for name in ("ssh_host", "ssh_user", "ssh_port", "ssh_db"):
            view.option_vars[name].set("")
        view.option_vars["db"].set(str(trades_db))
        view.load_database_fields()
        assert view.values_for_field("strategy_name") == ["alpha", "beta"]
        view.read_controls()
        assert view.args.ssh_host is None
        assert view.args.ssh_port is None
        assert view.table_names == ["signals", "trades"]
    finally:
        app.root.destroy()


def test_remote_startup_is_responsive_and_old_result_cannot_replace_local(trades_db, monkeypatch):
    app = current.QuickApp(size=(1250, 900))
    app.root.withdraw()
    app.report_args = current.TradeAnalyzerTool.make_parser().parse_args(
        ["--gui", "--db", str(trades_db), "--ssh-host", "vps", "--ssh-db", "/srv/trades.db"]
    )
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def delayed_remote(command, **kwargs):
        started.set()
        assert release.wait(5), "GUI startup blocked on SSH"
        return current.subprocess.CompletedProcess(
            command, 0, '{"columns":["strategy_name"],"rows":[["remote-only"]]}', ""
        )

    original_read = current.TradeAnalyzerTool.read_database_fields

    def tracked_read(tool):
        try:
            return original_read(tool)
        finally:
            if tool.args.ssh_host:
                finished.set()

    monkeypatch.setattr(current.subprocess, "run", delayed_remote)
    monkeypatch.setattr(current.TradeAnalyzerTool, "read_database_fields", tracked_read)
    try:
        app.set_single_tool(current.TradeAnalyzerTool)
        view = app._active_view
        assert started.wait(1)
        assert view.database_loading
        heartbeat = []
        app.root.after(0, lambda: heartbeat.append(True))
        app.root.update()
        assert heartbeat  # Tk can process events while SSH remains blocked.
        view.option_vars["ssh_host"].set("")
        view.load_database_fields()
        assert view.values_for_field("strategy_name") == ["alpha", "beta"]
        release.set()
        assert finished.wait(2)
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            app.root.update()
            time.sleep(0.01)
        assert view.values_for_field("strategy_name") == ["alpha", "beta"]
        assert not view.database_loading
    finally:
        release.set()
        finished.wait(2)
        app.root.destroy()


def test_real_widgets_choices_repeated_runs_sort_export_and_errors(
    trades_db, tmp_path, monkeypatch
):
    app = current.QuickApp(size=(1250, 900))
    app.root.withdraw()
    app.report_args = current.TradeAnalyzerTool.make_parser().parse_args(
        ["--gui", "--db", str(trades_db)]
    )
    errors, windows = [], []
    monkeypatch.setattr(
        current.messagebox,
        "showerror",
        lambda title, text, **kwargs: errors.append(
            text
        ),
    )
    monkeypatch.setattr(
        current.messagebox,
        "showinfo",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        current.filedialog,
        "askdirectory",
        lambda **kwargs: str(tmp_path),
    )
    try:
        app.set_single_tool(
            current.TradeAnalyzerTool
        )
        view = app._active_view
        app.root.update_idletasks()
        assert (
            not view.reports
        )  # Opening --gui alone must not run a report.
        assert app.root.winfo_reqheight() < 900
        defaults = view.make_parser().parse_args(["--gui"])
        assert defaults.ssh_host is None  # CLI defaults still select local SQLite.
        view.apply_options_to_controls(defaults)
        for name, value in current.GUI_SSH_DEFAULTS.items():
            assert view.option_vars[name].get() == value
        defaults.ssh_host = ""  # Explicit local mode is respected.
        view.apply_options_to_controls(defaults)
        assert view.option_vars["ssh_host"].get() == ""
        view.apply_options_to_controls(app.report_args)
        assert view.option_vars["ssh_host"].get() == ""
        original_open = view.open_report_window

        def open_hidden(report):
            win = original_open(report)
            win.withdraw()
            windows.append(win)
            return win

        monkeypatch.setattr(
            view,
            "open_report_window",
            open_hidden,
        )
        view.keys_selector.set(
            ["strategy_name", "symbol"]
        )
        assert [
            v.get() for v in view.key_vars[:2]
        ] == ["strategy_name", "symbol"]
        assert view.value_boxes[0].options == [
            "ALL",
            "alpha",
            "beta",
        ]
        assert view.value_boxes[1].options == [
            "ALL",
            "AAA",
            "BBB",
            "CCC",
        ]
        view.value_boxes[0].set(["alpha"])
        view.value_boxes[1].set(["AAA"])
        # Hold the worker like a slow SSH response: Tk must still process events.
        release = threading.Event()
        original_loop = current.TradeAnalyzerTool.main_loop
        def slow_loop(worker):
            assert threading.current_thread() is not threading.main_thread()
            assert release.wait(5)
            return original_loop(worker)
        monkeypatch.setattr(current.TradeAnalyzerTool, "main_loop", slow_loop)
        view.on_analyze()
        try:
            assert view.report_running
            assert str(view.run_button.cget("state")) == "disabled"
            heartbeat = []
            app.root.after(0, lambda: heartbeat.append(True))
            app.root.update()
            assert heartbeat and not windows
            view.on_analyze()  # Duplicate click must not start another report.
        finally:
            release.set()
        wait_for_report(app, view)
        monkeypatch.setattr(current.TradeAnalyzerTool, "main_loop", original_loop)
        assert str(view.run_button.cget("state")) == "normal"
        assert not errors and len(windows) == 2
        first_report = view.reports[0]
        view.option_vars["and_filter"].set(True)
        view.on_analyze()
        wait_for_report(app, view)
        assert (
            len(windows) == 3
            and len(view.reports[0]["rows"]) == 1
        )
        # Original window still has its original two rows. Heading sorting works.
        pages = next(
            w
            for w in windows[0].winfo_children()
            if isinstance(w, current.ttk.Notebook)
        )
        split = pages.winfo_children()[0]
        table = split.winfo_children()[0]
        footer = split.winfo_children()[1]
        totals = next(w for w in footer.winfo_children() if isinstance(w, current.tk.Text))
        assert "Total Trades:" in totals.get("1.0", "end")
        assert "Avg Win:" in totals.get("1.0", "end")
        assert "\x1b" not in totals.get("1.0", "end")
        assert any(totals.tag_ranges(tag) for tag in totals.tag_names() if tag.startswith("ansi_#"))
        assert "\x1b[" in "".join(first_report["text"])
        saved = view.write_report_file(first_report, tmp_path, as_csv=False)
        assert "\x1b" not in saved.read_text()
        table._sort_column("pnl")
        assert table.text.tag_ranges("negative")
        assert table.text.tag_ranges("positive")
        negative = table.text.tag_ranges("negative")
        assert table.text.get(negative[0], negative[1]) == "-25.000000"
        assert not table.text.tag_names("1.0")  # The trade ID stays neutral.
        table._search_var.set("BBB")
        assert len(table.visible_rows) == 1
        assert table.text.tag_ranges("negative")
        table._search_var.set("")
        assert [
            float(row[first_report["columns"].index("pnl")])
            for row in table.visible_rows
        ] == [-25, 100]
        assert len(first_report["rows"]) == 2
        bar = windows[0].winfo_children()[0]
        export = next(
            w
            for w in bar.winfo_children()
            if isinstance(w, current.ttk.Button)
            and w.cget("text")
            == "Export visible CSV"
        )
        export.invoke()
        assert (
            len(
                list(
                    tmp_path.glob("trades_*.csv")
                )
            )
            == 1
        )
        view.keys_selector.set(
            [
                "strategy_name",
                "symbol",
                "direction",
                "quantity",
                "pnl",
            ]
        )
        view.option_vars["and_filter"].set(False)
        view.on_analyze()
        wait_for_report(app, view)
        assert (
            len(view.reports) == 5
            and len(windows) == 8
        )
        view.keys_selector.set(
            [
                "strategy_name",
                "symbol",
                "direction",
                "quantity",
                "pnl",
                "status",
            ]
        )
        assert (
            len(
                [
                    v
                    for v in view.key_vars
                    if v.get()
                ]
            )
            == 5
        )
        view.option_vars["start"].set(
            "not a date"
        )
        view.on_analyze()
        wait_for_report(app, view)
        assert (
            errors
            and "Invalid start date" in errors[-1]
        )
        view.on_reset()
        view.on_analyze()
        wait_for_report(app, view)
        assert (
            len(view.reports) == 1
            and app.root.winfo_exists()
        )
    finally:
        app.root.destroy()
