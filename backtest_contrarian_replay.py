#!/usr/bin/env python3
"""backtest_contrarian_replay.py — paper-only contrarian replay for breakout trades.

Mirrors the contrarian rule already implemented in the live bot
(core/breakout_receiver.py): after a signal passes its checklist, a long
signal becomes a short and a short becomes a long. This script applies
that same direction flip to a set of already-closed trades and reports
what the day would have looked like with every signal inverted.

PAPER ONLY. This script:
  - never imports any bot module (no config, no receiver, no database),
  - never opens a database, never places an order, never touches live
    trading state,
  - only reads the trade file you point it at and prints a comparison.

It replays at identical entry/exit prices: an inverted trade's profit
is the negation of the original trade's profit. That is a first-order
approximation. In real trading a flipped signal would hit different
stop-loss / take-profit levels, spreads, and fees, so a flipped trade
would not necessarily exit at the mirrored price. Treat the inverted
column as a what-if replay, not as a prediction.

Input file format (JSON), two accepted shapes:

  1. Per-trade rows (preferred — rerun this script against a per-trade
     export from the bot database whenever one is available):

         {
           "date": "2026-10-19",
           "strategy": "breakout_scanner",
           "asset_class": "crypto",
           "trades": [
             {"symbol": "UMXM/USD", "direction": "long", "pnl": -106.86},
             {"symbol": "PHA/USD",  "direction": "short", "pnl": 42.10}
           ]
         }

  2. Aggregate groups (used when only day totals are available, as for
     2026-10-19 — see backtest_data/oct19_crypto_breakout.json). Each
     group carries its own win/loss split so the inverted win rate is
     exact, not estimated:

         {
           "date": "2026-10-19",
           "strategy": "breakout_scanner",
           "asset_class": "crypto",
           "groups": [
             {"label": "UMXM/USD", "trades": 1, "wins": 0, "losses": 1,
              "net_pnl": -106.86},
             {"label": "Other 9 trades", "trades": 9, "wins": 4, "losses": 5,
              "net_pnl": -0.56}
           ]
         }

A trade counts as a win when pnl > 0 and a loss when pnl < 0. A pnl of
exactly 0 counts as breakeven and changes neither the win nor the loss
count.

Usage (from the repository root):

    python backtest_contrarian_replay.py
    python backtest_contrarian_replay.py --data backtest_data/oct19_crypto_breakout.json
    python backtest_contrarian_replay.py --data my_export.json
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parent / "backtest_data" / "oct19_crypto_breakout.json"


def flip_direction(direction):
    """Mirror the receiver's flip: long -> short, short -> long."""
    lowered = str(direction).strip().lower()
    if lowered == "long":
        return "short"
    if lowered == "short":
        return "long"
    raise ValueError("direction must be 'long' or 'short', got %r" % (direction,))


def summarize_trades(trades):
    """Actual vs inverted summary for a list of per-trade rows."""
    actual = {"trades": 0, "wins": 0, "losses": 0, "breakeven": 0, "net_pnl": 0.0}
    inverted = {"trades": 0, "wins": 0, "losses": 0, "breakeven": 0, "net_pnl": 0.0}
    rows = []
    for trade in trades:
        pnl = float(trade["pnl"])
        flipped_pnl = -pnl
        rows.append({
            "symbol": trade.get("symbol", "?"),
            "actual_direction": trade["direction"],
            "inverted_direction": flip_direction(trade["direction"]),
            "actual_pnl": pnl,
            "inverted_pnl": flipped_pnl,
        })
        for summary, value in ((actual, pnl), (inverted, flipped_pnl)):
            summary["trades"] += 1
            summary["net_pnl"] += value
            if value > 0:
                summary["wins"] += 1
            elif value < 0:
                summary["losses"] += 1
            else:
                summary["breakeven"] += 1
    return rows, actual, inverted


