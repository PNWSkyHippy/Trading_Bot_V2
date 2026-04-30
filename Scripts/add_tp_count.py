import sys
import os

# Add project root to Python path and change working directory to root.
# This allows scripts in Scripts/ to import from data/, core/, strategies/ etc.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)


from data.database import Database

db = Database()
with db._conn() as conn:
    try:
        conn.execute("ALTER TABLE trades ADD COLUMN tp_hit_count INTEGER DEFAULT 0")
        conn.commit()
        print("Column tp_hit_count added successfully")
    except Exception as e:
        print(f"Error (may already exist): {e}")