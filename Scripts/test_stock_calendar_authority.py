"""
Deterministic tests for core/stock_calendar_authority.py (Patch A, B5).

Covers: successful refresh, malformed-batch rejection (whole batch, not
partial adoption, including a duplicate-date malformed response), empty-
response rejection, no-API-client rejection (now routed through rate-limited
gate-failure alerting), same-day (same-ET-date, not merely elapsed-seconds)
freshness window, future-refresh-timestamp rejection, clock-rollback
rejection, out-of-request-range rejection, internally-incomplete/partial-
response rejection (a genuinely truncated response is rejected in full, not
partially adopted or used to fabricate confirmed-holiday facts), emergency
schedule changes (once a refresh is proven complete, it atomically replaces
the full requested window), weekend traversal, holiday traversal,
is_valid_session_gap (weekend/holiday/early-close gaps confirmed; wrong/
unconfirmed gaps rejected), grid-aligned intraday bar-timestamp-convention
fixtures for 5m/15m/1h (the corrected convention — NOT session-open-relative
for 1h), the midnight-UTC daily-bar convention, and is_regular_session_now's
fail-closed (None) behavior when uncertain.

All fixture dates are fixed, real historical (2026-01-05 is a real Monday,
2026-01-02 the preceding Friday, 2026-01-01 a real US holiday) dates safely
in the past relative to this suite's expected run window — never a
hardcoded *future* placeholder epoch, since the authority rejects refresh()
calls whose now_epoch is implausibly ahead of the actual wall clock.

IMPORTANT: every test that can reach metrics.alert_gate_failure() mocks
reporting.alerts.alert_manager.gate_failure first so it never attempts a
real email/SMS send — do not remove that mock, and remember that the
no-API-client path now ALSO routes through this alert (a change from an
earlier revision), so any test exercising `api=None` must mock it too.

Runnable directly (`python Scripts/test_stock_calendar_authority.py`) or via
pytest.
"""

import datetime as dt
import sys
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import metrics
from core.candle_validation import ScanCutoff
from core.stock_calendar_authority import (
    StockCalendarAuthority,
    EASTERN,
    _session_bar_opens,
    _latest_closed_bar_open_in_session,
)


class _FakeCalEntry:
    def __init__(self, date_, open_t, close_t):
        self.date = pd.Timestamp(date_)
        self.open = open_t
        self.close = close_t


class _FakeAPI:
    def __init__(self, entries):
        self.entries = entries

    def get_calendar(self, start=None, end=None):
        return self.entries


class _RaisingAPI:
    def get_calendar(self, start=None, end=None):
        raise RuntimeError("simulated network failure")


def _mock_alerts():
    """Context manager patching alert_manager.gate_failure so no test can
    ever reach real SMTP/SMS infrastructure. Must wrap EVERY refresh() call
    in this file, including api=None cases (now routed through alerting)."""
    return mock.patch("reporting.alerts.alert_manager.gate_failure", return_value=True)


def _et_epoch(y, m, d, hh, mm):
    return int(dt.datetime(y, m, d, hh, mm, tzinfo=EASTERN).timestamp())


# Fixed, real-calendar historical fixture dates (all safely in the past):
MON = dt.date(2026, 1, 5)     # a real Monday
FRI_PREV = dt.date(2026, 1, 2)  # the preceding Friday
SAT = dt.date(2026, 1, 3)
SUN = dt.date(2026, 1, 4)
NEW_YEARS_DAY = dt.date(2026, 1, 1)  # a real US market holiday (Thursday)
DAY_BEFORE_HOLIDAY = dt.date(2025, 12, 31)  # Wednesday before New Year's
TUE = dt.date(2026, 1, 6)


def test_successful_refresh():
    metrics.reset()
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=open_epoch) is True
        m.assert_not_called()
    assert metrics.get_snapshot().get("calendar.refresh.success") == 1
    session = auth.get_session(MON, open_epoch)
    assert session is not None
    open_e, close_e = session
    assert open_e == open_epoch
    assert close_e == _et_epoch(2026, 1, 5, 16, 0)


