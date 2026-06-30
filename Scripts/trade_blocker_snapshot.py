#!/usr/bin/env python3
"""
Fast live-trading blockage snapshot.

Run from the repo root on the active server:
    python Scripts/trade_blocker_snapshot.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import date, datetime
from pathlib import Path


DEFAULT_PATTERNS = (
    "[SCHED]",
    "skipped; previous run still active",
    "Crypto scan",
    "Signal REJECTED",
    "CHECKLIST REJECTED",
    "Trade rejected",
    "Trading halted",
    "daily loss",
    "consecutive",
    "insufficient",
    "ModuleNotFoundError",
    "Traceback",
    "ERROR",
)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _json_value(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _print_rows(title: str, rows, limit: int = 20) -> None:
    print(f"\n== {title} ==")
    if not rows:
        print("(none)")
        return
    for row in list(rows)[:limit]:
        if isinstance(row, sqlite3.Row):
            row = dict(row)
        print(row)


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    if not path.exists():
        return []
    with path.open("rb") as f:
        f.seek(0, 2)
        end = f.tell()
        block = 8192
        data = b""
        while end > 0 and data.count(b"\n") <= max_lines:
            step = min(block, end)
            end -= step
            f.seek(end)
            data = f.read(step) + data
    return data.decode("utf-8", errors="replace").splitlines()[-max_lines:]


def _scan_log(path: Path, max_lines: int, patterns: tuple[str, ...]) -> list[str]:
    lines = _tail_lines(path, max_lines)
    hits = []
    for line in lines:
        lower = line.lower()
        if any(pattern.lower() in lower for pattern in patterns):
            hits.append(line)
    return hits[-80:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Show why the bot may not be taking trades.")
    parser.add_argument("--db", default="data/trading_bot.db")
    parser.add_argument("--logs", default="logs")
    parser.add_argument("--lines", type=int, default=6000)
    args = parser.parse_args()

    root = Path.cwd()
    db_path = (root / args.db).resolve()
    log_dir = (root / args.logs).resolve()
    today = date.today().isoformat()

    print("== snapshot ==")
    print(f"time_local={datetime.now().isoformat(timespec='seconds')}")
    print(f"repo={root}")
    print(f"db={db_path} exists={db_path.exists()}")
    print(f"logs={log_dir} exists={log_dir.exists()}")

    if not db_path.exists():
        print("\nDB not found; run from repo root or pass --db.")
        return 2

    with _connect(db_path) as conn:
        session = conn.execute(
            "SELECT * FROM session_state WHERE session_date=?", (today,)
        ).fetchone()
        _print_rows(f"session_state {today}", [session] if session else [])

        scanner_keys = (
            "breakout_scanner_enabled",
            "scanner_funding_scanner_enabled",
            "scanner_gap_scanner_enabled",
            "scanner_nr7_scanner_enabled",
            "scanner_volume_surge_enabled",
        )
        rows = conn.execute(
            f"SELECT key, value, updated FROM bot_state WHERE key IN ({','.join('?' for _ in scanner_keys)}) "
            "ORDER BY key",
            scanner_keys,
        ).fetchall()
        scanner_rows = []
        for row in rows:
            item = dict(row)
            item["value"] = _json_value(item["value"])
            scanner_rows.append(item)
        _print_rows("scanner toggles", scanner_rows)

        enabled_rows = conn.execute(
            "SELECT key, value, updated FROM bot_state "
            "WHERE key LIKE 'strategy_%_enabled' ORDER BY key"
        ).fetchall()
        strategies = []
        for row in enabled_rows:
            item = dict(row)
            item["value"] = _json_value(item["value"])
            strategies.append(item)
        _print_rows("strategy enable flags", strategies, limit=60)

        open_trades = conn.execute(
            "SELECT trade_id, symbol, asset_class, direction, status, entry_time, strategy_name, broker "
            "FROM trades WHERE status='open' ORDER BY entry_time DESC LIMIT 50"
        ).fetchall()
        _print_rows("open trades", open_trades, limit=50)

        today_entries = conn.execute(
            "SELECT trade_id, symbol, asset_class, direction, status, entry_time, exit_time, strategy_name, broker, pnl "
            "FROM trades WHERE date(entry_time)=? ORDER BY entry_time DESC LIMIT 80",
            (today,),
        ).fetchall()
        _print_rows(f"entries today {today}", today_entries, limit=80)

        closed_today = conn.execute(
            "SELECT trade_id, symbol, asset_class, direction, exit_time, strategy_name, broker, pnl, exit_reason "
            "FROM trades WHERE status='closed' AND date(exit_time)=? ORDER BY exit_time DESC LIMIT 80",
            (today,),
        ).fetchall()
        _print_rows(f"closed today {today}", closed_today, limit=80)

    print("\n== recent log signals ==")
    for name in ("bot.log", "scanner_signals.log"):
        path = log_dir / name
        hits = _scan_log(path, args.lines, DEFAULT_PATTERNS)
        print(f"\n-- {name} last {args.lines} lines, hits={len(hits)} --")
        counts = Counter()
        for line in hits:
            for pattern in DEFAULT_PATTERNS:
                if pattern.lower() in line.lower():
                    counts[pattern] += 1
        if counts:
            print("counts:", dict(counts.most_common()))
        for line in hits[-40:]:
            print(line)

    print("\n== quick read ==")
    print("If you see many 'skipped; previous run still active', scans are wedged/too slow.")
    print("If session_state trading_halted=1, unhalt before expecting trades.")
    print("If signals are CHECKLIST/Trade rejected, the bot is alive but filters/risk are blocking.")
    print("If there are no Crypto scan lines, scheduler/service is not running the crypto job.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
