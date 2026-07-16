"""
=============================================================
  CANDLE STORE  v1.0
  Persistent OHLCV cache for backtester / optimizer.

  Stores downloaded candle data in SQLite so the optimizer
  can iterate parameter combos without re-fetching from
  yfinance on every restart or every iteration.

  Lookup priority (backtester):
    1. In-memory _candle_cache   (fastest — cleared on restart)
    2. CandleStore SQLite        (fast   — survives restarts)
    3. yfinance network          (slow   — fallback only)

  Location:  data/candle_store.db  (separate from main bot DB)

  Usage:
    from intelligence.candle_store import CandleStore, get_store
    store = get_store()

    store.save("BTC/USD", "1h", df)          # store candles
    df    = store.load("BTC/USD", "1h", 365) # last 365 days
    rows  = store.list_available()           # [{symbol, timeframe, ...}]
    ok    = store.has_data("BTC/USD","1h",90)# quick freshness check
    store.delete("BTC/USD", "1h")            # remove from store
=============================================================
"""

import sqlite3
import logging
import os
import time
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


def _now_ts() -> int:
    """
    Current UTC epoch seconds, host-timezone-independent.

    `int(datetime.utcnow().timestamp())` is a classic footgun: `datetime.utcnow()`
    returns a naive datetime whose *fields* are UTC, but `.timestamp()` on a naive
    datetime interprets those fields as *local* time (Python's documented
    behavior). On any host whose local timezone isn't UTC, that combination
    silently produces the wrong epoch, shifted by the host's UTC offset — this is
    exactly the defect this helper exists to eliminate (see F11,
    reports/agent_pipeline/20260716-082429/final_unified_report.md). `time.time()`
    is defined as UTC epoch seconds regardless of host timezone and has no such
    ambiguity.
    """
    return int(time.time())


def _cutoff_ts(days: float) -> int:
    """Epoch seconds `days` days before now, host-timezone-independent (see `_now_ts`)."""
    return _now_ts() - int(days * 86400)

# ---------------------------------------------------------------------------
# DB path — data/ folder next to this package
# ---------------------------------------------------------------------------
_HERE       = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.normpath(os.path.join(_HERE, '..', 'data', 'candle_store.db'))

# Bars-per-day estimates for freshness checking
_BARS_PER_DAY = {
    '5m':  288,   # 24h × 60m/5m
    '15m':  96,
    '1h':   24,
    '4h':    6,
    '1d':    1,
}

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_store_instance: Optional['CandleStore'] = None

