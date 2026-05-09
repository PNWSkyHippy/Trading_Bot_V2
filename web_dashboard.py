"""HTML dashboard bridge.

Run: python web_dashboard.py
"""
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
HTML_ROOT = ROOT / "Html-Files"
if not HTML_ROOT.exists():
    HTML_ROOT = ROOT / "HTML-Files"

try:
    import config as _config
    _default_db_path = Path(_config.DB_PATH)
    if not _default_db_path.is_absolute():
        _default_db_path = ROOT / _default_db_path
except Exception:
    _default_db_path = ROOT / "data" / "trading_bot.db"

DB_PATH = Path(os.environ.get("WEB_DASHBOARD_DB_PATH", str(_default_db_path)))
BOT_SCRIPT = ROOT / "bot_engine.py"
BOT_PYTHON = ROOT / "venv312" / "Scripts" / "python.exe"
WEB_DASHBOARD_PORT = 8125

risk_manager = None
db = None

try:
    from data.database import db as _db
    db = _db
except Exception:
    db = None

try:
    from core.risk_manager import risk_manager as _risk_manager
    risk_manager = _risk_manager
except Exception:
    risk_manager = None


def is_bot_running():
    """Best-effort check for bot process."""
    try:
        if sys.platform == "win32":
            pids = find_bot_pids_windows()
            return len(pids) > 0
        out = subprocess.check_output(["ps", "-ef"], text=True)
        return "bot_engine.py" in out
    except Exception:
        return False


def find_bot_pids_windows():
    """Find PIDs for processes whose command line contains bot_engine.py."""
    try:
        import psutil

        bot_name = BOT_SCRIPT.name.lower()
        current_pid = os.getpid()
        pids = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                pid = int(info.get("pid") or 0)
                if pid == current_pid:
                    continue
                name = (info.get("name") or "").lower()
                if name not in ("python.exe", "pythonw.exe", "python"):
                    continue
                cmdline = [str(part) for part in (info.get("cmdline") or [])]
                if any(Path(part).name.lower() == bot_name for part in cmdline):
                    pids.append(pid)
            except Exception:
                continue
        if pids:
            return pids
    except Exception:
        pass

    try:
        bot_path = str(BOT_SCRIPT.resolve()).replace("'", "''").lower()
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$target = '"
                + bot_path
                + "'; "
                + "$current = "
                + str(os.getpid())
                + "; "
                + "Get-CimInstance Win32_Process | "
                + "Where-Object { "
                + "$_.ProcessId -ne $current -and "
                + "$_.Name -match '^(python|pythonw)\\.exe$' -and "
                + "$_.CommandLine -and "
                + "$_.CommandLine.ToLower().Contains($target) "
                + "} | "
                + "Select-Object -ExpandProperty ProcessId"
            ),
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
        return [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]
    except Exception:
        return []


