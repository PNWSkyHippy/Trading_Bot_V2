import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
rows = conn.execute("""
    SELECT symbol, entry_time, exit_time, exit_reason, pnl 
    FROM trades 
    WHERE status='closed' 
    ORDER BY exit_time DESC 
    LIMIT 20
""").fetchall()
for r in rows:
    print(f"{r[0]:12} | in: {str(r[1])[:16]} | out: {str(r[2])[:16]} | {str(r[3]):25} | ${r[4]:+.2f}")
conn.close()
 