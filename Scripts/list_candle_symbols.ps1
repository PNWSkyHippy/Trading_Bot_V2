$script = @"
import sqlite3

conn = sqlite3.connect('data/candle_store.db')
rows = conn.execute('SELECT DISTINCT symbol FROM candles ORDER BY symbol').fetchall()
symbols = [r[0] for r in rows]

crypto = [s for s in symbols if '/' in s]
stocks = [s for s in symbols if '/' not in s]

import sys
mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

if mode == 'crypto':
    for s in crypto:
        print(s)
    print(f'\nTotal crypto: {len(crypto)}')
elif mode == 'stocks':
    for s in stocks:
        print(s)
    print(f'\nTotal stocks: {len(stocks)}')
else:
    print('--- CRYPTO ---')
    for s in crypto:
        print(s)
    print(f'\nTotal crypto: {len(crypto)}')
    print('\n--- STOCKS ---')
    for s in stocks:
        print(s)
    print(f'\nTotal stocks: {len(stocks)}')
    print(f'Grand total:  {len(symbols)}')

conn.close()
"@

$mode = if ($args.Count -gt 0) { $args[0] } else { "all" }
cd C:\Users\Linda\trading_bot_v2
.\venv312\Scripts\python.exe -c $script $mode
