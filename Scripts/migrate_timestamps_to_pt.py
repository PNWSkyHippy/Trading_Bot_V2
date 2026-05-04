"""
migrate_timestamps_to_pt.py
============================
One-time migration: shifts all existing UTC timestamps in the DB
back by 7 hours (PDT) to match Pacific Time.

Run ONCE before restarting the bot after the database.py timezone fix.
Safe to run multiple times — checks if migration already applied.

Usage:
    python Scripts/migrate_timestamps_to_pt.py

What it converts (all TEXT timestamp columns):
    trades:        entry_time, exit_time
    capital:       timestamp
    withdrawals:   timestamp
    bot_state:     updated
    fund_events:   timestamp
    chat_actions:  timestamp

Note: We use -7 hours (PDT). In winter when PST is active (-8 hours),
there will be a 1-hour discrepancy on timestamps from that period.
Since the bot runs year-round in Spokane (PDT Apr-Nov, PST Nov-Mar),
and most activity is during trading hours (PDT), -7 is correct for
the majority of data. The bot going forward uses datetime.now() which
automatically uses the system clock in the correct local time.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DB_PATH    = config.DB_PATH
OFFSET_HRS = -7   # UTC to PDT. Change to -8 for PST if running in winter.


def shift_timestamp(ts_str: str, hours: int) -> str:
    """Shift an ISO timestamp string by N hours. Returns original if parse fails."""
    if not ts_str:
        return ts_str
    try:
        dt  = datetime.fromisoformat(ts_str)
        dt2 = dt + timedelta(hours=hours)
        return dt2.isoformat()
    except Exception:
        return ts_str


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # Check if already migrated by looking at a recent trade entry_time.
    # If the hour is reasonable for PT (6am-6pm), it's already converted.
    row = cur.execute(
        "SELECT entry_time FROM trades WHERE entry_time IS NOT NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if row:
        ts  = row["entry_time"]
        try:
            dt  = datetime.fromisoformat(ts)
            hr  = dt.hour
            # UTC times for US market hours (9:30 ET = 13:30 UTC, 4 ET = 20 UTC)
            # PT times would be 6:30-13:00
            # If hour is between 13-23, still in UTC — migrate.
            # If hour is between 6-13, already in PT — skip.
            if hr < 13:
                print(f"Timestamps appear to already be in PT (hour={hr}) — skipping migration.")
                print(f"Sample: {ts}")
                conn.close()
                return
            print(f"Sample UTC timestamp: {ts} (hour={hr}) — will shift by {OFFSET_HRS}h to PT")
        except Exception:
            pass

    print(f"\nMigrating timestamps: UTC → PT ({OFFSET_HRS:+d} hours)")
    print(f"Database: {DB_PATH}\n")

    tables = [
        ("trades",       ["entry_time", "exit_time"]),
        ("capital",      ["timestamp"]),
        ("withdrawals",  ["timestamp"]),
        ("bot_state",    ["updated"]),
        ("fund_events",  ["timestamp"]),
        ("chat_actions", ["timestamp"]),
    ]

    total_updated = 0

    for table, columns in tables:
        for col in columns:
            try:
                rows = cur.execute(
                    f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL"
                ).fetchall()
                count = 0
                for row in rows:
                    new_ts = shift_timestamp(row[col], OFFSET_HRS)
                    if new_ts != row[col]:
                        cur.execute(
                            f"UPDATE {table} SET {col}=? WHERE rowid=?",
                            (new_ts, row["rowid"])
                        )
                        count += 1
                if count:
                    print(f"  {table}.{col}: {count} rows updated")
                    total_updated += count
                else:
                    print(f"  {table}.{col}: no rows to update")
            except Exception as e:
                print(f"  {table}.{col}: ERROR — {e}")

    conn.commit()
    conn.close()

    print(f"\nMigration complete: {total_updated} timestamps converted to PT.")
    print("Going forward, database.py uses datetime.now() (local PT).")
    print("Restart the bot after running this script.")


if __name__ == "__main__":
    migrate()
