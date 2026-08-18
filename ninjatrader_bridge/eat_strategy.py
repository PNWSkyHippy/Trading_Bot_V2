"""Early Acceleration Trade (EAT) paper-trading state machine.

EAT builds a session box from the first 5-minute bar, optionally falls back to
the first 15-minute bar when the 5-minute range is too small, then trades
1-minute candle closes into the configured buffer zones. It is intentionally
paper-first: partial TP plus runner behavior needs more broker-side plumbing
than EMT's simple all-in/all-out bracket.
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
from typing import Deque, Iterable, List, Optional
from zoneinfo import ZoneInfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@dataclass(frozen=True)
class EATEvent:
    time: str
    level: int
    kind: str
    direction: str
    price: float
    message: str


@dataclass
class EATTrade:
    trade_id: str
    symbol: str
    direction: str
    quantity: int
    entry_time: str
    entry_price: float
    stop_price: float
    tp1_price: float
    entry_bar_time: str
    remaining_quantity: int
    tp1_quantity: int
    tp1_done: bool = False
    runner_stop: Optional[float] = None
    best_price: Optional[float] = None
    status: str = "open"
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_pnl: float = 0.0
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
    values = {
        name: _finite_number(bar.get(name))
        for name in ("open", "high", "low", "close", "volume")
    }
    if min(values[name] for name in ("open", "high", "low", "close")) <= 0:
        raise ValueError("OHLC prices must be positive")
    if values["low"] > min(values["open"], values["close"]):
        raise ValueError("low is above the candle body")
    if values["high"] < max(values["open"], values["close"]):
        raise ValueError("high is below the candle body")
    return {
        "dt": _parse_timestamp(bar.get("time"), source_timezone),
        "time": str(bar.get("time")),
        **values,
    }


def _clock(value: object) -> dt_time:
    hour, minute = [int(part) for part in str(value).split(":", 1)]
    return dt_time(hour, minute)


_PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


class EATStrategyEngine:
    """Stateful EAT evaluator for one futures root symbol."""

    def __init__(self, settings: dict, contract: dict, root_dir: str,
                 db_mirror=None):
        self.settings = dict(settings or {})
        self.contract = dict(contract or {})
        self.root_dir = root_dir
        self.enabled = bool(self.settings.get("enabled", False))
        self.paper_only = bool(self.settings.get("paper_only", True))
        if not self.paper_only:
            raise ValueError("EAT live broker routing is not implemented yet")

        self.symbol = str(self.settings.get("symbol", "MNQ")).upper()
        self.broker_symbol = str(
            self.settings.get("broker_symbol")
            or self.settings.get("instrument")
            or self.symbol
        )
        self.source_timezone = str(
            self.settings.get("source_timezone", "America/Los_Angeles")
        )
        # EAT session definitions are Pacific wall-clock times. Offset-aware
        # source bars are converted before any session or box comparison.
        self.market_tz = _PACIFIC_TZ
        self.db_timezone = _PACIFIC_TZ
        self.tick_size = _finite_number(self.contract.get("tick_size", 0.25))
        self.tick_value = _finite_number(self.contract.get("tick_value", 0.5))
        self.point_value = self.tick_value / self.tick_size
        self.quantity = int(self.settings.get("contracts", 1))
        self.primary_box_minutes = int(self.settings.get("primary_box_minutes", 5))
        self.fallback_box_minutes = int(self.settings.get("fallback_box_minutes", 15))
        self.min_box_ticks = int(self.settings.get("min_box_ticks", 100))
        self.max_box_ticks = int(self.settings.get("max_box_ticks", 250))
        self.buffer_ticks = int(self.settings.get("buffer_ticks", 30))
        self.tp1_ticks = int(self.settings.get("tp1_ticks", 100))
        self.runner_trail_ticks = int(self.settings.get("runner_trail_ticks", 30))
        self.trade_window_minutes = int(self.settings.get("trade_window_minutes", 60))
        self.max_trades_per_session = int(self.settings.get("max_trades_per_session", 12))
        self.wick_stop_lookback_minutes = int(
            self.settings.get("wick_stop_lookback_minutes", 20)
        )
        self.max_stop_ticks = int(self.settings.get("max_stop_ticks", 0))
        self.stop_ticks_override = int(self.settings.get("stop_ticks_override", 0))
        self.enable_longs = bool(self.settings.get("enable_longs", True))
        self.enable_shorts = bool(self.settings.get("enable_shorts", True))
        self.allow_reentry = bool(self.settings.get("allow_reentry", True))
        self.control_state_key = str(self.settings.get("control_state_key") or "").strip()
        self.mirror_to_bot_db = bool(self.settings.get("mirror_to_bot_db", False))
        self.db_mirror = db_mirror
        self.ledger_path = os.path.join(
            root_dir,
            str(self.settings.get("ledger_path") or "eat_trades.jsonl"),
        )
        self.sessions = self._load_sessions(self.settings.get("sessions"))

        if self.quantity < 1:
            raise ValueError("EAT contracts must be >= 1")
        if (
            self.primary_box_minutes < 1
            or self.fallback_box_minutes < self.primary_box_minutes
        ):
            raise ValueError(
                "EAT fallback box minutes must be at least the primary box minutes"
            )
        if self.min_box_ticks < 1 or self.max_box_ticks < self.min_box_ticks:
            raise ValueError("EAT box tick range is invalid")
        if min(self.buffer_ticks, self.tp1_ticks, self.runner_trail_ticks) < 1:
            raise ValueError("EAT tick distances must be positive")
        if self.max_stop_ticks < 0:
            raise ValueError("EAT max_stop_ticks must be >= 0")
        if self.stop_ticks_override < 0:
            raise ValueError("EAT stop_ticks_override must be >= 0")
        if not (self.enable_longs or self.enable_shorts):
            raise ValueError("EAT needs at least one of enable_longs/enable_shorts on")

        self.lock = threading.RLock()
        self.minute_bars: Deque[dict] = deque(maxlen=3000)
        self.events: Deque[EATEvent] = deque(maxlen=100)
        self.closed_trades: Deque[EATTrade] = deque(maxlen=100)
        self.active_trade: Optional[EATTrade] = None
        self._event_counter = 0
        self.last_execution_error: Optional[str] = None
        self.last_live_price: Optional[float] = None
        if self.mirror_to_bot_db and self.db_mirror is None:
            try:
                from data.database import db as bot_db
                self.db_mirror = bot_db
            except Exception as exc:
                self.last_execution_error = (
                    f"DB mirror unavailable: {type(exc).__name__}: {exc}"
                )
        self._reset_session(None, None)

    def _load_sessions(self, value: object) -> List[dict]:
        raw = value if isinstance(value, list) else []
        if not raw:
            raw = [
                {"name": "ny", "start": "05:00"},
                {"name": "tokyo", "start": "14:30"},
                {"name": "london", "standard_start": "22:30", "dst_start": "23:30"},
            ]
        sessions = []
        for item in raw:
            if not isinstance(item, dict) or item.get("enabled", True) is False:
                continue
            sessions.append(dict(item))
        if not sessions:
            raise ValueError("EAT needs at least one enabled session")
        return sessions

    def _session_start_time(self, session: dict, day) -> dt_time:
        if session.get("dst_start") or session.get("standard_start"):
            noon = datetime.combine(day, dt_time(12, 0), tzinfo=self.market_tz)
            is_dst = bool(noon.dst() and noon.dst().total_seconds())
            key = "dst_start" if is_dst else "standard_start"
            return _clock(session.get(key) or session.get("start"))
        return _clock(session.get("start"))

    def _session_candidates(self, stamp: datetime) -> List[dict]:
        stamp_pacific = stamp.astimezone(self.market_tz)
        candidates = []
        for offset in (-1, 0, 1):
            day = (stamp_pacific + timedelta(days=offset)).date()
            for session in self.sessions:
                start = datetime.combine(
                    day, self._session_start_time(session, day), tzinfo=self.market_tz
                )
                final_box_end = start + timedelta(minutes=self.fallback_box_minutes)
                trade_end = final_box_end + timedelta(minutes=self.trade_window_minutes)
                if start <= stamp_pacific <= trade_end:
                    candidates.append({
                        "name": str(session.get("name") or "eat"),
                        "start": start,
                        "final_box_end": final_box_end,
                        "trade_end": trade_end,
                    })
        candidates.sort(key=lambda item: item["start"], reverse=True)
        return candidates

    def _session_key(self, candidate: dict) -> str:
        return f"{candidate['name']}:{candidate['start'].isoformat()}"

    def _reset_session(self, key: Optional[str], candidate: Optional[dict]) -> None:
        self.session_key = key
        self.session_name = None if candidate is None else candidate["name"]
        self.session_start = None if candidate is None else candidate["start"]
        self.box_minutes: Optional[int] = None
        self.box_start = self.session_start
        self.box_end = None
        self.trade_end = None
        self.phase = "WAIT_SESSION" if candidate is None else "BUILDING_BOX"
        self.inner_high: Optional[float] = None
        self.inner_low: Optional[float] = None
        self.outer_high: Optional[float] = None
        self.outer_low: Optional[float] = None
        self.box_range_ticks: Optional[int] = None
        self.skip_reason: Optional[str] = None
        self.trades_this_session = 0
        self.last_zone: Optional[str] = None

    def _in_market_blackout(self, stamp: datetime) -> bool:
        stamp_pt = stamp.astimezone(_PACIFIC_TZ)
        weekday = stamp_pt.weekday()
        t = stamp_pt.time()
        if weekday == 5:
            return True
        if weekday == 6:
            return t < dt_time(15, 0)
        if weekday == 4:
            return t >= dt_time(13, 0)
        return dt_time(13, 0) <= t < dt_time(15, 0)

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

    def _emit(self, stamp: datetime, level: int, kind: str, direction: str,
              price: float, message: str) -> None:
        self.events.append(EATEvent(
            time=stamp.astimezone(timezone.utc).isoformat(),
            level=int(level),
            kind=kind,
            direction=direction,
            price=round(float(price or 0.0), 8),
            message=message,
        ))

    def _status_message(self) -> str:
        if not self.enabled:
            return "EAT disabled"
        if self.skip_reason:
            return self.skip_reason
        if self.phase == "WAIT_SESSION":
            return "Waiting for next EAT session"
        bits = [self.session_name or "session", self.phase]
        if self.box_range_ticks is not None:
            bits.append(f"box {self.box_range_ticks} ticks")
        if self.box_end:
            bits.append(f"trade until {self.trade_end.strftime('%H:%M %Z')}")
        return " | ".join(bits)

    def _upsert_minute_bar(self, bar: dict) -> None:
        rows = {item["time"]: item for item in self.minute_bars}
        rows[bar["time"]] = bar
        ordered = sorted(rows.values(), key=lambda item: item["dt"])[-self.minute_bars.maxlen:]
        self.minute_bars.clear()
        self.minute_bars.extend(ordered)

    def _bars_between(self, start: datetime, end: datetime) -> List[dict]:
        return [
            bar for bar in self.minute_bars
            if start <= bar["dt"].astimezone(self.market_tz) < end
        ]

    def _try_build_box(self, stamp_pacific: datetime) -> None:
        if self.session_start is None or self.phase != "BUILDING_BOX":
            return
        primary_end = self.session_start + timedelta(minutes=self.primary_box_minutes)
        fallback_end = self.session_start + timedelta(minutes=self.fallback_box_minutes)
        if stamp_pacific >= primary_end and self.box_minutes is None:
            bars = self._bars_between(self.session_start, primary_end)
            if len(bars) >= self.primary_box_minutes:
                ticks = self._range_ticks(bars)
                if ticks > self.max_box_ticks:
                    self._skip_session(
                        bars[-1]["dt"],
                        f"Primary box too large ({ticks} ticks > {self.max_box_ticks})",
                    )
                    return
                if ticks >= self.min_box_ticks:
                    self._set_box(bars, self.primary_box_minutes, ticks)
                    return
                self.box_minutes = self.fallback_box_minutes
                self._emit(
                    bars[-1]["dt"], 1, "FALLBACK_15M", "", bars[-1]["close"],
                    f"5-minute box too small ({ticks} ticks); waiting for 15-minute box",
                )
        if (
            stamp_pacific >= fallback_end
            and self.box_minutes == self.fallback_box_minutes
        ):
            bars = self._bars_between(self.session_start, fallback_end)
            if len(bars) >= self.fallback_box_minutes:
                ticks = self._range_ticks(bars)
                if ticks < self.min_box_ticks:
                    self._skip_session(
                        bars[-1]["dt"],
                        f"Fallback box too small ({ticks} ticks < {self.min_box_ticks})",
                    )
                    return
                if ticks > self.max_box_ticks:
                    self._skip_session(
                        bars[-1]["dt"],
                        f"Fallback box too large ({ticks} ticks > {self.max_box_ticks})",
                    )
                    return
                self._set_box(bars, self.fallback_box_minutes, ticks)

    def _range_ticks(self, bars: Iterable[dict]) -> int:
        bars = list(bars)
        high = max(float(bar["high"]) for bar in bars)
        low = min(float(bar["low"]) for bar in bars)
        return int(round((high - low) / self.tick_size))

    def _set_box(self, bars: List[dict], minutes: int, ticks: int) -> None:
        self.box_minutes = minutes
        self.box_end = self.session_start + timedelta(minutes=minutes)
        self.trade_end = self.box_end + timedelta(minutes=self.trade_window_minutes)
        self.inner_high = max(float(bar["high"]) for bar in bars)
        self.inner_low = min(float(bar["low"]) for bar in bars)
        self.outer_high = self.inner_high + self.buffer_ticks * self.tick_size
        self.outer_low = self.inner_low - self.buffer_ticks * self.tick_size
        self.box_range_ticks = ticks
        self.phase = "WAIT_BUFFER_CLOSE"
        self._emit(
            bars[-1]["dt"], 2, "BOX_READY", "", bars[-1]["close"],
            f"EAT box ready from {minutes}m candle: {self.inner_low:.2f}-"
            f"{self.inner_high:.2f} ({ticks} ticks)",
        )

    def _skip_session(self, stamp: datetime, reason: str) -> None:
        self.skip_reason = reason
        self.phase = "SESSION_DONE"
        self._emit(stamp, 1, "SESSION_SKIPPED", "", 0.0, reason)

    def _zone_for_close(self, close: float) -> Optional[str]:
        if None in (self.inner_high, self.inner_low, self.outer_high, self.outer_low):
            return None
        if self.inner_high <= close <= self.outer_high:
            return "top"
        if self.outer_low <= close <= self.inner_low:
            return "bottom"
        return None

    def _check_entry(self, bar: dict, stamp_pacific: datetime) -> None:
        if self.phase != "WAIT_BUFFER_CLOSE" or self.active_trade is not None:
            return
        if self.trade_end is None or stamp_pacific > self.trade_end:
            self.phase = "SESSION_DONE"
            self._emit(
                bar["dt"], 1, "SESSION_DONE", "", bar["close"],
                "EAT trade window ended",
            )
            return
        if self.trades_this_session >= self.max_trades_per_session:
            self.phase = "SESSION_DONE"
            return
        zone = self._zone_for_close(bar["close"])
        if zone is None:
            self.last_zone = None
            return
        if self.last_zone == zone and self.allow_reentry:
            return
        direction = "long" if zone == "top" else "short"
        if direction == "long" and not self.enable_longs:
            self.last_zone = zone
            return
        if direction == "short" and not self.enable_shorts:
            self.last_zone = zone
            return
        self._open_trade(direction, float(bar["close"]), bar)
        self.last_zone = zone

    def _wick_stop(self, direction: str, fallback_stop: float, stamp: datetime) -> float:
        if self.inner_high is None or self.inner_low is None:
            return fallback_stop
        start = stamp - timedelta(minutes=self.wick_stop_lookback_minutes)
        recent = [
            bar for bar in self.minute_bars
            if start <= bar["dt"].astimezone(self.market_tz) < stamp
        ]
        if direction == "long":
            candidates = [
                bar["low"] for bar in recent
                if self.outer_low is not None
                and self.outer_low <= bar["low"] < self.inner_low
                and bar["close"] >= self.inner_low
            ]
            return round(min(candidates), 8) if candidates else fallback_stop
        candidates = [
            bar["high"] for bar in recent
            if self.outer_high is not None
            and self.inner_high < bar["high"] <= self.outer_high
            and bar["close"] <= self.inner_high
        ]
        return round(max(candidates), 8) if candidates else fallback_stop

    def _open_trade(self, direction: str, price: float, bar: dict) -> None:
        self._event_counter += 1
        if self.stop_ticks_override > 0:
            override_distance = self.stop_ticks_override * self.tick_size
            if direction == "long":
                stop = price - override_distance
            else:
                stop = price + override_distance
        elif direction == "long":
            stop = self._wick_stop(
                direction, float(self.inner_low), bar["dt"].astimezone(self.market_tz)
            )
        else:
            stop = self._wick_stop(
                direction, float(self.inner_high), bar["dt"].astimezone(self.market_tz)
            )
        if direction == "long":
            tp1 = float(self.inner_high) + self.tp1_ticks * self.tick_size
        else:
            tp1 = float(self.inner_low) - self.tp1_ticks * self.tick_size
        if self.stop_ticks_override <= 0 and self.max_stop_ticks > 0:
            max_distance = self.max_stop_ticks * self.tick_size
            if direction == "long":
                stop = max(stop, price - max_distance)
            else:
                stop = min(stop, price + max_distance)
        tp1_qty = int(math.ceil(self.quantity / 2.0))
        trade_id = (
            f"EAT-PAPER-"
            f"{bar['dt'].astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
            f"-{self._event_counter}"
        )
        trade = EATTrade(
            trade_id=trade_id,
            symbol=self.symbol,
            direction=direction,
            quantity=self.quantity,
            entry_time=bar["dt"].astimezone(timezone.utc).isoformat(),
            entry_price=round(price, 8),
            stop_price=round(stop, 8),
            tp1_price=round(tp1, 8),
            entry_bar_time=bar["time"],
            remaining_quantity=self.quantity,
            tp1_quantity=tp1_qty,
            best_price=round(price, 8),
        )
        self.active_trade = trade
        self.trades_this_session += 1
        self.phase = "IN_TRADE"
        self._write_ledger("OPEN", trade)
        self._mirror_open_trade(trade)
        self._emit(
            bar["dt"], 3, "PAPER_ENTRY", direction, price,
            f"EAT PAPER {direction.upper()} {self.quantity} {self.broker_symbol} "
            f"| stop {stop:.2f} | TP1 {tp1:.2f} | runner trail {self.runner_trail_ticks} ticks",
        )

    def _points_won(self, trade: EATTrade, price: float) -> float:
        return price - trade.entry_price if trade.direction == "long" else trade.entry_price - price

    def _realize(self, trade: EATTrade, quantity: int, price: float) -> float:
        pnl = self._points_won(trade, price) * self.point_value * quantity
        trade.realized_pnl = round(trade.realized_pnl + pnl, 2)
        trade.remaining_quantity -= quantity
        return round(pnl, 2)

    def _check_exit(self, bar: dict) -> None:
        trade = self.active_trade
        if trade is None:
            return
        same_entry_bar = bar["time"] == trade.entry_bar_time
        observed_low = bar["close"] if same_entry_bar else bar["low"]
        observed_high = bar["close"] if same_entry_bar else bar["high"]

        if trade.direction == "long":
            original_stop_hit = observed_low <= trade.stop_price
            tp1_hit = observed_high >= trade.tp1_price
        else:
            original_stop_hit = observed_high >= trade.stop_price
            tp1_hit = observed_low <= trade.tp1_price

        if not trade.tp1_done and original_stop_hit:
            self._close_trade(trade.stop_price, bar["dt"], "stop_loss")
            return

        if not trade.tp1_done and tp1_hit:
            qty = min(trade.tp1_quantity, trade.remaining_quantity)
            pnl = self._realize(trade, qty, trade.tp1_price)
            trade.tp1_done = True
            if trade.remaining_quantity <= 0:
                self._close_trade(trade.tp1_price, bar["dt"], "tp1_take_profit")
                return
            if trade.direction == "long":
                trade.best_price = max(float(trade.best_price or trade.entry_price), observed_high)
                trade.runner_stop = round(
                    float(trade.best_price) - self.runner_trail_ticks * self.tick_size, 8
                )
            else:
                trade.best_price = min(float(trade.best_price or trade.entry_price), observed_low)
                trade.runner_stop = round(
                    float(trade.best_price) + self.runner_trail_ticks * self.tick_size, 8
                )
            self._write_ledger("PARTIAL", trade)
            self._emit(
                bar["dt"], 2, "PAPER_TP1", trade.direction, trade.tp1_price,
                f"EAT TP1 filled {qty}/{trade.quantity} | partial P&L ${pnl:.2f} "
                f"| runner stop {trade.runner_stop:.2f}",
            )

        if trade.tp1_done and trade.remaining_quantity > 0:
            if trade.direction == "long":
                trade.best_price = max(float(trade.best_price or trade.entry_price), observed_high)
                trade.runner_stop = max(
                    float(trade.runner_stop or trade.stop_price),
                    float(trade.best_price) - self.runner_trail_ticks * self.tick_size,
                )
                if observed_low <= float(trade.runner_stop):
                    self._close_trade(float(trade.runner_stop), bar["dt"], "runner_trailing_stop")
            else:
                trade.best_price = min(float(trade.best_price or trade.entry_price), observed_low)
                trade.runner_stop = min(
                    float(trade.runner_stop or trade.stop_price),
                    float(trade.best_price) + self.runner_trail_ticks * self.tick_size,
                )
                if observed_high >= float(trade.runner_stop):
                    self._close_trade(float(trade.runner_stop), bar["dt"], "runner_trailing_stop")

    def _close_trade(self, price: float, stamp: datetime, reason: str) -> None:
        trade = self.active_trade
        if trade is None:
            return
        if trade.remaining_quantity > 0:
            self._realize(trade, trade.remaining_quantity, price)
        trade.status = "closed"
        trade.exit_time = stamp.astimezone(timezone.utc).isoformat()
        trade.exit_price = round(price, 8)
        trade.exit_reason = reason
        self.closed_trades.append(trade)
        self._write_ledger("CLOSE", trade)
        self._mirror_close_trade(trade)
        self._emit(
            stamp, 0, "PAPER_EXIT", trade.direction, price,
            f"EAT PAPER EXIT {reason} | P&L ${trade.realized_pnl:.2f}",
        )
        self.active_trade = None
        if self.allow_reentry and self.trade_end and stamp.astimezone(self.market_tz) < self.trade_end:
            self.phase = "WAIT_BUFFER_CLOSE"
        else:
            self.phase = "SESSION_DONE"

    def manual_close(self, trade_id: str, price: Optional[float] = None) -> dict:
        """Close one exact paper trade through the owning strategy engine."""
        with self.lock:
            if not self.paper_only:
                raise ValueError("manual paper close cannot operate on live EAT")
            trade = self.active_trade
            if trade is None or str(trade.trade_id) != str(trade_id):
                active_id = None if trade is None else trade.trade_id
                raise LookupError(
                    f"EAT {self.symbol} trade {trade_id} is not active"
                    + ("" if active_id is None else f"; active trade is {active_id}")
                )
            exit_price = _finite_number(
                self.last_live_price if price is None else price
            )
            if exit_price <= 0:
                raise ValueError("EAT manual close needs a positive current price")
            self._close_trade(
                exit_price, datetime.now(timezone.utc), "manual_close"
            )
            return asdict(trade)

    def on_minute_bar(self, raw_bar: dict, historical: bool = False) -> List[EATEvent]:
        self._refresh_runtime_enabled()
        if not self.enabled and self.active_trade is None:
            return []
        bar = _clean_bar(raw_bar, self.source_timezone)
        with self.lock:
            before = len(self.events)
            self._upsert_minute_bar(bar)
            stamp_pacific = bar["dt"].astimezone(self.market_tz)
            self.last_live_price = bar["close"]
            if historical:
                return []
            candidate = next(iter(self._session_candidates(bar["dt"])), None)
            key = None if candidate is None else self._session_key(candidate)
            if key != self.session_key and self.active_trade is None:
                self._reset_session(key, candidate)
                if candidate is not None:
                    self._emit(
                        bar["dt"], 1, "SESSION_START", "", bar["close"],
                        f"EAT {candidate['name']} session started; building box",
                    )
            if candidate is None:
                if self.active_trade is not None:
                    self._check_exit(bar)
                return list(self.events)[before:]
            if self._in_market_blackout(bar["dt"]):
                self.phase = "MARKET_CLOSED"
                if self.active_trade is not None:
                    self._check_exit(bar)
                return list(self.events)[before:]
            if self.active_trade is not None:
                self._check_exit(bar)
            else:
                self._try_build_box(stamp_pacific)
                self._check_entry(bar, stamp_pacific)
            return list(self.events)[before:]

    def chart_overlay(self) -> dict:
        with self.lock:
            return {
                "status_message": self._status_message(),
                "phase": self.phase,
                "symbol": self.symbol,
                "session_name": self.session_name,
                "inner_high": self.inner_high,
                "inner_low": self.inner_low,
                "outer_high": self.outer_high,
                "outer_low": self.outer_low,
                "box_start": None if self.box_start is None else int(self.box_start.timestamp()),
                "box_end": None if self.box_end is None else int(self.box_end.timestamp()),
                "trade_end": None if self.trade_end is None else int(self.trade_end.timestamp()),
                "last_live_price": self.last_live_price,
                "active_trade": None if self.active_trade is None else asdict(self.active_trade),
                "events": [asdict(event) for event in list(self.events)[-30:]],
            }

    def _write_ledger(self, action: str, trade: EATTrade) -> None:
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

    def _db_position_value(self, trade: EATTrade) -> float:
        points = abs(trade.entry_price - trade.stop_price)
        return round(points * self.point_value * trade.quantity, 2)

    def _db_payload(self, trade: EATTrade) -> dict:
        indicators = {
            "strategy_name": "eat",
            "signal_source": "eat",
            "root_symbol": self.symbol,
            "broker_symbol": self.broker_symbol,
            "execution_mode": trade.execution_mode,
            "box_range_ticks": self.box_range_ticks,
            "inner_high": self.inner_high,
            "inner_low": self.inner_low,
            "outer_high": self.outer_high,
            "outer_low": self.outer_low,
            "tp1_ticks": self.tp1_ticks,
            "runner_trail_ticks": self.runner_trail_ticks,
            "tick_size": self.tick_size,
            "tick_value": self.tick_value,
            "point_value": self.point_value,
        }
        return {
            "trade_id": trade.trade_id,
            "symbol": self.broker_symbol,
            "asset_class": "future",
            "direction": trade.direction,
            "entry_time": self._db_time(trade.entry_time),
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "position_value": self._db_position_value(trade),
            "stop_loss": trade.stop_price,
            "take_profit": trade.tp1_price,
            "signal_score": 1.0,
            "indicators": indicators,
            "broker": "paper_eat",
            "broker_order_id": None,
            "strategy_name": "eat",
            "entry_timeframe": "1Min",
            "event_id": trade.trade_id,
        }

    def _mirror_open_trade(self, trade: EATTrade) -> None:
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

    def _mirror_close_trade(self, trade: EATTrade) -> None:
        if not self.mirror_to_bot_db or self.db_mirror is None:
            return
        try:
            position_value = self._db_position_value(trade)
            pnl_pct = (
                trade.realized_pnl / position_value * 100.0
                if position_value else 0.0
            )
            self.db_mirror.close_trade(
                trade.trade_id,
                float(trade.exit_price or trade.entry_price),
                str(trade.exit_reason or "eat_closed"),
                round(float(trade.realized_pnl), 2),
                round(pnl_pct, 4),
            )
            self.db_mirror.record_consecutive_result(trade.realized_pnl > 0)
        except Exception as exc:
            self.last_execution_error = (
                f"DB mirror close failed: {type(exc).__name__}: {exc}"
            )

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "enabled": self.enabled,
                "paper_only": self.paper_only,
                "execution_mode": "paper",
                "symbol": self.symbol,
                "broker_symbol": self.broker_symbol,
                "contracts": self.quantity,
                "phase": self.phase,
                "session_key": self.session_key,
                "session_name": self.session_name,
                "inner_high": self.inner_high,
                "inner_low": self.inner_low,
                "outer_high": self.outer_high,
                "outer_low": self.outer_low,
                "box_range_ticks": self.box_range_ticks,
                "box_minutes": self.box_minutes,
                "trades_this_session": self.trades_this_session,
                "active_trade": None if self.active_trade is None else asdict(self.active_trade),
                "last_closed_trade": (
                    None if not self.closed_trades else asdict(self.closed_trades[-1])
                ),
                "last_execution_error": self.last_execution_error,
                "status_message": self._status_message(),
                "last_live_price": self.last_live_price,
                "events": [asdict(event) for event in list(self.events)[-30:]],
            }
