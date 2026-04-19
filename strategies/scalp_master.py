"""
scalp_master.py — Strategy 5: Scalp Master
Trading Bot v2

High-frequency scalping with tight stops (0.5%) and quick profit targets (1%).
Uses a short RSI period (7) and requires volume confirmation to avoid noise.
Position size is slightly smaller (1.5% vs default 2%) due to higher frequency.

Thresholds configurable in config.SIGNAL_TUNING.

Symbol whitelist: backtest data (30d 5m, Apr 2026) confirmed positive Sharpe
only on META, PLTR, ALAB, AMZN, GOOGL, MSFT. IREN and INTV added after
Anthropic backtest review Apr 2026.

Per-symbol adaptive SL/TP: After every 20 closed trades per symbol,
SL and TP are recalculated from actual trade history and saved to
symbol_params.json. Minimum R:R of 2.5 is always enforced.
"""

import json
import logging
import os
import threading
from typing import Dict, Optional

import pandas as pd
import pandas_ta as ta

import config
from strategies.base_strategy import BaseStrategy, TradeSignal


# ── Symbol whitelist ────────────────────────────────────────────────────────
SCALP_WHITELIST = {"META", "PLTR", "ALAB", "AMZN", "GOOGL", "MSFT", "IREN", "INTV"}

# ── Adaptive params file path ───────────────────────────────────────────────
# Lives in project root next to config.py
PARAMS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "symbol_params.json"
)

# ── Per-symbol starting defaults (seed values before any trade history) ─────
SYMBOL_DEFAULTS: Dict[str, Dict] = {
    "META":  {"sl": 0.60, "tp": 1.75},
    "PLTR":  {"sl": 0.50, "tp": 1.25},
    "MSFT":  {"sl": 0.50, "tp": 1.25},
    "GOOGL": {"sl": 0.40, "tp": 1.50},
    "AMZN":  {"sl": 0.50, "tp": 1.25},
    "ALAB":  {"sl": 0.40, "tp": 1.00, "min_confidence": 0.58},
    "IREN":  {"sl": 0.35, "tp": 1.00, "min_confidence": 0.60},
    # INTV has no specific default — falls through to GLOBAL_FALLBACK
}

# ── Global fallback for symbols not in SYMBOL_DEFAULTS ─────────────────────
GLOBAL_FALLBACK = {"sl": 0.50, "tp": 1.25}

# ── Constants ───────────────────────────────────────────────────────────────
MIN_RR       = 2.5   # Minimum reward:risk ratio enforced at all times
RECALC_EVERY = 20    # Recalculate after this many closed trades per symbol

# ── File write lock — prevents simultaneous write conflicts ─────────────────
# Two symbols cannot write symbol_params.json at the exact same moment.
_params_lock = threading.Lock()


# ===========================================================================
#  Adaptive params helpers
# ===========================================================================

def _load_params_file() -> Dict:
    """
    Load symbol_params.json from disk.
    Returns empty dict if file doesn't exist or is corrupt — never raises.
    Edge case Q2: file doesn't exist → os.path.exists returns False →
    we skip the open() and return {} safely.
    """
    try:
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logging.getLogger("ScalpMaster").warning(
            f"Could not load {PARAMS_FILE}: {e} — using defaults"
        )
    return {}


def _save_params_file(data: Dict) -> None:
    """
    Write symbol_params.json atomically.
    Uses write-to-temp + os.replace() so a crash mid-write never
    leaves a corrupt file. The threading lock prevents two symbols
    from writing simultaneously (edge case Q6).
    """
    with _params_lock:
        try:
            tmp = PARAMS_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, PARAMS_FILE)  # atomic rename on all OS
        except Exception as e:
            logging.getLogger("ScalpMaster").error(
                f"Failed to save {PARAMS_FILE}: {e}"
            )


def get_symbol_params(symbol: str) -> Dict:
    """
    Return current SL/TP params for a symbol.

    Priority:
      1. Learned params stored in symbol_params.json  (post-recalc)
      2. Per-symbol seed defaults in SYMBOL_DEFAULTS  (first run)
      3. GLOBAL_FALLBACK                              (unknown symbols)

    Edge case Q7: symbol not in SYMBOL_DEFAULTS (e.g. INTV, new crypto)
    → falls through to GLOBAL_FALLBACK, returns sl=0.50, tp=1.25.
    This is safe — conservative defaults, no crash.

    Returns dict with keys: sl, tp, and optionally min_confidence.
    sl/tp are percentages: 0.5 = 0.5%
    """
    sym = symbol.upper()

    # 1. Learned params on disk take highest priority
    stored = _load_params_file()
    if sym in stored and "sl" in stored[sym] and "tp" in stored[sym]:
        return stored[sym]

    # 2. Per-symbol seed default
    if sym in SYMBOL_DEFAULTS:
        return dict(SYMBOL_DEFAULTS[sym])

    # 3. Global fallback
    return dict(GLOBAL_FALLBACK)


