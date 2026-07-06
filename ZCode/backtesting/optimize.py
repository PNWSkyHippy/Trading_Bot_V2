"""
Parameter optimization for the VTRT strategy (v7 structure).

Approach: grid search over the parameters that control the WR vs R:R tradeoff.
We evaluate each combination on BOTH symbols and pick params that are robust
(perform well on both, not curve-fit to one). The objective is a custom score
that rewards PF, penalizes drawdown, and requires minimum trade count.

Objective score = profit_factor - 2.0 * max_drawdown   (if trades >= 30)
                  (filtered out otherwise)

We log every combination to CSV and print the top 15 by score.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
from tqdm import tqdm

from data_loader import load_data, resample_ohlcv
from strategy import generate_signals

FEES = 0.001
INIT_CASH = 10_000
CACHE = Path(__file__).resolve().parent / "cache"


def _load_tf(symbol: str, tf: str) -> pd.DataFrame:
    df5 = load_data(symbol, "5m", days=200)
    rule = {"5m": None, "15m": "15min", "1h": "1h"}[tf]
    return resample_ohlcv(df5, rule) if rule else df5


def _freq(tf: str) -> str:
    return {"5m": "5min", "15m": "15min", "1h": "1h"}[tf]


def _backtest(close, le, lx, se, sx, sl_stop, tp_stop, trailing, max_hold, tf, direction="both"):
    common = dict(init_cash=INIT_CASH, fees=FEES, freq=_freq(tf),
                  min_size=0.0, size_granularity=np.nan)
    if sl_stop is not None:
        common["sl_stop"] = sl_stop
    if tp_stop is not None:
        common["tp_stop"] = tp_stop
    if trailing is not None:
        common["sl_trail"] = trailing
    EMPTY = pd.Series(False, index=close.index)
    if direction == "both":
        pf = vbt.Portfolio.from_signals(close, entries=le, exits=lx,
                                        short_entries=se, short_exits=sx, **common)
    elif direction == "long":
        pf = vbt.Portfolio.from_signals(close, entries=le, exits=lx,
                                        short_entries=EMPTY, short_exits=EMPTY,
                                        direction="longonly", **common)
    else:
        pf = vbt.Portfolio.from_signals(close, short_entries=se, short_exits=sx,
                                        direction="shortonly", **common)
    n = pf.trades.count()
    return {
        "trades": int(n),
        "win_rate": float(pf.trades.win_rate()) if n else float("nan"),
        "profit_factor": float(pf.trades.profit_factor()) if n else 0.0,
        "total_return": float(pf.total_return()),
        "max_drawdown": float(abs(pf.max_drawdown())),
        "sharpe": float(pf.sharpe_ratio()),
    }


# Parameter grid -- final pass. Goal: PF>=1.5 AND >=300 trades (few/day),
# robust across BOTH symbols. Using consec=1 (more trades) but keeping the
# strict S threshold + a 2-bar ADX trend confirmation for WR preservation.
GRID = {
    "ema_trend":     [50],
    "adx_period":    [14],
    "adx_min":       [20.0, 25.0, 30.0],
    "rsi_period":    [2],
    "rsi_long_max":  [10, 15],
    "rsi_short_min": [80, 85, 90],
    "consec_bars":   [1],
    "ema_exit":      [5, 8, 13],
    "sl_atr_mult":   [0.8, 1.0, 1.3],
    "tp_atr_mult":   [0.0],
    "max_hold":      [24, 48],
    "close_pos_min": [0.40, 0.45],
    "close_pos_max": [0.55, 0.60],
}


def _score(m):
    """Robustness-weighted objective. m is the cross-symbol aggregate.

    Key anti-overfit rule: each symbol must be profitable on its own (not just
    on the average). Rewards PF, requires a healthy trade count, penalizes DD.
    """
    if not np.isfinite(m["profit_factor"]):
        return -999.0
    if m["min_symbol_return"] < 0:        # both symbols must be green
        return -998.0
    pf = min(m["profit_factor"], 5.0)
    trades = m["trades_total"]
    # core: PF above 1.5, scaled by trade-count confidence, minus DD penalty
    base = pf - 1.5
    trade_bonus = min(trades / 300.0, 1.5)        # reward up to 300+ trades
    return base + 0.5 * trade_bonus - 2.0 * m["max_drawdown"]


def run_optimization(tf: str = "1h", direction: str = "both",
                     symbols=("BTC/USD", "ETH/USD")):
    print(f"=== Optimizing VTRT on {tf} / {direction} ===")
    data = {s: _load_tf(s, tf) for s in symbols}

    keys = list(GRID.keys())
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    print(f"Grid size: {len(combos)} combinations x {len(symbols)} symbols")

    results = []
    for combo in tqdm(combos, desc=f"opt {tf}/{direction}"):
        params = dict(zip(keys, combo))
        per_symbol_metrics = []
        skip = False
        for sym in symbols:
            df = data[sym]
            try:
                le, lx, se, sx, sl, tp, tr, mh = generate_signals(df, params)
            except Exception:
                skip = True
                break
            m = _backtest(df["close"], le, lx, se, sx, sl, tp, tr, mh, tf, direction)
            m["symbol"] = sym
            per_symbol_metrics.append(m)
        if skip:
            continue
        # aggregate across symbols (mean), require each to have trades
        trades = [m["trades"] for m in per_symbol_metrics]
        if min(trades) < 15:
            continue
        agg = {
            "trades_total": sum(trades),
            "win_rate": float(np.mean([m["win_rate"] for m in per_symbol_metrics])),
            "profit_factor": float(np.mean([m["profit_factor"] for m in per_symbol_metrics])),
            "total_return": float(np.mean([m["total_return"] for m in per_symbol_metrics])),
            "min_symbol_return": float(np.min([m["total_return"] for m in per_symbol_metrics])),
            "max_drawdown": float(np.max([m["max_drawdown"] for m in per_symbol_metrics])),
            "sharpe": float(np.mean([m["sharpe"] for m in per_symbol_metrics])),
            "trades_btc": trades[0], "trades_eth": trades[1],
        }
        agg["score"] = _score(agg)
        agg["params"] = params
        results.append(agg)

    if not results:
        print("No valid combinations.")
        return None

    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values("score", ascending=False).reset_index(drop=True)

    out_csv = Path(__file__).resolve().parent / f"opt_results_{tf}_{direction}.csv"
    flat = df_res.copy()
    for k in keys:
        flat[k] = flat["params"].apply(lambda d, k=k: d[k])
    flat = flat.drop(columns=["params"])
    flat.to_csv(out_csv, index=False)
    print(f"\nSaved {len(flat)} combinations to {out_csv}")

    print(f"\n--- TOP 15 by score ({tf}/{direction}) ---")
    print(f"{'rank':4} {'score':7} {'PF':6} {'WR':6} {'ret%':8} {'MDD%':6} {'trades':7} {'sharpe':7}  params")
    for i, row in df_res.head(15).iterrows():
        pp = row["params"]
        pstr = (f"adx>={pp['adx_min']:.0f} rsi{pp['rsi_period']} "
                f"L<{pp['rsi_long_max']} S>{pp['rsi_short_min']} "
                f"emaX{pp['ema_exit']} sl{pp['sl_atr_mult']}")
        print(f"{i:4} {row['score']:7.3f} {row['profit_factor']:6.2f} "
              f"{row['win_rate']*100:5.1f}% {row['total_return']*100:7.2f}% "
              f"{row['max_drawdown']*100:5.1f}% {int(row['trades_total']):7} "
              f"{row['sharpe']:7.2f}  {pstr}")
    return df_res


if __name__ == "__main__":
    import sys
    tf = sys.argv[1] if len(sys.argv) > 1 else "1h"
    direction = sys.argv[2] if len(sys.argv) > 2 else "both"
    run_optimization(tf, direction)
