"""Backfill missing EAT/EMT futures fees and apply their accounting deltas.

Usage:
    venv312\\Scripts\\python.exe Scripts\\backfill_eat_emt_fees.py
    venv312\\Scripts\\python.exe Scripts\\backfill_eat_emt_fees.py --apply

The default is a read-only preview.  ``--apply`` creates a timestamped SQLite
backup beside the database, then updates only closed EAT/EMT rows whose
``fees_paid`` is still zero.  It uses the same dependent-record scope as
``Scripts/remove_trade.py`` without deleting any trade.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ninjatrader_bridge.futures_fees import futures_product_root, tradovate_round_trip_fee


REQUIRED_COLUMNS = {
    "trades": {"id", "trade_id", "strategy_name", "status", "symbol", "quantity", "pnl", "pnl_pct", "fees_paid", "position_value", "entry_time", "exit_time", "entry_price", "exit_price"},
    "settlement_queue": {"trade_id", "amount"},
    "tax_ledger": {"trade_id", "symbol", "open_date", "close_date", "proceeds", "cost_basis", "fees_paid", "gain_loss", "hold_days", "term", "tax_year"},
    "strategy_results": {"id", "strategy_name", "trade_date", "pnl", "won"},
    "capital": {"id", "total_capital", "daily_pnl", "total_pnl"},
    "session_state": {"session_date", "pnl_today"},
    "daily_summaries": {"trade_date", "daily_pnl", "fees_paid", "total_trades", "winning_trades", "losing_trades", "win_rate"},
}


def validate_schema(conn: sqlite3.Connection) -> None:
    """Fail before mutation if this database differs from the expected schema."""
    for table, required in REQUIRED_COLUMNS.items():
        actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        missing = required - actual
        if missing:
            raise RuntimeError(f"{table} is missing required columns: {sorted(missing)}")


def trade_date(trade: sqlite3.Row) -> str:
    value = trade["exit_time"] or trade["entry_time"]
    if not value:
        raise ValueError(f"Trade {trade['trade_id']} has no entry or exit time")
    return str(value)[:10]


def tax_values(trade: sqlite3.Row, fee: float) -> tuple[float, float, float]:
    """Use the repository's existing tax-ledger price-basis convention."""
    quantity = float(trade["quantity"])
    proceeds = round(float(trade["exit_price"]) * quantity, 4)
    cost_basis = round(float(trade["entry_price"]) * quantity, 4)
    return proceeds, cost_basis, round(proceeds - cost_basis - fee, 4)


