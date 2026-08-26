"""
remove_trade.py — Safely remove a trade from ALL tables and adjust all financial state.

Usage:
  python Scripts/remove_trade.py           -- list last 50 closed trades
  python Scripts/remove_trade.py -n 100    -- list last 100 closed trades
  python Scripts/remove_trade.py --open    -- list open trades (with broker close option)
  python Scripts/remove_trade.py --open -n 30

The script will:
  1. Show a numbered list of trades
  2. Ask which trade(s) to remove (comma-separated)
  3. Show a preview of all changes
  4. Ask for confirmation
  5. Remove from: trades, settlement_queue, tax_ledger, strategy_results
  6. Adjust: capital (latest row), session_state (today), daily_summaries (trade date)
  7. For open trades: optionally cancel/close at broker first
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime, date

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "trading_bot.db",
)

ADMIN_REASONS = {
    "alpaca_account_reset",
    "duplicate_signal_close",
    "reconciled_ghost",
    "duplicate_closed",
    "manual_db_remove",
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_closed_trades(conn, n):
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY exit_time DESC LIMIT ?",
        ("closed", n),
    )
    return [dict(r) for r in c.fetchall()]


def get_open_trades(conn, n):
    c = conn.cursor()
    c.execute(
        "SELECT * FROM trades WHERE status=? ORDER BY entry_time DESC LIMIT ?",
        ("open", n),
    )
    return [dict(r) for r in c.fetchall()]


def print_closed_table(trades):
    print(
        f"\n{'#':>3}  {'ID':>5}  {'Symbol':<10}  {'Dir':<6}  {'Strategy':<22}  "
        f"{'Entry':>10}  {'Exit':>10}  {'PNL':>9}  {'Exit Reason'}"
    )
    print("-" * 110)
    for i, t in enumerate(trades, 1):
        pnl = t.get("pnl") or 0
        sign = "+" if pnl >= 0 else ""
        print(
            f"{i:>3}  {t['id']:>5}  {(t['symbol'] or '?'):<10}  "
            f"{(t['direction'] or '?').upper():<6}  "
            f"{(t['strategy_name'] or '?'):<22}  "
            f"{(t['entry_price'] or 0):>10.4f}  "
            f"{(t['exit_price'] or 0):>10.4f}  "
            f"{sign}{pnl:>8.2f}  "
            f"{t.get('exit_reason') or ''}"
        )


def print_open_table(trades):
    print(
        f"\n{'#':>3}  {'ID':>5}  {'Symbol':<10}  {'Dir':<6}  {'Strategy':<22}  "
        f"{'Entry':>10}  {'Broker':<10}  {'Entry Time'}"
    )
    print("-" * 100)
    for i, t in enumerate(trades, 1):
        print(
            f"{i:>3}  {t['id']:>5}  {(t['symbol'] or '?'):<10}  "
            f"{(t['direction'] or '?').upper():<6}  "
            f"{(t['strategy_name'] or '?'):<22}  "
            f"{(t['entry_price'] or 0):>10.4f}  "
            f"{(t['broker'] or '?'):<10}  "
            f"{t.get('entry_time') or ''}"
        )


def broker_close(trade):
    """Attempt to cancel/close the position at the broker."""
    broker = (trade.get("broker") or "").lower()
    symbol = trade["symbol"]
    trade_id = trade.get("trade_id") or ""

    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), ".."
        ),
    )

    if "alpaca" in broker:
        try:
            import config
            import alpaca_trade_api as tradeapi

            api = tradeapi.REST(
                config.ALPACA_API_KEY,
                config.ALPACA_SECRET_KEY,
                config.ALPACA_BASE_URL,
            )
            # Cancel any open orders for this symbol first
            orders = api.list_orders(
                status="open", symbols=[symbol]
            )
            cancelled = 0
            for o in orders:
                try:
                    api.cancel_order(o.id)
                    cancelled += 1
                except Exception:
                    pass
            # Close position if it exists
            try:
                api.close_position(symbol)
                print(
                    f"  [ALPACA] Closed position {symbol} at broker. Cancelled {cancelled} orders."
                )
            except Exception as e:
                print(
                    f"  [ALPACA] No position to close or error: {e}. Cancelled {cancelled} orders."
                )
        except Exception as e:
            print(
                f"  [ALPACA] Could not connect to broker: {e}"
            )

    elif "kraken" in broker:
        print(
            f"  [KRAKEN] Kraken paper mode — no broker action needed (simulated locally)."
        )

    elif "ibkr" in broker or "ib" in broker:
        print(
            f"  [IBKR] Manual close required — connect to TWS and close {symbol} manually."
        )

    else:
        print(
            f"  [BROKER] Unknown broker '{broker}' — close {symbol} manually if needed."
        )


def remove_trade(conn, trade, dry_run=False):
    """Remove trade from all tables and adjust financial state. Returns summary of changes."""
    c = conn.cursor()
    trade_id = trade["trade_id"]
    db_id = trade["id"]
    symbol = trade["symbol"]
    pnl = float(trade.get("pnl") or 0)
    status = trade.get("status")

    # Determine trade date for daily_summaries and session
    time_field = (
        "exit_time"
        if status == "closed"
        else "entry_time"
    )
    trade_dt_str = trade.get(time_field) or ""
    trade_date = (
        trade_dt_str[:10]
        if trade_dt_str
        else date.today().isoformat()
    )
    today = date.today().isoformat()

    changes = []

    # 1. trades table
    changes.append(
        f"  DELETE trades id={db_id} ({symbol} {status} pnl={pnl:+.2f})"
    )

    # 2. settlement_queue
    c.execute(
        "SELECT id, amount FROM settlement_queue WHERE trade_id=?",
        (trade_id,),
    )
    sq = c.fetchone()
    if sq:
        changes.append(
            f"  DELETE settlement_queue id={sq['id']} amount={sq['amount']:.2f}"
        )

    # 3. tax_ledger
    c.execute(
        "SELECT id, gain_loss FROM tax_ledger WHERE trade_id=?",
        (trade_id,),
    )
    tl = c.fetchone()
    if tl:
        changes.append(
            f"  DELETE tax_ledger id={tl['id']} gain_loss={tl['gain_loss']:+.2f}"
        )

    # 4. strategy_results
    strategy = trade.get("strategy_name") or ""
    if strategy and strategy not in (
        "original",
        "manual",
    ):
        c.execute(
            "SELECT id, pnl FROM strategy_results WHERE strategy_name=? AND trade_date=? AND ABS(pnl-?)<?",
            (
                strategy,
                trade_date,
                abs(pnl),
                0.01,
            ),
        )
        sr = c.fetchone()
        if sr:
            changes.append(
                f"  DELETE strategy_results id={sr['id']} strategy={strategy} pnl={sr['pnl']:+.2f}"
            )

    # 5. capital adjustment (latest row only, if pnl != 0)
    if pnl != 0 and status == "closed":
        c.execute(
            "SELECT timestamp, total_capital, daily_pnl, total_pnl FROM capital ORDER BY timestamp DESC LIMIT 1"
        )
        cap = c.fetchone()
        if cap:
            changes.append(
                f"  UPDATE capital: total_capital {cap['total_capital']:.2f} -> {cap['total_capital']-pnl:.2f}"
                f"  |  daily_pnl {cap['daily_pnl']:.2f} -> {cap['daily_pnl']-pnl:.2f}"
                f"  |  total_pnl {cap['total_pnl']:.2f} -> {cap['total_pnl']-pnl:.2f}"
            )

    # 6. session_state (today only)
    if trade_date == today and status == "closed":
        c.execute(
            "SELECT pnl_today, trades_today FROM session_state WHERE session_date=?",
            (today,),
        )
        sess = c.fetchone()
        if sess:
            won = 1 if pnl > 0 else 0
            changes.append(
                f"  UPDATE session_state: pnl_today {sess['pnl_today']:.2f} -> {sess['pnl_today']-pnl:.2f}"
                f"  |  trades_today {sess['trades_today']} -> {sess['trades_today']-1}"
            )

    # 7. daily_summaries
    c.execute(
        "SELECT * FROM daily_summaries WHERE trade_date=?",
        (trade_date,),
    )
    ds = c.fetchone()
    if ds and status == "closed":
        won = pnl > 0
        new_total = max(0, ds["total_trades"] - 1)
        new_wins = max(
            0,
            ds["winning_trades"]
            - (1 if won else 0),
        )
        new_losses = max(
            0,
            ds["losing_trades"]
            - (0 if won else 1),
        )
        new_pnl = ds["daily_pnl"] - pnl
        new_wr = (
            round(new_wins / new_total * 100, 1)
            if new_total > 0
            else 0
        )
        changes.append(
            f"  UPDATE daily_summaries {trade_date}: trades {ds['total_trades']}->{new_total}"
            f"  wins {ds['winning_trades']}->{new_wins}  losses {ds['losing_trades']}->{new_losses}"
            f"  pnl {ds['daily_pnl']:+.2f}->{new_pnl:+.2f}  wr {ds['win_rate']:.1f}%->{new_wr:.1f}%"
        )

    if dry_run:
        return changes

    # ── Apply changes ──────────────────────────────────────────────────────

    c.execute(
        "DELETE FROM trades WHERE id=?", (db_id,)
    )

    if sq:
        c.execute(
            "DELETE FROM settlement_queue WHERE trade_id=?",
            (trade_id,),
        )

    if tl:
        c.execute(
            "DELETE FROM tax_ledger WHERE trade_id=?",
            (trade_id,),
        )

    if strategy and strategy not in (
        "original",
        "manual",
    ):
        c.execute(
            "DELETE FROM strategy_results WHERE strategy_name=? AND trade_date=? AND ABS(pnl-?)<0.01",
            (strategy, trade_date, abs(pnl)),
        )

    if pnl != 0 and status == "closed":
        c.execute(
            "UPDATE capital SET total_capital=total_capital-?, daily_pnl=daily_pnl-?, total_pnl=total_pnl-? "
            "WHERE timestamp=(SELECT MAX(timestamp) FROM capital)",
            (pnl, pnl, pnl),
        )

    if trade_date == today and status == "closed":
        c.execute(
            "UPDATE session_state SET pnl_today=pnl_today-?, trades_today=MAX(0,trades_today-1) "
            "WHERE session_date=?",
            (pnl, today),
        )

    if ds and status == "closed":
        won = pnl > 0
        c.execute(
            "UPDATE daily_summaries SET "
            "total_trades=MAX(0,total_trades-1), "
            "winning_trades=MAX(0,winning_trades-?), "
            "losing_trades=MAX(0,losing_trades-?), "
            "daily_pnl=daily_pnl-?, "
            "win_rate=CASE WHEN MAX(0,total_trades-1)>0 "
            "  THEN ROUND(MAX(0,winning_trades-?)*100.0/MAX(0,total_trades-1),1) ELSE 0 END "
            "WHERE trade_date=?",
            (
                1 if won else 0,
                0 if won else 1,
                pnl,
                1 if won else 0,
                trade_date,
            ),
        )

    conn.commit()
    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Remove trades from DB and adjust all financial state."
    )
    parser.add_argument(
        "-n",
        type=int,
        default=50,
        help="Number of trades to list (default 50)",
    )
    parser.add_argument(
        "-i",
        "--id",
        metavar="",
        help="ID of trade to remove",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="List open trades instead of closed",
    )
    args = parser.parse_args()

    trade_id_to_remove = args.id if args.id else 0

    conn = connect()
    mode = "open" if args.open else "closed"
    num_records = (
        args.n
        if not trade_id_to_remove
        else 1000000000
    )
    if (
        mode == "closed"
        and not trade_id_to_remove
    ):
        trades = get_closed_trades(
            conn, num_records
        )
        if not trades:
            print("No closed trades found.")
            conn.close()
            return
        print(
            f"\nLast {len(trades)} closed trades:"
        )
        print_closed_table(trades)
    elif not trade_id_to_remove:
        trades = get_open_trades(
            conn, num_records
        )
        if not trades:
            print("No open trades found.")
            conn.close()
            return
        print(
            f"\nCurrent {len(trades)} open trades:"
        )
        print_open_table(trades)

    print()

    if trade_id_to_remove == 0:
        selection = input(
            "Enter trade number(s) to remove (comma-separated), or q to quit: "
        ).strip()
        if (
            selection.lower() == "q"
            or not selection
        ):
            print("Cancelled.")
            conn.close()
            return

        try:
            indices = [
                int(x.strip()) - 1
                for x in selection.split(",")
            ]
        except ValueError:
            print("Invalid selection.")
            conn.close()
            return

    selected = []
    if trade_id_to_remove == 0:
        for i in indices:
            if 0 <= i < len(trades):
                selected.append(trades[i])
            else:
                print(
                    f"  Warning: index {i+1} out of range, skipping."
                )
    else:
        for trade in trades:
            if (
                trade["trade_id"]
                == trade_id_to_remove
            ):
                selected.append(trade)
    if not selected:
        print("No valid trades selected.")
        conn.close()
        return

    # Show preview
    print(
        f"\nPreview — {len(selected)} trade(s) to remove:"
    )
    for t in selected:
        print(
            f'\n  [{t["id"]}] {t["symbol"]} {(t["direction"] or "").upper()} '
            f'pnl={float(t.get("pnl") or 0):+.2f} strategy={t.get("strategy_name")} '
            f'broker={t.get("broker")}'
        )
        changes = remove_trade(
            conn, t, dry_run=True
        )
        for ch in changes:
            print(ch)

    # For open trades, offer broker close
    broker_close_trades = []
    if mode == "open":
        print()
        do_broker = (
            input(
                "Also close position(s) at broker? (y/n): "
            )
            .strip()
            .lower()
        )
        if do_broker == "y":
            broker_close_trades = selected

    print()
    confirm = (
        input(
            f"Confirm removal of {len(selected)} trade(s)? (yes/no): "
        )
        .strip()
        .lower()
    )
    if confirm != "yes":
        print("Cancelled — nothing changed.")
        conn.close()
        return

    # Execute broker closes first (before DB changes)
    for t in broker_close_trades:
        print(
            f'\nClosing {t["symbol"]} at broker...'
        )
        broker_close(t)

    # Apply DB changes
    for t in selected:
        changes = remove_trade(
            conn, t, dry_run=False
        )
        print(
            f'\n  Removed [{t["id"]}] {t["symbol"]}:'
        )
        for ch in changes:
            print(ch)

    print(
        f"\nDone. {len(selected)} trade(s) removed and all tables adjusted."
    )
    conn.close()


if __name__ == "__main__":
    main()
