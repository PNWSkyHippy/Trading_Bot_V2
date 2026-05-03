"""
Ron's Market Breakout Scanner
==============================
Scans stocks and crypto for early breakout patterns.
Detects price compression + volume spike + momentum acceleration
before big moves happen.

Run:
    python BreakoutScanner.py          # GUI if tkinter available, else console
    python BreakoutScanner.py --console # Force console mode

Config:
    scanner_config.json is auto-created on first run.
    Edit it to set API keys, thresholds, email settings.

API Keys:
    Store keys in scanner_config.json (gitignored) or .env
    NEVER hardcode keys in this file.
"""

import csv
import json
import logging
import os
import queue
import smtplib
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dt_time
from enum import Enum
from typing import Any, Dict, List, Optional

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("scanner.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Signal CSV ────────────────────────────────────────────────────────────────
CSV_FILE = "signals_log.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    # Market Hours (Pacific Time)
    "stock_market_open":  "06:30",
    "stock_market_close": "13:00",
    "crypto_24_7":        True,
    "scan_interval_seconds": 30,
    "timezone": "US/Pacific",
    # Top Lists
    "top_stocks_count":  100,
    "top_cryptos_count": 100,
    # Breakout Detection Thresholds
    "momentum_window":               5,    # candles to analyze momentum
    "volume_spike_multiplier":       3.0,  # volume must be 3x average
    "price_acceleration_threshold":  0.5,  # % increase per interval
    # Alert Settings
    "enable_sound_alert":  True,
    "enable_visual_alert": True,
    "enable_email_alert":  False,
    "email_smtp_server":   "smtp.gmail.com",
    "email_smtp_port":     587,
    "email_from":          "",
    "email_to":            "",
    "email_password":      "",
    # Auto-Trading Settings
    "enable_auto_trade":          False,
    "auto_trade_without_confirm": False,
    "broker":                     "alpaca",
    # API Keys — fill these in scanner_config.json, never hardcode here
    "alpaca_api_key":       "",
    "alpaca_secret_key":    "",
    "alpaca_base_url":      "https://paper-api.alpaca.markets",
    "coinbase_api_key":     "",
    "coinbase_api_secret":  "",
    "kraken_api_key":       "",
    "kraken_api_secret":    "",
    # Trading Parameters
    "default_trade_amount_usd": 1000,
    "max_position_size_usd":    5000,
    "stop_loss_percent":        5,
    "take_profit_percent":      20,
    # Schedule
    "run_days":      ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "exclude_dates": [],
    # Sound
    "alert_sound_frequency":  800,
    "alert_sound_duration_ms": 1000,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

class AlertType(Enum):
    SOUND  = "sound"
    VISUAL = "visual"
    EMAIL  = "email"
    TRADE  = "trade"


class AssetType(Enum):
    STOCK  = "stock"
    CRYPTO = "crypto"


@dataclass
class PriceData:
    symbol:     str
    price:      float
    open_price: float
    high:       float
    low:        float
    volume:     float
    timestamp:  datetime
    asset_type: AssetType

    @property
    def daily_change_pct(self) -> float:
        if self.open_price == 0:
            return 0.0
        return ((self.price - self.open_price) / self.open_price) * 100

    @property
    def daily_high_pct(self) -> float:
        if self.open_price == 0:
            return 0.0
        return ((self.high - self.open_price) / self.open_price) * 100


@dataclass
class BreakoutSignal:
    symbol:             str
    asset_type:         AssetType
    current_price:      float
    predicted_move_pct: float
    confidence:         float        # 0.0 to 1.0
    volume_spike:       float
    momentum_score:     float
    pattern_detected:   str
    timestamp:          datetime
    price_history:      List[float] = field(default_factory=list)
    volume_history:     List[float] = field(default_factory=list)


@dataclass
class Alert:
    signal:       BreakoutSignal
    alert_type:   AlertType
    message:      str
    timestamp:    datetime
    acknowledged: bool = False


# =============================================================================
# SIGNAL CLASSIFICATION
# =============================================================================

def classify_signal(signal: BreakoutSignal) -> dict:
    """
    Classify signal direction, stage, and probability of continuation.
    Returns dict with keys: direction, stage, poc (probability of continuation %)
    """
    score = signal.confidence

    # Direction
    if signal.momentum_score > 0:
        direction = "LONG"
    elif signal.momentum_score < -0.5:
        direction = "SHORT"
    else:
        direction = "LONG"  # default to long for compression setups

    # Stage
    if "strong" in signal.pattern_detected:
        stage = "CONFIRMED"
    elif "early" in signal.pattern_detected:
        stage = "EARLY"
    else:
        stage = "WATCHLIST"

    # Probability of continuation
    poc = min(95, score * 100)

    # Boost for volume confirmation
    if signal.volume_spike > 3.0:
        poc = min(95, poc + 10)

    return {
        "direction": direction,
        "stage":     stage,
        "poc":       poc,
    }


def classify_momentum(entry_price: float, current_price: float) -> tuple:
    """Return (status_str, move_pct) for a position."""
    try:
        move_pct = ((float(current_price) - float(entry_price)) / float(entry_price)) * 100
        if move_pct < 1:
            return "DEAD", move_pct
        elif move_pct < 3:
            return "SMALL", move_pct
        elif move_pct < 5:
            return "MEDIUM", move_pct
        else:
            return "STRONG", move_pct
    except Exception:
        return "UNKNOWN", 0.0


# =============================================================================
# SIGNAL CSV LOGGING
# =============================================================================

def log_signal_to_csv(signal: BreakoutSignal):
    """Append a new signal to the CSV log."""
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Symbol", "Score", "Confidence",
                "Date", "Time", "Price",
                "t_5m", "t_15m", "t_1h", "t_4h", "t_24h",
                "momentum", "move_pct",
            ])
        writer.writerow([
            signal.symbol,
            round(signal.predicted_move_pct, 2),
            round(signal.confidence * 100, 2),
            signal.timestamp.strftime("%Y-%m-%d"),
            signal.timestamp.strftime("%H:%M:%S"),
            signal.current_price,
            "", "", "", "", "",
            "", "",
        ])


