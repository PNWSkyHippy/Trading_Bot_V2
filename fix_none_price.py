with open('BreakoutScanner.py', encoding='utf-8') as f:
    src = f.read()

# Find and fix the None price issue by replacing t["last"] with safe version
# Works regardless of indentation level
old1 = 't["last"], op,'
new1 = 'float(t["last"]) if t.get("last") else None, op,'

old2 = 't.get("high") or t["last"], t.get("low") or t["last"],'
new2 = 'float(t.get("high") or t.get("last") or 0), float(t.get("low") or t.get("last") or 0),'

old3 = 't.get("quoteVolume") or t.get("baseVolume", 0),'
new3 = 'float(t.get("quoteVolume") or t.get("baseVolume") or 0),'

# Also add None check before PriceData construction
old4 = 'chg = t.get("percentage", 0) or 0
                        if chg == 0: continue
                        op  = t["open"] if t.get("open") else t["last"] / (1 + chg/100)'
new4 = 'last_price = t.get("last") or t.get("close")
                        if not last_price or float(last_price) <= 0: continue
                        chg = t.get("percentage", 0) or 0
                        if chg == 0: continue
                        op  = t["open"] if t.get("open") else float(last_price) / (1 + chg/100)'

changes = 0
for old, new in [(old4, new4), (old1, new1), (old2, new2), (old3, new3)]:
    if old in src:
        src = src.replace(old, new, 1)
        changes += 1
        print(f'Fixed: {old[:40]}...')
    else:
        print(f'Skip: {old[:40]}...')

if changes > 0:
    open('BreakoutScanner.py', 'w', encoding='utf-8').write(src)
    print(f'Done - {changes} fixes applied')
else:
    print('Nothing changed')