def start_bot_process():
    """Start bot_engine.py if not already running."""
    if is_bot_running():
        return False, "Bot is already running."
    try:
        python_exe = str(BOT_PYTHON if BOT_PYTHON.exists() else Path(sys.executable))
        if sys.platform == "win32":
            # Launch through cmd /k so the bot has a visible console with live output.
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NEW_CONSOLE = 0x00000010
            flags = CREATE_NEW_CONSOLE | CREATE_NEW_PROCESS_GROUP
            launcher = ROOT / "StartBotEngine.bat"
            ps_launcher = ROOT / "StartBotEngine.ps1"
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-File",
                    str(ps_launcher if ps_launcher.exists() else launcher),
                ],
                cwd=str(ROOT),
                creationflags=flags,
            )
        else:
            subprocess.Popen(
                [python_exe, str(BOT_SCRIPT)],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        return True, "Bot start requested."
    except Exception as exc:
        return False, f"Failed to start bot: {exc}"


def stop_bot_process():
    """Stop bot_engine.py process(es)."""
    try:
        if sys.platform == "win32":
            pids = find_bot_pids_windows()
            if not pids:
                return False, "No bot_engine.py process found."
            killed = 0
            for pid in pids:
                result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    killed += 1
            if killed > 0:
                return True, f"Bot stop requested for {killed} process(es)."
            return False, "Matched bot process IDs but taskkill failed."
        else:
            result = subprocess.run(["pkill", "-f", "bot_engine.py"], check=False)
            if result.returncode == 0:
                return True, "Bot stop requested."
            return False, "No bot_engine.py process found."
    except Exception as exc:
        return False, f"Failed to stop bot: {exc}"


def get_open_positions():
    """Return open positions using DB adapter when available, else SQLite fallback."""
    if db is not None:
        try:
            rows = db.get_open_trades() or []
            positions = []
            for t in rows:
                current_price = get_current_price(
                    t.get("symbol") or t.get("ticker") or "?",
                    t.get("asset_class") or "crypto",
                ) or float(t.get("entry_price") or 0)
                entry_price = float(t.get("entry_price") or 0)
                qty = float(t.get("quantity") or t.get("shares") or 0)
                direction = (t.get("direction") or t.get("side") or "long").lower()
                pnl = (current_price - entry_price) * qty
                if direction == "short":
                    pnl = -pnl
                pnl_pct = 0.0
                if entry_price:
                    raw_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl_pct = raw_pct if direction == "long" else -raw_pct
                stop_loss = float(t.get("stop_loss") or entry_price or 0)
                take_profit = float(t.get("take_profit") or entry_price or 0)
                distance_to_sl = abs((current_price - stop_loss) / current_price * 100) if current_price else 0
                distance_to_tp = abs((take_profit - current_price) / current_price * 100) if current_price else 0
                positions.append({
                    "id": t.get("id"),
                    "trade_id": t.get("trade_id"),
                    "symbol": t.get("symbol") or t.get("ticker") or "?",
                    "asset_class": t.get("asset_class") or "crypto",
                    "side": direction,
                    "direction": direction,
                    "qty": qty,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "unrealized_pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "distance_to_sl": distance_to_sl,
                    "distance_to_tp": distance_to_tp,
                    "entry_time": t.get("entry_time") or "",
                })
            return positions
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, symbol, side, COALESCE(shares, quantity, 0), entry_price, entry_time
            FROM trades
            WHERE status='open'
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "symbol": r[1],
                "side": r[2] or "",
                "qty": float(r[3] or 0),
                "entry_price": float(r[4] or 0),
                "entry_time": r[5] or "",
            }
            for r in rows
        ]
    except Exception:
        return []


def close_position(position_id):
    """Close a position through the same executor path used by the bot."""
    try:
        trade_record = None
        if db is not None:
            for t in db.get_open_trades() or []:
                if str(t.get("id")) == str(position_id) or str(t.get("trade_id")) == str(position_id):
                    trade_record = t
                    break

        if trade_record is None:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM trades WHERE status='open' AND (id=? OR trade_id=?)",
                (position_id, str(position_id)),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                trade_record = dict(row)

        if not trade_record:
            return False, f"Position id {position_id} not found or already closed."

        symbol = trade_record["symbol"]
        asset_class = trade_record.get("asset_class", "crypto")
        current_price = get_current_price(symbol, asset_class) or trade_record.get("entry_price")
        if not current_price:
            return False, f"Could not get current price for {symbol}."

        from core.trade_executor import executor

        success = executor.close_trade(trade_record, float(current_price), "manual_close")
        if not success:
            return False, f"Executor returned failure for {symbol}."
        return True, f"Closed {symbol} @ ${float(current_price):.4f}."
    except Exception as exc:
        return False, f"Close failed: {exc}"


def get_current_price(symbol, asset_class):
    try:
        from scanners.market_scanner import scanner
        return scanner.get_current_price(symbol, asset_class)
    except Exception:
        try:
            from scanners.market_scanner import MarketScanner
            market_scanner = MarketScanner()
            return market_scanner.get_current_price(symbol, asset_class)
        except Exception:
            return None


