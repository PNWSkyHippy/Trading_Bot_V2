import sqlite3, hashlib, secrets

db = r'C:\Users\Linda\trading_bot_v2\data\trading_bot.db'

def make_hash(password):
    salt = secrets.token_hex(16)
    h    = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f'plain:sha256:{salt}:{h}'

conn = sqlite3.connect(db)

# Reset admin - plain hash, force_change OFF
conn.execute("UPDATE dashboard_users SET hash_enc=?, force_change=0 WHERE username='admin'",
             (make_hash('admin'),))

# Reset Ron - plain hash, force_change OFF
conn.execute("UPDATE dashboard_users SET hash_enc=?, force_change=0 WHERE username='Ron'",
             (make_hash('Ron'),))

conn.commit()

# Verify
rows = conn.execute("SELECT username, force_change, substr(hash_enc,1,20) as hash_start FROM dashboard_users").fetchall()
for r in rows:
    print(r)

conn.close()
print("Done")
