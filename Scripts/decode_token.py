"""Decode and show the current Tradovate token info from the running dashboard."""
import json, base64, urllib.request, time

try:
    # Get debug state
    req = urllib.request.Request("http://127.0.0.1:8125/api/tradovate_debug",
                                  data=b"{}", method="POST",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        state = json.loads(r.read())
    print(f"WS URL     : {state.get('ws_url')}")
    print(f"Connected  : {state.get('connected')}")
    print(f"Running    : {state.get('running')}")
    for k, v in (state.get("cache") or {}).items():
        lb = v.get("last_bar")
        if lb:
            from datetime import datetime, timezone
            t = datetime.fromtimestamp(lb["time"], tz=timezone.utc).strftime("%H:%M")
            print(f"  {k:12} bars={v['count']}  last={t}  close={lb['close']}")
except Exception as e:
    print(f"Dashboard error: {e}")

print()
raw = input("Paste your token to decode it (Authorization header value): ").strip()
if "eyJ" in raw:
    raw = raw[raw.index("eyJ"):]
try:
    parts = raw.split(".")
    pad = parts[1] + "=="
    payload = json.loads(base64.urlsafe_b64decode(pad))
    env = payload.get("envEndpoint") or {}
    print(f"\nToken environment:")
    print(f"  marketData : {env.get('marketData', 'N/A')}")
    print(f"  trading    : {env.get('trading', 'N/A')}")
    print(f"  acl        : {payload.get('acl')}")
    exp = payload.get("exp", 0)
    print(f"  expires in : {max(0, int(exp - time.time()))}s")
    md = env.get("marketData", "")
    if "md-live" in md:
        print("\n→ LIVE market data token — should use live WS for real-time ticks")
    elif "md-demo" in md:
        print("\n→ DEMO market data token — slight delay expected (1-2 min)")
    else:
        print("\n→ Unknown endpoint")
except Exception as e:
    print(f"Decode error: {e}")
