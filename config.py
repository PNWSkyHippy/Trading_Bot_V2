"""
config.py — All settings, API keys, and tunable parameters
Trading Bot v2
"""
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
import keyring
load_dotenv()

# =============================================================================
# API KEYS (loaded from .env)
# =============================================================================

ALPACA_API_KEY      = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY   = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL     = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

COINBASE_API_KEY    = os.getenv("COINBASE_API_KEY", "")
COINBASE_SECRET_KEY = os.getenv("COINBASE_SECRET_KEY", "")

KRAKEN_API_KEY      = os.getenv("KRAKEN_API_KEY", "")
KRAKEN_SECRET_KEY   = os.getenv("KRAKEN_SECRET_KEY", "")
KRAKEN_ENABLED      = True

# Interactive Brokers — add keys to .env when account is ready
# IBKR uses TWS or IB Gateway running locally (no REST key — just account ID)
# TWS paper port: 7497  |  TWS live port: 7496
IBKR_ACCOUNT        = os.getenv("IBKR_ACCOUNT", "")    # Account ID e.g. DU1234567
IBKR_ENABLED        = True                              # Set True after TWS is running
IBKR_PAPER_MODE     = True                              # True = paper (port 7497)

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
_fernet_key = keyring.get_password("trading_bot_v2", "fernet_key")
BASE_KEY = _fernet_key.encode() if _fernet_key else None
if ANTHROPIC_API_KEY and not BASE_KEY:
    raise RuntimeError(
        "Fernet key not found in Windows Credential Manager. "
        "Run: python Scripts\\store_fernet_key.py"
    )
if ANTHROPIC_API_KEY:
    cipher_suite = Fernet(BASE_KEY)
    encrypted_val = ANTHROPIC_API_KEY.strip().encode()
    decrypted_val = cipher_suite.decrypt(encrypted_val).decode()
    ANTHROPIC_API_KEY = decrypted_val
else:
    pass

EMAIL_SENDER        = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD      = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT     = os.getenv("EMAIL_RECIPIENT", "")

# =============================================================================
# CAPITAL & TRADING PARAMETERS
# =============================================================================

STARTING_CAPITAL        = 100000.00
BOT_CAPITAL_ALLOCATION  = 0.00
DAILY_PROFIT_TARGET_PCT = 2.0
GOAL_CAPITAL            = 1038198.96
GOAL_DAYS               = 480

# Position sizing
MAX_POSITION_PCT        = 2.0
MIN_SIGNAL_CONFIDENCE   = 0.65

# Stop-loss / take-profit defaults
DEFAULT_STOP_LOSS_PCT   = 1.5
DEFAULT_TAKE_PROFIT_PCT = 3.0
TRAILING_STOP_PCT       = 1.5

# ---------------------------------------------------------------------------
# Backtest friction assumptions
# Applied as round-trip cost (commission + slippage) per closed trade.
# Per-leg means entry AND exit each incur the cost (total = 2× per trade).
#
# Stocks  — Alpaca: zero commission; assume 1 bp half-spread for fills.
# Crypto  — Kraken taker fee 0.26% (standard tier); 5 bp half-spread.
#            Higher-volume traders pay less (0.10% at highest tier).
# Set both to 0.0 to reproduce the old friction-free (optimistic) results.
# ---------------------------------------------------------------------------
BT_COMMISSION_STOCK_PCT  = 0.00   # Alpaca is commission-free
BT_COMMISSION_CRYPTO_PCT = 0.26   # Kraken taker fee, standard tier
BT_SLIPPAGE_STOCK_PCT    = 0.01   # stock NBBO half-spread estimate
BT_SLIPPAGE_CRYPTO_PCT   = 0.05   # crypto bid-ask half-spread estimate

# Momentum rider
MOMENTUM_RIDER_ENABLED        = True
MOMENTUM_RIDER_RSI_MIN        = 50
MOMENTUM_RIDER_VOL_RATIO      = 1.3
MOMENTUM_RIDER_MIN_SCORE      = 0.67
MOMENTUM_RIDER_MAX_EXTENSIONS = 3

# Risk circuit breakers
MAX_DAILY_LOSS_PCT      = 15.0
MAX_CONSECUTIVE_LOSSES  = 10
MAX_OPEN_POSITIONS      = 30

# Price filters
STOCK_MIN_PRICE     = 0.40
STOCK_MAX_PRICE     = 5000.00
STOCK_MIN_VOLUME    = 100000
CRYPTO_MIN_PRICE    = 0.001
CRYPTO_MAX_PRICE    = 999999.00

# Inverse ETF / Leveraged ETF settings
USE_LEVERAGED_LONGS = False

# Cash account / PDT settings
# T+1 is the SEC standard since May 2024 (was T+2).
# IBKR cash accounts use T+1. Alpaca cash accounts use T+1.
# Set SETTLEMENT_DAYS=2 only if your broker still settles T+2.
CASH_ACCOUNT_MODE   = True
SETTLEMENT_DAYS     = 1

