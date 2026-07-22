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

from dotenv import load_dotenv

try:
    from .emt_strategy import EMTStrategyEngine
    from .futures_signal_engine import assess_confluence
    from .tradovate_executor import TradovateExecutor
except ImportError:  # direct script execution
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
        # The console and GUI read the same calculations.  Keep one short-lived
        # shared result instead of making both recalculate every symbol at once.
        self.assessment_lock = threading.Lock()
        self.assessment_rows = None
        self.assessment_created_at = 0.0
        emt_settings = dict(config.get("emt", {}))
        execution_mode = os.getenv("EMT_EXECUTION_MODE", "paper").strip().lower()
        if execution_mode not in ("paper", "live"):
            raise ValueError("EMT_EXECUTION_MODE must be paper or live")
        emt_settings["paper_only"] = execution_mode != "live"
        emt_symbol = str(emt_settings.get("symbol", "ES")).upper()
        executor = None
        if execution_mode == "live":
            executor = TradovateExecutor.from_env(emt_settings)
            executor.verify_account()
        self.emt = EMTStrategyEngine(
            emt_settings,
            config.get("contracts", {}).get(emt_symbol, {}),
            ROOT,
            executor=executor,
        )

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
        if symbol == self.emt.symbol:
            self.emt.on_minute_bar(clean, historical=bool(bar.get("historical", False)))

    def add_emt(self, bar):
        if str(bar.get("bar_type", "")).lower() != "tick":
            raise ValueError("EMT accepts tick bars only")
        self.emt.on_tick_bar(
            bar,
            complete=bool(bar.get("complete", False)),
            historical=bool(bar.get("historical", False)),
        )

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
        print(
            f"EMT {emt['execution_mode'].upper()} · {emt['symbol']} · {emt['phase']} · "
            f"OR {emt['opening_low']}/{emt['opening_high']} · "
            f"610t bars {emt['tick_bars']} · trades {emt['trades_this_session']}\n"
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


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/health", "/snapshot"):
                self.send_error(404)
                return
            body = {
                "ok": True,
                "bridge": state.bridge_status(),
                "emt": state.emt.snapshot(),
            }
            if self.path == "/snapshot":
                body["contracts"] = current_assessments(state)
                body["generated_at"] = datetime.now(timezone.utc).isoformat()
            else:
                body["symbols"] = list(state.bars)
            payload = json.dumps(body).encode()
            try:
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                # A GUI/browser poll can disappear while its response is being written.
                # That is a client disconnect, not a scanner or NinjaTrader failure.
                return

        def do_POST(self):
            if self.path not in ("/ingest/bar", "/ingest/emt/bar", "/ingest/heartbeat"):
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
                if self.path == "/ingest/heartbeat":
                    state.heartbeat(value)
                elif self.path == "/ingest/emt/bar":
                    state.add_emt(value)
                else:
                    state.add(value)
                try:
                    self.send_response(204); self.end_headers()
                except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                    return
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
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