def get_store(db_path: str = None) -> 'CandleStore':
    """Return the shared CandleStore singleton (creates on first call)."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CandleStore(db_path)
    return _store_instance


# ---------------------------------------------------------------------------
# CandleStore
# ---------------------------------------------------------------------------

class CandleStore:
    """
    Thread-safe persistent OHLCV cache backed by SQLite (WAL mode).
    Each connection is created per-call so multiple threads can read/write safely.
    """

    REQUIRED_COLS = ('open', 'high', 'low', 'close')

    def __init__(self, db_path: str = None):
        self.db_path = os.path.abspath(db_path or _DEFAULT_DB)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        logger.info(f"CandleStore initialised at {self.db_path}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _conn(self):
        """Open a connection with WAL and busy-timeout."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    symbol    TEXT    NOT NULL,
                    timeframe TEXT    NOT NULL,
                    ts        INTEGER NOT NULL,   -- unix seconds (UTC)
                    open      REAL,
                    high      REAL,
                    low       REAL,
                    close     REAL,
                    volume    REAL,
                    PRIMARY KEY (symbol, timeframe, ts)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candle_meta (
                    symbol     TEXT NOT NULL,
                    timeframe  TEXT NOT NULL,
                    bar_count  INTEGER,
                    first_ts   INTEGER,   -- earliest bar in store
                    last_ts    INTEGER,   -- latest bar in store
                    fetched_at TEXT,      -- ISO timestamp of last save()
                    PRIMARY KEY (symbol, timeframe)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_candles_sym_tf_ts
                ON candles (symbol, timeframe, ts)
            """)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, symbol: str, timeframe: str, df: pd.DataFrame) -> int:
        """
        Upsert candles into the store.
        df must have a DatetimeIndex and at minimum open/high/low/close columns.
        Returns number of rows written.
        """
        if df is None or df.empty:
            return 0

        df2 = df.copy()
        df2.columns = [c.lower() for c in df2.columns]

        # Drop duplicate columns that can arise when two data sources merge
        # or when column names collide after lowercasing (e.g. 'Volume' + 'volume').
        # Keep the first occurrence; duplicates cause pd.notna(Series) ambiguity
        # errors in the iterrows loop and corrupt downstream strategy DataFrames.
        if df2.columns.duplicated().any():
            logger.debug(
                f"CandleStore.save: dropping duplicate columns for {symbol}/{timeframe}: "
                f"{list(df2.columns[df2.columns.duplicated()])}"
            )
            df2 = df2.loc[:, ~df2.columns.duplicated()]

        for col in self.REQUIRED_COLS:
            if col not in df2.columns:
                logger.warning(f"CandleStore.save: missing column '{col}' for {symbol}/{timeframe}")
                return 0

        # DatetimeIndex → unix seconds (UTC).
        #
        # Contract: every caller of save() must hand this method a DatetimeIndex
        # whose values represent UTC — either tz-aware (any timezone; converted
        # correctly below) or naive with UTC-valued fields (this is what every
        # current fetcher produces: Alpaca stays tz-aware end-to-end; Kraken/
        # KuCoin explicitly compute UTC via `utc=True` before stripping the tz
        # tag).
        #
        # Correction to an earlier round of this audit: a naive *pandas*
        # Timestamp's `.timestamp()` was originally assumed to interpret its
        # fields as host-local time — by analogy with stdlib
        # `datetime.timestamp()`, which does exactly that and is genuinely
        # host-timezone-dependent (see the fixed `_now_ts()`/`_cutoff_ts()`
        # helpers above, which replace real `datetime.utcnow().timestamp()`
        # bugs elsewhere in this file). That analogy does not hold here:
        # verified directly (pd.Timestamp(naive).value is always UTC-based
        # nanoseconds-since-epoch, unconditionally, regardless of host `TZ` —
        # naive pandas Timestamps are not host-local the way naive stdlib
        # datetimes are), a naive pandas Timestamp's `.timestamp()` already
        # treats its fields as UTC. This call site was therefore never
        # actually host-timezone-dependent. The explicit `tz_localize("UTC")`
        # below is kept as a defensive, self-documenting statement of the
        # UTC-naive contract this method requires (and a guard against ever
        # depending on this specific pandas behavior implicitly), not because
        # it fixes an active bug at this line.
        try:
            idx = df2.index
            if hasattr(idx, 'tz') and idx.tz is not None:
                timestamps = [int(t.timestamp()) for t in idx]
            else:
                timestamps = [
                    int(pd.Timestamp(t).tz_localize("UTC").timestamp()) for t in idx
                ]
        except Exception as e:
            logger.error(f"CandleStore.save: timestamp conversion failed: {e}")
            return 0

        rows = []
        for ts, (_, row) in zip(timestamps, df2.iterrows()):
            # Use scalar extraction helper — row[col] can return a Series when
            # duplicate columns slip through despite the dedup above (extra safety net).
            def _scalar(col):
                val = row[col]
                if hasattr(val, 'iloc'):
                    val = val.iloc[0]  # take first value from accidental Series
                return float(val)
            try:
                vol_raw = row.get('volume') if 'volume' in row.index else None
                if vol_raw is not None and hasattr(vol_raw, 'iloc'):
                    vol_raw = vol_raw.iloc[0]
                vol = float(vol_raw) if vol_raw is not None and pd.notna(vol_raw) else 0.0
                rows.append((
                    symbol, timeframe, ts,
                    _scalar('open'), _scalar('high'),
                    _scalar('low'),  _scalar('close'),
                    vol,
                ))
            except Exception as _row_err:
                logger.debug(f"CandleStore.save: skipping bad row for {symbol} ts={ts}: {_row_err}")
                continue

        if not rows:
            return 0

        ts_vals   = [r[2] for r in rows]
        first_ts  = min(ts_vals)
        last_ts   = max(ts_vals)
        now_iso   = datetime.now().isoformat(timespec='seconds')

        with self._conn() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO candles
                    (symbol, timeframe, ts, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            # Prune bars older than the oldest bar in this batch.
            # Prevents unbounded growth — each save keeps exactly the current window.
            conn.execute("""
                DELETE FROM candles
                WHERE symbol = ? AND timeframe = ? AND ts < ?
            """, (symbol, timeframe, first_ts))

            # Update meta with actual DB counts after pruning
            actual = conn.execute("""
                SELECT COUNT(*), MIN(ts), MAX(ts) FROM candles
                WHERE symbol = ? AND timeframe = ?
            """, (symbol, timeframe)).fetchone()
            actual_count  = actual[0] or 0
            actual_first  = actual[1] or first_ts
            actual_last   = actual[2] or last_ts

            conn.execute("""
                INSERT OR REPLACE INTO candle_meta
                    (symbol, timeframe, bar_count, first_ts, last_ts, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, timeframe, actual_count, actual_first, actual_last, now_iso))

        logger.debug(f"CandleStore: saved {len(rows):,} bars for {symbol}/{timeframe}")
        return len(rows)

    def load(self, symbol: str, timeframe: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        Load the most recent `days` of candles from the store.
        Returns a DataFrame with DatetimeIndex and OHLCV columns, or None if empty.
        """
        cutoff = _cutoff_ts(days + 1)

        with self._conn() as conn:
            rows = conn.execute("""
                SELECT ts, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ? AND ts >= ?
                ORDER BY ts ASC
            """, (symbol, timeframe, cutoff)).fetchall()

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['ts'], unit='s', utc=True).dt.tz_localize(None)
        df = df.set_index('datetime').drop(columns=['ts'])

        logger.debug(f"CandleStore: loaded {len(df):,} bars for {symbol}/{timeframe}/{days}d")  # noqa
        return df

    def has_data(self, symbol: str, timeframe: str, days: int) -> bool:
        """
        Return True if the store has sufficient data for this request.
        'Sufficient' = at least 80% of expected bars AND data is no more than 24h stale.
        """
        with self._conn() as conn:
            meta = conn.execute("""
                SELECT bar_count, last_ts, fetched_at FROM candle_meta
                WHERE symbol = ? AND timeframe = ?
            """, (symbol, timeframe)).fetchone()

        if meta is None:
            return False

        bar_count, last_ts, fetched_at = meta

        # Freshness: last bar must be within 48h of now (crypto trades 24/7)
        now_ts = _now_ts()
        stale_after = 48 * 3600   # 48 hours
        if last_ts is not None and (now_ts - last_ts) > stale_after:
            logger.debug(f"CandleStore: {symbol}/{timeframe} stale (last bar {(now_ts-last_ts)//3600}h ago)")
            return False

        # Coverage: at least 80% of expected bars
        bars_per_day = _BARS_PER_DAY.get(timeframe, 24)
        expected     = days * bars_per_day * 0.80   # 80% threshold
        cutoff       = _cutoff_ts(days + 1)
        with self._conn() as conn:
            count = conn.execute("""
                SELECT COUNT(*) FROM candles
                WHERE symbol = ? AND timeframe = ? AND ts >= ?
            """, (symbol, timeframe, cutoff)).fetchone()[0]

        ok = count >= expected
        if not ok:
            logger.debug(
                f"CandleStore: {symbol}/{timeframe}/{days}d insufficient "
                f"({count:,} bars, need {expected:,.0f})"
            )
        return ok

    def list_available(self) -> List[Dict]:
        """
        Return metadata for every (symbol, timeframe) in the store.
        Each entry: {symbol, timeframe, bar_count, first_date, last_date, fetched_at, stale}
        """
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT symbol, timeframe, bar_count, first_ts, last_ts, fetched_at
                FROM candle_meta
                ORDER BY symbol, timeframe
            """).fetchall()

        now_ts = _now_ts()
        result = []
        for symbol, tf, bar_count, first_ts, last_ts, fetched_at in rows:
            age_h  = (now_ts - (last_ts or 0)) // 3600
            result.append({
                "symbol":     symbol,
                "timeframe":  tf,
                "bar_count":  bar_count or 0,
                "first_date": datetime.utcfromtimestamp(first_ts).strftime('%Y-%m-%d') if first_ts else None,
                "last_date":  datetime.utcfromtimestamp(last_ts).strftime('%Y-%m-%d')  if last_ts  else None,
                "fetched_at": fetched_at,
                "age_hours":  age_h,
                "stale":      age_h > 48,
            })
        return result

    def cleanup_stale(self, max_age_days: int = 2) -> int:
        """
        Remove (symbol, timeframe) entries whose last bar is older than max_age_days.
        Handles symbols/timeframes that fell off the watchlist and are never refreshed.
        Returns total candle rows deleted.
        """
        cutoff_ts = _cutoff_ts(max_age_days)
        with self._conn() as conn:
            stale = conn.execute("""
                SELECT symbol, timeframe FROM candle_meta
                WHERE last_ts < ? OR last_ts IS NULL
            """, (cutoff_ts,)).fetchall()

            total_deleted = 0
            for symbol, timeframe in stale:
                n = conn.execute(
                    "DELETE FROM candles WHERE symbol = ? AND timeframe = ?",
                    (symbol, timeframe)
                ).rowcount
                conn.execute(
                    "DELETE FROM candle_meta WHERE symbol = ? AND timeframe = ?",
                    (symbol, timeframe)
                )
                total_deleted += n
                logger.info(
                    f"CandleStore: purged stale {symbol}/{timeframe} "
                    f"({n:,} bars, last bar > {max_age_days}d ago)"
                )

        if total_deleted:
            logger.info(f"CandleStore: cleanup removed {total_deleted:,} stale rows total")
        return total_deleted

    def delete(self, symbol: str, timeframe: str) -> int:
        """Remove all candles for a (symbol, timeframe). Returns rows deleted."""
        with self._conn() as conn:
            n = conn.execute(
                "DELETE FROM candles WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe)
            ).rowcount
            conn.execute(
                "DELETE FROM candle_meta WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe)
            )
        logger.info(f"CandleStore: deleted {n:,} bars for {symbol}/{timeframe}")
        return n
