"""Deterministic isolation tests for Kraken recovery-script reconciliation holds."""

import contextlib
import importlib.util
import io
import json
import sqlite3
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts"


def load_script(module_name, filename):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SqliteStateStore:
    """Minimal isolated stand-in for Database.set_state()."""

    def __init__(self, database_path):
        self.database_path = database_path

    def set_state(self, key, value):
        with contextlib.closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
                (key, json.dumps(value)),
            )
            conn.commit()


def seed_database(database_path):
    with contextlib.closing(sqlite3.connect(database_path)) as conn:
        conn.executescript("""
            CREATE TABLE trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                asset_class TEXT NOT NULL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                position_value REAL NOT NULL,
                broker TEXT,
                exit_price REAL,
                exit_time TEXT,
                exit_reason TEXT,
                pnl REAL,
                pnl_pct REAL
            );
            CREATE TABLE bot_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            );
        """)
        trades = (
            ("ORDINARY-1", "BTC/USD"),
            ("PARTIAL-1", "ETH/USD"),
            ("FULL-1", "SOL/USD"),
            ("SYMBOL-1", "ADA/USD"),
        )
        for trade_id, symbol in trades:
            conn.execute(
                """INSERT INTO trades
                   (trade_id, symbol, asset_class, direction, status, entry_price,
                    quantity, position_value, broker)
                   VALUES (?, ?, 'crypto', 'long', 'open', 100, 1, 100, 'kraken')""",
                (trade_id, symbol),
            )
            for prefix in ("close_stuck_", "close_attempts_", "close_last_attempt_"):
                conn.execute(
                    "INSERT INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
                    (f"{prefix}{trade_id}", json.dumps(1)),
                )

        # Explicit zero proves a cleared marker does not block an ordinary recovery.
        conn.execute(
            "INSERT INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
            ("kraken_partial_reconcile_ORDINARY-1", json.dumps(0)),
        )
        conn.execute(
            "INSERT INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
            ("kraken_partial_reconcile_PARTIAL-1", json.dumps({"required": True})),
        )
        conn.execute(
            "INSERT INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
            ("kraken_full_reconcile_FULL-1", json.dumps(1)),
        )
        conn.execute(
            "INSERT INTO bot_state (key, value, updated) VALUES (?, ?, 'test')",
            ("kraken_unresolved_symbol_ADA/USD", json.dumps({"required": True})),
        )
        conn.commit()


def state_value(database_path, key):
    with contextlib.closing(sqlite3.connect(database_path)) as conn:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    return None if row is None else json.loads(row[0])


def trade_status(database_path, trade_id):
    with contextlib.closing(sqlite3.connect(database_path)) as conn:
        return conn.execute(
            "SELECT status FROM trades WHERE trade_id=?", (trade_id,)
        ).fetchone()[0]


def assert_guarded_trades_unchanged(database_path):
    for trade_id in ("PARTIAL-1", "FULL-1", "SYMBOL-1"):
        assert trade_status(database_path, trade_id) == "open"
        assert state_value(database_path, f"close_stuck_{trade_id}") == 1
        assert state_value(database_path, f"close_attempts_{trade_id}") == 1
        assert state_value(database_path, f"close_last_attempt_{trade_id}") == 1

    assert state_value(database_path, "kraken_partial_reconcile_PARTIAL-1") == {"required": True}
    assert state_value(database_path, "kraken_full_reconcile_FULL-1") == 1
    assert state_value(database_path, "kraken_unresolved_symbol_ADA/USD") == {"required": True}


def run_with_output(callable_):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = callable_()
    text = output.getvalue()
    assert "kraken_partial_reconcile_PARTIAL-1" in text
    assert "kraken_full_reconcile_FULL-1" in text
    assert "kraken_unresolved_symbol_ADA/USD" in text
    return result


def test_clear_stuck_set_state_script(module, database_path):
    result = run_with_output(
        lambda: module.main(database_path, SqliteStateStore(database_path))
    )
    assert result == (1, 3)
    assert trade_status(database_path, "ORDINARY-1") == "open"
    assert state_value(database_path, "close_stuck_ORDINARY-1") == 0
    assert state_value(database_path, "close_attempts_ORDINARY-1") == 0
    assert state_value(database_path, "close_last_attempt_ORDINARY-1") == 1
    assert_guarded_trades_unchanged(database_path)


def test_clear_stuck_delete_script(module, database_path):
    result = run_with_output(lambda: module.main(database_path))
    assert result == (1, 3)
    assert trade_status(database_path, "ORDINARY-1") == "open"
    assert state_value(database_path, "close_stuck_ORDINARY-1") is None
    assert state_value(database_path, "close_attempts_ORDINARY-1") is None
    assert state_value(database_path, "close_last_attempt_ORDINARY-1") is None
    assert_guarded_trades_unchanged(database_path)


def test_force_close_script(module, database_path):
    result = run_with_output(lambda: module.main(database_path))
    assert result == (1, 3)
    assert trade_status(database_path, "ORDINARY-1") == "closed"
    assert state_value(database_path, "close_stuck_ORDINARY-1") is None
    assert state_value(database_path, "close_attempts_ORDINARY-1") is None
    assert_guarded_trades_unchanged(database_path)


def main():
    clear_set = load_script("clear_stuck_set_state_test", "clear_stuck_trades.py")
    clear_delete = load_script("clear_stuck_delete_test", "ClearStuckTrades.py")
    force_close = load_script("force_close_paper_test", "force_close_paper_trades.py")
    cases = (
        ("clear_stuck_trades.py", clear_set, test_clear_stuck_set_state_script),
        ("ClearStuckTrades.py", clear_delete, test_clear_stuck_delete_script),
        ("force_close_paper_trades.py", force_close, test_force_close_script),
    )
    for label, module, test in cases:
        with tempfile.TemporaryDirectory(prefix="recovery-guard-") as temp_dir:
            database_path = str(Path(temp_dir) / "test.db")
            seed_database(database_path)
            test(module, database_path)
            print(f"PASS: {label}")
    print("3/3 recovery reconciliation guard tests passed")


if __name__ == "__main__":
    main()