def load_signal_results() -> dict:
    """Load signal tracking results from CSV."""
    results = {}
    try:
        with open(CSV_FILE, "r") as f:
            for row in csv.DictReader(f):
                symbol = row["Symbol"]
                results[symbol] = {
                    "move_pct": float(row["move_pct"]) if row.get("move_pct") else 0,
                    "t_5m":     row.get("t_5m", ""),
                    "t_15m":    row.get("t_15m", ""),
                    "t_1h":     row.get("t_1h", ""),
                    "momentum": row.get("momentum", ""),
                }
    except Exception:
        pass
    return results


def update_signal_tracking(scanner):
    """
    Update the CSV with price tracking at 5m / 15m / 1h / 4h / 24h intervals.
    Called periodically by the scanner loop.
    """
    if not os.path.isfile(CSV_FILE):
        return

    rows = []
    with open(CSV_FILE, mode="r") as f:
        rows = list(csv.DictReader(f))

    updated = False

    for row in rows:
        symbol = row["Symbol"]
        try:
            # Fetch current price
            if "/" in symbol:
                ticker = scanner.crypto_fetcher.exchange.fetch_ticker(symbol)
                price  = ticker["last"]
            else:
                hist_data = scanner.stock_fetcher.get_historical_data(symbol)
                price     = hist_data[-1].price if hist_data else None

            if price is None:
                continue

            entry_time = datetime.strptime(
                row["Date"] + " " + row["Time"],
                "%Y-%m-%d %H:%M:%S"
            )
            elapsed = (datetime.now() - entry_time).total_seconds()

            def fill(col, seconds):
                nonlocal updated
                if row[col] == "" and elapsed >= seconds:
                    row[col] = round(price, 4)
                    updated  = True

            fill("t_5m",  300)
            fill("t_15m", 900)
            fill("t_1h",  3600)
            fill("t_4h",  14400)
            fill("t_24h", 86400)

            entry_price = float(row["Price"])
            status, move_pct = classify_momentum(entry_price, price)
            row["momentum"] = status
            row["move_pct"] = round(move_pct, 2)

            if row["t_5m"] != "":
                t5 = float(row["t_5m"])
                if t5 <= entry_price:
                    row["momentum"] = "DEAD"
                elif move_pct < 1.0:
                    row["momentum"] = "WEAK"
                elif row["t_15m"] != "":
                    t15 = float(row["t_15m"])
                    if t15 <= t5:
                        row["momentum"] = "FADING"

            if move_pct >= 2.0:
                logger.warning(f"STRONG MOVE: {symbol} +{move_pct:.2f}%")
            elif move_pct >= 1.5:
                logger.info(f"LIVE MOVE: {symbol} +{move_pct:.2f}%")

        except Exception:
            continue

    if updated and rows:
        with open(CSV_FILE, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    def __init__(self, config_path: str = "scanner_config.json"):
        self.config_path = config_path
        self.config      = {}
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"Config loaded from {self.config_path}")
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()
            logger.info(f"Default config created at {self.config_path}")

    def save(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()

    def is_market_open(self, asset_type: AssetType) -> bool:
        now      = datetime.now()
        today    = now.strftime("%Y-%m-%d")
        day_name = now.strftime("%A")

        if today in self.config.get("exclude_dates", []):
            return False
        if day_name not in self.config.get("run_days", []):
            return False

        if asset_type == AssetType.CRYPTO and self.config.get("crypto_24_7", True):
            return True

        if asset_type == AssetType.STOCK:
            open_time  = self.config.get("stock_market_open",  "06:30")
            close_time = self.config.get("stock_market_close", "13:00")
            oh, om     = map(int, open_time.split(":"))
            ch, cm     = map(int, close_time.split(":"))
            cur        = now.time()
            return dt_time(oh, om) <= cur <= dt_time(ch, cm)

        return False


# =============================================================================
# DATA FETCHERS
# =============================================================================

class StockDataFetcher:
    """Fetches stock data via Alpaca (primary) or yfinance (fallback)."""

    # Major stocks for yfinance fallback
    FALLBACK_SYMBOLS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA",
        "JPM",  "V",    "JNJ",   "WMT",  "UNH",  "PG",   "HD",
        "MA",   "BAC",  "ABBV",  "PFE",  "KO",   "AVGO", "PEP",
        "LLY",  "COST", "TMO",   "CSCO", "ACN",  "CVX",  "MRK",
        "NFLX", "QCOM", "TXN",   "AMD",  "INTC", "CRM",  "AMGN",
        "IBM",  "GE",   "HON",   "SBUX", "GS",   "CAT",  "BLK",
        "AXP",  "SPGI", "DE",    "ISRG", "MDLZ", "ADP",  "NOW",
        "BKNG", "MO",   "AMAT",  "LRCX", "PANW", "SNOW", "PLTR",
        "COIN", "SHOP", "CRWD",  "ABNB", "UBER", "LYFT", "ROKU",
        "DDOG", "NET",  "ZS",    "OKTA", "MDB",  "BILL", "TTD",
        "SMCI", "ARM",  "MSTR",  "IONQ", "SOUN", "BBAI", "ASTS",
    ]

    def __init__(self, config: ConfigManager):
        self.config = config
        self.api    = None
        if ALPACA_AVAILABLE:
            try:
                self.api = tradeapi.REST(
                    config.get("alpaca_api_key"),
                    config.get("alpaca_secret_key"),
                    config.get("alpaca_base_url"),
                    api_version="v2",
                )
                logger.info("Alpaca API initialized")
            except Exception as e:
                logger.error(f"Alpaca init failed: {e}")

    def get_top_movers(self, count: int = 100) -> List[PriceData]:
        stocks = []

        if self.api:
            try:
                assets    = self.api.list_assets(status="active", asset_class="us_equity")
                symbols   = [a.symbol for a in assets[:500]]
                snapshots = self.api.get_snapshots(symbols)

                for symbol, snap in snapshots.items():
                    if snap and snap.daily_bar:
                        bar = snap.daily_bar
                        stocks.append(PriceData(
                            symbol     = symbol,
                            price      = bar.c,
                            open_price = bar.o,
                            high       = bar.h,
                            low        = bar.l,
                            volume     = bar.v,
                            timestamp  = datetime.now(),
                            asset_type = AssetType.STOCK,
                        ))
            except Exception as e:
                logger.error(f"Alpaca snapshot error: {e}")

        if not stocks and YFINANCE_AVAILABLE:
            stocks = self._get_movers_yfinance()

        stocks.sort(key=lambda x: x.daily_change_pct, reverse=True)
        return stocks[:count]

    def _get_movers_yfinance(self) -> List[PriceData]:
        stocks = []
        try:
            tickers = yf.download(
                self.FALLBACK_SYMBOLS, period="1d", interval="1m",
                progress=False, group_by="ticker"
            )
            for symbol in self.FALLBACK_SYMBOLS:
                try:
                    df = tickers[symbol].dropna()
                    if df.empty:
                        continue
                    stocks.append(PriceData(
                        symbol     = symbol,
                        price      = float(df["Close"].iloc[-1]),
                        open_price = float(df["Open"].iloc[0]),
                        high       = float(df["High"].max()),
                        low        = float(df["Low"].min()),
                        volume     = float(df["Volume"].sum()),
                        timestamp  = datetime.now(),
                        asset_type = AssetType.STOCK,
                    ))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"yfinance error: {e}")
        return stocks

    def get_historical_data(self, symbol: str, period: str = "5d",
                             interval: str = "5m") -> List[PriceData]:
        data = []
        if not YFINANCE_AVAILABLE:
            return data
        try:
            df = yf.download(symbol, period=period, interval=interval,
                             progress=False, auto_adjust=True)
            df = df.dropna()
            for ts, row in df.iterrows():
                data.append(PriceData(
                    symbol     = symbol,
                    price      = float(row["Close"]),
                    open_price = float(row["Open"]),
                    high       = float(row["High"]),
                    low        = float(row["Low"]),
                    volume     = float(row["Volume"]),
                    timestamp  = ts.to_pydatetime(),
                    asset_type = AssetType.STOCK,
                ))
        except Exception as e:
            logger.error(f"yfinance history error for {symbol}: {e}")
        return data


