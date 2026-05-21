"""
Hammer Reversal audit — baseline + filter relaxation sweep
Run: python Scripts/audit_hammer_v1.py
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.hammer_reversal import HammerReversal

CAPITAL    = 10_000.0
COMMISSION = 0.26
SLIPPAGE   = 0.05
DAYS       = 180
TF         = "5m"

bt = Backtester(starting_capital=CAPITAL)

SYMBOLS = ["SOL-USD", "BTC-USD"]

def run(label, strat, sym):
    df = bt.fetch_history_crypto(sym, DAYS, TF)
    if df is None or len(df) < 100:
        print(f"{label} [{sym}]: not enough data")
        return
    r = bt._simulate(sym, df, "hammer_reversal", strat, CAPITAL, TF,
                     stop_mode=STOP_STANDARD, asset_class="crypto",
                     commission_pct=COMMISSION, slippage_pct=SLIPPAGE,
                     entry_side_filter="long")
    if r is None:
        print(f"{label} [{sym}]: no result")
        return
    net = r.ending_capital - r.starting_capital
    pf  = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "inf"
    print(f"{label:<42} [{sym}]  trades={r.total_trades:>3}  WR={r.win_rate:>5.1f}%  "
          f"PF={pf:>7}  P&L=${net:>8.2f}  DD={r.max_drawdown_pct:>5.2f}%")

def make(rsi_os=30, stoch_os=20, obv_bars=3, min_score=0.70):
    s = HammerReversal()
    s.rsi_oversold   = rsi_os
    s.stoch_oversold = stoch_os
    s.obv_rising_bars= obv_bars
    s.min_score      = min_score
    return s

print("Fetching data...")
print()
print("=" * 85)
print("HAMMER REVERSAL — Baseline + Filter Relaxation Sweep (180d 5m)")
print("=" * 85)

for sym in SYMBOLS:
    print(f"\n--- {sym} ---")
    run("Baseline  (RSI30 Stoch20 OBV3)",      make(),                           sym)
    run("OBV2      (OBV bars 3->2)",             make(obv_bars=2),                 sym)
    run("OBV1      (OBV bars 3->1)",             make(obv_bars=1),                 sym)
    run("RSI35     (RSI 30→35)",                make(rsi_os=35),                  sym)
    run("RSI35+OBV2 (RSI35, OBV2)",             make(rsi_os=35, obv_bars=2),      sym)
    run("Stoch25   (Stoch 20→25)",              make(stoch_os=25),                sym)
    run("RSI35+Stoch25 (relax both)",           make(rsi_os=35, stoch_os=25),     sym)
    run("RSI40+Stoch30+OBV2 (aggressive)",      make(rsi_os=40, stoch_os=30, obv_bars=2), sym)
