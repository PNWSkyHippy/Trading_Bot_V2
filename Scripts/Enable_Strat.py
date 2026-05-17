
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

from data.database import db
import sqlite3

if len(sys.argv) >= 2:
    if sys.argv[1] == "-":
        # Piped via stdin: echo KEY | python encrypt_key.py -
        plaintext = sys.stdin.read().strip()
    else:
        plaintext = sys.argv[1].strip()
else:
    # Interactive — visible prompt
    plaintext = input("Strategy to Enable ").strip()

if not plaintext:
    print("ERROR: No strategy provided.", file=sys.stderr)
    sys.exit(1)

key = f"strategy_{plaintext}_enabled"
existing = db.get_state(key)
if existing is None:
    raise ValueError(f"Unknown strategy setting: {key}")
db.set_state(key, 'true')
#db.set_state(f"strategy_{plaintext}_enabled", 'true') 
print(f"'Done strategy_{plaintext}_enabled = true'")