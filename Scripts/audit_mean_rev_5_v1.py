"""
Mean Reversion 5-Strategy Viability Audit
==========================================
Quick viability pass: all 5 mean reversion hypotheses against yfinance data.

Strategies:
  ECB   ? Entropy Collapse Breakout       (CANDIDATE in Trader Dev)
  VDMR  ? Velocity-Deceleration MR        (INCUBATE in Trader Dev)
  CBAE  ? Candle Body Asymmetry Exhaust   (Watchlist in Trader Dev)
  RARE  ? Rolling Autocorrelation Regime  (Reject v1 in Trader Dev ? exits fixed)
  FELS  ? Failed Extension Liquidity Swp  (Reject v1 in Trader Dev ? exits fixed)

Pass 1: BTC-USD + SOL-USD only, 180d, 1h, no parameter sweep.
Goal: validate core hypothesis holds on yfinance/Coinbase data.
Trader Dev results (Binance) are noted for comparison.

Run: venv312\Scripts\python.exe Scripts\audit_mean_rev_5_v1.py
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.ecb_strategy   import ECBStrategy
from strategies.vdmr_strategy  import VDMRStrategy
from strategies.cbae_strategy  import CBAEStrategy
from strategies.rare_strategy  import RAREStrategy
from strategies.fels_strategy  import FELSStrategy

CAPITAL    = 10_000.0
COMMISSION = 0.26
SLIPPAGE   = 0.05
DAYS       = 180
TF         = "1h"

# Quick pass: 2 symbols. Expand to full basket once we see viability.
SYMBOLS = ["BTC-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "BNB-USD"]

# Trader Dev (Binance) results for comparison
TRADER_DEV_NOTES = {
    "ecb_strategy":   "PF 2.59 BTC 2024 (Binance) ? CANDIDATE",
    "vdmr_strategy":  "PF 1.94 BTC 2024 (Binance) ? INCUBATE",
    "cbae_strategy":  "PF 1.27 BTC (Binance, not swept) ? Watchlist",
    "rare_strategy":  "PF 1.12 BTC (Binance, exits broken) ? Reject v1",
    "fels_strategy":  "PF 1.11 BTC (Binance, exits broken) ? Reject v1",
}

bt = Backtester(starting_capital=CAPITAL)

STRATEGIES = [
    ("ECB  (Entropy Collapse Breakout)",     ECBStrategy,   "ecb_strategy"),
    ("VDMR (Velocity-Decel MR)",             VDMRStrategy,  "vdmr_strategy"),
    ("CBAE (Body Asymmetry Exhaust)",         CBAEStrategy,  "cbae_strategy"),
    ("RARE (Autocorr Regime Entry)",          RAREStrategy,  "rare_strategy"),
    ("FELS (Failed Extension Sweep)",         FELSStrategy,  "fels_strategy"),
]


def run(label, strat_instance, strat_name, sym):
    df = bt.fetch_history_crypto(sym, DAYS, TF)
    if df is None or len(df) < 220:
        n = len(df) if df is not None else 0
        print(f"  {label:<40} [{sym:<10}]: not enough data ({n} bars)")
        return None
    r = bt._simulate(sym, df, strat_name, strat_instance, CAPITAL, TF,
                     stop_mode=STOP_STANDARD, asset_class="crypto",
                     commission_pct=COMMISSION, slippage_pct=SLIPPAGE)
    if r is None:
        print(f"  {label:<40} [{sym:<10}]: no result")
        return None
    net = r.ending_capital - r.starting_capital
    pf  = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "  inf"
    print(f"  {label:<40} [{sym:<10}]  "
          f"trades={r.total_trades:>3}  WR={r.win_rate:>5.1f}%  "
          f"PF={pf:>7}  P&L=${net:>8.2f}  DD={r.max_drawdown_pct:>5.2f}%")
    return r


print()
print("=" * 100)
print("Mean Reversion 5-Strategy Viability Audit ? yfinance data (NOT Binance)")
print(f"180d 1h  |  Commission {COMMISSION}%  |  Slippage {SLIPPAGE}%")
print("Goal: does the core hypothesis hold on yfinance/Coinbase candles?")
print("=" * 100)

totals = {n: {"trades": 0, "wins": 0, "gross_w": 0.0, "gross_l": 0.0, "pnl": 0.0}
          for _, _, n in STRATEGIES}

for label, cls, sname in STRATEGIES:
    print(f"\n--- {label} ---")
    print(f"    Trader Dev baseline: {TRADER_DEV_NOTES.get(sname, '?')}")
    for sym in SYMBOLS:
        strat = cls()
        r = run(label, strat, sname, sym)
        if r and r.total_trades > 0:
            totals[sname]["trades"] += r.total_trades
            wins = round(r.total_trades * r.win_rate / 100)
            totals[sname]["wins"]   += wins

print()
print("=" * 100)
print("CROSS-SYMBOL SUMMARY")
print(f"{'Strategy':<42}  {'Trades':>7}  {'Basket WR':>9}")
print("-" * 70)
for label, cls, sname in STRATEGIES:
    t = totals[sname]
    if t["trades"] > 0:
        bwr = t["wins"] / t["trades"] * 100
        print(f"  {label:<40}  {t['trades']:>7}  {bwr:>8.1f}%")
    else:
        print(f"  {label:<40}  {'0':>7}  {'n/a':>9}")

print()
print("RANKING NOTES:")
print("  Target: 15+ trades/symbol, WR > 50%, PF > 1.3")
print("  Strategies with <10 total trades need longer DAYS window")
print("  Trader Dev PF numbers above were on Binance ? expect differences")
print("=" * 100)

