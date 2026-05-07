import re

with open('dashboard.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# Fix 1: Manual trade entry uses UTC - change to local time
old1 = 'dt.utcnow().isoformat()'
new1 = 'datetime.now().isoformat()'
if old1 in src:
    src = src.replace(old1, new1, 1)
    changes += 1
    print('Fix 1 OK: manual trade entry_time now uses local PT')
else:
    print('Fix 1 FAIL: dt.utcnow() not found')

# Fix 2a: Add Broker to open positions row
old2 = '"To SL %": float(dist_sl), "To TP %": float(dist_tp)})'
new2 = '"To SL %": float(dist_sl), "To TP %": float(dist_tp), "Broker": p.get("broker", "?")})'
if old2 in src:
    src = src.replace(old2, new2, 1)
    changes += 1
    print('Fix 2a OK: Broker column added to open positions')
else:
    print('Fix 2a FAIL')

# Fix 2b: Add Broker to trade history (closed trades)
# Find the closed trades row builder
old3 = '"Exit Reason": t.get("exit_reason", ""), "Strategy": t.get("strategy_name", "")}'
new3 = '"Exit Reason": t.get("exit_reason", ""), "Strategy": t.get("strategy_name", ""), "Broker": t.get("broker", "?")}'
if old3 in src:
    src = src.replace(old3, new3, 1)
    changes += 1
    print('Fix 2b OK: Broker column added to trade history')
else:
    print('Fix 2b FAIL - showing context:')
    idx = src.find('Exit Reason')
    if idx > 0: print(repr(src[idx-20:idx+120]))

if changes > 0:
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'Done - {changes} fixes applied. Restart Streamlit.')
else:
    print('No changes made.')