class CryptoDataFetcher:
    """Fetches crypto data via Kraken (primary) or Coinbase (fallback)."""

    def __init__(self, config: ConfigManager):
        self.config   = config
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        if not CCXT_AVAILABLE:
            logger.warning("ccxt not installed — crypto scanning disabled")
            return

        # Try Kraken first
        try:
            self.exchange = ccxt.kraken({
                "apiKey":          self.config.get("kraken_api_key"),
                "secret":          self.config.get("kraken_api_secret"),
                "enableRateLimit": True,
                "timeout":         10000,
            })
            self.exchange.load_markets()
            logger.info("Kraken exchange initialized")
            return
        except Exception as e:
            logger.warning(f"Kraken init failed: {e}")

        # Fallback to Coinbase
        try:
            self.exchange = ccxt.coinbase({
                "apiKey":          self.config.get("coinbase_api_key"),
                "secret":          self.config.get("coinbase_api_secret"),
                "enableRateLimit": True,
            })
            self.exchange.load_markets()
            logger.info("Coinbase exchange initialized")
        except Exception as e:
            logger.warning(f"Coinbase init failed: {e}")

    def get_top_movers(self, count: int = 100) -> List[PriceData]:
        cryptos = []
        if not self.exchange:
            return cryptos
        try:
            tickers = self.exchange.fetch_tickers()
            for symbol, ticker in tickers.items():
                if "/USD" not in symbol and "/USDT" not in symbol:
                    continue
                try:
                    change_pct = ticker.get("percentage", 0) or 0
                    if change_pct == 0:
                        continue
                    open_p = (ticker["open"] if ticker.get("open")
                              else ticker["last"] / (1 + change_pct / 100))
                    cryptos.append(PriceData(
                        symbol     = symbol,
                        price      = ticker["last"],
                        open_price = open_p,
                        high       = ticker.get("high") or ticker["last"],
                        low        = ticker.get("low")  or ticker["last"],
                        volume     = ticker.get("quoteVolume") or ticker.get("baseVolume", 0),
                        timestamp  = datetime.now(),
                        asset_type = AssetType.CRYPTO,
                    ))
                except Exception:
                    continue
            cryptos.sort(key=lambda x: abs(x.daily_change_pct), reverse=True)
        except Exception as e:
            logger.error(f"Crypto fetch error: {e}")
        return cryptos[:count]

    def get_historical_data(self, symbol: str, timeframe: str = "5m",
                            limit: int = 100) -> List[PriceData]:
        data = []
        if not self.exchange:
            return data
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            for candle in ohlcv:
                ts, open_p, high, low, close, volume = candle
                data.append(PriceData(
                    symbol     = symbol,
                    price      = close,
                    open_price = open_p,
                    high       = high,
                    low        = low,
                    volume     = volume,
                    timestamp  = datetime.fromtimestamp(ts / 1000),
                    asset_type = AssetType.CRYPTO,
                ))
        except Exception as e:
            logger.error(f"Crypto history error for {symbol}: {e}")
        return data


