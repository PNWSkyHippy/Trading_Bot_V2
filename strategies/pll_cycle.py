"""
PLL Cycle Detector
==================
Classification : INCUBATE
Source         : Pine Scripts "PLL inv p96 lock1.2 + F19" (ETHUSDT_60) and
                 "PLL F19+F41d c=1.5 H2" (TraderDev)

Both Pine variants are implemented here via the `use_martingale` parameter.

Core hypothesis
---------------
Price oscillates around a dominant cycle. A Phase-Locked Loop (PLL) — borrowed
from digital signal processing — locks onto that cycle's frequency and tracks its
phase. When the sine of the phase crosses zero upward, the cycle is at its trough
(buy). When it crosses zero downward, the cycle is at its peak (sell/short).

Only trade when the PLL is "locked" — amplitude above a threshold — meaning the
oscillation is coherent enough to trust the phase estimate. This acts as a regime
filter: avoids trending markets where the cycle breaks down.

Algorithm (bar-by-bar, stateful)
---------------------------------
  1. trend   = SMA(close, detrendLen)          -- remove long-term trend
  2. osc     = close - trend                   -- centred oscillator
  3. norm    = osc / RMS(osc, detrendLen)      -- normalise amplitude
  4. PLL inner loop (updates phase, freq, integrator each bar):
       cosRef = cos(phase)  ;  sinRef = sin(phase)
       i_inst = norm × cosRef  ;  q_inst = -norm × sinRef
       iLpf  += lpfAlpha × (i_inst - iLpf)
       qLpf  += lpfAlpha × (q_inst - qLpf)
       phaseErr = 2 × atan(qLpf / (√(iLpf²+qLpf²) + iLpf))
       integrator += Ki × phaseErr
       freq = clamp(nomFreq + Kp×phaseErr + integrator, fMin, fMax)
       phase += freq  (wrap to [0, 2π))
  5. amp  = √(iLpf² + qLpf²)
     lockQ = amp / 0.7071                      -- normalised lock quality
  6. sinP = sin(phase)
     longSig  = sinP crosses above  0  AND locked  AND ready
     shortSig = sinP crosses below  0  AND locked  AND ready

  "Ready" = bar_index > detrendLen + 100  (warmup guard)
  "Locked" = lockQ > lockThresh

Parameters
----------
  PLL inv p96 lock1.2 + F19  (ETHUSDT_60 file):
    centerPeriod=80, detrendLen=180, loopBW=0.05, lpfAlpha=0.13
    lockThresh=1.2, slPct=4.0, tpPct=12.0, use_martingale=False

  PLL F19+F41d c=1.5 H2  (PLL F41d file):
    centerPeriod=96, detrendLen=200, loopBW=0.04, lpfAlpha=0.15
    lockThresh=1.0, slPct=3.0, tpPct=12.0, use_martingale=True, martCap=1.5
"""

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Tuple


# ── Parameters ───────────────────────────────────────────────────────────────

@dataclass
class PLLCycleParams:
    # PLL parameters
    center_period: int   = 96       # dominant cycle period (bars)
    detrend_len:   int   = 200      # SMA detrend + RMS window
    loop_bw:       float = 0.04     # PLL loop bandwidth
    lpf_alpha:     float = 0.15     # LPF smoothing factor
    lock_thresh:   float = 1.0      # minimum lockQ to trade

    # Vol multiplier (F19): position size scales with normalised ATR
    vol_mult_min:  float = 1.0
    vol_mult_max:  float = 1.5
    atr_length:    int   = 14
    atr_ref_len:   int   = 200      # reference ATR window

    # Martingale (F41d): add martStep × lossStreak to position mult, capped at martCap
    use_martingale: bool  = False
    mart_cap:       float = 1.5
    mart_step:      float = 0.5

    # Trade management
    sl_pct:        float = 3.0
    tp_pct:        float = 12.0


# ── PLL core (stateful, must run bar-by-bar) ──────────────────────────────────

