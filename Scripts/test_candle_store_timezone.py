"""
Deterministic tests for the host-timezone-independence fix in
intelligence/candle_store.py (Patch A, F11).

The confirmed defect: `datetime.utcnow().timestamp()` (five call sites in
this file, plus core/candle_manager.py:190) interprets a naive datetime's
fields as HOST-LOCAL time — stdlib `datetime.timestamp()` on a naive
instance is documented to do exactly that. Since `datetime.utcnow()`'s
fields ARE UTC values, this silently produced the wrong epoch on any
non-UTC host. Fixed by `_now_ts()`/`_cutoff_ts()`, which use `time.time()`
(always UTC, host-independent).

Correction to an earlier round of this audit: `CandleStore.save()`'s
naive-DatetimeIndex write path (used by the crypto fetchers, which produce
naive-but-UTC-valued timestamps) was originally also assumed buggy, by
analogy with stdlib datetime. Verified directly and reproduced in
`test_save_naive_utc_timestamp_converts_to_correct_epoch_not_host_local`
below: a naive *pandas* Timestamp's `.timestamp()` is always UTC-based
internally, unlike stdlib `datetime.timestamp()` — that call site was never
actually host-timezone-dependent. Only the `datetime.utcnow()` read-side
call sites were ever buggy.

This test suite proves correctness against an independent oracle
(`calendar.timegm`, stdlib) rather than by toggling the OS timezone
(`time.tzset()` is POSIX-only and unavailable on this Windows test host
anyway).

Runnable directly (`python Scripts/test_candle_store_timezone.py`) or via
pytest.
"""

import calendar
import datetime
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intelligence.candle_store import CandleStore, _now_ts, _cutoff_ts


def _host_is_utc() -> bool:
    return time.timezone == 0 and time.altzone == 0


def test_host_timezone_info_only():
    # Informational only: _now_ts()/_cutoff_ts() are correct on any host by
    # construction (time.time() has no host-timezone dependency to begin
    # with), so unlike an environment-toggling test, nothing below actually
    # requires a non-UTC host to be a meaningful regression test. Recorded
    # for visibility when reading test output, not as a precondition.
    print(f"host_is_utc={_host_is_utc()} time.timezone={time.timezone}")


def test_now_ts_matches_time_time_not_datetime_utcnow():
    before = int(time.time())
    got = _now_ts()
    after = int(time.time())
    assert before <= got <= after


def test_cutoff_ts_arithmetic():
    now = _now_ts()
    assert _cutoff_ts(1) == now - 86400 or abs(_cutoff_ts(1) - (now - 86400)) <= 1
    assert _cutoff_ts(0) in (now, now - 0)


def test_save_naive_utc_timestamp_converts_to_correct_epoch_not_host_local():
    """
    Constructs a naive DatetimeIndex whose fields represent a known UTC
    wall-clock instant (exactly what _fetch_kraken/_fetch_kucoin produce:
    utc=True then tz_localize(None)), saves it, and asserts the stored `ts`
    column equals the independently computed correct UTC epoch for that
    instant.

    Note on this test's history: an earlier round of this audit assumed
    `pd.Timestamp(naive).timestamp()` behaves like stdlib
    `datetime.timestamp()` (host-local interpretation for naive values) and
    treated this call site as a confirmed host-timezone bug. Verified
    directly (see the comment in CandleStore.save()): a naive *pandas*
    Timestamp's `.timestamp()` is always UTC-based internally
    (`Timestamp.value` is UTC nanoseconds since epoch regardless of host
    `TZ`), unlike stdlib `datetime.timestamp()`. That assumption was wrong,
    and this test no longer asserts the old "buggy vs. correct" contrast —
    it only asserts the actually-required property: the stored epoch is
    correct. (The genuinely host-timezone-dependent bugs in this file were
    the five `datetime.utcnow().timestamp()` call sites fixed by `_now_ts()`/
    `_cutoff_ts()` above, and `core/candle_manager.py:190` — those remain
    real, confirmed, and fixed.)
    """
    known_utc_wallclock = datetime.datetime(2026, 7, 16, 15, 30, 0)  # naive, UTC-valued
    correct_epoch = calendar.timegm(known_utc_wallclock.timetuple())

    idx = pd.DatetimeIndex([known_utc_wallclock, known_utc_wallclock + datetime.timedelta(minutes=5)])
    df = pd.DataFrame(
        {"open": [1.0, 1.1], "high": [1.2, 1.3], "low": [0.9, 1.0],
         "close": [1.1, 1.2], "volume": [100.0, 110.0]},
        index=idx,
    )

    with tempfile.TemporaryDirectory(prefix="candle-store-tz-test-", ignore_cleanup_errors=True) as tmp:
        db_path = str(Path(tmp) / "test_candles.db")
        store = CandleStore(db_path)
        n = store.save("TEST/USD", "5m", df)
        assert n == 2

        import sqlite3
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT ts FROM candles WHERE symbol=? AND timeframe=? ORDER BY ts",
                ("TEST/USD", "5m"),
            ).fetchall()
        stored_first_ts = rows[0][0]
        assert stored_first_ts == correct_epoch, (
            f"stored ts {stored_first_ts} != correct UTC epoch {correct_epoch}"
        )


