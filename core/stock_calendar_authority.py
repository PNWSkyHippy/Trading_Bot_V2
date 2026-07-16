"""
=============================================================
  STOCK CALENDAR AUTHORITY — Patch A (B5)
  reports/agent_pipeline/20260716-082429/final_unified_report.md

  Wraps Alpaca's own market-calendar API (REST.get_calendar()) as the SOLE
  authoritative source of stock session open/close times, replacing the
  hand-maintained core/market_calendar.py approximation for live-freshness
  decisions. core/market_calendar.py implements only ten fixed full-day
  holidays and a hardcoded 09:30-16:00 window — it has no half-day/
  early-close, emergency-closure, or publication-delay modeling, and cannot
  support the strict "session-aware expected closed bar" contract this system
  requires. Alpaca is already this system's broker of record for stock data,
  so this introduces no new external dependency. core.market_calendar is NOT
  consulted anywhere in this module, including for completeness checking (an
  earlier revision cross-checked missing weekdays against its fixed-holiday
  list; that made this authority's correctness partially depend on a second,
  independently-fallible, hand-maintained data source — exactly the kind of
  approximation this class exists to replace, and it could either falsely
  reject a genuine Alpaca response for a holiday not in the local list, or
  falsely excuse a real Alpaca gap that happened to coincide with a listed
  holiday. See refresh() for how missing weekdays are now confirmed instead:
  a targeted, single-date follow-up call to Alpaca's own get_calendar(),
  never a local table.

  Decided contract (B5, not an either/or option menu; revised across several
  rounds of review — see the numbered points below for what changed and why):

    1. The daily schedule may be prefetched/cached for a rolling forward
       window, but merely covering a date is not sufficient to treat it as
       authoritative for that date.
    2. Before permitting any new entry or due-scheduling decision on a given
       trading date, there must have been a successful refresh *for that
       date* within config.STOCK_CALENDAR_FRESHNESS_SEC, AND that refresh
       must have occurred on the same Eastern-Time calendar date being
       evaluated (an elapsed-seconds check alone is not enough: a refresh at
       23:58 ET one day should not be treated as fresh deep into the next ET
       day merely because the elapsed-seconds window hasn't lapsed).
    3. A `refresh()` call is validated on two axes: a caller-supplied
       `now_epoch` unreasonably in the future (more than a small clock-skew
       tolerance ahead of the actual wall clock) is rejected outright; so is
       one earlier than the last accepted refresh's now_epoch (a possible
       system clock rollback), since accepting it could write fetched_at
       bookkeeping earlier than data already on file.
    4. A refresh is validated for COMPLETENESS before being adopted at all:
       every returned date must fall within the requested [start, end]
       window (otherwise: reject, "out-of-request-range"), and every weekday
       within [start, end] must be either returned as a trading session, a
       locally-verifiable weekend (no data needed — every calendar computes
       this identically), or independently confirmed non-trading by a
       TARGETED single-date get_calendar(start=d, end=d) follow-up call to
       Alpaca itself. If that targeted call instead confirms `d` IS a
       trading session, the original batch response omitted a real trading
       day (e.g. truncation/pagination) and is internally inconsistent — the
       ENTIRE refresh is rejected ("internally_incomplete_response" or
       "internally_inconsistent_response"). This replaces two earlier
       designs: first, one that tried to salvage a "safe subset" from a
       partial response by only updating its observed date span (which could
       still silently fabricate a false "confirmed holiday" for a genuine
       trading day within its own observed span); second, one that
       cross-checked missing weekdays against core.market_calendar's fixed
       local holiday list (which makes correctness depend on a second,
       independently-fallible data source instead of on Alpaca itself). The
       current design asks Alpaca to confirm or refute its own gap directly.
       An incomplete, inconsistent, or out-of-range response is rejected
       outright, and no previously-cached data for any date in [start, end]
       is touched — no stale entry is silently promoted to "reconfirmed",
       and no absent date is fabricated as a holiday.
    5. Only once completeness is proven does a refresh atomically replace
       AND revoke across the FULL requested [start, end] window: every date
       in that window not present in the (now-proven-complete) response is
       recorded as an explicit, authoritative "confirmed closed" fact — not
       merely absent — so that looking for the most recent prior completed
       session can correctly traverse weekends and holidays instead of
       stopping at the first uncached calendar day.
    6. This class never silently falls back to core/market_calendar.py's
       hardcoded 09:30-16:00 assumption for a live-freshness decision on a
       missing/stale/malformed schedule.

  Bar-timestamp conventions (encoded as representative fixtures — see
  Scripts/test_stock_calendar_authority.py's fixture tests, and the module-
  level convention constants below for the precise, independently-labeled
  assumption per granularity):
    - Intraday bars (5m/15m/1h/etc.) are aligned to a UTC wall-clock grid,
      NOT anchored to the session's own open time. A stock session's open
      (09:30 ET) is not aligned to a 60-minute clock grid, so the session's
      first 1-hour bar is a partial bar (09:30-10:00 ET), followed by full
      hour-aligned bars (10:00-11:00, 11:00-12:00, ...). 5-minute and
      15-minute bars remain session-open-aligned under this same rule as a
      *consequence* of 09:30's minute-of-hour (30) already being a multiple
      of 5 and 15 (but not of 60) — not because they are a special case. An
      earlier version of this module assumed ALL intraday granularities were
      anchored to session-open, which is specifically wrong for 1-hour bars.
    - Daily bars are timestamped at midnight UTC of the trading date — the
      common cross-provider convention for daily OHLC — not session open and
      not midnight Eastern. An earlier version of this module used the
      session-open time for daily bars and flagged it explicitly as
      unverified; this revision commits to a specific, cited convention
      instead of carrying that flag forward indefinitely.
    - A direct empirical check against this repository's own cached Alpaca
      stock candle history (data/candle_store.db) was attempted while
      writing this revision, specifically to measure the real convention
      from production data rather than from memory of documentation. The
      database file was found to be corrupted (`PRAGMA integrity_check`
      reported real btree structural damage — invalid page numbers,
      out-of-order rowids, duplicate page references — not a transient lock
      contention issue) and could not be used as a ground-truth source. This
      corruption is a separate, real production data-integrity problem
      worth investigating on its own; it is unrelated to this patch. The
      conventions above should be given a final live-response confirmation
      pass before Patch B/C wires this authority into real routing.

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
from typing import Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo

import config
from core import metrics
from core.candle_validation import ScanCutoff, timeframe_seconds

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

# Explicit, separately-documented, fixture-measured assumptions about
# Alpaca's own bar-timestamp convention per granularity (see module
# docstring for the full reasoning and the corrupted-local-cache caveat).
_INTRADAY_BAR_TIMESTAMP_CONVENTION = "utc_wall_clock_grid"
_DAILY_BAR_TIMESTAMP_CONVENTION = "midnight_utc_of_trading_date"


def _session_bar_opens(open_epoch: int, close_epoch: int, tf_sec: int) -> List[int]:
    """
    Enumerate the open-time epoch of every intraday bar in a session
    [open_epoch, close_epoch), per `_INTRADAY_BAR_TIMESTAMP_CONVENTION`:
    bars are aligned to a UTC wall-clock grid (multiples of tf_sec since the
    UTC epoch), not anchored to the session's own open time. The session's
    first bar starts exactly at `open_epoch` (a partial bar if `open_epoch`
    is not itself grid-aligned) and every subsequent bar starts at the next
    grid boundary, continuing until the next boundary would be at or past
    `close_epoch` (the final bar of a session may also be partial-width,
    ending exactly at `close_epoch` rather than the next full grid tick —
    trading stops at the session close regardless of grid alignment).
    """
    opens = []
    cursor = open_epoch
    while cursor < close_epoch:
        opens.append(cursor)
        if cursor % tf_sec == 0:
            cursor += tf_sec
        else:
            cursor = ((cursor // tf_sec) + 1) * tf_sec
    return opens


def _bar_close_epoch_in_session(
    open_epoch: int, session_open_epoch: int, session_close_epoch: int, tf_sec: int
) -> Optional[int]:
    """
    Authoritative close-time epoch for the bar opening at `open_epoch`
    within the session [session_open_epoch, session_close_epoch), per
    `_INTRADAY_BAR_TIMESTAMP_CONVENTION`. NEVER `open_epoch + tf_sec` — the
    session's first bar is a partial bar closing at the next UTC-grid
    boundary (or the session close, if that comes first), not a full
    `tf_sec` later. Derived from the SAME `_session_bar_opens` enumeration
    `_latest_closed_bar_open_in_session` uses, so the two can never
    disagree about where a given bar's close actually falls. Returns None
    if `open_epoch` is not itself a real bar-open time within this session.
    """
    opens = _session_bar_opens(session_open_epoch, session_close_epoch, tf_sec)
    if open_epoch not in opens:
        return None
    closes = opens[1:] + [session_close_epoch]
    return closes[opens.index(open_epoch)]


def _latest_closed_bar_open_in_session(
    open_epoch: int, close_epoch: int, tf_sec: int, cutoff_epoch
) -> Optional[int]:
    """Open-time epoch of the latest bar in the session whose close time is
    at or before `cutoff_epoch`, or None if no bar in the session has closed
    yet as of `cutoff_epoch`."""
    opens = _session_bar_opens(open_epoch, close_epoch, tf_sec)
    if not opens:
        return None
    closes = opens[1:] + [close_epoch]
    latest = None
    for o, c in zip(opens, closes):
        if c <= cutoff_epoch:
            latest = o
        else:
            break
    return latest


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
        # than the last successfully accepted refresh's now_epoch.
        self._last_accepted_refresh_epoch: Optional[int] = None

    @staticmethod
    def _et_date(epoch) -> date:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(EASTERN).date()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self, now_epoch: Optional[int] = None) -> bool:
        """
        Fetch a fresh rolling window from Alpaca's get_calendar(), validate
        it for completeness across the FULL requested [start, end] window,
        and only then atomically replace/revoke the cached entries for that
        entire window. Returns True only on a fully successful, fully
        parsed, fully complete refresh — a partial/incomplete/out-of-range
        response is rejected in full, touching no previously-cached data.
        """
        actual_now = int(time.time())

        if self._api is None:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure(
                "stock_calendar_authority", "no API client configured", actual_now,
            )
            logger.warning("[StockCalendarAuthority] no API client configured — refresh skipped")
            return False

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
            # inconsistent batch): do not partially adopt it.
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", f"malformed calendar response: {e}", now_epoch)
            logger.error(f"[StockCalendarAuthority] malformed calendar response, rejecting entire batch: {e}")
            return False

        if not new_schedule:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure("stock_calendar_authority", "refresh returned zero sessions", now_epoch)
            logger.warning("[StockCalendarAuthority] refresh returned zero sessions — rejecting")
            return False

        returned_dates = set(new_schedule.keys())

        # Reject outright if the response includes any date outside the
        # requested window — a suspicious/malformed response, not something
        # to silently accept a subset of.
        out_of_range = sorted(d for d in returned_dates if d < start or d > end)
        if out_of_range:
            metrics.increment("calendar.refresh.failure")
            metrics.alert_gate_failure(
                "stock_calendar_authority",
                f"response included {len(out_of_range)} date(s) outside requested "
                f"window {start}..{end}: {out_of_range[:5]}",
                now_epoch,
            )
            logger.error(
                f"[StockCalendarAuthority] rejecting refresh: response included "
                f"out-of-request-range dates: {out_of_range[:5]}"
            )
            return False

        # Completeness: every weekday in [start, end] must be either a
        # returned trading session, or independently confirmed non-trading
        # by Alpaca ITSELF via a targeted single-date follow-up call — never
        # by a separately-maintained local holiday list (see module
        # docstring point 4). Weekends are locally, deterministically
        # verifiable and require no confirmation at all.
        missing_candidates = []
        d = start
        while d <= end:
            if d not in returned_dates and d.weekday() < 5:
                missing_candidates.append(d)
            d += timedelta(days=1)

        for missing_date in missing_candidates:
            try:
                targeted = self._api.get_calendar(
                    start=missing_date.isoformat(), end=missing_date.isoformat()
                )
            except Exception as e:
                metrics.increment("calendar.refresh.failure")
                metrics.alert_gate_failure(
                    "stock_calendar_authority",
                    f"targeted completeness check for {missing_date} raised: {e} — "
                    f"original batch response is unverifiable, rejecting in full",
                    now_epoch,
                )
                logger.error(
                    f"[StockCalendarAuthority] rejecting refresh: targeted "
                    f"completeness check for {missing_date} raised: {e}"
                )
                return False
            if targeted:
                # Alpaca itself says `missing_date` IS a trading session when
                # asked directly — the original batch response is internally
                # inconsistent (e.g. truncated/paginated) and untrustworthy
                # as a whole, not merely missing one harmless entry.
                metrics.increment("calendar.refresh.failure")
                metrics.alert_gate_failure(
                    "stock_calendar_authority",
                    f"batch response omitted {missing_date} but a targeted "
                    f"get_calendar({missing_date}) call confirms it IS a trading "
                    f"session — original batch response is internally "
                    f"inconsistent, rejecting in full",
                    now_epoch,
                )
                logger.error(
                    f"[StockCalendarAuthority] rejecting refresh: {missing_date} "
                    f"omitted from batch but confirmed a trading day by a "
                    f"targeted call"
                )
                return False
            # Targeted call agrees `missing_date` is non-trading — it will be
            # recorded as an explicit confirmed-closed date below.

        # Completeness proven for the full [start, end] window — apply
        # atomically across the entire window now, not a narrowed subset.
        with self._lock:
            d = start
            while d <= end:
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
                d += timedelta(days=1)
            self._last_accepted_refresh_epoch = now_epoch

        metrics.increment("calendar.refresh.success")
        logger.info(
            f"[StockCalendarAuthority] refreshed {len(new_schedule)} trading "
            f"sessions and {(end - start).days + 1 - len(new_schedule)} "
            f"confirmed non-trading dates ({start} to {end})"
        )
        return True

    # ------------------------------------------------------------------
    # Freshness — every check requires BOTH: within the elapsed freshness
    # window AND fetched on the same ET calendar date as `now_epoch`.
    # ------------------------------------------------------------------

    def _is_fresh(self, fetched_at: Optional[int], fetched_at_et_date: Optional[date], now_epoch) -> bool:
        if fetched_at is None or fetched_at_et_date is None:
            return False
        if (now_epoch - fetched_at) > self._freshness_sec:
            return False
        if fetched_at_et_date != self._et_date(now_epoch):
            return False
        return True

    def _fresh_session(self, d: date, now_epoch) -> Optional[_SessionWindow]:
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

    def _is_confirmed_closed(self, d: date, now_epoch) -> Optional[bool]:
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
        self, start_date: date, now_epoch, max_days: int
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

    def _walk_forward_to_next_session(
        self, start_date: date, now_epoch, max_days: int
    ) -> Optional[Tuple[date, _SessionWindow]]:
        """Mirror of `_walk_back_to_prior_session`, walking forward. Used by
        `is_valid_session_gap` to prove a gap spans exactly one or more
        confirmed non-trading dates to the next real session, not an
        unexplained/unknown stretch."""
        d = start_date
        for _ in range(max_days + 1):
            window = self._fresh_session(d, now_epoch)
            if window is not None:
                return d, window
            if self._is_confirmed_closed(d, now_epoch):
                d = d + timedelta(days=1)
                continue
            return None
        return None

    def get_session(self, d: date, now_epoch) -> Optional[tuple]:
        """Return (open_epoch, close_epoch) for date `d` if a fresh (per the
        configured freshness window and same-ET-date requirement),
        successfully-parsed schedule is cached for it — else None. A date
        merely covered by an old cache is NOT treated as authoritative on
        its own."""
        window = self._fresh_session(d, now_epoch)
        if window is None:
            return None
        return (window.open_epoch, window.close_epoch)

    def is_confirmed_non_trading_day(self, d: date, now_epoch) -> Optional[bool]:
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
        `cutoff`, or None if this cannot be determined with confidence.
        Dispatches to a daily-specific or intraday-specific method per the
        distinct, independently-labeled bar-timestamp conventions at the top
        of this module.
        """
        tf_sec = timeframe_seconds(timeframe)
        if tf_sec is None:
            return None
        if tf_sec >= 86400:
            return self._expected_daily_bar_open(cutoff)
        return self._expected_intraday_bar_open(tf_sec, cutoff)

    def _daily_bar_open_epoch(self, d: date) -> int:
        """Encodes `_DAILY_BAR_TIMESTAMP_CONVENTION`: midnight UTC of the
        trading date."""
        return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())

    def _expected_daily_bar_open(self, cutoff: ScanCutoff) -> Optional[int]:
        today = self._et_date(cutoff.epoch)
        today_window = self._fresh_session(today, cutoff.epoch)
        if today_window is not None and today_window.close_epoch <= cutoff.epoch:
            # Today's session has already closed as of cutoff — today is the
            # latest completed daily bar.
            return self._daily_bar_open_epoch(today)

        found = self._walk_back_to_prior_session(today - timedelta(days=1), cutoff.epoch, self._days_behind)
        if found is None:
            return None
        prior_date, _ = found
        return self._daily_bar_open_epoch(prior_date)

    def _expected_intraday_bar_open(self, tf_sec: int, cutoff: ScanCutoff) -> Optional[int]:
        """Encodes `_INTRADAY_BAR_TIMESTAMP_CONVENTION` (UTC wall-clock grid
        alignment, with a partial first/last bar per session as needed —
        see `_session_bar_opens`)."""
        today = self._et_date(cutoff.epoch)
        today_window = self._fresh_session(today, cutoff.epoch)
        if today_window is not None and today_window.open_epoch <= cutoff.epoch:
            latest = _latest_closed_bar_open_in_session(
                today_window.open_epoch, today_window.close_epoch, tf_sec, cutoff.epoch
            )
            if latest is not None:
                return latest
            # No bar has closed yet this session as of cutoff — fall through
            # to the prior completed session below.

        found = self._walk_back_to_prior_session(today - timedelta(days=1), cutoff.epoch, self._days_behind)
        if found is None:
            return None
        _, prior_window = found
        return _latest_closed_bar_open_in_session(
            prior_window.open_epoch, prior_window.close_epoch, tf_sec, prior_window.close_epoch,
        )

    def bar_close_epoch(
        self, open_epoch: int, timeframe: str, cutoff: ScanCutoff
    ) -> Optional[int]:
        """
        Implements candle_validation.SessionAuthority. Returns the
        AUTHORITATIVE close-time epoch for the bar opening at `open_epoch`
        on `timeframe`, or None if this cannot be determined (unrefreshed/
        stale schedule for the relevant trading date, or an unrecognized
        timeframe). Never approximates this as `open_epoch + tf_sec`:

          - Intraday: dispatches to `_bar_close_epoch_in_session` against
            the fresh session covering `open_epoch`'s ET calendar date,
            which correctly returns a 30-minute close for a 1-hour bar
            opening at a 09:30 ET session open (the session's partial first
            bar), not a full hour later.
          - Daily: the bar's open (per `_DAILY_BAR_TIMESTAMP_CONVENTION`) is
            midnight UTC of the trading date, but its close is that
            session's real close time (16:00 ET, or an early-close time) —
            `open_epoch + 86400` would instead land near midnight UTC of
            the FOLLOWING day, many hours after the session (and its
            publication grace) has already elapsed.
        """
        tf_sec = timeframe_seconds(timeframe)
        if tf_sec is None:
            return None
        if tf_sec >= 86400:
            d = datetime.fromtimestamp(open_epoch, tz=timezone.utc).date()
            if self._daily_bar_open_epoch(d) != open_epoch:
                return None
            session = self._fresh_session(d, cutoff.epoch)
            if session is None:
                return None
            return session.close_epoch
        d = self._et_date(open_epoch)
        session = self._fresh_session(d, cutoff.epoch)
        if session is None:
            return None
        return _bar_close_epoch_in_session(
            open_epoch, session.open_epoch, session.close_epoch, tf_sec
        )

    def is_valid_session_gap(
        self, prior_bar_close_epoch: int, next_bar_open_epoch: int, cutoff: ScanCutoff
    ) -> Optional[bool]:
        """
        Implements candle_validation.SessionAuthority. Proves (or refuses to
        vouch for) that a gap between two consecutive bars corresponds to a
        legitimate non-trading period: `prior_bar_close_epoch` must be
        exactly some fresh trading session's close, `next_bar_open_epoch`
        must be exactly the NEXT fresh trading session's open (traversing
        any confirmed-closed weekend/holiday dates strictly between them),
        with every date in between confirmed non-trading. Returns None
        (never assumes "fine") if any part of this cannot be confirmed.
        """
        if next_bar_open_epoch <= prior_bar_close_epoch:
            return False
        now_epoch = cutoff.epoch
        d1 = self._et_date(prior_bar_close_epoch)
        window1 = self._fresh_session(d1, now_epoch)
        if window1 is None or window1.close_epoch != prior_bar_close_epoch:
            return None
        d2 = self._et_date(next_bar_open_epoch)
        window2 = self._fresh_session(d2, now_epoch)
        if window2 is None or window2.open_epoch != next_bar_open_epoch:
            return None
        if d2 <= d1:
            return False
        d = d1 + timedelta(days=1)
        while d < d2:
            if self._is_confirmed_closed(d, now_epoch) is not True:
                return None
            d += timedelta(days=1)
        return True