# =============================================================================
# BREAKOUT DETECTION ENGINE
# =============================================================================

class BreakoutDetector:
    """
    Pro-grade breakout detector.
    Focuses on EARLY breakout signals — before big moves happen.
    Looks for: price compression + volume expansion + momentum acceleration.
    """

    def __init__(self, config: ConfigManager):
        self.config           = config
        self.price_history    = {}
        self.volume_history   = {}
        self.detected_signals = {}
        self.history_length   = 50

    def update_history(self, price_data: PriceData):
        sym = price_data.symbol
        if sym not in self.price_history:
            self.price_history[sym]  = deque(maxlen=self.history_length)
            self.volume_history[sym] = deque(maxlen=self.history_length)
        self.price_history[sym].append(price_data.price)
        self.volume_history[sym].append(price_data.volume)

    def detect_breakout(self, price_data: PriceData) -> Optional[BreakoutSignal]:
        sym = price_data.symbol
        self.update_history(price_data)

        if len(self.price_history[sym]) < 25:
            return None

        prices  = list(self.price_history[sym])
        volumes = list(self.volume_history[sym])

        compression  = self._is_compressing(prices)
        expansion    = self._is_expanding(prices)
        early_volume = self._early_volume(volumes, prices)
        vwap_ok      = self._near_vwap(prices, volumes)
        not_chasing  = self._not_overextended(prices)
        momentum     = self._momentum(prices)

        score = 0.0
        if compression:  score += 0.25
        if early_volume: score += 0.25
        if expansion:    score += 0.20
        if vwap_ok:      score += 0.15
        if momentum > 1: score += 0.10
        if not_chasing:  score += 0.05

        if score < 0.5:
            return None

        # Cooldown — avoid signal spam per symbol
        last = self.detected_signals.get(sym)
        if last and (datetime.now() - last).total_seconds() < 300:
            return None
        self.detected_signals[sym] = datetime.now()

        if score > 0.75:
            pattern = "early_breakout_strong"
        elif score > 0.60:
            pattern = "early_breakout"
        else:
            pattern = "watchlist"

        return BreakoutSignal(
            symbol             = sym,
            asset_type         = price_data.asset_type,
            current_price      = price_data.price,
            predicted_move_pct = score * 100,
            confidence         = score,
            volume_spike       = self._volume_spike(volumes),
            momentum_score     = momentum,
            pattern_detected   = pattern,
            timestamp          = datetime.now(),
            price_history      = prices[-20:],
            volume_history     = volumes[-20:],
        )

    # ── Signal components ─────────────────────────────────────────────────────

    def _is_compressing(self, prices: list) -> bool:
        recent    = prices[-20:]
        avg       = sum(recent) / len(recent)
        range_pct = (max(recent) - min(recent)) / avg * 100
        return range_pct < 2.0

    def _is_expanding(self, prices: list) -> bool:
        move = (prices[-1] - prices[-3]) / prices[-3] * 100
        return move > 1.2

    def _early_volume(self, volumes: list, prices: list) -> bool:
        avg_vol      = sum(volumes[:-1]) / len(volumes[:-1])
        spike        = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        price_change = (prices[-1] - prices[-5]) / prices[-5] * 100
        return spike > 2.5 and price_change < 2.0

    def _near_vwap(self, prices: list, volumes: list) -> bool:
        total_vol = sum(volumes)
        if total_vol == 0:
            return False
        vwap     = sum(p * v for p, v in zip(prices, volumes)) / total_vol
        distance = abs(prices[-1] - vwap) / vwap * 100
        return distance < 1.0

    def _not_overextended(self, prices: list) -> bool:
        move = (prices[-1] - prices[-10]) / prices[-10] * 100
        return move < 8.0

    def _momentum(self, prices: list) -> float:
        changes = [
            (prices[i] - prices[i - 1]) / prices[i - 1] * 100
            for i in range(1, len(prices))
        ]
        return sum(changes[-5:]) / 5 if len(changes) >= 5 else 0.0

    def _volume_spike(self, volumes: list) -> float:
        avg = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 1.0
        return volumes[-1] / avg if avg > 0 else 1.0


