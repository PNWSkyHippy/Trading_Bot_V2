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


ROOT = os.path.dirname(os.path.abspath(__file__))


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class MarketState:
    def __init__(self, config):
        self.config = config
        self.bars = defaultdict(lambda: deque(maxlen=2000))
        self.last_received = {}
        self.lock = threading.Lock()

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

    def snapshot(self):
        with self.lock:
            return {symbol: list(values) for symbol, values in self.bars.items()}, dict(self.last_received)


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


def dashboard(state):
    while True:
        bars_by_symbol, received = state.snapshot()
        os.system("cls" if os.name == "nt" else "clear")
        print("NINJATRADER FUTURES SCANNER — ADVISORY ONLY")
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "local\n")
        print(f"{'SYMBOL':<8} {'BARS':>5} {'AGE':>7} {'STATE':<9} {'SCORE':>5}  DETAILS")
        print("-" * 90)
        for symbol in state.config["contracts"]:
            bars = bars_by_symbol.get(symbol, [])
            decision, score, reason, age = assess(symbol, bars, received.get(symbol), state.config)
            if decision == "STALE":
                family = state.config["contracts"][symbol].get("family")
                sibling_fresh = any(
                    other != symbol
                    and details.get("family") == family
                    and time.time() - received.get(other, 0) <= state.config["stale_after_seconds"]
                    for other, details in state.config["contracts"].items()
                )
                if sibling_fresh:
                    decision = "ILLIQUID"
                    reason = "No recent trades; related contract feed is healthy"
            age_text = "--" if age == float("inf") else f"{age:4.0f}s"
            print(f"{symbol:<8} {len(bars):>5} {age_text:>7} {decision:<9} {score:>5}  {reason}")
        print("\nCtrl+C stops the receiver. No order endpoint exists.")
        time.sleep(2)


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            payload = json.dumps({"ok": True, "symbols": list(state.bars)}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

        def do_POST(self):
            if self.path != "/ingest/bar":
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
                state.add(value)
                self.send_response(204); self.end_headers()
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send_error(400, str(exc))

        def log_message(self, _format, *_args):
            return
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join(ROOT, "ninja_futures_config.json"))
    args = parser.parse_args()
    config = load_config(args.config)
    if config["listen_host"] not in ("127.0.0.1", "localhost"):
        raise SystemExit("Refusing to bind outside localhost")
    if config["shared_secret"] == "change-this-local-secret":
        print("WARNING: replace the default shared_secret in both bridge files.")
    state = MarketState(config)
    server = ThreadingHTTPServer((config["listen_host"], int(config["listen_port"])), make_handler(state))
    threading.Thread(target=server.serve_forever, name="ninja-receiver", daemon=True).start()
    try:
        dashboard(state)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
