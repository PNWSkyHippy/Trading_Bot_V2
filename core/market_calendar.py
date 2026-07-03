"""Small US equity market calendar helper used by live stock gates."""

from __future__ import annotations

from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")


def _observed(fixed_day: date) -> date:
    """Return the observed weekday for a fixed-date US market holiday."""
    if fixed_day.weekday() == 5:  # Saturday observed Friday
        return fixed_day - timedelta(days=1)
    if fixed_day.weekday() == 6:  # Sunday observed Monday
        return fixed_day + timedelta(days=1)
    return fixed_day


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _easter_date(year: int) -> date:
    """Gregorian Easter date, valid for modern NYSE Good Friday checks."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def us_equity_market_holidays(year: int) -> set[date]:
    """Return regular full-day NYSE/Nasdaq holidays for a year."""
    return {
        _observed(date(year, 1, 1)),                  # New Year's Day
        _nth_weekday(year, 1, 0, 3),                  # MLK Day
        _nth_weekday(year, 2, 0, 3),                  # Presidents' Day
        _easter_date(year) - timedelta(days=2),       # Good Friday
        _last_weekday(year, 5, 0),                    # Memorial Day
        _observed(date(year, 6, 19)),                 # Juneteenth
        _observed(date(year, 7, 4)),                  # Independence Day
        _nth_weekday(year, 9, 0, 1),                  # Labor Day
        _nth_weekday(year, 11, 3, 4),                 # Thanksgiving
        _observed(date(year, 12, 25)),                # Christmas
    }


def is_us_equity_market_holiday(day: date) -> bool:
    return day in us_equity_market_holidays(day.year)


def is_us_equity_regular_session_now(
    *,
    open_hour: int = 9,
    open_minute: int = 30,
    close_hour: int = 16,
    close_minute: int = 0,
    now: datetime | None = None,
) -> bool:
    """Return True during regular US equity session, excluding full holidays."""
    now_et = now.astimezone(EASTERN) if now else datetime.now(EASTERN)
    if now_et.weekday() > 4:
        return False
    if is_us_equity_market_holiday(now_et.date()):
        return False

    after_open = (now_et.hour, now_et.minute) >= (open_hour, open_minute)
    before_close = (now_et.hour, now_et.minute) < (close_hour, close_minute)
    return after_open and before_close