# =============================================================================
# ALERT SYSTEM
# =============================================================================

class AlertSystem:
    """Handles sound, visual, and email alerts."""

    def __init__(self, config: ConfigManager):
        self.config          = config
        self.alert_queue:    queue.Queue = queue.Queue()
        self.alert_history:  List[Alert] = []
        self.email_last_sent: Dict[str, datetime] = {}
        self.gui             = None
        self.running         = False

    def start(self):
        self.running      = True
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
        logger.info("Alert system started")

    def stop(self):
        self.running = False

    def send_alert(self, signal: BreakoutSignal):
        message = self._format_alert_message(signal)

        if self.config.get("enable_sound_alert", True):
            self._sound_alert()

        if self.config.get("enable_visual_alert", True):
            self.alert_queue.put(Alert(
                signal     = signal,
                alert_type = AlertType.VISUAL,
                message    = message,
                timestamp  = datetime.now(),
            ))
            # Push to GUI if available
            if self.gui and hasattr(self.gui, "add_alert"):
                self.gui.add_alert(message, signal)

        if self.config.get("enable_email_alert", False):
            self._email_alert(signal, message)

    def _format_alert_message(self, signal: BreakoutSignal) -> str:
        meta      = classify_signal(signal)
        direction = meta["direction"]
        stage     = meta["stage"]
        poc       = meta["poc"]
        strength  = "HIGH" if poc > 75 else "MEDIUM" if poc > 60 else "LOW"

        reasons = []
        if signal.volume_spike > 2:
            reasons.append(f"Volume spike ({signal.volume_spike:.1f}x)")
        if signal.momentum_score > 0.5:
            reasons.append(f"Strong momentum ({signal.momentum_score:.2f})")
        if "compression" in signal.pattern_detected:
            reasons.append("Price compression detected")
        if "early" in signal.pattern_detected:
            reasons.append("Early breakout structure")
        if "strong" in signal.pattern_detected:
            reasons.append("Strong breakout pattern")

        reason_text = "\n- " + "\n- ".join(reasons) if reasons else "N/A"

        return (
            f"{'='*50}\n"
            f"BREAKOUT SIGNAL\n"
            f"{'='*50}\n"
            f"Symbol:    {signal.symbol}\n"
            f"Type:      {signal.asset_type.value.upper()}\n"
            f"Direction: {direction}  |  Stage: {stage}\n"
            f"Prob Cont: {poc:.0f}% ({strength})\n"
            f"Price:     ${signal.current_price:.4f}\n"
            f"Score:     {signal.predicted_move_pct:.0f}\n"
            f"Vol Spike: {signal.volume_spike:.1f}x\n"
            f"Momentum:  {signal.momentum_score:.2f}\n"
            f"Pattern:   {signal.pattern_detected}\n"
            f"Reasons:{reason_text}\n"
            f"Time:      {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    def _sound_alert(self):
        """Play alert sound with 3-second cooldown."""
        now = time.time()
        if not hasattr(self, "_last_sound"):
            self._last_sound = 0
        if now - self._last_sound < 3:
            return
        self._last_sound = now

        try:
            volume = 0.5
            if self.gui and hasattr(self.gui, "volume_var"):
                volume = self.gui.volume_var.get()
            if volume < 0.05:
                return

            if WINSOUND_AVAILABLE:
                repeats = max(1, int(volume * 3))
                for _ in range(repeats):
                    winsound.PlaySound(
                        r"C:\Windows\Media\chimes.wav",
                        winsound.SND_FILENAME | winsound.SND_ASYNC,
                    )
        except Exception:
            pass

    def _email_alert(self, signal: BreakoutSignal, message: str):
        symbol    = signal.symbol
        last_sent = self.email_last_sent.get(symbol)
        if last_sent and (datetime.now() - last_sent).total_seconds() < 600:
            return

        try:
            smtp_server = self.config.get("email_smtp_server", "smtp.gmail.com")
            smtp_port   = self.config.get("email_smtp_port", 587)
            email_from  = self.config.get("email_from", "")
            email_to    = self.config.get("email_to", "")
            password    = self.config.get("email_password", "")

            if not all([email_from, email_to, password]):
                logger.warning("Email credentials not configured — skipping email alert")
                return

            subject   = f"BREAKOUT ALERT: {signal.symbol} (+{signal.predicted_move_pct:.1f}%)"
            email_body = f"From: {email_from}\nTo: {email_to}\nSubject: {subject}\n\n{message}"

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_from, password)
                server.sendmail(email_from, email_to, email_body)

            self.email_last_sent[symbol] = datetime.now()
            logger.info(f"Email alert sent for {symbol}")

        except Exception as e:
            logger.error(f"Email alert failed: {e}")

    def _process_alerts(self):
        while self.running:
            try:
                alert = self.alert_queue.get(timeout=1)
                self.alert_history.append(alert)
                logger.info(f"Alert: {alert.signal.symbol} — {alert.signal.pattern_detected}")
                # Push to GUI on the main thread via after()
                if self.gui and hasattr(self.gui, "root") and self.gui.root:
                    try:
                        self.gui.root.after(
                            0, self.gui.add_alert, alert.message, alert.signal
                        )
                    except Exception:
                        pass
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processing error: {e}")


