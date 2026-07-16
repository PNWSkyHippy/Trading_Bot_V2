"""
Deterministic tests for core/stock_calendar_authority.py (Patch A, B5).

Covers: successful refresh, malformed-batch rejection (whole batch, not
partial adoption), empty-response rejection, no-API-client rejection,
same-day freshness window (a date-covering-but-stale cache is NOT
authoritative), atomic schedule replacement on an emergency/changed
schedule, expected-latest-closed-bar computation for intraday and daily
timeframes, and is_regular_session_now's fail-closed (None) behavior when
uncertain.

IMPORTANT: every test that can reach metrics.alert_gate_failure() mocks
reporting.alerts.alert_manager first so it never attempts a real email/SMS
send — do not remove that mock. (An earlier ad-hoc smoke test during
development skipped this and triggered a real, if failed, SMTP attempt
against this system's actual configured alert credentials.)

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
    """Context manager patching alert_manager.trading_halted so no test can
    ever reach real SMTP/SMS infrastructure."""
    return mock.patch("reporting.alerts.alert_manager.trading_halted")


def test_successful_refresh():
    metrics.reset()
    today = dt.date(2026, 7, 16)
    api = _FakeAPI([_FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=open_epoch) is True
        m.assert_not_called()
    assert metrics.get_snapshot().get("calendar.refresh.success") == 1
    session = auth.get_session(today, open_epoch)
    assert session is not None
    open_e, close_e = session
    assert open_e == open_epoch
    assert close_e == int(dt.datetime(2026, 7, 16, 16, 0, tzinfo=EASTERN).timestamp())


def test_no_api_client_fails_closed():
    metrics.reset()
    auth = StockCalendarAuthority(api=None)
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=1_800_000_000) is False
        m.assert_not_called()  # no-api is a config problem, not alerted (can't call get_calendar at all)
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1


def test_api_exception_fails_closed_and_alerts():
    metrics.reset()
    auth = StockCalendarAuthority(api=_RaisingAPI())
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=1_800_000_000) is False
        m.assert_called_once()
    assert metrics.get_snapshot().get("calendar.refresh.failure") == 1
    assert metrics.get_snapshot().get("gate_failure.stock_calendar_authority") == 1


def test_malformed_batch_is_rejected_entirely_not_partially_adopted():
    metrics.reset()
    today = dt.date(2026, 7, 16)
    tomorrow = dt.date(2026, 7, 17)
    # One good entry, one malformed (close before open) — the whole batch
    # must be rejected, not just the bad row silently dropped.
    api = _FakeAPI([
        _FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(16, 0), dt.time(9, 30)),
    ])
    auth = StockCalendarAuthority(api=api)
    now_epoch = int(dt.datetime(2026, 7, 16, 9, 0, tzinfo=EASTERN).timestamp())
    with _mock_alerts() as m:
        assert auth.refresh(now_epoch=now_epoch) is False
        m.assert_called_once()
    # Neither date should have been adopted, including the well-formed one.
    assert auth.get_session(today, now_epoch) is None
    assert auth.get_session(tomorrow, now_epoch) is None


def test_empty_response_rejected():
    metrics.reset()
    auth = StockCalendarAuthority(api=_FakeAPI([]))
    with _mock_alerts():
        assert auth.refresh(now_epoch=1_800_000_000) is False


def test_stale_date_covering_cache_is_not_authoritative():
    """The crux of B5's decided rule: merely covering a date is not enough."""
    today = dt.date(2026, 7, 16)
    api = _FakeAPI([_FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=open_epoch)

    # Still within the freshness window: authoritative.
    assert auth.get_session(today, open_epoch + 3599) is not None
    # Past the freshness window, even though the date is still "covered":
    # NOT authoritative, per the decided rule.
    assert auth.get_session(today, open_epoch + 3601) is None
    assert auth.is_regular_session_now(ScanCutoff(epoch=open_epoch + 3601)) is None


def test_emergency_schedule_change_replaces_atomically():
    today = dt.date(2026, 7, 15)
    tomorrow = dt.date(2026, 7, 16)
    api = _FakeAPI([
        _FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600, days_behind=3)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=open_epoch)

    # Emergency early close announced for tomorrow's date.
    api.entries = [
        _FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(9, 30), dt.time(13, 0)),
    ]
    auth.refresh(now_epoch=open_epoch + 60)

    session = auth.get_session(tomorrow, open_epoch + 120)
    assert session is not None
    _, close_e = session
    assert close_e == int(dt.datetime(2026, 7, 16, 13, 0, tzinfo=EASTERN).timestamp())


def test_expected_latest_closed_bar_intraday():
    today = dt.date(2026, 7, 16)
    api = _FakeAPI([_FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=open_epoch)

    # 17 minutes after open: three 5-min bars closed (9:30-35, 9:35-40, 9:40-45)
    cutoff = ScanCutoff(epoch=open_epoch + 17 * 60)
    expected = auth.expected_latest_closed_bar_open("5m", cutoff)
    assert expected == int(dt.datetime(2026, 7, 16, 9, 40, tzinfo=EASTERN).timestamp())


def test_expected_latest_closed_bar_before_session_open_uses_prior_day():
    today = dt.date(2026, 7, 15)
    tomorrow = dt.date(2026, 7, 16)
    api = _FakeAPI([
        _FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3)
    ref_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=ref_epoch)

    pre_market_cutoff = ScanCutoff(epoch=ref_epoch - 30 * 60)  # 9:00 ET, before open
    expected = auth.expected_latest_closed_bar_open("5m", pre_market_cutoff)
    prior_close = int(dt.datetime(2026, 7, 15, 16, 0, tzinfo=EASTERN).timestamp())
    # Last bar of the prior day's session opens 5 minutes before its close.
    assert expected == prior_close - 5 * 60


def test_expected_latest_closed_bar_daily():
    today = dt.date(2026, 7, 15)
    tomorrow = dt.date(2026, 7, 16)
    api = _FakeAPI([
        _FakeCalEntry(today, dt.time(9, 30), dt.time(16, 0)),
        _FakeCalEntry(tomorrow, dt.time(9, 30), dt.time(16, 0)),
    ])
    auth = StockCalendarAuthority(api=api, freshness_sec=7200, days_behind=3)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=open_epoch)

    # Before tomorrow's session closes, the latest *completed* daily bar is today.
    cutoff = ScanCutoff(epoch=open_epoch + 60)
    expected = auth.expected_latest_closed_bar_open("1d", cutoff)
    assert expected == int(dt.datetime(2026, 7, 15, 9, 30, tzinfo=EASTERN).timestamp())


def test_expected_latest_closed_bar_uncertain_when_unrecognized_timeframe():
    api = _FakeAPI([_FakeCalEntry(dt.date(2026, 7, 16), dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api)
    open_epoch = int(dt.datetime(2026, 7, 16, 9, 30, tzinfo=EASTERN).timestamp())
    auth.refresh(now_epoch=open_epoch)
    assert auth.expected_latest_closed_bar_open("bogus", ScanCutoff(epoch=open_epoch + 60)) is None


def test_dst_spring_forward_session_boundary():
    """2026-03-08 is the US spring-forward DST transition. Session open/close
    must still resolve correctly via zoneinfo (America/New_York), not a fixed
    UTC offset."""
    d = dt.date(2026, 3, 9)  # first trading day after the transition
    api = _FakeAPI([_FakeCalEntry(d, dt.time(9, 30), dt.time(16, 0))])
    auth = StockCalendarAuthority(api=api, freshness_sec=3600)
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