# Market timing (Eastern Time)
MARKET_OPEN_BUFFER_MIN   = 30
STOCK_SCAN_INTERVAL_SEC  = 60
CRYPTO_SCAN_INTERVAL_SEC = 300

# =============================================================================
# BROKER SETTINGS
# =============================================================================

ALPACA_PAPER_MODE   = True
KRAKEN_PAPER_MODE   = True

# =============================================================================
# WATCHLISTS
# =============================================================================

def _load_watchlist(filepath: str, fallback: list) -> list:
    """Load a watchlist from a text file, falling back to hardcoded list."""
    try:
        with open(filepath, "r") as f:
            symbols = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        if symbols:
            return symbols
    except FileNotFoundError:
        pass
    return fallback

_STOCK_FALLBACK = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "AMD",  "INTC", "BABA",  "NFLX", "SPY",  "QQQ",  "IWM",
    "JPM",  "BAC",  "GS",    "XOM",  "CVX",  "PFE",
]

_CRYPTO_FALLBACK = [
    "BTC/USD",  "ETH/USD",  "SOL/USD",  "ADA/USD",
    "MATIC/USD","DOT/USD",  "AVAX/USD", "LINK/USD",
    "LTC/USD",  "XRP/USD",
]

STOCK_WATCHLIST  = _load_watchlist("watchlists/stocks.txt",  _STOCK_FALLBACK)
CRYPTO_WATCHLIST = _load_watchlist("watchlists/crypto.txt",  _CRYPTO_FALLBACK)

# =============================================================================
# DATABASE
# =============================================================================

DB_PATH = "data/trading_bot.db"

# =============================================================================
# REPORTING
# =============================================================================

EOD_REPORT_HOUR_ET  = 17
ML_RETRAIN_HOUR_ET  = 18
CAPITAL_SYNC_MIN    = 15
ML_MIN_TRADES       = 50

# =============================================================================
# STRATEGY AUTO-DISABLE
# =============================================================================

STRATEGY_MIN_TRADES         = 20
STRATEGY_DISABLE_WIN_RATE   = 45.0
STRATEGY_REENABLE_WIN_RATE  = 50.0

# =============================================================================
# VERBOSE MODE
# =============================================================================

VERBOSE_MODE = False

# =============================================================================
# POSITION MONITOR EXIT SETTINGS
# =============================================================================

# Performance-contingent time stops
# Closes trades that aren't producing within expected timeframes.
# Frees up capital for better opportunities rather than waiting for stop loss.
PERF_TIME_STOP_ENABLED   = True
PERF_CHECK_1HR_MIN_PCT   = 0.2    # need at least 0.5% profit after 1 hour
PERF_CHECK_3HR_MIN_PCT   = 1.5    # need at least 1.5% profit after 3 hours
HARD_TIME_STOP_HOURS     = 3.5    # hard kill after 3.5 hours regardless

# Early loss identification
# At 20 min: if trade is negative AND still moving wrong direction → close
EARLY_LOSS_ENABLED       = True
EARLY_LOSS_CHECK_MINUTES = 20
EARLY_LOSS_MIN_PCT       = -0.3   # trigger threshold (negative = loss)

# Pivot point break exit
# Long breaks below S1 → close | Short breaks above R1 → close
# Only fires after 30 minutes to allow trade to breathe past entry noise
PIVOT_EXIT_ENABLED       = True
PIVOT_EXIT_BARS          = 20     # bars used to calculate pivot levels

# =============================================================================
# DAILY MARKET SCANNER
# =============================================================================

SCANNER_ENABLED          = True
SCANNER_TOP_N            = 10
SCANNER_RUN_TIME_ET      = "16:30"   # 4:30 PM ET = 1:30 PM PT

# Stock filter thresholds
STOCK_PCT_OF_52W_HIGH    = 0.98
STOCK_VOL_SURGE_MIN      = 1.30
STOCK_HISTORY_DAYS       = "1y"

# Crypto filter thresholds
CRYPTO_RSI_MIN           = 50
CRYPTO_RSI_MAX           = 80
CRYPTO_VOL_SURGE_MIN     = 1.20

# CoinGecko rate limiting
COINGECKO_API_KEY        = ""     # leave blank for free tier
COINGECKO_DELAY          = 2.5
COINGECKO_MAX_RETRIES    = 3
COINGECKO_BASE_WAIT      = 30
WIKIPEDIA_DELAY          = 3.0

# Scanner file paths
SCANNER_REPORTS_DIR      = "reports"
SCANNER_WATCHLIST_DIR    = "watchlist"
TEMP_STOCKS_FILE         = "watchlist/scanned_stocks.txt"
TEMP_CRYPTO_FILE         = "watchlist/scanned_crypto.txt"

# =============================================================================
# SIGNAL FINE-TUNING
# =============================================================================