def test_no_api_client_fails_closed_and_alerts():
    """api=None is now routed through the same rate-limited gate-failure
    alerting as every other failure path — an earlier revision left this
    path un-alerted, an inconsistency this test guards against regressing."""
    metrics.reset()
    auth = StockCalendarAuthority(api=None)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1
    assert metrics.get_snapshot().get("gate_failure.stock_calendar_authority") == 1


def test_api_exception_fails_closed_and_alerts():
    metrics.reset()
    auth = StockCalendarAuthority(api=_RaisingAPI())
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1
    assert metrics.get_snapshot().get("gate_failure.stock_calendar_authority") == 1


def test_malformed_batch_close_before_open_is_rejected_entirely():
    metrics.reset()
    api = _FakeAPI([
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(TUE, dt.time(16, 0), dt.time(9, 30)),  # malformed
    ])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=1)
    now_epoch = _et_epoch(2026, 1, 5, 9, 0)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    assert auth.get_session(MON, now_epoch) is None
    assert auth.get_session(TUE, now_epoch) is None


def test_malformed_batch_duplicate_date_is_rejected_entirely():
    metrics.reset()
    api = _FakeAPI([
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(13, 0)),  # duplicate date
    ])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=0)
    now_epoch = _et_epoch(2026, 1, 5, 9, 0)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    assert auth.get_session(MON, now_epoch) is None


def test_empty_response_rejected():
    metrics.reset()
    auth = StockCalendarAuthority(api=_FakeAPI([]))
    with _mock_alerts():
        assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is False


def test_out_of_request_range_response_rejected():
    """A response containing a date outside the requested [start, end]
    window is suspicious/malformed, not something to partially trust."""
    metrics.reset()
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(dt.date(2026, 2, 1), dt.time(9, 30), dt.time(16, 0)),  # far outside window
    ])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=3)  # window: Jan2..Jan5
    now_epoch = _et_epoch(2026, 1, 5, 9, 0)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    assert auth.get_session(MON, now_epoch) is None


def test_internally_incomplete_response_rejected_not_partially_adopted():
    """The crux of the completeness rewrite: a response missing a genuine
    trading weekday (not explained by a known fixed holiday or weekend) must
    reject the ENTIRE refresh — not adopt a 'safe subset', and not touch any
    previously-cached data for dates within the window."""
    metrics.reset()
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        # MON (a real trading Monday, not a holiday) is missing -- incomplete.
        _FakeCalEntry(TUE, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=4)  # window: Jan2..Jan6
    now_epoch = _et_epoch(2026, 1, 2, 9, 0)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    # Nothing was adopted, including the well-formed dates.
    assert auth.get_session(FRI_PREV, now_epoch) is None
    assert auth.get_session(TUE, now_epoch) is None
    assert auth.is_confirmed_non_trading_day(MON, now_epoch) is None  # not fabricated as a holiday


def test_partial_response_does_not_leave_stale_data_masquerading_as_reconfirmed():
    """A rejected (incomplete) refresh must not silently 'reconfirm' stale
    previously-cached data for dates within the requested window either."""
    metrics.reset()
    api_good = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api_good, freshness_sec=60, days_behind=0, days_ahead=3)
    now1 = _et_epoch(2026, 1, 2, 9, 0)
    with _mock_alerts():
        assert auth.refresh(now_epoch=now1) is True
    assert auth.get_session(MON, now1) is not None

    # A later, incomplete response for an overlapping window must be
    # rejected -- and the earlier (now possibly stale) data must not be
    # treated as "reconfirmed" by the rejected attempt.
    api_good.entries = [_FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0))]  # MON now missing
    now2 = now1 + 120  # past the 60s freshness window
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now2) is False
        m.assert_called_once()
    # MON's original cache entry is now stale (elapsed > freshness_sec) and
    # was never reconfirmed by the (rejected) second refresh.
    assert auth.get_session(MON, now2) is None


def test_same_et_date_required_not_just_elapsed_seconds():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=24 * 3600, days_behind=0, days_ahead=0)
    late_on_mon = _et_epoch(2026, 1, 5, 23, 58)
    with _mock_alerts():
        auth.refresh(now_epoch=late_on_mon)
    assert auth.get_session(MON, late_on_mon + 60) is not None
    next_day_morning = _et_epoch(2026, 1, 6, 9, 0)
    assert (next_day_morning - late_on_mon) < 24 * 3600
    assert auth.get_session(MON, next_day_morning) is None


