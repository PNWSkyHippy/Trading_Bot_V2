import sqlite3
conn = sqlite3.connect('data/trading_bot.db')

# ALL TIME - no date filter
print("=== ALL TIME ===")
sql = """
SELECT strategy_name,
       COUNT(*) AS trades,
       SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0*SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS win_rate_pct,
       ROUND(SUM(pnl),2) AS total_pnl,
       ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),2) AS gross_wins,
       ROUND(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END),2) AS gross_losses,
       ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)/NULLIF(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),0),3) AS profit_factor,
       ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)/NULLIF(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),0),2) AS avg_win,
       ROUND(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)/NULLIF(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END),0),2) AS avg_loss
FROM trades WHERE status='closed' AND strategy_name='breakout_scanner'
GROUP BY strategy_name
"""
cur = conn.execute(sql)
cols = [d[0] for d in cur.description]
row = cur.fetchone()
print("Cols:", cols)
if row:
    for c, v in zip(cols, row):
        print(f"  {c}: {v!r}")
else:
    print("  (no rows)")

# Check null issue with profit_factor=0
print("\n=== CHECK profit_factor when wins=0 ===")
r = conn.execute("SELECT ROUND(0.0/NULLIF(ABS(-60.16),0), 3) AS pf").fetchone()
print("  profit_factor (0 wins / -60.16 losses):", r[0])

conn.close()
