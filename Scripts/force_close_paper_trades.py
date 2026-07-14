"""
Force database closure of crypto paper positions that have no exchange position.

Trades protected by Kraken reconciliation markers are never closed by this script;
their live fills must be reconciled first.
"""

import json
import os
import sqlite3
from datetime import datetime


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
    """Force-close unguarded open crypto rows and preserve reconciliation holds."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        open_trades = conn.execute("""
            SELECT trade_id, symbol, direction, entry_price, quantity,
                   position_value, broker
            FROM trades
            WHERE status='open' AND asset_class='crypto'
        """).fetchall()

        if not open_trades:
            print("No open crypto trades found.")
            return 0, 0

        print(f"Found {len(open_trades)} open crypto trades:\n")
        for trade in open_trades:
            print(
                f"  {trade['symbol']:12} | {trade['direction']:5} | "
                f"entry=${trade['entry_price']:.4f} | broker={trade['broker']}"
            )

        print("\nForce closing eligible paper simulations (pnl=0)...")
        print("Marker-bearing Kraken trades will be skipped for live fill reconciliation.\n")

        now = datetime.now().isoformat()
        closed = 0
        skipped = 0
        for trade in open_trades:
            trade_id = trade["trade_id"]
            symbol = trade["symbol"]
            blocking_key = has_active_kraken_reconciliation_marker(conn, trade_id, symbol)
            if blocking_key:
                print(f"  SKIPPED reconciliation hold: {symbol} {trade_id[:8]} ({blocking_key})")
                skipped += 1
                continue

            conn.execute("""
                UPDATE trades
                SET status='closed',
                    exit_price=entry_price,
                    exit_time=?,
                    exit_reason='force_close_paper',
                    pnl=0.0,
                    pnl_pct=0.0
                WHERE trade_id=?
            """, (now, trade_id))
            conn.execute("DELETE FROM bot_state WHERE key=?", (f"close_stuck_{trade_id}",))
            conn.execute("DELETE FROM bot_state WHERE key=?", (f"close_attempts_{trade_id}",))
            print(
                f"  Closed: {symbol} {trade['direction']} @ "
                f"${trade['entry_price']:.4f} (paper, pnl=$0)"
            )
            closed += 1

        conn.commit()
    finally:
        conn.close()

    print(f"\nDone — force closed {closed} paper crypto position(s); skipped {skipped} hold(s).")
    if closed:
        print("Restart the bot to clear the position monitor cache.")
    return closed, skipped


if __name__ == "__main__":
    main()
