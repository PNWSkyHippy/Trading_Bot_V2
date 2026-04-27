"""
flush_log.py
Clears bot.log without stopping the running server.
Keeps the last N lines so you don't lose recent context.
Run any time: python flush_log.py
"""
import os

LOG_FILE  = "logs/bot.log"
KEEP_LINES = 50  # how many recent lines to keep after flush

if not os.path.exists(LOG_FILE):
    print(f"Log file not found: {LOG_FILE}")
else:
    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    keep  = lines[-KEEP_LINES:] if len(lines) > KEEP_LINES else lines
    total = len(lines)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.writelines(keep)

    print(f"Log flushed — kept last {len(keep)} of {total} lines.")
    print(f"Log file: {LOG_FILE}")
