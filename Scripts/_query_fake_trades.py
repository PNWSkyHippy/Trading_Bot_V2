import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
conn.row_factory = sqlite3.Row

# All PDD/CORZ/MRNA/BAC regardless of date
rows = conn.execute(
    "SELECT id, symbol, entry_price, exit_price, pnl, exit_reason, exit_time, strategy_name "
    "FROM trades WHERE symbol IN ('PDD','CORZ','MRNA','BAC') AND status='closed' "
    "ORDER BY exit_time DESC LIMIT 20"
).fetchall()
print(f'All PDD/CORZ/MRNA/BAC closed trades ({len(rows)} found):')
for r in rows:
    print(f"  id={r['id']:>5}  {r['symbol']:<6}  pnl={r['pnl']:+.2f}  exit={r['exit_time']}  reason={r['exit_reason']}  strat={r['strategy_name']}")

print()
# All big wins from bollinger/breakout any date
big = conn.execute(
    "SELECT id, symbol, entry_price, exit_price, pnl, exit_reason, exit_time, strategy_name "
    "FROM trades WHERE status='closed' AND pnl > 200 "
    "AND strategy_name IN ('bollinger_breakout','breakout_scanner') "
    "ORDER BY exit_time DESC LIMIT 30"
).fetchall()
print(f'All bollinger/breakout wins >$200 (last 30):')
for r in big:
    print(f"  id={r['id']:>5}  {r['symbol']:<8}  entry={r['entry_price']:.4f}  exit={r['exit_price']:.4f}  pnl={r['pnl']:+.2f}  exit_time={r['exit_time']}")
conn.close()
