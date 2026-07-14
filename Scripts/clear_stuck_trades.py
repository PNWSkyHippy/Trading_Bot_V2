"""Reset STUCK close flags while preserving Kraken reconciliation holds."""

import json
import os
import sqlite3
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "trading_bot.db")


def _marker_value_is_active(raw_value):
    """Return True when a persisted bot_state marker represents an active hold."""
    try:
        value = json.loads(raw_value)
    except (TypeError, ValueError):
        value = raw_value
    if isinstance(value, str) and value.strip().lower() in {"", "0", "false", "null", "none"}:
        return False
    return bool(value)


def has_active_kraken_reconciliation_marker(conn, trade_id, symbol):
    """Return the first active Kraken reconciliation key protecting this trade."""
    keys = (
        f"kraken_partial_reconcile_{trade_id}",
        f"kraken_full_reconcile_{trade_id}",
        f"kraken_unresolved_symbol_{symbol}",
    )
    for key in keys:
        row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
        if row and _marker_value_is_active(row[0]):
            return key
    return None


def main(database_path=DEFAULT_DB_PATH, state_store=None):
    """Clear retry flags for ordinary open trades, skipping reconciliation holds."""
    if state_store is None:
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        from data.database import db as state_store

    conn = sqlite3.connect(database_path)
    try:
        rows = conn.execute("SELECT trade_id, symbol FROM trades WHERE status='open'").fetchall()
        cleared = 0
        skipped = 0
        for trade_id, symbol in rows:
            blocking_key = has_active_kraken_reconciliation_marker(conn, trade_id, symbol)
            if blocking_key:
                print(f"SKIPPED reconciliation hold: {symbol} {trade_id[:8]} ({blocking_key})")
                skipped += 1
                continue
            state_store.set_state(f"close_stuck_{trade_id}", 0)
            state_store.set_state(f"close_attempts_{trade_id}", 0)
            print(f"Reset stuck flag: {symbol} {trade_id[:8]}")
            cleared += 1
    finally:
        conn.close()

    print(f"\nDone — reset {cleared} trade(s); skipped {skipped} reconciliation hold(s).")
    return cleared, skipped


if __name__ == "__main__":
    main()
