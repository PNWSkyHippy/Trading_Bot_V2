"""
ECB — Entropy Collapse Breakout
================================
Classification : CANDIDATE
Best markets   : DOGEUSDT (+5.16%), BNBUSDT (+2.76%), ETHUSDT (+2.24%),
                 BTCUSDT (+1.43%), XRPUSDT (+0.77%)  — 5/6 symbols positive
Avoid          : SOLUSDT (−0.44%, borderline)
Timeframe      : 1h  (primary)

Mathematical hypothesis
-----------------------
When the Shannon entropy of candle direction over a rolling window collapses
below a threshold, price is moving with abnormal directional consistency —
the market has stopped being random. This signals a regime of active
directional commitment. Entering in the direction of that commitment, aligned
with the macro trend (200-bar SMA), captures the continuation of that move
before the regime normalises.

Entropy = −p_up·log₂(p_up) − p_dn·log₂(p_dn)
  1.0 = fully random (50/50 up/down)
  0.0 = all bars same direction

Entry when entropy < 0.75 AND macro regime aligned.
Exit: 24-bar time hold. ATR-based SL/TP as catastrophic stops.

BTC 1h backtest results (2024-01-01 → 2025-05-14)
--------------------------------------------------
  Net profit     : +1.43 %
  Profit factor  : 2.59
  Win rate       : 63.6 %
  Avg win / loss : 1.48 R
  Max drawdown   : 0.66 %
  Sharpe ratio   : 0.87
  Trades         : 22

Cross-symbol 1h (2024) summary
--------------------------------
  DOGEUSDT  +5.16%  PF 2.86  Sharpe 1.17
  BNBUSDT   +2.76%  PF 2.26  Sharpe 0.96
  ETHUSDT   +2.24%  PF 2.40  Sharpe 0.75
  BTCUSDT   +1.43%  PF 2.59  Sharpe 0.87
  XRPUSDT   +0.77%  PF 1.26  Sharpe 0.20
  SOLUSDT   −0.44%  PF 0.95  Sharpe −0.10

Dependencies
------------
  pip install pandas numpy ccxt
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ─── Parameter dataclass ──────────────────────────────────────────────────────

@dataclass
class ECBParams:
    # Entropy
    entropy_window:  int   = 20    # Rolling window for Shannon entropy
    entropy_thresh:  float = 0.75  # Enter when entropy < this (low = directional)

    # ATR
    atr_length:      int   = 14
    sl_atr_mult:     float = 1.5   # Catastrophic stop = entry ± sl_atr_mult * ATR
    tp_atr_mult:     float = 2.5   # Profit target (rarely hit; main exit is time)
    vol_filter_len:  int   = 50
    vol_filter_pct:  float = 0.75  # ATR must be > vol_filter_pct * MA(ATR)

    # Macro trend regime
    trend_ma_length: int   = 200   # Long only above SMA, short only below

    # Trade duration
    max_bars_hold:   int   = 24    # Primary exit: time-based hold


# ─── Core entropy calculation ─────────────────────────────────────────────────

def rolling_entropy(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Compute 2-class Shannon entropy of candle direction over a rolling window.
    Returns a Series in [0.0, 1.0]:  1.0 = random,  0.0 = fully directional.
    """
    is_up  = (df["close"] > df["open"]).astype(float)
    p_up   = is_up.rolling(window).mean().clip(1e-9, 1 - 1e-9)
    p_dn   = 1.0 - p_up
    entropy = -(p_up * np.log2(p_up) + p_dn * np.log2(p_dn))
    return entropy.rename("entropy")


