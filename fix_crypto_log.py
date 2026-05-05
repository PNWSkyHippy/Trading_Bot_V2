with open('BreakoutScanner.py', encoding='utf-8') as f:
    src = f.read()
new = src.replace(
    'logger.error(f"Crypto history error {symbol}: {e}")',
    'logger.debug(f"Crypto history skip {symbol}: {e}")'
)
if new != src:
    open('BreakoutScanner.py', 'w', encoding='utf-8').write(new)
    print('Fixed')
else:
    print('Not found - already patched or different text')
    # show context
    idx = src.find('Crypto history')
    if idx > 0: print(repr(src[idx-20:idx+80]))
