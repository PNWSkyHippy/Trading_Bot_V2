"""
Deterministic tests for core/stock_calendar_authority.py (Patch A, B5).

Covers: successful refresh, malformed-batch rejection (whole batch, not
partial adoption, including a duplicate-date malformed response), empty-
response rejection, no-API-client rejection, same-day (same-ET-date, not
merely elapsed-seconds) freshness window, future-refresh-timestamp
rejection, clock-rollback rejection, atomic schedule replacement on an
emergency/changed schedule, atomic revoke of the response's observed span,
partial/truncated-response handling (does not fabricate confirmed-holiday
facts beyond what was actually observed), weekend traversal, holiday
traversal, expected-latest-closed-bar computation for intraday and daily
timeframes, and is_regular_session_now's fail-closed (None) behavior when
uncertain.

All fixture dates are fixed, real historical (2026-01-05 is a real Monday,
2026-01-02 the preceding Friday, 2026-01-01 a real US holiday) dates safely
in the past relative to this suite's expected run window — never a
hardcoded *future* placeholder epoch, since the authority now rejects
refresh() calls whose now_epoch is implausibly ahead of the actual wall
clock (an earlier draft of this suite used a bare `1_800_000_000` epoch for
convenience, which silently drifted into "the future" as calendar time
passed and began tripping the new clock-skew guard instead of exercising
the intended code path).

IMPORTANT: every test that can reach metrics.alert_gate_failure() mocks
reporting.alerts.alert_manager first so it never attempts a real email/SMS
send — do not remove that mock.

Runnable directly (`python Scripts/test_stock_calendar_authority.py`) or via
pytest.
"""

import datetime as dt
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import metrics
from core.candle_validation import ScanCutoff
from core.stock_calendar_authority import StockCalendarAuthority, EASTERN


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
    """Context manager patching alert_manager.gate_failure (the dedicated
    gate-failure alert, distinct from trading_halted()) so no test can ever
    reach real SMTP/SMS infrastructure."""
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


def test_no_api_client_fails_closed():
    metrics.reset()
    auth = StockCalendarAuthority(api=None)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is False
        m.assert_not_called()  # no-api is a config problem, not alerted (can't call get_calendar at all)
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1


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
    tomorrow = dt.date(2026, 1, 6)
    api = _FakeAPI([
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(16, 0), dt.time(9, 30)),  # malformed
    ])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=1)
    now_epoch = _et_epoch(2026, 1, 5, 9, 0)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    # Neither date should have been adopted, including the well-formed one.
    assert auth.get_session(MON, now_epoch) is None
    assert auth.get_session(tomorrow, now_epoch) is None


def test_malformed_batch_duplicate_date_is_rejected_entirely():
    """Adversarial: two calendar entries for the identical date in one
    response is itself a malformed/internally-inconsistent batch, distinct
    from a simple close<=open error."""
    metrics.reset()
    api = _FakeAPI([
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(13, 0)),  # duplicate date, different close
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


def test_stale_date_covering_cache_is_not_authoritative():
    """The crux of B5's decided rule: merely covering a date is not enough."""
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)

    # Still within the freshness window: authoritative.
    assert auth.get_session(MON, open_epoch + 3599) is not None
    # Past the freshness window, even though the date is still "covered":
    # NOT authoritative, per the decided rule.
    assert auth.get_session(MON, open_epoch + 3601) is None
    assert auth.is_regular_session_now(ScanCutoff(epoch=open_epoch + 3601)) is None


def test_same_et_date_required_not_just_elapsed_seconds():
    """A refresh late on one ET day must not be treated as fresh deep into
    the next ET day merely because a large freshness_sec window hasn't
    elapsed — the fetch must have happened on the SAME ET calendar date
    being evaluated."""
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    # A generous 24h freshness window would, on elapsed-seconds alone,
    # consider a 23:58 refresh still "fresh" at 09:00 the next day.
    auth = StockCalendarAuthority(api=api, freshness_sec=24 * 3600, days_behind=0, days_ahead=0)
    late_on_mon = _et_epoch(2026, 1, 5, 23, 58)
    auth.refresh(now_epoch=late_on_mon)
    # Same ET date, still within elapsed window: fresh.
    assert auth.get_session(MON, late_on_mon + 60) is not None
    # Next ET calendar date (Tuesday morning), well within the 24h elapsed
    # window, but NOT the same ET date as the refresh: must be treated as
    # unknown, not fresh.
    next_day_morning = _et_epoch(2026, 1, 6, 9, 0)
    assert (next_day_morning - late_on_mon) < 24 * 3600  # confirm elapsed check alone would pass
    assert auth.get_session(MON, next_day_morning) is None