# =============================================================================
# TRADING ENGINE
# =============================================================================

class TradingEngine:
    """Executes trades through configured brokers."""

    def __init__(self, config: ConfigManager):
        self.config          = config
        self.alpaca_api      = None
        self.crypto_exchange = None
        self.positions:      Dict[str, dict] = {}
        self._init_brokers()

    def _init_brokers(self):
        if ALPACA_AVAILABLE and self.config.get("broker") == "alpaca":
            try:
                self.alpaca_api = tradeapi.REST(
                    self.config.get("alpaca_api_key"),
                    self.config.get("alpaca_secret_key"),
                    self.config.get("alpaca_base_url"),
                    api_version="v2",
                )
                logger.info("Alpaca trading API initialized")
            except Exception as e:
                logger.error(f"Alpaca init failed: {e}")

        if CCXT_AVAILABLE:
            try:
                self.crypto_exchange = ccxt.kraken({
                    "apiKey":          self.config.get("kraken_api_key"),
                    "secret":          self.config.get("kraken_api_secret"),
                    "enableRateLimit": True,
                })
            except Exception as e:
                logger.warning(f"Kraken trading init failed: {e}")
                try:
                    self.crypto_exchange = ccxt.coinbase({
                        "apiKey":          self.config.get("coinbase_api_key"),
                        "secret":          self.config.get("coinbase_api_secret"),
                        "enableRateLimit": True,
                    })
                except Exception as e2:
                    logger.warning(f"Coinbase trading init also failed: {e2}")

    def can_auto_trade(self) -> bool:
        return self.config.get("enable_auto_trade", False)

    def should_confirm_trade(self) -> bool:
        return not self.config.get("auto_trade_without_confirm", False)

    def place_stock_order(self, symbol: str, side: str,
                          qty: float = None, notional: float = None) -> dict:
        if not self.alpaca_api:
            return {"error": "Alpaca API not available"}
        try:
            if notional:
                order = self.alpaca_api.submit_order(
                    symbol=symbol, notional=notional,
                    side=side, type="market", time_in_force="day"
                )
            else:
                order = self.alpaca_api.submit_order(
                    symbol=symbol, qty=qty,
                    side=side, type="market", time_in_force="day"
                )
            logger.info(f"Stock order placed: {side} {symbol}")
            return {"success": True, "order_id": order.id, "status": order.status}
        except Exception as e:
            logger.error(f"Stock order failed: {e}")
            return {"error": str(e)}

    def place_crypto_order(self, symbol: str, side: str, amount: float) -> dict:
        if not self.crypto_exchange:
            return {"error": "Crypto exchange not available"}
        try:
            order = self.crypto_exchange.create_order(
                symbol=symbol, type="market", side=side, amount=amount
            )
            logger.info(f"Crypto order placed: {side} {amount} {symbol}")
            return {"success": True, "order_id": order.get("id"), "status": order.get("status")}
        except Exception as e:
            logger.error(f"Crypto order failed: {e}")
            return {"error": str(e)}

    def execute_signal(self, signal: BreakoutSignal) -> dict:
        if not self.can_auto_trade():
            return {"status": "auto_trade_disabled"}
        if self.should_confirm_trade():
            return {"status": "confirmation_required"}

        amount = self.config.get("default_trade_amount_usd", 1000)
        if signal.asset_type == AssetType.STOCK:
            return self.place_stock_order(symbol=signal.symbol, side="buy", notional=amount)
        else:
            qty = amount / signal.current_price
            return self.place_crypto_order(symbol=signal.symbol, side="buy", amount=qty)


# =============================================================================
# MAIN SCANNER
# =============================================================================

