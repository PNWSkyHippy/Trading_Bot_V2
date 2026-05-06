# Fix capital growth chart X-axis showing UTC instead of PT
# The timestamps in the capital table are stored in PT after migration.
# Plotly is treating them as UTC. Fix by parsing as naive datetimes.

with open('dashboard.py', encoding='utf-8') as f:
    src = f.read()

old = '''        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_sum["trade_date"], y=df_sum["ending_capital"], mode="lines+markers", name="Capital", line=dict(color="#4fc3f7", width=2), fill="tozeroy", fillcolor="rgba(79,195,247,0.08)"))'''

new = '''        # Parse trade_date as local PT — strip any tz info so Plotly renders as-is
        import pandas as _pd
        df_sum["trade_date"] = _pd.to_datetime(df_sum["trade_date"]).dt.tz_localize(None)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_sum["trade_date"], y=df_sum["ending_capital"], mode="lines+markers", name="Capital", line=dict(color="#4fc3f7", width=2), fill="tozeroy", fillcolor="rgba(79,195,247,0.08)"))'''

if old in src:
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fixed - chart X-axis will show PT times')
else:
    print('Not found')
    idx = src.find('go.Scatter(x=df_sum')
    if idx > 0: print(repr(src[idx-50:idx+150]))
