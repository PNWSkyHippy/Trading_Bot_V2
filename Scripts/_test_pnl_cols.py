import sqlite3
conn = sqlite3.connect('data/trading_bot.db')

base_where = "status='closed' AND exit_time >= ? AND exit_time <= ?"
params = ['2026-06-06T12:00', '2026-06-07T23:59']

sql = f"""SELECT s.strategy_name,
       COALESCE(t.trades,0) AS trades,
       COALESCE(t.wins,0)   AS wins,
       COALESCE(t.losses,0) AS losses,
       ROUND(COALESCE(CAST(t.wins AS REAL)/NULLIF(t.trades,0)*100,0),1) AS win_rate_pct,
       ROUND(COALESCE(t.total_pnl,0),2) AS total_pnl
FROM (
    SELECT SUBSTR(key,10,LENGTH(key)-17) AS strategy_name
    FROM bot_state WHERE key LIKE 'strategy_%_enabled'
    UNION
    SELECT DISTINCT strategy_name FROM trades
    WHERE {base_where} AND strategy_name IS NOT NULL
) s
LEFT JOIN (
    SELECT strategy_name,
           COUNT(*) AS trades,
           SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS wins,
           SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS losses,
           SUM(pnl) AS total_pnl
    FROM trades WHERE {base_where}
    GROUP BY strategy_name
) t ON s.strategy_name=t.strategy_name
ORDER BY COALESCE(t.trades,0) DESC, s.strategy_name ASC"""

cur = conn.execute(sql, params * 2)
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print("COLS:", cols)
print(f"NUM COLS: {len(cols)}")
print("ROWS:")
for r in rows:
    print(" ", r)
conn.close()
