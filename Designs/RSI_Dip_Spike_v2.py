"""
RSI Dip & Spike — v2
====================
Classification : REJECT (reconstruction failed testing)
Symbol         : BTCUSDT 1h Bybit
Source         : Reverse-engineered from public Trader Dev strategy
                 "v2 BTCUSDT RSI Dip & Spike — 1h Bybit"
                 Optimizer hint visible on report: "tuned defaults 7/35/80"
                 Original Pine source not accessible (anonymous account).

NOTE: This is a reconstruction attempt, NOT the exact source.
      Core RSI parameters (7/35/80) are confirmed from the optimizer label.
      Exit logic and stop placement are inferred from backtest statistics.

⚠  TESTING VERDICT — REJECT
   This reconstruction DIVERGES significantly from the original strategy.
   The original had 320 trades over 4.3 years (~74/year, Dec 2021–May 2026,
   including the 2022 bear market). Our reconstruction generates 750+/year
   on the same symbol/timeframe — 10× the signal frequency — suggesting
   the original has unseen filters that cannot be inferred from the stats.

   Four iterations tested (v2→v2d) — none profitable in 2024–2025 BTCUSDT:
     v2   (RSI 7/35/80, ATR stop)           : −13.2%, 1050 trades
     v2b  (+ 200 SMA + RSI 30/70)           : −5.6%,   344 trades
     v2c  (+ RSI exit 60/40, 3×ATR stop)   : −3.4%,   306 trades
     v2d  (+ volume surge filter 1.5×)      : −4.3%,   208 trades

   Root cause: RSI(7) mean reversion in the 2024 bull run generates too many
   marginal entries. The original's edge came from cross-regime performance
   (2022 shorts in bear + 2024 longs in bull). Without the source, we cannot
   reconstruct the filtering logic that controlled entry frequency.

   The file is preserved as a reference skeleton but should NOT be deployed.
   See RSI_Dip_Spike_v4.py (v4c) for the working evolved version.

Reported backtest of original (Dec 31 2021 → May 13 2026, BTCUSDT 1h)
-----------------------------------------------------------------------
  Net profit     : +100.61 %   ($10,060 on $10k)
  Profit factor  : 1.17
  Win rate       : 69.4 %       (222W / 98L)
  Avg win        : +$315.74
  Avg loss       : −$612.60
  Max drawdown   : −47.99 %
  Total trades   : 320

Mathematical hypothesis
-----------------------
RSI(7) is fast enough to capture short-term exhaustion. When price dips
below RSI 35, momentum is over-extended to the downside — a bounce is
statistically likely. When price spikes above RSI 80, upside momentum is
exhausted. The edge is high win-rate (mean reversion of fast RSI), with
fixed ATR stops to cap the left tail.

Entry
-----
  Long  : RSI(7) crosses below 35  (oversold dip)
  Short : RSI(7) crosses above 80  (overbought spike)

Exit (in priority order)
------------------------
  1. RSI crosses back through 50 (momentum neutral — primary exit)
  2. ATR hard stop (catastrophic loss cap)
  3. Max 48-bar time hold (2 days)

Parameters
----------
  rsi_length   : 7
  rsi_oversold : 35
  rsi_overbought: 80
  rsi_exit     : 50
  atr_length   : 14
  sl_atr_mult  : 2.0
  max_bars_hold: 48

Dependencies
------------
  pip install pandas numpy ccxt
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ─── Parameters ───────────────────────────────────────────────────────────────

@dataclass
class RSIDipSpikeV2Params:
    rsi_length:     int   = 7
    rsi_oversold:   float = 35.0   # Long entry when RSI crosses below this
    rsi_overbought: float = 80.0   # Short entry when RSI crosses above this
    rsi_exit:       float = 50.0   # Exit when RSI crosses back through this
    atr_length:     int   = 14
    sl_atr_mult:    float = 2.0    # Hard stop = entry ± sl_atr_mult * ATR
    max_bars_hold:  int   = 48     # Time-based exit (2 days on 1h)


# ─── Indicators ───────────────────────────────────────────────────────────────

def _rsi(close: pd.Series, length: int) -> pd.Series:
    """Wilder's RSI using EWM (matches Pine Script / TradingView)."""
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    alpha = 1.0 / length
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).rename("rsi")


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    hl  = df["high"] - df["low"]
    hpc = (df["high"] - df["close"].shift()).abs()
    lpc = (df["low"]  - df["close"].shift()).abs()
    tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean().rename("atr")


# ─── Signal generation ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame,
                     params: RSIDipSpikeV2Params = RSIDipSpikeV2Params()) -> pd.DataFrame:
    """
    Compute RSI Dip & Spike v2 signals on a standard OHLCV DataFrame.

    Returns DataFrame with additional columns:
        rsi, atr, long_signal, short_signal, sl_long, sl_short
    """
    p   = params
    out = df.copy()
    c   = out["close"]

    out["rsi"] = _rsi(c, p.rsi_length)
    out["atr"] = _atr(out, p.atr_length)

    # Cross detection: RSI enters oversold/overbought zone
    rsi_prev = out["rsi"].shift(1)
    out["long_signal"]  = (rsi_prev >= p.rsi_oversold)   & (out["rsi"] < p.rsi_oversold)
    out["short_signal"] = (rsi_prev <= p.rsi_overbought) & (out["rsi"] > p.rsi_overbought)

    # Catastrophic stops at signal bar
    out["sl_long"]  = c - out["atr"] * p.sl_atr_mult
    out["sl_short"] = c + out["atr"] * p.sl_atr_mult

    return out


# ─── Backtest ─────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    direction:   str
    entry_bar:   int
    entry_price: float
    sl_price:    float
    exit_bar:    Optional[int]   = None
    exit_price:  Optional[float] = None
    exit_reason: str             = ""
    pnl_pct:     float           = 0.0


