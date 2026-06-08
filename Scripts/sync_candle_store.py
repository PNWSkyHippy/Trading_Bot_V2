"""
=================================================================
  sync_candle_store.py
  Cleans the candle store DB so it exactly matches the current
  active watchlists.

  TWO MODES:

  1. SYNC (default)
     Deletes every symbol that is NOT in crypto.txt / stocks.txt.
     Keeps all candles for symbols still on the watchlist.
     Fast — surgical deletion of orphaned symbols only.

       python Scripts/sync_candle_store.py

  2. NUKE + RESEED  (--nuke flag)
     Wipes the ENTIRE candle store, then triggers CandleManager
     to re-download fresh data for every current watchlist symbol.
     Use this when the DB is bloated or data quality is suspect.

       python Scripts/sync_candle_store.py --nuke

  OUTPUT
     Prints a summary of what was deleted / what remains.
=================================================================
"""

import argparse
import os
import sqlite3
import sys
import time

# ── Project root setup ────────────────────────────────────────────────────────
_script_dir   = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

_DB_PATH = os.path.join(_project_root, "data", "candle_store.db")


# ── Watchlist loader ──────────────────────────────────────────────────────────

def _load_watchlist(path: str) -> list:
    """Read a watchlist file, return stripped non-comment lines."""
    symbols = []
    if not os.path.exists(path):
        return symbols
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                symbols.append(line.upper())
    return symbols


def get_active_symbols() -> set:
    """Return the full set of symbols currently on any watchlist."""
    active = set()
    watchlists = [
        "watchlists/crypto.txt",
        "watchlists/stocks.txt",
        "watchlist/scanned_crypto.txt",
        "watchlist/scanned_stocks.txt",
    ]
    for wl in watchlists:
        path = os.path.join(_project_root, wl)
        syms = _load_watchlist(path)
        active.update(syms)
    return active


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db_symbols(conn) -> set:
    """Return all distinct symbols currently in the candle store."""
    rows = conn.execute("SELECT DISTINCT symbol FROM candles").fetchall()
    return {r[0] for r in rows}


def get_db_stats(conn) -> dict:
    total_candles = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM candles").fetchone()[0]
    return {"candles": total_candles, "symbols": total_symbols}


# ── SYNC MODE ─────────────────────────────────────────────────────────────────

def run_sync(dry_run: bool = False):
    """Delete candles for symbols NOT in the active watchlists."""
    print(f"\n  {'[DRY RUN] ' if dry_run else ''}SYNC MODE — removing orphaned symbols")
    print(f"  DB: {_DB_PATH}\n")

    if not os.path.exists(_DB_PATH):
        print(f"  [ERROR] DB not found at {_DB_PATH}")
        sys.exit(1)

    active  = get_active_symbols()
    print(f"  Active watchlist symbols : {len(active)}")

    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")

    before = get_db_stats(conn)
    db_syms = get_db_symbols(conn)

    orphans = sorted(db_syms - active)
    kept    = sorted(db_syms & active)

    print(f"  Symbols in DB            : {len(db_syms)}")
    print(f"  Orphaned (to delete)     : {len(orphans)}")
    print(f"  Kept (on watchlist)      : {len(kept)}")
    print(f"  Total candles before     : {before['candles']:,}\n")

    if not orphans:
        print("  Nothing to delete — DB already matches watchlists.")
        conn.close()
        return

    print("  Orphaned symbols:")
    for s in orphans:
        count = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol=?", (s,)
        ).fetchone()[0]
        print(f"    {s:<20} ({count:,} candles)")

    if dry_run:
        print("\n  [DRY RUN] No changes made. Re-run without --dry-run to apply.")
        conn.close()
        return

    print("\n  Deleting orphaned candles...")
    t0 = time.time()
    for sym in orphans:
        conn.execute("DELETE FROM candles WHERE symbol=?", (sym,))
        # Also clean candle_meta if it exists
        try:
            conn.execute("DELETE FROM candle_meta WHERE symbol=?", (sym,))
        except Exception:
            pass
    conn.commit()

    # VACUUM to reclaim disk space from deleted rows
    print("  Running VACUUM to reclaim disk space...")
    conn.execute("VACUUM")

    after = get_db_stats(conn)
    conn.close()

    elapsed = time.time() - t0
    freed = before["candles"] - after["candles"]
    print(f"\n  Done in {elapsed:.1f}s")
    print(f"  Candles deleted  : {freed:,}")
    print(f"  Candles remaining: {after['candles']:,}")
    print(f"  Symbols remaining: {after['symbols']}")


# ── NUKE + RESEED MODE ────────────────────────────────────────────────────────

def run_nuke():
    """Wipe entire candle store then trigger CandleManager to re-download."""
    print(f"\n  NUKE + RESEED MODE")
    print(f"  DB: {_DB_PATH}\n")

    if not os.path.exists(_DB_PATH):
        print(f"  [ERROR] DB not found at {_DB_PATH}")
        sys.exit(1)

    active = get_active_symbols()
    print(f"  Active watchlist symbols : {len(active)}")
    print(f"  These will be re-downloaded after wipe.\n")

    confirm = input("  Type YES to wipe the entire candle store: ").strip()
    if confirm != "YES":
        print("  Aborted.")
        sys.exit(0)

    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")

    before = get_db_stats(conn)
    print(f"\n  Wiping {before['candles']:,} candles across {before['symbols']} symbols...")

    t0 = time.time()
    conn.execute("DELETE FROM candles")
    try:
        conn.execute("DELETE FROM candle_meta")
    except Exception:
        pass
    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    elapsed = time.time() - t0
    print(f"  Wiped in {elapsed:.1f}s")

    # Trigger CandleManager re-download
    print("\n  Triggering CandleManager to re-download all watchlist symbols...")
    try:
        from core.candle_manager import candle_manager
        crypto_syms = [s for s in active if "/" in s]
        stock_syms  = [s for s in active if "/" not in s]
        print(f"  Queuing {len(crypto_syms)} crypto + {len(stock_syms)} stock symbols...")
        # Invalidate forces a fresh fetch on next get() call
        for sym in active:
            for tf in ["5m", "15m", "1h", "4h", "1d"]:
                try:
                    candle_manager.invalidate(sym, tf)
                except Exception:
                    pass
        print("  CandleManager invalidated — bot will re-fetch on next scan cycle.")
        print("  Full refresh takes ~5-10 minutes depending on watchlist size.")
    except Exception as e:
        print(f"  CandleManager not available (bot not running?): {e}")
        print("  Start the bot and it will re-download automatically on first scan.")

    print("\n  Nuke + reseed complete.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sync candle store DB to current watchlists."
    )
    parser.add_argument("--nuke",    action="store_true",
                        help="Wipe entire DB and re-download from scratch")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what SYNC would delete without actually deleting")
    args = parser.parse_args()

    if args.nuke:
        run_nuke()
    else:
        run_sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
