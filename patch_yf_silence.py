src = open('BreakoutScanner.py', encoding='utf-8').read()
old = '    import yfinance as yf'
new = '    import yfinance as yf\n    import logging as _logging\n    _logging.getLogger("yfinance").setLevel(_logging.CRITICAL)\n    _logging.getLogger("yfinance.base").setLevel(_logging.CRITICAL)\n    _logging.getLogger("yfinance.utils").setLevel(_logging.CRITICAL)\n    _logging.getLogger("peewee").setLevel(_logging.CRITICAL)'
if old in src:
    open('BreakoutScanner.py', 'w', encoding='utf-8').write(src.replace(old, new, 1))
    print('Done')
else:
    print('Not found')
