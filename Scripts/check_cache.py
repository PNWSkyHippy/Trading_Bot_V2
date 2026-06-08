import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'logs'))
from intelligence.candle_store import get_store
store = get_store()
rows = store.list_available()
print(f"Symbols in cache: {len(rows)}")
for r in sorted(rows, key=lambda x: x['symbol'])[:30]:
    print(f"  {r['symbol']:20s} {r['timeframe']:6s} {r['bar_count']:6,} bars  last={r['last_date']}")
if len(rows) > 30:
    print(f"  ... and {len(rows)-30} more")
