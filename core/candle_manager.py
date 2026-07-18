"""
=============================================================
  CANDLE MANAGER  v1.0
  Unified candle data layer for the entire trading system.

  Replaces scattered yfinance/CCXT/Alpaca calls across:
    - scanners/market_scanner.py
    - core/position_monitor.py
    - logs/intelligence/backtester.py
    - logs/intelligence/optimizer.py
    - breakout_receiver.py
    - web_dashboard.py

  Architecture
  ------------
  1. CandleStore SQLite (existing) — persistent OHLCV cache
  2. symbol_source_registry table — which source works for each symbol
  3. In-memory registry dict — loaded at boot, updated on fetch
  4. 5-minute refresh loop — background daemon pre-fetches all watchlist symbols
  5. Multi-source fallback — CCXT→yfinance (crypto), Alpaca→yfinance (stocks)

  Consumer interface
  ------------------
    from core.candle_manager import candle_manager
    df = candle_manager.get("BTC/USD", "1h", limit=200)
    df = candle_manager.get("AAPL", "5Min", limit=100)

  Threading
  ---------
  Only the refresh loop ever calls external APIs. All consumers read
  from the SQLite cache via CandleStore (WAL mode, safe for concurrent reads).
  Eliminates the ccxt thread-safety issue in position_monitor.
=============================================================

  PATCH NOTES — 2026-07-18, Step 6b (Reconciled Safe Patch Sequence,
  reports/agent_pipeline/20260717-085541/final_unified_report.md §6 item 6,
  narrow slice only — NOT the full Patch B data contract). Spec:
  reports/agent_pipeline/20260716-082429/final_unified_report.md §13.

  Bug: Alpaca's native 1Hour stock bars are plain UTC-hour-boundary,
  extended-hours buckets, not anchored to the 09:30 ET regular-session
  open — a genuine 09:30-10:00 ET partial opening bar can never be
  recovered by slicing already-1h-aggregated data (per-trade detail is
  gone by the time Alpaca returns 1Hour bars).

  Fix, applied by agent (Ron reviewing before commit):
    - _fetch_alpaca() now branches: for the "1h" timeframe specifically,
      delegates to the new _fetch_alpaca_session_hourly() instead of
      calling get_bars(..., "1Hour", ...) directly. Every other timeframe
      (5Min/15Min/1Day, and all of crypto which never routes through
      Alpaca) is untouched — same single get_bars() call as before.
    - New method _fetch_alpaca_session_hourly(api, symbol, limit): fetches
      native 30Min bars, filters each trading day to its regular session
      via core.stock_calendar_authority.get_authority(), and resamples
      into session-anchored hourly buckets via the new
      resample_30m_to_session_hourly() (see that module's own patch
      notes). If the calendar authority can't confirm a date's session
      (stale/unrefreshed), that date falls back to its raw, unfiltered
      30Min bars rather than being dropped (logged via logger.warning) —
      "degraded, not dark." Only the resampled 1Hour result is cached
      under the existing timeframe key; raw 30Min bars are not separately
      cached.

  Explicitly NOT touched: the broader Option B extended-hours-filtering
  decision for other timeframes/consumers — see
  core/stock_calendar_authority.py's own patch notes and module docstring.

  Tests: Scripts/test_candle_manager_session_hourly_resample.py (new,
  5/5 passing, includes a dedicated test proving non-1h timeframes never
  call get_calendar()). Full existing regression suite re-run with zero
  regressions.

  To back out: remove the "1h" branch and _fetch_alpaca_session_hourly()
  from _fetch_alpaca() below, restoring the single unconditional
  get_bars(..., tf_alpaca, ...) call for all stock timeframes. Also revert
  the corresponding change in core/stock_calendar_authority.py. No other
  files were touched by this patch.
=============================================================
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timeframe helpers
# ---------------------------------------------------------------------------

# Map between different API timeframe formats
_TF_CCXT_TO_YF  = {"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d"}
_TF_ALPACA_TO_YF = {"1Min":"1m","5Min":"5m","15Min":"15m","1Hour":"1h","1Day":"1d"}
_TF_BARS_PER_DAY = {"1m":1440,"5m":288,"15m":96,"1h":24,"4h":6,"1d":1,
                    "1Min":1440,"5Min":288,"15Min":96,"1Hour":24,"1Day":1}

def _bars_to_days(limit: int, timeframe: str) -> int:
    """Convert a bar limit to approximate number of days needed."""
    bpd = _TF_BARS_PER_DAY.get(timeframe, 24)
    return max(2, int(limit / bpd) + 2)

def _normalise_tf(timeframe: str) -> str:
    """Normalise timeframe to CCXT/yfinance format (e.g. '5Min' → '5m')."""
    mapping = {
        "1Min":"1m","5Min":"5m","15Min":"15m","30Min":"30m",
        "1Hour":"1h","4Hour":"4h","1Day":"1d",
        "1H":"1h","1D":"1d",
    }
    return mapping.get(timeframe, timeframe)

def _alpaca_tf(timeframe: str) -> str:
    """Convert any timeframe to Alpaca format."""
    mapping = {
        "1m":"1Min","5m":"5Min","15m":"15Min","30m":"30Min",
        "1h":"1Hour","4h":"4Hour","1d":"1Day",
    }
    return mapping.get(timeframe, timeframe)


# ---------------------------------------------------------------------------
# Source constants
# ---------------------------------------------------------------------------
SRC_KRAKEN   = "kraken"
SRC_ALPACA   = "alpaca"
SRC_YFINANCE = "yfinance"
SRC_KUCOIN   = "kucoin"

# KuCoin runs in parallel with Kraken — no auth required, large US-accessible symbol universe.
# Kraken tried first (existing preferred-source registry), KuCoin second (BTC/USDT pairs),
# yfinance last resort.
# Note: Binance 451 geo-blocks US IPs; Bybit geo-blocks US; Coinbase requires CDP auth.
_CRYPTO_SOURCES = [SRC_KRAKEN, SRC_KUCOIN, SRC_YFINANCE]
_STOCK_SOURCES  = [SRC_ALPACA, SRC_YFINANCE]

# Crypto tickers that consistently fail yfinance (NoneType errors) — skip directly to Kraken.
# yfinance uses SYMBOL-USD format but many newer/meme tokens are not listed there.
_YFINANCE_CRYPTO_SKIP: set[str] = {
    "DASH-USD", "DOGE-USD", "WIF-USD", "BONK-USD", "TRUMP-USD",
    "MELANIA-USD", "FLOKI-USD", "RUNE-USD", "ZRX-USD", "REN-USD",
    "ANKR-USD", "TIA-USD", "DYM-USD", "PYTH-USD", "JTO-USD",
    "BOME-USD", "W-USD", "EREBRO-USD",   # delisted — hangs yfinance fetch
    "EOS-USD",                           # frequent empty Yahoo response
}

# Limit simultaneous yfinance calls — Yahoo rate-limits aggressively.
# 2 concurrent slots + exponential backoff in _fetch_yfinance().
_yf_semaphore = threading.Semaphore(2)


# ---------------------------------------------------------------------------
# CandleManager
# ---------------------------------------------------------------------------

class CandleManager:
    """
    Single source of truth for OHLCV data.
    All consumers call get() — cache hit returns instantly,
    cache miss triggers a multi-source fetch and caches the result.
    """

    def __init__(self):
        # Import CandleStore (lives in logs/intelligence — path added to sys.path by bot)
        try:
            from intelligence.candle_store import get_store
            self._store = get_store()
        except ImportError:
            logger.warning("CandleStore unavailable — candle_manager running without persistence")
            self._store = None

        # In-memory source registry: "SYMBOL|asset_class" → preferred_source
        self._registry: Dict[str, str] = {}
        self._registry_lock = threading.Lock()

        self._init_registry_table()
        self._load_registry()

        # Refresh loop state
        self._refresh_thread: Optional[threading.Thread] = None
        self._refresh_stop   = threading.Event()
        self._refresh_symbols: List[Tuple[str, str]] = []  # [(symbol, asset_class)]

        # Unreachable log path
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._unreachable_log = os.path.join(_root, "logs", "unreachable_symbols.log")

        logger.info("CandleManager initialised")

    # -----------------------------------------------------------------------
    # Registry DB
    # -----------------------------------------------------------------------

    def _init_registry_table(self):
        if self._store is None:
            return
        try:
            with self._store._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbol_source_registry (
                        symbol           TEXT NOT NULL,
                        asset_class      TEXT NOT NULL,
                        preferred_source TEXT,
                        last_success_ts  INTEGER,
                        last_fail_ts     INTEGER,
                        fail_count       INTEGER DEFAULT 0,
                        PRIMARY KEY (symbol, asset_class)
                    )
                """)
        except Exception as e:
            logger.warning(f"CandleManager: registry table init failed: {e}")

    def _load_registry(self):
        if self._store is None:
            return
        try:
            with self._store._conn() as conn:
                rows = conn.execute(
                    "SELECT symbol, asset_class, preferred_source FROM symbol_source_registry"
                ).fetchall()
            with self._registry_lock:
                for symbol, asset_class, preferred in rows:
                    if preferred:
                        self._registry[f"{symbol}|{asset_class}"] = preferred
            logger.info(f"CandleManager: loaded {len(rows)} symbol sources from registry")
        except Exception as e:
            logger.warning(f"CandleManager: registry load failed: {e}")

    def _update_registry(self, symbol: str, asset_class: str, source: str, success: bool):
        """Update both in-memory dict and DB row."""
        key = f"{symbol}|{asset_class}"
        # time.time() is UTC epoch seconds regardless of host timezone;
        # datetime.utcnow().timestamp() is NOT (see F11 in the market-data
        # caching audit — a naive datetime's .timestamp() is interpreted as
        # host-local time, silently shifting the epoch on non-UTC hosts).
        now = int(time.time())

        with self._registry_lock:
            if success:
                self._registry[key] = source

        if self._store is None:
            return
        try:
            with self._store._conn() as conn:
                if success:
                    conn.execute("""
                        INSERT INTO symbol_source_registry
                            (symbol, asset_class, preferred_source, last_success_ts, fail_count)
                        VALUES (?, ?, ?, ?, 0)
                        ON CONFLICT(symbol, asset_class) DO UPDATE SET
                            preferred_source = excluded.preferred_source,
                            last_success_ts  = excluded.last_success_ts,
                            fail_count       = 0
                    """, (symbol, asset_class, source, now))
                else:
                    conn.execute("""
                        INSERT INTO symbol_source_registry
                            (symbol, asset_class, last_fail_ts, fail_count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(symbol, asset_class) DO UPDATE SET
                            last_fail_ts = excluded.last_fail_ts,
                            fail_count   = fail_count + 1
                    """, (symbol, asset_class, now))
        except Exception as e:
            logger.debug(f"CandleManager: registry update failed for {symbol}: {e}")

    def _get_source_order(self, symbol: str, asset_class: str) -> List[str]:
        """Return sources in preferred order — try last-known-good first."""
        key = f"{symbol}|{asset_class}"
        with self._registry_lock:
            preferred = self._registry.get(key)

        defaults = _CRYPTO_SOURCES if asset_class == "crypto" else _STOCK_SOURCES
        if preferred and preferred in defaults:
            rest = [s for s in defaults if s != preferred]
            return [preferred] + rest
        return defaults

    # -----------------------------------------------------------------------
    # Fetchers (one per source)
    # -----------------------------------------------------------------------

    def _fetch_kraken(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from Kraken via CCXT."""
        try:
            import ccxt
            import config
            tf = _normalise_tf(timeframe)
            ex = ccxt.kraken({
                "apiKey":          config.KRAKEN_API_KEY,
                "secret":          config.KRAKEN_SECRET_KEY,
                "enableRateLimit": True,
                "timeout":         10000,
            })
            ohlcv = ex.fetch_ohlcv(symbol, tf, limit=limit + 1)
            if not ohlcv:
                return None
            df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
            df.set_index("timestamp", inplace=True)
            if len(df) > 1:
                df = df.iloc[:-1]   # drop forming bar
            return df if not df.empty else None
        except Exception as e:
            logger.debug(f"[CandleManager] Kraken fetch failed for {symbol}/{timeframe}: {e}")
            return None

    def _fetch_alpaca(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from Alpaca."""
        try:
            import alpaca_trade_api as tradeapi
            import config
            api = tradeapi.REST(
                config.ALPACA_API_KEY,
                config.ALPACA_SECRET_KEY,
                base_url=config.ALPACA_BASE_URL
            )
            tf_alpaca = _alpaca_tf(_normalise_tf(timeframe))
            if _normalise_tf(timeframe) == "1h":
                return self._fetch_alpaca_session_hourly(api, symbol, limit)
            bars = api.get_bars(symbol, tf_alpaca, limit=limit + 1, adjustment="raw").df
            if bars.empty:
                return None
            bars.columns = [c.lower() for c in bars.columns]
            if len(bars) > 1:
                bars = bars.iloc[:-1]   # drop forming bar
            return bars
        except Exception as e:
            logger.debug(f"[CandleManager] Alpaca fetch failed for {symbol}/{timeframe}: {e}")
            return None

    def _fetch_alpaca_session_hourly(self, api, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        """
        1-hour stock bars can't be sliced from Alpaca's native 1Hour endpoint
        into a genuine 09:30-10:00 ET partial opening bar — by the time
        Alpaca returns 1Hour data, the underlying trades are already
        aggregated into whole-UTC-hour extended-hours buckets (see
        core/stock_calendar_authority.py module docstring, live-checked
        2026-07-16). Instead: fetch native 30Min bars, filter each trading
        day to its regular session via StockCalendarAuthority, and resample
        into session-anchored hourly buckets ourselves.

        If the calendar authority can't confirm a given date's session
        (stale/not-yet-refreshed schedule), that date falls back to its raw,
        unfiltered 30Min bars rather than being dropped — degraded data
        beats no data for a live exit check, and downstream validation
        already fails closed independently on stale/wrong session data.
        """
        import time as _time
        from core.stock_calendar_authority import get_authority, resample_30m_to_session_hourly

        authority = get_authority(api)
        # ~13 30Min bars per regular session. Overfetch generously so the
        # post-resample result still has >= `limit` hourly bars.
        raw_limit = max(limit * 2 + 20, 60)
        raw = api.get_bars(symbol, "30Min", limit=raw_limit, adjustment="raw").df
        if raw.empty:
            return None
        raw.columns = [c.lower() for c in raw.columns]
        if len(raw) > 1:
            raw = raw.iloc[:-1]   # drop forming bar
        raw.index = (
            raw.index.tz_localize(None) if raw.index.tz is None
            else raw.index.tz_convert("UTC").tz_localize(None)
        )

        dates = sorted({ts.date() for ts in raw.index})
        chunks = []
        now_epoch = int(_time.time())
        for d in dates:
            day_raw = raw[raw.index.date == d]
            window = authority.get_session(d, now_epoch)
            if window is None:
                if authority.refresh(now_epoch=now_epoch):
                    window = authority.get_session(d, now_epoch)
            if window is None:
                logger.warning(
                    f"[CandleManager] StockCalendarAuthority has no confirmed "
                    f"session for {symbol} {d} — using unfiltered 30Min bars "
                    f"for that date instead of session-resampled hourly bars"
                )
                chunks.append(day_raw)
                continue
            open_epoch, close_epoch = window
            chunks.append(resample_30m_to_session_hourly(day_raw, open_epoch, close_epoch))

        if not chunks:
            return None
        out = pd.concat(chunks).sort_index()
        return out.tail(limit) if len(out) > limit else out

    def _fetch_yfinance(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from yfinance with semaphore + exponential backoff retry."""
        import yfinance as yf
        tf = _normalise_tf(timeframe)
        yf_sym = symbol.replace("/", "-")
        if yf_sym in _YFINANCE_CRYPTO_SKIP:
            return None
        days = _bars_to_days(limit, tf)
        interval_map = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m",
                        "1h":"1h","4h":"4h","1d":"1d"}
        interval = interval_map.get(tf, tf)
        period   = f"{min(days, 60)}d" if tf in ("1m","5m","15m","30m") else f"{days}d"

        with _yf_semaphore:
            for attempt in range(3):
                yf_logger = logging.getLogger("yfinance")
                old_yf_level = yf_logger.level
                try:
                    # yfinance logs empty Yahoo responses as ERROR before raising/returning.
                    # CandleManager already records the failed source and unreachable symbol,
                    # so suppress the library noise during this controlled fallback attempt.
                    yf_logger.setLevel(logging.CRITICAL)
                    df = yf.download(yf_sym, period=period, interval=interval,
                                     progress=False, auto_adjust=True)
                    if df is None or df.empty:
                        return None
                    df.columns = [c.lower() if isinstance(c, str) else c[0].lower()
                                  for c in df.columns]
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    if len(df) > 1:
                        df = df.iloc[:-1]   # drop forming bar
                    return df if not df.empty else None
                except Exception as e:
                    wait = 2 ** attempt   # 1s, 2s, 4s
                    logger.debug(
                        f"[CandleManager] yfinance attempt {attempt+1}/3 failed "
                        f"for {symbol}/{timeframe}: {e} — retrying in {wait}s"
                    )
                    if attempt < 2:
                        time.sleep(wait)
                finally:
                    yf_logger.setLevel(old_yf_level)
        return None

    def _fetch_kucoin(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetch from KuCoin via CCXT — no auth required (public endpoint).
        KuCoin uses BTC/USDT pairs; we translate from BTC/USD internally.
        US-accessible, large symbol universe, well-supported by CCXT.

        Supported timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 1w
        Note: Binance/Bybit geo-block US IPs; KuCoin does not.
        """
        try:
            import ccxt
            tf = _normalise_tf(timeframe)

            # KuCoin timeframe map
            _KC_TF = {
                "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
                "1h":"1h","2h":"2h","4h":"4h","6h":"6h","8h":"8h","12h":"12h",
                "1d":"1d","1w":"1week",
            }
            if tf not in _KC_TF:
                return None   # unsupported timeframe, skip silently

            # Symbol translation: BTC/USD → BTC/USDT  (KuCoin trades USDT pairs, not USD)
            parts = symbol.split("/")
            if len(parts) == 2 and parts[1] == "USD":
                kc_symbol = f"{parts[0]}/USDT"
            else:
                kc_symbol = symbol   # already in USDT or other quote form

            ex = ccxt.kucoin({"enableRateLimit": True, "timeout": 10000})
            ohlcv = ex.fetch_ohlcv(kc_symbol, _KC_TF[tf], limit=limit + 1)
            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
            df.set_index("timestamp", inplace=True)
            if len(df) > 1:
                df = df.iloc[:-1]   # drop forming bar
            return df if not df.empty else None

        except Exception as e:
            logger.debug(f"[CandleManager] KuCoin fetch failed for {symbol}/{timeframe}: {e}")
            return None

    def _fetch_from_source(self, symbol: str, timeframe: str,
                           limit: int, source: str) -> Optional[pd.DataFrame]:
        """Dispatch to the correct fetcher."""
        if source == SRC_KRAKEN:
            return self._fetch_kraken(symbol, timeframe, limit)
        if source == SRC_ALPACA:
            return self._fetch_alpaca(symbol, timeframe, limit)
        if source == SRC_YFINANCE:
            return self._fetch_yfinance(symbol, timeframe, limit)
        if source == SRC_KUCOIN:
            return self._fetch_kucoin(symbol, timeframe, limit)
        logger.warning(f"[CandleManager] Unknown source: {source}")
        return None

    def _fetch_multi(self, symbol: str, asset_class: str,
                     timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Try all sources in preferred order. Cache on first success."""
        if self._is_unfetchable(symbol):
            return None   # Tradovate futures / cross-pairs — skip silently
        sources = self._get_source_order(symbol, asset_class)
        for source in sources:
            df = self._fetch_from_source(symbol, timeframe, limit, source)
            if df is not None and not df.empty:
                # Strip duplicate columns before caching and returning — duplicate
                # column names (e.g. two 'volume' columns after lowercasing) cause
                # "truth value of a Series is ambiguous" in candle_store.save() and
                # "cannot convert series to float" in downstream strategies.
                if df.columns.duplicated().any():
                    df = df.loc[:, ~df.columns.duplicated()]
                if self._store:
                    try:
                        self._store.save(self._store_key(symbol, asset_class), timeframe, df)
                    except Exception as e:
                        logger.debug(f"[CandleManager] Cache save failed for {symbol}: {e}")
                self._update_registry(symbol, asset_class, source, success=True)
                return df
            self._update_registry(symbol, asset_class, source, success=False)

        # All sources failed
        self._log_unreachable(symbol, timeframe)
        return None

    def _log_unreachable(self, symbol: str, timeframe: str):
        """Append to unreachable_symbols.log — for manual cleanup."""
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"{ts} | {symbol} | {timeframe} | all sources failed\n"
            os.makedirs(os.path.dirname(self._unreachable_log), exist_ok=True)
            with open(self._unreachable_log, "a") as f:
                f.write(line)
            logger.warning(f"[CandleManager] {symbol}/{timeframe} unreachable on all sources — logged")
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @staticmethod
    def _is_unfetchable(symbol: str) -> bool:
        """Return True for symbols that can never be fetched (Tradovate futures, etc.)."""
        s = symbol.upper()
        return (
            s.endswith(":BTNL") or          # Tradovate futures e.g. ALGOUSD:BTNL
            s.endswith("ZUSD") or           # e.g. SOXLZUSD
            s.endswith("/BTC") or           # crypto cross-pairs not on yfinance
            ":" in s                        # any exchange-specific notation
        )

    @staticmethod
    def _store_key(symbol: str, asset_class: str) -> str:
        """
        Namespace stock symbols in the candle store to prevent collision with
        any same-named crypto token (e.g. stock META vs crypto META token).
        Crypto symbols already carry "/" so they are inherently unique.
        """
        if asset_class == "stock" and "/" not in symbol:
            return f"{symbol}/stock"
        return symbol

    def get(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Get OHLCV candles for a symbol/timeframe.
        Returns cached data if fresh, otherwise fetches and caches.
        """
        if self._is_unfetchable(symbol):
            return None
        asset_class = "crypto" if "/" in symbol else "stock"
        tf = _normalise_tf(timeframe)
        store_sym = self._store_key(symbol, asset_class)

        # Cache hit?
        if self._store:
            days = _bars_to_days(limit, tf)
            if self._store.has_data(store_sym, tf, days):
                df = self._store.load(store_sym, tf, days)
                if df is not None and not df.empty:
                    return df.tail(limit)

        # Cache miss — fetch
        return self._fetch_multi(symbol, asset_class, tf, limit)

    def prefetch(self, symbol: str, timeframe: str, limit: int = 300) -> bool:
        """Force-fetch and cache. Returns True if successful."""
        asset_class = "crypto" if "/" in symbol else "stock"
        tf = _normalise_tf(timeframe)
        df = self._fetch_multi(symbol, asset_class, tf, limit)
        return df is not None

    def invalidate_store(self, symbol: str, asset_class: str, timeframe: str):
        """Remove a namespaced entry from the candle store."""
        if self._store:
            store_sym = self._store_key(symbol, asset_class)
            try:
                self._store.delete(store_sym, _normalise_tf(timeframe))
            except Exception:
                pass

    def invalidate(self, symbol: str, timeframe: str):
        """Force next get() to re-fetch (e.g. after a known stale period)."""
        if self._store:
            try:
                self._store.delete(symbol, _normalise_tf(timeframe))
            except Exception:
                pass

    def list_available(self) -> list:
        """Return metadata for every (symbol, timeframe) in the cache.
        Proxies CandleStore.list_available() so the optimizer UI can use
        the main system cache without any separate store reference."""
        if self._store:
            try:
                return self._store.list_available()
            except Exception:
                pass
        return []

    def delete(self, symbol: str, timeframe: str) -> int:
        """Remove all candles for (symbol, timeframe) from the main cache.
        Returns rows deleted. Also clears the in-memory registry entry."""
        n = 0
        if self._store:
            try:
                n = self._store.delete(symbol, _normalise_tf(timeframe))
            except Exception:
                pass
        # Remove from in-memory registry too
        key = f"{symbol}|{_normalise_tf(timeframe)}"
        with self._registry_lock:
            self._registry.pop(key, None)
        return n

    def get_registry(self) -> Dict[str, str]:
        """Return copy of in-memory source registry."""
        with self._registry_lock:
            return dict(self._registry)

    # -----------------------------------------------------------------------
    # Background refresh loop
    # -----------------------------------------------------------------------

    def start_refresh_loop(self,
                           crypto_symbols: List[str],
                           stock_symbols:  List[str],
                           crypto_tfs:     List[str] = None,
                           stock_tfs:      List[str] = None,
                           interval_sec:   int = 300):
        """
        Start a background daemon thread that refreshes all watchlist symbols
        every `interval_sec` seconds (default 5 min = matches crypto scan interval).

        Call once from bot_engine.py after startup.
        """
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.warning("CandleManager refresh loop already running")
            return

        crypto_tfs = crypto_tfs or ["5m", "15m", "1h"]
        stock_tfs  = stock_tfs  or ["5Min", "15Min", "1Hour"]

        self._refresh_symbols = (
            [(s, "crypto") for s in crypto_symbols] +
            [(s, "stock")  for s in stock_symbols]
        )
        self._refresh_tfs = {
            "crypto": [_normalise_tf(tf) for tf in crypto_tfs],
            "stock":  [_normalise_tf(tf) for tf in stock_tfs],
        }
        self._refresh_interval = interval_sec
        self._refresh_stop.clear()

        self._refresh_thread = threading.Thread(
            target=self._refresh_worker,
            name="candle-refresh",
            daemon=True,
        )
        self._refresh_thread.start()
        logger.info(
            f"CandleManager refresh loop started — "
            f"{len(crypto_symbols)} crypto + {len(stock_symbols)} stock symbols, "
            f"every {interval_sec}s"
        )

    def stop_refresh_loop(self):
        self._refresh_stop.set()

    def _refresh_worker(self):
        """Background worker — refreshes all symbols on interval."""
        logger.info("[CandleManager] Refresh worker started")
        _last_cleanup = 0.0   # track last stale-purge time

        while not self._refresh_stop.is_set():
            t0 = time.time()
            ok = fail = skipped_stock = 0
            try:
                from core.market_calendar import is_us_equity_regular_session_now

                stock_refresh_open = is_us_equity_regular_session_now()
            except Exception as e:
                logger.debug(f"[CandleManager] Market calendar unavailable; refreshing stocks normally: {e}")
                stock_refresh_open = True

            for symbol, asset_class in self._refresh_symbols:
                if self._refresh_stop.is_set():
                    break
                if asset_class == "stock" and not stock_refresh_open:
                    skipped_stock += len(self._refresh_tfs.get(asset_class, ["1h"]))
                    continue
                if symbol in _CRYPTO_BLACKLIST and asset_class == "crypto":
                    continue
                tfs = self._refresh_tfs.get(asset_class, ["1h"])
                for tf in tfs:
                    try:
                        df = self._fetch_multi(symbol, asset_class, tf, limit=300)
                        if df is not None:
                            ok += 1
                        else:
                            fail += 1
                    except Exception as e:
                        logger.debug(f"[CandleManager] Refresh error {symbol}/{tf}: {e}")
                        fail += 1
                    # Small sleep between fetches to avoid rate limits
                    time.sleep(0.1)

            elapsed = time.time() - t0
            if skipped_stock:
                logger.info(
                    f"[CandleManager] Refresh complete — "
                    f"{ok} ok / {fail} failed / {skipped_stock} stock skipped "
                    f"(market closed) in {elapsed:.1f}s"
                )
            else:
                logger.info(
                    f"[CandleManager] Refresh complete — "
                    f"{ok} ok / {fail} failed in {elapsed:.1f}s"
                )

            # Once per 24 hours: purge stale (symbol, timeframe) entries
            now = time.time()
            if self._store and (now - _last_cleanup) > 86400:
                try:
                    self._store.cleanup_stale(max_age_days=7)
                except Exception as _ce:
                    logger.debug(f"[CandleManager] Stale cleanup error: {_ce}")
                _last_cleanup = now

            # Wait for next interval
            self._refresh_stop.wait(timeout=max(0, self._refresh_interval - elapsed))

        logger.info("[CandleManager] Refresh worker stopped")


# ---------------------------------------------------------------------------
# Stablecoin / pegged token blacklist (never trade these)
# ---------------------------------------------------------------------------
_CRYPTO_BLACKLIST = {
    "USDT/USD", "USDC/USD", "DAI/USD", "BUSD/USD", "TUSD/USD",
    "USDS/USD", "USDE/USD", "FDUSD/USD", "USDP/USD", "FRAX/USD",
    "LUSD/USD", "PYUSD/USD", "USDD/USD", "GUSD/USD", "SUSD/USD",
    "PAXG/USD", "XAUT/USD", "STETH/USD", "CBETH/USD", "RETH/USD",
    "WSTETH/USD", "WBTC/USD",
}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
candle_manager = CandleManager()
