"""
config.py — All settings, API keys, and tunable parameters
Trading Bot v2
"""

import os
from dotenv import load_dotenv

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
KRAKEN_ENABLED      = False

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")

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
CASH_ACCOUNT_MODE   = True
SETTLEMENT_DAYS     = 2

# Market timing (Eastern Time)
MARKET_OPEN_BUFFER_MIN  = 30
STOCK_SCAN_INTERVAL_SEC = 60
CRYPTO_SCAN_INTERVAL_SEC= 300

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
    "scalp_adx_min":                20,     # NEW: ADX floor for scalp_master (Apr 2026)

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
    # STRATEGY 9: VWAP Momentum  (NEW — Apr 2026)
    # EMA 5/13/34 stack + VWAP directional filter + ADX + RSI zone + volume.
    # Stock-only, 5-minute bars.
    #
    # Tuning guide:
    #   vwap_mom_adx_min:      Raise to 30 for stricter trend requirement.
    #                          Lower to 20 if signal volume is too low.
    #   vwap_mom_rsi_low/high: The 40-60 zone is the "momentum sweet spot".
    #                          Widen to 35-65 for more signals, narrow to
    #                          45-55 for higher quality but fewer trades.
    #   vwap_mom_volume_ratio: 1.5x is the minimum conviction bar.
    #                          Raise to 2.0x if too many false signals.
    # -------------------------------------------------------------------------
    "vwap_mom_adx_min":             25,     # ADX must be >= this (trending market)
    "vwap_mom_adx_period":          14,     # ADX lookback period
    "vwap_mom_rsi_period":          14,     # RSI lookback period
    "vwap_mom_rsi_low":             40,     # RSI lower bound of momentum zone
    "vwap_mom_rsi_high":            60,     # RSI upper bound of momentum zone
    "vwap_mom_volume_ratio":        1.5,    # Volume must be >= Nx 20-bar average
    "vwap_mom_min_score":           0.65,   # Minimum confidence to fire signal

    # -------------------------------------------------------------------------
    # ML SCORER BOOST
    # -------------------------------------------------------------------------
    "ml_score_multiplier":          1.5,
    "ml_min_confidence":            0.55,
}
