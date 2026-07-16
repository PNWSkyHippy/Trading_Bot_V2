"""
Deterministic tests for core/candle_validation.py (Patch A).

Covers: closed/forming-bar boundary (including the corrected publication-
grace direction and exact subsecond close+grace boundaries), session-aware
stock continuity (legitimate overnight/weekend/holiday/early-close gaps pass
only when a session authority proves them; unexplained intraday gaps and
crypto-style no-authority gaps still fail closed), alignment, relational
OHLC integrity (including explicit numeric coercion and object/string-dtype
ambiguity rejection), malformed OHLC/volume, non-monotonic and duplicate
index, NaT timestamps, OverflowError/nonfinite-timestamp rejection in every
factory, future-timestamped bars, unrecognized timeframe, subsecond
ScanCutoff precision, session-authority integration (fresh-match, stale-
mismatch, and authority-uncertain/exception propagating as rejection),
multiple-forming-row truncation, missing-bar/gap detection, the public
validator returning the ClosedCandleSeries contract (not a raw DataFrame),
construction-safety/immutability of the three data types, and entry-quote
validation.

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
    before = time.time()
    cutoff = ScanCutoff.now()
    after = time.time()
    assert before <= cutoff.epoch <= after


def test_scan_cutoff_has_subsecond_precision():
    """The crux of the precision restoration: ScanCutoff.now() must not be
    truncated to whole seconds."""
    cutoffs = [ScanCutoff.now().epoch for _ in range(20)]
    assert any(c != int(c) for c in cutoffs), (
        "expected at least one ScanCutoff.now() capture across 20 samples to "
        "have a nonzero fractional second — got only whole-second values, "
        "suggesting truncation has crept back in"
    )


def test_scan_cutoff_rejects_non_numeric_or_nonfinite_epoch():
    with pytest.raises(ValueError):
        ScanCutoff(epoch="not-a-number")
    with pytest.raises(ValueError):
        ScanCutoff(epoch=True)
    with pytest.raises(ValueError):
        ScanCutoff(epoch=float("nan"))
    with pytest.raises(ValueError):
        ScanCutoff(epoch=float("inf"))
    # Both int and float are accepted (existing int-based fixtures throughout
    # this suite must keep working).
    ScanCutoff(epoch=1_700_000_000)
    ScanCutoff(epoch=1_700_000_000.5)


def test_public_validator_returns_the_contract_not_a_raw_dataframe():
    df = _bars(10)
    cutoff = _cutoff_after(10)
    result = validate_closed_candles("AAPL", df, "5m", cutoff)
    assert isinstance(result, ClosedCandleSeries)
    assert not isinstance(result, pd.DataFrame)
    assert result.symbol == "AAPL"
    assert len(result.df) == 10


def test_closed_series_passes_unchanged():
    df = _bars(10)
    cutoff = _cutoff_after(10)
    out = validate_closed_candles("AAPL", df, "5m", cutoff)
    assert out is not None
    assert len(out.df) == 10


def test_forming_last_bar_is_dropped_not_the_whole_series():
    df = _bars(10)
    last_open = _ALIGNED_BASE + 9 * 300
    cutoff = ScanCutoff(epoch=last_open + 10)  # last bar has only just opened
    out = validate_closed_candles("AAPL", df, "5m", cutoff)
    assert out is not None
    assert len(out.df) == 9  # only the forming last row dropped


def test_multiple_forming_rows_all_dropped():
    """More than one trailing row not yet *eligible* simultaneously: a
    publication_grace_sec spanning more than one bar width produces several
    already-wall-clock-closed trailing bars all still below the
    close+grace eligibility bar simultaneously."""
    df = _bars(10)
    bar9_close = _ALIGNED_BASE + 9 * 300 + 300
    cutoff = ScanCutoff(epoch=bar9_close + 10)
    grace = 500
    out = validate_closed_candles("AAPL", df, "5m", cutoff, publication_grace_sec=grace)
    assert out is not None
    assert len(out.df) == 8


def test_only_bar_forming_rejects_entirely():
    df = _bars(1)
    cutoff = ScanCutoff(epoch=_ALIGNED_BASE + 10)
    assert validate_closed_candles("AAPL", df, "5m", cutoff) is None


def test_publication_grace_requires_close_plus_grace_not_close_minus_grace():
    """The corrected direction: a bar is eligible only once
    cutoff >= close + grace, never merely close - grace (early admission)."""
    df = _bars(2)
    close_epoch = _ALIGNED_BASE + 300 + 300  # bar[1] opens at +300, closes at +600

    cutoff_before_close = ScanCutoff(epoch=close_epoch - 5)
    out = validate_closed_candles("AAPL", df, "5m", cutoff_before_close, publication_grace_sec=60)
    assert out is not None and len(out.df) == 1

    cutoff_at_close = ScanCutoff(epoch=close_epoch)
    out = validate_closed_candles("AAPL", df, "5m", cutoff_at_close, publication_grace_sec=0)
    assert out is not None and len(out.df) == 2

    out = validate_closed_candles("AAPL", df, "5m", cutoff_at_close, publication_grace_sec=60)
    assert out is not None and len(out.df) == 1

    cutoff_close_plus_grace = ScanCutoff(epoch=close_epoch + 60)
    out = validate_closed_candles("AAPL", df, "5m", cutoff_close_plus_grace, publication_grace_sec=60)
    assert out is not None and len(out.df) == 2

    cutoff_short = ScanCutoff(epoch=close_epoch + 59)
    out = validate_closed_candles("AAPL", df, "5m", cutoff_short, publication_grace_sec=60)
    assert out is not None and len(out.df) == 1


def test_exact_subsecond_close_plus_grace_boundary():
    """With subsecond ScanCutoff precision restored, the close+grace
    boundary must be exact to the fraction of a second, not just the whole
    second."""
    df = _bars(1)
    close_epoch = _ALIGNED_BASE + 300
    grace = 10.0

    just_short = ScanCutoff(epoch=close_epoch + grace - 0.001)
    assert validate_closed_candles("AAPL", df, "5m", just_short, publication_grace_sec=grace) is None

    exact = ScanCutoff(epoch=close_epoch + grace)
    out = validate_closed_candles("AAPL", df, "5m", exact, publication_grace_sec=grace)
    assert out is not None and len(out.df) == 1

    just_over = ScanCutoff(epoch=close_epoch + grace + 0.001)
    out2 = validate_closed_candles("AAPL", df, "5m", just_over, publication_grace_sec=grace)
    assert out2 is not None and len(out2.df) == 1


def test_exact_boundary_cutoff_equals_close_is_eligible():
    df = _bars(1)
    close_epoch = _ALIGNED_BASE + 300
    assert validate_closed_candles("AAPL", df, "5m", ScanCutoff(epoch=close_epoch)) is not None
    assert validate_closed_candles("AAPL", df, "5m", ScanCutoff(epoch=close_epoch - 1)) is None


def test_unrecognized_timeframe_rejects():
    df = _bars(1)
    assert validate_closed_candles("AAPL", df, "bogus", _cutoff_after(1)) is None


def test_missing_column_rejects():
    df = _bars(2).drop(columns=["close"])
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_nonfinite_ohlc_rejects():
    df = _bars(2)
    df.iloc[-1, df.columns.get_loc("high")] = float("inf")
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_negative_infinity_ohlc_rejects():
    df = _bars(2)
    df.iloc[0, df.columns.get_loc("low")] = float("-inf")
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_nan_ohlc_rejects():
    df = _bars(2)
    df.iloc[-1, df.columns.get_loc("close")] = float("nan")
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_nonpositive_ohlc_rejects():
    df = _bars(2)
    df.iloc[0, df.columns.get_loc("low")] = 0.0
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_low_greater_than_high_rejects():
    df = _bars(2, low=5.0, high=1.0)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_open_outside_low_high_rejects():
    df = _bars(2, low=1.0, high=2.0, open=5.0, close=1.5)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_impossible_ohlc_close_outside_low_high_rejects():
    df = _bars(2, low=1.0, high=2.0, open=1.5, close=10.0)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_ohlc_touching_boundaries_is_valid():
    df = _bars(2, low=1.0, high=2.0, open=1.0, close=2.0)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is not None


def test_ohlc_string_dtype_is_coerced_numerically_not_compared_lexicographically():
    """The core numeric-coercion regression test. As raw strings, "3.0" >
    "10.0" is True lexicographically (comparing '3' > '1') even though
    3.0 < 10.0 numerically. If OHLC relational checks ran on the raw
    object/string column, a high=3.0 < low=10.0 impossible bar could slip
    through undetected (or the reverse could be falsely flagged) depending
    on the specific string values. Coercing to numeric first must always
    reach the numerically-correct verdict."""
    df = _bars(2)
    df["low"] = ["5.0", "10.0"]
    df["high"] = ["3.0", "20.0"]  # row 0: high(3.0) < low(5.0) -- numerically impossible
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_ohlc_valid_numeric_strings_are_accepted():
    df = _bars(2)
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(str)
    out = validate_closed_candles("AAPL", df, "5m", _cutoff_after(2))
    assert out is not None
    assert len(out.df) == 2


def test_ohlc_non_numeric_object_rejects():
    df = _bars(2)
    df.iloc[0, df.columns.get_loc("close")] = "not-a-number"
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_ohlc_mixed_type_object_column_rejects():
    """A column containing a mix of numeric and non-numeric-looking objects
    (e.g. a stray None or dict) must be rejected outright, not partially
    coerced."""
    df = _bars(2)
    df["high"] = df["high"].astype(object)
    df.iloc[1, df.columns.get_loc("high")] = None
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_negative_volume_rejects():
    df = _bars(2, volume=100.0)
    df.iloc[0, df.columns.get_loc("volume")] = -5.0
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_nonmonotonic_index_rejects():
    opens = [_ALIGNED_BASE + 300, _ALIGNED_BASE]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_duplicate_index_rejects():
    opens = [_ALIGNED_BASE, _ALIGNED_BASE, _ALIGNED_BASE + 300]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(3)) is None


def test_missing_bar_gap_rejects_via_continuity_when_no_authority():
    """Crypto-style (no session_authority): any gap must fail closed, no
    exceptions possible."""
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 300, _ALIGNED_BASE + 900]  # missing +600
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("BTC/USD", df, "5m", _cutoff_after(3)) is None


def test_overlapping_bars_reject_via_continuity():
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 100]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_misaligned_to_utc_grid_rejects_for_crypto_style_no_authority():
    opens = [_ALIGNED_BASE + 7, _ALIGNED_BASE + 307]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("BTC/USD", df, "5m", _cutoff_after(2)) is None


def test_nat_timestamp_rejects():
    idx = pd.DatetimeIndex([pd.Timestamp(_ALIGNED_BASE, unit="s"), pd.NaT])
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    assert validate_closed_candles("AAPL", df, "5m", _cutoff_after(2)) is None


def test_future_bar_rejects():
    df = _bars(1, start=_ALIGNED_BASE + 365 * 86400)
    cutoff = ScanCutoff(epoch=_ALIGNED_BASE)
    assert validate_closed_candles("AAPL", df, "5m", cutoff) is None


def test_empty_or_none_df_rejects():
    cutoff = ScanCutoff.now()
    assert validate_closed_candles("AAPL", None, "5m", cutoff) is None
    assert validate_closed_candles("AAPL", pd.DataFrame(), "5m", cutoff) is None


class _FakeAuthority:
    """Minimal SessionAuthority stub for testing the integration points."""
    def __init__(self, expected_open=None, raises=None, gap_verdict=True, gap_raises=None):
        self._expected_open = expected_open
        self._raises = raises
        self._gap_verdict = gap_verdict
        self._gap_raises = gap_raises

    def expected_latest_closed_bar_open(self, timeframe, cutoff):
        if self._raises is not None:
            raise self._raises
        return self._expected_open

    def is_valid_session_gap(self, prior_close, next_open, cutoff):
        if self._gap_raises is not None:
            raise self._gap_raises
        return self._gap_verdict


def test_session_authority_match_passes():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=_ALIGNED_BASE + 300)
    out = validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority)
    assert out is not None and len(out.df) == 2


def test_session_authority_mismatch_rejects_stale_bar():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=_ALIGNED_BASE + 600)
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority) is None


def test_session_authority_uncertain_propagates_as_rejection():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(expected_open=None)
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority) is None


def test_session_authority_exception_propagates_as_rejection_not_a_crash():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    authority = _FakeAuthority(raises=RuntimeError("calendar backend exploded"))
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority) is None


def test_legitimate_session_gap_passes_when_authority_confirms_it():
    """Session-aware continuity: a genuine overnight/weekend/holiday gap
    passes ONLY because the (fake) authority explicitly confirms it —
    the validator itself has no special-case gap-shape logic; it defers
    entirely to the authority's verdict."""
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 300, _ALIGNED_BASE + 3 * 86400]  # a big multi-day gap
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    cutoff = ScanCutoff(epoch=opens[-1] + 300 + 1)
    authority = _FakeAuthority(expected_open=opens[-1], gap_verdict=True)
    out = validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority)
    assert out is not None
    assert len(out.df) == 3