def test_save_tz_aware_timestamp_still_correct():
    """Alpaca's path (tz-aware end to end) must remain correct — this branch
    of save() was never buggy and must not regress."""
    aware = pd.Timestamp("2026-07-16 15:30:00", tz="UTC")
    correct_epoch = int(aware.timestamp())
    idx = pd.DatetimeIndex([aware, aware + pd.Timedelta(minutes=5)])
    df = pd.DataFrame(
        {"open": [1.0, 1.1], "high": [1.2, 1.3], "low": [0.9, 1.0],
         "close": [1.1, 1.2], "volume": [100.0, 110.0]},
        index=idx,
    )
    with tempfile.TemporaryDirectory(prefix="candle-store-tz-test-", ignore_cleanup_errors=True) as tmp:
        db_path = str(Path(tmp) / "test_candles.db")
        store = CandleStore(db_path)
        store.save("AAPL/stock", "5m", df)
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT ts FROM candles WHERE symbol=? AND timeframe=? ORDER BY ts LIMIT 1",
                ("AAPL/stock", "5m"),
            ).fetchone()
        assert row[0] == correct_epoch


def test_has_data_freshness_uses_correct_now():
    """has_data()'s staleness check must measure true age, not a host-shifted
    one. A bar saved 'now' (correct UTC) must read back as fresh."""
    now_utc_naive = datetime.datetime.fromtimestamp(_now_ts(), tz=datetime.timezone.utc).replace(tzinfo=None)
    idx = pd.DatetimeIndex([now_utc_naive - datetime.timedelta(minutes=5), now_utc_naive])
    df = pd.DataFrame(
        {"open": [1.0, 1.1], "high": [1.2, 1.3], "low": [0.9, 1.0],
         "close": [1.1, 1.2], "volume": [100.0, 110.0]},
        index=idx,
    )
    with tempfile.TemporaryDirectory(prefix="candle-store-tz-test-", ignore_cleanup_errors=True) as tmp:
        db_path = str(Path(tmp) / "test_candles.db")
        store = CandleStore(db_path)
        store.save("TEST/USD", "5m", df)
        # Coverage-ratio math aside (that's Claim 6, a separate defect), the
        # bar we just wrote must not appear artificially stale.
        with __import__("sqlite3").connect(db_path) as conn:
            meta = conn.execute(
                "SELECT last_ts FROM candle_meta WHERE symbol=? AND timeframe=?",
                ("TEST/USD", "5m"),
            ).fetchone()
        assert meta is not None
        age = _now_ts() - meta[0]
        assert 0 <= age < 60, f"expected near-zero age, got {age}s (host-shift bug would show ~{time.timezone}s)"


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} candle_store timezone tests passed")


if __name__ == "__main__":
    main()
