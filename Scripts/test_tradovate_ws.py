"""
Quick standalone test — connects to Tradovate demo WS and shows raw server responses.
Run: python Scripts/test_tradovate_ws.py
Paste your token when prompted (same copy/paste from DevTools Network PATCH → Authorization).
"""
import json
import sys
import threading
import time

TOKEN_PROMPT = "Paste token (or Authorization header value): "

def main():
    try:
        import websocket
    except ImportError:
        print("ERROR: pip install websocket-client")
        sys.exit(1)

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
    else:
        raw = input(TOKEN_PROMPT).strip()

    # Strip "Bearer Ron Hensley " or any prefix before eyJ
    if "eyJ" in raw:
        token = raw[raw.index("eyJ"):]
    else:
        token = raw

    # Decode JWT payload to see envEndpoint
    try:
        import base64
        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        md_url = (payload.get("envEndpoint") or {}).get("marketData", "UNKNOWN")
        exp    = payload.get("exp", 0)
        now    = time.time()
        print(f"\nToken info:")
        print(f"  marketData endpoint : {md_url}")
        print(f"  expires in          : {max(0, int(exp - now))}s  ({'EXPIRED' if exp < now else 'OK'})")
        print(f"  sub (contact ID)    : {payload.get('sub')}")
        print(f"  acl                 : {payload.get('acl')}")
        use_live = "md-live" in md_url
    except Exception as e:
        print(f"  (could not decode JWT: {e})")
        use_live = False

    ws_url = ("wss://md-live.tradovateapi.com/v1/websocket"
              if use_live else
              "wss://md-demo.tradovateapi.com/v1/websocket")
    print(f"\nConnecting to: {ws_url}\n")

    done = threading.Event()
    msgs = []

    def on_open(ws):
        print(f"[WS] connected — sending authorize frame")
        frame = f"authorize\n1\n\n{token}"
        ws.send(frame)

    def on_message(ws, msg):
        msgs.append(msg)
        print(f"[WS] << {msg[:400]}")
        # stop after a few messages
        if len(msgs) >= 6:
            ws.close()

    def on_error(ws, err):
        print(f"[WS] ERROR: {err}")

    def on_close(ws, code, reason):
        print(f"[WS] closed code={code} reason={reason}")
        done.set()

    ws = websocket.WebSocketApp(ws_url,
        on_open=on_open, on_message=on_message,
        on_error=on_error, on_close=on_close)

    t = threading.Thread(target=lambda: ws.run_forever(ping_interval=20))
    t.daemon = True
    t.start()
    done.wait(timeout=15)
    print("\nDone.")

if __name__ == "__main__":
    main()
