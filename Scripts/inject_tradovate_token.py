"""
Tradovate token injector.

Usage:
    1. In Chrome DevTools → Application → Local Storage → trader.tradovate.com
       Find 'accessToken', copy the value

    2. Run and paste when prompted:
           python Scripts/inject_tradovate_token.py

       Or pipe it:
           echo "<token>" | python Scripts/inject_tradovate_token.py

    Token lasts ~20 min but the feed now auto-renews via Tradovate's
    renewaccesstoken endpoint — you typically only need this once per session.
"""
import json
import sys
import urllib.request

DASHBOARD_URL = "http://127.0.0.1:8125/api/tradovate_token"


def main():
    if not sys.stdin.isatty():
        token = sys.stdin.read().strip()
    else:
        token = input("Paste Tradovate accessToken: ").strip()

    if not token:
        print("ERROR: no token provided")
        sys.exit(1)

    # Strip "Bearer <username> " prefix if pasted from DevTools Network tab
    if "eyJ" in token:
        token = token[token.index("eyJ"):]

    payload = json.dumps({"token": token}).encode()
    req = urllib.request.Request(
        DASHBOARD_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print("✓ Tradovate feed active — auto-renews every ~18 min")
            else:
                print(f"ERROR: {result}")
    except Exception as e:
        print(f"ERROR contacting dashboard: {e}")
        print("Is web_dashboard.py running on port 8125?")


if __name__ == "__main__":
    main()