class MarketScanner:
    """
    Main scanner — orchestrates stock and crypto breakout detection.
    Runs both scanners in background threads on a configurable interval.
    """

    def __init__(self, config_path: str = "scanner_config.json"):
        self.config         = ConfigManager(config_path)
        self.stock_fetcher  = StockDataFetcher(self.config)
        self.crypto_fetcher = CryptoDataFetcher(self.config)
        self.detector       = BreakoutDetector(self.config)
        self.alert_system   = AlertSystem(self.config)
        self.trading        = TradingEngine(self.config)
        self.running        = False
        self.scan_thread    = None
        self.gui            = None
        self.latest_movers: List[PriceData] = []
        self.recent_signals: Dict[str, datetime] = {}

    def start(self):
        """Start the scanner background thread."""
        self.running = True
        self.alert_system.start()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Market scanner started")

    def stop(self):
        self.running = False
        self.alert_system.stop()
        logger.info("Market scanner stopped")

    def _scan_loop(self):
        while self.running:
            try:
                if self.config.is_market_open(AssetType.STOCK):
                    self._scan_stocks()

                if self.config.is_market_open(AssetType.CRYPTO):
                    self._scan_cryptos()

                update_signal_tracking(self)

            except Exception as e:
                logger.error(f"Scan loop error: {e}")

            interval = self.config.get("scan_interval_seconds", 30)
            time.sleep(interval)

    def should_log_signal(self, signal: BreakoutSignal) -> bool:
        """10-minute cooldown per symbol to avoid duplicate alerts."""
        key      = signal.symbol
        now      = datetime.now()
        last     = self.recent_signals.get(key)
        if last and (now - last).total_seconds() < 600:
            return False
        self.recent_signals[key] = now
        return True

    def _passes_quality_filter(self, signal: BreakoutSignal) -> bool:
        """Basic quality gate before logging or alerting."""
        if signal.confidence < 0.5:
            return False
        if signal.volume_spike < 1.5:
            return False
        return True

    def _scan_cryptos(self):
        logger.info("Scanning cryptos...")
        try:
            movers = self.crypto_fetcher.get_top_movers(
                self.config.get("top_cryptos_count", 100)
            )
            logger.info(f"Crypto movers: {len(movers)}")

            for crypto in movers:
                if not self.crypto_fetcher.exchange:
                    break
                if crypto.symbol not in self.crypto_fetcher.exchange.symbols:
                    continue

                history = self.crypto_fetcher.get_historical_data(crypto.symbol)
                for h in history:
                    self.detector.update_history(h)

                signal = self.detector.detect_breakout(crypto)
                if not signal:
                    continue

                if not self._passes_quality_filter(signal):
                    continue

                if not self.should_log_signal(signal):
                    continue

                meta = classify_signal(signal)
                logger.warning(
                    f"CRYPTO BREAKOUT: {signal.symbol} | "
                    f"Direction: {meta['direction']} | "
                    f"Stage: {meta['stage']} | "
                    f"PoC: {meta['poc']:.0f}% | "
                    f"Score: {signal.predicted_move_pct:.0f} | "
                    f"Confidence: {signal.confidence*100:.0f}%"
                )
                self.alert_system.send_alert(signal)
                log_signal_to_csv(signal)

        except Exception as e:
            logger.error(f"Crypto scan error: {e}")

    def _scan_stocks(self):
        logger.info("Scanning stocks...")
        try:
            movers = self.stock_fetcher.get_top_movers(
                self.config.get("top_stocks_count", 100)
            )
            self.latest_movers = movers

            for stock in movers:
                history = self.stock_fetcher.get_historical_data(stock.symbol)
                for h in history:
                    self.detector.update_history(h)

                signal = self.detector.detect_breakout(stock)
                if not signal:
                    continue

                if not self._passes_quality_filter(signal):
                    continue

                meta = classify_signal(signal)

                # Long-only filter for now (change when margin enabled)
                if meta["direction"] != "LONG":
                    continue

                # Require strong continuation probability
                if meta["poc"] < 60:
                    continue

                if not self.should_log_signal(signal):
                    continue

                logger.warning(
                    f"STOCK BREAKOUT: {signal.symbol} | "
                    f"Stage: {meta['stage']} | "
                    f"PoC: {meta['poc']:.0f}% | "
                    f"Score: {signal.predicted_move_pct:.0f} | "
                    f"Confidence: {signal.confidence*100:.0f}%"
                )
                self.alert_system.send_alert(signal)
                log_signal_to_csv(signal)

                if self.trading.can_auto_trade():
                    if self.trading.should_confirm_trade():
                        logger.info(f"Trade confirmation required for {signal.symbol}")
                    else:
                        result = self.trading.execute_signal(signal)
                        logger.info(f"Auto-trade result: {result}")

        except Exception as e:
            logger.error(f"Stock scan error: {e}")

    def run_gui(self):
        """Launch the Tkinter GUI."""
        self.gui = ScannerGUI(self)
        self.alert_system.gui = self.gui
        # DO NOT auto-start here — let the GUI Start button control it
        # so the gui.root reference exists before scanner fires first alert
        self.gui.start()

    def run_console(self):
        """Run in headless console mode."""
        self.start()
        print("\n" + "=" * 60)
        print("  RON'S MARKET BREAKOUT SCANNER")
        print("  Press Ctrl+C to stop")
        print("=" * 60 + "\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping scanner...")
            self.stop()


# =============================================================================
# GUI
# =============================================================================

