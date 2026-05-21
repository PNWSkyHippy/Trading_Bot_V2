"""
Grid Bot Iter4 quick audit — BTC only, 90 days
Run: python Scripts/audit_grid_iter4_quick.py
"""
import os, sys, logging
logging.basicConfig(level=logging.WARNING)
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from intelligence.backtester import Backtester, STOP_STANDARD
from strategies.grid_bot import GridBot

SYM        = "BTC-USD"
DAYS       = 180
TIMEFRAME  = "1h"
CAPITAL    = 10_000.0
COMMISSION = 0.26
SLIPPAGE   = 0.05

bt = Backtester(starting_capital=CAPITAL)
print("Fetching BTC-USD 1h 180d...")
df = bt.fetch_history_crypto(SYM, DAYS, TIMEFRAME)
print(f"Candles fetched: {len(df) if df is not None else 0}")
if df is None or len(df) < 60:
    print("Not enough data — exiting")
    sys.exit(1)

def test(label, bbw_enabled, bbw_threshold=0.40):
    strat = GridBot()
    strat.bbw_filter_enabled       = bbw_enabled
    strat.bbw_pct_threshold        = bbw_threshold
    strat.backtest_allow_crypto_shorts = False
    r = bt._simulate(SYM, df, "grid_bot", strat, CAPITAL, TIMEFRAME,
                     stop_mode=STOP_STANDARD, asset_class="crypto",
                     commission_pct=COMMISSION, slippage_pct=SLIPPAGE,
                     entry_side_filter="long")
    if r is None:
        print(f"{label}: no result")
        return
    net_pnl = r.ending_capital - r.starting_capital
    pf = f"{r.profit_factor:.3f}" if r.profit_factor != float("inf") else "inf"
    print(f"{label:40s}  trades={r.total_trades:>3}  WR={r.win_rate:>5.1f}%  "
          f"PF={pf:>7}  P&L=${net_pnl:>8.2f}  DD={r.max_drawdown_pct:>5.2f}%")

test("Baseline  (no BBW filter)",      bbw_enabled=False)
test("Iter4     (BBW <= 40%)",          bbw_enabled=True, bbw_threshold=0.40)
test("Iter4b    (BBW <= 30%)",          bbw_enabled=True, bbw_threshold=0.30)
test("Iter4c    (BBW <= 50%)",          bbw_enabled=True, bbw_threshold=0.50)
