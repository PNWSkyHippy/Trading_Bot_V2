"""
=============================================================
  STOCK CALENDAR AUTHORITY — Patch A (B5)
  reports/agent_pipeline/20260716-082429/final_unified_report.md

  Wraps Alpaca's own market-calendar API (REST.get_calendar()) as the
  authoritative source of stock session open/close times, replacing the
  hand-maintained core/market_calendar.py approximation for live-freshness
  decisions. core/market_calendar.py implements only ten fixed full-day
  holidays and a hardcoded 09:30-16:00 window — it has no half-day/
  early-close, emergency-closure, or publication-delay modeling, and cannot
  support the strict "session-aware expected closed bar" contract this system
  requires. Alpaca is already this system's broker of record for stock data,
  so this introduces no new external dependency.

  Decided contract (B5, not an either/or option menu):
    - The daily schedule may be prefetched/cached for a rolling forward
      window, but merely covering a date is not sufficient to treat it as
      authoritative for that date.
    - Before permitting any new entry or due-scheduling decision on a given
      trading date, there must have been a successful refresh *for that date*
      within config.STOCK_CALENDAR_FRESHNESS_SEC, AND that refresh must have
      occurred on the same Eastern-Time calendar date being evaluated (an
      elapsed-seconds check alone is not enough: a refresh at 23:58 ET one
      day should not be treated as "fresh" deep into the next ET day merely
      because the elapsed-seconds window hasn't lapsed).
    - A `refresh()` call is itself validated: a caller-supplied `now_epoch`
      that is unreasonably in the future (more than a small clock-skew
      tolerance ahead of the actual wall clock) is rejected outright, rather
      than trusted to write cache entries.
    - A missing, stale (past the freshness window or wrong ET date), or
      malformed schedule globally blocks entries/due-scheduling for that
      date — this class never silently falls back to
      core/market_calendar.py's hardcoded 09:30-16:00 assumption for a
      live-freshness decision.
    - A refresh atomically replaces AND revokes across the response's own
      OBSERVED date span (min..max of the dates it actually returned), not
      blindly across the full originally-requested [start, end] window: any
      date within that observed span previously cached (as a session or as a
      confirmed non-trading day) that is NOT reconfirmed by the new response
      is removed, not left stale. Non-trading dates (weekends/holidays)
      within the observed span are recorded as explicit, authoritative
      "confirmed closed" facts — not merely absent — so that looking for the
      most recent prior completed session can correctly traverse weekends
      and holidays instead of stopping at the first uncached calendar day.
      A genuinely partial/truncated response (observed span narrower than
      requested — a provider bug, incomplete pagination) is NOT trusted
      beyond what it actually returned: dates in the requested window but
      outside the observed span are left untouched rather than being
      mischaracterized as confirmed holidays.
    - `refresh()` also rejects a `now_epoch` earlier than the last accepted
      refresh's `now_epoch` (a possible system clock rollback), since
      accepting it could write fetched_at bookkeeping earlier than data
      already on file, corrupting freshness comparisons going forward.

  This module is not yet wired into any live fetch/scan routing — Patch A is
  contracts and tests only. It implements the candle_validation.SessionAuthority
  protocol so Patch B/C can consume it directly once ready.
=============================================================
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo

import config
from core import metrics
from core.candle_validation import ScanCutoff, timeframe_seconds

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

# Explicit, separately-documented assumptions about Alpaca's own bar-
# timestamp convention per granularity (B5's "encode conventions separately"
# requirement). Kept as distinct labeled constants — not one shared implicit
# formula — so a future patch can correct a single entry if live Alpaca
# response data reveals a difference, without touching shared logic.
#
#   Intraday (5m/15m/1h/etc): each bar's index timestamp is its OWN open
#   time. This matches Alpaca's documented v2 bars behavior and is also what
#   scanners/market_scanner.py's own _strip_forming_bar() assumes. Not
#   independently re-verified against a live response in this patch (no
#   network access during this audit) — flagged for confirmation before
#   Patch B/C relies on this authority for live routing.
_INTRADAY_BAR_TIMESTAMP_CONVENTION = "bar_open"

#   Daily (1d): this authority assumes a daily bar's index timestamp is that
#   trading date's regular-session OPEN time (09:30 ET), i.e. the same
#   session-open value used for intraday bars, NOT UTC midnight and NOT the
#   session close. THIS SPECIFIC ASSUMPTION IS UNVERIFIED against a live
#   Alpaca daily-bar response and must be confirmed before Patch B/C wires
#   daily-bar validation through this authority for live entries — Alpaca's
#   actual convention for daily bars may differ from its intraday convention.
_DAILY_BAR_TIMESTAMP_CONVENTION = "session_open_unverified"


@dataclass(frozen=True)
class _SessionWindow:
    open_epoch: int
    close_epoch: int


class StockCalendarAuthority:
    """
    Primary stock-session authority per B5's decided rule. See module
    docstring. Thread-safe; safe to share a single instance across the
    scanner, refresh loop, and position monitor once wired in.
    """

    def __init__(
        self,
        api=None,
        freshness_sec: Optional[int] = None,
        days_ahead: Optional[int] = None,
        days_behind: Optional[int] = None,
        clock_skew_tolerance_sec: Optional[int] = None,
    ):
        # `api` is injected (not constructed here) so tests can supply a fake
        # with a controllable get_calendar() — this class has no import-time
        # dependency on a live Alpaca connection.
        self._api = api
        self._freshness_sec = (
            freshness_sec if freshness_sec is not None
            else config.STOCK_CALENDAR_FRESHNESS_SEC
        )
        self._days_ahead = (
            days_ahead if days_ahead is not None
            else config.STOCK_CALENDAR_CACHE_DAYS_AHEAD
        )
        self._days_behind = (
            days_behind if days_behind is not None
            else config.STOCK_CALENDAR_CACHE_DAYS_BEHIND
        )
        self._clock_skew_tolerance_sec = (
            clock_skew_tolerance_sec if clock_skew_tolerance_sec is not None
            else getattr(config, "STOCK_CALENDAR_CLOCK_SKEW_TOLERANCE_SEC", 5)
        )
        self._lock = threading.Lock()
        # Trading-day sessions.
        self._schedule: Dict[date, _SessionWindow] = {}
        self._fetched_at: Dict[date, int] = {}
        self._fetched_at_et_date: Dict[date, date] = {}
        # Confirmed NON-trading dates (weekends/holidays) within a refreshed
        # window — an authoritative fact, not merely "we have no data".
        self._closed_dates: Dict[date, int] = {}
        self._closed_dates_et_date: Dict[date, date] = {}
        # Clock-rollback guard: a refresh's now_epoch must never be earlier
        # than the last successfully accepted refresh's now_epoch. A system
        # clock that has jumped backward is itself a reason to distrust
        # further automated freshness decisions, not something to silently
        # tolerate by writing new fetched_at values earlier than existing ones.
        self._last_accepted_refresh_epoch: Optional[int] = None

    @staticmethod
    def _et_date(epoch: int) -> date:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(EASTERN).date()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, now_epoch: Optional[int] = None) -> bool:
        """
        Fetch a fresh rolling window from Alpaca's get_calendar() and
        atomically replace AND revoke the cached entries for every date in
        that window (never merge partial results into stale ones, and never
        leave a previously-cached date that the new response no longer
        confirms). Returns True only on a fully successful, fully parsed
        refresh.
        """
        if self._api is None:
            metrics.increment("calendar.refresh.failure")
            logger.warning("[StockCalendarAuthority] no API client configured — refresh skipped")
            return False

        actual_now = int(time.time())
        now_epoch = now_epoch if now_epoch is not None else actual_now
        if now_epoch > actual_now + self._clock_skew_tolerance_sec:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure(
                "stock_calendar_authority",
                f"refresh() called with now_epoch={now_epoch} which is "
                f"{now_epoch - actual_now}s ahead of actual wall clock "
                f"{actual_now} (tolerance {self._clock_skew_tolerance_sec}s)",
                actual_now,
            )
            logger.error(
                f"[StockCalendarAuthority] rejecting refresh: now_epoch={now_epoch} "
                f"is implausibly in the future (actual={actual_now})"
            )
            return False

        with self._lock:
            last_accepted = self._last_accepted_refresh_epoch
        if last_accepted is not None and now_epoch < last_accepted:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure(
                "stock_calendar_authority",
                f"refresh() called with now_epoch={now_epoch} which is before "
                f"the last accepted refresh's now_epoch={last_accepted} — "
                f"possible system clock rollback",
                actual_now,
            )
            logger.error(
                f"[StockCalendarAuthority] rejecting refresh: now_epoch={now_epoch} "
                f"is earlier than last accepted refresh at {last_accepted} "
                f"(possible clock rollback)"
            )
            return False

        today = self._et_date(now_epoch)
        start = today - timedelta(days=self._days_behind)
        end = today + timedelta(days=self._days_ahead)

        try:
            raw = self._api.get_calendar(
                start=start.isoformat(), end=end.isoformat()
            )
        except Exception as e:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", f"get_calendar() raised: {e}", now_epoch)
            logger.warning(f"[StockCalendarAuthority] get_calendar() failed: {e}")
            return False

        if raw is None:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", "get_calendar() returned None", now_epoch)
            logger.warning("[StockCalendarAuthority] get_calendar() returned None")
            return False

        new_schedule: Dict[date, _SessionWindow] = {}
        try:
            for entry in raw:
                d = entry.date.date() if hasattr(entry.date, "date") else entry.date
                if d in new_schedule:
                    raise ValueError(f"duplicate date in calendar response: {d}")
                open_t = entry.open
                close_t = entry.close
                open_dt = datetime.combine(d, open_t, tzinfo=EASTERN)
                close_dt = datetime.combine(d, close_t, tzinfo=EASTERN)
                if close_dt <= open_dt:
                    raise ValueError(f"malformed session for {d}: close <= open")
                new_schedule[d] = _SessionWindow(
                    open_epoch=int(open_dt.timestamp()),
                    close_epoch=int(close_dt.timestamp()),
                )
        except Exception as e:
            # Malformed response (including a duplicate date — an internally
            # inconsistent batch): do not partially adopt it. A bad batch
            # must never silently replace good cached data with garbage for
            # some dates while leaving others untouched.
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", f"malformed calendar response: {e}", now_epoch)
            logger.error(f"[StockCalendarAuthority] malformed calendar response, rejecting entire batch: {e}")
            return False

        if not new_schedule:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", "refresh returned zero sessions", now_epoch)
            logger.warning("[StockCalendarAuthority] refresh returned zero sessions — rejecting")
            return False

        # Every ET calendar date within the response's own OBSERVED span
        # (min..max of the dates it actually returned) is now authoritatively
        # accounted for: present -> trading session; absent-but-within-span
        # -> confirmed non-trading (weekend/holiday). Deliberately NOT the
        # full originally-requested [start, end] window: if the response is
        # genuinely partial/truncated (a provider bug, incomplete pagination)
        # rather than malformed, trusting the full requested window would
        # silently mischaracterize real trading days beyond the response's
        # actual coverage as confirmed holidays. Dates in [start, end] but
        # outside the observed span are left untouched — neither revoked nor
        # marked closed — since this response did not actually address them.
        observed_min = min(new_schedule.keys())
        observed_max = max(new_schedule.keys())
        if observed_min > start or observed_max < end:
            logger.warning(
                f"[StockCalendarAuthority] partial calendar response: requested "
                f"{start}..{end}, observed span {observed_min}..{observed_max} — "
                f"only the observed span is authoritatively updated this refresh"
            )
        all_dates_in_observed_span = []
        d = observed_min
        while d <= observed_max:
            all_dates_in_observed_span.append(d)
            d += timedelta(days=1)

        with self._lock:
            for d in all_dates_in_observed_span:
                if d in new_schedule:
                    self._schedule[d] = new_schedule[d]
                    self._fetched_at[d] = now_epoch
                    self._fetched_at_et_date[d] = today
                    self._closed_dates.pop(d, None)
                    self._closed_dates_et_date.pop(d, None)
                else:
                    self._closed_dates[d] = now_epoch
                    self._closed_dates_et_date[d] = today
                    self._schedule.pop(d, None)
                    self._fetched_at.pop(d, None)
                    self._fetched_at_et_date.pop(d, None)
            self._last_accepted_refresh_epoch = now_epoch

        metrics.increment("calendar.refresh.success")
        logger.info(
            f"[StockCalendarAuthority] refreshed {len(new_schedule)} trading "
            f"sessions and {len(all_dates_in_observed_span) - len(new_schedule)} "
            f"confirmed non-trading dates (requested {start} to {end}, "
            f"observed {observed_min} to {observed_max})"
        )
        return True

    # ------------------------------------------------------------------
    # Freshness — every check requires BOTH: within the elapsed freshness
    # window AND fetched on the same ET calendar date as `now_epoch`.
    # ------------------------------------------------------------------

    def _is_fresh(self, fetched_at: Optional[int], fetched_at_et_date: Optional[date], now_epoch: int) -> bool:
        if fetched_at is None or fetched_at_et_date is None:
            return False
        if (now_epoch - fetched_at) > self._freshness_sec:
            return False
        if fetched_at_et_date != self._et_date(now_epoch):
            return False
        return True

    def _fresh_session(self, d: date, now_epoch: int) -> Optional[_SessionWindow]:
        with self._lock:
            window = self._schedule.get(d)
            fetched = self._fetched_at.get(d)
            fetched_et = self._fetched_at_et_date.get(d)
        if window is None or not self._is_fresh(fetched, fetched_et, now_epoch):
            if window is not None:
                logger.debug(
                    f"[StockCalendarAuthority] {d}: cached schedule exists but is not "
                    f"fresh (fetched={fetched}, fetched_et_date={fetched_et}, "
                    f"now_et_date={self._et_date(now_epoch)}) — treating as unknown"
                )
            return None
        return window

    def _is_confirmed_closed(self, d: date, now_epoch: int) -> Optional[bool]:
        """True if `d` is a confirmed non-trading date per a fresh refresh,
        None if unknown (never refreshed, stale, or wrong ET date) — None
        must never be treated as "assume closed", only as "cannot determine"."""
        with self._lock:
            fetched = self._closed_dates.get(d)
            fetched_et = self._closed_dates_et_date.get(d)
        if not self._is_fresh(fetched, fetched_et, now_epoch):
            return None
        return True

    def _walk_back_to_prior_session(
        self, start_date: date, now_epoch: int, max_days: int
    ) -> Optional[Tuple[date, _SessionWindow]]:
        """
        Walk backward from `start_date` (inclusive) up to `max_days`
        calendar days, skipping over dates confirmed non-trading
        (weekends/holidays), and return the first date with a fresh
        session. Returns None if an "unknown" date (neither a fresh session
        nor confirmed closed) is encountered, or if `max_days` is exhausted
        without finding a session — in both cases the caller must fail
        closed rather than guess further back.
        """
        d = start_date
        for _ in range(max_days + 1):
            window = self._fresh_session(d, now_epoch)
            if window is not None:
                return d, window
            if self._is_confirmed_closed(d, now_epoch):
                d = d - timedelta(days=1)
                continue
            return None
        return None

    def get_session(self, d: date, now_epoch: int) -> Optional[tuple]:
        """Return (open_epoch, close_epoch) for date `d` if a fresh (per the
        configured freshness window and same-ET-date requirement),
        successfully-parsed schedule is cached for it — else None. A date
        merely covered by an old cache is NOT treated as authoritative on
        its own."""
        window = self._fresh_session(d, now_epoch)
        if window is None:
            return None
        return (window.open_epoch, window.close_epoch)

    def is_confirmed_non_trading_day(self, d: date, now_epoch: int) -> Optional[bool]:
        """Public accessor for the confirmed-closed-date fact. Returns None
        (unknown) rather than False when we cannot confirm either way —
        callers must not treat None as "must be a trading day"."""
        return self._is_confirmed_closed(d, now_epoch)

    def is_regular_session_now(self, cutoff: ScanCutoff) -> Optional[bool]:
        """True/False if the schedule for `cutoff`'s date is fresh enough to
        answer confidently, else None (fail closed — caller must not assume
        either open or closed)."""
        d = self._et_date(cutoff.epoch)
        window = self._fresh_session(d, cutoff.epoch)
        if window is None:
            return None
        return window.open_epoch <= cutoff.epoch < window.close_epoch

    # ------------------------------------------------------------------
    # SessionAuthority protocol
    # ------------------------------------------------------------------

    def expected_latest_closed_bar_open(
        self, timeframe: str, cutoff: ScanCutoff
    ) -> Optional[int]:
        """
        Implements candle_validation.SessionAuthority. Returns the open-time
        epoch of the most recent bar that should already be closed as of
        `cutoff`, or None if this cannot be determined with confidence
        (missing/stale schedule, lookback budget exhausted, etc). Dispatches
        to a daily-specific or intraday-specific method since this system's
        assumed Alpaca timestamp convention differs by granularity (see the
        module-level `_INTRADAY_BAR_TIMESTAMP_CONVENTION` /
        `_DAILY_BAR_TIMESTAMP_CONVENTION` constants).
        """
        tf_sec = timeframe_seconds(timeframe)
        if tf_sec is None:
            return None
        if tf_sec >= 86400:
            return self._expected_daily_bar_open(cutoff)
        return self._expected_intraday_bar_open(tf_sec, cutoff)

    def _daily_bar_open_epoch(self, d: date, window: _SessionWindow) -> int:
        """Encodes `_DAILY_BAR_TIMESTAMP_CONVENTION`. See that constant's
        docstring — this specific mapping is unverified against a live
        Alpaca daily-bar response."""
        return window.open_epoch

    def _expected_daily_bar_open(self, cutoff: ScanCutoff) -> Optional[int]:
        today = self._et_date(cutoff.epoch)
        today_window = self._fresh_session(today, cutoff.epoch)
        if today_window is not None and today_window.close_epoch <= cutoff.epoch:
            # Today's session has already closed as of cutoff — today is the
            # latest completed daily bar.
            return self._daily_bar_open_epoch(today, today_window)

        # Today hasn't closed yet (or is unknown) — the latest completed
        # daily bar is the most recent prior session, traversing back across
        # any weekends/holidays as needed.
        found = self._walk_back_to_prior_session(today - timedelta(days=1), cutoff.epoch, self._days_behind)
        if found is None:
            return None
        prior_date, prior_window = found
        return self._daily_bar_open_epoch(prior_date, prior_window)

    def _expected_intraday_bar_open(self, tf_sec: int, cutoff: ScanCutoff) -> Optional[int]:
        """Encodes `_INTRADAY_BAR_TIMESTAMP_CONVENTION` (each bar's index is
        its own open time)."""
        today = self._et_date(cutoff.epoch)
        today_window = self._fresh_session(today, cutoff.epoch)
        if today_window is not None and today_window.open_epoch <= cutoff.epoch:
            bars_elapsed = (
                min(cutoff.epoch, today_window.close_epoch) - today_window.open_epoch
            ) // tf_sec
            if bars_elapsed > 0:
                return today_window.open_epoch + (bars_elapsed - 1) * tf_sec
            # bars_elapsed == 0: cutoff is exactly at today's open, no bar
            # has closed yet this session — fall through to the prior
            # session below.

        # Before today's open, today unknown, or zero bars elapsed today so
        # far — find the most recent prior completed session, traversing
        # back across any weekends/holidays as needed.
        found = self._walk_back_to_prior_session(today - timedelta(days=1), cutoff.epoch, self._days_behind)
        if found is None:
            return None
        prior_date, prior_window = found
        prior_bars = (prior_window.close_epoch - prior_window.open_epoch) // tf_sec
        if prior_bars <= 0:
            return None
        return prior_window.open_epoch + (prior_bars - 1) * tf_sec