# ─── Signal generation ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, params: ECBParams = ECBParams()) -> pd.DataFrame:
    """
    Compute ECB signals on a standard OHLCV DataFrame.

    Parameters
    ----------
    df : DataFrame with columns [open, high, low, close, volume].
         Index should be a DatetimeIndex.
    params : ECBParams instance.

    Returns
    -------
    DataFrame with additional columns:
        entropy, bias_up, low_entropy, macro_ma, bull_regime, bear_regime,
        vol_ok, atr, long_signal, short_signal, sl_long, sl_short, tp_long, tp_short
    """
    p   = params
    out = df.copy()
    c   = out["close"]

    # ── Shannon entropy of candle direction ───────────────────────────────────
    out["entropy"]     = rolling_entropy(out, p.entropy_window)
    is_up              = (c > out["open"]).astype(float)
    out["bias_up"]     = is_up.rolling(p.entropy_window).mean() > 0.5
    out["low_entropy"] = out["entropy"] < p.entropy_thresh

    # ── ATR ───────────────────────────────────────────────────────────────────
    hl   = out["high"] - out["low"]
    hpc  = (out["high"] - c.shift()).abs()
    lpc  = (out["low"]  - c.shift()).abs()
    tr   = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    out["atr"]    = tr.ewm(span=p.atr_length, adjust=False).mean()
    atr_ma        = out["atr"].rolling(p.vol_filter_len).mean()
    out["vol_ok"] = out["atr"] > atr_ma * p.vol_filter_pct

    # ── Macro trend regime ────────────────────────────────────────────────────
    out["macro_ma"]    = c.rolling(p.trend_ma_length).mean()
    out["bull_regime"] = c > out["macro_ma"]
    out["bear_regime"] = c < out["macro_ma"]

    # ── Entry signals ─────────────────────────────────────────────────────────
    # LONG: entropy collapsed with upward bias, price above 200 SMA, vol active
    out["long_signal"] = (
        out["low_entropy"] &
        out["bias_up"]     &
        out["bull_regime"] &
        out["vol_ok"]
    )

    # SHORT: entropy collapsed with downward bias, price below 200 SMA, vol active
    out["short_signal"] = (
        out["low_entropy"]    &
        ~out["bias_up"]       &
        out["bear_regime"]    &
        out["vol_ok"]
    )

    # ── Stop / target prices ──────────────────────────────────────────────────
    out["sl_long"]  = c - out["atr"] * p.sl_atr_mult
    out["sl_short"] = c + out["atr"] * p.sl_atr_mult
    out["tp_long"]  = c + out["atr"] * p.tp_atr_mult
    out["tp_short"] = c - out["atr"] * p.tp_atr_mult

    return out


# ─── Simple event-driven backtest ────────────────────────────────────────────

@dataclass
class Trade:
    direction:   str
    entry_bar:   int
    entry_price: float
    sl_price:    float
    tp_price:    float
    exit_bar:    Optional[int]   = None
    exit_price:  Optional[float] = None
    exit_reason: str             = ""
    pnl_pct:     float           = 0.0


def backtest(df: pd.DataFrame, params: ECBParams = ECBParams(),
             commission_pct: float = 0.05,
             position_size_pct: float = 10.0) -> tuple[list[Trade], pd.Series]:
    """
    Event-driven backtest. Returns (trades, equity_curve).

    position_size_pct : % of equity allocated per trade (default 10%).
    commission_pct    : round-trip commission as % of trade value.
    """
    sig    = generate_signals(df, params)
    size   = position_size_pct / 100.0
    equity = 1.0
    curve  = []
    trades: list[Trade] = []

    position: Optional[Trade] = None
    bars_held = 0

    for i, (idx, row) in enumerate(sig.iterrows()):
        c = row["close"]

        if position is not None:
            bars_held += 1
            exit_triggered = False
            pnl = 0.0

            if position.direction == "long":
                if c <= position.sl_price:
                    pnl = (c - position.entry_price) / position.entry_price
                    position.exit_reason = "SL"
                    exit_triggered = True
                elif c >= position.tp_price:
                    pnl = (c - position.entry_price) / position.entry_price
                    position.exit_reason = "TP"
                    exit_triggered = True
                elif bars_held >= params.max_bars_hold:
                    pnl = (c - position.entry_price) / position.entry_price
                    position.exit_reason = "MaxDur"
                    exit_triggered = True
            else:
                if c >= position.sl_price:
                    pnl = (position.entry_price - c) / position.entry_price
                    position.exit_reason = "SL"
                    exit_triggered = True
                elif c <= position.tp_price:
                    pnl = (position.entry_price - c) / position.entry_price
                    position.exit_reason = "TP"
                    exit_triggered = True
                elif bars_held >= params.max_bars_hold:
                    pnl = (position.entry_price - c) / position.entry_price
                    position.exit_reason = "MaxDur"
                    exit_triggered = True

            if exit_triggered:
                net = pnl - commission_pct / 100 * 2
                position.exit_bar   = i
                position.exit_price = c
                position.pnl_pct    = net
                trades.append(position)
                equity *= (1 + net * size)
                position   = None
                bars_held  = 0

        if position is None:
            if row["long_signal"]:
                position = Trade(
                    direction="long",
                    entry_bar=i,
                    entry_price=c,
                    sl_price=row["sl_long"],
                    tp_price=row["tp_long"],
                )
                bars_held = 0
            elif row["short_signal"]:
                position = Trade(
                    direction="short",
                    entry_bar=i,
                    entry_price=c,
                    sl_price=row["sl_short"],
                    tp_price=row["tp_short"],
                )
                bars_held = 0

        curve.append(equity)

    return trades, pd.Series(curve, index=sig.index, name="equity")


