"""
patch_breakout_integration.py
==============================
Wires the BreakoutScanner → Trading_Bot_V2 signal injection pipeline.

Changes:
  1. BreakoutScanner.py  — imports BreakoutSender, calls send_signal() in send_alert()
  2. bot_engine.py       — starts API server, wires breakout_receiver
  3. scanner_config.json — adds bot_api_url, bot_api_key, bot_min_escalation, bot_enabled
  4. config.py           — adds BOT_API_KEY, BREAKOUT_MIN_ESCALATION

Run once then delete: python patch_breakout_integration.py
"""

import json, os, secrets

# ── 1. BreakoutScanner.py — add sender import and call ──────────────────────
print("Patching BreakoutScanner.py...")
with open("BreakoutScanner.py", encoding="utf-8") as f:
    src = f.read()

# Add import after existing imports
old_import = "from alert_sound import init_audio, _play_pattern"
new_import = ("from alert_sound import init_audio, _play_pattern\n"
              "from breakout_sender import BreakoutSender")

if "from breakout_sender import" not in src:
    if old_import in src:
        src = src.replace(old_import, new_import, 1)
        print("  Added BreakoutSender import")
    else:
        print("  WARN: Could not find import anchor — add manually")

# Initialize sender in AlertSystem.__init__
old_init_end = "        self.running          = False\n        import threading as _thr"
new_init_end = ("        self.running          = False\n"
                "        import threading as _thr\n"
                "        # Bot injection sender\n"
                "        self.bot_sender = BreakoutSender(self.config)")

if "self.bot_sender" not in src:
    if old_init_end in src:
        src = src.replace(old_init_end, new_init_end, 1)
        print("  Added bot_sender to AlertSystem.__init__")
    else:
        print("  WARN: Could not find __init__ anchor — add manually")

# Call send_signal in send_alert() after beep/GUI
old_send = "        if self.config.get(\"enable_email_alert\", False):\n            self._email_alert(signal, message, escalation=escalation)"
new_send = ("        if self.config.get(\"enable_email_alert\", False):\n"
            "            self._email_alert(signal, message, escalation=escalation)\n"
            "        # Inject to Trading Bot V2 if escalation threshold met\n"
            "        if hasattr(self, \"bot_sender\"):\n"
            "            self.bot_sender.send_signal(signal, escalation)")

if "bot_sender.send_signal" not in src:
    if old_send in src:
        src = src.replace(old_send, new_send, 1)
        print("  Added bot_sender.send_signal() call in send_alert()")
    else:
        print("  WARN: Could not find send_alert anchor — add manually")

with open("BreakoutScanner.py", "w", encoding="utf-8") as f:
    f.write(src)
print("  BreakoutScanner.py saved")

# ── 2. bot_engine.py — start API server and wire receiver ───────────────────
print("\nPatching bot_engine.py...")
with open("bot_engine.py", encoding="utf-8") as f:
    be = f.read()

old_be_import = "import config\n"
new_be_import = ("import config\n"
                 "from api_server import start_api_server\n"
                 "from core.breakout_receiver import breakout_receiver\n")

if "from api_server import" not in be:
    if old_be_import in be:
        be = be.replace(old_be_import, new_be_import, 1)
        print("  Added api_server imports")
    else:
        print("  WARN: Could not find import anchor in bot_engine.py")

# Wire receiver after components initialized
old_wire = "        self.logger.info(\"All components initialized successfully.\")"
new_wire = ("        self.logger.info(\"All components initialized successfully.\")\n"
            "        # Wire breakout receiver\n"
            "        breakout_receiver.set_executor(self.trade_executor)\n"
            "        breakout_receiver.set_scanner(self.market_scanner)\n"
            "        start_api_server(port=getattr(config, 'BOT_API_PORT', 8181))\n"
            "        self.logger.info(\"[API] Breakout receiver active on port \"\n"
            "                         f\"{getattr(config, 'BOT_API_PORT', 8181)}\")")

if "breakout_receiver.set_executor" not in be:
    if old_wire in be:
        be = be.replace(old_wire, new_wire, 1)
        print("  Added receiver wiring in BotEngine.__init__")
    else:
        print("  WARN: Could not find init anchor in bot_engine.py")

with open("bot_engine.py", "w", encoding="utf-8") as f:
    f.write(be)
print("  bot_engine.py saved")

# ── 3. scanner_config.json — add bot connection settings ────────────────────
print("\nPatching scanner_config.json...")
with open("scanner_config.json", encoding="utf-8") as f:
    cfg = json.load(f)

if "bot_api_url" not in cfg:
    cfg["bot_api_url"]        = "http://localhost:8181"
    cfg["bot_api_key"]        = ""   # fill in after generating key
    cfg["bot_min_escalation"] = 2    # 0=watchlist 1=moving 2=hot(>5%) 3=rocket(>10%)
    cfg["bot_enabled"]        = True
    with open("scanner_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("  Added bot connection keys to scanner_config.json")
else:
    print("  scanner_config.json already has bot keys")

# ── 4. config.py — add BOT_API_KEY ──────────────────────────────────────────
print("\nPatching config.py...")
with open("config.py", encoding="utf-8") as f:
    cp = f.read()

if "BOT_API_KEY" not in cp:
    # Generate a random API key
    api_key = secrets.token_urlsafe(32)
    addition = (f"\n# ── Breakout Signal API ────────────────────────────────────────\n"
                f"BOT_API_KEY           = \"{api_key}\"   # copy this to scanner_config.json bot_api_key\n"
                f"BOT_API_PORT          = 8181\n"
                f"BREAKOUT_MIN_ESCALATION = 2   # 0-3; only inject escalation >= this\n")
    # Append to end of config
    with open("config.py", "a", encoding="utf-8") as f:
        f.write(addition)
    print(f"  Generated BOT_API_KEY: {api_key}")
    print(f"  >>> Copy this key into scanner_config.json bot_api_key field <<<")

    # Auto-update scanner_config.json with the key
    with open("scanner_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["bot_api_key"] = api_key
    with open("scanner_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print("  Key auto-copied to scanner_config.json")
else:
    print("  BOT_API_KEY already in config.py")

# ── 5. Install fastapi + uvicorn if needed ───────────────────────────────────
print("\nChecking dependencies...")
try:
    import fastapi, uvicorn
    print("  fastapi and uvicorn already installed")
except ImportError:
    print("  Installing fastapi and uvicorn...")
    os.system("pip install fastapi uvicorn --break-system-packages -q")
    print("  Done")

print("""
All patches applied.

Next steps:
  1. Copy core/breakout_receiver.py  → C:\\Users\\Linda\\trading_bot_v2\\core\\
  2. Copy api_server.py              → C:\\Users\\Linda\\trading_bot_v2\\
  3. Copy breakout_sender.py         → C:\\Users\\Linda\\trading_bot_v2\\
  4. Run: python patch_breakout_integration.py  (from trading_bot_v2 dir)
  5. Restart bot:    python bot_engine.py
  6. Restart scanner: python BreakoutScanner.py

The bot will log:
  [API] Breakout receiver active on port 8181

The scanner will log:
  [SENDER] Bot injection enabled → http://localhost:8181

When a ROCKET fires the scanner sends it, bot validates checklist, executes if all pass.
""")
