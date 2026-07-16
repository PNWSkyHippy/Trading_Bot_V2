"""
Deterministic tests for core/candle_validation.py (Patch A).

Covers: closed/forming-bar boundary (including the corrected publication-grace
direction — eligible only at close+grace, not close-grace), continuity,
alignment, relational OHLC integrity, malformed OHLC/volume, non-monotonic and
duplicate index, NaT timestamps, future-timestamped bars, unrecognized
timeframe, session-authority integration (fresh-match, stale-mismatch,
authority-uncertain, and authority-raises all propagate as rejection),
multiple-forming-row truncation, missing-bar/gap detection, exact-boundary
cases, validated-factory enforcement on the three data types, and entry-quote
validation (finite/positive price, missing/unparseable/future/stale
timestamp).

Runnable directly (`python Scripts/test_candle_validation.py`) or via pytest.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import metrics
from core.candle_validation import (
    ScanCutoff,
    ClosedCandleSeries,
    EntryQuoteSnapshot,
    HeldPositionPrice,
    validate_closed_candles,
    validate_entry_quote,
    timeframe_seconds,
)

# A UTC-midnight-aligned epoch, divisible by every timeframe this module
# supports (60/300/900/1800/3600/7200/14400/86400) — used as the base for
# every "valid" fixture so continuity/alignment checks pass by construction,
# with individual tests deliberately breaking exactly one property.
_ALIGNED_BASE = (int(time.time()) // 86400) * 86400


def _bars(n, start=_ALIGNED_BASE, tf_sec=300, **overrides):
    """n grid-aligned, continuous bars starting at `start`, spaced tf_sec apart."""
    opens = [start + i * tf_sec for i in range(n)]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    data = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}
    data.update(overrides)
    return pd.DataFrame(data, index=idx)


def _cutoff_after(n, start=_ALIGNED_BASE, tf_sec=300, extra=1):
    """A cutoff exactly `extra` seconds after the n-th bar (0-indexed) closes."""
    last_open = start + (n - 1) * tf_sec
    return ScanCutoff(epoch=last_open + tf_sec + extra)


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


def test_scan_cutoff_rejects_non_int_epoch():
    with pytest.raises(ValueError):
        ScanCutoff(epoch="not-an-int")
    with pytest.raises(ValueError):
        ScanCutoff(epoch=1.5)


def test_closed_series_passes_unchanged():
    df = _bars(10)
    cutoff = _cutoff_after(10)
    out = validate_closed_candles(df, "5m", cutoff)
    assert out is not None
    assert len(out) == 10


def test_forming_last_bar_is_dropped_not_the_whole_series():
    df = _bars(10)
    last_open = _ALIGNED_BASE + 9 * 300
    cutoff = ScanCutoff(epoch=last_open + 10)  # last bar has only just opened
    out = validate_closed_candles(df, "5m", cutoff)
    assert out is not None
    assert len(out) == 9  # only the forming last row dropped


def test_multiple_forming_rows_all_dropped():
    """Adversarial: more than one trailing row is not yet *eligible*
    simultaneously. This cannot happen from wall-clock closure alone in a
    contiguous series (only one bar can be genuinely mid-formation at any
    instant; anything after it is a distinct 'future_bar' case) — but a
    publication_grace_sec spanning more than one bar width produces exactly
    this: several already-wall-clock-closed trailing bars are all still
    below the close+grace eligibility bar simultaneously. The truncation
    loop must drop all of them, not just the last one."""
    df = _bars(10)
    bar9_close = _ALIGNED_BASE + 9 * 300 + 300
    cutoff = ScanCutoff(epoch=bar9_close + 10)  # every bar has closed by wall clock
    grace = 500  # spans more than one 5-min bar width
    out = validate_closed_candles(df, "5m", cutoff, publication_grace_sec=grace)
    assert out is not None
    assert len(out) == 8  # indices 0-7 remain eligible; 8 and 9 both dropped


def test_only_bar_forming_rejects_entirely():
    df = _bars(1)
    cutoff = ScanCutoff(epoch=_ALIGNED_BASE + 10)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_publication_grace_requires_close_plus_grace_not_close_minus_grace():
    """The corrected direction: a bar is eligible only once
    cutoff >= close + grace, never merely close - grace (early admission)."""
    df = _bars(2)
    close_epoch = _ALIGNED_BASE + 300 + 300  # bar[1] opens at +300, closes at +600

    # Just BEFORE close: never eligible regardless of grace.
    cutoff_before_close = ScanCutoff(epoch=close_epoch - 5)
    out = validate_closed_candles(df, "5m", cutoff_before_close, publication_grace_sec=60)
    assert out is not None and len(out) == 1  # bar[1] dropped as forming

    # Exactly at close, zero grace: eligible.
    cutoff_at_close = ScanCutoff(epoch=close_epoch)
    out = validate_closed_candles(df, "5m", cutoff_at_close, publication_grace_sec=0)
    assert out is not None and len(out) == 2

    # At close, but grace > 0 required and not yet elapsed: NOT eligible.
    out = validate_closed_candles(df, "5m", cutoff_at_close, publication_grace_sec=60)
    assert out is not None and len(out) == 1  # bar[1] still dropped — grace not elapsed

    # close + grace exactly: eligible (boundary is inclusive).
    cutoff_close_plus_grace = ScanCutoff(epoch=close_epoch + 60)
    out = validate_closed_candles(df, "5m", cutoff_close_plus_grace, publication_grace_sec=60)
    assert out is not None and len(out) == 2

    # close + grace - 1: still not eligible (one second short).
    cutoff_short = ScanCutoff(epoch=close_epoch + 59)
    out = validate_closed_candles(df, "5m", cutoff_short, publication_grace_sec=60)
    assert out is not None and len(out) == 1


def test_exact_boundary_cutoff_equals_close_is_eligible():
    df = _bars(1)
    close_epoch = _ALIGNED_BASE + 300
    assert validate_closed_candles(df, "5m", ScanCutoff(epoch=close_epoch)) is not None
    assert validate_closed_candles(df, "5m", ScanCutoff(epoch=close_epoch - 1)) is None


def test_unrecognized_timeframe_rejects():
    df = _bars(1)
    assert validate_closed_candles(df, "bogus", _cutoff_after(1)) is None


def test_missing_column_rejects():
    df = _bars(2).drop(columns=["close"])
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_nonfinite_ohlc_rejects():
    df = _bars(2)
    df.iloc[-1, df.columns.get_loc("high")] = float("inf")
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_negative_infinity_ohlc_rejects():
    df = _bars(2)
    df.iloc[0, df.columns.get_loc("low")] = float("-inf")
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_nan_ohlc_rejects():
    df = _bars(2)
    df.iloc[-1, df.columns.get_loc("close")] = float("nan")
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_nonpositive_ohlc_rejects():
    df = _bars(2)
    df.iloc[0, df.columns.get_loc("low")] = 0.0
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_low_greater_than_high_rejects():
    df = _bars(2, low=5.0, high=1.0)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_open_outside_low_high_rejects():
    df = _bars(2, low=1.0, high=2.0, open=5.0, close=1.5)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_close_outside_low_high_rejects():
    df = _bars(2, low=1.0, high=2.0, open=1.5, close=10.0)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_ohlc_touching_boundaries_is_valid():
    """open==low and close==high (or vice versa) are legitimate, not impossible."""
    df = _bars(2, low=1.0, high=2.0, open=1.0, close=2.0)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is not None


def test_negative_volume_rejects():
    df = _bars(2, volume=100.0)
    df.iloc[0, df.columns.get_loc("volume")] = -5.0
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_nonmonotonic_index_rejects():
    opens = [_ALIGNED_BASE + 300, _ALIGNED_BASE]  # deliberately reversed
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_duplicate_index_rejects():
    opens = [_ALIGNED_BASE, _ALIGNED_BASE, _ALIGNED_BASE + 300]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(3)) is None


def test_missing_bar_gap_rejects_via_continuity():
    """A bar missing from the middle of the series (a real provider gap, not
    a forming-bar or malformed-timestamp issue) must be rejected — Patch A's
    pure validator has no backfill/gap-policy layer yet (that's B8, later)."""
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 300, _ALIGNED_BASE + 900]  # missing +600
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(3)) is None


