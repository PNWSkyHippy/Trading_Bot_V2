"""
One-shot candle store cleanup.
Deletes (symbol, timeframe) entries whose last bar is older than MAX_AGE_DAYS.
Run from the project root:
    venv312/Scripts/python.exe cleanup_candle_store.py
"""

import sqlite3
import os
from datetime import datetime, timedelta, timezone

MAX_AGE_DAYS = 2
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "candle_store.db")

if not os.path.exists(DB_PATH):
    print(f"DB not found at {DB_PATH}")
    raise SystemExit(1)

now_utc   = datetime.now(timezone.utc)
cutoff_ts = int((now_utc - timedelta(days=MAX_AGE_DAYS)).timestamp())

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")

stale = conn.execute(
    "SELECT symbol, timeframe, last_ts FROM candle_meta WHERE last_ts < ? OR last_ts IS NULL",
    (cutoff_ts,)
).fetchall()

print(f"Found {len(stale)} stale (symbol, timeframe) entries older than {MAX_AGE_DAYS} days:\n")

total_rows = 0
for symbol, timeframe, last_ts in stale:
    age_days = (now_utc.timestamp() - (last_ts or 0)) / 86400
    n = conn.execute(
        "DELETE FROM candles WHERE symbol = ? AND timeframe = ?",
        (symbol, timeframe)
    ).rowcount
    conn.execute(
        "DELETE FROM candle_meta WHERE symbol = ? AND timeframe = ?",
        (symbol, timeframe)
    )
    total_rows += n
    print(f"  Removed {symbol}/{timeframe}  ({n:,} bars,  {age_days:.1f}d old)")

conn.commit()
conn.close()

print(f"\nDone — {total_rows:,} candle rows deleted across {len(stale)} stale entries.")
