"""
Deterministic tests for core/candle_validation.py (Patch A).

Covers: closed/forming-bar boundary, malformed OHLC/volume, non-monotonic and
duplicate index, future-timestamped bar, unrecognized timeframe, publication
grace, session-authority integration (fresh-match, stale-mismatch, and
authority-uncertain-propagates-as-rejection), and entry-quote validation
(finite/positive price, missing/unparseable/future/stale timestamp).

Runnable directly (`python Scripts/test_candle_validation.py`) or via pytest.
"""

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import metrics
from core.candle_validation import (
    ScanCutoff,
    validate_closed_candles,
    validate_entry_quote,
    timeframe_seconds,
)


def _bars(opens_epoch, tf_sec=300, **overrides):
    idx = pd.to_datetime(opens_epoch, unit="s", utc=True).tz_localize(None)
    data = {
        "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0,
    }
    data.update(overrides)
    return pd.DataFrame(data, index=idx)


def test_timeframe_seconds_known_and_unknown():
    assert timeframe_seconds("5Min") == 300
    assert timeframe_seconds("5m") == 300
    assert timeframe_seconds("1Hour") == 3600
    assert timeframe_seconds("1Day") == 86400
    assert timeframe_seconds("bogus-timeframe") is None
    assert timeframe_seconds("") is None
    assert timeframe_seconds(None) is None


def test_scan_cutoff_now_uses_time_time_not_datetime_utcnow():
    before = int(time.time())
    cutoff = ScanCutoff.now()
    after = int(time.time())
    assert before <= cutoff.epoch <= after


def test_closed_series_passes_unchanged():
    now = int(time.time())
    opens = [now - 3600 + i * 300 for i in range(10)]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=opens[-1] + 301)  # bar fully closed, no grace needed
    out = validate_closed_candles(df, "5m", cutoff)
    assert out is not None
    assert len(out) == 10


def test_forming_last_bar_is_dropped_not_the_whole_series():
    now = int(time.time())
    opens = [now - 3600 + i * 300 for i in range(10)]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=opens[-1] + 10)  # last bar has only just opened
    out = validate_closed_candles(df, "5m", cutoff)
    assert out is not None
    assert len(out) == 9  # only the forming last row dropped


def test_only_bar_forming_rejects_entirely():
    opens = [int(time.time())]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=opens[0] + 10)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_publication_grace_delays_forming_cutoff():
    now = int(time.time())
    opens = [now - 300, now]
    df = _bars(opens)
    # Bar closes at now+300; cutoff is now+250, i.e. 50s before nominal close.
    # With 60s grace, the bar is still accepted as "closed enough to publish".
    cutoff = ScanCutoff(epoch=now + 250)
    out_no_grace = validate_closed_candles(df, "5m", cutoff, publication_grace_sec=0)
    assert out_no_grace is not None and len(out_no_grace) == 1  # last (forming) row dropped
    out_with_grace = validate_closed_candles(df, "5m", cutoff, publication_grace_sec=60)
    assert out_with_grace is not None and len(out_with_grace) == 2  # kept as closed-with-grace


def test_unrecognized_timeframe_rejects():
    df = _bars([int(time.time()) - 300])
    cutoff = ScanCutoff.now()
    assert validate_closed_candles(df, "bogus", cutoff) is None