def get_candles(symbol, asset_class, timeframe="5 Min", limit=100):
    """Return OHLC candles for the HTML chart."""
    try:
        limit = max(10, min(int(limit), 300))
    except Exception:
        limit = 100

    if asset_class == "stock":
        tf_map = {"1 Min": "1Min", "5 Min": "5Min", "15 Min": "15Min", "1 H": "1Hour", "4 H": "1Hour", "1 D": "1Day"}
        try:
            import alpaca_trade_api as tradeapi
            import config

            api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
            raw = api.get_bars(symbol, tf_map.get(timeframe, "5Min"), limit=limit, adjustment="raw").df
            if raw.empty:
                return []
            raw.index = raw.index.astype(str)
            return [
                {
                    "time": str(idx),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
                for idx, row in raw.iterrows()
            ]
        except Exception:
            return []

    tf_map = {"1 Min": "1m", "5 Min": "5m", "15 Min": "15m", "1 H": "1h", "4 H": "4h", "1 D": "1d"}
    try:
        import ccxt

        exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 10000})
        rows = exchange.fetch_ohlcv(symbol, tf_map.get(timeframe, "5m"), limit=limit)
        return [
            {
                "time": int(ts),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
            for ts, o, h, l, c, _v in rows
        ]
    except Exception:
        return []


WATCHLIST_DIR = ROOT / "watchlist"
INJECTED_STOCKS_FILE = WATCHLIST_DIR / "scanned_stocks.txt"
INJECTED_CRYPTO_FILE = WATCHLIST_DIR / "scanned_crypto.txt"


def _read_symbol_file(path):
    try:
        if not path.exists():
            return []
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except Exception:
        return []


def get_injected_symbols():
    return {
        "stocks": _read_symbol_file(INJECTED_STOCKS_FILE),
        "crypto": _read_symbol_file(INJECTED_CRYPTO_FILE),
    }


def inject_symbols(kind, raw_symbols):
    if isinstance(raw_symbols, str):
        symbols = raw_symbols.replace(",", "\n").splitlines()
    else:
        symbols = raw_symbols or []

    cleaned = []
    for symbol in symbols:
        value = str(symbol or "").strip().upper()
        if not value:
            continue
        if kind == "crypto" and "/" not in value:
            value = f"{value}/USD"
        if value not in cleaned:
            cleaned.append(value)

    if kind not in ("stocks", "stock", "crypto"):
        return False, f"Unsupported injection kind: {kind}", get_injected_symbols()
    if not cleaned:
        return False, "No valid symbols entered.", get_injected_symbols()

    path = INJECTED_CRYPTO_FILE if kind == "crypto" else INJECTED_STOCKS_FILE
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    existing = [s for s in _read_symbol_file(path) if s not in cleaned]
    path.write_text("\n".join(cleaned + existing))
    label = "crypto pair" if kind == "crypto" else "stock"
    return True, f"Injected {len(cleaned)} {label}(s): {', '.join(cleaned)}", get_injected_symbols()


def clear_injected_symbols():
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    INJECTED_STOCKS_FILE.write_text("")
    INJECTED_CRYPTO_FILE.write_text("")
    return {"stocks": [], "crypto": []}


def _format_trade_time(raw):
    if not raw:
        return "—", None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed.strftime("%m/%d %H:%M"), parsed
    except Exception:
        return str(raw)[:16], None


def _normalize_trade_datetimes(entry_dt, exit_dt):
    if not entry_dt or not exit_dt:
        return entry_dt, exit_dt
    if entry_dt <= exit_dt:
        return entry_dt, exit_dt

    hours_ahead = (entry_dt - exit_dt).total_seconds() / 3600
    if 0 < hours_ahead <= 8.5:
        adjusted = entry_dt - timedelta(hours=7)
        if adjusted <= exit_dt:
            return adjusted, exit_dt
    return entry_dt, exit_dt


def _format_duration(entry_dt, exit_dt):
    if not entry_dt or not exit_dt:
        return "—"
    if entry_dt > exit_dt:
        return "—"
    minutes = int((exit_dt - entry_dt).total_seconds() / 60)
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60}m"
    return f"{minutes}m"


