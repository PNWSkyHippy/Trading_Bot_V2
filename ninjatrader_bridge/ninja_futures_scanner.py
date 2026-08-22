"""Read-only localhost receiver and futures opportunity dashboard."""

import argparse
import json
import os
import statistics
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

try:
    from .eat_strategy import EATStrategyEngine
    from .emt_strategy import EMTStrategyEngine
    from .futures_signal_engine import assess_confluence
    from .tradovate_executor import TradovateExecutor
except ImportError:  # direct script execution
    from eat_strategy import EATStrategyEngine
    from emt_strategy import EMTStrategyEngine
    from futures_signal_engine import assess_confluence
    from tradovate_executor import TradovateExecutor


ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        config = json.load(handle)
    config["shared_secret"] = os.getenv(
        "NINJA_BRIDGE_SECRET", str(config.get("shared_secret", ""))
    )
    config["listen_host"] = os.getenv(
        "NINJA_BRIDGE_LISTEN_HOST", str(config.get("listen_host", "127.0.0.1"))
    )
    if not config["shared_secret"] or config["shared_secret"] == "SET_IN_ENV":
        raise ValueError("NINJA_BRIDGE_SECRET must be set")
    return config


class MarketState:
    def __init__(self, config):
        self.config = config
        self.bars = defaultdict(lambda: deque(maxlen=2000))
        self.last_received = {}
        self.last_heartbeat = None
        self.heartbeat_details = {}
        self.lock = threading.Lock()
        # The console and GUI read the same calculations. Keep one short-lived
        # shared result instead of making both recalculate every symbol at once.
        self.assessment_lock = threading.Lock()
        self.assessment_rows = None
        self.assessment_created_at = 0.0
        self.last_emt_status_log = 0.0
        self.last_emt_watch_log = 0.0
        self.last_eat_status_log = 0.0
        self.engine_lock = threading.RLock()
        self.strategy_runtime_path = os.path.join(
            PROJECT_ROOT, "data", "ninja_strategy_instances.json"
        )
        self.strategy_runtime = {"emt": {}, "eat": {}}
        self.emt_base_settings = dict(config.get("emt", {}))
        self.eat_base_settings = dict(config.get("eat", {}))
        self.emt_default_symbol = str(
            self.emt_base_settings.get("symbol", "ES")
        ).upper()
        self.eat_default_symbol = str(
            self.eat_base_settings.get("symbol", "MNQ")
        ).upper()
        self.emt_execution_mode = os.getenv(
            "EMT_EXECUTION_MODE", "paper"
        ).strip().lower()
        if self.emt_execution_mode not in ("paper", "live"):
            raise ValueError("EMT_EXECUTION_MODE must be paper or live")
        self.eat_execution_mode = os.getenv(
            "EAT_EXECUTION_MODE", "paper"
        ).strip().lower()
        if self.eat_execution_mode != "paper":
            raise ValueError(
                "EAT_EXECUTION_MODE must be paper; live routing is not implemented yet"
            )
        self.emt_engines = {}
        self.eat_engines = {}
        self._load_strategy_runtime()
        self._load_initial_engines()

    def _load_strategy_runtime(self):
        try:
            with open(self.strategy_runtime_path, encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("runtime strategy settings must be an object")
            for strategy in ("emt", "eat"):
                values = payload.get(strategy, {})
                if isinstance(values, dict):
                    self.strategy_runtime[strategy] = {
                        str(symbol).upper(): dict(settings)
                        for symbol, settings in values.items()
                        if isinstance(settings, dict)
                    }
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            print(
                f"STRATEGY CONFIG WARNING · ignoring runtime settings · "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    def _persist_strategy_runtime(self):
        directory = os.path.dirname(self.strategy_runtime_path)
        os.makedirs(directory, exist_ok=True)
        temporary = self.strategy_runtime_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self.strategy_runtime, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.strategy_runtime_path)

    def _settings_for(self, strategy, symbol, overrides=None):
        symbol = self.root_symbol(symbol)
        contract = self.config.get("contracts", {}).get(symbol)
        if not isinstance(contract, dict):
            raise ValueError(f"{symbol} is not an enabled Ninja futures contract")
        base = dict(
            self.emt_base_settings if strategy == "emt"
            else self.eat_base_settings
        )
        default_symbol = (
            self.emt_default_symbol if strategy == "emt"
            else self.eat_default_symbol
        )
        values = dict(base)
        values.update(self.strategy_runtime.get(strategy, {}).get(symbol, {}))
        values.update(dict(overrides or {}))
        values["symbol"] = symbol
        values["paper_only"] = (
            self.emt_execution_mode != "live" if strategy == "emt" else True
        )
        if symbol != default_symbol:
            if (
                strategy == "emt"
                and self.emt_execution_mode == "live"
                and not (contract.get("broker_symbol") or contract.get("instrument"))
            ):
                raise ValueError(
                    f"live EMT {symbol} requires broker_symbol or instrument "
                    "in ninja_futures_config.json"
                )
            values["instrument"] = str(
                contract.get("instrument")
                or contract.get("broker_symbol")
                or symbol
            )
            values["broker_symbol"] = str(
                contract.get("broker_symbol")
                or contract.get("instrument")
                or symbol
            )
            values["control_state_key"] = (
                f"scanner_{strategy}_{symbol.lower()}_enabled"
            )
            values["ledger_path"] = f"{strategy}_trades_{symbol.lower()}.jsonl"
        return values

    def _new_engine(self, strategy, symbol, overrides=None):
        settings = self._settings_for(strategy, symbol, overrides)
        contract = self.config.get("contracts", {}).get(symbol, {})
        if strategy == "eat":
            return EATStrategyEngine(settings, contract, ROOT)
        executor = None
        if self.emt_execution_mode == "live":
            executor = TradovateExecutor.from_env(settings)
            executor.verify_account()
        return EMTStrategyEngine(settings, contract, ROOT, executor=executor)

    @staticmethod
    def _engine_replay_bar(bar, symbol):
        return {
            "symbol": symbol,
            "time": str(bar.get("time")),
            "open": float(bar.get("open")),
            "high": float(bar.get("high")),
            "low": float(bar.get("low")),
            "close": float(bar.get("close")),
            "volume": float(bar.get("volume", 0) or 0),
        }

    def _replace_engine(self, strategy, symbol, overrides=None):
        symbol = self.root_symbol(symbol)
        engines = self.emt_engines if strategy == "emt" else self.eat_engines
        old = engines.get(symbol)
        if old is not None and old.active_trade is not None:
            raise ValueError(
                f"cannot reconfigure {strategy.upper()} {symbol} while a trade is open"
            )
        settings = self._settings_for(strategy, symbol, overrides)
        if old is not None and old.settings == settings:
            return old
        engine = self._new_engine(strategy, symbol, overrides)
        with self.lock:
            minute_bars = list(self.bars.get(symbol, ()))
        for bar in minute_bars:
            engine.on_minute_bar(
                self._engine_replay_bar(bar, symbol), historical=True
            )
        if strategy == "emt" and old is not None:
            for bar in list(old.tick_bars):
                replay = self._engine_replay_bar(bar, symbol)
                replay.update({
                    "bar_type": "tick",
                    "bar_value": int(settings.get("tick_bar_value", 610)),
                })
                engine.on_tick_bar(replay, complete=True, historical=True)
        engines[symbol] = engine
        if strategy == "emt" and symbol == self.emt_default_symbol:
            self.emt = engine
        if strategy == "eat" and symbol == self.eat_default_symbol:
            self.eat = engine
        return engine

    def _load_initial_engines(self):
        emt_symbols = {
            self.emt_default_symbol,
            *self.strategy_runtime.get("emt", {}).keys(),
        }
        eat_symbols = {
            self.eat_default_symbol,
            *self.strategy_runtime.get("eat", {}).keys(),
        }
        with self.engine_lock:
            for symbol in sorted(emt_symbols):
                try:
                    self._replace_engine("emt", symbol)
                except ValueError as exc:
                    print(
                        f"STRATEGY CONFIG WARNING · skipping EMT {symbol} · {exc}",
                        flush=True,
                    )
            for symbol in sorted(eat_symbols):
                try:
                    self._replace_engine("eat", symbol)
                except ValueError as exc:
                    print(
                        f"STRATEGY CONFIG WARNING · skipping EAT {symbol} · {exc}",
                        flush=True,
                    )

    @staticmethod
    def _clean_runtime_settings(strategy, settings):
        if not isinstance(settings, dict):
            raise ValueError("settings must be an object")
        allowed = {
            "emt": {
                "enabled", "contracts", "opening_range_start",
                "opening_range_minutes", "trade_window_minutes",
                "stop_points", "target_points", "max_trades_per_session",
            },
            "eat": {
                "enabled", "contracts", "primary_box_minutes",
                "fallback_box_minutes", "min_box_ticks", "max_box_ticks",
                "buffer_ticks", "tp1_ticks", "runner_trail_ticks",
                "wick_stop_lookback_minutes", "trade_window_minutes",
                "max_trades_per_session", "allow_reentry", "sessions",
                "max_stop_ticks", "enable_longs", "enable_shorts",
                "stop_ticks_override",
            },
        }[strategy]
        unknown = sorted(set(settings) - allowed)
        if unknown:
            raise ValueError(
                f"unsupported {strategy.upper()} settings: {', '.join(unknown)}"
            )
        clean = {key: settings[key] for key in allowed if key in settings}
        for key in ("enabled", "allow_reentry", "enable_longs", "enable_shorts"):
            if key in clean and not isinstance(clean[key], bool):
                raise ValueError(f"{key} must be true or false")
        for key in (
            "contracts", "opening_range_minutes", "trade_window_minutes",
            "max_trades_per_session", "primary_box_minutes",
            "fallback_box_minutes", "min_box_ticks", "max_box_ticks",
            "buffer_ticks", "tp1_ticks", "runner_trail_ticks",
            "wick_stop_lookback_minutes",
        ):
            if key in clean:
                clean[key] = int(clean[key])
                if clean[key] < 1:
                    raise ValueError(f"{key} must be at least 1")
        if "max_stop_ticks" in clean:
            clean["max_stop_ticks"] = int(clean["max_stop_ticks"])
            if clean["max_stop_ticks"] < 0:
                raise ValueError("max_stop_ticks must be >= 0")
        if "stop_ticks_override" in clean:
            clean["stop_ticks_override"] = int(clean["stop_ticks_override"])
            if clean["stop_ticks_override"] < 0:
                raise ValueError("stop_ticks_override must be >= 0")
        for key in ("stop_points", "target_points"):
            if key in clean:
                clean[key] = float(clean[key])
                if clean[key] <= 0:
                    raise ValueError(f"{key} must be positive")
        if "opening_range_start" in clean:
            datetime.strptime(str(clean["opening_range_start"]), "%H:%M")
            clean["opening_range_start"] = str(clean["opening_range_start"])
        if "sessions" in clean:
            sessions = clean["sessions"]
            if not isinstance(sessions, list) or not sessions:
                raise ValueError("sessions must be a non-empty list")
            validated = []
            for item in sessions:
                if not isinstance(item, dict):
                    raise ValueError("each session must be an object")
                unknown_session = set(item) - {
                    "name", "start", "standard_start", "dst_start", "enabled",
                }
                if unknown_session:
                    raise ValueError(
                        "unsupported session settings: "
                        + ", ".join(sorted(unknown_session))
                    )
                name = str(item.get("name") or "").strip().lower()
                if not name:
                    raise ValueError("each session needs a name")
                value = {"name": name}
                if "enabled" in item:
                    if not isinstance(item["enabled"], bool):
                        raise ValueError("session enabled must be true or false")
                    value["enabled"] = item["enabled"]
                clock_keys = [
                    key for key in ("start", "standard_start", "dst_start")
                    if item.get(key) not in (None, "")
                ]
                if "start" not in clock_keys and not {
                    "standard_start", "dst_start",
                }.issubset(clock_keys):
                    raise ValueError(
                        f"session {name} needs start or both DST start values"
                    )
                for key in clock_keys:
                    clock_value = str(item[key])
                    datetime.strptime(clock_value, "%H:%M")
                    value[key] = clock_value
                validated.append(value)
            clean["sessions"] = validated
        return clean

    def configure_strategy(self, strategy, symbol, settings):
        strategy = str(strategy or "").strip().lower()
        if strategy not in ("emt", "eat"):
            raise ValueError("strategy must be EMT or EAT")
        symbol = self.root_symbol(symbol)
        clean = self._clean_runtime_settings(strategy, settings)
        other = "eat" if strategy == "emt" else "emt"
        disabled_other = False
        with self.engine_lock:
            saved = dict(self.strategy_runtime[strategy].get(symbol, {}))
            saved.update(clean)
            engine = self._replace_engine(strategy, symbol, saved)
            if "enabled" in clean and engine.control_state_key and engine.db_mirror:
                engine.db_mirror.set_state(
                    engine.control_state_key,
                    "true" if bool(clean["enabled"]) else "false",
                )
                engine.enabled = bool(clean["enabled"])
            self.strategy_runtime[strategy][symbol] = saved
            # Mutual exclusion: only one strategy may run per symbol at a time.
            # Enabling one here auto-disables the other rather than rejecting
            # the request — the other engine is left in place (not torn down)
            # so an already-open trade keeps being managed to close.
            if clean.get("enabled"):
                other_engines = (
                    self.emt_engines if other == "emt" else self.eat_engines
                )
                other_engine = other_engines.get(symbol)
                if other_engine is not None and other_engine.enabled:
                    if other_engine.control_state_key and other_engine.db_mirror:
                        other_engine.db_mirror.set_state(
                            other_engine.control_state_key, "false"
                        )
                    other_engine.enabled = False
                    other_saved = dict(
                        self.strategy_runtime[other].get(symbol, {})
                    )
                    other_saved["enabled"] = False
                    self.strategy_runtime[other][symbol] = other_saved
                    disabled_other = True
            self._persist_strategy_runtime()
        print(
            f"{strategy.upper()} CONFIG · {symbol} · "
            f"{'enabled' if engine.enabled else 'disabled'} · "
            f"contracts {engine.quantity}"
            + (
                f" · auto-disabled {other.upper()} on {symbol} (mutual exclusion)"
                if disabled_other else ""
            ),
            flush=True,
        )
        return self.strategy_status(symbol)

    def strategy_status(self, symbol, strategy=None):
        symbol = self.root_symbol(symbol)
        if symbol not in self.config.get("contracts", {}):
            raise ValueError(f"{symbol} is not an enabled Ninja futures contract")
        result = {
            "ok": True,
            "symbol": symbol,
            "futures_only": True,
            "bridge": self.bridge_status(),
            "strategies": {},
        }
        names = (strategy,) if strategy in ("emt", "eat") else ("emt", "eat")
        with self.engine_lock:
            for name in names:
                engines = self.emt_engines if name == "emt" else self.eat_engines
                engine = engines.get(symbol)
                if engine is None:
                    result["strategies"][name] = {
                        "configured": False,
                        "enabled": False,
                    }
                    continue
                result["strategies"][name] = {
                    "configured": True,
                    "enabled": bool(engine.enabled),
                    "settings": dict(engine.settings),
                    "state": engine.snapshot(),
                    "overlay": engine.chart_overlay(),
                }
        return result

    def close_strategy_trade(self, strategy, symbol, trade_id):
        """Close an exact VPS paper trade without involving any broker adapter."""
        strategy = str(strategy or "").strip().lower()
        if strategy not in ("emt", "eat"):
            raise ValueError("strategy must be EMT or EAT")
        symbol = self.root_symbol(str(symbol or ""))
        if not trade_id:
            raise ValueError("trade_id is required")
        with self.engine_lock:
            engines = self.emt_engines if strategy == "emt" else self.eat_engines
            engine = engines.get(symbol)
        if engine is None:
            raise LookupError(
                f"{strategy.upper()} {symbol} is not configured in this scanner"
            )
        closed = engine.manual_close(str(trade_id))
        print(
            f"{strategy.upper()} MANUAL CLOSE · {symbol} · {trade_id} · "
            f"{closed.get('exit_price')} · P&L "
            f"${float(closed.get('pnl', closed.get('realized_pnl', 0)) or 0):.2f}",
            flush=True,
        )
        return {
            "ok": True,
            "strategy": strategy,
            "symbol": symbol,
            "trade_id": str(trade_id),
            "trade": closed,
        }

    @staticmethod
    def root_symbol(symbol):
        return symbol.split()[0].upper()

    def add(self, bar):
        required = ("symbol", "time", "open", "high", "low", "close", "volume")
        if any(key not in bar for key in required):
            raise ValueError("bar is missing required fields")
        symbol = self.root_symbol(str(bar["symbol"]))
        clean = {"symbol": symbol, "time": str(bar["time"])}
        for key in ("open", "high", "low", "close", "volume"):
            clean[key] = float(bar[key])
        with self.lock:
            by_time = {item["time"]: item for item in self.bars[symbol]}
            by_time[clean["time"]] = clean
            ordered = sorted(by_time.values(), key=lambda item: item["time"])[-2000:]
            self.bars[symbol].clear()
            self.bars[symbol].extend(ordered)
            self.last_received[symbol] = time.time()
        with self.engine_lock:
            emt = self.emt_engines.get(symbol)
            eat = self.eat_engines.get(symbol)
        if emt is not None:
            emt.on_minute_bar(
                clean, historical=bool(bar.get("historical", False))
            )
        if eat is not None:
            events = eat.on_minute_bar(
                clean, historical=bool(bar.get("historical", False))
            )
            now = time.time()
            for event in events:
                print(
                    f"EAT EVENT · {symbol} · {event.kind} · "
                    f"{event.direction or ''} · {event.price:.2f} · "
                    f"{event.message}",
                    flush=True,
                )
            if now - self.last_eat_status_log >= 30:
                snap = eat.snapshot()
                print(
                    f"EAT STATUS · {symbol} · {snap.get('phase')} · "
                    f"{snap.get('status_message')} · trades "
                    f"{snap.get('trades_this_session')}",
                    flush=True,
                )
                self.last_eat_status_log = now

    def add_emt(self, bar):
        if str(bar.get("bar_type", "")).lower() != "tick":
            raise ValueError("EMT accepts tick bars only")
        symbol = self.root_symbol(str(bar.get("symbol", "")))
        with self.engine_lock:
            engine = self.emt_engines.get(symbol)
        if engine is None:
            return
        events = engine.on_tick_bar(
            bar,
            complete=bool(bar.get("complete", False)),
            historical=bool(bar.get("historical", False)),
        )
        now = time.time()
        for event in events:
            print(
                f"EMT EVENT · {symbol} · {event.kind} · "
                f"{event.direction or ''} · {event.price:.2f} · "
                f"{event.message}",
                flush=True,
            )
        if now - self.last_emt_status_log >= 30:
            snap = engine.snapshot()
            print(
                f"EMT STATUS · {symbol} · {snap.get('phase')} · "
                f"{snap.get('status_message')} · tick bars "
                f"{snap.get('tick_bars')} · trades "
                f"{snap.get('trades_this_session')}",
                flush=True,
            )
            self.last_emt_status_log = now
    def snapshot(self):
        with self.lock:
            return {symbol: list(values) for symbol, values in self.bars.items()}, dict(self.last_received)

    def heartbeat(self, value):
        with self.lock:
            self.last_heartbeat = time.time()
            self.heartbeat_details = {
                "source": str(value.get("source") or "ninjatrader"),
                "subscriptions": int(value.get("subscriptions") or 0),
                "reported_time": str(value.get("time") or ""),
            }

    def touch_bridge(self, value=None):
        """Mark the Ninja bridge alive when any authenticated payload arrives."""
        value = value or {}
        with self.lock:
            self.last_heartbeat = time.time()
            if not self.heartbeat_details:
                self.heartbeat_details = {
                    "source": str(value.get("source") or "ninjatrader"),
                    "subscriptions": int(value.get("subscriptions") or 0),
                    "reported_time": str(value.get("time") or ""),
                }
            elif value.get("time"):
                self.heartbeat_details["reported_time"] = str(value.get("time"))

    def bridge_status(self):
        with self.lock:
            last = self.last_heartbeat
            details = dict(self.heartbeat_details)
        age = None if last is None else max(0.0, time.time() - last)
        return {
            "alive": age is not None and age <= 75,
            "age_seconds": None if age is None else round(age, 1),
            **details,
        }


def ema(values, period):
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def aggregate(bars, size):
    """Combine sequential one-minute bars into completed N-minute groups."""
    complete = len(bars) - (len(bars) % size)
    result = []
    for start in range(0, complete, size):
        group = bars[start:start + size]
        result.append({
            "time": group[0]["time"], "open": group[0]["open"],
            "high": max(item["high"] for item in group),
            "low": min(item["low"] for item in group),
            "close": group[-1]["close"],
            "volume": sum(item["volume"] for item in group),
        })
    return result


def assess(symbol, bars, received, config):
    """Original straight-up/straight-down trend signal; retained alongside confluence."""
    age = time.time() - received if received else float("inf")
    if age > config["stale_after_seconds"]:
        return "STALE", 0, "No recent completed bar", age
    if len(bars) < 45:
        return "WARMING", 0, f"{len(bars)}/45 one-minute bars", age
    bars3 = aggregate(bars, 3)
    bars15 = aggregate(bars, 15)
    closes = [bar["close"] for bar in bars3]
    ranges = [bar["high"] - bar["low"] for bar in bars3[-20:]]
    fast, slow = ema(closes[-15:], 4), ema(closes[-30:], 8)
    atr = statistics.fmean(ranges) if ranges else 0
    momentum = closes[-1] - closes[-2]
    trend15 = bars15[-1]["close"] - bars15[-3]["open"]
    direction = ("LONG" if fast > slow and momentum > 0 and trend15 > 0 else
                 "SHORT" if fast < slow and momentum < 0 and trend15 < 0 else "WAIT")
    score = min(100, int(abs(fast - slow) / max(atr, 1e-9) * 45 + abs(momentum) / max(atr, 1e-9) * 20))
    decision = "READY" if direction != "WAIT" and score >= 65 else "WATCH" if direction != "WAIT" else "WAIT"
    support = min(item["low"] for item in bars15[-3:])
    resistance = max(item["high"] for item in bars15[-3:])
    reason = (f"{direction} 3m EMA4/8={fast:.2f}/{slow:.2f} "
              f"15m S/R={support:.2f}/{resistance:.2f}")
    return decision, score, reason, age


def sound_ready_alert(config):
    settings = config.get("signal_engine", {})
    if not settings.get("terminal_sound_alerts", False):
        return
    try:
        if os.name == "nt":
            import winsound
            winsound.Beep(int(settings.get("alert_frequency_hz", 1100)),
                          int(settings.get("alert_duration_ms", 250)))
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


def state_cell(decision, config):
    """Color only the fixed-width state cell; calculations remain plain text."""
    cell = f"{decision:<8}"
    if not config.get("signal_engine", {}).get("color_output", True):
        return cell
    color = {
        "READY": "\033[92m",
        "WATCH": "\033[93m",
        "WAIT": "\033[37m",
        "WARMING": "\033[96m",
        "STALE": "\033[91m",
        "ILLIQUID": "\033[90m",
    }.get(decision, "")
    return f"{color}{cell}\033[0m" if color else cell


def evaluate_symbols(state):
    """Return one read-only, JSON-safe assessment row per configured contract."""
    bars_by_symbol, received = state.snapshot()
    rows = []
    for symbol, contract in state.config["contracts"].items():
        bars = bars_by_symbol.get(symbol, [])
        trend_state, trend_score, trend_reason, age = assess(
            symbol, bars, received.get(symbol), state.config
        )
        try:
            enhanced = assess_confluence(
                symbol, bars, contract, state.config.get("signal_engine", {})
            )
            decision, score, reason = enhanced.state, enhanced.score, enhanced.reason
            direction, metrics = enhanced.direction, enhanced.metrics
        except Exception as exc:
            decision, score = "WAIT", 0
            direction, metrics = "wait", {}
            reason = f"confluence error: {type(exc).__name__}: {exc}"

        if trend_state == "STALE":
            decision, score, reason = "STALE", 0, "No recent completed bar"
            direction, metrics = "wait", {}
            family = contract.get("family")
            sibling_fresh = any(
                other != symbol
                and details.get("family") == family
                and time.time() - received.get(other, 0) <= state.config["stale_after_seconds"]
                for other, details in state.config["contracts"].items()
            )
            if sibling_fresh:
                decision = "ILLIQUID"
                reason = "No recent trades; related contract feed is healthy"

        rows.append({
            "symbol": symbol,
            "bars": len(bars),
            "age_seconds": None if age == float("inf") else round(age, 1),
            "state": decision,
            "score": score,
            "direction": direction,
            "reason": reason,
            "metrics": metrics,
            "trend_state": trend_state,
            "trend_score": trend_score,
            "trend_reason": trend_reason,
            "contract": contract,
        })
    return rows


def current_assessments(state, max_age_seconds=2.0):
    """Return one short-lived shared assessment for every display client."""
    now = time.monotonic()
    with state.assessment_lock:
        if state.assessment_rows is not None and now - state.assessment_created_at < max_age_seconds:
            return state.assessment_rows
        state.assessment_rows = evaluate_symbols(state)
        state.assessment_created_at = time.monotonic()
        return state.assessment_rows


def dashboard(state):
    previous_states = {}
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("NINJATRADER FUTURES SCANNER — ADVISORY ONLY")
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "local\n")
        bridge = state.bridge_status()
        bridge_age = "--" if bridge["age_seconds"] is None else f'{bridge["age_seconds"]:.0f}s'
        bridge_state = "ALIVE" if bridge["alive"] else "NO HEARTBEAT"
        print(
            f"BRIDGE {bridge_state} · heartbeat age {bridge_age} · "
            f"subscriptions {bridge.get('subscriptions', 0)}\n"
        )
        emt = state.emt.snapshot()
        eat = state.eat.snapshot()
        print(
            f"EMT {emt['execution_mode'].upper()} · {emt['symbol']} · {emt['phase']} · "
            f"OR {emt['opening_low']}/{emt['opening_high']} · "
            f"610t bars {emt['tick_bars']} · trades {emt['trades_this_session']}\n"
        )
        print(
            f"EAT {eat['execution_mode'].upper()} · {eat['symbol']} · {eat['phase']} · "
            f"box {eat['inner_low']}/{eat['inner_high']} · "
            f"trades {eat['trades_this_session']}\n"
        )
        print(f"{'SYMBOL':<8} {'BARS':>5} {'AGE':>7} {'STATE':<8} {'SCORE':>5} {'TREND':<7} {'T-SCR':>5}  DETAILS")
        print("-" * 150)
        for row in current_assessments(state):
            symbol = row["symbol"]
            decision, score, reason = row["state"], row["score"], row["reason"]
            trend_state, trend_score, trend_reason = (
                row["trend_state"], row["trend_score"], row["trend_reason"]
            )
            previous = previous_states.get(symbol)
            if decision == "READY" and previous is not None and previous != "READY":
                threading.Thread(target=sound_ready_alert, args=(state.config,), daemon=True).start()
            previous_states[symbol] = decision
            age = row["age_seconds"]
            age_text = "--" if age is None else f"{age:4.0f}s"
            print(
                f"{symbol:<8} {row['bars']:>5} {age_text:>7} {state_cell(decision, state.config)} {score:>5} "
                f"{trend_state:<7} {trend_score:>5}  {reason} | FAST: {trend_reason}"
            )
        print("\nCtrl+C stops the receiver. EMT live mode uses broker-hosted brackets.")
        time.sleep(2)


