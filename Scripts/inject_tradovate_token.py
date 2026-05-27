"""
Tradovate token injector — run this in your Ubuntu terminal.

Usage:
    1. In Chrome DevTools → Application → Local Storage → trader.tradovate.com
       Find the key that contains your JWT (look for 'token' or 'accessToken')
       Copy the value

    2. Paste it when prompted, or pipe it:
       echo "<token>" | python Scripts/inject_tradovate_token.py

    3. The script POSTs it to the dashboard feed endpoint and exits.
       The token is NEVER written to disk or logged.

The feed will auto-reconnect with the new token immediately.
Run again whenever your session expires (~30 min).
"""
import json
import sys
import urllib.request

DASHBOARD_URL = "http://127.0.0.1:8125/api/tradovate_token"

def main():
    if not sys.stdin.isatty():
        token = sys.stdin.read().strip()
    else:
        token = input("Paste JWT token (input hidden in terminal): ").strip()

    if not token:
        print("ERROR: no token provided")
        sys.exit(1)

    # Extract raw JWT if pasted with "Bearer <username> eyJ..." format
    if 'eyJ' in token:
        token = token[token.index('eyJ'):]

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
                print("✓ Tradovate real-time feed active")
            else:
                print(f"ERROR: {result}")
    except Exception as e:
        print(f"ERROR contacting dashboard: {e}")
        print("Is web_dashboard.py running?")


if __name__ == "__main__":
    main()