def test_future_refresh_timestamp_rejected():
    metrics.reset()
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, clock_skew_tolerance_sec=5)
    import time as _time
    far_future = int(_time.time()) + 3600  # an hour ahead of actual wall clock
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=far_future) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1
    # Confirm the rejection happened BEFORE ever calling the API (no session cached).
    assert auth.get_session(MON, far_future) is None


def test_refresh_within_clock_skew_tolerance_is_accepted():
    import time as _time
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, clock_skew_tolerance_sec=5, days_behind=0, days_ahead=0)
    # This test's now_epoch is derived from MON's real date, which is safely
    # in the past — well within tolerance regardless of skew direction.
    assert auth.refresh(now_epoch=_et_epoch(2026, 1, 5, 9, 0)) is True


def test_clock_rollback_between_refreshes_rejected():
    metrics.reset()
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, days_behind=0, days_ahead=0)
    later = _et_epoch(2026, 1, 5, 12, 0)
    earlier = _et_epoch(2026, 1, 5, 9, 0)
    assert auth.refresh(now_epoch=later) is True
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=earlier) is False  # clock appears to have rolled back
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1


def test_emergency_schedule_change_replaces_atomically():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=3, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)

    # Emergency early close announced for Monday.
    api.entries = [
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(13, 0)),
    ]
    auth.refresh(now_epoch=open_epoch + 60)

    session = auth.get_session(MON, open_epoch + 120)
    assert session is not None
    _, close_e = session
    assert close_e == _et_epoch(2026, 1, 5, 13, 0)


def test_atomic_revoke_removes_date_no_longer_confirmed_by_new_response():
    """A date previously cached as a session must be revoked if a later
    refresh's observed span covers it but no longer includes it (not left
    stale under an old fetched_at)."""
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=3, days_ahead=0)
    now1 = _et_epoch(2026, 1, 5, 9, 0)
    auth.refresh(now_epoch=now1)
    assert auth.get_session(MON, now1) is not None

    # A later refresh's response no longer includes Monday at all (e.g. Alpaca
    # corrected a data error) but its observed span still covers that date.
    api.entries = [_FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0))]
    now2 = _et_epoch(2026, 1, 5, 9, 30)
    # Observed span is now just FRI_PREV..FRI_PREV (a single date) -- to
    # exercise revocation we need the observed span to still include MON,
    # so give a second, later-dated entry to keep the span wide enough while
    # still omitting MON from the *set* of confirmed sessions.
    api.entries = [
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(dt.date(2026, 1, 6), dt.time(9, 30), dt.time(16, 0)),
    ]
    auth.refresh(now_epoch=now2)
    assert auth.get_session(MON, now2) is None  # revoked, not stale-but-present
    assert auth.is_confirmed_non_trading_day(MON, now2) is True  # and now confirmed closed


def test_partial_response_does_not_fabricate_holidays_beyond_observed_span():
    """A genuinely partial/truncated response (observed span narrower than
    requested) must not cause dates outside its own observed span to be
    marked as confirmed non-trading days."""
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    # Request a wide window (days_behind/ahead), but the fake API only ever
    # returns a single date -- simulating a truncated/partial response.
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=5, days_ahead=5)
    now_epoch = _et_epoch(2026, 1, 5, 9, 0)
    assert auth.refresh(now_epoch=now_epoch) is True
    # The single observed date is a confirmed session.
    assert auth.get_session(MON, now_epoch) is not None
    # A date well outside the single-date observed span (e.g. 3 days later,
    # still within the originally-*requested* window) must be UNKNOWN, not
    # confirmed closed -- the response never actually addressed it.
    far_date = dt.date(2026, 1, 8)
    assert auth.get_session(far_date, now_epoch) is None
    assert auth.is_confirmed_non_trading_day(far_date, now_epoch) is None


def test_weekend_traversal_finds_prior_friday_session():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=5, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 5, 9, 30)  # Monday open
    auth.refresh(now_epoch=ref_epoch)
    # SAT and SUN are within the observed span (FRI_PREV..MON) and were not
    # returned as sessions, so they are correctly confirmed non-trading.
    assert auth.is_confirmed_non_trading_day(SAT, ref_epoch) is True
    assert auth.is_confirmed_non_trading_day(SUN, ref_epoch) is True

    pre_market_monday = ScanCutoff(epoch=ref_epoch - 30 * 60)  # before Monday's open
    expected = auth.expected_latest_closed_bar_open("5m", pre_market_monday)
    friday_close = _et_epoch(2026, 1, 2, 16, 0)
    assert expected == friday_close - 5 * 60  # last 5-min bar of Friday's session


