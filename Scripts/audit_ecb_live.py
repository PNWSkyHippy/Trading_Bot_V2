"""ECB live trade audit — run from trading_bot_v2 root"""
import sqlite3, os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db = sqlite3.connect("data/trading_bot.db")
cur = db.cursor()

# ── Strategy-exit trades by direction ────────────────────────────────────────
cur.execute("""
    SELECT
        direction,
        COUNT(*) as total,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(pnl), 2) as net_pnl,
        ROUND(AVG(pnl), 2) as avg_pnl,
        ROUND(AVG(CASE WHEN pnl > 0 THEN pnl END), 2) as avg_win,
        ROUND(AVG(CASE WHEN pnl <= 0 THEN pnl END), 2) as avg_loss
    FROM trades
    WHERE strategy_name = 'ecb_strategy'
      AND exit_reason NOT IN ('manual_close','reconciled_ghost','position_reconciled')
    GROUP BY direction
""")
rows = cur.fetchall()
print("ECB live trades (strategy exits only, by direction):")
if rows:
    for direction, total, wins, net, avg, avg_win, avg_loss in rows:
        wr = wins / total * 100 if total else 0
        print(f"  {direction:6s}  trades={total}  WR={wr:.1f}%  net=${net}  avg=${avg}  avg_win=${avg_win}  avg_loss=${avg_loss}")
else:
    print("  No strategy-exit trades found")

# ── All exits by reason ───────────────────────────────────────────────────────
print()
cur.execute("""
    SELECT exit_reason, COUNT(*) as n, ROUND(SUM(pnl),2) as pnl
    FROM trades WHERE strategy_name='ecb_strategy'
    GROUP BY exit_reason ORDER BY n DESC
""")
print("All ECB exits by reason:")
for reason, n, pnl in cur.fetchall():
    print(f"  {reason or 'None':35s}  n={n:>3}  pnl=${pnl}")

# ── Recent 10 trades ──────────────────────────────────────────────────────────
print()
cur.execute("""
    SELECT symbol, direction, entry_price, exit_price, pnl, exit_reason, entry_time
    FROM trades WHERE strategy_name='ecb_strategy'
    ORDER BY entry_time DESC LIMIT 10
""")
print("10 most recent ECB trades:")
for sym, d, ep, xp, pnl, reason, ts in cur.fetchall():
    ep_s = f"{ep:.4f}" if ep is not None else "N/A"
    xp_s = f"{xp:.4f}" if xp is not None else "N/A"
    pnl_s = f"${pnl:.2f}" if pnl is not None else "$0"
    ts_s = ts[:16] if ts else "N/A"
    print(f"  {ts_s}  {sym:<12}  {str(d):5s}  entry={ep_s}  exit={xp_s}  pnl={pnl_s}  {reason}")

db.close()
