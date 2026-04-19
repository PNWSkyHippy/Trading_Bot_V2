from data.database import Database

db = Database()
with db._conn() as conn:
    try:
        conn.execute("ALTER TABLE trades ADD COLUMN tp_hit_count INTEGER DEFAULT 0")
        conn.commit()
        print("Column tp_hit_count added successfully")
    except Exception as e:
        print(f"Error (may already exist): {e}")