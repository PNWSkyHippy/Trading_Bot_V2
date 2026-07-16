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
      within config.STOCK_CALENDAR_FRESHNESS_SEC (tracked via an explicit
      per-date fetched_at, not "the date merely falls within some cached
      range").
    - A missing, stale (past the freshness window), or malformed schedule
      globally blocks entries/due-scheduling for that date — this class
      never silently falls back to core/market_calendar.py's hardcoded
      09:30-16:00 assumption for a live-freshness decision.
    - A changed schedule (emergency close, corrected early-close time)
      atomically replaces the prior cached entry for that date, never merges.

  This module is not yet wired into any live fetch/scan routing — Patch A is
  contracts and tests only. It implements the candle_validation.SessionAuthority
  protocol so Patch B/C can consume it directly once ready.
=============================================================
"""

import logging
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo

import config
from core import metrics
from core.candle_validation import ScanCutoff, timeframe_seconds

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")


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
        self._lock = threading.Lock()
        self._schedule: Dict[date, _SessionWindow] = {}
        self._fetched_at: Dict[date, int] = {}

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, now_epoch: Optional[int] = None) -> bool:
        """
        Fetch a fresh rolling window from Alpaca's get_calendar() and
        atomically replace the cached entries for every date in that window
        (never merge partial results into stale ones). Returns True only on
        a fully successful, fully parsed refresh.
        """
        if self._api is None:
            metrics.increment("calendar.refresh.failure")
            logger.warning("[StockCalendarAuthority] no API client configured — refresh skipped")
            return False

        now_epoch = now_epoch if now_epoch is not None else int(__import__("time").time())
        today = datetime.fromtimestamp(now_epoch, tz=timezone.utc).astimezone(EASTERN).date()
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
            # Malformed response: do not partially adopt it. A bad batch must
            # never silently replace good cached data with garbage for some
            # dates while leaving others untouched.
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", f"malformed calendar response: {e}", now_epoch)
            logger.error(f"[StockCalendarAuthority] malformed calendar response, rejecting entire batch: {e}")
            return False

        if not new_schedule:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", "refresh returned zero sessions", now_epoch)
            logger.warning("[StockCalendarAuthority] refresh returned zero sessions — rejecting")
            return False

        with self._lock:
            # Atomic replace: every date in this batch gets a fresh fetched_at
            # and its schedule is fully overwritten (B4's "atomic replace, not
            # merge" principle applied here to calendar data too).
            for d, window in new_schedule.items():
                self._schedule[d] = window
                self._fetched_at[d] = now_epoch

        metrics.increment("calendar.refresh.success")
        logger.info(
            f"[StockCalendarAuthority] refreshed {len(new_schedule)} sessions "
            f"({start} to {end})"
        )
        return True

    # ------------------------------------------------------------------
    # Queries — every method fails closed (returns None) on any uncertainty
    # ------------------------------------------------------------------

    def _fresh_session(self, d: date, now_epoch: int) -> Optional[_SessionWindow]:
        with self._lock:
            window = self._schedule.get(d)
            fetched = self._fetched_at.get(d)
        if window is None or fetched is None:
            return None
        if (now_epoch - fetched) > self._freshness_sec:
            logger.debug(
                f"[StockCalendarAuthority] {d}: cached schedule is stale "
                f"({now_epoch - fetched}s since last refresh, "
                f"freshness window {self._freshness_sec}s) — treating as unknown"
            )
            return None
        return window

    def get_session(self, d: date, now_epoch: int) -> Optional[tuple]:
        """Return (open_epoch, close_epoch) for date `d` if a fresh (per the
        configured freshness window), successfully-parsed schedule is cached
        for it — else None. A date merely covered by an old cache is NOT
        treated as authoritative on its own."""
        window = self._fresh_session(d, now_epoch)
        if window is None:
            return None
        return (window.open_epoch, window.close_epoch)

    def is_regular_session_now(self, cutoff: ScanCutoff) -> Optional[bool]:
        """True/False if the schedule for `cutoff`'s date is fresh enough to
        answer confidently, else None (fail closed — caller must not assume
        either open or closed)."""
        d = datetime.fromtimestamp(cutoff.epoch, tz=timezone.utc).astimezone(EASTERN).date()
        window = self._fresh_session(d, cutoff.epoch)
        if window is None:
            return None
        return window.open_epoch <= cutoff.epoch < window.close_epoch

    def expected_latest_closed_bar_open(
        self, timeframe: str, cutoff: ScanCutoff
    ) -> Optional[int]:
        """
        Implements candle_validation.SessionAuthority. Returns the open-time
        epoch of the most recent bar that should already be closed as of
        `cutoff`, aligned to the session's open time, or None if this cannot
        be determined with confidence (missing/stale schedule, daily
        timeframe with no intraday bar concept handled by the caller
        directly, etc.).
        """
        tf_sec = timeframe_seconds(timeframe)
        if tf_sec is None:
            return None
        if tf_sec >= 86400:
            # Daily bars: "the expected latest closed bar" is the most recent
            # completed trading session's date, not an intraday-aligned time.
            # Walk backwards through cached, fresh sessions to find it.
            for back in range(0, self._days_behind + 1):
                d = (
                    datetime.fromtimestamp(cutoff.epoch, tz=timezone.utc)
                    .astimezone(EASTERN).date() - timedelta(days=back)
                )
                window = self._fresh_session(d, cutoff.epoch)
                if window is not None and window.close_epoch <= cutoff.epoch:
                    return window.open_epoch
                if window is not None and back == 0:
                    # Today's session is fresh but hasn't closed yet — look
                    # further back for the prior completed session.
                    continue
                if window is None:
                    return None
            return None

        d = datetime.fromtimestamp(cutoff.epoch, tz=timezone.utc).astimezone(EASTERN).date()
        window = self._fresh_session(d, cutoff.epoch)
        if window is None:
            # Try the prior calendar day (cutoff may be before today's open,
            # e.g. pre-market) — the "latest expected closed bar" is then the
            # last bar of the previous session.
            prev_d = d - timedelta(days=1)
            window = self._fresh_session(prev_d, cutoff.epoch)
            if window is None:
                return None
            d = prev_d

        if cutoff.epoch < window.open_epoch:
            # Before session open: fall back one more session back.
            prev_d = d - timedelta(days=1)
            prev_window = self._fresh_session(prev_d, cutoff.epoch)
            if prev_window is None:
                return None
            window = prev_window

        session_end_for_bars = min(cutoff.epoch, window.close_epoch)
        bars_elapsed = (session_end_for_bars - window.open_epoch) // tf_sec
        if bars_elapsed <= 0:
            # No bar has closed yet this session as of cutoff — the latest
            # expected closed bar is the last bar of the prior session.
            prev_d = d - timedelta(days=1)
            prev_window = self._fresh_session(prev_d, cutoff.epoch)
            if prev_window is None:
                return None
            prev_bars = (prev_window.close_epoch - prev_window.open_epoch) // tf_sec
            if prev_bars <= 0:
                return None
            return prev_window.open_epoch + (prev_bars - 1) * tf_sec

        return window.open_epoch + (bars_elapsed - 1) * tf_sec