def log_trade_result(symbol: str, pnl_pct: float, won: bool) -> None:
    """
    Record a closed scalp trade result for a symbol and trigger
    recalculation if RECALC_EVERY trades have accumulated.

    INTEGRATION NOTE: This function must be called from
    trade_executor.py's close_trade() method when strategy_name
    == "scalp_master". Add after the existing strategy result recording:

        if trade.get("strategy_name") == "scalp_master":
            from strategies.scalp_master import log_trade_result
            log_trade_result(symbol, pnl_pct, trade_won)

    Edge case Q3: bot restarts with 19 trades saved.
    → _load_params_file() reads history list from disk.
    → history already has 19 entries.
    → 20th trade appended → len(history) % 20 == 0 → recalc fires.
    → Trade count resumes correctly from disk, NOT from 0.
    """
    sym = symbol.upper()
    stored = _load_params_file()

    # Initialise symbol entry if missing
    if sym not in stored:
        stored[sym] = {}
    if "history" not in stored[sym]:
        stored[sym]["history"] = []

    # Append this trade's result
    stored[sym]["history"].append({
        "pnl_pct": round(pnl_pct, 4),
        "won":     won
    })

    history = stored[sym]["history"]

    # Trigger recalc every RECALC_EVERY trades
    if len(history) % RECALC_EVERY == 0:
        stored[sym] = _recalculate_params(sym, history, stored[sym])
        logging.getLogger("ScalpMaster").info(
            f"[Adaptive] {sym}: recalculated after {len(history)} trades — "
            f"SL={stored[sym]['sl']:.3f}%  TP={stored[sym]['tp']:.3f}%"
        )

    _save_params_file(stored)


def _recalculate_params(symbol: str, history: list, current: Dict) -> Dict:
    """
    Recalculate SL and TP from actual closed trade history.

    Formula:
      new_sl = avg_actual_loss_pct * 0.85
      new_tp = max(avg_actual_win_pct * 0.90, new_sl * MIN_RR)

    Edge cases:
      Q4 (all winners, avg_loss=0): keeps current SL, recalcs TP only.
      Q5 (TP below 2.5R floor): line "new_tp = max(new_tp, new_sl * MIN_RR)"
         catches this — guaranteed to enforce minimum R:R.
      Fewer than 5 wins or losses: insufficient data, keeps that side unchanged.
    """
    logger = logging.getLogger("ScalpMaster")
    wins   = [abs(t["pnl_pct"]) for t in history if     t["won"]]
    losses = [abs(t["pnl_pct"]) for t in history if not t["won"]]

    # ── Recalculate SL ───────────────────────────────────────────────────
    if len(losses) < 5:
        # Insufficient loss data — keep current SL
        logger.info(f"[Adaptive] {symbol}: {len(losses)} losses < 5 — keeping SL")
        new_sl = current.get("sl", GLOBAL_FALLBACK["sl"])
    else:
        avg_loss = sum(losses) / len(losses)
        if avg_loss == 0:
            # Edge case Q4: all losses were exactly 0% — keep current SL
            logger.info(f"[Adaptive] {symbol}: avg_loss=0 — keeping current SL")
            new_sl = current.get("sl", GLOBAL_FALLBACK["sl"])
        else:
            new_sl = avg_loss * 0.85

    # ── Recalculate TP ───────────────────────────────────────────────────
    if len(wins) < 5:
        logger.info(f"[Adaptive] {symbol}: {len(wins)} wins < 5 — keeping TP")
        new_tp = current.get("tp", GLOBAL_FALLBACK["tp"])
    else:
        avg_win = sum(wins) / len(wins)
        new_tp  = avg_win * 0.90

    # ── Enforce minimum R:R = MIN_RR (2.5) ──────────────────────────────
    # Edge case Q5: this is the exact line that catches TP below the floor.
    new_tp = max(new_tp, new_sl * MIN_RR)

    # ── Clamp to sane operational ranges ────────────────────────────────
    new_sl = max(0.10, min(new_sl, 3.0))   # 0.1% to 3.0%
    new_tp = max(0.25, min(new_tp, 10.0))  # 0.25% to 10.0%

    # Build updated entry — preserve history, min_confidence, and any
    # other fields that may have been stored
    updated = dict(current)
    updated["sl"] = round(new_sl, 4)
    updated["tp"] = round(new_tp, 4)
    return updated


# ===========================================================================
#  Strategy class
# ===========================================================================