def summarize_groups(groups):
    """Actual vs inverted summary for aggregate groups.

    Flipping a group swaps its wins and losses and negates its net P&L.
    The group split must already be known; nothing here estimates it.
    """
    actual = {"trades": 0, "wins": 0, "losses": 0, "breakeven": 0, "net_pnl": 0.0}
    inverted = {"trades": 0, "wins": 0, "losses": 0, "breakeven": 0, "net_pnl": 0.0}
    rows = []
    for group in groups:
        trades = int(group["trades"])
        wins = int(group["wins"])
        losses = int(group["losses"])
        breakeven = trades - wins - losses
        if breakeven < 0:
            raise ValueError(
                "group %r: wins + losses exceeds trades" % (group.get("label", "?"),)
            )
        net = float(group["net_pnl"])
        rows.append({
            "label": group.get("label", "?"),
            "actual": {"trades": trades, "wins": wins, "losses": losses,
                       "breakeven": breakeven, "net_pnl": net},
            "inverted": {"trades": trades, "wins": losses, "losses": wins,
                         "breakeven": breakeven, "net_pnl": -net},
        })
        actual["trades"] += trades
        actual["wins"] += wins
        actual["losses"] += losses
        actual["breakeven"] += breakeven
        actual["net_pnl"] += net
        inverted["trades"] += trades
        inverted["wins"] += losses
        inverted["losses"] += wins
        inverted["breakeven"] += breakeven
        inverted["net_pnl"] += -net
    return rows, actual, inverted


def win_rate(summary):
    decided = summary["wins"] + summary["losses"]
    if decided == 0:
        return 0.0
    return 100.0 * summary["wins"] / decided


def money(value):
    sign = "-" if value < 0 else ""
    return "%s$%.2f" % (sign, abs(value))


def print_summary(title, summary):
    print("%-12s %6d trades  %3dW / %3dL  (win rate %5.1f%%)  net %s" % (
        title,
        summary["trades"],
        summary["wins"],
        summary["losses"],
        win_rate(summary),
        money(summary["net_pnl"]),
    ))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Paper-only contrarian replay: invert breakout signals "
                    "and compare against the actual outcome."
    )
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA),
        help="JSON file of trades or aggregate groups (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    data_path = Path(args.data)
    if not data_path.exists():
        print("ERROR: trade file not found: %s" % (data_path,), file=sys.stderr)
        return 2
    with open(data_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    print("=" * 72)
    print("CONTRARIAN REPLAY — PAPER ONLY, NOT LIVE PERFORMANCE")
    print("=" * 72)
    print("Date:         %s" % (data.get("date", "unknown"),))
    print("Strategy:     %s" % (data.get("strategy", "unknown"),))
    print("Asset class:  %s" % (data.get("asset_class", "unknown"),))
    print("Source file:  %s" % (data_path,))
    if data.get("provenance"):
        print("Provenance:   %s" % (data["provenance"],))
    print("-" * 72)

    if "trades" in data:
        rows, actual, inverted = summarize_trades(data["trades"])
        print("%-12s %-8s %-8s %12s %12s" % (
            "Symbol", "Actual", "Inverted", "Actual P&L", "Inverted P&L"))
        for row in rows:
            print("%-12s %-8s %-8s %12s %12s" % (
                row["symbol"],
                row["actual_direction"],
                row["inverted_direction"],
                money(row["actual_pnl"]),
                money(row["inverted_pnl"]),
            ))
    elif "groups" in data:
        rows, actual, inverted = summarize_groups(data["groups"])
        print("%-16s %22s %22s" % ("Group", "Actual", "Inverted"))
        for row in rows:
            a = row["actual"]
            inv = row["inverted"]
            print("%-16s %3dW/%3dL %10s %3dW/%3dL %10s" % (
                row["label"],
                a["wins"], a["losses"], money(a["net_pnl"]),
                inv["wins"], inv["losses"], money(inv["net_pnl"]),
            ))
    else:
        print("ERROR: file must contain a 'trades' list or a 'groups' list.",
              file=sys.stderr)
        return 2

    print("-" * 72)
    print_summary("Actual:", actual)
    print_summary("Inverted:", inverted)
    print("Swing (inverted - actual): %s" % (
        money(inverted["net_pnl"] - actual["net_pnl"]),))
    print("-" * 72)
    print("Caveats: inverted P&L assumes identical entry/exit prices with")
    print("the direction flipped. Real flipped trades would face different")
    print("stop-loss / take-profit triggers, spreads, and fees, and the")
    print("live receiver also clears a flipped trade's structural stop.")
    print("This replay is a what-if test, not a promise of future profit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