def get_today_trade_log():
    try:
        trades = db.get_trades_for_date(date.today().isoformat()) if db is not None else []
    except Exception:
        trades = []

    if not trades:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            trades = [dict(r) for r in conn.execute(
                "SELECT * FROM trades WHERE date(entry_time)=? ORDER BY entry_time",
                (date.today().isoformat(),),
            ).fetchall()]
            conn.close()
        except Exception:
            trades = []

    rows = []
    for trade in trades:
        if trade.get("status") != "closed":
            continue
        opened, entry_dt = _format_trade_time(trade.get("entry_time"))
        closed, exit_dt = _format_trade_time(trade.get("exit_time"))
        entry_dt, exit_dt = _normalize_trade_datetimes(entry_dt, exit_dt)
        if entry_dt:
            opened = entry_dt.strftime("%m/%d %H:%M")
        if exit_dt:
            closed = exit_dt.strftime("%m/%d %H:%M")
        pnl = float(trade.get("pnl") or 0)
        pnl_pct = float(trade.get("pnl_pct") or 0)
        rows.append({
            "opened": opened,
            "closed": closed,
            "duration": _format_duration(entry_dt, exit_dt),
            "symbol": trade.get("symbol") or "?",
            "direction": str(trade.get("direction") or "").upper(),
            "strategy": trade.get("strategy_name") or "original",
            "entry_price": float(trade.get("entry_price") or 0),
            "exit_price": float(trade.get("exit_price") or 0),
            "reason": str(trade.get("exit_reason") or "").replace("_", " ").title(),
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "result": "Win" if pnl > 0 else "Loss",
            "_sort": trade.get("exit_time") or "",
        })

    rows.sort(key=lambda row: row["_sort"], reverse=True)
    for row in rows:
        row.pop("_sort", None)
    return rows