class ScalpMaster(BaseStrategy):

    def __init__(self):
        super().__init__()
        self.strategy_name   = "scalp_master"
        # Class-level values are global defaults only.
        # Per-symbol params from get_symbol_params() override at signal time.
        self.stop_loss_pct   = 0.5
        self.take_profit_pct = 1.0
        self.logger = logging.getLogger("ScalpMaster")

    def analyze(
        self,
        symbol: str,
        candles: pd.DataFrame,
        market_condition: str = "unknown"
    ) -> Optional[TradeSignal]:

        # ── Whitelist check ──────────────────────────────────────────────
        if symbol.upper() not in SCALP_WHITELIST:
            self.verbose_log_skip(
                symbol,
                f"Not in scalp whitelist — skipping "
                f"(allowed: {', '.join(sorted(SCALP_WHITELIST))})"
            )
            return None

        # ── Load per-symbol adaptive params ─────────────────────────────
        # Loaded fresh every call so recalculated values are used immediately
        # without requiring a bot restart.
        sym_params   = get_symbol_params(symbol)
        sym_sl       = sym_params.get("sl",             self.stop_loss_pct)
        sym_tp       = sym_params.get("tp",             self.take_profit_pct)
        global_min   = config.SIGNAL_TUNING.get("scalp_min_score", 0.60)
        sym_min_conf = sym_params.get("min_confidence", global_min)

        tuning           = config.SIGNAL_TUNING
        rsi_oversold     = tuning["scalp_rsi_oversold"]
        rsi_overbought   = tuning["scalp_rsi_overbought"]
        rsi_period       = tuning["scalp_rsi_period"]
        min_volume_ratio = tuning["scalp_min_volume_ratio"]

        required = rsi_period + 10
        if not self._check_enough_candles(symbol, candles, required):
            return None

        if market_condition == "ranging":
            self.verbose_log_skip(symbol, "Ranging market — scalp signals unreliable")
            return None

        close  = candles["close"]
        volume = candles["volume"]

        try:
            rsi_series = ta.rsi(close, length=rsi_period)
            if rsi_series is None or rsi_series.isna().all():
                self.verbose_log_skip(symbol, "RSI returned no data")
                return None
        except Exception as e:
            self.verbose_log_skip(symbol, f"RSI error: {e}")
            return None

        current_rsi  = rsi_series.iloc[-1]
        previous_rsi = rsi_series.iloc[-2]

        if pd.isna(current_rsi) or pd.isna(previous_rsi):
            self.verbose_log_skip(symbol, "RSI is NaN")
            return None

        avg_volume     = volume.iloc[-20:].mean()
        current_volume = volume.iloc[-1]
        volume_ratio   = current_volume / avg_volume if avg_volume > 0 else 0

        volume_ok = volume_ratio >= min_volume_ratio
        self.verbose_log(
            symbol, "Volume spike confirmation",
            volume_ok, volume_ratio, f">={min_volume_ratio}",
            extra=f"current_vol={current_volume:.0f} avg_vol={avg_volume:.0f}"
        )
        if not volume_ok:
            return None

        # ── LONG SIGNAL ──────────────────────────────────────────────────
        was_oversold   = previous_rsi < rsi_oversold
        now_recovering = current_rsi  >= rsi_oversold

        self.verbose_log(
            symbol, "Scalp: RSI was oversold (long setup)",
            was_oversold, previous_rsi, f"<{rsi_oversold}", "long"
        )

        if was_oversold:
            self.verbose_log(
                symbol, "Scalp: RSI recovering from oversold (long entry)",
                now_recovering, current_rsi, f">={rsi_oversold}", "long"
            )
            if now_recovering:
                score = min(1.0, sym_min_conf + volume_ratio * 0.05)
                self.verbose_log_score(symbol, score, sym_min_conf)
                if score >= sym_min_conf:
                    return self._make_signal(
                        symbol          = symbol,
                        direction       = "long",
                        score           = score,
                        stop_loss_pct   = sym_sl,
                        take_profit_pct = sym_tp,
                        reason          = (
                            f"Scalp long: RSI {previous_rsi:.1f}→{current_rsi:.1f} "
                            f"vol={volume_ratio:.2f}x "
                            f"SL={sym_sl}% TP={sym_tp}%"
                        )
                    )

        # ── SHORT SIGNAL ─────────────────────────────────────────────────
        was_overbought = previous_rsi > rsi_overbought
        now_retreating = current_rsi  <= rsi_overbought

        self.verbose_log(
            symbol, "Scalp: RSI was overbought (short setup)",
            was_overbought, previous_rsi, f">{rsi_overbought}", "short"
        )

        if was_overbought:
            self.verbose_log(
                symbol, "Scalp: RSI retreating from overbought (short entry)",
                now_retreating, current_rsi, f"<={rsi_overbought}", "short"
            )
            if now_retreating:
                score = min(1.0, sym_min_conf + volume_ratio * 0.05)
                self.verbose_log_score(symbol, score, sym_min_conf)
                if score >= sym_min_conf:
                    return self._make_signal(
                        symbol          = symbol,
                        direction       = "short",
                        score           = score,
                        stop_loss_pct   = sym_sl,
                        take_profit_pct = sym_tp,
                        reason          = (
                            f"Scalp short: RSI {previous_rsi:.1f}→{current_rsi:.1f} "
                            f"vol={volume_ratio:.2f}x "
                            f"SL={sym_sl}% TP={sym_tp}%"
                        )
                    )

        self.verbose_log(
            symbol, "Scalp: RSI in neutral zone",
            False, current_rsi, f"need <{rsi_oversold} or >{rsi_overbought}"
        )
        return None
