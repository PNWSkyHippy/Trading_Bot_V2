"""
fix_exit_timestamps.py
======================
Fixes exit_time timestamps still in UTC after the PT migration.
Identifies trades where exit_time < entry_time (impossible in reality)
and shifts those exit_times forward by 7 hours to PT.

Run once then delete.
"""
import sqlite3, sys
sys.path.insert(0, ".")
import config
from datetime import datetime, timedelta

conn = sqlite3.connect(config.DB_PATH)
cur  = conn.cursor()

# Find trades where exit is before entry (still UTC)
rows = cur.execute("""
    SELECT rowid, trade_id, symbol, entry_time, exit_time
    FROM trades
    WHERE status='closed'
    AND exit_time IS NOT NULL
    AND exit_time < entry_time
""").fetchall()

print(f"Trades with exit before entry (UTC exit_time): {len(rows)}")

count = 0
for rowid, trade_id, symbol, entry_time, exit_time in rows:
    try:
        dt  = datetime.fromisoformat(exit_time)
        new = (dt + timedelta(hours=7)).isoformat()
        cur.execute("UPDATE trades SET exit_time=? WHERE rowid=?", (new, rowid))
        count += 1
    except Exception as e:
        print(f"  Skip {symbol}: {e}")

conn.commit()
conn.close()
print(f"Fixed {count} exit timestamps. Restart bot.")