def test_overlapping_bars_reject_via_continuity():
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 100]  # spacing != 300s for 5m
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_misaligned_to_utc_grid_rejects_for_crypto_style_no_authority():
    opens = [_ALIGNED_BASE + 7, _ALIGNED_BASE + 307]  # offset by 7s from the grid
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_nat_timestamp_rejects():
    idx = pd.DatetimeIndex([pd.Timestamp(_ALIGNED_BASE, unit="s"), pd.NaT])
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles(df, "5m", _cutoff_after(2)) is None


def test_future_bar_rejects():
    df = _bars(1, start=_ALIGNED_BASE + 365 * 86400)  # a year in the future
    cutoff = ScanCutoff(epoch=_ALIGNED_BASE)
    assert validate_closed_candles(df, "5m", cutoff) is None


def test_empty_or_none_df_rejects():
    cutoff = ScanCutoff.now()
    assert validate_closed_candles(None, "5m", cutoff) is None
    assert validate_closed_candles(pd.DataFrame(), "5m", cutoff) is None


class _FakeAuthority:
    """Minimal SessionAuthority stub for testing the integration point."""
    def __init__(self, expected_open=None, raises=None):
        self._expected_open = expected_open
        self._raises = raises

    def expected_latest_closed_bar_open(self, timeframe, cutoff):
        if self._raises is not None:
            raise self._raises
        return self._expected_open