def open_manual_trade(payload):
    """Open a manual trade and register it in the DB for bot management."""
    try:
        import uuid
        from datetime import datetime as dt

        symbol = str(payload.get("symbol") or "").strip().upper()
        if not symbol:
            return False, "Symbol is required.", {}

        asset_class = str(payload.get("asset") or payload.get("asset_class") or "stock").lower()
        direction = str(payload.get("dir") or payload.get("direction") or "long").lower()
        broker = str(payload.get("broker") or "paper").lower()
        strategy_label = str(payload.get("label") or payload.get("strategy") or "manual")
        position_size = float(payload.get("size") or payload.get("position_size") or 0)
        sl_pct = float(payload.get("sl") or payload.get("stop_loss_pct") or 1.5)
        tp_pct = float(payload.get("tp") or payload.get("take_profit_pct") or 3.0)
        overnight = bool(payload.get("overnight"))

        if asset_class not in ("stock", "crypto"):
            return False, f"Unsupported asset class: {asset_class}", {}
        if direction not in ("long", "short"):
            return False, f"Unsupported direction: {direction}", {}
        if position_size <= 0:
            return False, "Position size must be greater than 0.", {}

        entry = get_current_price(symbol, asset_class)
        if not entry:
            return False, f"Could not get live price for {symbol}.", {}

        qty = position_size / entry
        if direction == "long":
            sl = entry * (1 - sl_pct / 100)
            tp = entry * (1 + tp_pct / 100)
            side = "buy"
        else:
            sl = entry * (1 + sl_pct / 100)
            tp = entry * (1 - tp_pct / 100)
            side = "sell"

        broker_order_id = None
        actual_fill_price = entry

        if broker == "ibkr" and asset_class == "stock":
            try:
                from core.trade_executor import executor
                if not executor._ibkr or not executor._ibkr.is_available():
                    return False, "IBKR is not available. Check TWS is running on port 7497.", {}
                submit_qty = int(qty) if qty >= 1 else qty
                result = executor._ibkr.submit_order(
                    symbol=symbol,
                    qty=submit_qty,
                    side=side,
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                )
                if not result:
                    return False, f"IBKR rejected the order for {symbol}.", {}
                broker_order_id = result.get("broker_order_id")
                fill_price = result.get("filled_avg_price", 0)
                actual_fill_price = fill_price if fill_price and fill_price > 0 else entry
            except Exception as exc:
                return False, f"IBKR order error: {exc}", {}

        elif broker == "alpaca" and asset_class == "stock":
            try:
                from core.trade_executor import AlpacaExecutor
                alpaca_ex = AlpacaExecutor()
                submit_qty = int(qty) if qty >= 1 else qty
                result = alpaca_ex.submit_order(
                    symbol=symbol,
                    qty=submit_qty,
                    side=side,
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                )
                if not result:
                    return False, f"Alpaca rejected the order for {symbol}.", {}
                broker_order_id = result.get("broker_order_id")
                fill_price = result.get("filled_avg_price", 0)
                actual_fill_price = fill_price if fill_price and fill_price > 0 else entry
            except Exception as exc:
                return False, f"Alpaca order error: {exc}", {}

        if direction == "long":
            sl = actual_fill_price * (1 - sl_pct / 100)
            tp = actual_fill_price * (1 + tp_pct / 100)
        else:
            sl = actual_fill_price * (1 + sl_pct / 100)
            tp = actual_fill_price * (1 - tp_pct / 100)
        qty = position_size / actual_fill_price

        trade_id = str(uuid.uuid4())[:12]
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            INSERT INTO trades
                (trade_id, symbol, asset_class, direction, status,
                 entry_time, entry_price, quantity, position_value,
                 stop_loss, take_profit, pnl, pnl_pct,
                 signal_score, broker, strategy_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0,1.0,?,?)
            """,
            (
                trade_id,
                symbol,
                asset_class,
                direction,
                "open",
                dt.now().isoformat(),
                round(actual_fill_price, 6),
                round(qty, 6),
                round(position_size, 2),
                round(sl, 6),
                round(tp, 6),
                broker,
                strategy_label,
            ),
        )
        try:
            conn.execute(
                "UPDATE trades SET is_overnight=?, broker_order_id=? WHERE trade_id=?",
                (1 if overnight else 0, broker_order_id, trade_id),
            )
        except Exception:
            pass
        conn.commit()
        conn.close()

        return True, (
            f"{direction.upper()} {symbol} opened @ ${actual_fill_price:.6f} | "
            f"SL: ${sl:.6f} | TP: ${tp:.6f} | Qty: {qty:.4f} | Broker: {broker}"
        ), {"trade_id": trade_id, "entry_price": actual_fill_price, "quantity": qty}
    except Exception as exc:
        return False, f"Trade entry error: {exc}", {}


def build_snapshot():
    """Top-level status metrics."""
    if db is not None:
        cap = db.get_latest_capital() or {}
        open_trades = db.get_open_trades() or []
        halted = bool(getattr(risk_manager, "trading_halted", False)) if risk_manager else False
        return {
            "bot_status": "PAUSED" if halted else "ACTIVE",
            "open_positions": len(open_trades),
            "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
            "bot_process_running": is_bot_running(),
            "snapshot_source": "live_db_adapter",
            "db_path": str(DB_PATH),
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_positions = int(cur.fetchone()[0])
        cur.execute("SELECT available_cash FROM capital ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        available_cash = float(row[0]) if row else 0.0
        conn.close()
        return {
            "bot_status": "UNKNOWN",
            "open_positions": open_positions,
            "available_cash": available_cash,
            "bot_process_running": is_bot_running(),
            "snapshot_source": "sqlite_fallback",
            "db_path": str(DB_PATH),
        }
    except Exception:
        return {
            "bot_status": "UNKNOWN",
            "open_positions": 0,
            "available_cash": 0.0,
            "bot_process_running": is_bot_running(),
            "snapshot_source": "error_fallback",
            "db_path": str(DB_PATH),
        }


def load_entry_html(prefer_modular=True):
    modular = HTML_ROOT / "Trading Dashboard.html"
    stage3 = HTML_ROOT / "index.html"
    if prefer_modular and modular.exists():
        return modular.read_bytes(), "modular"
    return stage3.read_bytes(), "stage3"


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/snapshot":
            return self._json(200, build_snapshot())

        if path == "/api/open_positions":
            return self._json(200, {"positions": get_open_positions(), "db_path": str(DB_PATH)})

        if path == "/api/candles":
            params = parse_qs(parsed.query)
            symbol = (params.get("symbol") or [""])[0].strip().upper()
            asset_class = (params.get("asset_class") or params.get("asset") or ["crypto"])[0].lower()
            timeframe = (params.get("timeframe") or ["5 Min"])[0]
            limit = (params.get("limit") or ["100"])[0]
            if not symbol:
                return self._json(400, {"error": "symbol is required"})
            return self._json(200, {"candles": get_candles(symbol, asset_class, timeframe, limit)})

        if path == "/api/injected_symbols":
            return self._json(200, get_injected_symbols())

        if path == "/api/trade_log/today":
            return self._json(200, {"trades": get_today_trade_log(), "db_path": str(DB_PATH)})

        if path == "/" or path == "/index.html":
            page, mode = load_entry_html(prefer_modular=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Dashboard-Mode", mode)
            self._cors_headers()
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if path == "/stage3":
            page, _ = load_entry_html(prefer_modular=False)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors_headers()
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        rel_path = path.lstrip("/")
        if rel_path.startswith("static/"):
            rel_path = rel_path[len("static/"):]
        if rel_path:
            file_path = HTML_ROOT / rel_path
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                self.send_response(200)
                if file_path.suffix in (".jsx", ".js"):
                    mime = "text/javascript"
                elif file_path.suffix == ".css":
                    mime = "text/css"
                elif file_path.suffix == ".html":
                    mime = "text/html; charset=utf-8"
                else:
                    mime = "application/octet-stream"
                self.send_header("Content-Type", mime)
                self._cors_headers()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/trades/manual":
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            ok, msg, details = open_manual_trade(data)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/injected_symbols":
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            ok, msg, symbols = inject_symbols(str(data.get("kind") or "").lower(), data.get("symbols"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **symbols})

        if path == "/api/injected_symbols/clear":
            return self._json(200, {"ok": True, "message": "Injected symbols cleared.", **clear_injected_symbols()})

        if path != "/api/control":
            return self._json(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        action = data.get("action")

        if action == "pause_trading":
            if risk_manager is not None:
                risk_manager.manual_halt("Paused via HTML dashboard")
                return self._json(200, {"ok": True, "message": "Trading paused."})
            return self._json(202, {"ok": False, "message": "Risk manager unavailable in fallback mode."})

        if action == "resume_trading":
            if risk_manager is not None:
                risk_manager.manual_resume()
                return self._json(200, {"ok": True, "message": "Trading resumed."})
            return self._json(202, {"ok": False, "message": "Risk manager unavailable in fallback mode."})

        if action == "start_bot":
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        if action == "stop_bot":
            ok, msg = stop_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        if action == "restart_bot":
            stop_bot_process()
            # light delay to reduce duplicate-start races
            try:
                import time
                time.sleep(2)
            except Exception:
                pass
            if is_bot_running():
                return self._json(400, {"ok": False, "message": "Bot still running after stop; restart aborted."})
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": f"Restart requested. {msg}"})

        if action == "refresh_scan":
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})

        if action == "close_position":
            position_id = data.get("position_id")
            if position_id is None:
                return self._json(400, {"ok": False, "message": "position_id is required"})
            ok, msg = close_position(position_id)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        return self._json(400, {"error": f"Unknown action: {action}"})


if __name__ == "__main__":
    print(f"Starting HTML dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    print(f"Using DB path: {DB_PATH}", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    print(f"Serving HTML dashboard at http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server.serve_forever()