def test_unexplained_gap_still_fails_closed_even_with_an_authority_present():
    """The other half of session-aware continuity: having an authority does
    not mean every gap is excused — only ones the authority explicitly
    confirms. An authority that returns False/None for the gap must still
    reject, exactly like having no authority at all."""
    opens = [_ALIGNED_BASE, _ALIGNED_BASE + 300, _ALIGNED_BASE + 3 * 86400]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}, index=idx)
    cutoff = ScanCutoff(epoch=opens[-1] + 300 + 1)

    authority_false = _FakeAuthority(expected_open=opens[-1], gap_verdict=False)
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority_false) is None

    authority_none = _FakeAuthority(expected_open=opens[-1], gap_verdict=None)
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority_none) is None

    authority_raises = _FakeAuthority(expected_open=opens[-1], gap_raises=RuntimeError("boom"))
    assert validate_closed_candles("AAPL", df, "5m", cutoff, session_authority=authority_raises) is None


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


def test_entry_quote_rejects_overflow_and_nonfinite_timestamp():
    now = int(time.time())
    cutoff = ScanCutoff(epoch=now)
    assert validate_entry_quote("AAPL", 1.0, float("inf"), cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, float("-inf"), cutoff, 30, "alpaca") is None
    assert validate_entry_quote("AAPL", 1.0, float("nan"), cutoff, 30, "alpaca") is None


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
    validate_closed_candles("AAPL", None, "5m", ScanCutoff.now())
    validate_entry_quote("AAPL", float("nan"), int(time.time()), ScanCutoff.now(), 30, "alpaca")
    snap = metrics.get_snapshot()
    assert snap.get("candle_validation.reject.invalid_quote_price") == 1


