"""HTML dashboard bridge.

Run: python web_dashboard.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
HTML_ROOT = ROOT / "Html-Files"
if not HTML_ROOT.exists():
    HTML_ROOT = ROOT / "HTML-Files"

_config = None
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
monitor = None
_close_lock = threading.Lock()
_close_requests = {}

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

try:
    from core.position_monitor import monitor as _monitor
    monitor = _monitor
except Exception:
    monitor = None


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


def open_project_terminal():
    """Open an interactive PowerShell rooted in the trading bot workspace."""
    try:
        if sys.platform == "win32":
            CREATE_NEW_CONSOLE = 0x00000010
            root = str(ROOT.resolve()).replace("'", "''")
            command = (
                f"Set-Location -LiteralPath '{root}'; "
                "$Host.UI.RawUI.WindowTitle = 'Trading Bot Workspace Shell'; "
                "Write-Host 'Trading bot workspace shell ready.' -ForegroundColor Cyan; "
                "Write-Host 'Root: ' -NoNewline -ForegroundColor DarkGray; "
                "Write-Host (Get-Location).Path; "
                "Write-Host 'Try: Get-Content .\\logs\\bot.log -Tail 80 -Wait' -ForegroundColor DarkGray"
            )
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-Command",
                    command,
                ],
                cwd=str(ROOT),
                creationflags=CREATE_NEW_CONSOLE,
            )
            return True, "PowerShell opened in the trading bot workspace."

        shell = os.environ.get("SHELL", "/bin/sh")
        subprocess.Popen([shell], cwd=str(ROOT))
        return True, "Shell opened in the trading bot workspace."
    except Exception as exc:
        return False, f"Failed to open PowerShell: {exc}"


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


def sort_open_positions(rows, sort_by=None, sort_dir="desc"):
    key_map = {
        "opened": "entry_time",
        "symbol": "symbol",
        "type": "asset_class",
        "dir": "direction",
        "entry": "entry_price",
        "current": "current_price",
        "sl": "stop_loss",
        "tp": "take_profit",
        "pnlD": "unrealized_pnl",
        "pnlP": "pnl_pct",
        "toSL": "distance_to_sl",
        "toTP": "distance_to_tp",
    }
    field = key_map.get(sort_by or "opened", "entry_time")
    reverse = str(sort_dir or "desc").lower() != "asc"

    def value(row):
        raw = row.get(field)
        if field in ("asset_class", "direction", "entry_time", "symbol"):
            return str(raw or "").lower()
        try:
            return float(raw or 0)
        except Exception:
            return 0.0

    return sorted(rows, key=value, reverse=reverse)


def get_open_positions(sort_by=None, sort_dir="desc", enrich=True):
    """Return open positions using DB adapter when available, else SQLite fallback."""
    if enrich and monitor is not None:
        try:
            rows = monitor.get_positions_summary() or []
            positions = [
                {
                    "id": t.get("id"),
                    "trade_id": t.get("trade_id"),
                    "symbol": t.get("symbol") or t.get("ticker") or "?",
                    "asset_class": t.get("asset_class") or "crypto",
                    "side": t.get("direction") or t.get("side") or "long",
                    "direction": t.get("direction") or t.get("side") or "long",
                    "qty": float(t.get("quantity") or t.get("shares") or 0),
                    "entry_price": float(t.get("entry_price") or 0),
                    "current_price": float(t.get("current_price") or t.get("entry_price") or 0),
                    "stop_loss": float(t.get("stop_loss") or t.get("entry_price") or 0),
                    "take_profit": float(t.get("take_profit") or t.get("entry_price") or 0),
                    "unrealized_pnl": float(t.get("unrealized_pnl") or 0),
                    "pnl_pct": float(t.get("pnl_pct") or 0),
                    "distance_to_sl": float(t.get("distance_to_sl") or 0),
                    "distance_to_tp": float(t.get("distance_to_tp") or 0),
                    "entry_time": t.get("entry_time") or "",
                    "age_hours": float(t.get("age_hours") or 0),
                    "is_stuck": bool(t.get("is_stuck")),
                    "close_attempts": int(t.get("close_attempts") or 0),
                    "tp_hit_count": int(t.get("tp_hit_count") or 0),
                }
                for t in rows
            ]
            return sort_open_positions(positions, sort_by, sort_dir)
        except Exception:
            pass

    if db is not None:
        try:
            rows = db.get_open_trades() or []
            positions = []
            for t in rows:
                entry_price = float(t.get("entry_price") or 0)
                if enrich:
                    current_price = get_current_price(
                        t.get("symbol") or t.get("ticker") or "?",
                        t.get("asset_class") or "crypto",
                    ) or entry_price
                else:
                    current_price = float(t.get("current_price") or entry_price or 0)
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
            return sort_open_positions(positions, sort_by, sort_dir)
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
 #       conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
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
        positions = [
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
        return sort_open_positions(positions, sort_by, sort_dir)
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


def request_close_position(position_id):
    """Start a manual close in the background so the dashboard stays usable."""
    key = str(position_id)
    with _close_lock:
        if key in _close_requests:
            return True, f"Close already in progress for position {position_id}."
        _close_requests[key] = datetime.now()

    def worker():
        try:
            ok, msg = close_position(position_id)
            status = "OK" if ok else "FAILED"
            print(f"[manual close {status}] position={position_id}: {msg}", flush=True)
        except Exception as exc:
            print(f"[manual close ERROR] position={position_id}: {exc}", flush=True)
        finally:
            with _close_lock:
                _close_requests.pop(key, None)

    thread = threading.Timer(0.25, worker)
    thread.name = f"manual-close-{key}"
    thread.daemon = True
    thread.start()
    return True, f"Close requested for position {position_id}; broker close is running in the background."


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


def get_manual_trade_config():
    brokers = ["alpaca", "coinbase", "kraken", "paper"]
    if getattr(_config, "IBKR_ENABLED", False):
        brokers.insert(0, "ibkr")
    return {
        "brokers": brokers,
        "default_broker": brokers[0],
        "asset_classes": ["stock", "crypto"],
        "directions": ["long", "short"],
        "default_size": 2000.0,
        "default_stop_loss_pct": 1.5,
        "default_take_profit_pct": 3.0,
        "default_strategy": "manual",
    }


# Cancel flag — set by POST /api/backtest/cancel, checked in the inner run loop.
# Cleared at the start of every new run so stale signals don't bleed through.
_bt_cancel = threading.Event()
_bt_running = threading.Event()

BACKTEST_STRATEGIES = [
    "adaptive_regime", "rsi_momentum", "bollinger_breakout", "ema_crossover",
    "mean_reversion", "scalp_master", "swing_trader", "grid_bot",
    "dca_accumulator", "vwap_momentum", "hammer_reversal", "orb_breakout",
    "ecb_strategy", "vdmr_strategy", "rsi_dip_spike_v4",
    "original_scorer", "vwap_confirmed_orb",
]


def _parse_backtest_days(raw):
    text = str(raw or "90").strip().lower()
    if text in ("1y", "1yr", "1 year"):
        return 365
    if text in ("2y", "2yr", "2 years"):
        return 730
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    return max(1, int(digits[0])) if digits else 90


def _load_watchlist_file(path):
    try:
        p = ROOT / path
        if not p.exists():
            return []
        return [
            line.strip() for line in p.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    except Exception:
        return []


def _unique_symbols(symbols, crypto=False):
    seen = set()
    out = []
    for raw in symbols or []:
        symbol = str(raw or "").strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        if crypto and "/" not in symbol:
            symbol = f"{symbol}/USD"
        if not crypto and ("/" in symbol or "-" in symbol):
            continue
        if symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def get_backtest_config():
    try:
        import config as cfg
    except Exception:
        cfg = None

    stock_symbols = []
    crypto_symbols = []
    if cfg is not None:
        stock_symbols.extend(getattr(cfg, "STOCK_WATCHLIST", []) or [])
        crypto_symbols.extend(getattr(cfg, "CRYPTO_WATCHLIST", []) or [])

    stock_symbols.extend(_load_watchlist_file("watchlists/stocks.txt"))
    stock_symbols.extend(_load_watchlist_file("watchlist/scanned_stocks.txt"))
    crypto_symbols.extend(_load_watchlist_file("watchlists/crypto.txt"))
    crypto_symbols.extend(_load_watchlist_file("watchlist/scanned_crypto.txt"))

    stocks = _unique_symbols(stock_symbols, crypto=False)
    crypto = _unique_symbols(crypto_symbols, crypto=True)
    return {
        "asset_classes": ["Stocks", "Crypto"],
        "strategies": ["ALL strategies", *BACKTEST_STRATEGIES],
        "timeframes": ["5m", "1h", "1d"],
        "durations": ["30d", "60d", "90d (3mo)", "180d (6mo)", "365d (1y)", "730d (2y)"],
        "symbols": {
            "Stocks": ["ALL", *stocks],
            "Crypto": ["ALL", *crypto],
        },
        "counts": {"stocks": len(stocks), "crypto": len(crypto)},
    }


def _backtest_result_payload(result):
    trades = list(getattr(result, "trades", []) or [])
    wins = [t for t in trades if getattr(t, "pnl", 0) > 0]
    losses = [t for t in trades if getattr(t, "pnl", 0) <= 0]
    avg_win = sum(float(getattr(t, "pnl", 0) or 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(float(getattr(t, "pnl", 0) or 0) for t in losses) / len(losses) if losses else 0
    start_cap = float(getattr(result, "starting_capital", 0) or 0)
    end_cap = float(getattr(result, "ending_capital", start_cap) or start_cap)
    start_date = getattr(result, "start_date", "")
    end_date = getattr(result, "end_date", "")
    stop_mode = getattr(result, "stop_mode", "") or (getattr(trades[0], "stop_mode", "") if trades else "") or "standard"
    win_rate = float(getattr(result, "win_rate", 0) or 0)
    profit_factor = float(getattr(result, "profit_factor", 0) or 0)
    max_drawdown = float(getattr(result, "max_drawdown_pct", 0) or 0)
    verdict = "GO" if win_rate >= 50 and profit_factor >= 1.2 and max_drawdown > -25 else "TUNE"
    equity_curve = list(getattr(result, "equity_curve", []) or [])
    sample_step = max(1, len(equity_curve) // 500)
    sampled_equity = [
        {
            "t": str(getattr(ep, "timestamp", ""))[:16],
            "e": float(getattr(ep, "equity", 0) or 0),
            "d": float(getattr(ep, "drawdown", 0) or 0),
            "r": float(getattr(ep, "daily_ret", 0) or 0),
        }
        for ep in equity_curve[::sample_step]
    ]
    return {
        "symbol": getattr(result, "symbol", ""),
        "strategy": getattr(result, "strategy_name", ""),
        "timeframe": getattr(result, "timeframe", ""),
        "stop_mode": stop_mode,
        "stop": "2-Bar" if str(stop_mode).lower() in ("two_bar", "trailing") else "Standard",
        "start_date": start_date,
        "end_date": end_date,
        "period": f"{str(start_date)[:10]} -> {str(end_date)[:10]}",
        "starting_capital": start_cap,
        "ending_capital": end_cap,
        "wins": len(wins),
        "losses": len(losses),
        "wl": f"{len(wins)}W/{len(losses)}L",
        "verdict": verdict,
        "totalTrades": int(getattr(result, "total_trades", 0) or 0),
        "winRate": win_rate,
        "pnlD": round(end_cap - start_cap, 2),
        "pnlP": float(getattr(result, "total_return_pct", 0) or 0),
        "sharpe": float(getattr(result, "sharpe_ratio", 0) or 0),
        "sortino": float(getattr(result, "sortino_ratio", 0) or 0),
        "maxDD": max_drawdown,
        "profitFactor": profit_factor,
        "avgWin": round(avg_win, 2),
        "avgLoss": round(avg_loss, 2),
        "equity_curve": sampled_equity,
    }


def run_backtest_api(payload):
    try:
        from intelligence.backtester import Backtester
        import config as cfg
    except Exception as exc:
        return False, f"Backtester unavailable: {exc}", {}

    asset = str(payload.get("asset") or "Stocks")
    symbol = str(payload.get("symbol") or "ALL").strip()
    strategy = str(payload.get("strategy") or "ALL strategies").strip()
    timeframe = str(payload.get("tf") or payload.get("timeframe") or "1h").strip()
    days = _parse_backtest_days(payload.get("duration") or payload.get("days"))
    capital = float(payload.get("cap") or payload.get("capital") or getattr(cfg, "STARTING_CAPITAL", 100000))
    stop_mode = "two_bar" if str(payload.get("mode") or "").lower() in ("trailing", "two_bar") else "standard"
    lookback = max(1, int(float(payload.get("lookback") or 2)))
    entry_side_filter = str(payload.get("side")         or "all").strip().lower()
    entry_mode_filter = str(payload.get("entry_mode")   or "all").strip().lower()
    initial_stop_mode = str(payload.get("initial_stop") or "auto").strip().lower()
    trail_mode        = str(payload.get("trail")        or "auto").strip().lower()
    _commission_raw   = payload.get("commission")
    _slippage_raw     = payload.get("slippage")
    commission_pct    = float(_commission_raw) if _commission_raw not in (None, "", "default") else None
    slippage_pct      = float(_slippage_raw)   if _slippage_raw   not in (None, "", "default") else None

    asset_class = "crypto" if asset.lower().startswith("crypto") or "/" in symbol else "stock"
    if asset_class == "crypto":
        if symbol.upper() == "ALL":
            symbols = [s for s in get_backtest_config()["symbols"]["Crypto"] if s != "ALL"]
        else:
            symbols = _unique_symbols([symbol], crypto=True)
    else:
        if symbol.upper() == "ALL":
            symbols = [s for s in get_backtest_config()["symbols"]["Stocks"] if s != "ALL"]
        else:
            symbols = _unique_symbols([symbol.upper()], crypto=False)
    strategies = BACKTEST_STRATEGIES if strategy == "ALL strategies" else [strategy]

    if not symbols:
        return False, "No symbols selected for backtest.", {}

    # Clear any stale cancel signals from a previous run
    _bt_cancel.clear()
    _bt_running.set()
    try:
        from intelligence.backtester import clear_cancel
        clear_cancel()
    except Exception:
        pass

    results = []
    skipped = 0
    was_cancelled = False
    try:
        bt = Backtester(starting_capital=capital)
        for strat in strategies:
            if _bt_cancel.is_set():
                break
            for sym in symbols:
                if _bt_cancel.is_set():
                    break
                try:
                    if strat == "original_scorer":
                        result = bt.run(
                            sym, days, capital, timeframe, asset_class=asset_class,
                            stop_mode=stop_mode, two_bar_lookback=lookback,
                            commission_pct=commission_pct, slippage_pct=slippage_pct,
                            initial_stop_mode=initial_stop_mode, trail_mode=trail_mode,
                            entry_mode_filter=entry_mode_filter,
                            entry_side_filter=entry_side_filter,
                        )
                    else:
                        result = bt.run_strategy(
                            sym, strat, days, capital, timeframe, asset_class=asset_class,
                            stop_mode=stop_mode, two_bar_lookback=lookback,
                            commission_pct=commission_pct, slippage_pct=slippage_pct,
                            initial_stop_mode=initial_stop_mode, trail_mode=trail_mode,
                            entry_mode_filter=entry_mode_filter,
                            entry_side_filter=entry_side_filter,
                        )
                    if result and getattr(result, "total_trades", 0) > 0:
                        results.append(_backtest_result_payload(result))
                    else:
                        skipped += 1
                except Exception as _exc:
                    if type(_exc).__name__ == "_BacktestCancelled":
                        # Inner-loop cancel checkpoint fired — treat as cancelled
                        _bt_cancel.set()
                        break
                    skipped += 1

        was_cancelled = _bt_cancel.is_set()
    finally:
        _bt_running.clear()
        _bt_cancel.clear()

    if not results:
        if was_cancelled:
            return True, f"Cancelled — no runs completed.", {
                "skipped": skipped,
                "requested_runs": len(symbols) * len(strategies),
                "cancelled": True,
            }
        return False, f"No results; {skipped} run(s) had insufficient data or no trades.", {
            "skipped": skipped,
            "requested_runs": len(symbols) * len(strategies),
            "cancelled": False,
        }

    total_trades = sum(r["totalTrades"] for r in results)
    total_wins = sum(round(r["totalTrades"] * r["winRate"] / 100) for r in results)
    summary = {
        "totalTrades": total_trades,
        "winRate": round((total_wins / total_trades * 100) if total_trades else 0, 1),
        "pnlD": round(sum(r["pnlD"] for r in results), 2),
        "pnlP": round(sum(r["pnlP"] for r in results) / len(results), 2),
        "sharpe": round(sum(r["sharpe"] for r in results) / len(results), 2),
        "maxDD": round(sum(r["maxDD"] for r in results) / len(results), 2),
        "profitFactor": round(sum(r["profitFactor"] for r in results) / len(results), 2),
        "avgWin": round(sum(r["avgWin"] for r in results) / len(results), 2),
        "avgLoss": round(sum(r["avgLoss"] for r in results) / len(results), 2),
    }
    complete_msg = (
        f"Cancelled — partial results: {len(results)} run(s) completed, {skipped} skipped."
        if was_cancelled
        else f"Backtest complete: {len(results)} result(s), {skipped} skipped."
    )
    return True, complete_msg, {
        **summary,
        "results": results,
        "skipped": skipped,
        "requested_runs": len(symbols) * len(strategies),
        "cancelled": was_cancelled,
    }


def get_manual_trade_preview(params):
    symbol = (params.get("symbol") or [""])[0].strip().upper()
    asset_class = (params.get("asset") or params.get("asset_class") or ["stock"])[0].lower()
    direction = (params.get("dir") or params.get("direction") or ["long"])[0].lower()
    if not symbol:
        return False, "Symbol is required.", {}
    try:
        position_size = float((params.get("size") or params.get("position_size") or ["0"])[0] or 0)
        sl_pct = float((params.get("sl") or params.get("stop_loss_pct") or ["1.5"])[0] or 1.5)
        tp_pct = float((params.get("tp") or params.get("take_profit_pct") or ["3.0"])[0] or 3.0)
    except Exception:
        return False, "Position size, stop loss, and take profit must be numeric.", {}
    if asset_class not in ("stock", "crypto"):
        return False, f"Unsupported asset class: {asset_class}", {}
    if direction not in ("long", "short"):
        return False, f"Unsupported direction: {direction}", {}
    if position_size <= 0:
        return False, "Position size must be greater than 0.", {}

    entry = get_current_price(symbol, asset_class)
    if not entry:
        return False, f"Could not fetch live price for {symbol}.", {}
    if direction == "long":
        sl = entry * (1 - sl_pct / 100)
        tp = entry * (1 + tp_pct / 100)
    else:
        sl = entry * (1 + sl_pct / 100)
        tp = entry * (1 - tp_pct / 100)
    return True, "Preview ready.", {
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": direction,
        "entry_price": float(entry),
        "stop_loss": float(sl),
        "take_profit": float(tp),
        "quantity": float(position_size / entry),
        "position_size": position_size,
    }


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


# ---------------------------------------------------------------------------
# Chart panel data — OHLCV bars + bot trade markers
# ---------------------------------------------------------------------------

_CHART_TF_ALPACA = {
    '1m': '1Min', '5m': '5Min', '15m': '15Min', '30m': '30Min',
    '1h': '1Hour', '4h': '4Hour', '1D': '1Day', '1W': '1Week',
}
_CHART_TF_CCXT = {
    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '1h', '4h': '4h', '1D': '1d', '1W': '1w',
}


def _chart_bars_alpaca(symbol, timeframe, limit):
    try:
        import alpaca_trade_api as tradeapi
        if not _config:
            return []
        api = tradeapi.REST(_config.ALPACA_API_KEY, _config.ALPACA_SECRET_KEY, _config.ALPACA_BASE_URL)
        tf  = _CHART_TF_ALPACA.get(timeframe, '5Min')
        raw = api.get_bars(symbol, tf, limit=limit, adjustment='raw').df
        if raw.empty:
            return []
        # Flatten MultiIndex columns (newer alpaca-trade-api versions)
        if hasattr(raw.columns, 'levels'):
            raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        bars = []
        for ts, r in raw.iterrows():
            try:
                bars.append({
                    'time': int(ts.timestamp()),
                    'open': float(r['open']), 'high': float(r['high']),
                    'low':  float(r['low']),  'close': float(r['close']),
                    'volume': float(r.get('volume', 0)),
                })
            except Exception:
                continue
        return bars
    except Exception as e:
        import logging; logging.getLogger(__name__).warning(f"[chart/alpaca] {symbol}: {e}")
        return []


def _chart_bars_ibkr(symbol, timeframe, limit):
    # Reuse the bot's live executor singleton — don't create a new connection
    # per chart request (wastes clientIds and triggers event-loop errors).
    try:
        from core.trade_executor import executor as _tex
        ibkr = getattr(_tex, '_ibkr', None)
        if ibkr and ibkr.is_available():
            return ibkr.get_historical_bars(symbol, timeframe, limit)
    except Exception:
        pass
    # Fallback: yfinance (no connection needed)
    return _chart_bars_yfinance(symbol, timeframe, limit)


def _chart_bars_kraken(symbol, timeframe, limit):
    try:
        import json as _json
        import logging
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        interval = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1D': 1440, '1W': 10080,
        }.get(timeframe, 5)
        pair = symbol.replace('/', '').replace('-', '').upper()
        if pair.startswith('BTC'):
            pair = pair.replace('BTC', 'XBT', 1)

        url = 'https://api.kraken.com/0/public/OHLC?' + urlencode({
            'pair': pair,
            'interval': interval,
        })
        req = Request(url, headers={'User-Agent': 'trading-bot-dashboard/1.0'})
        with urlopen(req, timeout=6) as resp:
            payload = _json.loads(resp.read().decode('utf-8'))
        if payload.get('error'):
            logging.getLogger(__name__).warning(f"[chart/kraken] {symbol}: {payload['error']}")
            return []
        result = payload.get('result') or {}
        data_key = next((k for k in result.keys() if k != 'last'), None)
        rows = result.get(data_key) or []
        rows = rows[-limit:]
        return [
            {'time': int(r[0]), 'open': float(r[1]), 'high': float(r[2]),
             'low': float(r[3]), 'close': float(r[4]), 'volume': float(r[6])}
            for r in rows
        ]
    except Exception as e:
        logging.getLogger(__name__).warning(f"[chart/kraken] {symbol}: {e}")
        return []


def _chart_bars_coinbase(symbol, timeframe, limit):
    try:
        import logging
        import ccxt
        exc  = ccxt.coinbase({'enableRateLimit': True, 'timeout': 5000})
        tf   = _CHART_TF_CCXT.get(timeframe, '5m')
        rows = exc.fetch_ohlcv(symbol, tf, limit=limit)
        return [
            {'time': int(ts // 1000), 'open': float(o), 'high': float(h),
             'low': float(l), 'close': float(c), 'volume': float(v)}
            for ts, o, h, l, c, v in rows
        ]
    except Exception as e:
        logging.getLogger(__name__).warning(f"[chart/coinbase] {symbol}: {e}")
        return []


def _chart_bars_yfinance(symbol, timeframe, limit):
    try:
        import yfinance as yf
        from datetime import timedelta
        # yfinance uses BTC-USD format for crypto
        yfSym = symbol.replace('/', '-')
        _interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '1h', '1D': '1d', '1W': '1wk',
        }
        interval = _interval_map.get(timeframe, '5m')
        # Approximate period needed
        mins_per_bar = {'1m':1,'5m':5,'15m':15,'30m':30,'1h':60,'4h':240,'1D':1440,'1W':10080}.get(timeframe,5)
        total_days = max(2, (mins_per_bar * limit) // 1440 + 1)
        period_str = f"{min(total_days, 729)}d" if interval not in ('1d','1wk') else f"{min(total_days*2, 1800)}d"
        raw = yf.download(
            yfSym,
            period=period_str,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
            timeout=6,
        )
        if raw.empty:
            return []
        # yfinance 0.2.x returns MultiIndex columns for single symbols: ('Open','TSLA')
        # Flatten so row['Open'] works instead of requiring row[('Open','TSLA')]
        if hasattr(raw.columns, 'levels'):
            raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        bars = []
        for ts, row in raw.iterrows():
            try:
                t = int(ts.timestamp())
                bars.append({'time': t, 'open': float(row['Open']), 'high': float(row['High']),
                             'low': float(row['Low']), 'close': float(row['Close']),
                             'volume': float(row.get('Volume', 0))})
            except Exception:
                continue
        return bars[-limit:]
    except Exception:
        return []


def get_chart_data(symbol, timeframe='5m', limit=300, broker=None):
    symbol = symbol.upper().strip()
    is_crypto = '/' in symbol
    try:
        limit = max(50, min(int(limit), 1000))
    except Exception:
        limit = 300

    # Default broker by asset type
    if not broker:
        broker = 'kraken' if is_crypto else 'alpaca'

    _fetchers = {
        'alpaca':   _chart_bars_alpaca,
        'ibkr':     _chart_bars_ibkr,
        'kraken':   _chart_bars_kraken,
        'coinbase': _chart_bars_coinbase,
        'yfinance': _chart_bars_yfinance,
    }
    fetch = _fetchers.get(broker, _chart_bars_alpaca if not is_crypto else _chart_bars_kraken)
    bars = fetch(symbol, timeframe, limit)

    # Fallback if chosen broker returns nothing
    if not bars:
        if is_crypto:
            fallback = _chart_bars_yfinance if fetch is not _chart_bars_yfinance else None
        else:
            # yfinance is the universal stock fallback — don't retry Alpaca on Alpaca failure
            fallback = _chart_bars_yfinance if fetch is not _chart_bars_yfinance else None
        if fallback:
            bars = fallback(symbol, timeframe, limit)

    # Sort ascending — required by Lightweight Charts
    bars.sort(key=lambda b: b['time'])

    # Deduplicate — Alpaca/yfinance can emit two bars at the same timestamp
    # (e.g. DST boundary, or bar-boundary off-by-one).  LightweightCharts v4
    # aborts setData on CandlestickSeries if any duplicate timestamp exists.
    seen_t: set = set()
    deduped = []
    for b in bars:
        if b['time'] not in seen_t:
            seen_t.add(b['time'])
            deduped.append(b)
    bars = deduped

    # Trade markers for this symbol
    markers = []
    try:
        if db:
            trades = db.get_all_closed_trades(limit=500)
            for t in trades:
                if (t.get('symbol') or '').upper() != symbol:
                    continue
                entry_time = t.get('entry_time')
                if entry_time:
                    try:
                        et = datetime.fromisoformat(entry_time)
                        markers.append({
                            'time': int(et.timestamp()), 'type': 'entry',
                            'direction': t.get('direction', 'long'),
                            'price': float(t.get('entry_price', 0)),
                            'pnl': 0,
                        })
                    except Exception:
                        pass
                exit_time = t.get('exit_time')
                exit_price = t.get('exit_price')
                if exit_time and exit_price:
                    try:
                        xt = datetime.fromisoformat(exit_time)
                        pnl = float(t.get('pnl', 0) or 0)
                        markers.append({
                            'time': int(xt.timestamp()), 'type': 'exit',
                            'direction': t.get('direction', 'long'),
                            'price': float(exit_price), 'pnl': pnl,
                        })
                    except Exception:
                        pass
    except Exception:
        pass

    markers.sort(key=lambda m: m['time'])
    return {'bars': bars, 'markers': markers, 'symbol': symbol, 'timeframe': timeframe}


def get_chart_symbols():
    stocks = list(getattr(_config, 'STOCK_WATCHLIST', []) or [])
    crypto = list(getattr(_config, 'CRYPTO_WATCHLIST', []) or [])
    try:
        inj = get_injected_symbols()
        stocks = list(dict.fromkeys(stocks + inj.get('stocks', [])))
        crypto = list(dict.fromkeys(crypto + inj.get('crypto', [])))
    except Exception:
        pass
    return (
        [{'symbol': s, 'type': 'stock'} for s in stocks] +
        [{'symbol': s, 'type': 'crypto'} for s in crypto]
    )


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
        "files": {
            "stocks": str(INJECTED_STOCKS_FILE),
            "crypto": str(INJECTED_CRYPTO_FILE),
        },
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
 #           conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            trades = [dict(r) for r in conn.execute(
                "SELECT * FROM trades WHERE status='closed' AND date(exit_time)=? ORDER BY exit_time",
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
            "id": trade.get("id"),
            "trade_id": trade.get("trade_id"),
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
            "tp_hit_count": int(trade.get("tp_hit_count") or 0),
            "_sort": trade.get("exit_time") or "",
        })

    rows.sort(key=lambda row: row["_sort"], reverse=True)
    for row in rows:
        row.pop("_sort", None)
    return rows


def get_overview_data():
    if db is None:
        return {}

    try:
        status = risk_manager.get_daily_status() if risk_manager else None
    except Exception:
        status = None

    cap = db.get_latest_capital() or {}
    open_trades = db.get_open_trades() or []
    closed_today = get_today_trade_log()
    wins_today = sum(1 for trade in closed_today if float(trade.get("pnl") or 0) > 0)
    losses_today = sum(1 for trade in closed_today if float(trade.get("pnl") or 0) <= 0)
    closed_trade_count = len(closed_today)
    win_rate = (wins_today / closed_trade_count * 100) if closed_trade_count else 0

    daily_summaries = db.get_daily_summaries(370) or []
    daily_perf = [
        {
            "date": s.get("trade_date"),
            "trades": int(s.get("total_trades") or 0),
            "wins": int(s.get("winning_trades") or 0),
            "losses": int(s.get("losing_trades") or 0),
            "win_rate": float(s.get("win_rate") or 0),
            "pnl": float(s.get("daily_pnl") or 0),
            "pnl_pct": float(s.get("daily_pnl_pct") or 0),
            "capital": float(s.get("ending_capital") or 0),
            "goal_met": bool(s.get("goal_met")),
            "trading_halted": bool(s.get("trading_halted")),
        }
        for s in daily_summaries
    ]

    capital_history = [
        {
            "date": row["date"],
            "capital": row["capital"],
        }
        for row in reversed([
            {"date": s.get("trade_date"), "capital": float(s.get("ending_capital") or 0)}
            for s in daily_summaries
            if s.get("trade_date")
        ])
    ]
    if cap:
        today = date.today().isoformat()
        current_capital = float(cap.get("total_capital") or 0)
        if not capital_history or capital_history[-1]["date"] != today:
            capital_history.append({"date": today, "capital": current_capital})

    if status:
        trading_active = bool(status.trading_active)
        halt_reason = status.halt_reason or ""
        daily_pnl = float(status.pnl_today or 0)
        daily_pnl_pct = float(status.pnl_pct_today or 0)
        consecutive_losses = int(status.consecutive_losses or 0)
        status_trades_today = int(status.trades_today or 0)
        capital = float(status.capital or cap.get("total_capital") or 0)
        starting_capital_today = float(status.starting_capital_today or 0)
    else:
        session = db.get_session(date.today().isoformat()) or {}
        trading_active = not bool(session.get("trading_halted", 0))
        halt_reason = session.get("halt_reason") or ""
        daily_pnl = float(session.get("pnl_today") or 0)
        starting_capital_today = float(session.get("starting_capital_today") or 0)
        daily_pnl_pct = (daily_pnl / starting_capital_today * 100) if starting_capital_today else 0
        consecutive_losses = int(session.get("consecutive_losses") or 0)
        status_trades_today = int(session.get("trades_today") or 0)
        capital = float(cap.get("total_capital") or 0)

    return {
        "trading_active": trading_active,
        "halt_reason": halt_reason,
        "bot_process_running": is_bot_running(),
        "capital": capital,
        "available_cash": float(cap.get("available_cash") or 0),
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "open_positions": len(open_trades),
        "trades_today": closed_trade_count,        # matches Trade Log count
        "session_trades_today": status_trades_today, # session counter (since last bot start)
        "closed_trades_today": closed_trade_count,
        "wins_today": wins_today,
        "losses_today": losses_today,
        "win_rate_today": win_rate,
        "consecutive_losses": consecutive_losses,
        "capital_history": capital_history,
        "daily_performance": daily_perf,
    }


def get_quick_status(year=None):
    year = int(year or date.today().year)
    status = {}

    try:
        from intelligence.ml_scorer import ml_scorer
        status["ml"] = ml_scorer.get_status()
    except Exception:
        status["ml"] = {"stage": "unknown", "progress_pct": 0, "message": "ML scorer initializing."}

    try:
        status["tax"] = db.get_tax_year_summary(year) if db is not None else {}
    except Exception:
        status["tax"] = {}

    try:
        from intelligence.condition_detector import condition_detector
        from scanners.market_scanner import scanner
        cond = condition_detector.get_spy_condition(scanner.stock_scanner)
        status["market_condition"] = {
            "condition": getattr(cond.condition, "value", str(cond.condition)),
            "confidence": float(cond.confidence or 0),
            "position_scalar": float(cond.position_scalar or 0),
            "should_trade": bool(cond.should_trade),
            "reason": cond.reason,
            "adx": float(cond.adx or 0),
            "atr_pct": float(cond.atr_pct or 0),
            "bb_width": float(cond.bb_width or 0),
        }
    except Exception:
        status["market_condition"] = {
            "condition": "unknown",
            "confidence": 0,
            "position_scalar": 0,
            "should_trade": True,
            "reason": "Condition detector initializing.",
            "adx": 0,
            "atr_pct": 0,
            "bb_width": 0,
        }

    status["year"] = year
    return status


def generate_daily_report():
    try:
        from reporting.report_generator import ReportGenerator

        generator = ReportGenerator()
        summary = generator.generate_daily_summary()
        if db is not None:
            db.save_daily_summary(summary)
        return True, "Daily report generated and saved.", {"summary": summary}
    except Exception as exc:
        return False, f"Report generation failed: {exc}", {}


def export_tax_csv(year):
    try:
        year = int(year or date.today().year)
        exports = ROOT / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        filepath = exports / f"tax_form_8949_{year}.csv"
        db.export_8949_csv(year, str(filepath))
        return True, f"Saved: {filepath}", {"path": str(filepath)}
    except Exception as exc:
        return False, f"Tax export failed: {exc}", {}


def process_withdrawal(amount, reason):
    try:
        result = risk_manager.process_withdrawal(float(amount or 0), str(reason or "Living expenses"))
        return bool(result.get("approved")), result.get("message", "Withdrawal processed."), result
    except Exception as exc:
        return False, f"Withdrawal failed: {exc}", {}


def retrain_ml():
    try:
        from intelligence.ml_scorer import ml_scorer

        success = bool(ml_scorer.retrain())
        msg = "Retrain complete." if success else "Retrain skipped: not enough closed trades yet."
        return True, msg, {"ml": ml_scorer.get_status()}
    except Exception as exc:
        return False, f"ML retrain failed: {exc}", {}


def chat_with_bot(message):
    text = str(message or "").strip()
    if not text:
        return False, "Message is required.", {}
    try:
        from intelligence.chat_interface import chat

        reply = chat.chat(text)
        return True, reply, {"reply": reply}
    except Exception as exc:
        return False, f"Chat failed: {exc}", {}


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
        try:
            session = db.get_session(date.today().isoformat()) or {}
        except Exception:
            session = {}
        halted = bool(session.get("trading_halted", 0))
        halt_reason = session.get("halt_reason") or ""
        return {
            "bot_status": "PAUSED" if halted else "ACTIVE",
            "trading_active": not halted,
            "halt_reason": halt_reason,
            "open_positions": len(open_trades),
            "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
            "bot_process_running": is_bot_running(),
            "snapshot_source": "live_db_adapter",
            "db_path": str(DB_PATH),
        }

    try:
        conn = sqlite3.connect(DB_PATH)
 #       conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
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
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass  # Client disconnected mid-response — harmless

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/hello":
            return self._json(200, {"message": "hello world"})

        if path == "/api/snapshot":
            return self._json(200, build_snapshot())

        if path == "/api/open_positions":
            params = parse_qs(parsed.query)
            sort_by = (params.get("sort_by") or ["opened"])[0]
            sort_dir = (params.get("sort_dir") or ["desc"])[0]
            return self._json(200, {
                "positions": get_open_positions(sort_by, sort_dir),
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "db_path": str(DB_PATH),
            })

        if path == "/api/chart":
            params = parse_qs(parsed.query)
            symbol    = (params.get("symbol")    or ["BTC/USD"])[0].strip()
            timeframe = (params.get("timeframe") or ["5m"])[0].strip()
            limit     = (params.get("limit")     or ["300"])[0].strip()
            broker    = (params.get("broker")    or [""])[0].strip().lower() or None
            try:
                return self._json(200, get_chart_data(symbol, timeframe, limit, broker))
            except Exception as _ce:
                import logging as _lg
                _lg.getLogger(__name__).error(f"[/api/chart] {symbol} crashed: {_ce}", exc_info=True)
                return self._json(200, {"bars": [], "markers": [], "symbol": symbol, "error": str(_ce)})

        if path == "/api/chart/symbols":
            return self._json(200, {"symbols": get_chart_symbols()})

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

        if path == "/api/overview":
            return self._json(200, get_overview_data())

        if path == "/api/quick_status":
            params = parse_qs(parsed.query)
            year = (params.get("year") or [date.today().year])[0]
            return self._json(200, get_quick_status(year))

        if path == "/api/manual_trade/config":
            return self._json(200, get_manual_trade_config())

        if path == "/api/backtest/config":
            return self._json(200, get_backtest_config())

        if path == "/api/manual_trade/preview":
            ok, msg, details = get_manual_trade_preview(parse_qs(parsed.query))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

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

        if path == "/api/report/daily":
            ok, msg, details = generate_daily_report()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/tax/export":
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            ok, msg, details = export_tax_csv(data.get("year"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/withdrawal":
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            ok, msg, details = process_withdrawal(data.get("amount"), data.get("reason"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/ml/retrain":
            ok, msg, details = retrain_ml()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/backtest/cancel":
            running = _bt_running.is_set()
            _bt_cancel.set()
            try:
                from intelligence.backtester import request_cancel
                request_cancel()
            except Exception:
                pass
            msg = "Cancel signal sent — waiting for next backtest checkpoint." if running else "Cancel signal set; no active backtest was marked running."
            return self._json(200, {"ok": True, "running": running, "message": msg})

        if path == "/api/backtest":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                return self._json(400, {"ok": False, "message": f"Invalid JSON: {exc.msg}"})
            ok, msg, details = run_backtest_api(data)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/chat":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                return self._json(400, {"ok": False, "message": f"Invalid JSON: {exc.msg}"})
            ok, msg, details = chat_with_bot(data.get("message"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

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

        if action == "open_terminal":
            ok, msg = open_project_terminal()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        if action == "close_position":
            position_id = data.get("position_id")
            if position_id is None:
                return self._json(400, {"ok": False, "message": "position_id is required"})
            ok, msg = request_close_position(position_id)
            return self._json(202 if ok else 400, {"ok": ok, "message": msg})

        return self._json(400, {"error": f"Unknown action: {action}"})


if __name__ == "__main__":
    print(f"Starting HTML dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    print(f"Using DB path: {DB_PATH}", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    print(f"Serving HTML dashboard at http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server.serve_forever()
