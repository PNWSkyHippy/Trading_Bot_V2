"""Deterministic Easy Money Trade (EMT) paper-trading state machine.

The engine consumes completed one-minute bars for the exact cash-session
opening range and 610-tick bars/current-bar snapshots for the Keltner
midline, breakout, retracement, and confirmation. Paper fills are simulated;
live fills use an injected broker adapter with server-side protection.
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Deque, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from chart_patterns import PatternDetector


@dataclass(frozen=True)
class EMTEvent:
    time: str
    level: int
    kind: str
    direction: str
    price: float
    message: str


@dataclass
class PaperTrade:
    trade_id: str
    symbol: str
    direction: str
    quantity: int
    entry_time: str
    entry_price: float
    stop_price: float
    target_price: float
    entry_bar_time: str
    status: str = "open"
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    broker_strategy_id: Optional[int] = None
    execution_mode: str = "paper"


def _finite_number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric value: {value!r}")
    return number


def _parse_timestamp(value: object, source_timezone: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError("bar time is required")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
    return parsed.astimezone(timezone.utc)


def _clean_bar(bar: dict, source_timezone: str) -> dict:
    if not isinstance(bar, dict):
        raise ValueError("bar must be a dictionary")
    values = {
        name: _finite_number(bar.get(name))
        for name in ("open", "high", "low", "close", "volume")
    }
    if min(values[name] for name in ("open", "high", "low", "close")) <= 0:
        raise ValueError("OHLC prices must be positive")
    if values["volume"] < 0:
        raise ValueError("volume cannot be negative")
    if values["low"] > min(values["open"], values["close"]):
        raise ValueError("low is above the candle body")
    if values["high"] < max(values["open"], values["close"]):
        raise ValueError("high is below the candle body")
    return {
        "dt": _parse_timestamp(bar.get("time"), source_timezone),
        "time": str(bar.get("time")),
        **values,
    }


def _ema_last(values: Iterable[float], period: int) -> Optional[float]:
    values = list(values)
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _sma_last(values: Iterable[float], period: int) -> Optional[float]:
    values = list(values)
    if len(values) < period:
        return None
    return sum(float(value) for value in values[-period:]) / float(period)


def _true_ranges(bars: Iterable[dict]) -> List[float]:
    result: List[float] = []
    previous_close: Optional[float] = None
    for bar in bars:
        high = float(bar["high"])
        low = float(bar["low"])
        if previous_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        result.append(tr)
        previous_close = float(bar["close"])
    return result
class EMTStrategyEngine:
    """Stateful EMT evaluator for one configured futures contract."""

    def __init__(self, settings: dict, contract: dict, root_dir: str,
                 executor=None, db_mirror=None):
        self.settings = dict(settings or {})
        self.contract = dict(contract or {})
        self.root_dir = root_dir
        self.enabled = bool(self.settings.get("enabled", False))
        self.paper_only = bool(self.settings.get("paper_only", True))
        self.executor = executor
        if not self.paper_only and self.executor is None:
            raise ValueError("live EMT requires a configured broker executor")

        self.symbol = str(self.settings.get("symbol", "ES")).upper()
        self.broker_symbol = str(
            self.settings.get("broker_symbol")
            or self.settings.get("instrument")
            or self.symbol
        )
        self.source_timezone = str(
            self.settings.get("source_timezone", "America/Los_Angeles")
        )
        self.market_tz = ZoneInfo(
            str(self.settings.get("market_timezone", "America/New_York"))
        )
        self.tick_size = _finite_number(self.contract.get("tick_size", 0.25))
        self.tick_value = _finite_number(self.contract.get("tick_value", 12.50))
        self.point_value = self.tick_value / self.tick_size
        self.ema_period = int(self.settings.get("keltner_ema_period", 20))
        self.atr_period = int(self.settings.get("keltner_atr_period", 10))
        self.atr_mult = _finite_number(self.settings.get("keltner_atr_multiplier", 1.5))
        self.quantity = int(self.settings.get("contracts", 1))
        self.stop_points = _finite_number(self.settings.get("stop_points", 2.0))
        self.target_points = _finite_number(self.settings.get("target_points", 2.0))
        self.max_trades = int(self.settings.get("max_trades_per_session", 12))
        self.db_timezone = ZoneInfo(str(
            self.settings.get("db_timezone", "America/Los_Angeles")
        ))
        self.retrace_tolerance = (
            int(self.settings.get("retrace_tolerance_ticks", 1)) * self.tick_size
        )
        self.confirmation_distance = (
            int(self.settings.get("confirmation_ticks", 1)) * self.tick_size
        )
        self.pattern_lookback = int(
            self.settings.get("double_pattern_lookback_bars", 20)
        )
        self.pattern_tolerance = _finite_number(
            self.settings.get("double_pattern_tolerance_points", 1.0)
        )
        self.pattern_separation = int(
            self.settings.get("double_pattern_min_separation_bars", 2)
        )
        self.pattern_neckline = _finite_number(
            self.settings.get("double_pattern_neckline_points", 1.0)
        )
        self.pattern_detector = PatternDetector()
        self.range_start = self._clock(self.settings.get("opening_range_start", "09:30"))
        self.range_minutes = int(self.settings.get("opening_range_minutes", 15))
        self.trade_window_minutes = int(self.settings.get("trade_window_minutes", 60))
        self.ledger_path = os.path.join(
            root_dir,
            str(self.settings.get("ledger_path")
                or self.settings.get("paper_ledger_path", "emt_trades.jsonl")),
        )
        self.mirror_to_bot_db = bool(self.settings.get("mirror_to_bot_db", False))
        self.control_state_key = str(self.settings.get("control_state_key") or "").strip()
        self.db_mirror = db_mirror

        if self.quantity < 1 or self.ema_period < 2:
            raise ValueError("contracts must be >= 1 and keltner_ema_period >= 2")
        if self.stop_points <= 0 or self.target_points <= 0:
            raise ValueError("EMT stop and target distances must be positive")

        self.lock = threading.RLock()
        self.minute_bars: Deque[dict] = deque(maxlen=2000)
        self.tick_bars: Deque[dict] = deque(maxlen=2000)
        self.events: Deque[EMTEvent] = deque(maxlen=100)
        self.closed_trades: Deque[PaperTrade] = deque(maxlen=100)
        self.active_trade: Optional[PaperTrade] = None
        self.last_tick_received: Optional[float] = None
        self._event_counter = 0
        self._last_broker_check = 0.0
        self.last_execution_error: Optional[str] = None
        if self.mirror_to_bot_db and self.db_mirror is None:
            try:
                from data.database import db as bot_db
                self.db_mirror = bot_db
            except Exception as exc:
                self.last_execution_error = (
                    f"DB mirror unavailable: {type(exc).__name__}: {exc}"
                )
        self._reset_session(None)

    @staticmethod
    def _clock(value: object) -> dt_time:
        hour, minute = [int(part) for part in str(value).split(":", 1)]
        return dt_time(hour, minute)

    def _reset_session(self, session_date) -> None:
        self.session_date = session_date
        self.phase = "BUILDING_RANGE"
        self.direction: Optional[str] = None
        self.opening_high: Optional[float] = None
        self.opening_low: Optional[float] = None
        self.support_level: Optional[float] = None
        self.resistance_level: Optional[float] = None
        self.breakout_extreme: Optional[float] = None
        self.setup_start_index = 0
        self.retrace_seen = False
        self.retrace_touched = False
        self.last_live_price: Optional[float] = None
        self.trades_this_session = 0

    def _session_times(self, stamp_et: datetime):
        # Anchor on the session's own start date, not the bar's calendar date.
        # Overnight sessions (e.g. 22:01 ET range start with an 8h trade
        # window) cross midnight ET; re-deriving the window from stamp_et's
        # date would silently roll the window forward mid-session.
        anchor = self.session_date if self.session_date is not None else stamp_et.date()
        start = datetime.combine(anchor, self.range_start, tzinfo=self.market_tz)
        range_end = start + timedelta(minutes=self.range_minutes)
        trade_end = range_end + timedelta(minutes=self.trade_window_minutes)
        return start, range_end, trade_end

    def _ensure_session(self, stamp_et: datetime) -> None:
        if self.session_date is None:
            self._reset_session(stamp_et.date())
            return
        # Only start a new session once the current one's trade window has
        # actually elapsed -- not merely when the ET calendar date rolls over,
        # which happens mid-window for any session spanning midnight ET.
        _, _, trade_end = self._session_times(stamp_et)
        if stamp_et >= trade_end:
            self._reset_session(stamp_et.date())

    def _emit(self, stamp: datetime, level: int, kind: str, direction: str,
              price: float, message: str) -> None:
        event = EMTEvent(
            time=stamp.astimezone(timezone.utc).isoformat(),
            level=level,
            kind=kind,
            direction=direction,
            price=round(price, 8),
            message=message,
        )
        self.events.append(event)

    def _status_message(self, stamp_et: Optional[datetime] = None) -> str:
        stamp_et = stamp_et or datetime.now(self.market_tz)
        start, range_end, trade_end = self._session_times(stamp_et)
        phase_text = {
            "BUILDING_RANGE": "Building opening range",
            "RANGE_DATA_MISSED": "Opening range data missing (no 1-minute bars received) — no trades this session",
            "WARMING": "Warming Keltner data",
            "WAIT_BREAKOUT": "Waiting for breakout",
            "WAIT_RETRACE": "Breakout seen; waiting for retracement",
            "RETRACE_TOUCHED": "Retracement touched; waiting for confirmation",
            "IN_TRADE": "Trade active",
            "SESSION_DONE": "Trade window complete",
            "EXECUTION_HALTED": "Execution halted",
        }.get(self.phase, self.phase)
        bits = [phase_text]
        if self.opening_low is not None and self.opening_high is not None:
            bits.append(f"OR {self.opening_low:.2f}-{self.opening_high:.2f}")
        else:
            bits.append(f"OR window {start.strftime('%H:%M')}-{range_end.strftime('%H:%M')} ET")
        if self.support_level is not None or self.resistance_level is not None:
            bits.append(f"S/R {self.support_level if self.support_level is not None else '--'}/{self.resistance_level if self.resistance_level is not None else '--'}")
        if self.direction:
            bits.append(f"bias {self.direction.upper()}")
        bits.append(f"trades {self.trades_this_session}/{self.max_trades}")
        bits.append(f"ends {trade_end.strftime('%H:%M')} ET")
        return " | ".join(str(x) for x in bits)

    def _state_signature(self) -> tuple:
        return (
            self.phase,
            self.direction,
            None if self.opening_high is None else round(float(self.opening_high), 2),
            None if self.opening_low is None else round(float(self.opening_low), 2),
            None if self.support_level is None else round(float(self.support_level), 2),
            None if self.resistance_level is None else round(float(self.resistance_level), 2),
            None if self.active_trade is None else self.active_trade.trade_id,
            self.trades_this_session,
        )

    def _emit_if_state_changed(self, stamp: datetime, old_signature: tuple, price: float = 0.0) -> None:
        if self._state_signature() == old_signature:
            return
        kind = "STATUS"
        if self.phase == "WAIT_BREAKOUT":
            kind = "WAIT_BREAKOUT"
        elif self.phase == "WAIT_RETRACE":
            kind = "WAIT_RETRACE"
        elif self.phase == "RETRACE_TOUCHED":
            kind = "WAIT_CONFIRMATION"
        elif self.phase == "BUILDING_RANGE":
            kind = "BUILDING_RANGE"
        elif self.phase == "IN_TRADE":
            kind = "IN_TRADE"
        elif self.phase == "SESSION_DONE":
            kind = "SESSION_DONE"
        self._emit(stamp, 1, kind, self.direction or "", float(price or self.last_live_price or 0.0), self._status_message(stamp.astimezone(self.market_tz)))

    def _keltner_points(self, limit: int = 400) -> dict:
        # _ema_last() reseeds at closes[0] of whatever slice it's given, and
        # that seed's influence only decays to ~0 after several dozen bars.
        # Slicing straight to the last `limit` bars would make closes[0] --
        # and therefore every point's value -- shift each time the window
        # rolls forward by one bar, which reads as the whole line jittering
        # between polls. Pull in extra warmup history so the seed has fully
        # decayed by the time a bar enters the returned window, then only
        # emit the last `limit` points.
        warmup = max(self.ema_period, self.atr_period) * 10
        bars = list(self.tick_bars)[-(limit + warmup):]
        closes = [float(b["close"]) for b in bars]
        trs = _true_ranges(bars)
        mid, upper, lower = [], [], []
        start_idx = max(0, len(bars) - limit)
        for idx, bar in enumerate(bars):
            if idx < start_idx:
                continue
            t = int(_parse_timestamp(bar["time"], self.source_timezone).timestamp())
            m = _ema_last(closes[:idx + 1], self.ema_period)
            a = _sma_last(trs[:idx + 1], self.atr_period)
            if m is None or a is None:
                continue
            band = a * self.atr_mult
            mid.append({"time": t, "value": round(m, 6)})
            upper.append({"time": t, "value": round(m + band, 6)})
            lower.append({"time": t, "value": round(m - band, 6)})
        return {"mid": mid, "upper": upper, "lower": lower}

    def chart_overlay(self) -> dict:
        with self.lock:
            bars = []
            for bar in list(self.tick_bars)[-600:]:
                try:
                    bars.append({
                        "time": int(_parse_timestamp(bar["time"], self.source_timezone).timestamp()),
                        "open": float(bar["open"]),
                        "high": float(bar["high"]),
                        "low": float(bar["low"]),
                        "close": float(bar["close"]),
                        "volume": float(bar.get("volume", 0) or 0),
                    })
                except Exception:
                    continue
            return {
                "status_message": self._status_message(),
                "phase": self.phase,
                "direction": self.direction,
                "support_level": self.support_level,
                "resistance_level": self.resistance_level,
                "opening_high": self.opening_high,
                "opening_low": self.opening_low,
                "breakout_extreme": self.breakout_extreme,
                "last_live_price": self.last_live_price,
                "keltner": self._keltner_points(),
                "tick_bars_data": bars,
                "events": [asdict(event) for event in list(self.events)[-30:]],
            }
    def on_minute_bar(self, raw_bar: dict, historical: bool = False) -> None:
        self._refresh_runtime_enabled()
        if not self.enabled:
            return
        bar = _clean_bar(raw_bar, self.source_timezone)
        stamp_et = bar["dt"].astimezone(self.market_tz)
        with self.lock:
            self._ensure_session(stamp_et)
            old_signature = self._state_signature()
            self._upsert(self.minute_bars, bar)
            start, range_end, _ = self._session_times(stamp_et)
            if start <= stamp_et < range_end:
                self.opening_high = (
                    bar["high"] if self.opening_high is None
                    else max(self.opening_high, bar["high"])
                )
                self.opening_low = (
                    bar["low"] if self.opening_low is None
                    else min(self.opening_low, bar["low"])
                )
            if stamp_et >= range_end and self.opening_high is not None:
                if self.resistance_level is None:
                    self.resistance_level = self.opening_high
                    self.support_level = self.opening_low
                if self.phase == "BUILDING_RANGE":
                    self.phase = "WAIT_BREAKOUT"

            self._emit_if_state_changed(bar["dt"], old_signature, bar["close"])

    @staticmethod
    def _upsert(values: Deque[dict], bar: dict) -> None:
        rows = {item["time"]: item for item in values}
        rows[bar["time"]] = bar
        ordered = sorted(rows.values(), key=lambda item: item["dt"])[-values.maxlen:]
        values.clear()
        values.extend(ordered)

    def on_tick_bar(self, raw_bar: dict, complete: bool,
                    historical: bool = False) -> List[EMTEvent]:
        self._refresh_runtime_enabled()
        if not self.enabled and self.active_trade is None:
            return []
        bar = _clean_bar(raw_bar, self.source_timezone)
        root_symbol = str(raw_bar.get("symbol", "")).split()[0].upper()
        if root_symbol != self.symbol:
            return []
        if int(raw_bar.get("bar_value", 610)) != int(self.settings.get("tick_bar_value", 610)):
            raise ValueError("unexpected EMT tick-bar size")

        with self.lock:
            before = len(self.events)
            stamp_et = bar["dt"].astimezone(self.market_tz)
            if historical:
                if complete:
                    self._upsert(self.tick_bars, bar)
                self.last_tick_received = datetime.now(timezone.utc).timestamp()
                return []
            self._ensure_session(stamp_et)
            old_signature = self._state_signature()
            if complete:
                self._upsert(self.tick_bars, bar)
            self.last_tick_received = datetime.now(timezone.utc).timestamp()
            self._evaluate(bar, stamp_et, complete)
            self._emit_if_state_changed(bar["dt"], old_signature, bar["close"])
            return list(self.events)[before:]

    def _midline(self, current_close: float, complete: bool) -> Optional[float]:
        closes = [item["close"] for item in self.tick_bars]
        if complete and closes:
            return _ema_last(closes, self.ema_period)
        return _ema_last([*closes, current_close], self.ema_period)

    def _evaluate(self, bar: dict, stamp_et: datetime, complete: bool) -> None:
        start, range_end, trade_end = self._session_times(stamp_et)
        # Captured before being overwritten below: RETRACE_TOUCHED needs the
        # prior tick's price (not this one's) to tell whether price is still
        # moving away from the Keltner midline.
        previous_live_price = self.last_live_price
        self.last_live_price = bar["close"]
        # Broker strategies remain active outside the entry window. Keep
        # reconciling them so a completed overnight/server-side bracket cannot
        # leave stale in-memory state or permit a duplicate next session.
        if self.active_trade is not None and not self.paper_only:
            self._update_trade_extreme(bar)
            self._reconcile_live_trade(bar, stamp_et)
            return
        if stamp_et < range_end:
            self.phase = "BUILDING_RANGE"
            return
        if stamp_et >= trade_end:
            # Check this before RANGE_DATA_MISSED: _ensure_session() can roll
            # straight into a brand-new session for a stale/late bar whose
            # own trade window has already elapsed too (opening_high/low get
            # reset to None in the process). SESSION_DONE is the accurate
            # terminal state for "the window is over" regardless of whether
            # the range was ever captured, so it must take priority.
            if self.active_trade is not None and self.paper_only:
                self._close_trade(bar["close"], stamp_et, "trade_window_end")
            self.phase = "SESSION_DONE"
            return
        if self.opening_high is None or self.opening_low is None:
            # The opening-range window has already closed but on_minute_bar()
            # never received a single 1-minute bar inside [start, range_end)
            # (e.g. the bridge/tunnel was down through the whole window).
            # opening_high/low can only ever be set from bars inside that
            # window, so BUILDING_RANGE would otherwise persist for the rest
            # of the session -- surface the real reason instead of looking
            # like it is still about to finish.
            if self.phase != "RANGE_DATA_MISSED":
                self.phase = "RANGE_DATA_MISSED"
                self._emit(
                    bar["dt"], 1, "RANGE_DATA_MISSED", self.direction or "", bar["close"],
                    "Opening range window closed with no 1-minute bar data received; "
                    "no trades this session",
                )
            return
        if self.resistance_level is None:
            self.resistance_level = self.opening_high
            self.support_level = self.opening_low
            self.phase = "WAIT_BREAKOUT"
        if stamp_et < start or self.trades_this_session >= self.max_trades:
            return

        if self.active_trade is not None:
            self._update_trade_extreme(bar)
            self._check_exit(bar, stamp_et, complete)
            return

        midline = self._midline(bar["close"], complete)
        if midline is None:
            self.phase = "WARMING"
            return

        price = bar["close"]
        if self.phase in ("BUILDING_RANGE", "WARMING"):
            self.phase = "WAIT_BREAKOUT"

        if self.phase == "WAIT_BREAKOUT":
            if price < self.support_level and midline < self.support_level:
                self._arm_breakout("short", bar, stamp_et, midline)
            elif price > self.resistance_level and midline > self.resistance_level:
                self._arm_breakout("long", bar, stamp_et, midline)
            self.last_live_price = price
            return

        if self.phase == "WAIT_RETRACE":
            self._track_retrace(bar, stamp_et, midline, complete)
            self.last_live_price = price
            return

        if self.phase == "RETRACE_TOUCHED":
            previous = previous_live_price
            away = (
                self.direction == "short"
                and price <= midline - self.confirmation_distance
                and previous is not None and price < previous
            ) or (
                self.direction == "long"
                and price >= midline + self.confirmation_distance
                and previous is not None and price > previous
            )
            if away:
                if self._adverse_double_pattern(self.direction):
                    self._emit(
                        bar["dt"], 0, "PATTERN_BLOCK", self.direction, price,
                        "Entry blocked by adverse double-top/double-bottom reversal pattern",
                    )
                    self._reset_setup_after_block()
                else:
                    self._open_trade(price, stamp_et, bar["time"])
            self.last_live_price = price

    def _arm_breakout(self, direction: str, bar: dict,
                      stamp_et: datetime, midline: float) -> None:
        self.direction = direction
        self.phase = "WAIT_RETRACE"
        self.breakout_extreme = bar["low"] if direction == "short" else bar["high"]
        self.setup_start_index = max(0, len(self.tick_bars) - 4)
        self.retrace_seen = False
        self.retrace_touched = False
        level = self.support_level if direction == "short" else self.resistance_level
        self._emit(
            bar["dt"], 1, "BREAKOUT", direction, bar["close"],
            f"Price and Keltner midline {midline:.2f} broke {level:.2f}; waiting for retracement",
        )

    def _track_retrace(self, bar: dict, stamp_et: datetime,
                       midline: float, complete: bool) -> None:
        price = bar["close"]
        if self.direction == "short":
            prior_extreme = self.breakout_extreme
            self.breakout_extreme = min(self.breakout_extreme, bar["low"])
            if price >= self.breakout_extreme + self.confirmation_distance:
                self.retrace_seen = True
            touched = price >= midline - self.retrace_tolerance
            continued = self.retrace_seen and price < prior_extreme
            if continued and not touched:
                self.support_level = prior_extreme
                self.retrace_seen = False
                self._emit(
                    bar["dt"], 1, "CONTINUATION_BREAKOUT", "short", price,
                    f"Failed retracement; tracking new support {self.support_level:.2f}",
                )
        else:
            prior_extreme = self.breakout_extreme
            self.breakout_extreme = max(self.breakout_extreme, bar["high"])
            if price <= self.breakout_extreme - self.confirmation_distance:
                self.retrace_seen = True
            touched = price <= midline + self.retrace_tolerance
            continued = self.retrace_seen and price > prior_extreme
            if continued and not touched:
                self.resistance_level = prior_extreme
                self.retrace_seen = False
                self._emit(
                    bar["dt"], 1, "CONTINUATION_BREAKOUT", "long", price,
                    f"Failed retracement; tracking new resistance {self.resistance_level:.2f}",
                )
        if touched:
            self.phase = "RETRACE_TOUCHED"
            self.retrace_touched = True
            self._emit(
                bar["dt"], 2, "RETRACE", self.direction, price,
                f"Retracement reached Keltner midline {midline:.2f}; waiting for reversal confirmation",
            )

    def _adverse_double_pattern(self, direction: str) -> bool:
        """Use the shared chart-pattern pivot definition with ES-sized thresholds.

        The root detector's full confirmed W/M rules require percentage moves
        appropriate to stocks/crypto (a 3% neckline), which is far too large
        for a two-point ES scalp. EMT therefore reuses its pivot extraction but
        applies configured point distances. The result is a veto only.
        """
        bars = list(self.tick_bars)[self.setup_start_index:][-self.pattern_lookback:]
        if len(bars) < 9:
            return False
        if direction == "short":
            values = [bar["low"] for bar in bars]
            pivots = self.pattern_detector._pivot_lows_idx(values)
        else:
            values = [bar["high"] for bar in bars]
            pivots = self.pattern_detector._pivot_highs_idx(values)
        if len(pivots) < 2:
            return False
        first, second = pivots[-2], pivots[-1]
        if second[0] - first[0] < self.pattern_separation:
            return False
        if abs(first[1] - second[1]) > self.pattern_tolerance:
            return False
        between = bars[first[0]:second[0] + 1]
        if direction == "short":
            neckline = max(bar["high"] for bar in between)
            return neckline - max(first[1], second[1]) >= self.pattern_neckline
        neckline = min(bar["low"] for bar in between)
        return min(first[1], second[1]) - neckline >= self.pattern_neckline

    def _reset_setup_after_block(self) -> None:
        if self.direction == "short" and self.breakout_extreme is not None:
            self.support_level = self.breakout_extreme
        elif self.direction == "long" and self.breakout_extreme is not None:
            self.resistance_level = self.breakout_extreme
        self.phase = "WAIT_BREAKOUT"
        self.direction = None
        self.retrace_seen = False
        self.retrace_touched = False

    def _open_trade(self, price: float, stamp_et: datetime,
                    entry_bar_time: str) -> None:
        self._event_counter += 1
        direction = self.direction
        if direction == "long":
            stop = price - self.stop_points
            target = price + self.target_points
        else:
            stop = price + self.stop_points
            target = price - self.target_points
        mode = "paper" if self.paper_only else "live"
        trade_id = (
            f"EMT-{mode.upper()}-"
            f"{stamp_et.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
            f"-{self._event_counter}"
        )
        trade = PaperTrade(
            trade_id=trade_id,
            symbol=self.symbol,
            direction=direction,
            quantity=self.quantity,
            entry_time=stamp_et.astimezone(timezone.utc).isoformat(),
            entry_price=round(price, 8),
            stop_price=round(stop, 8),
            target_price=round(target, 8),
            entry_bar_time=entry_bar_time,
            execution_mode=mode,
        )
        if not self.paper_only:
            try:
                accepted = self.executor.place_bracket(
                    symbol=self.broker_symbol,
                    direction=direction,
                    quantity=self.quantity,
                    stop_points=self.stop_points,
                    target_points=self.target_points,
                    tick_size=self.tick_size,
                    client_id=trade_id,
                )
                trade.broker_strategy_id = int(accepted.strategy_id)
            except Exception as exc:
                # Never retry an ambiguous submission; that could double size.
                self.last_execution_error = f"{type(exc).__name__}: {exc}"
                self.phase = "EXECUTION_HALTED"
                self._emit(
                    stamp_et.astimezone(timezone.utc), 0, "ORDER_ERROR",
                    direction, price,
                    f"LIVE ORDER HALTED: {self.last_execution_error}",
                )
                return
        self.active_trade = trade
        self.trades_this_session += 1
        self.phase = "IN_TRADE"
        self._write_ledger("OPEN", trade)
        self._mirror_open_trade(trade)
        self._emit(
            stamp_et.astimezone(timezone.utc), 3,
            "PAPER_ENTRY" if self.paper_only else "LIVE_ENTRY",
            direction, price,
            f"{mode.upper()} {direction.upper()} {self.quantity} {self.broker_symbol} "
            f"| 2-sided broker bracket | stop {stop:.2f} | target {target:.2f}",
        )

    def _update_trade_extreme(self, bar: dict) -> None:
        direction = self.active_trade.direction if self.active_trade else self.direction
        if direction == "short":
            self.breakout_extreme = (
                bar["low"] if self.breakout_extreme is None
                else min(self.breakout_extreme, bar["low"])
            )
        else:
            self.breakout_extreme = (
                bar["high"] if self.breakout_extreme is None
                else max(self.breakout_extreme, bar["high"])
            )

    def _reconcile_live_trade(self, bar: dict, stamp_et: datetime) -> None:
        now = datetime.now(timezone.utc).timestamp()
        interval = float(self.settings.get("broker_status_interval_seconds", 2.0))
        if now - self._last_broker_check < interval:
            return
        self._last_broker_check = now
        trade = self.active_trade
        try:
            status = self.executor.strategy_status(trade.broker_strategy_id)
        except Exception as exc:
            self.last_execution_error = f"{type(exc).__name__}: {exc}"
            self._emit(
                stamp_et.astimezone(timezone.utc), 0, "BROKER_STATUS_ERROR",
                trade.direction, bar["close"], self.last_execution_error,
            )
            return
        if status == "closed":
            self._mark_broker_closed(bar["close"], stamp_et, "broker_bracket_complete")
        elif status == "rejected":
            self._mark_broker_closed(bar["close"], stamp_et, "broker_rejected")
            self.phase = "EXECUTION_HALTED"

    def _mark_broker_closed(self, observed_price: float, stamp_et: datetime,
                            reason: str) -> None:
        trade = self.active_trade
        if trade is None:
            return
        trade.status = "closed"
        trade.exit_time = stamp_et.astimezone(timezone.utc).isoformat()
        trade.exit_price = round(observed_price, 8)
        trade.exit_reason = reason
        trade.pnl = None  # Exact broker fill and fees are not inferred.
        self.closed_trades.append(trade)
        self._write_ledger("CLOSE", trade)
        self._mirror_close_trade(trade)
        self._emit(
            stamp_et.astimezone(timezone.utc), 0, "LIVE_EXIT",
            trade.direction, observed_price,
            f"LIVE strategy {trade.broker_strategy_id} {reason}",
        )
        if trade.direction == "short" and self.breakout_extreme is not None:
            self.support_level = self.breakout_extreme
        elif trade.direction == "long" and self.breakout_extreme is not None:
            self.resistance_level = self.breakout_extreme
        self.active_trade = None
        self.phase = "WAIT_BREAKOUT"
        self.direction = None
        self.retrace_seen = False
        self.retrace_touched = False

    def _check_exit(self, bar: dict, stamp_et: datetime, complete: bool) -> None:
        trade = self.active_trade
        same_entry_bar = bar["time"] == trade.entry_bar_time
        observed_low = bar["close"] if same_entry_bar else bar["low"]
        observed_high = bar["close"] if same_entry_bar else bar["high"]
        if trade.direction == "long":
            stop_hit = observed_low <= trade.stop_price
            target_hit = observed_high >= trade.target_price
        else:
            stop_hit = observed_high >= trade.stop_price
            target_hit = observed_low <= trade.target_price
        # If a completed bar spans both levels, use the pessimistic ordering.
        if stop_hit:
            self._close_trade(trade.stop_price, stamp_et, "stop_loss")
        elif target_hit:
            self._close_trade(trade.target_price, stamp_et, "take_profit")

    def _close_trade(self, price: float, stamp_et: datetime, reason: str) -> None:
        trade = self.active_trade
        if trade is None:
            return
        points = (
            price - trade.entry_price
            if trade.direction == "long"
            else trade.entry_price - price
        )
        trade.status = "closed"
        trade.exit_time = stamp_et.astimezone(timezone.utc).isoformat()
        trade.exit_price = round(price, 8)
        trade.exit_reason = reason
        trade.pnl = round(points * self.point_value * trade.quantity, 2)
        self.closed_trades.append(trade)
        self._write_ledger("CLOSE", trade)
        self._mirror_close_trade(trade)
        self._emit(
            stamp_et.astimezone(timezone.utc), 0, "PAPER_EXIT", trade.direction, price,
            f"PAPER EXIT {reason} | P&L ${trade.pnl:.2f}",
        )
        if trade.direction == "short" and self.breakout_extreme is not None:
            self.support_level = self.breakout_extreme
        elif trade.direction == "long" and self.breakout_extreme is not None:
            self.resistance_level = self.breakout_extreme
        self.active_trade = None
        self.phase = "WAIT_BREAKOUT"
        self.direction = None
        self.retrace_seen = False
        self.retrace_touched = False

    def _refresh_runtime_enabled(self) -> None:
        if not self.control_state_key or self.db_mirror is None:
            return
        try:
            raw = self.db_mirror.get_state(self.control_state_key, default=self.enabled)
            self.enabled = str(raw).strip().lower() not in {
                "0", "false", "no", "off", "disabled"
            }
        except Exception as exc:
            self.last_execution_error = (
                f"DB control read failed: {type(exc).__name__}: {exc}"
            )

    def _write_ledger(self, action: str, trade: PaperTrade) -> None:
        directory = os.path.dirname(self.ledger_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        record = {"action": action, **asdict(trade)}
        with open(self.ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _db_time(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(self.db_timezone).replace(tzinfo=None).isoformat()

    def _db_position_value(self, trade: PaperTrade) -> float:
        mode = str(self.settings.get("db_position_value_mode", "risk")).lower()
        if mode == "notional":
            return round(trade.entry_price * self.point_value * trade.quantity, 2)
        return round(self.stop_points * self.point_value * trade.quantity, 2)

    def _db_payload(self, trade: PaperTrade) -> dict:
        position_value = self._db_position_value(trade)
        notional_value = round(trade.entry_price * self.point_value * trade.quantity, 2)
        indicators = {
            "strategy_name": "emt",
            "signal_source": "emt",
            "root_symbol": self.symbol,
            "broker_symbol": self.broker_symbol,
            "execution_mode": trade.execution_mode,
            "entry_bar_time": trade.entry_bar_time,
            "tick_size": self.tick_size,
            "tick_value": self.tick_value,
            "point_value": self.point_value,
            "stop_points": self.stop_points,
            "target_points": self.target_points,
            "notional_value": notional_value,
            "position_value_mode": str(
                self.settings.get("db_position_value_mode", "risk")
            ).lower(),
        }
        return {
            "trade_id": trade.trade_id,
            "symbol": self.broker_symbol,
            "asset_class": "future",
            "direction": trade.direction,
            "entry_time": self._db_time(trade.entry_time),
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "position_value": position_value,
            "stop_loss": trade.stop_price,
            "take_profit": trade.target_price,
            "signal_score": 1.0,
            "indicators": indicators,
            "broker": "paper_emt" if trade.execution_mode == "paper" else "tradovate",
            "broker_order_id": (
                str(trade.broker_strategy_id)
                if trade.broker_strategy_id is not None else None
            ),
            "strategy_name": "emt",
            "entry_timeframe": f"{int(self.settings.get('tick_bar_value', 610))}Tick",
            "event_id": trade.trade_id,
        }

    def _mirror_open_trade(self, trade: PaperTrade) -> None:
        if not self.mirror_to_bot_db or self.db_mirror is None:
            return
        try:
            result = self.db_mirror.open_trade(self._db_payload(trade))
            if result.get("status") == "conflict":
                self.last_execution_error = (
                    f"DB mirror conflict for {trade.trade_id}: "
                    f"{result.get('conflicting_fields')}"
                )
        except Exception as exc:
            self.last_execution_error = (
                f"DB mirror open failed: {type(exc).__name__}: {exc}"
            )

    def _mirror_close_trade(self, trade: PaperTrade) -> None:
        if not self.mirror_to_bot_db or self.db_mirror is None:
            return
        try:
            pnl = float(trade.pnl or 0.0)
            position_value = self._db_position_value(trade)
            pnl_pct = (pnl / position_value * 100.0) if position_value else 0.0
            self.db_mirror.close_trade(
                trade.trade_id,
                float(trade.exit_price or trade.entry_price),
                str(trade.exit_reason or "emt_closed"),
                round(pnl, 2),
                round(pnl_pct, 4),
            )
        except Exception as exc:
            self.last_execution_error = (
                f"DB mirror close failed: {type(exc).__name__}: {exc}"
            )

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "enabled": self.enabled,
                "paper_only": self.paper_only,
                "execution_mode": "paper" if self.paper_only else "live",
                "broker_symbol": self.broker_symbol,
                "symbol": self.symbol,
                "phase": self.phase,
                "session_date": None if self.session_date is None else str(self.session_date),
                "opening_high": self.opening_high,
                "opening_low": self.opening_low,
                "support_level": self.support_level,
                "resistance_level": self.resistance_level,
                "direction": self.direction,
                "tick_bars": len(self.tick_bars),
                "trades_this_session": self.trades_this_session,
                "active_trade": None if self.active_trade is None else asdict(self.active_trade),
                "last_execution_error": self.last_execution_error,
                "last_closed_trade": (
                    None if not self.closed_trades else asdict(self.closed_trades[-1])
                ),
                "status_message": self._status_message(),
                "last_live_price": self.last_live_price,
                "breakout_extreme": self.breakout_extreme,
                "keltner": self._keltner_points(),
                "events": [asdict(event) for event in list(self.events)[-30:]],
            }
