"""
RSI Dip & Spike v4c audit — activity + filter sweep
Run: python Scripts/audit_rsi_dip_spike_v1.py

Hypothesis: ADX>=25 is the primary activity bottleneck.
Test: lower ADX, expand symbols, test reclaim vs penetration mode.
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.rsi_dip_spike_v4 import RSIDipSpikeV4Strategy, RSIDipSpikeV4Params

CAPITAL    = 10_000.0
COMMISSION = 0.26
SLIPPAGE   = 0.05
DAYS       = 180
TF         = "1h"

bt = Backtester(starting_capital=CAPITAL)

# Core symbols from validated backtest results
SYMBOLS = ["SOL-USD", "BTC-USD", "ETH-USD", "DOGE-USD", "BNB-USD"]

def run(label, strat, sym):
    df = bt.fetch_history_crypto(sym, DAYS, TF)
    if df is None or len(df) < 220:
        print(f"  {label:<44} [{sym}]: not enough data ({len(df) if df is not None else 0} bars)")
        return
    r = bt._simulate(sym, df, "rsi_dip_spike_v4", strat, CAPITAL, TF,
                     stop_mode=STOP_STANDARD, asset_class="crypto",
                     commission_pct=COMMISSION, slippage_pct=SLIPPAGE)
    if r is None:
        print(f"  {label:<44} [{sym}]: no result")
        return
    net = r.ending_capital - r.starting_capital
    pf  = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "  inf"
    print(f"  {label:<44} [{sym}]  trades={r.total_trades:>3}  WR={r.win_rate:>5.1f}%  "
          f"PF={pf:>7}  P&L=${net:>8.2f}  DD={r.max_drawdown_pct:>5.2f}%")

def make(adx_min=25, adx_max=60, rsi_os=35, rsi_exit=55, mode="penetration"):
    s = RSIDipSpikeV4Strategy()
    s.params.adx_min       = adx_min
    s.params.adx_max       = adx_max
    s.params.rsi_oversold  = rsi_os
    s.params.rsi_exit_long = rsi_exit
    s.params.signal_mode   = mode
    return s

print("Fetching data...")
print()
print("=" * 92)
print("RSI Dip & Spike v4c — ADX Max Filter Sweep (180d 1h)")
print("Hypothesis: adding ADX ceiling removes runaway-trend losses, improves WR")
print("=" * 92)

for sym in SYMBOLS:
    print(f"\n--- {sym} ---")
    run("Baseline   (ADX25-60  no ceiling change)",    make(),                                  sym)
    run("ADXmax50   (ceiling 60->50)",                 make(adx_max=50),                        sym)
    run("ADXmax40   (ceiling 60->40)",                 make(adx_max=40),                        sym)
    run("ADXmax35   (ceiling 60->35, tight range)",    make(adx_max=35),                        sym)
    run("ADXmax999  (no ceiling — old behaviour)",     make(adx_max=999),                       sym)
    run("ADX20-40   (widen min, tight max)",           make(adx_min=20, adx_max=40),            sym)
    run("ADX20-50   (widen min, med max)",             make(adx_min=20, adx_max=50),            sym)
    run("ADXmax40+RSI40 (tight max, wider entry)",     make(adx_max=40, rsi_os=40),             sym)
    run("ADXmax40+Exit60 (tight max, hold longer)",    make(adx_max=40, rsi_exit=60),           sym)

print()
print("=" * 92)
print("SUMMARY: Look for highest PF with most trades (activity vs quality tradeoff)")
print("Target: 30+ trades per symbol, PF > 1.3, WR > 55%")
print("=" * 92)
