"""
ClearStuckTrades.py
====================
Resets STUCK flags and close attempt counters for ordinary open trades.
Trades protected by Kraken reconciliation markers are left unchanged.

Run this FIRST before force-close scripts when trades get stuck.

Usage:
    python Scripts/ClearStuckTrades.py
"""

import json
import os
import sqlite3


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


def main(database_path=DEFAULT_DB_PATH):
    """Delete retry flags for ordinary trades, preserving reconciliation holds."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT trade_id, symbol FROM trades WHERE status='open'"
        ).fetchall()

        if not rows:
            print("No open trades found — nothing to reset.")
            return 0, 0

        cleared = 0
        skipped = 0
        for row in rows:
            trade_id = row["trade_id"]
            symbol = row["symbol"]
            blocking_key = has_active_kraken_reconciliation_marker(conn, trade_id, symbol)
            if blocking_key:
                print(f"SKIPPED reconciliation hold: {symbol} {trade_id[:8]} ({blocking_key})")
                skipped += 1
                continue

            conn.execute(
                "DELETE FROM bot_state WHERE key IN (?, ?, ?)",
                (
                    f"close_stuck_{trade_id}",
                    f"close_attempts_{trade_id}",
                    f"close_last_attempt_{trade_id}",
                ),
            )
            print(f"Reset stuck flag: {symbol} {trade_id[:8]}")
            cleared += 1

        conn.commit()
    finally:
        conn.close()

    print(f"\nDone — reset {cleared} trade(s); skipped {skipped} reconciliation hold(s).")
    if cleared:
        print("Restart the bot — position monitor will retry closes within 30s.")
    return cleared, skipped


if __name__ == "__main__":
    main()
