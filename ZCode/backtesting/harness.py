"""
Backtest harness for the MARC strategy.
Runs the strategy across (symbol, timeframe) and prints a stats table that
maps directly onto the success criteria:
    - Win Rate       >= 50%
    - Max Drawdown   <= 20%
    - Profit Factor  >= 1.5
    - Trade count    ~ a few per day over 6 months (hundreds)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

from data_loader import load_data, resample_ohlcv
from strategy import generate_signals

# Crypto spot costs (Binance-base tier taker 0.1% per side), per crypto rules.
FEES = 0.001
INIT_CASH = 10_000


def _tf_to_resample(tf: str) -> str | None:
    return {"5m": None, "15m": "15min", "1h": "1h"}.get(tf)


def _freq_str(tf: str) -> str:
    return {"5m": "5min", "15m": "15min", "1h": "1h"}[tf]


def _days_in(df: pd.DataFrame) -> float:
    return (df.index[-1] - df.index[0]).total_seconds() / 86400.0


def run_one(symbol: str, tf: str, params: dict | None = None,
            direction: str = "both", silent: bool = False) -> dict:
    """Backtest MARC on symbol@tf. Returns a metrics dict."""
    df = load_data(symbol, "5m", days=200)
    rule = _tf_to_resample(tf)
    if rule:
        df = resample_ohlcv(df, rule)

    sigs = generate_signals(df, params)
    # support both v1 (7-tuple) and v2 (8-tuple with trailing)
    if len(sigs) == 8:
        le, lx, se, sx, sl_stop, tp_stop, trailing, max_hold = sigs
    else:
        le, lx, se, sx, sl_stop, tp_stop, max_hold = sigs
        trailing = None
    close = df["close"]

    common = dict(
        init_cash=INIT_CASH,
        fees=FEES,
        freq=_freq_str(tf),
        min_size=0.0,
        size_granularity=np.nan,   # fractional crypto; v1.0 needs NaN not 0
    )
    # only pass stops that are actually set (lifecycle may fully manage exits)
    if sl_stop is not None:
        common["sl_stop"] = sl_stop
    if tp_stop is not None:
        common["tp_stop"] = tp_stop
    if trailing is not None:
        common["sl_trail"] = trailing

    EMPTY = pd.Series(False, index=close.index)
    if direction == "both":
        pf = vbt.Portfolio.from_signals(
            close,
            entries=le, exits=lx,
            short_entries=se, short_exits=sx,
            **common)
    elif direction == "long":
        pf = vbt.Portfolio.from_signals(
            close,
            entries=le, exits=lx, short_entries=EMPTY, short_exits=EMPTY,
            direction="longonly", **common)
    elif direction == "short":
        pf = vbt.Portfolio.from_signals(
            close,
            short_entries=se, short_exits=sx, direction="shortonly",
            **common)
    else:
        raise ValueError(direction)

    n_trades = pf.trades.count()
    days = _days_in(df)
    wr = pf.trades.win_rate() if n_trades else float("nan")
    pf_factor = pf.trades.profit_factor() if n_trades else float("nan")
    mdd = abs(pf.max_drawdown())
    metrics = {
        "symbol": symbol,
        "tf": tf,
        "dir": direction,
        "trades": int(n_trades),
        "trades_per_day": n_trades / days if days else float("nan"),
        "win_rate": wr,
        "profit_factor": pf_factor,
        "total_return": pf.total_return(),
        "max_drawdown": mdd,
        "sharpe": pf.sharpe_ratio(),
        "sortino": pf.sortino_ratio(),
        "expectancy": pf.trades.expectancy() if n_trades else float("nan"),
        "final_value": pf.value().iloc[-1],
    }
    if not silent:
        print(f"  {symbol:7s} {tf:3s} {direction:5s} | trades={n_trades:4d} "
              f"({n_trades/days:.2f}/d) WR={wr*100:5.1f}% PF={pf_factor:5.2f} "
              f"ret={pf.total_return()*100:6.2f}% MDD={mdd*100:5.1f}% "
              f"Sharpe={pf.sharpe_ratio():5.2f}")
    return metrics


def run_grid(params=None, symbols=("BTC/USD", "ETH/USD"),
             tfs=("5m", "15m", "1h"), directions=("both", "long", "short")):
    print("=" * 100)
    print("MARC backtest grid")
    print("=" * 100)
    rows = []
    for sym in symbols:
        for tf in tfs:
            for d in directions:
                rows.append(run_one(sym, tf, params, d))
    df = pd.DataFrame(rows)
    print("\n" + "=" * 100)
    print("SUMMARY (criteria: WR>=50%, MDD<=20%, PF>=1.5, ~few trades/day)")
    print("=" * 100)
    show = df[["symbol", "tf", "dir", "trades", "trades_per_day",
               "win_rate", "profit_factor", "total_return", "max_drawdown", "sharpe"]]
    print(show.to_string(index=False,
          formatters={"win_rate": lambda v: f"{v*100:.1f}%",
                      "total_return": lambda v: f"{v*100:.2f}%",
                      "max_drawdown": lambda v: f"{v*100:.1f}%",
                      "profit_factor": lambda v: f"{v:.2f}",
                      "sharpe": lambda v: f"{v:.2f}",
                      "trades_per_day": lambda v: f"{v:.2f}"}))
    # criteria pass count (both-direction rows, averaged across symbols/tfs)
    both = df[df["dir"] == "both"]
    passes = {
        "WR>=50%": (both["win_rate"] >= 0.50).sum(),
        "MDD<=20%": (both["max_drawdown"] <= 0.20).sum(),
        "PF>=1.5": (both["profit_factor"] >= 1.5).sum(),
    }
    print(f"\nCriteria passes (both-direction, {len(both)} configs): {passes}")
    return df


if __name__ == "__main__":
    import sys
    from strategy import DEFAULT_PARAMS
    params = DEFAULT_PARAMS
    run_grid(params)
