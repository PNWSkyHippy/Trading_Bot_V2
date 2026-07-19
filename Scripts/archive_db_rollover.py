"""
Scripts/archive_db_rollover.py
================================
Monthly maintenance job: move rows older than RETENTION_DAYS out of the live
trading_bot.db into per-calendar-year archive files (trading_bot<YEAR>.db),
so the live DB stays small/fast while every row is still on disk for IRS
records and historical lookups.

STATUS: DESIGN / REVIEW ONLY. Not wired into cron/systemd, not executed
against any real database. Ron: "dont run it on db yet" (2026-07-18).
Run with --dry-run (the default) to see counts with zero writes. Only
--execute performs real changes, and only after you've reviewed a --dry-run
report first.

Redesigned from an initial Gemini draft. Changes made from that draft and
why:

  1. Archive-year routing uses the RECORD'S OWN DATE (e.g. a trade's
     exit_time, an expense's expense_date), not "the year the script
     happens to run in". Gemini's version used current-year, which is a
     latent bug: a trade that closed in December but ages past the 90-day
     window in the following February would land in the wrong yearly file
     under Gemini's approach. For IRS records, the row's own year is the
     only correct bucket.
  2. Table list and columns are pulled from the actual schema in
     data/database.py (Ron/integration_repo copy — this is the version
     that's actually deployed/pushed; the top-level Trading_Bot_V2/data/
     database.py is an older copy missing breakout_event_execution
     entirely). Gemini's draft referenced a "candles" table that does not
     exist in trading_bot.db (turned out to be cross-conversation mix-up
     with an unrelated candle_store.db git issue) — dropped.
  3. Never-archive tables are hard-excluded regardless of age: bot_state,
     api_keys, dashboard_users (current account/credential state, not
     history), plus non-terminal breakout_event_execution rows (CLAIMED /
     SUBMITTING / SUBMISSION_UNKNOWN — these are actively-reconciled
     durable-event-claim state, not history; archiving one mid-flight
     would break the idempotency guarantee the whole system depends on).
  4. trades and its dependents (trade_partials, ai_signal_reviews,
     scanner_alerts) are archived as a UNIT, keyed off the trade's own
     exit_time year, because there are no enforced foreign keys in this
     schema (trade_partials.trade_id etc. reference trades.trade_id by
     convention only). Splitting a trade from its partials/reviews across
     two different yearly archive files would silently break every manual
     join anything downstream does against archived data. Only CLOSED
     trades are eligible; open trades are never touched regardless of age.
  5. WAL checkpoint (PRAGMA wal_checkpoint(TRUNCATE)) runs before any
     read/copy, so nothing sitting in trading_bot.db-wal is missed.
  6. A full copy of the live DB is taken (backups/db_rollover/
     trading_bot_pre_rollover_<timestamp>.db) after the WAL checkpoint but
     before any table is touched, so a bad run or a mid-run hiccup can be
     undone by stopping services and copying that file back over
     trading_bot.db. This backup is separate from and additional to the
     yearly archive files -- it's a full-DB rollback point, not per-row
     archival.
  7. Services are stopped before the run and restarted after, matching
     Ron's explicit requirement ("script should stop server while it runs
     ... then restart server so no corruption"). astral-drift.service
     (unrelated DecentClone game) is deliberately excluded from the
     stop/start list.

Usage (once reviewed and approved):
    python Scripts/archive_db_rollover.py --dry-run      # default, safe
    python Scripts/archive_db_rollover.py --execute       # real run
    python Scripts/archive_db_rollover.py --execute --no-service-control
        # for local/dev runs where there's no systemd bot service running

Testing --execute for real WITHOUT touching the production DB: point it at
a scratch copy instead. --db-path/--archive-dir/--backup-dir all default to
the real production locations, but override them to run the full write/
delete/VACUUM path against a throwaway file and inspect the result:

    cp trading_bot.db /tmp/test_rollover.db
    python Scripts/archive_db_rollover.py --execute --no-service-control \
        --db-path /tmp/test_rollover.db \
        --archive-dir /tmp/test_archives \
        --backup-dir /tmp/test_backups
    # then open /tmp/test_rollover.db and /tmp/test_archives/trading_bot<YEAR>.db
    # in a DB browser / sqlite3 CLI and check row counts, that nothing
    # eligible was left behind, and that trade_partials/ai_signal_reviews
    # landed in the same yearly file as their parent trade.
--no-service-control is required for this since /tmp/test_rollover.db
isn't a service the real trading-bot.service/web-dashboard.service etc.
know how to stop -- systemctl would just fail against the real services
for no reason while you're testing against a throwaway file.

Intended schedule (not yet installed): 2:00 AM on the 1st of each month,
e.g. via a systemd timer or cron entry pointing at this script with
--execute on the VPS deployment.
"""

