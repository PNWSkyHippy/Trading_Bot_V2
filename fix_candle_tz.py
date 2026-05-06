with open('dashboard.py', encoding='utf-8') as f:
    src = f.read()

old = '                bars["ts"] = pd.to_datetime(bars["ts"], unit="ms")'
new = '                bars["ts"] = pd.to_datetime(bars["ts"], unit="ms", utc=True).dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)'

if old in src:
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fixed - candlestick chart will show PT times')
else:
    print('Not found')
    idx = src.find('to_datetime(bars')
    if idx > 0: print(repr(src[idx-20:idx+80]))
