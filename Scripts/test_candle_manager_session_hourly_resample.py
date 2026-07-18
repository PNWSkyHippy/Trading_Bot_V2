"""
Session-anchored hourly stock-bar resampling tests — Step 6b (Patch B data
contract), reports/agent_pipeline/20260716-082429/final_unified_report.md
§13.

Bug: Alpaca's native 1Hour stock bars are plain UTC-hour-boundary buckets
across the full extended-hours window; the 09:30 ET regular-session open
falls inside one of those buckets, not on a boundary, so post-fetch
filtering of already-hourly data can never recover a genuine 09:30-10:00 ET
partial opening bar — the underlying trades are already aggregated away.

Fix (core/candle_manager.py::_fetch_alpaca_session_hourly +
core/stock_calendar_authority.py::resample_30m_to_session_hourly): fetch
native 30Min bars instead, filter each trading day to its regular session
via StockCalendarAuthority, and resample into session-anchored hourly
buckets ourselves — reusing the SAME _session_bar_opens boundary math
Scripts/test_stock_calendar_authority.py already proves correct, so fetch
output and validator expectations can never disagree.

These tests cover: correct bucket boundaries/OHLCV aggregation for a single
session, end-to-end resampling through CandleManager with a fake Alpaca
client, the calendar-authority-unavailable fallback (raw 30Min bars for
that date rather than dropped data), multi-day fetches resampling each day
independently, and proof that non-1h timeframes (and therefore all of
crypto, which never routes through Alpaca at all) are untouched by this
branch.

Runnable directly (`python Scripts/test_candle_manager_session_hourly_resample.py`).
"""

import datetime as dt
import sys
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.stock_calendar_authority import EASTERN, resample_30m_to_session_hourly


def _et_epoch(y, m, d, hh, mm):
    return int(dt.datetime(y, m, d, hh, mm, tzinfo=EASTERN).timestamp())


MON = dt.date(2026, 1, 5)   # real Monday
TUE = dt.date(2026, 1, 6)   # real Tuesday


def _mock_alerts():
    return mock.patch("reporting.alerts.alert_manager.gate_failure", return_value=True)


class _FakeCalEntry:
    def __init__(self, date_, open_t, close_t):
        self.date = pd.Timestamp(date_)
        self.open = open_t
        self.close = close_t


class _FakeCalendarApi:
    """Combined fake Alpaca client: .get_calendar() for StockCalendarAuthority
    and .get_bars() for CandleManager's fetch, so a single fake drives both
    sides of the resample path exactly like the real Alpaca REST client does."""

    def __init__(self, cal_entries, bars_df=None):
        self.cal_entries = cal_entries
        self._bars_df = bars_df if bars_df is not None else pd.DataFrame()

    @staticmethod
    def _entry_date(entry):
        return entry.date.date() if hasattr(entry.date, "date") else entry.date

    def get_calendar(self, start=None, end=None):
        start_d = dt.date.fromisoformat(start) if isinstance(start, str) else start
        end_d = dt.date.fromisoformat(end) if isinstance(end, str) else end
        if start_d is not None and start_d == end_d:
            return [e for e in self.cal_entries if self._entry_date(e) == start_d]
        return self.cal_entries

    def get_bars(self, symbol, timeframe, limit=None, adjustment="raw"):
        class _Resp:
            pass
        r = _Resp()
        r.df = self._bars_df
        return r


class _NoCalendarApi:
    """Simulates a calendar authority that can never confirm any session —
    e.g. Alpaca get_calendar() failing/empty — while still serving bars."""

    def __init__(self, bars_df):
        self._bars_df = bars_df

    def get_calendar(self, start=None, end=None):
        return []

    def get_bars(self, symbol, timeframe, limit=None, adjustment="raw"):
        class _Resp:
            pass
        r = _Resp()
        r.df = self._bars_df
        return r


