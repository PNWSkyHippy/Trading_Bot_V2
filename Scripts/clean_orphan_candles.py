"""Remove orphaned symbols from candle_store.db (not in any watchlist)."""
import sqlite3, os

DB   = os.path.join(os.path.dirname(__file__), '..', 'data', 'candle_store.db')
ORPHANS = [
    "ALGOUSD:BTNL", "DUAL/USD", "F", "HYPE/USD", "HYPEUSD:BTNL",
    "LLY", "SOXLS", "SOXLZUSD", "SOXS", "SOXS/USD",
    "STG/USD", "SUI/BTC", "SUI/USD", "ZORA/USD",
]

with sqlite3.connect(DB) as conn:
    for sym in ORPHANS:
        n1 = conn.execute("DELETE FROM candles WHERE symbol=?", (sym,)).rowcount
        n2 = conn.execute("DELETE FROM candle_meta WHERE symbol=?", (sym,)).rowcount
        print(f"  {sym:25s}  {n1:5,} bars removed" if n1 else f"  {sym:25s}  (not in cache)")
    conn.commit()

print("\nDone — orphaned symbols cleared from candle cache.")