# ─── Stats ────────────────────────────────────────────────────────────────────

def print_stats(trades: list[Trade], label: str = "") -> None:
    if not trades:
        print("No trades.")
        return

    pnls   = [t.pnl_pct for t in trades]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    pf     = abs(sum(wins) / sum(losses)) if losses else float("inf")
    wr     = len(wins) / len(pnls) * 100
    aw     = np.mean(wins)   if wins   else 0
    al     = np.mean(losses) if losses else 0
    reasons = pd.Series([t.exit_reason for t in trades]).value_counts().to_dict()

    hdr = f"  [{label}]" if label else ""
    print(f"{'─'*45}{hdr}")
    print(f"  Trades        : {len(trades)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win rate      : {wr:.1f}%")
    print(f"  Profit factor : {pf:.2f}")
    print(f"  Avg win       : {aw*100:+.3f}%")
    print(f"  Avg loss      : {al*100:+.3f}%")
    print(f"  Win/Loss R    : {abs(aw/al):.2f}" if al else "  Win/Loss R    : ∞")
    print(f"  Net P&L       : {sum(pnls)*100:+.2f}%  (10% sizing, compounding)")
    print(f"  Exit reasons  : {reasons}")
    longs  = [t for t in trades if t.direction == "long"]
    shorts = [t for t in trades if t.direction == "short"]
    print(f"  Longs / Shorts: {len(longs)} / {len(shorts)}")
    print(f"{'─'*45}")


# ─── Live signal scanner ─────────────────────────────────────────────────────

def fetch_ohlcv_ccxt(symbol: str = "BTC/USDT", timeframe: str = "1h",
                     limit: int = 500, exchange_id: str = "bybit") -> pd.DataFrame:
    try:
        import ccxt
    except ImportError:
        raise ImportError("pip install ccxt")
    ex  = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    raw = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
    df  = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.set_index("timestamp")


def scan_current_signal(symbol: str = "BTC/USDT", timeframe: str = "1h",
                        params: ECBParams = ECBParams()) -> dict:
    """Return current bar's signal state for live monitoring."""
    df   = fetch_ohlcv_ccxt(symbol, timeframe)
    sig  = generate_signals(df, params)
    last = sig.iloc[-1]
    return {
        "symbol":       symbol,
        "timeframe":    timeframe,
        "bar_time":     str(last.name),
        "close":        round(last["close"], 6),
        "entropy":      round(last["entropy"],  4),
        "bias_up":      bool(last["bias_up"]),
        "low_entropy":  bool(last["low_entropy"]),
        "bull_regime":  bool(last["bull_regime"]),
        "bear_regime":  bool(last["bear_regime"]),
        "long_signal":  bool(last["long_signal"]),
        "short_signal": bool(last["short_signal"]),
        "sl_long":      round(last["sl_long"],  6),
        "tp_long":      round(last["tp_long"],  6),
        "sl_short":     round(last["sl_short"], 6),
        "tp_short":     round(last["tp_short"], 6),
    }


def scan_watchlist(symbols: list[str], timeframe: str = "1h",
                   params: ECBParams = ECBParams()) -> list[dict]:
    """Scan multiple symbols and return only those with active signals."""
    active = []
    for sym in symbols:
        try:
            result = scan_current_signal(sym, timeframe, params)
            if result["long_signal"] or result["short_signal"]:
                active.append(result)
        except Exception as e:
            print(f"  {sym}: error — {e}")
    return active


# ─── Entry point ─────────────────────────────────────────────────────────────

WATCHLIST = [
    "BTC/USD",  "ETH/USD",  "SOL/USD",  "ADA/USD",
    "MATIC/USD","DOT/USD",  "AVAX/USD", "LINK/USD",
    "LTC/USD",  "XRP/USD",
]