def test_session_authority_match_passes():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=_ALIGNED_BASE + 300)
    out = validate_closed_candles(df, "5m", cutoff, session_authority=authority)
    assert out is not None and len(out) == 2


def test_session_authority_mismatch_rejects_stale_bar():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=_ALIGNED_BASE + 600)  # expects a later bar
    assert validate_closed_candles(df, "5m", cutoff, session_authority=authority) is None


def test_session_authority_uncertain_propagates_as_rejection():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=None)
    assert validate_closed_candles(df, "5m", cutoff, session_authority=authority) is None


def test_session_authority_exception_propagates_as_rejection_not_a_crash():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(raises=RuntimeError("calendar backend exploded"))
    # Must not raise out of validate_closed_candles — must fail closed.
    assert validate_closed_candles(df, "5m", cutoff, session_authority=authority) is None


def test_valid_entry_quote_accepted():
    now = int(time.time())
    q = validate_entry_quote("AAPL", 123.45, now, ScanCutoff(epoch=now + 2), max_age_sec=30, source="alpaca")
    assert q is not None
    assert q.symbol == "AAPL" and q.price == 123.45 and q.source == "alpaca"


def test_entry_quote_rejects_nan_inf_zero_negative():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    for bad_price in (float("nan"), float("inf"), float("-inf"), 0.0, -5.0):
        assert validate_entry_quote("AAPL", bad_price, now, cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_missing_or_unparseable_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, None, cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, "not-a-timestamp", cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, -5, cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_future_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, now + 100, cutoff, 30, "alpaca") is None


def test_entry_quote_rejects_stale_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, now - 1000, cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, now - 30, cutoff, 30, "alpaca") is not None
    assert validate_entry_quote("AAPL", 1.0, now - 31, cutoff, 30, "alpaca") is None


