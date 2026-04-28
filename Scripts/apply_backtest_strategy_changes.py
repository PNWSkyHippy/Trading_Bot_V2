"""
apply_backtest_strategy_changes.py
====================================
Applies strategy enable/disable changes based on backtest results.

Results summary (5min/30day all stocks, 2-bar trailing stop):
  KEEP:    grid_bot (130/137 GO), mean_reversion (16/16 GO, 79.8% win rate)
           dca_accumulator (all GO), vwap_momentum (pending more data)
           swing_trader (pending 1hr/365 test)
  DISABLE: rsi_momentum (3/85 GO), bollinger_breakout (4/137 GO)
           ema_crossover (5/137 GO)

Run: python Scripts/apply_backtest_strategy_changes.py
"""
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("data/trading_bot.db")
now  = datetime.now(timezone.utc).isoformat()

changes = [
    # Enable proven strategies
    ("strategy_mean_reversion_enabled",    "true",  "ENABLE  mean_reversion  — 79.8% avg win rate, 16/16 GO on stocks"),
    ("strategy_grid_bot_enabled",          "true",  "ENABLE  grid_bot        — 130/137 GO stocks, 80+ GO crypto"),
    ("strategy_dca_accumulator_enabled",   "true",  "ENABLE  dca_accumulator — all GO on blue chips"),
    ("strategy_vwap_momentum_enabled",     "true",  "ENABLE  vwap_momentum   — pending 1hr test, keep for now"),
    ("strategy_swing_trader_enabled",      "true",  "ENABLE  swing_trader    — pending 1hr/365 test, keep for now"),

    # Disable consistently underperforming strategies
    ("strategy_rsi_momentum_enabled",      "false", "DISABLE rsi_momentum    — 3/85 GO, avg win rate 34%"),
    ("strategy_bollinger_breakout_enabled","false", "DISABLE bollinger       — 4/137 GO, avg win rate 36%"),
    ("strategy_ema_crossover_enabled",     "false", "DISABLE ema_crossover   — 5/137 GO, avg win rate 33%"),

    # Keep disabled pending backtest
    ("strategy_orb_breakout_enabled",      "false", "DISABLE orb_breakout    — pending full backtest"),
    ("strategy_hammer_reversal_enabled",   "false", "DISABLE hammer_reversal — pending backtest"),
]

print("Applying strategy changes based on backtest results:\n")
for key, value, description in changes:
    conn.execute(
        "INSERT OR REPLACE INTO bot_state (key, value, updated) VALUES (?, ?, ?)",
        (key, value, now)
    )
    print(f"  {description}")

conn.commit()

print("\nVerifying final strategy states:")
rows = conn.execute(
    "SELECT key, value FROM bot_state WHERE key LIKE 'strategy_%_enabled' ORDER BY key"
).fetchall()
for row in rows:
    name   = row[0].replace("strategy_", "").replace("_enabled", "")
    state  = "✅ ENABLED " if row[1] == "true" else "❌ DISABLED"
    print(f"  {state} {name}")

conn.close()
print("\nDone — restart bot to apply changes.")