# ------------------------------------------------------------------
# Validated-factory / data-class separation / construction-safety /
# immutability enforcement
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


def test_closed_candle_series_direct_construction_accepts_gaps_by_documented_design():
    """
    Scope of the construction-safety guarantee: continuity/gap-legitimacy
    for session-gapped stock data fundamentally requires a live session
    authority to adjudicate (is this specific gap a confirmed weekend/
    holiday boundary?) — and ClosedCandleSeries deliberately does not store
    a reference to one, to remain a pure, authority-independent data
    contract. __post_init__'s self-check therefore does NOT re-derive
    continuity/alignment; it re-checks everything else (see the other
    `test_closed_candle_series_direct_construction_rejects_*` tests). This
    is a documented, deliberate trade-off, not an oversight — verified here
    so a future change to this scope is a conscious decision, not a silent
    regression in either direction.
    """
    bad_df = _bars(3)
    bad_df = bad_df.drop(bad_df.index[1])  # remove the middle bar -> gap
    cutoff = _cutoff_after(3)
    series = ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=bad_df, validated_at=cutoff)
    assert len(series.df) == 2
    # But the *factory* path, which does have a real authority to consult
    # (or correctly has none, for the crypto/no-authority case), still
    # correctly rejects this exact same gapped input outright.
    assert validate_closed_candles("AAPL", bad_df, "5m", cutoff) is None


