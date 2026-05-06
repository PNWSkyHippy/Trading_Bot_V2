# Fix dashboard timestamp double-conversion
# Timestamps are now stored in PT (after migration), not UTC.
# Remove the .tz_localize('UTC').tz_convert('America/Los_Angeles') calls.

with open('dashboard.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# Fix exit_time display
old1 = '''            exit_dt_local = exit_dt.tz_localize("UTC").tz_convert("America/Los_Angeles")
            exit_str      = exit_dt_local.strftime("%m/%d %H:%M PDT")'''
new1 = '''            exit_str      = exit_dt.strftime("%m/%d %H:%M PT")'''
if old1 in src:
    src = src.replace(old1, new1, 1); changes += 1; print('Fix 1 OK: exit_time')
else: print('Fix 1 SKIP')

# Fix entry_time display in positions
old2 = '''            entry_dt_local = entry_dt.tz_localize("UTC").tz_convert("America/Los_Angeles")
            entry_str      = entry_dt_local.strftime("%m/%d %H:%M PDT")'''
new2 = '''            entry_str      = entry_dt.strftime("%m/%d %H:%M PT")'''
if old2 in src:
    src = src.replace(old2, new2, 1); changes += 1; print('Fix 2 OK: entry_time positions')
else: print('Fix 2 SKIP')

# Fix entry_time display in trade log
old3 = '''            entry_dt_local = entry_dt.tz_localize("UTC").tz_convert("America/Los_Angeles")
            entry_str      = entry_dt_local.strftime("%m/%d %H:%M PDT")'''
new3 = '''            entry_str      = entry_dt.strftime("%m/%d %H:%M PT")'''
if old3 in src:
    src = src.replace(old3, new3); changes += 1; print('Fix 3 OK: entry_time trade log')
else: print('Fix 3 SKIP')

if changes:
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'Done - {changes} fixes applied. Restart Streamlit.')
else:
    print('Nothing changed')
