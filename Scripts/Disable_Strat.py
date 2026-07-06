import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

from data.database import db
from core.scanner_controls import (
    SCANNER_CONTROLS,
    normalize_scanner_name,
    scanner_state_key,
)


if len(sys.argv) >= 2:
    if sys.argv[1] == "-":
        # Piped via stdin: echo grid_bot | python Scripts/disable_strat.py -
        plaintext = sys.stdin.read().strip()
    else:
        plaintext = sys.argv[1].strip()
else:
    plaintext = input("Strategy to Disable ").strip()

if not plaintext:
    print("ERROR: No strategy provided.", file=sys.stderr)
    sys.exit(1)

scanner_name = normalize_scanner_name(plaintext)
if scanner_name in SCANNER_CONTROLS:
    key = scanner_state_key(scanner_name)
elif plaintext.startswith("strategy_") and plaintext.endswith("_enabled"):
    key = plaintext
else:
    key = f"strategy_{plaintext}_enabled"

db.set_state(key, False)
print(f"Done {key} = false")

# Strategy disables from this script are MANUAL — set the sticky flag so the
# engine's AUTO-ENABLE (profitable-again) logic cannot flip it back on.
# Cleared only by Scripts/Enable_Strat.py.
if key.startswith("strategy_") and key.endswith("_enabled"):
    manual_key = key[: -len("_enabled")] + "_manual_disable"
    db.set_state(manual_key, True)
    print(f"Done {manual_key} = true (sticky - survives auto-enable)")