def test_closed_candle_series_direct_construction_rejects_impossible_ohlc():
    bad_df = _bars(2, low=5.0, high=1.0)
    cutoff = _cutoff_after(2)
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=bad_df, validated_at=cutoff)


def test_closed_candle_series_direct_construction_rejects_forming_bar():
    df = _bars(1)
    cutoff = ScanCutoff(epoch=_ALIGNED_BASE + 10)  # bar hasn't closed yet
    with pytest.raises(ValueError):
        ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=df, validated_at=cutoff)


def test_closed_candle_series_construction_succeeds_on_genuinely_valid_data():
    df = _bars(2)
    cutoff = _cutoff_after(2)
    series = ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=df, validated_at=cutoff)
    assert len(series.df) == 2


def test_closed_candle_series_is_immune_to_mutation_of_callers_original_dataframe():
    """Immutability: mutating the caller's original DataFrame after
    construction must not alter the wrapped data."""
    df = _bars(2)
    cutoff = _cutoff_after(2)
    series = ClosedCandleSeries(symbol="AAPL", timeframe="5m", df=df, validated_at=cutoff)
    original_close_values = series.df["close"].tolist()
    df.iloc[0, df.columns.get_loc("close")] = 99999.0  # mutate the ORIGINAL reference
    assert series.df["close"].tolist() == original_close_values
    assert 99999.0 not in series.df["close"].tolist()


def test_closed_candle_series_from_validated_factory_fails_closed_not_raises():
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


def test_held_position_price_from_broker_factory_rejects_overflow_and_nonfinite_timestamp():
    assert HeldPositionPrice.from_broker("AAPL", 1.0, float("inf"), "alpaca") is None
    assert HeldPositionPrice.from_broker("AAPL", 1.0, float("-inf"), "alpaca") is None
    assert HeldPositionPrice.from_broker("AAPL", 1.0, float("nan"), "alpaca") is None


def test_held_position_price_from_broker_factory_succeeds_on_good_input():
    result = HeldPositionPrice.from_broker("AAPL", 123.45, 1_700_000_000, "alpaca")
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
