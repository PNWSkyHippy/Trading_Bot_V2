import sqlite3, sys
sys.path.insert(0, '.')
from data.database import db

conn = sqlite3.connect('data/trading_bot.db')
rows = conn.execute(
    "SELECT service, key_name, updated_at FROM api_keys WHERE service LIKE 'alpaca%' ORDER BY updated_at DESC"
).fetchall()
print("Alpaca keys in DB (metadata):")
for r in rows:
    print(" ", r)

# Also check base_url value
base_url_val = db.get_api_key('alpaca', 'base_url')
api_key_val  = db.get_api_key('alpaca', 'api_key')
print(f"\nbase_url = {base_url_val}")
print(f"api_key  = {api_key_val[:8]}..." if api_key_val else "api_key  = None")
conn.close()