import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────
# These three are defaults only. main() overwrites them from
# --db-path/--archive-dir/--backup-dir so a test run can point the entire
# script at scratch files without touching production -- see the "Testing
# --execute for real" note above.
REPO_ROOT = Path(__file__).resolve().parents[1]
# Matches config.DB_PATH = "data/trading_bot.db" -- the actual path the
# running bot/dashboard use (data.database.Database.__init__ defaults to
# config.DB_PATH). Not just "trading_bot.db" at repo root.
DB_PATH = REPO_ROOT / "data" / "trading_bot.db"
ARCHIVE_DIR = REPO_ROOT / "archives"
BACKUP_DIR = REPO_ROOT / "backups" / "db_rollover"
RETENTION_DAYS = 90

# Services to stop before touching the DB file and restart after.
# astral-drift.service is a different project (DecentClone game) and is
# deliberately NOT in this list.
BOT_SERVICES = [
    "trading-bot.service",
    "web-dashboard.service",
    "breakout-scanner.service",
    "ibkr-watchdog.service",
]

# Tables that are never archived by age, regardless of RETENTION_DAYS.
# bot_state / api_keys / dashboard_users are current operational/account
# state, not history. session_state and breakout_event_execution get
# custom (non-blanket) handling below instead of a blanket skip.
NEVER_ARCHIVE = {"bot_state", "api_keys", "dashboard_users"}

# Simple tables: archive any row whose date column is older than the
# cutoff, routed to the archive file matching that column's own year.
# (table_name, date_column)
SIMPLE_TABLES = [
    ("capital", "timestamp"),
    ("daily_summaries", "trade_date"),
    ("tax_ledger", "close_date"),
    ("expenses", "expense_date"),
    ("withdrawals", "timestamp"),
    ("strategy_results", "trade_date"),
    ("fund_events", "timestamp"),
    ("chat_actions", "action_date"),
    ("log_events", "timestamp"),
]

# session_state: keep the current day always; archive anything older by
# session_date, same as SIMPLE_TABLES otherwise.
SESSION_STATE_TABLE = ("session_state", "session_date")

# scanner_alerts: only archive alerts that have reached a terminal status
# (not still pending/live), keyed by registered_at.
SCANNER_ALERTS_TABLE = ("scanner_alerts", "registered_at")
SCANNER_ALERTS_TERMINAL_STATUSES = ("fired", "expired", "cancelled")

# trades + dependents: archived as a unit, keyed by the trade's own
# exit_time year. Only status='closed' trades are eligible.
TRADE_CHILD_TABLES = ["trade_partials", "ai_signal_reviews", "scanner_alerts"]
# NOTE: scanner_alerts also appears above for its own independent
# age-based archiving of alerts with no linked trade_id. A row is
# archived via at most one path in the same run (trade-linked rows are
# excluded from the independent scanner_alerts pass below).

# breakout_event_execution: only TERMINAL rows (ACCEPTED /
# PRE_SUBMISSION_REJECTED) with terminal_at_utc older than cutoff are
# eligible. CLAIMED / SUBMITTING / SUBMISSION_UNKNOWN are never archived
# regardless of age -- they are live idempotency state.
BEE_TERMINAL_STATES = ("ACCEPTED", "PRE_SUBMISSION_REJECTED")


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}")


