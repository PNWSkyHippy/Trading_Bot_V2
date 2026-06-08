"""Sync DB strategy states with tonight's matrix decisions."""
import sqlite3, os

db = sqlite3.connect(os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db'))

disable = [
    'strategy_adaptive_regime_enabled',
    'strategy_bollinger_squeeze_enabled',
    'strategy_ema_ribbon_breakout_enabled',
    'strategy_kds_mean_reversion_enabled',
    'strategy_rare_strategy_enabled',
    'strategy_cbae_strategy_enabled',
]

enable = [
    'strategy_sfr_structural_fakeout_enabled',
]

for key in disable:
    cur = db.execute('SELECT value FROM bot_state WHERE key=?', (key,)).fetchone()
    if cur:
        db.execute("UPDATE bot_state SET value='false', updated=datetime('now') WHERE key=?", (key,))
        print(f"DISABLED  {key}  (was {cur[0]})")
    else:
        print(f"NOT FOUND {key}")

for key in enable:
    cur = db.execute('SELECT value FROM bot_state WHERE key=?', (key,)).fetchone()
    if cur:
        db.execute("UPDATE bot_state SET value='true', updated=datetime('now') WHERE key=?", (key,))
        print(f"ENABLED   {key}  (was {cur[0]})")
    else:
        print(f"NOT FOUND {key}")

db.commit()
print("\nDone.")
