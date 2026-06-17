r"""
Remove one symbol from the candle cache across all stored timeframes.

Examples:
  venv312\Scripts\python.exe Scripts\flush_candle_symbol.py --symbol CRM --dry-run
  venv312\Scripts\python.exe Scripts\flush_candle_symbol.py --symbol CRM
  venv312\Scripts\python.exe Scripts\flush_candle_symbol.py --symbol BTC/USD
  venv312\Scripts\python.exe Scripts\flush_candle_symbol.py --symbol CRM --timeframe 5m
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from typing import List


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

_DB_PATH = os.path.join(_PROJECT_ROOT, "data", "candle_store.db")


@dataclass
class MatchRow:
    symbol: str
    timeframe: str
    bar_count: int
    first_ts: int | None
    last_ts: int | None


def _candidate_symbols(raw_symbol: str) -> List[str]:
    sym = raw_symbol.strip()
    if not sym:
        return []
    upper = sym.upper()
    candidates = [upper]
    if "/" not in upper:
        candidates.append(f"{upper}/stock")
    return candidates


def _load_matches(conn: sqlite3.Connection, symbols: List[str], timeframe: str | None) -> List[MatchRow]:
    placeholders = ",".join("?" for _ in symbols)
    sql = f"""
        SELECT symbol, timeframe, bar_count, first_ts, last_ts
        FROM candle_meta
        WHERE symbol IN ({placeholders})
    """
    params: List[object] = list(symbols)
    if timeframe:
        sql += " AND timeframe = ?"
        params.append(timeframe)
    sql += " ORDER BY symbol, timeframe"

    rows = conn.execute(sql, params).fetchall()
    return [MatchRow(*row) for row in rows]


def _fallback_matches_from_candles(conn: sqlite3.Connection, symbols: List[str], timeframe: str | None) -> List[MatchRow]:
    placeholders = ",".join("?" for _ in symbols)
    sql = f"""
        SELECT symbol, timeframe, COUNT(*) AS bar_count, MIN(ts) AS first_ts, MAX(ts) AS last_ts
        FROM candles
        WHERE symbol IN ({placeholders})
    """
    params: List[object] = list(symbols)
    if timeframe:
        sql += " AND timeframe = ?"
        params.append(timeframe)
    sql += " GROUP BY symbol, timeframe ORDER BY symbol, timeframe"

    rows = conn.execute(sql, params).fetchall()
    return [MatchRow(*row) for row in rows]


def _format_ts(ts: int | None) -> str:
    return str(ts) if ts is not None else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description="Flush one symbol from candle_store.db.")
    parser.add_argument("--symbol", required=True, help="Symbol to purge, e.g. CRM or BTC/USD")
    parser.add_argument("--timeframe", default="", help="Optional timeframe filter, e.g. 5m or 1h")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    parser.add_argument(
        "--keep-registry",
        action="store_true",
        help="Keep symbol_source_registry rows instead of clearing them",
    )
    args = parser.parse_args()

    if not os.path.exists(_DB_PATH):
        print(f"[ERROR] DB not found at {_DB_PATH}")
        return 1

    timeframe = args.timeframe.strip() or None
    symbols = _candidate_symbols(args.symbol)
    if not symbols:
        print("[ERROR] Empty symbol")
        return 1

    print(f"\n  Candle flush target : {args.symbol.strip().upper()}")
    print(f"  Candidate keys      : {', '.join(symbols)}")
    print(f"  Timeframe filter    : {timeframe or 'ALL'}")
    print(f"  DB                  : {_DB_PATH}\n")

    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")

    matches = _load_matches(conn, symbols, timeframe)
    if not matches:
        matches = _fallback_matches_from_candles(conn, symbols, timeframe)

    if not matches:
        print("  No cached candles found for that symbol.")
        conn.close()
        return 0

    total_bars = sum(row.bar_count or 0 for row in matches)
    print("  Matching cache entries:")
    for row in matches:
        print(
            f"    {row.symbol:<16} {row.timeframe:<6} "
            f"bars={row.bar_count:>8,} first_ts={_format_ts(row.first_ts)} last_ts={_format_ts(row.last_ts)}"
        )
    print(f"\n  Total bars matched  : {total_bars:,}")

    registry_deleted = 0
    if not args.keep_registry:
        registry_deleted = conn.execute(
            "SELECT COUNT(*) FROM symbol_source_registry WHERE symbol IN ({})".format(
                ",".join("?" for _ in symbols)
            ),
            symbols,
        ).fetchone()[0]
        print(f"  Registry rows match : {registry_deleted}")

    if args.dry_run:
        print("\n  [DRY RUN] No changes made.")
        conn.close()
        return 0

    deleted_bars = 0
    deleted_meta = 0
    for row in matches:
        deleted_bars += conn.execute(
            "DELETE FROM candles WHERE symbol = ? AND timeframe = ?",
            (row.symbol, row.timeframe),
        ).rowcount
        deleted_meta += conn.execute(
            "DELETE FROM candle_meta WHERE symbol = ? AND timeframe = ?",
            (row.symbol, row.timeframe),
        ).rowcount

    deleted_registry = 0
    if not args.keep_registry:
        deleted_registry = conn.execute(
            "DELETE FROM symbol_source_registry WHERE symbol IN ({})".format(
                ",".join("?" for _ in symbols)
            ),
            symbols,
        ).rowcount

    conn.commit()
    conn.close()

    print("\n  Flush complete.")
    print(f"  Candle rows deleted : {deleted_bars:,}")
    print(f"  Meta rows deleted   : {deleted_meta:,}")
    if not args.keep_registry:
        print(f"  Registry rows reset : {deleted_registry:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
