$script = @'
import sqlite3

DB = 'data/trading_bot.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT trade_id, symbol, entry_price, exit_price, pnl, pnl_pct, exit_reason, close_time
    FROM trades
    WHERE symbol IN ('PDD','CORZ','MRNA','BAC')
      AND exit_reason = 'trailing_stop'
      AND status = 'closed'
      AND pnl > 200
    ORDER BY close_time DESC
""").fetchall()

if not rows:
    print("No matching fake trades found.")
    conn.close()
    exit()

print(f"Found {len(rows)} fake trade(s) to correct:")
for r in rows:
    print(f"  {r['symbol']:6s}  entry={r['entry_price']:.4f}  fake_exit={r['exit_price']:.4f}  fake_pnl=${r['pnl']:.2f}  closed={r['close_time']}")

print()
confirm = input("Apply corrections? (yes/no): ").strip().lower()
if confirm != 'yes':
    print("Aborted.")
    conn.close()
    exit()

corrected = 0
for r in rows:
    conn.execute("""
        UPDATE trades
        SET exit_price  = entry_price,
            pnl         = 0.0,
            pnl_pct     = 0.0,
            exit_reason = 'corrected_bad_feed_spike'
        WHERE trade_id = ?
    """, (r['trade_id'],))
    print(f"  Corrected {r['symbol']}: fake +${r['pnl']:.2f} -> $0.00")
    corrected += 1

conn.commit()
conn.close()
print(f"\nDone. {corrected} trade(s) corrected.")
'@

cd C:\Users\Linda\trading_bot_v2
.\venv312\Scripts\python.exe -c $script
