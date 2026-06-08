import sqlite3, os
db = sqlite3.connect(os.path.join(os.path.dirname(__file__), '..', 'data', 'trading_bot.db'))
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
# Find strategy-related tables
for t in tables:
    if 'strat' in t[0].lower() or 'config' in t[0].lower():
        print(f"\n{t[0]}:")
        rows = db.execute(f"SELECT * FROM {t[0]} WHERE name LIKE '%mr_03%' OR name LIKE '%fbs%' LIMIT 5").fetchall()
        for r in rows:
            print(" ", r)
