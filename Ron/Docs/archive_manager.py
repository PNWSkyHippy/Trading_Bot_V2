import os
import sqlite3
from datetime import datetime, timedelta
# Cron entry to add
# 0 0 1 * * /opt/trading_bot_v2/.venv312/bin/python /opt/trading_bot_v2/scripts/archive_manager.py >> /opt/trading_bot_v2/data/archive_log.txt 2>&1

# Define the production data directory
DATA_DIR = "/opt/trading_bot_v2/data"
ACTIVE_DB = os.path.join(DATA_DIR, "trading_bot.db")

def get_yearly_db_path(year):
    """Generates the absolute path for a specific year's database storage."""
    return os.path.join(DATA_DIR, f"trading_bot{year}.db")

def ensure_yearly_db_exists(year):
    """Ensures a specific year's file exists and copies the active schema into it."""
    target_db = get_yearly_db_path(year)
    if not os.path.exists(target_db):
        print(f"Initializing a new yearly database archive file: {target_db}")
        # Connect to active database to extract schema layouts
        with sqlite3.connect(ACTIVE_DB) as active_conn, sqlite3.connect(target_db) as yearly_conn:
            # Extract table creation schemas dynamically
            schema_queries = active_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
            
            # Recreate identical tables in the new archive file
            for query in schema_queries:
                if query[0]:
                    yearly_conn.execute(query[0])
    return target_db

def run_archive_and_rollover():
    now = datetime.now()
    current_year = now.strftime("%Y")
    
    if not os.path.exists(ACTIVE_DB):
        print(f"Active database '{ACTIVE_DB}' not found. Aborting.")
        return

    # 1. NEW YEAR AUTOMATION RULES (JANUARY 1st SPECIFIC PROVISIONS)
    # Automatically pre-build the current year's database if it's missing
    ensure_yearly_db_exists(current_year)

    # 2. CALCULATE ROLLING 90-DAY RETENTION INTERVAL LIMITS
    # Rows older than this threshold will be moved out of the active database
    cutoff_date = (now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Processing database clean-up. 90-day cutoff point: {cutoff_date}")

    # 3. OPEN AND INTER-CONNECT THE ARCHIVE STREAMS
    conn = sqlite3.connect(ACTIVE_DB)
    cursor = conn.cursor()

    try:
        # We attach the target archive file dynamically using SQLite's ATTACH function
        # Data will be moved into the file matching the year the database manager runs
        archive_path = get_yearly_db_path(current_year)
        cursor.execute(f"ATTACH DATABASE '{archive_path}' AS year_archive")

        # Replace 'candles' with your actual bot database primary table name
        # Move older records out of active scope and append into the annual file
        cursor.execute("""
            INSERT OR IGNORE INTO year_archive.candles 
            SELECT * FROM main.candles WHERE timestamp < ?
        """, (cutoff_date,))
        rows_archived = cursor.rowcount

        # Erase those processed records out of the primary running file
        cursor.execute("DELETE FROM main.candles WHERE timestamp < ?", (cutoff_date,))
        rows_deleted = cursor.rowcount

        # Save all filesystem changes atomically
        conn.commit()
        print(f"Moved {rows_archived} records to historical file. Erased {rows_deleted} rows from active loop.")

        # Reclaim unused sector capacity on your server hard drive
        print("Executing SQLite VACUUM optimization sweep on active drive...")
        cursor.execute("VACUUM")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Archival pipeline execution halted due to SQLite error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_archive_and_rollover()