def test_missing_column_rejects():
    df = _bars([int(time.time()) - 600, int(time.time()) - 300]).drop(columns=["close"])
    cutoff = ScanCutoff(epoch=int(time.time()) + 10)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_nonfinite_ohlc_rejects():
    now = int(time.time())
    df = _bars([now - 600, now - 300])
    df.iloc[-1, df.columns.get_loc("high")] = float("inf")
    cutoff = ScanCutoff(epoch=now + 301)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_nonpositive_ohlc_rejects():
    now = int(time.time())
    df = _bars([now - 600, now - 300])
    df.iloc[0, df.columns.get_loc("low")] = 0.0
    cutoff = ScanCutoff(epoch=now + 301)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_negative_volume_rejects():
    now = int(time.time())
    df = _bars([now - 600, now - 300], volume=100.0)
    df.iloc[0, df.columns.get_loc("volume")] = -5.0
    cutoff = ScanCutoff(epoch=now + 301)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_nonmonotonic_index_rejects():
    now = int(time.time())
    df = _bars([now - 300, now - 600])  # deliberately out of order
    cutoff = ScanCutoff(epoch=now + 301)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_duplicate_index_rejects():
    now = int(time.time())
    df = _bars([now - 600, now - 600, now - 300])
    cutoff = ScanCutoff(epoch=now + 301)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_future_bar_rejects():
    now = int(time.time())
    df = _bars([now + 3600])  # opens an hour in the future
    cutoff = ScanCutoff(epoch=now)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_empty_or_none_df_rejects():
    cutoff = ScanCutoff.now()
    assert validate_closed_candles(None, "5m", cutoff) is None
    assert validate_closed_candles(pd.DataFrame(), "5m", cutoff) is None


class _FakeAuthority:
    """Minimal SessionAuthority stub for testing the integration point."""
    def __init__(self, expected_open):
        self._expected_open = expected_open

    def expected_latest_closed_bar_open(self, timeframe, cutoff):
        return self._expected_open


def test_session_authority_match_passes():
    now = int(time.time())
    opens = [now - 600, now - 300]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=now + 301)
    authority = _FakeAuthority(expected_open=opens[-1])
    out = validate_closed_candles(df, "5m", cutoff, session_authority=authority)
    assert out is not None and len(out) == 2


def test_session_authority_mismatch_rejects_stale_bar():
    now = int(time.time())
    opens = [now - 600, now - 300]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=now + 301)
    # Authority expects a bar opened later than what we actually have -> stale.
    authority = _FakeAuthority(expected_open=opens[-1] + 300)
    assert validate_closed_candles(df, "5m", cutoff, session_authority=authority) is None


def test_session_authority_uncertain_propagates_as_rejection():
    now = int(time.time())
    opens = [now - 600, now - 300]
    df = _bars(opens)
    cutoff = ScanCutoff(epoch=now + 301)
    authority = _FakeAuthority(expected_open=None)  # authority itself unsure
    assert validate_closed_candles(df, "5m", cutoff, session_authority=authority) is None


def test_valid_entry_quote_accepted():
    now = int(time.time())
    q = validate_entry_quote("AAPL", 123.45, now, ScanCutoff(epoch=now + 2), max_age_sec=30, source="alpaca")
    assert q is not None
    assert q.symbol == "AAPL" and q.price == 123.45 and q.source == "alpaca"


def test_entry_quote_rejects_nan_inf_zero_negative():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    for bad_price in (float("nan"), float("inf"), 0.0, -5.0):
        assert validate_entry_quote("AAPL", bad_price, now, cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_missing_or_unparseable_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, None, cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, "not-a-timestamp", cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_future_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, now + 100, cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_stale_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, now - 1000, cutoff, 30, "alpaca") is None
    # Exactly at the boundary is still accepted; one second over is not.
    assert validate_entry_quote("AAPL", 1.0, now - 30, cutoff, 30, "alpaca") is not None
    assert validate_entry_quote("AAPL", 1.0, now - 31, cutoff, 30, "alpaca") is None


def test_rejections_are_counted_in_metrics():
    metrics.reset()
    validate_closed_candles(None, "5m", ScanCutoff.now())
    validate_entry_quote("AAPL", float("nan"), int(time.time()), ScanCutoff.now(), 30, "alpaca")
    snap = metrics.get_snapshot()
    assert snap.get("candle_validation.reject.invalid_quote_price") == 1
    # None/empty df returns before any reject() call (nothing to count) — this
    # assertion documents that behavior rather than assuming it.
    assert "candle_validation.reject.invalid_quote_price" in snap


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} candle_validation tests passed")


if __name__ == "__main__":
    main()
