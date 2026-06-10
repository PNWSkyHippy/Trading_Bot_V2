"""
Fix ghost positions - marks positions as closed in DB that don't exist on any broker.
Run when position monitor shows repeated 'position does not exist' errors.
"""
import sqlite3
import datetime

DB_PATH = "data/trading_bot.db"

# Positions confirmed as ghosts from log analysis (broker says 'position does not exist')
GHOST_SYMBOLS = ["IONQ", "MRNA", "NOW"]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== Ghost Position Fix ===")
print(f"Run at: {datetime.datetime.now()}")
print()

for symbol in GHOST_SYMBOLS:
    c.execute(
        "SELECT id, symbol, direction, entry_price, quantity, strategy_name, broker, status, entry_time "
        "FROM trades WHERE symbol=? AND status='open'",
        (symbol,)
    )
    rows = c.fetchall()
    if not rows:
        print(f"{symbol}: no open positions in DB (already resolved or never recorded)")
        continue

    for row in rows:
        trade_id, sym, direction, entry_price, qty, strategy, broker, status, entry_time = row
        print(f"FOUND GHOST: id={trade_id} {sym} {direction} entry={entry_price} qty={qty} broker={broker} opened={entry_time}")
        # Mark as closed with ghost_position exit reason and 0 P&L
        now = datetime.datetime.now().isoformat()
        c.execute(
            "UPDATE trades SET status='closed', exit_price=entry_price, exit_time=?, "
            "exit_reason='ghost_position_auto_resolved' "
            "WHERE id=?",
            (now, trade_id)
        )
        print(f"  -> Marked closed (ghost_position_auto_resolved) at {now}")

conn.commit()

# Also show all currently open positions
print()
print("=== Remaining open positions after fix ===")
c.execute(
    "SELECT symbol, direction, entry_price, quantity, strategy_name, broker, entry_time "
    "FROM trades WHERE status='open' ORDER BY entry_time DESC"
)
remaining = c.fetchall()
print(f"Total open: {len(remaining)}")
for r in remaining:
    print(f"  {r[0]} {r[1]} @ {r[2]} qty={r[3]} broker={r[5]} opened={r[6]}")

conn.close()
print()
print("Done.")