def test_holiday_traversal_finds_prior_session_before_confirmed_holiday():
    api = _FakeAPI([
        _FakeCalEntry(DAY_BEFORE_HOLIDAY, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(dt.date(2026, 1, 2), dt.time(9, 30), dt.time(16, 0)),  # first trading day of 2026
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=5, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 2, 9, 30)
    auth.refresh(now_epoch=ref_epoch)
    # NEW_YEARS_DAY (2026-01-01) falls inside the observed span and was
    # correctly recorded as a confirmed non-trading (holiday) date.
    assert auth.is_confirmed_non_trading_day(NEW_YEARS_DAY, ref_epoch) is True

    pre_market_jan2 = ScanCutoff(epoch=ref_epoch - 30 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", pre_market_jan2)
    prior_close = _et_epoch(2025, 12, 31, 16, 0)
    assert expected == prior_close - 5 * 60


def test_lookback_returns_none_when_unknown_date_encountered():
    """If the walk-back hits a date that is neither a fresh session nor
    confirmed closed (outside anything ever refreshed), it must fail closed
    rather than assume the date is closed and keep guessing further back."""
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    # days_behind=0 means the refresh window never covers FRI_PREV/SAT/SUN at
    # all -- they are simply unknown, not confirmed closed.
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=0, days_ahead=0)
    ref_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=ref_epoch)
    pre_market_monday = ScanCutoff(epoch=ref_epoch - 30 * 60)
    assert auth.expected_latest_closed_bar_open("5m", pre_market_monday) is None


def test_expected_latest_closed_bar_intraday():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)

    cutoff = ScanCutoff(epoch=open_epoch + 17 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", cutoff)
    assert expected == _et_epoch(2026, 1, 5, 9, 40)


def test_expected_latest_closed_bar_exact_boundary_zero_bars_elapsed():
    """Cutoff exactly at session open: zero bars have closed yet this
    session, so the expected bar is the prior session's last bar, not a
    same-session bar with a negative/zero index."""
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=5, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)
    cutoff = ScanCutoff(epoch=open_epoch)  # exactly at Monday's open
    expected = auth.expected_latest_closed_bar_open("5m", cutoff)
    friday_close = _et_epoch(2026, 1, 2, 16, 0)
    assert expected == friday_close - 5 * 60


def test_expected_latest_closed_bar_daily():
    api = _FakeAPI([
        _FakeCalEntry(FRI_PREV, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=9 * 3600, days_behind=5, days_ahead=0)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)

    # Before Monday's session closes, the latest *completed* daily bar is Friday's.
    cutoff = ScanCutoff(epoch=open_epoch + 60)
    expected = auth.expected_latest_closed_bar_open("1d", cutoff)
    assert expected == _et_epoch(2026, 1, 2, 9, 30)

    # After Monday's session closes, Monday itself is the latest completed daily bar.
    # (freshness_sec is generous enough here to still cover the ~6.5h gap
    # from the 9:30 refresh to the 16:00 close within the SAME ET date.)
    after_close = ScanCutoff(epoch=_et_epoch(2026, 1, 5, 16, 0))
    expected2 = auth.expected_latest_closed_bar_open("1d", after_close)
    assert expected2 == _et_epoch(2026, 1, 5, 9, 30)


def test_expected_latest_closed_bar_uncertain_when_unrecognized_timeframe():
    api = _FakeAPI([_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api)
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    auth.refresh(now_epoch=open_epoch)
    assert auth.expected_latest_closed_bar_open("bogus", ScanCutoff(epoch=open_epoch + 60)) is None


def test_dst_spring_forward_session_boundary():
    """2026-03-08 is the US spring-forward DST transition. Session open/close
    must still resolve correctly via zoneinfo (America/New_York), not a fixed
    UTC offset."""
    d = dt.date(2026, 3, 9)  # first trading day after the transition
    api = _FakeAPI([_FakeCalEntry(d, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=0, days_ahead=0)
    open_dt = dt.datetime(2026, 3, 9, 9, 30, tzinfo=EASTERN)
    auth.refresh(now_epoch=int(open_dt.timestamp()))
    session = auth.get_session(d, int(open_dt.timestamp()))
    assert session is not None
    open_e, close_e = session
    assert open_e == int(open_dt.timestamp())
    assert close_e - open_e == 6.5 * 3600  # still a normal 6.5h session


ALL_TESTS = [v for k, v in list(globals().items()) if k.startswith("test_")]


def main():
    for t in ALL_TESTS:
        t()
        print(f"PASS: {t.__name__}")
    print(f"{len(ALL_TESTS)}/{len(ALL_TESTS)} stock_calendar_authority tests passed")


if __name__ == "__main__":
    main()