class ScannerGUI:
    """Tkinter GUI for the breakout scanner."""

    def __init__(self, scanner: MarketScanner):
        self.scanner    = scanner
        self.root       = None
        self.alert_text = None
        self.running    = False

    def start(self):
        if not TKINTER_AVAILABLE:
            logger.warning("Tkinter not available — running in console mode")
            self.scanner.run_console()
            return

        self.root = tk.Tk()
        self.root.title("Ron's Market Breakout Scanner")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")

        self._setup_ui()
        self.running = True
        self._update_loop()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _setup_ui(self):
        # Title
        tk.Label(
            self.root,
            text="BREAKOUT SCANNER",
            font=("Helvetica", 24, "bold"),
            bg="#1a1a2e", fg="#00ff88",
        ).pack(pady=10)

        # Status
        status_frame = tk.Frame(self.root, bg="#16213e")
        status_frame.pack(fill="x", padx=20, pady=5)
        self.status_label = tk.Label(
            status_frame,
            text="Status: Initializing...",
            font=("Helvetica", 12),
            bg="#16213e", fg="#ffffff",
        )
        self.status_label.pack(side="left", padx=10)

        # Controls
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="Start Scanner",
            command=self._start_scanner,
            bg="#00ff88", fg="#000000",
            font=("Helvetica", 12, "bold"), padx=20,
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="Stop Scanner",
            command=self._stop_scanner,
            bg="#ff4444", fg="#ffffff",
            font=("Helvetica", 12, "bold"), padx=20,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)

        self.volume_var = tk.DoubleVar(value=0.3)
        tk.Scale(
            btn_frame,
            from_=0, to=1, resolution=0.01,
            orient="horizontal", label="Volume",
            variable=self.volume_var,
            bg="#1a1a2e", fg="#ffffff",
        ).pack(side="left", padx=10)

        self.auto_trade_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            btn_frame, text="Auto-Trade",
            variable=self.auto_trade_var,
            command=self._toggle_auto_trade,
            bg="#1a1a2e", fg="#ffffff",
            selectcolor="#16213e",
            font=("Helvetica", 11),
        ).pack(side="left", padx=20)

        # Alert area
        alert_frame = tk.LabelFrame(
            self.root, text="LIVE ALERTS",
            font=("Helvetica", 14, "bold"),
            bg="#16213e", fg="#ffaa00",
            padx=10, pady=10,
        )
        alert_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.alert_text = scrolledtext.ScrolledText(
            alert_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#0f0f23", fg="#00ff88",
            insertbackground="#ffffff",
            state="disabled",
        )
        self.alert_text.pack(fill="both", expand=True)
        self.alert_text.tag_config("breakout", foreground="#00ff00",
                                   font=("Consolas", 11, "bold"))
        self.alert_text.tag_config("info",     foreground="#aaaaaa")

        # Top movers table
        movers_frame = tk.LabelFrame(
            self.root, text="Stock Top Movers",
            font=("Helvetica", 14, "bold"),
            bg="#16213e", fg="#00ccff",
            padx=10, pady=10,
        )
        movers_frame.pack(fill="both", expand=True, padx=20, pady=10)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
            background="#0f0f23", foreground="white",
            fieldbackground="#0f0f23", rowheight=24,
        )
        style.map("Dark.Treeview", background=[("selected", "#347083")])

        self.movers_tree = ttk.Treeview(
            movers_frame,
            columns=("Symbol", "Price", "Change%"),
            show="headings",
            style="Dark.Treeview",
        )
        for col in ("Symbol", "Price", "Change%"):
            self.movers_tree.heading(col, text=col)
            self.movers_tree.column(col, width=150)
        self.movers_tree.pack(fill="both", expand=True)

    def add_alert(self, message: str, signal: BreakoutSignal):
        """Add an alert message to the text widget."""
        if not self.alert_text:
            return
        self.alert_text.config(state="normal")
        self.alert_text.insert(tk.END, "\n" + message + "\n", "breakout")
        self.alert_text.see(tk.END)
        self.alert_text.config(state="disabled")

    def _start_scanner(self):
        if not self.scanner.running:
            # Set GUI reference on alert system before starting
            # so first signal can reach the text widget
            self.scanner.alert_system.gui = self
            self.scanner.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        if self.status_label:
            self.status_label.config(text="Status: Running")

    def _stop_scanner(self):
        self.scanner.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.status_label:
            self.status_label.config(text="Status: Stopped")

    def _toggle_auto_trade(self):
        self.scanner.config.set("enable_auto_trade", self.auto_trade_var.get())

    def _update_loop(self):
        """Refresh top movers table every 5 seconds."""
        try:
            movers = self.scanner.latest_movers[:20]
            for row in self.movers_tree.get_children():
                self.movers_tree.delete(row)
            for m in movers:
                chg = f"{m.daily_change_pct:+.2f}%"
                self.movers_tree.insert("", tk.END,
                    values=(m.symbol, f"${m.price:.2f}", chg))
        except Exception:
            pass

        if self.running:
            self.root.after(5000, self._update_loop)

    def _on_close(self):
        self.running = False
        self.scanner.stop()
        self.root.destroy()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ron's Market Breakout Scanner")
    parser.add_argument("--console", action="store_true",
                        help="Force console mode (no GUI)")
    args = parser.parse_args()

    scanner = MarketScanner()

    if args.console or not TKINTER_AVAILABLE:
        scanner.run_console()
    else:
        scanner.run_gui()
