import sqlite3, os
db = sqlite3.connect(os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db'))
key = 'strategy_mr_03_fbs_enabled'
current = db.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
print(f"Current: {current}")
db.execute("UPDATE bot_state SET value='true', updated=datetime('now') WHERE key=?", (key,))
db.commit()
print(f"Set {key} = 1 (enabled)")
