"""Deterministic tests for paginated public crypto history fallbacks."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intelligence.backtester import Backtester


def _hourly_rows(days=45):
    end = datetime.now(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )
    start = end - timedelta(days=days)
    rows = []
    cursor = start
    price = 2000.0
    while cursor <= end:
        stamp = int(cursor.timestamp() * 1000)
        rows.append([stamp, price, price + 2, price - 2, price + 1, 100.0])
        cursor += timedelta(hours=1)
        price += 0.1
    return rows


class _Exchange:
    rateLimit = 0

    def __init__(self, name, rows=None, error=None, calls=None):
        self.name = name
        self.rows = rows or []
        self.error = error
        self.calls = calls if calls is not None else []

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls.append((self.name, symbol, timeframe, since, limit))
        if self.error:
            raise self.error
        eligible = [row for row in self.rows if row[0] >= since]
        return eligible[:limit]


def _ccxt(exchange_specs, calls):
    module = SimpleNamespace()
    for name, spec in exchange_specs.items():
        setattr(
            module,
            name,
            lambda _options, n=name, s=spec: _Exchange(
                n, rows=s.get("rows"), error=s.get("error"), calls=calls
            ),
        )
    return module


def _backtester(fake_ccxt):
    bt = Backtester.__new__(Backtester)
    bt.ccxt = fake_ccxt
    return bt


def test_long_hourly_request_uses_paginating_exchange_and_covers_window():
    calls = []
    rows = _hourly_rows(45)
    fake = _ccxt({
        "binanceus": {"rows": rows},
        "bitfinex": {"rows": []},
        "kraken": {"rows": rows[-720:]},
    }, calls)

    frame = _backtester(fake)._fetch_history_crypto_ccxt("ETH/USD", 40, "1h")

    assert frame is not None
    assert len(frame) >= 40 * 24 * 0.95
    assert frame.index.is_monotonic_increasing
    assert not frame.index.has_duplicates
    assert calls[0][0] == "binanceus"
    assert sum(1 for call in calls if call[0] == "binanceus") >= 2


def test_failed_primary_historical_exchange_falls_back_to_bitfinex():
    calls = []
    rows = _hourly_rows(45)
    fake = _ccxt({
        "binanceus": {"error": RuntimeError("market unavailable")},
        "bitfinex": {"rows": rows},
        "kraken": {"rows": rows[-720:]},
    }, calls)

    frame = _backtester(fake)._fetch_history_crypto_ccxt("ETH/USD", 40, "1h")

    assert frame is not None
    assert len(frame) >= 40 * 24 * 0.95
    assert calls[0][0] == "binanceus"
    assert any(call[0] == "bitfinex" for call in calls)
    assert not any(call[0] == "kraken" for call in calls)


def test_short_request_still_prefers_execution_venue_kraken():
    calls = []
    rows = _hourly_rows(12)
    fake = _ccxt({
        "kraken": {"rows": rows},
        "binanceus": {"rows": rows},
        "bitfinex": {"rows": rows},
    }, calls)

    frame = _backtester(fake)._fetch_history_crypto_ccxt("ETH/USD", 10, "1h")

    assert frame is not None
    assert calls[0][0] == "kraken"
    assert not any(call[0] != "kraken" for call in calls)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} crypto-history pagination tests passed")
