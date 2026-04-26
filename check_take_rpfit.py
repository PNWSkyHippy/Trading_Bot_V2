import sqlite3

conn = sqlite3.connect("data/trading_bot.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT trade_id, symbol, entry_price, exit_price,
           exit_reason, pnl, pnl_pct, take_profit
    FROM trades
    WHERE symbol = 'TRUMP/USD'
    AND status = 'closed'
    AND DATE(entry_time) = '2026-04-25'
""""")

rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
