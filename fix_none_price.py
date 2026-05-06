with open('BreakoutScanner.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# Fix 1: add None check on last price before using it
if 't["last"], op,' in src:
    src = src.replace(
        't["last"], op,',
        'float(t["last"]) if t.get("last") else 0.0, op,',
        1
    )
    changes += 1
    print('Fix 1 OK: t["last"] guarded')
else:
    print('Fix 1 SKIP')

# Fix 2: guard high/low
if 't.get("high") or t["last"], t.get("low") or t["last"],' in src:
    src = src.replace(
        't.get("high") or t["last"], t.get("low") or t["last"],',
        'float(t.get("high") or t.get("last") or 0), float(t.get("low") or t.get("last") or 0),',
        1
    )
    changes += 1
    print('Fix 2 OK: high/low guarded')
else:
    print('Fix 2 SKIP')

# Fix 3: guard volume
if 't.get("quoteVolume") or t.get("baseVolume", 0),' in src:
    src = src.replace(
        't.get("quoteVolume") or t.get("baseVolume", 0),',
        'float(t.get("quoteVolume") or t.get("baseVolume") or 0),',
        1
    )
    changes += 1
    print('Fix 3 OK: volume guarded')
else:
    print('Fix 3 SKIP')

# Fix 4: skip None last_price before PriceData
# Find the line with t["open"] if t.get("open") else t["last"] and add guard before it
target = 'op  = t["open"] if t.get("open") else t["last"] / (1 + chg/100)'
if target in src:
    src = src.replace(
        target,
        'last_p = t.get("last") or t.get("close")\n' +
        '                        if not last_p or float(last_p) <= 0: continue\n' +
        '                        op  = t["open"] if t.get("open") else float(last_p) / (1 + chg/100)',
        1
    )
    changes += 1
    print('Fix 4 OK: None last guard added')
else:
    print('Fix 4 SKIP - showing context:')
    idx = src.find('t["open"] if t.get')
    if idx > 0:
        print(repr(src[idx-50:idx+100]))

if changes > 0:
    with open('BreakoutScanner.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'Done - {changes} fixes applied. Restart scanner.')
else:
    print('No changes made.')