def test_rejections_are_counted_in_metrics():
    metrics.reset()
    validate_closed_candles(None, "5m", ScanCutoff.now())
    validate_entry_quote("AAPL", float("nan"), int(time.time()), ScanCutoff.now(), 30, "alpaca")
    snap = metrics.get_snapshot()
    assert snap.get("candle_validation.reject.invalid_quote_price") == 1


# ------------------------------------------------------------------
# Validated-factory / data-class separation enforcement
# ------------------------------------------------------------------

def test_closed_candle_series_direct_construction_rejects_bad_structure():
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="", timeframe="5m", df=_bars(1), validated_at=ScanCutoff.now())
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="AAPL", timeframe="bogus", df=_bars(1), validated_at=ScanCutoff.now())
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=pd.DataFrame(), validated_at=ScanCutoff.now())
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=_bars(1).drop(columns=["high"]), validated_at=ScanCutoff.now())


def test_closed_candle_series_from_validated_factory_fails_closed_not_raises():
    # Bad input to the factory returns None, it does not raise — only direct
    # construction with structurally-bad data raises.
    result = ClosedCandleSeries.from_validated("AAPL", None, "5m", ScanCutoff.now())
    assert result is None
    result2 = ClosedCandleSeries.from_validated("AAPL", _bars(1), "bogus", ScanCutoff.now())
    assert result2 is None


def test_closed_candle_series_from_validated_factory_succeeds_on_good_input():
    cutoff = _cutoff_after(2)
    result = ClosedCandleSeries.from_validated("AAPL", _bars(2), "5m", cutoff)
    assert result is not None
    assert result.symbol == "AAPL" and len(result.df) == 2


def test_entry_quote_snapshot_direct_construction_rejects_bad_data():
    cutoff = ScanCutoff.now()
    with pytest.raises(ValueError):
        EntryQuoteSnapshot(symbol="", price=1.0, quote_epoch=1, source="x", scan_cutoff=cutoff)
    with pytest.raises(ValueError):
        EntryQuoteSnapshot(symbol="AAPL", price=float("nan"), quote_epoch=1, source="x", scan_cutoff=cutoff)
    with pytest.raises(ValueError):
        EntryQuoteSnapshot(symbol="AAPL", price=1.0, quote_epoch=-1, source="x", scan_cutoff=cutoff)
    with pytest.raises(ValueError):
        EntryQuoteSnapshot(symbol="AAPL", price=1.0, quote_epoch=1, source="", scan_cutoff=cutoff)


def test_held_position_price_direct_construction_rejects_bad_data():
    with pytest.raises(ValueError):
        HeldPositionPrice(symbol="", price=1.0, fetched_epoch=1, broker="alpaca")
    with pytest.raises(ValueError):
        HeldPositionPrice(symbol="AAPL", price=-1.0, fetched_epoch=1, broker="alpaca")
    with pytest.raises(ValueError):
        HeldPositionPrice(symbol="AAPL", price=1.0, fetched_epoch=-1, broker="alpaca")
    with pytest.raises(ValueError):
        HeldPositionPrice(symbol="AAPL", price=1.0, fetched_epoch=1, broker="")


def test_held_position_price_from_broker_factory_fails_closed():
    assert HeldPositionPrice.from_broker("AAPL", float("nan"), 123, "alpaca") is None
    assert HeldPositionPrice.from_broker("AAPL", -1.0, 123, "alpaca") is None
    assert HeldPositionPrice.from_broker("AAPL", 1.0, "not-a-timestamp", "alpaca") is None
    assert HeldPositionPrice.from_broker("AAPL", 1.0, -5, "alpaca") is None


def test_held_position_price_from_broker_factory_succeeds_on_good_input():
    result = HeldPositionPrice.from_broker("AAPL", 123.45, 1_800_000_000, "alpaca")
    assert result is not None
    assert result.symbol == "AAPL" and result.price == 123.45 and result.broker == "alpaca"


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} candle_validation tests passed")


if __name__ == "__main__":
    main()
