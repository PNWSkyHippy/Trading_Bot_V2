with open('core/position_monitor.py', encoding='utf-8') as f:
    src = f.read()

old = '''def _get_position_age_seconds(trade: Dict) -> float:
    """Return how many seconds a position has been open."""
    try:
        entry_raw = trade.get("entry_time", "")
        if not entry_raw:
            return 0.0
        entry_dt = pd.to_datetime(entry_raw)
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        return (now_utc - entry_dt).total_seconds()
    except Exception:
        return 0.0'''

new = '''def _get_position_age_seconds(trade: Dict) -> float:
    """Return how many seconds a position has been open.
    Entry times are stored in local PT (naive, no timezone).
    Compare against local time — NOT UTC.
    """
    try:
        entry_raw = trade.get("entry_time", "")
        if not entry_raw:
            return 0.0
        entry_dt = pd.to_datetime(entry_raw)
        # Strip any timezone info and compare as local time
        if entry_dt.tzinfo is not None:
            entry_dt = entry_dt.replace(tzinfo=None)
        now_local = datetime.now()   # local PT, no timezone
        age = (now_local - entry_dt).total_seconds()
        # Sanity check: age should never be negative or > 24 hours for a day trade
        if age < 0 or age > 86400:
            return 0.0
        return age
    except Exception:
        return 0.0'''

if old in src:
    with open('core/position_monitor.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fixed - position age now uses local PT not UTC')
else:
    print('Not found')
    idx = src.find('_get_position_age_seconds')
    if idx > 0: print(repr(src[idx:idx+300]))