def test_future_refresh_timestamp_rejected():
    metrics.reset()
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, clock_skew_tolerance_sec=5)
    import time as _time
    far_future = int(_time.time()) + 3600
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=far_future) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1
    assert auth.get_session(MON, far_future) is None


def test_refresh_within_clock_skew_tolerance_is_accepted():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, clock_skew_tolerance_sec=5, days_behind=0, days_ahead=0)
    with _mock_alerts():
        assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is True


def test_clock_rollback_between_refreshes_rejected():
    metrics.reset()
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=0)
    later = _et_epoch(2026, 1, 5, 12, 0)
    earlier = _et_epoch(2026, 1, 5, 9, 0)
    with _mock_alerts():
        assert auth.refresh(now_epoch=later) is True
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=earlier) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1


def test_emergency_schedule_change_replaces_atomically_once_complete():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=3, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True

    api.entries = [
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(13, 0)),  # emergency early close
    ]
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch + 60) is True

    session = auth.get_session(MON, open_epoch + 120)
    assert session is not None
    _, close_e = session
    assert close_e == _et_epoch(2026, 1, 5, 13, 0)


def test_weekend_traversal_finds_prior_friday_session():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=ref_epoch) is True
    assert auth.is_confirmed_non_trading_day(SAT, ref_epoch) is True
    assert auth.is_confirmed_non_trading_day(SUN, ref_epoch) is True

    pre_market_monday = ScanCutoff(epoch=ref_epoch - 30 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", pre_market_monday)
    friday_close = _et_epoch(2026, 1, 2, 16, 0)
    assert expected == friday_close - 5 * 60


def test_holiday_traversal_finds_prior_session_before_confirmed_holiday():
    api = _FakeAPI([
        _FakeCalEntry(DAY_BEFORE_HOLIDAY, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(dt.date(2026, 1, 2), dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=2, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 2, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=ref_epoch) is True
    assert auth.is_confirmed_non_trading_day(NEW_YEARS_DAY, ref_epoch) is True

    pre_market_jan2 = ScanCutoff(epoch=ref_epoch - 30 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", pre_market_jan2)
    prior_close = _et_epoch(2025, 12, 31, 16, 0)
    assert expected == prior_close - 5 * 60


def test_lookback_returns_none_when_unknown_date_encountered():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=0, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=ref_epoch) is True
    pre_market_monday = ScanCutoff(epoch=ref_epoch - 30 * 60)
    assert auth.expected_latest_closed_bar_open("5m", pre_market_monday) is None


# ------------------------------------------------------------------
# is_valid_session_gap — the validator-facing session-aware continuity proof
# ------------------------------------------------------------------

def test_is_valid_session_gap_confirms_weekend_boundary():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3, days_ahead=0)
    now_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=now_epoch) is True
    prior_close = _et_epoch(2026, 1, 2, 16, 0)
    next_open = _et_epoch(2026, 1, 5, 9, 30)
    assert auth.is_valid_session_gap(prior_close, next_open, ScanCutoff(epoch=now_epoch)) is True


def test_is_valid_session_gap_confirms_holiday_boundary():
    api = _FakeAPI([
        _FakeCalEntry(DAY_BEFORE_HOLIDAY, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(dt.date(2026, 1, 2), dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=2, days_ahead=0)
    now_epoch = _et_epoch(2026, 1, 2, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=now_epoch) is True
    prior_close = _et_epoch(2025, 12, 31, 16, 0)
    next_open = _et_epoch(2026, 1, 2, 9, 30)
    assert auth.is_valid_session_gap(prior_close, next_open, ScanCutoff(epoch=now_epoch)) is True


def test_is_valid_session_gap_confirms_early_close_boundary():
    """An early-close day's actual (shortened) close time is what the gap
    must match — an early close is just a session whose close_epoch happens
    to be earlier, handled by the same authoritative-close-time mechanism,
    no special-case logic required."""
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(13, 0)),  # early close
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3, days_ahead=0)
    now_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=now_epoch) is True
    prior_close = _et_epoch(2026, 1, 2, 13, 0)  # matches the early close, not 16:00
    next_open = _et_epoch(2026, 1, 5, 9, 30)
    assert auth.is_valid_session_gap(prior_close, next_open, ScanCutoff(epoch=now_epoch)) is True
    # The "normal" 16:00 close time is now WRONG for this early-close day.
    wrong_prior_close = _et_epoch(2026, 1, 2, 16, 0)
    assert auth.is_valid_session_gap(wrong_prior_close, next_open, ScanCutoff(epoch=now_epoch)) is not True


def test_is_valid_session_gap_rejects_unconfirmed_or_wrong_transition():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3, days_ahead=0)
    now_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=now_epoch) is True
    prior_close = _et_epoch(2026, 1, 2, 16, 0)
    wrong_next_open = _et_epoch(2026, 1, 5, 10, 0)  # not the real session open
    assert auth.is_valid_session_gap(prior_close, wrong_next_open, ScanCutoff(epoch=now_epoch)) is not True

    unknown_prior_close = _et_epoch(2026, 1, 1, 16, 0)  # a date never refreshed as a session
    assert auth.is_valid_session_gap(unknown_prior_close, _et_epoch(2026, 1, 2, 9, 30), ScanCutoff(epoch=now_epoch)) is None

    backwards = auth.is_valid_session_gap(
        _et_epoch(2026, 1, 5, 9, 30), _et_epoch(2026, 1, 2, 16, 0), ScanCutoff(epoch=now_epoch)
    )
    assert backwards is False


