"""
migrate_timestamps_to_pt.py
============================
One-time migration: shifts all existing UTC timestamps in the DB
back by 7 hours (PDT) to match Pacific Time.

Safe to run multiple times — detects if already migrated.

Usage:
    python Scripts/migrate_timestamps_to_pt.py
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DB_PATH    = config.DB_PATH
OFFSET_HRS = -7   # UTC to PDT


def shift_timestamp(ts_str: str, hours: int) -> str:
    if not ts_str:
        return ts_str
    try:
        dt  = datetime.fromisoformat(ts_str)
        return (dt + timedelta(hours=hours)).isoformat()
    except Exception:
        return ts_str


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # Check if already migrated
    row = cur.execute(
        "SELECT entry_time FROM trades WHERE entry_time IS NOT NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if row:
        ts = row["entry_time"]
        try:
            hr = datetime.fromisoformat(ts).hour
            if hr < 13:
                print(f"Already in PT (hour={hr}) — skipping migration.")
                print(f"Sample: {ts}")
                conn.close()
                return
            print(f"Sample UTC timestamp: {ts} (hour={hr}) — will shift by {OFFSET_HRS}h to PT")
        except Exception:
            pass

    print(f"\nMigrating timestamps: UTC -> PT ({OFFSET_HRS:+d} hours)")
    print(f"Database: {DB_PATH}\n")

    tables = [
        ("trades",       "id", ["entry_time", "exit_time"]),
        ("capital",      "id", ["timestamp"]),
        ("withdrawals",  "id", ["timestamp"]),
        ("bot_state",    "key", ["updated"]),
        ("fund_events",  "id", ["timestamp"]),
        ("chat_actions", "id", ["timestamp"]),
    ]

    total_updated = 0

    for table, pk, columns in tables:
        for col in columns:
            try:
                # Explicitly select the primary key so we can update by it
                rows = cur.execute(
                    f"SELECT {pk}, {col} FROM {table} WHERE {col} IS NOT NULL"
                ).fetchall()
                count = 0
                for row in rows:
                    new_ts = shift_timestamp(row[col], OFFSET_HRS)
                    if new_ts != row[col]:
                        cur.execute(
                            f"UPDATE {table} SET {col}=? WHERE {pk}=?",
                            (new_ts, row[pk])
                        )
                        count += 1
                if count:
                    print(f"  {table}.{col}: {count} rows updated")
                    total_updated += count
                else:
                    print(f"  {table}.{col}: no rows to update")
            except Exception as e:
                print(f"  {table}.{col}: ERROR -- {e}")

    conn.commit()
    conn.close()

    print(f"\nMigration complete: {total_updated} timestamps converted to PT.")
    print("Restart the bot after running this script.")


if __name__ == "__main__":
    migrate()
