"""
Grid Bot Iter4 audit — BBW compression filter
Compares Baseline (Iter3) vs Iter4 (BBW<=40%) vs Iter4b (BBW<=30%)
Run from trading_bot_v2 root:
  python Scripts/audit_grid_iter4.py
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.grid_bot import GridBot

SYMBOLS   = ["BTC-USD", "ETH-USD", "SOL-USD"]
DAYS      = 180
TIMEFRAME = "1h"
CAPITAL   = 10_000.0
# Kraken-ish commission: 0.26% per leg
COMMISSION = 0.26
SLIPPAGE   = 0.05

def run_basket(label, bbw_enabled, bbw_threshold=0.40):
    bt = Backtester(starting_capital=CAPITAL)
    results = []
    for sym in SYMBOLS:
        strat = GridBot()
        strat.bbw_filter_enabled = bbw_enabled
        strat.bbw_pct_threshold  = bbw_threshold
        strat.backtest_allow_crypto_shorts = False  # longs only — mirror Iter3
        try:
            df = bt.fetch_history_crypto(sym, DAYS, TIMEFRAME)
            if df is None or len(df) < 60:
                print(f"  {sym:<12}  no data")
                continue
            r = bt._simulate(
                sym, df, "grid_bot", strat, CAPITAL, TIMEFRAME,
                stop_mode=STOP_STANDARD,
                asset_class="crypto",
                commission_pct=COMMISSION,
                slippage_pct=SLIPPAGE,
                entry_side_filter="long",
            )
            if r is None:
                print(f"  {sym:<12}  no result")
                continue
            results.append(r)
            pf = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "  inf"
            print(f"  {sym:<12}  trades={r.total_trades:>3}  WR={r.win_rate*100:>5.1f}%  "
                  f"PF={pf:>7}  P&L=${r.total_pnl:>8.2f}  DD={r.max_drawdown_pct:>5.2f}%")
        except Exception as e:
            print(f"  {sym:<12}  ERROR: {e}")
            import traceback; traceback.print_exc()

    if results:
        total_trades = sum(r.total_trades for r in results)
        total_pnl    = sum(r.total_pnl for r in results)
        wins         = sum(r.winning_trades for r in results)
        wr           = wins / total_trades * 100 if total_trades else 0
        avg_dd       = sum(r.max_drawdown_pct for r in results) / len(results)
        print(f"  {'─'*60}")
        print(f"  {'BASKET':<12}  trades={total_trades:>3}  WR={wr:>5.1f}%"
              f"           P&L=${total_pnl:>8.2f}  avg_DD={avg_dd:.2f}%")
    return results

SEP = "=" * 65

print(SEP)
print("BASELINE — Iter3 (ADX<15, longs only, NO BBW filter)")
print(SEP)
base = run_basket("Baseline", bbw_enabled=False)

print()
print(SEP)
print("ITER4 — BBW compression gate (BBW in bottom 40% of 50-bar range)")
print(SEP)
iter4 = run_basket("Iter4", bbw_enabled=True, bbw_threshold=0.40)

print()
print(SEP)
print("ITER4b — BBW tighter gate (bottom 30%)")
print(SEP)
iter4b = run_basket("Iter4b", bbw_enabled=True, bbw_threshold=0.30)