def _session_30m_bars(d, price=100.0, n_extra_extended_hours=4):
    """30-minute bars for one trading day: `n_extra_extended_hours` hours of
    premarket (07:00-09:30 ET run-up) plus the full 09:30-16:00 ET regular
    session (13 half-hour bars) plus 1 after-hours bar — mirrors Alpaca's
    real extended-hours response shape, so filtering is actually exercised."""
    session_open = _et_epoch(d.year, d.month, d.day, 9, 30)
    rows = []
    # Premarket bars (must be excluded by the session filter).
    for i in range(n_extra_extended_hours * 2):
        ts = session_open - (n_extra_extended_hours * 2 - i) * 1800
        rows.append((ts, price - 5))
    # Regular session: 13 half-hour bars, 09:30 through 15:30-16:00.
    for i in range(13):
        ts = session_open + i * 1800
        rows.append((ts, price + i * 0.1))
    # One after-hours bar (must be excluded).
    rows.append((session_open + 13 * 1800 + 1800, price + 99))

    idx = pd.to_datetime([r[0] for r in rows], unit="s", utc=True).tz_localize(None)
    prices = [r[1] for r in rows]
    return pd.DataFrame({
        "open": prices, "high": [p + 0.05 for p in prices],
        "low": [p - 0.05 for p in prices], "close": prices,
        "volume": 1000.0,
    }, index=idx)


def _reset_authority_singleton():
    import core.stock_calendar_authority as sca
    sca._authority_instance = None


def _get_manager():
    from core.candle_manager import candle_manager
    return candle_manager


def test_resample_produces_correct_session_anchored_buckets():
    """Direct test of the resample function against a known 30m fixture:
    must produce exactly the 7 buckets ['09:30','10:00',...,'15:00'], with
    open=first/high=max/low=min/close=last/volume=sum aggregation."""
    open_epoch = _et_epoch(2026, 1, 5, 9, 30)
    close_epoch = _et_epoch(2026, 1, 5, 16, 0)

    # 13 half-hour bars spanning the full regular session, rising close price.
    opens = [open_epoch + i * 1800 for i in range(13)]
    idx = pd.to_datetime(opens, unit="s", utc=True).tz_localize(None)
    df_30m = pd.DataFrame({
        "open": [100.0 + i for i in range(13)],
        "high": [100.5 + i for i in range(13)],
        "low": [99.5 + i for i in range(13)],
        "close": [100.2 + i for i in range(13)],
        "volume": [10.0] * 13,
    }, index=idx)

    result = resample_30m_to_session_hourly(df_30m, open_epoch, close_epoch)

    hhmm = [
        dt.datetime.fromtimestamp(int(pd.Timestamp(ts).timestamp()), tz=dt.timezone.utc)
        .astimezone(EASTERN).strftime("%H:%M")
        for ts in result.index
    ]
    assert hhmm == ["09:30", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]

    # First bucket (09:30-10:00) is a partial bar covering exactly bar 0.
    assert result.iloc[0]["open"] == 100.0
    assert result.iloc[0]["close"] == 100.2
    assert result.iloc[0]["volume"] == 10.0

    # Second bucket (10:00-11:00) covers two half-hour bars (index 1, 2).
    assert result.iloc[1]["open"] == 101.0        # bar 1's open
    assert result.iloc[1]["close"] == 102.2        # bar 2's close
    assert result.iloc[1]["high"] == 102.5         # max(bar1.high, bar2.high)
    assert result.iloc[1]["low"] == 100.5          # min(bar1.low, bar2.low)
    assert result.iloc[1]["volume"] == 20.0        # sum of 2 bars

    # Last bucket (15:00-16:00) covers the two remaining half-hour bars
    # (15:00 and 15:30) up to the 16:00 session close.
    assert result.iloc[-1]["volume"] == 20.0