def build_plan(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT * FROM trades
        WHERE status='closed'
          AND lower(COALESCE(strategy_name, '')) IN ('eat', 'emt')
          AND ABS(COALESCE(fees_paid, 0)) < 0.000001
        ORDER BY id
    """).fetchall()
    plan = []
    for trade in rows:
        fee = tradovate_round_trip_fee(trade["symbol"], trade["quantity"])
        old_pnl = float(trade["pnl"] or 0.0)
        new_pnl = round(old_pnl - fee, 4)
        position_value = float(trade["position_value"] or 0.0)
        new_pnl_pct = round(new_pnl / position_value * 100.0, 4) if position_value else 0.0
        plan.append({
            "trade": trade,
            "root": futures_product_root(trade["symbol"]),
            "date": trade_date(trade),
            "fee": fee,
            "old_pnl": old_pnl,
            "new_pnl": new_pnl,
            "new_pnl_pct": new_pnl_pct,
            "pnl_delta": round(new_pnl - old_pnl, 4),
        })
    return plan


def preview(conn: sqlite3.Connection, plan: list[dict]) -> dict:
    totals = defaultdict(lambda: {"trades": 0, "contracts": 0.0, "fees": 0.0, "pnl_delta": 0.0})
    daily = defaultdict(lambda: {"fees": 0.0, "pnl_delta": 0.0, "wins_to_losses": 0, "losses_to_wins": 0})
    tax_existing = tax_missing = settlement_rows = strategy_rows = 0
    today = date.today().isoformat()
    session_delta = 0.0
    for item in plan:
        trade = item["trade"]
        group = totals[item["root"]]
        group["trades"] += 1
        group["contracts"] += float(trade["quantity"])
        group["fees"] += item["fee"]
        group["pnl_delta"] += item["pnl_delta"]
        day = daily[item["date"]]
        day["fees"] += item["fee"]
        day["pnl_delta"] += item["pnl_delta"]
        if item["old_pnl"] > 0 >= item["new_pnl"]:
            day["wins_to_losses"] += 1
        elif item["old_pnl"] <= 0 < item["new_pnl"]:
            day["losses_to_wins"] += 1
        tax_count = conn.execute("SELECT COUNT(*) FROM tax_ledger WHERE trade_id=?", (trade["trade_id"],)).fetchone()[0]
        tax_existing += tax_count
        tax_missing += int(tax_count == 0)
        settlement_rows += conn.execute("SELECT COUNT(*) FROM settlement_queue WHERE trade_id=?", (trade["trade_id"],)).fetchone()[0]
        strategy_rows += conn.execute(
            "SELECT COUNT(*) FROM strategy_results WHERE lower(strategy_name)=? AND trade_date=? AND ABS(pnl-?)<0.01",
            (str(trade["strategy_name"]).lower(), item["date"], item["old_pnl"]),
        ).fetchone()[0]
        if item["date"] == today:
            session_delta += item["pnl_delta"]
    total_fee = round(sum(item["fee"] for item in plan), 4)
    total_delta = round(sum(item["pnl_delta"] for item in plan), 4)
    print(f"Eligible closed EAT/EMT trades: {len(plan)}")
    print(f"Contracts: {sum(float(item['trade']['quantity']) for item in plan):.0f}")
    print(f"Gross P&L correction: {total_delta:+.2f} | fees to record: ${total_fee:,.2f}")
    print("\nPer contract root (round trip):")
    for root in sorted(totals):
        item = totals[root]
        print(f"  {root:<4} trades={item['trades']:>3} contracts={item['contracts']:>6.0f} "
              f"fees=${item['fees']:>8.2f} pnl_delta={item['pnl_delta']:+9.2f}")
    print("\nDependent records:")
    print(f"  trades:            {len(plan)} UPDATE fees_paid, pnl, pnl_pct")
    print(f"  settlement_queue:  {settlement_rows} amount updates")
    print(f"  tax_ledger:        {tax_existing} existing updates; {tax_missing} missing rows inserted")
    print(f"  strategy_results:  {strategy_rows} unambiguous matching updates")
    print(f"  capital:           latest row adjusted by {total_delta:+.2f}")
    print(f"  session_state:     today's P&L delta {session_delta:+.2f}")
    print(f"  daily_summaries:   {len(daily)} date aggregates updated")
    return {"daily": daily, "total_fee": total_fee, "total_delta": total_delta}


def apply_plan(conn: sqlite3.Connection, plan: list[dict], summary: dict) -> None:
    daily = summary["daily"]
    today = date.today().isoformat()
    for item in plan:
        trade = item["trade"]
        conn.execute(
            "UPDATE trades SET fees_paid=?, pnl=?, pnl_pct=? WHERE id=?",
            (item["fee"], item["new_pnl"], item["new_pnl_pct"], trade["id"]),
        )
        conn.execute(
            "UPDATE settlement_queue SET amount=amount+? WHERE trade_id=?",
            (item["pnl_delta"], trade["trade_id"]),
        )
        tax_rows = conn.execute("SELECT id FROM tax_ledger WHERE trade_id=?", (trade["trade_id"],)).fetchall()
        if tax_rows:
            # Preserve the existing ledger's proceeds/cost basis and apply only
            # the missing fee delta, so historical basis is not silently rewritten.
            conn.execute(
                "UPDATE tax_ledger SET fees_paid=fees_paid+?, gain_loss=gain_loss+? WHERE trade_id=?",
                (item["fee"], item["pnl_delta"], trade["trade_id"]),
            )
        else:
            proceeds, cost_basis, gain_loss = tax_values(trade, item["fee"])
            entry_date = str(trade["entry_time"])[:10]
            exit_date = item["date"]
            hold_days = max(0, (datetime.fromisoformat(exit_date).date() - datetime.fromisoformat(entry_date).date()).days)
            conn.execute(
                """INSERT INTO tax_ledger
                   (trade_id, symbol, open_date, close_date, proceeds, cost_basis,
                    fees_paid, gain_loss, hold_days, term, tax_year)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trade["trade_id"], trade["symbol"], entry_date, exit_date,
                 proceeds, cost_basis, item["fee"], gain_loss, hold_days,
                 "long" if hold_days >= 365 else "short", int(exit_date[:4])),
            )
        matches = conn.execute(
            "SELECT id FROM strategy_results WHERE lower(strategy_name)=? AND trade_date=? AND ABS(pnl-?)<0.01",
            (str(trade["strategy_name"]).lower(), item["date"], item["old_pnl"]),
        ).fetchall()
        if len(matches) == 1:
            conn.execute(
                "UPDATE strategy_results SET pnl=?, won=? WHERE id=?",
                (item["new_pnl"], int(item["new_pnl"] > 0), matches[0]["id"]),
            )
    for day, delta in daily.items():
        row = conn.execute("SELECT total_trades, winning_trades, losing_trades FROM daily_summaries WHERE trade_date=?", (day,)).fetchone()
        if not row:
            continue
        wins = max(0, int(row["winning_trades"] or 0) - delta["wins_to_losses"] + delta["losses_to_wins"])
        losses = max(0, int(row["losing_trades"] or 0) + delta["wins_to_losses"] - delta["losses_to_wins"])
        total = int(row["total_trades"] or 0)
        conn.execute(
            """UPDATE daily_summaries
               SET daily_pnl=daily_pnl+?, fees_paid=fees_paid+?,
                   winning_trades=?, losing_trades=?,
                   win_rate=CASE WHEN ? > 0 THEN ROUND(? * 100.0 / ?, 1) ELSE 0 END
               WHERE trade_date=?""",
            (delta["pnl_delta"], delta["fees"], wins, losses, total, wins, total, day),
        )
    if summary["total_delta"]:
        conn.execute(
            """UPDATE capital
               SET total_capital=total_capital+?, daily_pnl=daily_pnl+?, total_pnl=total_pnl+?
               WHERE id=(SELECT id FROM capital ORDER BY timestamp DESC, id DESC LIMIT 1)""",
            (summary["total_delta"], summary["total_delta"], summary["total_delta"]),
        )
    today_delta = daily.get(today, {}).get("pnl_delta", 0.0)
    if today_delta:
        conn.execute("UPDATE session_state SET pnl_today=pnl_today+? WHERE session_date=?", (today_delta, today))


def backup_path(database: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    directory = database.parent / "backups"
    directory.mkdir(exist_ok=True)
    return directory / f"{database.stem}.before_eat_emt_fee_backfill-{stamp}{database.suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "trading_bot.db")
    parser.add_argument("--apply", action="store_true", help="Back up and apply the displayed correction")
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"Database not found: {database}")
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        validate_schema(conn)
        plan = build_plan(conn)
        summary = preview(conn, plan)
        if not args.apply:
            print("\nPreview only. Re-run with --apply to create a backup and apply this exact plan.")
            return
        if not plan:
            print("\nNothing to apply.")
            return
        destination = backup_path(database)
        shutil.copy2(database, destination)
        try:
            conn.execute("BEGIN IMMEDIATE")
            apply_plan(conn, plan, summary)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        print(f"\nApplied {len(plan)} fee corrections. Backup: {destination}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