SIGNAL_TUNING = {

    # -------------------------------------------------------------------------
    # GLOBAL
    # -------------------------------------------------------------------------
    "min_signal_confidence":        0.65,

    # -------------------------------------------------------------------------
    # ORIGINAL SCANNER
    # -------------------------------------------------------------------------
    "stock_rsi_oversold":           35,
    "stock_rsi_overbought":         65,
    "stock_rsi_weight":             2.0,
    "stock_macd_weight":            2.5,
    "stock_ema_weight":             2.0,
    "stock_bb_weight":              1.5,
    "stock_volume_weight":          1.0,
    "stock_volume_spike_ratio":     1.5,
    "stock_bb_lower_pct":           0.05,
    "stock_bb_upper_pct":           0.95,
    "crypto_rsi_oversold":          38,
    "crypto_rsi_overbought":        62,
    "crypto_rsi_weight":            2.5,
    "crypto_macd_weight":           2.5,
    "crypto_ema_weight":            2.0,
    "crypto_bb_weight":             1.5,
    "crypto_volume_weight":         1.0,
    "crypto_volume_spike_ratio":    1.5,
    "crypto_bb_lower_pct":          0.05,
    "crypto_bb_upper_pct":          0.95,

    # -------------------------------------------------------------------------
    # STRATEGY 1: RSI Momentum
    # -------------------------------------------------------------------------
    "rsi_momentum_oversold":        30,
    "rsi_momentum_overbought":      70,
    "rsi_momentum_period":          14,
    "rsi_momentum_min_score":       0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 2: Bollinger Breakout
    # -------------------------------------------------------------------------
    "bb_breakout_period":           20,
    "bb_breakout_std":              2.0,
    "bb_squeeze_threshold":         0.04,
    "bb_breakout_min_score":        0.70,

    # -------------------------------------------------------------------------
    # STRATEGY 3: EMA Crossover
    # -------------------------------------------------------------------------
    "ema_fast_period":              9,
    "ema_slow_period":              21,
    "ema_trend_period":             50,
    "ema_crossover_min_score":      0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 4: Mean Reversion
    # -------------------------------------------------------------------------
    "mean_rev_zscore_entry":        2.0,
    "mean_rev_period":              20,
    "mean_rev_min_score":           0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 5: Scalp Master
    # -------------------------------------------------------------------------
    "scalp_rsi_oversold":           35,
    "scalp_rsi_overbought":         65,
    "scalp_rsi_period":             7,
    "scalp_min_volume_ratio":       1.2,
    "scalp_min_score":              0.60,
    "scalp_adx_min":                20,

    # -------------------------------------------------------------------------
    # STRATEGY 6: Swing Trader
    # -------------------------------------------------------------------------
    "swing_adx_min":                20,
    "swing_adx_period":             14,
    "swing_rsi_oversold":           40,
    "swing_rsi_overbought":         60,
    "swing_min_score":              0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 7: Grid Bot
    # -------------------------------------------------------------------------
    "grid_adx_max":                 20,
    "grid_adx_period":              14,
    "grid_bb_period":               30,
    "grid_min_score":               0.70,

    # -------------------------------------------------------------------------
    # STRATEGY 8: DCA Accumulator
    # -------------------------------------------------------------------------
    "dca_ema_period":               50,
    "dca_dip_pct":                  0.02,
    "dca_rsi_max":                  45,
    "dca_min_score":                0.60,

    # -------------------------------------------------------------------------
    # STRATEGY 9: VWAP Momentum
    # -------------------------------------------------------------------------
    "vwap_mom_adx_min":             25,
    "vwap_mom_adx_period":          14,
    "vwap_mom_rsi_period":          14,
    "vwap_mom_rsi_low":             40,
    "vwap_mom_rsi_high":            60,
    "vwap_mom_volume_ratio":        1.5,
    "vwap_mom_min_score":           0.65,

    # -------------------------------------------------------------------------
    # ML SCORER BOOST
    # -------------------------------------------------------------------------
    "ml_score_multiplier":          1.5,
    "ml_min_confidence":            0.55,
}

# ── Alert Digest Queue ──────────────────────────────────────────────────────────────
# Trade open/close alerts are batched into a single digest email sent every
# ALERT_DIGEST_HOURS hours instead of one email per trade.
# Errors and trading halts always bypass the queue and send immediately.
# Set to 0 to disable batching (reverts to one email per trade — old behavior).
ALERT_DIGEST_HOURS = 1   # Change to 2 or 3 to reduce email further

# ── Breakout Signal API ────────────────────────────────────────
BOT_API_KEY           = "pyd9pocfRHu0JxiiOQWQzuns5qdiikpRy8v5Vd3G0h4"   # copy this to scanner_config.json bot_api_key
BOT_API_PORT          = 8181
BREAKOUT_MIN_ESCALATION = 2   # 0-3; only inject escalation >= this