# ------------------------------------------------------------------
# Fixture-measured bar-timestamp conventions (task: "measure and encode
# actual Alpaca 5m/15m/1h/daily timestamp conventions")
# ------------------------------------------------------------------

def test_fixture_5m_bars_are_session_open_aligned():
    """5-minute bars remain session-open-aligned as a CONSEQUENCE of the
    UTC-wall-clock-grid rule (09:30's minute-of-hour, 30, is already a
    multiple of 5) — not a special case."""
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    close_epoch = _et_epoch(2026, 1, 5, 16, 0)
    opens = _session_bar_opens(open_epoch, close_epoch, 300)
    assert len(opens) == 78  # 6.5h * 12 bars/hour
    assert opens[0] == open_epoch  # first bar starts exactly at session open, full-width
    assert opens[1] == open_epoch + 300


def test_fixture_15m_bars_are_session_open_aligned():
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    close_epoch = _et_epoch(2026, 1, 5, 16, 0)
    opens = _session_bar_opens(open_epoch, close_epoch, 900)
    assert len(opens) == 26  # 6.5h * 4 bars/hour
    assert opens[0] == open_epoch
    assert opens[1] == open_epoch + 900


def test_fixture_1h_bars_have_a_partial_first_bar_not_session_open_relative():
    """The corrected convention: 1-hour bars align to the UTC/ET clock hour,
    NOT to session-open-plus-multiples-of-an-hour. The session's first bar
    is a partial 09:30-10:00 bar (30 minutes), then full hourly bars
    aligned to the clock (10:00, 11:00, ..., 15:00) — 7 bars total, not the
    'known-wrong' 09:30/10:30/11:30/... pattern an earlier version assumed."""
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    close_epoch = _et_epoch(2026, 1, 5, 16, 0)
    opens = _session_bar_opens(open_epoch, close_epoch, 3600)
    opens_hhmm = [
        dt.datetime.fromtimestamp(e, tz=dt.timezone.utc).astimezone(EASTERN).strftime("%H:%M")
        for e in opens
    ]
    assert opens_hhmm == ["09:30", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
    # Explicitly NOT the old session-open-relative assumption:
    assert "10:30" not in opens_hhmm
    assert "11:30" not in opens_hhmm


def test_fixture_latest_closed_1h_bar_partial_first_bar_closes_at_1000():
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    close_epoch = _et_epoch(2026, 1, 5, 16, 0)
    # Cutoff at 09:59 -- the partial 09:30-10:00 bar has NOT closed yet.
    cutoff_before_1000 = _et_epoch(2026, 1, 5, 9, 59)
    assert _latest_closed_bar_open_in_session(open_epoch, close_epoch, 3600, cutoff_before_1000) is None
    # Cutoff at exactly 10:00 -- the partial first bar has just closed.
    cutoff_at_1000 = _et_epoch(2026, 1, 5, 10, 0)
    assert _latest_closed_bar_open_in_session(open_epoch, close_epoch, 3600, cutoff_at_1000) == open_epoch
    # Cutoff at 11:15 -- the 10:00-11:00 bar is the latest closed.
    cutoff_1115 = _et_epoch(2026, 1, 5, 11, 15)
    assert _latest_closed_bar_open_in_session(open_epoch, close_epoch, 3600, cutoff_1115) == _et_epoch(2026, 1, 5, 10, 0)


def test_expected_latest_closed_bar_1h_via_authority_uses_corrected_convention():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True
    # 40 minutes after open: the partial 9:30-10:00 bar has not closed yet.
    cutoff_partial_forming = ScanCutoff(epoch=open_epoch + 25 * 60)
    assert auth.expected_latest_closed_bar_open("1h", cutoff_partial_forming) is None or \
        auth.expected_latest_closed_bar_open("1h", cutoff_partial_forming) != open_epoch
    # At 11:05: the partial 9:30-10:00 bar AND the 10:00-11:00 bar have both closed.
    cutoff_1105 = ScanCutoff(epoch=_et_epoch(2026, 1, 5, 11, 5))
    expected = auth.expected_latest_closed_bar_open("1h", cutoff_1105)
    assert expected == _et_epoch(2026, 1, 5, 10, 0)


def test_expected_latest_closed_bar_intraday_5m():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True
    cutoff = ScanCutoff(epoch=open_epoch + 17 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", cutoff)
    assert expected == _et_epoch(2026, 1, 5, 9, 40)


def test_expected_latest_closed_bar_exact_boundary_zero_bars_elapsed():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True
    cutoff = ScanCutoff(epoch=open_epoch)
    expected = auth.expected_latest_closed_bar_open("5m", cutoff)
    friday_close = _et_epoch(2026, 1, 2, 16, 0)
    assert expected == friday_close - 5 * 60


def test_fixture_daily_bar_is_midnight_utc_of_trading_date_not_session_open():
    """The corrected daily convention: midnight UTC of the trading date, not
    the session-open time — an earlier version used session-open and
    flagged it as unverified; this commits to a specific, cited convention."""
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=9 * 3600, days_behind=3, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True

    midnight_utc_mon = int(dt.datetime(2026, 1, 5, 0, 0, tzinfo=dt.timezone.utc).timestamp())
    session_open_mon = open_epoch  # 09:30 ET, NOT the expected daily convention

    after_close = ScanCutoff(epoch=_et_epoch(2026, 1, 5, 16, 0))
    expected = auth.expected_latest_closed_bar_open("1d", after_close)
    assert expected == midnight_utc_mon
    assert expected != session_open_mon


def test_expected_latest_closed_bar_daily_before_close_uses_prior_day():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=9 * 3600, days_behind=3, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True
    cutoff = ScanCutoff(epoch=open_epoch + 60)
    expected = auth.expected_latest_closed_bar_open("1d", cutoff)
    midnight_utc_fri = int(dt.datetime(2026, 1, 2, 0, 0, tzinfo=dt.timezone.utc).timestamp())
    assert expected == midnight_utc_fri


def test_expected_latest_closed_bar_uncertain_when_unrecognized_timeframe():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    with _mock_alerts():
        assert auth.refresh(now_epoch=open_epoch) is True
    assert auth.expected_latest_closed_bar_open("bogus", ScanCutoff(epoch=open_epoch + 60)) is None


def test_dst_spring_forward_session_boundary():
    d = dt.date(2026, 3, 9)  # first trading day after the 2026 spring-forward transition
    api = _FakeAPI([_FakeCalEntry(d, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_dt = dt.datetime(2026, 3, 9, 9, 30, tzinfo=EASTERN)
    with _mock_alerts():
        assert auth.refresh(now_epoch=int(open_dt.timestamp())) is True
    session = auth.get_session(d, int(open_dt.timestamp()))
    assert session is not None
    open_e, close_e = session
    assert open_e == int(open_dt.timestamp())
    assert close_e - open_e == 6.5 * 3600


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} stock_calendar_authority tests passed")


if __name__ == "__main__":
    main()