def emt_watchdog(state):
    while True:
        time.sleep(60)
        try:
            bridge = state.bridge_status()
            emt = state.emt.snapshot()
            eat = state.eat.snapshot()
            age = bridge.get("age_seconds")
            age_text = "--" if age is None else f"{age:.0f}s"
            bridge_text = "ALIVE" if bridge.get("alive") else "STALE"
            print(
                f"EMT WATCH · bridge {bridge_text} · heartbeat age {age_text} · "
                f"phase {emt.get('phase')} · tick bars {emt.get('tick_bars')} · "
                f"{emt.get('status_message')}",
                flush=True,
            )
            print(
                f"EAT WATCH · bridge {bridge_text} · heartbeat age {age_text} · "
                f"phase {eat.get('phase')} · {eat.get('status_message')}",
                flush=True,
            )
        except Exception as exc:
            print(f"EMT WATCH ERROR · {type(exc).__name__}: {exc}", flush=True)


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, body):
            payload = json.dumps(body).encode()
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/strategy/status":
                params = parse_qs(parsed.query)
                symbol = (params.get("symbol") or [""])[0]
                strategy = (params.get("strategy") or [""])[0].strip().lower()
                if not symbol:
                    return self._json(400, {"ok": False, "error": "symbol is required"})
                try:
                    result = state.strategy_status(symbol, strategy or None)
                except (ValueError, TypeError) as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})
                return self._json(200, result)
            if path not in ("/health", "/snapshot"):
                self.send_error(404)
                return
            with state.engine_lock:
                emt_engines = dict(state.emt_engines)
                eat_engines = dict(state.eat_engines)
            body = {
                "ok": True,
                "bridge": state.bridge_status(),
                "emt": state.emt.snapshot(),
                "eat": state.eat.snapshot(),
                "emt_strategies": {
                    symbol: engine.snapshot()
                    for symbol, engine in emt_engines.items()
                },
                "eat_strategies": {
                    symbol: engine.snapshot()
                    for symbol, engine in eat_engines.items()
                },
            }
            if path == "/snapshot":
                body["contracts"] = current_assessments(state)
                bars, received = state.snapshot()
                body["bars"] = bars
                body["last_received"] = {
                    key: round(time.time() - value, 1)
                    for key, value in received.items()
                }
                body["emt_overlays"] = {
                    symbol: engine.chart_overlay()
                    for symbol, engine in emt_engines.items()
                }
                body["eat_overlays"] = {
                    symbol: engine.chart_overlay()
                    for symbol, engine in eat_engines.items()
                }
                # Backward-compatible aliases for existing clients.
                body["emt_overlay"] = state.emt.chart_overlay()
                body["eat_overlay"] = state.eat.chart_overlay()
                body["generated_at"] = datetime.now(timezone.utc).isoformat()
            else:
                body["symbols"] = list(state.bars)
            self._json(200, body)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path not in (
                "/ingest/bar", "/ingest/emt/bar", "/ingest/heartbeat",
                "/strategy/config", "/strategy/close",
            ):
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 65536:
                    raise ValueError("invalid body size")
                value = json.loads(self.rfile.read(length))
                if value.get("secret") != state.config["shared_secret"]:
                    self.send_error(403)
                    return
                if path == "/strategy/config":
                    result = state.configure_strategy(
                        value.get("strategy"),
                        value.get("symbol"),
                        value.get("settings") or {},
                    )
                    self._json(200, result)
                    return
                if path == "/strategy/close":
                    try:
                        result = state.close_strategy_trade(
                            value.get("strategy"),
                            value.get("symbol"),
                            value.get("trade_id"),
                        )
                    except LookupError as exc:
                        self._json(409, {
                            "ok": False,
                            "code": "trade_not_active",
                            "error": str(exc),
                        })
                        return
                    self._json(200, result)
                    return
                if path == "/ingest/heartbeat":
                    state.heartbeat(value)
                elif path == "/ingest/emt/bar":
                    state.touch_bridge(value)
                    state.add_emt(value)
                else:
                    state.touch_bridge(value)
                    state.add(value)
                try:
                    self.send_response(204)
                    self.end_headers()
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                    return
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                if path in ("/strategy/config", "/strategy/close"):
                    self._json(400, {"ok": False, "error": str(exc)})
                else:
                    self.send_error(400, str(exc))

        def log_message(self, _format, *_args):
            return
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join(ROOT, "ninja_futures_config.json"))
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="run only the HTTP receiver (recommended for systemd)",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if os.name == "nt":
        os.system("")  # Enable ANSI colors in current Windows terminals.
    if config["listen_host"] not in ("127.0.0.1", "localhost"):
        raise SystemExit("Refusing to bind outside localhost")
    if len(config["shared_secret"]) < 32:
        print("WARNING: NINJA_BRIDGE_SECRET should be a 32+ character random value.")
    state = MarketState(config)
    server = ThreadingHTTPServer((config["listen_host"], int(config["listen_port"])), make_handler(state))
    threading.Thread(target=emt_watchdog, args=(state,), name="emt-watchdog", daemon=True).start()
    if args.no_dashboard:
        print(
            f"EMT receiver listening on {config['listen_host']}:{config['listen_port']} "
            f"in {state.emt.snapshot()['execution_mode'].upper()} mode",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    threading.Thread(target=server.serve_forever, name="ninja-receiver", daemon=True).start()
    try:
        dashboard(state)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
