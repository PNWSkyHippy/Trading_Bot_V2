with open('core/trade_executor.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# Fix entry_time UTC
old1 = '"entry_time":      datetime.utcnow().isoformat(),'
new1 = '"entry_time":      datetime.now().isoformat(),'
if old1 in src:
    src = src.replace(old1, new1, 1); changes += 1; print('Fix 1 OK: entry_time now uses local PT')
else: print('Fix 1 FAIL')

# Fix exit_time UTC in close_trade
old2 = '"exit_time":  datetime.utcnow().isoformat(),'
new2 = '"exit_time":  datetime.now().isoformat(),'
if old2 in src:
    src = src.replace(old2, new2, 1); changes += 1; print('Fix 2 OK: exit_time now uses local PT')
else: print('Fix 2 FAIL')

if changes:
    with open('core/trade_executor.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'Done - {changes} fixes. Restart bot.')
else:
    print('Nothing changed')