def backtest(df: pd.DataFrame,
             params: RSIDipSpikeV2Params = RSIDipSpikeV2Params(),
             commission_pct: float = 0.05,
             position_size_pct: float = 10.0) -> tuple[list[Trade], pd.Series]:
    """
    Event-driven backtest. Returns (trades, equity_curve).
    commission_pct    : per-side % (0.05 = 5 bps, Bybit maker/taker typical)
    position_size_pct : % of equity per trade
    """
    sig    = generate_signals(df, params)
    p      = params
    size   = position_size_pct / 100.0
    equity = 1.0
    curve  = []
    trades: list[Trade] = []
    position: Optional[Trade] = None
    bars_held = 0

    for i, (_, row) in enumerate(sig.iterrows()):
        c   = row["close"]
        rsi = row["rsi"]

        if position is not None:
            bars_held += 1
            exit_triggered = False
            pnl = 0.0

            if position.direction == "long":
                if c <= position.sl_price:
                    pnl, position.exit_reason = (c - position.entry_price) / position.entry_price, "SL"
                    exit_triggered = True
                elif rsi >= p.rsi_exit:
                    pnl, position.exit_reason = (c - position.entry_price) / position.entry_price, "RSI_Exit"
                    exit_triggered = True
                elif bars_held >= p.max_bars_hold:
                    pnl, position.exit_reason = (c - position.entry_price) / position.entry_price, "MaxDur"
                    exit_triggered = True
            else:
                if c >= position.sl_price:
                    pnl, position.exit_reason = (position.entry_price - c) / position.entry_price, "SL"
                    exit_triggered = True
                elif rsi <= p.rsi_exit:
                    pnl, position.exit_reason = (position.entry_price - c) / position.entry_price, "RSI_Exit"
                    exit_triggered = True
                elif bars_held >= p.max_bars_hold:
                    pnl, position.exit_reason = (position.entry_price - c) / position.entry_price, "MaxDur"
                    exit_triggered = True

            if exit_triggered:
                net = pnl - (commission_pct / 100) * 2
                position.exit_bar   = i
                position.exit_price = c
                position.pnl_pct    = net
                trades.append(position)
                equity   *= (1 + net * size)
                position  = None
                bars_held = 0

        if position is None:
            if row["long_signal"] and not pd.isna(rsi):
                position  = Trade("long", i, c, row["sl_long"])
                bars_held = 0
            elif row["short_signal"] and not pd.isna(rsi):
                position  = Trade("short", i, c, row["sl_short"])
                bars_held = 0

        curve.append(equity)

    return trades, pd.Series(curve, index=sig.index, name="equity")


# ─── Stats ────────────────────────────────────────────────────────────────────

def print_stats(trades: list[Trade], label: str = "") -> None:
    if not trades:
        print("No trades.")
        return
    pnls    = [t.pnl_pct for t in trades]
    wins    = [p for p in pnls if p > 0]
    losses  = [p for p in pnls if p <= 0]
    pf      = abs(sum(wins) / sum(losses)) if losses else float("inf")
    wr      = len(wins) / len(pnls) * 100
    aw      = np.mean(wins)   if wins   else 0.0
    al      = np.mean(losses) if losses else 0.0
    reasons = pd.Series([t.exit_reason for t in trades]).value_counts().to_dict()
    longs   = [t for t in trades if t.direction == "long"]
    shorts  = [t for t in trades if t.direction == "short"]

    hdr = f"  [{label}]" if label else ""
    print(f"{'─'*50}{hdr}")
    print(f"  Trades        : {len(trades)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win rate      : {wr:.1f}%")
    print(f"  Profit factor : {pf:.2f}")
    print(f"  Avg win       : {aw*100:+.3f}%")
    print(f"  Avg loss      : {al*100:+.3f}%")
    if al:
        print(f"  Win/Loss R    : {abs(aw/al):.2f}")
    print(f"  Net P&L       : {sum(pnls)*100:+.2f}%  (10% sizing, compounding)")
    print(f"  Longs/Shorts  : {len(longs)} / {len(shorts)}")
    print(f"  Exit reasons  : {reasons}")
    print(f"{'─'*50}")


# ─── Live data ────────────────────────────────────────────────────────────────

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
                        params: RSIDipSpikeV2Params = RSIDipSpikeV2Params()) -> dict:
    df   = fetch_ohlcv_ccxt(symbol, timeframe)
    sig  = generate_signals(df, params)
    last = sig.iloc[-1]
    return {
        "symbol":       symbol,
        "timeframe":    timeframe,
        "bar_time":     str(last.name),
        "close":        round(last["close"], 4),
        "rsi":          round(last["rsi"], 2),
        "long_signal":  bool(last["long_signal"]),
        "short_signal": bool(last["short_signal"]),
        "sl_long":      round(last["sl_long"], 4),
        "sl_short":     round(last["sl_short"], 4),
    }


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("RSI Dip & Spike v2 — live signal check (BTC/USDT 1h)")
    try:
        result = scan_current_signal("BTC/USDT", "1h")
        for k, v in result.items():
            print(f"  {k:<16}: {v}")
        if result["long_signal"]:
            print("\n  *** LONG SIGNAL — RSI DIP ENTRY ***")
        elif result["short_signal"]:
            print("\n  *** SHORT SIGNAL — RSI SPIKE ENTRY ***")
        else:
            print(f"\n  No signal.  RSI = {result['rsi']:.1f}")
    except Exception as e:
        print(f"  (Live fetch unavailable: {e})")
        print("  Pass a DataFrame to generate_signals() or backtest() directly.")