def run_service_command(action: str, service: str, dry_run: bool) -> None:
    cmd = ["systemctl", action, service]
    if dry_run:
        log(f"DRY-RUN would run: {' '.join(cmd)}")
        return
    log(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def stop_services(dry_run: bool) -> None:
    for svc in BOT_SERVICES:
        run_service_command("stop", svc, dry_run)


def start_services(dry_run: bool) -> None:
    # Restart in reverse order so dependents come back after what they
    # depend on where that matters (watchdog last).
    for svc in reversed(BOT_SERVICES):
        run_service_command("start", svc, dry_run)


def checkpoint_wal(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def backup_live_db(dry_run: bool) -> Path:
    """Snapshot the live DB file before any archive writes/deletes happen,
    so a bad run (or a hiccup mid-run) can be rolled back by copying this
    file back over trading_bot.db. Must be called only after the WAL has
    been checkpointed and truncated, so the copy is a complete, self-
    contained snapshot rather than missing whatever's still sitting in
    -wal at copy time."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"trading_bot_pre_rollover_{stamp}.db"

    if dry_run:
        log(f"DRY-RUN would back up {DB_PATH} -> {backup_path}")
        return backup_path

    shutil.copy2(DB_PATH, backup_path)
    log(f"Backed up live DB to {backup_path} before making any changes")
    return backup_path


def get_archive_conn(year: int) -> sqlite3.Connection:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"trading_bot{year}.db"
    return sqlite3.connect(archive_path)


def ensure_archive_table(archive_conn: sqlite3.Connection, table: str, columns: list) -> None:
    col_defs = ", ".join(f'"{c}"' for c in columns)
    archive_conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})')


def year_of(value: str) -> int:
    """Parse a stored date/timestamp string's calendar year. Handles both
    date-only ('2026-03-05') and full ISO timestamp forms."""
    return int(value[:4])


def move_rows(
    conn: sqlite3.Connection,
    table: str,
    rows: list,
    columns: list,
    id_column: str,
    dry_run: bool,
    archive_year_of_row,
) -> int:
    """Copy rows into the correct per-year archive DB, then delete them
    from the live DB. Rows are grouped by archive_year_of_row(row) so a
    single table's older rows can land in multiple yearly files if they
    span year boundaries."""
    if not rows:
        return 0

    by_year: dict = {}
    for row in rows:
        by_year.setdefault(archive_year_of_row(row), []).append(row)

    moved = 0
    for year, year_rows in by_year.items():
        if dry_run:
            log(f"DRY-RUN would archive {len(year_rows)} row(s) from {table} into trading_bot{year}.db")
            moved += len(year_rows)
            continue

        archive_conn = get_archive_conn(year)
        try:
            ensure_archive_table(archive_conn, table, columns)
            placeholders = ", ".join("?" for _ in columns)
            col_list = ", ".join(f'"{c}"' for c in columns)
            archive_conn.executemany(
                f'INSERT OR IGNORE INTO "{table}" ({col_list}) VALUES ({placeholders})',
                year_rows,
            )
            archive_conn.commit()
        finally:
            archive_conn.close()

        ids = [row[columns.index(id_column)] for row in year_rows]
        qmarks = ", ".join("?" for _ in ids)
        conn.execute(f'DELETE FROM "{table}" WHERE "{id_column}" IN ({qmarks})', ids)
        conn.commit()
        log(f"Archived {len(year_rows)} row(s) from {table} into trading_bot{year}.db and deleted from live DB")
        moved += len(year_rows)

    return moved


def archive_simple_table(conn: sqlite3.Connection, table: str, date_col: str, id_col: str, cutoff: str, dry_run: bool) -> int:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    columns = [r[1] for r in cur.fetchall()]
    if not columns:
        log(f"WARNING: table {table} not found in live DB, skipping")
        return 0

    col_list = ", ".join(f'"{c}"' for c in columns)
    cur = conn.execute(f'SELECT {col_list} FROM "{table}" WHERE "{date_col}" < ?', (cutoff,))
    rows = cur.fetchall()

    return move_rows(
        conn, table, rows, columns, id_col, dry_run,
        archive_year_of_row=lambda row: year_of(row[columns.index(date_col)]),
    )


def archive_session_state(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> int:
    table, date_col = SESSION_STATE_TABLE
    return archive_simple_table(conn, table, date_col, "id", cutoff, dry_run)


def archive_scanner_alerts(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> int:
    table, date_col = SCANNER_ALERTS_TABLE
    cur = conn.execute('PRAGMA table_info("scanner_alerts")')
    columns = [r[1] for r in cur.fetchall()]
    if not columns:
        log("WARNING: table scanner_alerts not found, skipping")
        return 0

    status_placeholders = ", ".join("?" for _ in SCANNER_ALERTS_TERMINAL_STATUSES)
    col_list = ", ".join(f'"{c}"' for c in columns)
    # Only alerts with no linked trade AND a terminal status are archived
    # independently here -- trade-linked alerts move with their parent
    # trade in archive_trades_and_children().
    cur = conn.execute(
        f'SELECT {col_list} FROM "scanner_alerts" '
        f'WHERE "{date_col}" < ? AND status IN ({status_placeholders}) '
        f'AND (trade_id IS NULL OR trade_id = "")',
        (cutoff, *SCANNER_ALERTS_TERMINAL_STATUSES),
    )
    rows = cur.fetchall()

    return move_rows(
        conn, table, rows, columns, "alert_id", dry_run,
        archive_year_of_row=lambda row: year_of(row[columns.index(date_col)]),
    )


def archive_trades_and_children(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> int:
    cur = conn.execute('PRAGMA table_info("trades")')
    trade_columns = [r[1] for r in cur.fetchall()]
    exit_idx = trade_columns.index("exit_time")
    trade_id_idx = trade_columns.index("trade_id")

    col_list = ", ".join(f'"{c}"' for c in trade_columns)
    cur = conn.execute(
        f'SELECT {col_list} FROM "trades" WHERE status = "closed" AND exit_time < ?',
        (cutoff,),
    )
    trades = cur.fetchall()
    if not trades:
        log("No closed trades older than cutoff -- nothing to archive for trades or dependents")
        return 0

    trade_ids = [t[trade_id_idx] for t in trades]
    year_by_trade_id = {t[trade_id_idx]: year_of(t[exit_idx]) for t in trades}

    total_moved = move_rows(
        conn, "trades", trades, trade_columns, "trade_id", dry_run,
        archive_year_of_row=lambda row: year_of(row[exit_idx]),
    )

    for child_table in TRADE_CHILD_TABLES:
        cur = conn.execute(f'PRAGMA table_info("{child_table}")')
        child_columns = [r[1] for r in cur.fetchall()]
        if not child_columns or "trade_id" not in child_columns:
            continue
        tid_idx = child_columns.index("trade_id")

        qmarks = ", ".join("?" for _ in trade_ids)
        col_list = ", ".join(f'"{c}"' for c in child_columns)
        cur = conn.execute(
            f'SELECT {col_list} FROM "{child_table}" WHERE trade_id IN ({qmarks})',
            trade_ids,
        )
        child_rows = cur.fetchall()

        pk_col = "alert_id" if child_table == "scanner_alerts" else "id"
        if pk_col not in child_columns:
            pk_col = child_columns[0]  # fall back to first column as row identity

        total_moved += move_rows(
            conn, child_table, child_rows, child_columns, pk_col, dry_run,
            archive_year_of_row=lambda row, _idx=tid_idx: year_by_trade_id[row[_idx]],
        )

    return total_moved


def archive_breakout_event_execution(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> int:
    cur = conn.execute('PRAGMA table_info("breakout_event_execution")')
    columns = [r[1] for r in cur.fetchall()]
    if not columns:
        log("WARNING: table breakout_event_execution not found, skipping")
        return 0

    state_placeholders = ", ".join("?" for _ in BEE_TERMINAL_STATES)
    col_list = ", ".join(f'"{c}"' for c in columns)
    cur = conn.execute(
        f'SELECT {col_list} FROM "breakout_event_execution" '
        f'WHERE state IN ({state_placeholders}) AND terminal_at_utc IS NOT NULL AND terminal_at_utc < ?',
        (*BEE_TERMINAL_STATES, cutoff),
    )
    rows = cur.fetchall()
    terminal_idx = columns.index("terminal_at_utc")

    return move_rows(
        conn, "breakout_event_execution", rows, columns, "event_id", dry_run,
        archive_year_of_row=lambda row: year_of(row[terminal_idx]),
    )


def main() -> int:
    global DB_PATH, ARCHIVE_DIR, BACKUP_DIR

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Perform real writes/deletes. Without this flag, runs as --dry-run.")
    parser.add_argument("--no-service-control", action="store_true", help="Skip systemctl stop/start (for local/dev runs with no bot services, or when testing against a scratch DB).")
    parser.add_argument("--retention-days", type=int, default=RETENTION_DAYS)
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Override the live DB file to operate on (e.g. a scratch copy for testing --execute safely).")
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR, help="Override where yearly trading_bot<YEAR>.db archive files are written.")
    parser.add_argument("--backup-dir", type=Path, default=BACKUP_DIR, help="Override where the pre-run full-DB backup is written.")
    args = parser.parse_args()

    DB_PATH = args.db_path
    ARCHIVE_DIR = args.archive_dir
    BACKUP_DIR = args.backup_dir

    dry_run = not args.execute
    cutoff_dt = date.today() - timedelta(days=args.retention_days)
    cutoff = cutoff_dt.isoformat()

    if DB_PATH != REPO_ROOT / "data" / "trading_bot.db":
        log(f"Operating on a non-default DB path ({DB_PATH}) -- this is NOT the production database.")

    log(f"{'DRY-RUN' if dry_run else 'EXECUTE'} mode. Retention cutoff: rows older than {cutoff} are eligible.")
    log(f"Live DB: {DB_PATH}")
    log(f"Archive dir: {ARCHIVE_DIR}")

    if not DB_PATH.exists():
        log(f"ERROR: {DB_PATH} does not exist")
        return 1

    control_services = not args.no_service_control
    if control_services:
        stop_services(dry_run)

    total = 0
    try:
        # Checkpoint on its own connection, then close it before copying
        # the file -- this guarantees the backup is a clean, complete
        # snapshot with nothing left outstanding in -wal, and that no
        # connection is holding the file open during the copy.
        conn = sqlite3.connect(DB_PATH)
        checkpoint_wal(conn)
        conn.close()

        backup_path = backup_live_db(dry_run)
        log(f"Rollback plan if anything below goes wrong: stop services, "
            f"copy {backup_path} back over {DB_PATH}, restart services.")

        conn = sqlite3.connect(DB_PATH)
        try:
            for table, date_col in SIMPLE_TABLES:
                if table in NEVER_ARCHIVE:
                    continue
                total += archive_simple_table(conn, table, date_col, "id", cutoff, dry_run)

            total += archive_session_state(conn, cutoff, dry_run)
            total += archive_scanner_alerts(conn, cutoff, dry_run)
            total += archive_trades_and_children(conn, cutoff, dry_run)
            total += archive_breakout_event_execution(conn, cutoff, dry_run)

            if not dry_run:
                log("Running VACUUM on live DB to reclaim freed space...")
                conn.execute("VACUUM")
        finally:
            conn.close()
    finally:
        if control_services:
            start_services(dry_run)

    log(f"{'Would archive' if dry_run else 'Archived'} {total} total row(s).")
    if dry_run:
        log("This was a dry run -- no data was moved or deleted. Re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
