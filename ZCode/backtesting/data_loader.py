"""
Data loader for crypto backtests.
Fetches BTC/USD and ETH/USD OHLCV data via CCXT (Kraken primary), with
paginated historical download and local parquet caching.

Usage:
    from data_loader import load_data
    df = load_data("BTC/USD", timeframe="5m", days=200)
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Primary + fallback exchanges. These have BTC/USD & ETH/USD spot pairs and
# deep free intraday history. Tested reachable from this environment.
EXCHANGE_CHAIN = ["kraken", "coinbase", "okx"]


def _make_exchange(name: str) -> ccxt.Exchange:
    ex = getattr(ccxt, name)()
    ex.enableRateLimit = True
    return ex


def _fetch_paginated(ex: ccxt.Exchange, symbol: str, timeframe: str,
                     since_ms: int, until_ms: int) -> list[list]:
    """Walk backwards through history with pagination to build a full series."""
    limit = 1000
    all_rows: list[list] = []
    cursor = since_ms
    guard = 0
    while cursor < until_ms:
        guard += 1
        if guard > 5000:
            break
        try:
            chunk = ex.fetch_ohlcv(symbol, timeframe=timeframe,
                                   since=cursor, limit=limit)
        except Exception:
            # brief backoff then retry once
            time.sleep(2)
            try:
                chunk = ex.fetch_ohlcv(symbol, timeframe=timeframe,
                                       since=cursor, limit=limit)
            except Exception:
                break
        if not chunk:
            break
        all_rows.extend(chunk)
        last_ts = chunk[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + 1  # +1 ms to avoid dup
    return all_rows


def _dedupe_rows(rows: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = (df.drop_duplicates(subset="ts")
            .sort_values("ts")
            .drop(columns="ts")
            .set_index("datetime"))
    # tz-naive for vectorbt
    df.index = df.index.tz_convert(None)
    return df[["open", "high", "low", "close", "volume"]]


def load_data(symbol: str = "BTC/USD", timeframe: str = "5m",
              days: int = 200) -> pd.DataFrame:
    """Load cached parquet or fetch fresh OHLCV from CCXT.

    Returns a DataFrame with DatetimeIndex (tz-naive) and columns
    [open, high, low, close, volume].
    """
    cache_path = CACHE_DIR / f"{symbol.replace('/', '_')}_{timeframe}_{days}d.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        print(f"[data] cached {symbol} {timeframe}: {len(df)} rows "
              f"({df.index[0]} .. {df.index[-1]})")
        return df

    until = datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(until.timestamp() * 1000)

    last_err = None
    for name in EXCHANGE_CHAIN:
        try:
            ex = _make_exchange(name)
            print(f"[data] fetching {symbol} {timeframe} from {name} "
                  f"({days}d since {since.date()})...")
            rows = _fetch_paginated(ex, symbol, timeframe, since_ms, until_ms)
            if len(rows) < 1000:
                print(f"[data] {name} returned too few rows ({len(rows)}), "
                      f"trying next exchange")
                last_err = f"insufficient rows from {name}"
                continue
            df = _dedupe_rows(rows)
            # trim to requested window
            df = df.loc[df.index >= pd.Timestamp(since).tz_localize(None)]
            df.to_parquet(cache_path)
            print(f"[data] cached {symbol} {timeframe}: {len(df)} rows "
                  f"({df.index[0]} .. {df.index[-1]}) from {name}")
            return df
        except Exception as e:  # pragma: no cover
            last_err = str(e)
            print(f"[data] {name} failed: {last_err[:80]}")
            continue

    raise RuntimeError(f"All exchanges failed for {symbol} {timeframe}: {last_err}")


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample a base OHLCV frame to a higher timeframe (e.g. 5m -> 15m/1h)."""
    rule = timeframe
    agg = {"open": "first", "high": "max", "low": "min",
           "close": "last", "volume": "sum"}
    out = df.resample(rule, label="left", closed="left").agg(agg).dropna()
    return out


if __name__ == "__main__":
    # Smoke test: fetch both symbols on 5m, derive 15m and 1h.
    for sym in ["BTC/USD", "ETH/USD"]:
        df5 = load_data(sym, "5m", days=200)
        df15 = resample_ohlcv(df5, "15min")
        df60 = resample_ohlcv(df5, "1h")
        print(f"\n{sym}: 5m={len(df5)} 15m={len(df15)} 1h={len(df60)}")
        print(df5.tail(2))
