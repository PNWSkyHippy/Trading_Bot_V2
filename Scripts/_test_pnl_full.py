import sqlite3

def db_strategy_pnl(from_dt=None, to_dt=None):
    base_where = "status='closed'"
    params = []
    if from_dt:
        base_where += " AND exit_time >= ?"
        params.append(from_dt)
    if to_dt:
        base_where += " AND exit_time <= ?"
        params.append(to_dt)

    sql = f"""
SELECT s.strategy_name,
       COALESCE(t.trades,0) AS trades,
       COALESCE(t.wins,0) AS wins,
       COALESCE(t.losses,0) AS losses,
       COALESCE(t.win_rate_pct,0) AS win_rate_pct,
       COALESCE(t.total_pnl,0) AS total_pnl,
       COALESCE(t.gross_wins,0) AS gross_wins,
       COALESCE(t.gross_losses,0) AS gross_losses,
       t.profit_factor,
       t.avg_win,
       t.avg_loss
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
           ROUND(100.0*SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS win_rate_pct,
           ROUND(SUM(pnl),2) AS total_pnl,
           ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),2) AS gross_wins,
           ROUND(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END),2) AS gross_losses,
           ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)/NULLIF(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),0),3) AS profit_factor,
           ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)/NULLIF(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),0),2) AS avg_win,
           ROUND(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)/NULLIF(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END),0),2) AS avg_loss
    FROM trades WHERE {base_where}
    GROUP BY strategy_name
) t ON s.strategy_name=t.strategy_name
ORDER BY COALESCE(t.trades,0) DESC, s.strategy_name ASC
"""
    conn = sqlite3.connect('data/trading_bot.db')
    cur = conn.execute(sql, params * 2)
    cols = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    conn.close()
    return cols, rows

# ALL TIME
print("=== ALL TIME (breakout_scanner row) ===")
cols, rows = db_strategy_pnl()
print("Cols:", cols)
for r in rows:
    if r[0] == 'breakout_scanner':
        print("Row:", dict(zip(cols, r)))

# CUSTOM DATE (today's range)
print("\n=== CUSTOM DATE (today noon - tomorrow midnight) ===")
cols2, rows2 = db_strategy_pnl('2026-06-06T12:00', '2026-06-07T23:59')
print("Cols:", cols2)
for r in rows2:
    if r[0] == 'breakout_scanner':
        print("Row:", dict(zip(cols2, r)))
