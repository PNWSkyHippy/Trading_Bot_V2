python -c "
from data.database import db
from data.database import db as _db
import sqlite3
conn = sqlite3.connect('data/trading_bot.db')
# Get all stuck trade IDs
rows = conn.execute(\"SELECT trade_id, symbol FROM trades WHERE status='open'\").fetchall()
for trade_id, symbol in rows:
    _db.set_state(f'close_stuck_{trade_id}', 0)
    _db.set_state(f'close_attempts_{trade_id}', 0)
    print(f'Reset stuck flag for {symbol} {trade_id[:8]}')
conn.close()
"