def test_fetch_alpaca_session_hourly_end_to_end_via_candle_manager():
    """Full path through CandleManager._fetch_alpaca_session_hourly with a
    fake Alpaca client: premarket/after-hours 30m bars must be excluded,
    and the regular session must resample into exactly 7 hourly buckets."""
    _reset_authority_singleton()
    bars = _session_30m_bars(MON)
    api = _FakeCalendarApi(
        cal_entries=[_FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0))],
        bars_df=bars,
    )
    mgr = _get_manager()
    with _mock_alerts():
        result = mgr._fetch_alpaca_session_hourly(api, "AAPL", limit=7)

    assert result is not None
    assert len(result) == 7
    hhmm = [
        dt.datetime.fromtimestamp(int(pd.Timestamp(ts).timestamp()), tz=dt.timezone.utc)
        .astimezone(EASTERN).strftime("%H:%M")
        for ts in result.index
    ]
    assert hhmm == ["09:30", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
    # No premarket (price-5) or after-hours (price+99) values leaked in.
    assert result["close"].max() < 110
    assert result["close"].min() > 95


def test_calendar_unavailable_falls_back_to_unfiltered_30m_bars():
    """If the calendar authority can never confirm a session (get_calendar()
    returns nothing), that date's raw 30Min bars — premarket/after-hours
    included — must still be returned rather than the date being dropped
    entirely from the result."""
    _reset_authority_singleton()
    bars = _session_30m_bars(MON)
    api = _NoCalendarApi(bars_df=bars)
    mgr = _get_manager()
    with _mock_alerts():
        result = mgr._fetch_alpaca_session_hourly(api, "AAPL", limit=100)

    assert result is not None
    # Falls back to the raw, unresampled 30Min rows for that date — same
    # row count as the input fixture (minus the trailing still-forming bar
    # that _fetch_alpaca_session_hourly always drops before use), not
    # resampled/filtered at all.
    assert len(result) == len(bars) - 1


def test_multi_day_fetch_resamples_each_day_independently():
    """Two trading days of 30m bars in a single raw fetch must each resample
    into their own 7-bucket session, never mixing bars across the day
    boundary (e.g. TUE's premarket bar must never land in MON's last bucket)."""
    _reset_authority_singleton()
    day1 = _session_30m_bars(MON, price=100.0)
    day2 = _session_30m_bars(TUE, price=200.0)
    combined = pd.concat([day1, day2]).sort_index()

    api = _FakeCalendarApi(
        cal_entries=[
            _FakeCalEntry(MON, dt.time(9, 30), dt.time(16, 0)),
            _FakeCalEntry(TUE, dt.time(9, 30), dt.time(16, 0)),
        ],
        bars_df=combined,
    )
    mgr = _get_manager()
    with _mock_alerts():
        result = mgr._fetch_alpaca_session_hourly(api, "AAPL", limit=100)

    assert result is not None
    assert len(result) == 14  # 7 buckets/day * 2 days
    # MON's bars are all ~100-101, TUE's are all ~200-201 — no cross-day mixing.
    day1_closes = result.iloc[:7]["close"]
    day2_closes = result.iloc[7:]["close"]
    assert day1_closes.max() < 150
    assert day2_closes.min() > 150


def test_non_hourly_timeframe_is_untouched_by_session_resampling():
    """5Min (and by extension every non-'1h' stock timeframe, and all of
    crypto which never routes through Alpaca at all) must go through the
    original single get_bars() call, never through the resample branch."""
    from core.candle_manager import CandleManager

    calls = {"get_bars": 0, "get_calendar": 0}

    class _TrackingApi:
        def get_bars(self, symbol, timeframe, limit=None, adjustment="raw"):
            calls["get_bars"] += 1
            assert timeframe == "5Min", "must request the plain native timeframe, unresampled"

            class _Resp:
                pass
            r = _Resp()
            idx = pd.date_range("2024-01-01", periods=5, freq="5min", tz="UTC").tz_localize(None)
            r.df = pd.DataFrame({
                "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 10.0,
            }, index=idx)
            return r

        def get_calendar(self, start=None, end=None):
            calls["get_calendar"] += 1
            return []

    with mock.patch("alpaca_trade_api.REST", return_value=_TrackingApi()):
        with mock.patch("config.ALPACA_API_KEY", "x"), \
             mock.patch("config.ALPACA_SECRET_KEY", "x"), \
             mock.patch("config.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"):
            mgr = CandleManager.__new__(CandleManager)  # skip __init__ (DB/registry side effects)
            result = mgr._fetch_alpaca("AAPL", "5Min", limit=5)

    assert result is not None
    assert calls["get_bars"] == 1
    assert calls["get_calendar"] == 0, "non-1h timeframes must never touch the calendar authority"


def main():
    tests = [
        test_resample_produces_correct_session_anchored_buckets,
        test_fetch_alpaca_session_hourly_end_to_end_via_candle_manager,
        test_calendar_unavailable_falls_back_to_unfiltered_30m_bars,
        test_multi_day_fetch_resamples_each_day_independently,
        test_non_hourly_timeframe_is_untouched_by_session_resampling,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} session-hourly resample tests passed")


if __name__ == "__main__":
    main()
