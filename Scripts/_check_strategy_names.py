import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
rows = conn.execute(
    "SELECT SUBSTR(key,10,LENGTH(key)-17) AS strategy_name FROM bot_state WHERE key LIKE 'strategy_%_enabled' ORDER BY strategy_name"
).fetchall()
print(f'{len(rows)} strategies found:')
for r in rows:
    print(' ', r[0])
conn.close()
