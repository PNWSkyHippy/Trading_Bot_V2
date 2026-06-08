import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
conn.execute("DELETE FROM bot_state WHERE key = 'strategy_bollinger_sqeeze_enabled'")
conn.commit()
print(f'Deleted misspelled key. Remaining bollinger keys:')
for r in conn.execute("SELECT key FROM bot_state WHERE key LIKE 'strategy_bollinger%'").fetchall():
    print(' ', r[0])
conn.close()