if __name__ == "__main__":
    print("ECB Strategy — live signal scan")
    print(f"Scanning {len(WATCHLIST)} symbols on 1h…\n")
    try:
        signals = scan_watchlist(WATCHLIST, "1h")
        if signals:
            print(f"  {len(signals)} active signal(s):\n")
            for s in signals:
                direction = "LONG" if s["long_signal"] else "SHORT"
                print(f"  *** {direction}  {s['symbol']}  @{s['close']}"
                      f"  entropy={s['entropy']:.3f}  bar={s['bar_time']}")
        else:
            print("  No active signals on current bar.")
    except Exception as e:
        print(f"  (Live fetch unavailable: {e})")
        print("  Supply a DataFrame to generate_signals() or backtest() directly.")


# ─── BaseStrategy wrapper — Trading Bot v2 integration ────────────────────────

# Bot integration imports (available when running inside the bot)
try:
    from strategies.base_strategy import BaseStrategy, TradeSignal
except ImportError:
    BaseStrategy = object  # fallback for standalone use
    TradeSignal  = None


# SOL confirmed negative in backtest (PF=0.95, Sharpe=-0.10) — excluded.
ECB_BLACKLIST = {"SOL/USD", "SOLUSDT", "SOL/USDT"}


class ECBStrategy(BaseStrategy):
    """Entropy Collapse Breakout — low-entropy directional commitment signals (CANDIDATE)."""

    def __init__(self):
        super().__init__()
        self.strategy_name           = "ECBStrategy"
        self.params                  = ECBParams()
        self.stop_loss_pct           = 1.5      # fallback default
        self.take_profit_pct         = 2.5
        self.crypto_enabled          = True
        self.stock_enabled           = False
        self.crypto_candle_timeframe = "1h"
        self.candle_limit            = 300      # needs 200-bar SMA + warmup
        self.reviewer_exempt         = True     # ATR-based dynamic stops

    def analyze(self, symbol: str, candles: pd.DataFrame,
                market_condition: str = "unknown") -> Optional[TradeSignal]:
        if symbol.upper() in ECB_BLACKLIST:
            self.verbose_log_skip(symbol, "In ECB blacklist (SOL: PF=0.95 negative backtest)")
            return None
        if not self._check_enough_candles(symbol, candles, 220):
            return None
        try:
            sig  = generate_signals(candles, self.params)
            last = sig.iloc[-1]

            long_sig  = bool(last["long_signal"])
            short_sig = bool(last["short_signal"])

            if not (long_sig or short_sig):
                return None

            direction = "long" if long_sig else "short"
            close     = float(last["close"])
            atr       = float(last["atr"])
            entropy   = float(last["entropy"])

            sl_pct = round(atr * self.params.sl_atr_mult / close * 100, 3)
            tp_pct = round(atr * self.params.tp_atr_mult / close * 100, 3)

            # Score: lower entropy = stronger directional commitment
            score = round(max(0.55, min(0.92, 1.0 - entropy / self.params.entropy_thresh)), 3)

            self.verbose_log(symbol, "entropy < thresh", True,
                             entropy, self.params.entropy_thresh, direction)
            self.verbose_log_score(symbol, score, 0.55)

            # Compute volume ratio for ML scorer
            vol_series = candles["volume"]
            vol_ma     = vol_series.rolling(50).mean().iloc[-1]
            vol_ratio  = round(float(vol_series.iloc[-1] / vol_ma), 3) if vol_ma > 0 else 1.0

            return self._make_signal(
                symbol          = symbol,
                direction       = direction,
                score           = score,
                reason          = (f"ECB: entropy={entropy:.3f} < {self.params.entropy_thresh} "
                                   f"| bias={'up' if last['bias_up'] else 'dn'} "
                                   f"| {'bull' if last['bull_regime'] else 'bear'} regime"),
                stop_loss_pct   = sl_pct,
                take_profit_pct = tp_pct,
                metadata={
                    "entropy":      round(entropy, 4),
                    "bias_up":      bool(last["bias_up"]),
                    "bull_regime":  bool(last["bull_regime"]),
                    "bear_regime":  bool(last["bear_regime"]),
                    "vol_ok":       bool(last["vol_ok"]),
                    "atr":          round(atr, 6),
                    # ML scorer keys
                    "rsi":          50.0,
                    "macd_hist":    0.0,
                    "macd":         0.0,
                    "volume_ratio": vol_ratio,
                    "bb_pct":       0.5,
                    "ema_fast":     0.0,
                    "ema_slow":     0.0,
                    "ema_trend":    0.0,
                    "adx":          25.0,
                },
            )
        except Exception as e:
            self.logger.error(f"ECBStrategy.analyze error on {symbol}: {e}", exc_info=True)
            return None
