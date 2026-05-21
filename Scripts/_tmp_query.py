import sqlite3

conn = sqlite3.connect('data/trading_bot.db')
cur = conn.cursor()
cur.execute("""
    SELECT symbol, direction, entry_time, pnl, pnl_pct, exit_reason
    FROM trades
    WHERE strategy_name='vwap_confirmed_orb'
      AND entry_time >= datetime('now','-2 days')
    ORDER BY entry_time DESC
""")
rows = cur.fetchall()
wins   = [r for r in rows if r[3] and r[3] > 0]
losses = [r for r in rows if r[3] and r[3] < 0]
total  = sum(r[3] for r in rows if r[3])
print(f"Trades: {len(rows)}  W:{len(wins)}  L:{len(losses)}  Total PnL: ${total:.2f}")
print()
print(f"{'Symbol':<14} {'Dir':<6} {'Entry':<18} {'PnL':>8}  {'PnL%':>7}  Exit Reason")
print("-"*75)
for r in rows:
    pnl = r[3] or 0
    pct = (r[4] or 0) * 100
    flag = " <-- LOSS" if pnl < -10 else (" <-- WIN" if pnl > 10 else "")
    print(f"{r[0]:<14} {r[1]:<6} {str(r[2])[:16]:<18} {pnl:>8.2f}  {pct:>6.2f}%  {r[5] or ''}{flag}")
conn.close()
