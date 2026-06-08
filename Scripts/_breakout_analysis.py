import sqlite3
conn = sqlite3.connect('data/trading_bot.db')

STRAT = 'breakout_scanner'

print('=== EXIT REASONS ===')
rows = conn.execute(
    "SELECT exit_reason, COUNT(*) as n, "
    "ROUND(AVG(pnl),2) as avg_pnl, "
    "ROUND(SUM(pnl),2) as total_pnl, "
    "SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) as wins, "
    "SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) as losses "
    "FROM trades WHERE strategy_name=? AND status='closed' "
    "GROUP BY exit_reason ORDER BY n DESC",
    (STRAT,)
).fetchall()
for r in rows:
    print(f"  {str(r[0]):<28} n={r[1]:>3}  avg={r[2]:>8}  total={r[3]:>10}  W={r[4]} L={r[5]}")

print()
print('=== PnL DISTRIBUTION ===')
rows = conn.execute(
    "SELECT "
    "CASE "
    "  WHEN pnl < -50 THEN '< -50' "
    "  WHEN pnl < -30 THEN '-50 to -30' "
    "  WHEN pnl < -20 THEN '-30 to -20' "
    "  WHEN pnl < -10 THEN '-20 to -10' "
    "  WHEN pnl <   0 THEN '-10 to 0' "
    "  WHEN pnl =   0 THEN '= 0 breakeven' "
    "  WHEN pnl <  10 THEN '0 to 10' "
    "  WHEN pnl <  20 THEN '10 to 20' "
    "  WHEN pnl <  30 THEN '20 to 30' "
    "  WHEN pnl <  50 THEN '30 to 50' "
    "  WHEN pnl < 100 THEN '50 to 100' "
    "  ELSE '> 100' "
    "END as bucket, "
    "COUNT(*) as n, ROUND(SUM(pnl),2) as total "
    "FROM trades WHERE strategy_name=? AND status='closed' "
    "GROUP BY bucket ORDER BY MIN(pnl)",
    (STRAT,)
).fetchall()
for r in rows:
    print(f"  {str(r[0]):<22} n={r[1]:>3}  total={r[2]:>10}")

print()
print('=== TOP 10 BIGGEST WINS ===')
rows = conn.execute(
    "SELECT symbol, pnl, exit_reason, exit_time FROM trades "
    "WHERE strategy_name=? AND status='closed' AND pnl>0 "
    "ORDER BY pnl DESC LIMIT 10",
    (STRAT,)
).fetchall()
for r in rows:
    print(f"  {r[0]:<8} pnl={r[1]:>8}  reason={str(r[2]):<20}  {r[3]}")

print()
print('=== TOP 10 BIGGEST LOSSES ===')
rows = conn.execute(
    "SELECT symbol, pnl, exit_reason, exit_time FROM trades "
    "WHERE strategy_name=? AND status='closed' AND pnl<=0 "
    "ORDER BY pnl ASC LIMIT 10",
    (STRAT,)
).fetchall()
for r in rows:
    print(f"  {r[0]:<8} pnl={r[1]:>8}  reason={str(r[2]):<20}  {r[3]}")

conn.close()
