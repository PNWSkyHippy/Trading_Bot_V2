"""
Fix wildly wrong stop-loss values in open Alpaca positions.
Updates DB stop_loss to percent-based (1.5% from entry) where the current stop
is more than 5% away from entry (indicating a structural stop data error).

Only updates local DB — broker bracket orders are not affected (those require
Alpaca API access which is currently unauthorized).
"""
import sqlite3
import datetime

DB_PATH = "data/trading_bot.db"
STOP_LOSS_PCT = 0.015  # 1.5% per config.py

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== Stop-Loss Fix ===")
print(f"Run at: {datetime.datetime.now()}")
print(f"Stop-loss threshold: {STOP_LOSS_PCT*100}% from entry")
print()

c.execute(
    "SELECT id, symbol, direction, entry_price, stop_loss, take_profit FROM trades "
    "WHERE status='open' AND broker='alpaca'"
)
rows = c.fetchall()
print(f"Open Alpaca positions: {len(rows)}")
print()

fixed = 0
for row in rows:
    trade_id, symbol, direction, entry_price, stop_loss, take_profit = row
    if not entry_price or entry_price <= 0:
        print(f"  SKIP {symbol}: invalid entry_price={entry_price}")
        continue

    if stop_loss is None:
        actual_pct = None
        wrong = True
    else:
        actual_pct = abs(entry_price - stop_loss) / entry_price
        # For longs: stop should be BELOW entry; for shorts: ABOVE entry
        if direction == 'long':
            wrong = stop_loss >= entry_price or actual_pct > 0.05
        else:
            wrong = stop_loss <= entry_price or actual_pct > 0.05

    if wrong:
        # Compute correct percent-based stop
        if direction == 'long':
            new_stop = round(entry_price * (1 - STOP_LOSS_PCT), 4)
        else:
            new_stop = round(entry_price * (1 + STOP_LOSS_PCT), 4)

        old_pct_str = f"{actual_pct*100:.1f}%" if actual_pct is not None else "None"
        print(f"  FIX {symbol} {direction} entry={entry_price} | old_stop={stop_loss} ({old_pct_str} from entry) -> new_stop={new_stop} (1.5%)")
        c.execute(
            "UPDATE trades SET stop_loss=? WHERE id=?",
            (new_stop, trade_id)
        )
        fixed += 1
    else:
        pct_str = f"{actual_pct*100:.2f}%"
        print(f"  OK  {symbol} {direction} entry={entry_price} stop={stop_loss} ({pct_str} — within range)")

conn.commit()
conn.close()

print()
print(f"Fixed {fixed} of {len(rows)} positions.")
print("DB updated. Broker bracket orders not affected (require Alpaca API access).")
print("Position monitor will now use correct stop levels for trailing stop calculations.")