def _run_pll(close: pd.Series,
             center_period: int = 96,
             detrend_len:   int = 200,
             loop_bw:       float = 0.04,
             lpf_alpha:     float = 0.15,
             lock_thresh:   float = 1.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run the Phase-Locked Loop over the full price series.

    Returns (sin_phase, lock_quality, ready_mask) as numpy arrays aligned to `close`.

    sin_phase   : sin(phase) at each bar  — zero-crossings are the signals
    lock_quality: lockQ = amp / 0.7071    — > lock_thresh = PLL locked
    ready_mask  : True once warmup complete (bar_index > detrend_len + 100)
    """
    n       = len(close)
    closes  = close.values.astype(float)

    two_pi   = 2.0 * math.pi
    nom_freq = two_pi / center_period
    f_max    = nom_freq * 2.0
    f_min    = nom_freq * 0.4
    Kp       = 1.4142 * loop_bw
    Ki       = loop_bw * loop_bw

    sin_phase    = np.zeros(n)
    lock_quality = np.zeros(n)
    ready_mask   = np.zeros(n, dtype=bool)

    # State variables
    phase      = 0.0
    freq       = nom_freq
    integrator = 0.0
    i_lpf      = 0.0
    q_lpf      = 0.0

    # Precompute rolling SMA and RMS for detrend
    # Use pandas for efficiency
    s = pd.Series(closes)
    trend_s  = s.rolling(detrend_len).mean().values
    osc_sq_s = (s - pd.Series(trend_s)).pow(2).rolling(detrend_len).mean().values

    for t in range(n):
        # Detrend
        if np.isnan(trend_s[t]) or np.isnan(osc_sq_s[t]):
            sin_phase[t]    = math.sin(phase)
            lock_quality[t] = 0.0
            phase           = (phase + freq) % two_pi
            continue

        osc     = closes[t] - trend_s[t]
        osc_rms = math.sqrt(max(osc_sq_s[t], 1e-10))
        norm    = osc / osc_rms

        warmed  = t > detrend_len + 5

        cos_ref = math.cos(phase)
        sin_ref = math.sin(phase)

        i_inst = norm * cos_ref if warmed else 0.0
        q_inst = -norm * sin_ref if warmed else 0.0

        i_lpf += lpf_alpha * (i_inst - i_lpf)
        q_lpf += lpf_alpha * (q_inst - q_lpf)

        denom = math.sqrt(i_lpf * i_lpf + q_lpf * q_lpf) + i_lpf
        if denom > 1e-10:
            phase_err = 2.0 * math.atan(q_lpf / denom)
        else:
            phase_err = math.pi if q_lpf >= 0 else -math.pi

        if warmed:
            integrator += Ki * phase_err
        else:
            integrator = 0.0

        freq_raw     = nom_freq + Kp * phase_err + integrator
        freq_clamped = max(f_min, min(f_max, freq_raw))
        if freq_clamped != freq_raw:
            integrator = freq_clamped - nom_freq - Kp * phase_err
        freq  = freq_clamped
        phase = (phase + freq) % two_pi

        amp          = math.sqrt(i_lpf * i_lpf + q_lpf * q_lpf)
        lock_quality[t] = amp / 0.7071
        sin_phase[t]    = math.sin(phase)
        ready_mask[t]   = t > detrend_len + 100

    return sin_phase, lock_quality, ready_mask


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    hl  = df["high"] - df["low"]
    hpc = (df["high"] - df["close"].shift()).abs()
    lpc = (df["low"]  - df["close"].shift()).abs()
    tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()


# ── Signal generation ─────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame,
                     params: PLLCycleParams = PLLCycleParams()) -> pd.DataFrame:
    p   = params
    out = df.copy()
    c   = out["close"]

    sin_p, lock_q, ready = _run_pll(
        c,
        center_period = p.center_period,
        detrend_len   = p.detrend_len,
        loop_bw       = p.loop_bw,
        lpf_alpha     = p.lpf_alpha,
        lock_thresh   = p.lock_thresh,
    )

    out["sin_phase"]    = sin_p
    out["lock_quality"] = lock_q
    out["pll_ready"]    = ready
    out["pll_locked"]   = lock_q > p.lock_thresh

    sin_prev = pd.Series(sin_p, index=out.index).shift(1)

    out["long_signal"]  = (
        (sin_prev < 0) & (out["sin_phase"] >= 0) &   # crossover zero
        out["pll_locked"] & out["pll_ready"]
    )
    out["short_signal"] = (
        (sin_prev > 0) & (out["sin_phase"] <= 0) &   # crossunder zero
        out["pll_locked"] & out["pll_ready"]
    )

    # F19 vol multiplier
    out["atr"]     = _atr(out, p.atr_length)
    out["norm_atr"] = out["atr"] / c.replace(0, np.nan)
    out["ref_atr"]  = out["norm_atr"].rolling(p.atr_ref_len).mean()
    out["vol_mult"] = (
        out["norm_atr"] / out["ref_atr"].replace(0, np.nan)
    ).clip(p.vol_mult_min, p.vol_mult_max)

    return out


# ── Bot integration ───────────────────────────────────────────────────────────

try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object
    TradeSignal  = None


class PLLCycleStrategy(BaseStrategy):
    """
    Phase-Locked Loop cycle detector — long/short on PLL sine zero-crossings.
    Only trades when PLL is locked (coherent cycle detected).
    Covers both PLL variants: base (use_martingale=False) and F41d (True).
    """

    def __init__(self, use_martingale: bool = False):
        super().__init__()
        p = PLLCycleParams(use_martingale=use_martingale)
        self.params                  = p
        self.strategy_name           = "pll_cycle_martingale" if use_martingale else "pll_cycle"
        self.stop_loss_pct           = p.sl_pct
        self.take_profit_pct         = p.tp_pct
        self.crypto_enabled          = True
        self.stock_enabled           = False   # designed for crypto 1h cycles
        self.crypto_candle_timeframe = "1h"
        self.time_stop_profile       = "strategy_defined"
        # Need at least detrend_len + 100 bars for warmup
        self.candle_limit            = p.detrend_len + 150

        # Martingale state (live trading — resets on bot restart)
        self._loss_streak: int = 0

    def _vol_score_boost(self, vol_mult: float) -> float:
        return (vol_mult - 1.0) * 0.10

    def _mart_score_boost(self) -> float:
        """F41d: deeper into a loss streak = more conviction needed, lower score."""
        if not self.params.use_martingale:
            return 0.0
        # Martingale increases size but we want the signal score to stay conservative
        return max(-0.05 * self._loss_streak, -0.10)

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional[TradeSignal]:
        p        = self.params
        min_bars = p.detrend_len + 110
        if not self._check_enough_candles(symbol, candles, min_bars):
            return None
        try:
            sig  = generate_signals(candles, p)
            last = sig.iloc[-1]

            long_sig  = bool(last["long_signal"])
            short_sig = bool(last["short_signal"])
            if not (long_sig or short_sig):
                return None

            direction  = "long" if long_sig else "short"
            close      = float(last["close"])
            lock_q     = float(last["lock_quality"])
            vol_m      = float(last["vol_mult"]) if not pd.isna(last["vol_mult"]) else 1.0
            sin_p      = float(last["sin_phase"])

            score = round(max(0.55, min(0.88,
                0.65
                + (lock_q - p.lock_thresh) * 0.08
                + self._vol_score_boost(vol_m)
                + self._mart_score_boost()
            )), 3)

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = (
                    f"PLL: sin={sin_p:.3f} lockQ={lock_q:.2f} "
                    f"volM={vol_m:.2f}"
                    + (" [martingale]" if p.use_martingale else "")
                ),
                stop_loss_pct   = p.sl_pct,
                take_profit_pct = p.tp_pct,
                metadata={
                    "strategy_name":               self.strategy_name,
                    "sin_phase":                   round(sin_p, 4),
                    "lock_quality":                round(lock_q, 4),
                    "vol_mult":                    round(vol_m, 3),
                    "loss_streak":                 self._loss_streak,
                    "use_martingale":              p.use_martingale,
                    "preferred_initial_stop_mode": "fixed_pct",
                    "preferred_trail_mode":        "none",
                },
            )
        except Exception as e:
            self.logger.error(f"PLLCycleStrategy error on {symbol}: {e}", exc_info=True)
            return None

    def _precompute(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        return generate_signals(df, self.params)

    def _analyze_from_precomputed(self, symbol: str, i: int,
                                  sigs: pd.DataFrame, df: pd.DataFrame) -> Optional[TradeSignal]:
        p   = self.params
        row = sigs.iloc[i]

        long_sig  = bool(row["long_signal"])
        short_sig = bool(row["short_signal"])
        if not (long_sig or short_sig):
            return None

        direction = "long" if long_sig else "short"
        lock_q    = float(row["lock_quality"])
        vol_m     = float(row["vol_mult"]) if not pd.isna(row["vol_mult"]) else 1.0
        sin_p     = float(row["sin_phase"])

        score = round(max(0.55, min(0.88,
            0.65
            + (lock_q - p.lock_thresh) * 0.08
            + self._vol_score_boost(vol_m)
        )), 3)

        return self._make_signal(
            symbol          = symbol,
            direction       = direction,
            score           = score,
            reason          = f"PLL: sin={sin_p:.3f} lockQ={lock_q:.2f}",
            stop_loss_pct   = p.sl_pct,
            take_profit_pct = p.tp_pct,
            metadata={
                "strategy_name":               self.strategy_name,
                "sin_phase":                   round(sin_p, 4),
                "lock_quality":                round(lock_q, 4),
                "vol_mult":                    round(vol_m, 3),
                "use_martingale":              p.use_martingale,
                "preferred_initial_stop_mode": "fixed_pct",
                "preferred_trail_mode":        "none",
            },
        )

    def _exit_from_precomputed(self, i: int, sigs: pd.DataFrame,
                               direction: str, meta: dict) -> Optional[str]:
        """PLL uses fixed SL/TP only — no custom exit logic needed."""
        return None

    def check_custom_exit(self, symbol: str, bars: pd.DataFrame,
                          direction: str, entry_metadata: Optional[dict] = None) -> Optional[str]:
        """PLL uses fixed SL/TP only."""
        return None



class PLLCycleMartingaleStrategy(PLLCycleStrategy):
    """Thin wrapper so the backtester can instantiate martingale variant with no args."""
    def __init__(self):
        super().__init__(use_martingale=True)
