"""
Multi-strategy harness: runs any strategy module across (symbol, tf, direction)
and prints a stats table mapped to the success criteria.

Usage:
    python harness2.py <strategy_module> [tf1 tf2 ...]
e.g. python harness2.py strategy_vbm 5m 15m 1h
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

from data_loader import load_data, resample_ohlcv

FEES = 0.001
INIT_CASH = 10_000


def _tf_resample(tf):
    return {"5m": None, "15m": "15min", "1h": "1h"}.get(tf)


def _freq(tf):
    return {"5m": "5min", "15m": "15min", "1h": "1h"}[tf]


def run_one(symbol, tf, generate_signals, params=None, direction="both"):
    df5 = load_data(symbol, "5m", days=200)
    rule = _tf_resample(tf)
    df = resample_ohlcv(df5, rule) if rule else df5

    sigs = generate_signals(df, params)
    if len(sigs) == 8:
        le, lx, se, sx, sl, tp, tr, mh = sigs
    else:
        le, lx, se, sx, sl, tp, mh = sigs
        tr = None
    close = df["close"]

    common = dict(init_cash=INIT_CASH, fees=FEES, freq=_freq(tf),
                  min_size=0.0, size_granularity=np.nan)
    if sl is not None:
        common["sl_stop"] = sl
    if tp is not None:
        common["tp_stop"] = tp
    if tr is not None:
        common["sl_trail"] = tr

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
    days = (df.index[-1] - df.index[0]).total_seconds() / 86400
    return {
        "symbol": symbol, "tf": tf, "dir": direction,
        "trades": int(n),
        "trades_per_day": n / days if days else np.nan,
        "win_rate": float(pf.trades.win_rate()) if n else np.nan,
        "profit_factor": float(pf.trades.profit_factor()) if n else np.nan,
        "total_return": float(pf.total_return()),
        "max_drawdown": float(abs(pf.max_drawdown())),
        "sharpe": float(pf.sharpe_ratio()),
    }, pf


def run_grid(mod_name, tfs=("5m", "15m", "1h"),
             symbols=("BTC/USD", "ETH/USD"),
             directions=("both", "long", "short"),
             params=None):
    mod = importlib.import_module(mod_name)
    gen = mod.generate_signals
    pname = mod_name.replace("strategy_", "").upper()
    print("=" * 110)
    print(f"{pname} backtest grid")
    print("=" * 110)
    rows = []
    for sym in symbols:
        for tf in tfs:
            for d in directions:
                m, _ = run_one(sym, tf, gen, params, d)
                rows.append(m)
                print(f"  {sym:7s} {tf:3s} {d:5s} | trades={m['trades']:5d} "
                      f"({m['trades_per_day']:.2f}/d) WR={m['win_rate']*100:5.1f}% "
                      f"PF={m['profit_factor']:5.2f} ret={m['total_return']*100:6.2f}% "
                      f"MDD={m['max_drawdown']*100:5.1f}% Sharpe={m['sharpe']:5.2f}")
    df = pd.DataFrame(rows)
    print("\n" + "=" * 110)
    print(f"CRITERIA CHECK (both-direction configs): WR>=50%  MDD<=20%  PF>=1.5  trades>=300")
    print("=" * 110)
    both = df[df["dir"] == "both"]
    for _, r in both.iterrows():
        wr_ok = r["win_rate"] >= 0.50
        dd_ok = r["max_drawdown"] <= 0.20
        pf_ok = r["profit_factor"] >= 1.5
        n_ok = r["trades"] >= 150  # per-symbol half of 300
        flags = ("WR " + ("Y" if wr_ok else "n") + " DD " + ("Y" if dd_ok else "n") +
                 " PF " + ("Y" if pf_ok else "n") + " N " + ("Y" if n_ok else "n"))
        print(f"  {r['symbol']:7s} {r['tf']:3s}: {flags}  "
              f"(WR={r['win_rate']*100:.0f}% PF={r['profit_factor']:.2f} "
              f"DD={r['max_drawdown']*100:.0f}% N={r['trades']})")
    return df


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "strategy_vbm"
    tfs = sys.argv[2:] if len(sys.argv) > 2 else ("5m", "15m", "1h")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    run_grid(mod, tfs=tfs)
