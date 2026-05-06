with open('BreakoutScanner.py', encoding='utf-8') as f:
    src = f.read()

old = '''                try:
                    chg = t.get("percentage", 0) or 0
                    if chg == 0: continue
                    op  = t["open"] if t.get("open") else t["last"] / (1 + chg/100)
                    pd_obj = PriceData(
                        sym, t["last"], op,
                        t.get("high") or t["last"], t.get("low") or t["last"],
                        t.get("quoteVolume") or t.get("baseVolume", 0),
                        datetime.now(), AssetType.CRYPTO,
                    )'''

new = '''                try:
                    last = t.get("last") or t.get("close")
                    if not last or last <= 0: continue
                    chg = t.get("percentage", 0) or 0
                    if chg == 0: continue
                    op  = t["open"] if t.get("open") else last / (1 + chg/100)
                    pd_obj = PriceData(
                        sym, float(last), float(op) if op else float(last),
                        float(t.get("high") or last), float(t.get("low") or last),
                        float(t.get("quoteVolume") or t.get("baseVolume") or 0),
                        datetime.now(), AssetType.CRYPTO,
                    )'''

if old in src:
    open('BreakoutScanner.py', 'w', encoding='utf-8').write(src.replace(old, new, 1))
    print('Fixed')
else:
    print('Not found - check if multi-exchange patch was applied')
    idx = src.find('pd_obj = PriceData')
    if idx > 0: print(repr(src[idx-200:idx+100]))
