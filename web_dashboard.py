"""HTML dashboard bridge.

Run: python web_dashboard.py
"""
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from chart_patterns import PatternDetector as _PatternDetector
except Exception:
    _PatternDetector = None

# Cache last 200 bars per symbol/tf — populated when /api/chart/data is served,
# consumed by /api/chart/patterns.  No I/O needed in the patterns endpoint.
_pattern_bars_cache: dict = {}   # key: "SYMBOL/tf"

ROOT = Path(__file__).parent
HTML_ROOT = ROOT / "Html-Files"
if not HTML_ROOT.exists():
    HTML_ROOT = ROOT / "HTML-Files"

_config = None
try:
    import config as _config
    _default_db_path = Path(_config.DB_PATH)
    if not _default_db_path.is_absolute():
        _default_db_path = ROOT / _default_db_path
except Exception:
    _default_db_path = ROOT / "data" / "trading_bot.db"

DB_PATH = Path(os.environ.get("WEB_DASHBOARD_DB_PATH", str(_default_db_path)))
BOT_SCRIPT = ROOT / "bot_engine.py"
BOT_PYTHON = ROOT / "venv312" / "Scripts" / "python.exe"
WEB_DASHBOARD_PORT = 8125
HOSTINGER_SSH_TARGET = os.environ.get("HOSTINGER_SSH_TARGET", "ronh@187.127.248.52")
MAX_POST_BYTES = int(os.environ.get("WEB_DASHBOARD_MAX_POST_BYTES", "1048576"))
TERMINAL_IDLE_SECONDS = int(os.environ.get("WEB_TERMINAL_IDLE_SECONDS", "900"))
TERMINAL_MAX_INPUT_BYTES = int(os.environ.get("WEB_TERMINAL_MAX_INPUT_BYTES", "8192"))
RECOVERY_TOKEN_MAX_CHARS = int(os.environ.get("WEB_RECOVERY_TOKEN_MAX_CHARS", "128"))
PASSWORD_MAX_CHARS = int(os.environ.get("WEB_PASSWORD_MAX_CHARS", "256"))

risk_manager = None
db = None
monitor = None
_close_lock = threading.Lock()
_close_requests = {}
_terminal_sessions = {}
_terminal_lock = threading.Lock()
_login_failures = {}
_login_lock = threading.Lock()
_recovery_failures = {}
_recovery_lock = threading.Lock()

try:
    from data.database import db as _db
    db = _db
except Exception:
    db = None

try:
    from core.risk_manager import risk_manager as _risk_manager
    risk_manager = _risk_manager
except Exception:
    risk_manager = None

try:
    from core.position_monitor import monitor as _monitor
    monitor = _monitor
except Exception:
    monitor = None

from core.strategy_registry import STRATEGY_MODULES as _STRATEGY_MODULES

# ── Tradovate real-time feed (optional) ──────────────────────────────────────
# Activated when a JWT token is posted to /api/tradovate_token.
# Falls back to yfinance silently when not active.
_tradovate_feed = None
_tradovate_feed_lock = threading.Lock()   # guards create/recreate of _tradovate_feed
try:
    from core.tradovate_feed import TradovateFeed, init_feed as _tv_init_feed
    import logging as _logging
    _logging.getLogger("core.tradovate_feed").setLevel(_logging.WARNING)
    _tradovate_available = True
except Exception:
    _tradovate_available = False

# Map dashboard symbol → Tradovate front-month contract name
# Format: ROOT → ROOT + MONTH_CODE + YEAR_CODE  (U6 = September 2026)
# Update month code each quarterly rollover: U6→Z6 (Dec), Z6→H7 (Mar), H7→M7 (Jun)
TRADOVATE_SYMBOL_MAP = {
    # ── CME Equity Index Micros & Minis ──────────────────────────────────
    "MES":  "MESU6",   "ES":  "ESU6",
    "MNQ":  "MNQU6",   "NQ":  "NQU6",
    "M2K":  "M2KU6",   "RTY": "RTYU6", "MNK": "MNKU6",
    # ── CBOT Equity ──────────────────────────────────────────────────────
    "MYM":  "MYMU6",   "YM":  "YMU6",
    # ── NYMEX Energy ─────────────────────────────────────────────────────
    "MCL":  "MCLM6",   "CL":  "CLN6",   # CL front-month is July (N6) in late May
    "NG":   "NGN6",    "MNG": "MNGN6",
    # ── COMEX Metals ─────────────────────────────────────────────────────
    "MGC":  "MGCM6",   "GC":  "GCM6",
    "SI":   "SIU6",    "SIL": "SILQ6",  # Silver rolls to Sep (U6) by May
    # ── CME Crypto Micros ────────────────────────────────────────────────
    "MBT":  "MBTM6",   "MET": "METM6",
}

# Known Tradovate numeric contract IDs (stable per contract, not per session)
# IDs discovered via: GET /v1/contract/find?name=<NAME>  (auto-populated at runtime)
TRADOVATE_SYMBOL_IDS: dict = {
    "MESM6":  3961353,   # confirmed
    # All others are auto-looked up via REST on first chart request and cached here
}


# ── Dashboard Auth ────────────────────────────────────────────────────────────
# User store: data/dashboard_users.json
# Schema: { username: { "hash": "pbkdf2_sha256:iterations:salt:hex", "role": "admin"|"user",
#                        "force_change": bool } }
#
# On first start the file is seeded with admin / admin (force_change=True).
# Admin is redirected to /setup to change the password and create a personal
# account before the dashboard becomes accessible.
#
# Recovery if locked out:
#   • A one-time recovery token is printed to the console every server start.
#     Visit /recover, paste the token, and reset the admin password.
#   • CLI: python Scripts/set_dashboard_password.py
#   • Nuclear: delete data/dashboard_users.json → re-seeds admin/admin on next start.

_ADMIN_DEFAULT  = "admin"
SESSION_TTL     = 86400           # 24 hours
_sessions: dict[str, tuple[float, str]] = {}   # token → (expiry, username)
_sessions_lock  = threading.Lock()
_RECOVERY_TOKEN = secrets.token_hex(24)        # regenerated each start

# Legacy JSON path — only used during one-time migration
_USERS_FILE_LEGACY = ROOT / "data" / "dashboard_users.json"


# ── Fernet helper (shared key with API key encryption) ────────────────────────

def _get_fernet():
    """Return a Fernet instance using the key from the OS credential store.
    Returns None if the key hasn’t been set up yet (new install pre-setup)."""
    try:
        import keyring as _kr
        from cryptography.fernet import Fernet as _F
        raw = _kr.get_password("trading_bot_v2", "fernet_key")
        return _F(raw.encode()) if raw else None
    except Exception:
        return None


def _enc_hash(hash_str: str) -> str:
    """Encrypt a password hash string for DB storage.
    Falls back to plain: prefix if the Fernet key isn’t set up yet."""
    f = _get_fernet()
    if f:
        return f.encrypt(hash_str.encode()).decode()
    return "plain:" + hash_str


def _dec_hash(stored: str) -> str:
    """Decrypt a stored hash_enc value back to the raw sha256 hash string."""
    if stored.startswith("plain:"):
        return stored[6:]
    f = _get_fernet()
    if not f:
        raise RuntimeError(
            "Fernet key missing — run: python Scripts/setup_encryption.py"
        )
    from cryptography.fernet import Fernet as _F
    return f.decrypt(stored.encode()).decode()


# ── User store (DB-backed) ────────────────────────────────────────────────────

def _db_path() -> str:
    return str(DB_PATH)


def _load_users() -> dict:
    """Return {username: {hash, role, force_change}} from DB."""
    try:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM dashboard_users").fetchall()
        conn.close()
        result = {}
        for r in rows:
            try:
                h = _dec_hash(r["hash_enc"])
            except Exception:
                h = ""   # decrypt failed — key mismatch, treat as locked
            result[r["username"]] = {
                "hash":         h,
                "role":         r["role"],
                "force_change": bool(r["force_change"]),
            }
        return result
    except Exception:
        return {}


def _save_users(users: dict) -> None:
    """Write the users dict back to DB, encrypting hashes."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = sqlite3.connect(_db_path())
        for username, rec in users.items():
            raw_hash  = rec.get("hash", "")
            enc       = _enc_hash(raw_hash) if raw_hash else ""
            role      = rec.get("role", "user")
            force     = 1 if rec.get("force_change") else 0
            conn.execute("""
                INSERT INTO dashboard_users (username, hash_enc, role, force_change, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    hash_enc     = excluded.hash_enc,
                    role         = excluded.role,
                    force_change = excluded.force_change,
                    updated_at   = excluded.updated_at
            """, (username, enc, role, force, now, now))
        conn.commit()
        conn.close()
    except Exception as e:
        import logging as _lg
        _lg.getLogger("dashboard.auth").error(f"[AUTH] _save_users error: {e}")


def _delete_user_db(username: str) -> None:
    try:
        conn = sqlite3.connect(_db_path())
        conn.execute("DELETE FROM dashboard_users WHERE username=?", (username,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _ensure_admin_seeded() -> None:
    """Seed admin/admin (force_change=True) if no users exist in DB yet.
    Also migrates the legacy JSON file if present."""
    try:
        # One-time migration from dashboard_users.json → DB
        if _USERS_FILE_LEGACY.exists():
            try:
                old = json.loads(_USERS_FILE_LEGACY.read_text(encoding="utf-8"))
                users_to_migrate = {}
                for u, v in old.items():
                    if isinstance(v, str):
                        users_to_migrate[u] = {"hash": v, "role": "admin" if u == "admin" else "user", "force_change": False}
                    else:
                        users_to_migrate[u] = v
                if users_to_migrate:
                    _save_users(users_to_migrate)
                    import logging as _lg
                    _lg.getLogger("dashboard.auth").info(
                        f"[AUTH] Migrated {len(users_to_migrate)} user(s) from JSON to DB")
                _USERS_FILE_LEGACY.rename(_USERS_FILE_LEGACY.with_suffix(".json.migrated"))
            except Exception as me:
                import logging as _lg
                _lg.getLogger("dashboard.auth").warning(f"[AUTH] JSON migration failed: {me}")

        conn = sqlite3.connect(_db_path())
        count = conn.execute("SELECT COUNT(*) FROM dashboard_users").fetchone()[0]
        conn.close()
        if count == 0:
            _save_users({_ADMIN_DEFAULT: {
                "hash":         _hash_password(_ADMIN_DEFAULT),
                "role":         "admin",
                "force_change": True,
            }})
    except Exception as e:
        import logging as _lg
        _lg.getLogger("dashboard.auth").error(f"[AUTH] _ensure_admin_seeded error: {e}")


def _needs_setup() -> bool:
    """True when the only account is admin with force_change=True (fresh install)."""
    users = _load_users()
    if len(users) != 1:
        return False
    rec = users.get(_ADMIN_DEFAULT, {})
    return bool(rec.get("force_change"))


def _hash_password(password: str) -> str:
    iterations = 260_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256:{iterations}:{salt}:{digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, *parts = (stored or "").split(":")
        if scheme == "pbkdf2_sha256" and len(parts) == 3:
            iterations_raw, salt, expected = parts
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations_raw),
            ).hex()
            return secrets.compare_digest(actual, expected)
        if scheme == "sha256" and len(parts) == 2:
            # Legacy hash format — accepted for backward compatibility only.
            # New passwords are stored as pbkdf2_sha256 (see _hash_password).
            # CodeQL CWE-916: SHA-256 is intentionally weak here; this branch
            # is only reached for hashes created before the pbkdf2 upgrade and
            # is never used for new accounts.
            salt, expected = parts
            actual = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            return secrets.compare_digest(actual, expected)
        return False
    except Exception:
        return False


def _auth_check(username: str, password: str) -> bool:
    users = _load_users()
    rec   = users.get(username)
    if not rec:
        return False
    stored = rec.get("hash", "")
    ok = _verify_password(password, stored)
    if ok and stored.startswith("sha256:"):
        # Legacy pre-pbkdf2 hash (only reachable via migrated accounts) — now that
        # we have the plaintext password in hand, transparently upgrade it so this
        # weak hash (CodeQL py/weak-sensitive-data-hashing) is never used again.
        try:
            users[username]["hash"] = _hash_password(password)
            _save_users(users)
        except Exception:
            pass  # upgrade is best-effort; login still succeeds either way
    return ok



def _login_throttle_key(username: str, ip: str) -> str:
    return f"{str(ip or 'unknown')}:{str(username or '').lower()}"


def _login_retry_after(username: str, ip: str) -> int:
    """Return seconds to wait when repeated login failures trip the throttle."""
    now = time.time()
    key = _login_throttle_key(username, ip)
    with _login_lock:
        failures = [t for t in _login_failures.get(key, []) if now - t < 300]
        _login_failures[key] = failures
        if len(failures) < 5:
            return 0
        oldest = min(failures)
        return max(1, int(300 - (now - oldest)))


def _record_login_attempt(username: str, ip: str, ok: bool) -> None:
    key = _login_throttle_key(username, ip)
    now = time.time()
    with _login_lock:
        if ok:
            _login_failures.pop(key, None)
            return
        failures = [t for t in _login_failures.get(key, []) if now - t < 300]
        failures.append(now)
        _login_failures[key] = failures[-10:]

def _recovery_retry_after(ip: str) -> int:
    """Return seconds to wait when repeated recovery failures trip the throttle."""
    now = time.time()
    key = str(ip or "unknown")
    with _recovery_lock:
        failures = [t for t in _recovery_failures.get(key, []) if now - t < 900]
        _recovery_failures[key] = failures
        if len(failures) < 5:
            return 0
        oldest = min(failures)
        return max(1, int(900 - (now - oldest)))


def _record_recovery_attempt(ip: str, ok: bool) -> None:
    key = str(ip or "unknown")
    now = time.time()
    with _recovery_lock:
        if ok:
            _recovery_failures.pop(key, None)
            return
        failures = [t for t in _recovery_failures.get(key, []) if now - t < 900]
        failures.append(now)
        _recovery_failures[key] = failures[-10:]
def _is_admin(username: str) -> bool:
    users = _load_users()
    return users.get(username, {}).get("role") == "admin"


def _user_force_change(username: str) -> bool:
    users = _load_users()
    return bool(users.get(username, {}).get("force_change"))


# ── Session management ────────────────────────────────────────────────────────

def _new_session(username: str) -> str:
    token = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[token] = (time.time() + SESSION_TTL, username)
    return token


def _valid_session(token: str) -> bool:
    if not token:
        return False
    with _sessions_lock:
        rec = _sessions.get(token)
        if not rec:
            return False
        if time.time() > rec[0]:
            del _sessions[token]
            return False
        return True


def _session_user(token: str) -> str:
    with _sessions_lock:
        rec = _sessions.get(token)
        return rec[1] if rec else ""


def _revoke_session(token: str) -> None:
    with _sessions_lock:
        _sessions.pop(token, None)


# ── Auth HTML pages (all inline — zero external dependencies) ─────────────────

def _auth_page(title: str, heading: str, sub: str, form_html: str,
               error_msg: str = "Something went wrong.", extra_js: str = "") -> bytes:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Bot &mdash; {title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0f172a;display:flex;align-items:center;justify-content:center;
       min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  .card{{background:#1e293b;border:1px solid #334155;border-radius:12px;
        padding:40px 36px;width:400px;box-shadow:0 20px 60px rgba(0,0,0,.5)}}
  h1{{color:#f1f5f9;font-size:1.3rem;font-weight:600;margin-bottom:6px}}
  p.sub{{color:#64748b;font-size:.85rem;margin-bottom:28px}}
  label{{display:block;color:#94a3b8;font-size:.78rem;font-weight:500;
        margin-bottom:5px;letter-spacing:.04em;text-transform:uppercase}}
  input{{width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;
        color:#f1f5f9;font-size:.95rem;padding:10px 12px;outline:none;transition:border-color .15s}}
  input:focus{{border-color:#6366f1}}
  .field{{margin-bottom:16px}}
  button{{width:100%;background:#6366f1;border:none;border-radius:6px;color:#fff;
         cursor:pointer;font-size:.95rem;font-weight:600;padding:11px;margin-top:4px;
         transition:background .15s}}
  button:hover{{background:#4f46e5}}
  .err{{background:#450a0a;border:1px solid #7f1d1d;border-radius:6px;
       color:#fca5a5;font-size:.83rem;padding:10px 12px;margin-bottom:16px;display:none}}
  .err.show{{display:block}}
  .notice{{background:#1c3048;border:1px solid #1e40af;border-radius:6px;
           color:#93c5fd;font-size:.82rem;padding:10px 12px;margin-bottom:16px;line-height:1.5}}
  hr{{border:none;border-top:1px solid #334155;margin:20px 0}}
  .sec{{color:#94a3b8;font-size:.78rem;font-weight:600;text-transform:uppercase;
        letter-spacing:.06em;margin-bottom:14px}}
</style>
</head>
<body><div class="card">
  <h1>{heading}</h1><p class="sub">{sub}</p>
  <div class="err" id="err">{error_msg}</div>
  {form_html}
</div><script>{extra_js}</script></body></html>"""
    return html.encode("utf-8")


# Login page
_LOGIN_PAGE = lambda: _auth_page("Login", "Trading Bot Dashboard", "Sign in to continue", """
<form id="form">
  <div class="field"><label>Username</label>
    <input type="text" id="u" autocomplete="username" autofocus></div>
  <div class="field"><label>Password</label>
    <input type="password" id="p" autocomplete="current-password"></div>
  <button type="submit">Sign in</button>
</form>""", error_msg="Invalid username or password.", extra_js="""
document.getElementById("form").addEventListener("submit",async e=>{
  e.preventDefault();
  const r=await fetch("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({username:document.getElementById("u").value,
                         password:document.getElementById("p").value})});
  if(r.ok){location.href=new URLSearchParams(location.search).get("next")||"/";}
  else{document.getElementById("err").classList.add("show");}
});""")

# First-run setup: change admin password + create personal account
_SETUP_PAGE = lambda: _auth_page("Setup", "First-Time Setup",
  "The default admin/admin credentials are active. Change the admin password and create your personal account to continue.", """
<div class="notice">&#x26A0;&#xFE0F; <strong>Default credentials are in use.</strong><br>
Complete this form before the dashboard becomes accessible.</div>
<p class="sec">&#x1F512; Change Admin Password</p>
<form id="form">
  <div class="field"><label>New Admin Password (min 8 chars)</label>
    <input type="password" id="ap" autocomplete="new-password" autofocus></div>
  <div class="field"><label>Confirm Admin Password</label>
    <input type="password" id="ap2" autocomplete="new-password"></div>
  <hr>
  <p class="sec">&#x1F464; Create Your Personal Account</p>
  <div class="field"><label>Your Username</label>
    <input type="text" id="u" autocomplete="username"></div>
  <div class="field"><label>Your Password (min 8 chars)</label>
    <input type="password" id="p" autocomplete="new-password"></div>
  <div class="field"><label>Confirm Your Password</label>
    <input type="password" id="p2" autocomplete="new-password"></div>
  <button type="submit">Save &amp; Enter Dashboard</button>
</form>""", extra_js="""
document.getElementById("form").addEventListener("submit",async e=>{
  e.preventDefault();
  const ap=document.getElementById("ap").value,ap2=document.getElementById("ap2").value,
        u=document.getElementById("u").value.trim(),
        p=document.getElementById("p").value,p2=document.getElementById("p2").value;
  const err=document.getElementById("err");err.classList.remove("show");
  if(ap.length<8){err.textContent="Admin password must be at least 8 characters.";err.classList.add("show");return;}
  if(ap!==ap2){err.textContent="Admin passwords do not match.";err.classList.add("show");return;}
  if(!u){err.textContent="Your username cannot be empty.";err.classList.add("show");return;}
  if(u.toLowerCase()==="admin"){err.textContent="Choose a username other than ‘admin’.";err.classList.add("show");return;}
  if(p.length<8){err.textContent="Your password must be at least 8 characters.";err.classList.add("show");return;}
  if(p!==p2){err.textContent="Your passwords do not match.";err.classList.add("show");return;}
  const r=await fetch("/api/auth/setup",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({admin_password:ap,username:u,password:p})});
  const d=await r.json();
  if(r.ok){location.href="/";}
  else{err.textContent=d.message||"Setup failed.";err.classList.add("show");}
});""")

# Recovery page (console token required)
_RECOVER_PAGE = lambda: _auth_page("Recovery", "Account Recovery",
  "Paste the recovery token from your server console to reset the admin password.", """
<div class="notice">&#x1F511; Find the recovery token in the server console output<br>
(printed each time the dashboard starts).</div>
<form id="form">
  <div class="field"><label>Recovery Token</label>
    <input type="text" id="tok" autocomplete="off" spellcheck="false"></div>
  <div class="field"><label>New Admin Password (min 8 chars)</label>
    <input type="password" id="p" autocomplete="new-password"></div>
  <div class="field"><label>Confirm Password</label>
    <input type="password" id="p2" autocomplete="new-password"></div>
  <button type="submit">Reset Admin Password</button>
</form>""", extra_js="""
document.getElementById("form").addEventListener("submit",async e=>{
  e.preventDefault();
  const p=document.getElementById("p").value,p2=document.getElementById("p2").value;
  const err=document.getElementById("err");err.classList.remove("show");
  if(p.length<8){err.textContent="Password must be at least 8 characters.";err.classList.add("show");return;}
  if(p!==p2){err.textContent="Passwords do not match.";err.classList.add("show");return;}
  const r=await fetch("/api/auth/recover",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({token:document.getElementById("tok").value.trim(),password:p})});
  const d=await r.json();
  if(r.ok){location.href="/login";}
  else{err.textContent=d.message||"Recovery failed.";err.classList.add("show");}
});""")


def _api_keys_page() -> bytes:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Bot — API Keys</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0f172a;color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:32px 24px}
  h1{font-size:1.25rem;font-weight:600;margin-bottom:4px}
  p.sub{color:#64748b;font-size:.85rem;margin-bottom:24px}
  .card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:24px;margin-bottom:24px}
  h2{font-size:.85rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:16px}
  table{width:100%;border-collapse:collapse;font-size:.88rem}
  th{text-align:left;color:#64748b;font-weight:500;padding:6px 10px;border-bottom:1px solid #334155;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
  td{padding:9px 10px;border-bottom:1px solid #1a2740;vertical-align:middle}
  tr:last-child td{border-bottom:none}
  tr:hover td{background:#1a2740}
  .svc{color:#818cf8;font-weight:600}
  .kn{color:#94a3b8}
  .val{font-family:ui-monospace,monospace;font-size:.82rem;color:#34d399;word-break:break-all;max-width:340px}
  .val.hidden{color:#334155;letter-spacing:.12em;user-select:none}
  .ts{color:#475569;font-size:.75rem;white-space:nowrap}
  .btn{border:none;border-radius:5px;cursor:pointer;font-size:.78rem;font-weight:600;padding:5px 11px;transition:background .15s;white-space:nowrap}
  .eye{background:#172033;color:#93c5fd}.eye:hover{background:#1e3a5f}
  .edit{background:#172a1e;color:#6ee7b7}.edit:hover{background:#065f46}
  .del{background:#2d0a0a;color:#fca5a5}.del:hover{background:#7f1d1d}
  .add-btn{background:#6366f1;color:#fff;padding:9px 18px;font-size:.88rem;border-radius:7px;border:none;cursor:pointer;font-weight:600;margin-top:16px;transition:background .15s}
  .add-btn:hover{background:#4f46e5}
  .save-btn{background:#059669;color:#fff}.save-btn:hover{background:#047857}
  .cancel-btn{background:#334155;color:#94a3b8}.cancel-btn:hover{background:#475569}
  .actions{display:flex;gap:6px}
  .add-form{display:none;margin-top:20px;padding-top:20px;border-top:1px solid #334155}
  .add-form.open{display:block}
  .frow{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
  .frow input{flex:1;min-width:150px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#f1f5f9;font-size:.88rem;padding:8px 11px;outline:none}
  .frow input:focus{border-color:#6366f1}
  .notice{background:#1c2f4a;border:1px solid #1e40af;border-radius:6px;color:#93c5fd;font-size:.82rem;padding:10px 14px;margin-bottom:20px;line-height:1.6}
  .back{color:#6366f1;font-size:.85rem;text-decoration:none;display:inline-flex;align-items:center;gap:4px;margin-bottom:22px}
  .back:hover{color:#818cf8}
  .empty{color:#475569;font-size:.85rem;padding:8px 0}
  .toast{position:fixed;bottom:24px;right:24px;background:#059669;color:#fff;padding:10px 18px;border-radius:8px;font-size:.88rem;font-weight:500;opacity:0;transition:opacity .2s;pointer-events:none}
  .toast.show{opacity:1}
  .toast.err{background:#7f1d1d}
</style>
</head>
<body>
<a class="back" href="/">← Back to Dashboard</a>
<h1>\U0001f511 API Key Manager</h1>
<p class="sub">Keys stored encrypted in the database — admin eyes only.</p>
<div class="notice">
  Values are decrypted for display here. Changes take effect on the next bot restart
  (config.py reloads at import time).<br>
  <strong>Fallback chain:</strong> DB (encrypted) → .env → empty string.
</div>
<div class="card">
  <h2>Stored Keys</h2>
  <div id="tbl"></div>
  <button class="add-btn" onclick="openAdd()">+ Add / Update Key</button>
  <div class="add-form" id="add-form">
    <div class="frow">
      <input type="text"     id="f-svc" placeholder="Service  (e.g. kraken)" autocomplete="off">
      <input type="text"     id="f-key" placeholder="Key name (e.g. api_key)" autocomplete="off">
    </div>
    <div class="frow">
      <input type="password" id="f-val" placeholder="Value — will be Fernet-encrypted on save" autocomplete="new-password">
    </div>
    <div class="actions">
      <button class="btn save-btn"   onclick="saveKey()">Save Encrypted</button>
      <button class="btn cancel-btn" onclick="closeAdd()">Cancel</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let _keys=[],_shown={};
async function load(){
  const r=await fetch('/api/admin/api_keys');
  if(!r.ok){document.getElementById('tbl').innerHTML='<p class="empty">Error loading keys.</p>';return;}
  const d=await r.json();_keys=d.keys||[];render();
}
function render(){
  const w=document.getElementById('tbl');
  if(!_keys.length){w.innerHTML='<p class="empty">No keys in DB yet.</p>';return;}
  const rows=_keys.map((k,i)=>{
    const shown=_shown[i];
    const val=shown?`<span class="val">${esc(k.value)}</span>`:`<span class="val hidden">••••••••••••</span>`;
    return `<tr><td><span class="svc">${esc(k.service)}</span></td><td><span class="kn">${esc(k.key_name)}</span></td><td>${val}</td><td><span class="ts">${esc(k.updated_at)}</span></td><td><div class="actions"><button class="btn eye" onclick="toggleVal(${i})">${shown?'Hide':'Show'}</button><button class="btn edit" onclick="prefill('${esc(k.service)}','${esc(k.key_name)}')">Edit</button><button class="btn del" onclick="delKey('${esc(k.service)}','${esc(k.key_name)}')">Delete</button></div></td></tr>`;
  }).join('');
  w.innerHTML=`<table><thead><tr><th>Service</th><th>Key Name</th><th>Value</th><th>Updated</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function toggleVal(i){_shown[i]=!_shown[i];render();}
function toast(msg,err=false){const t=document.getElementById('toast');t.textContent=msg;t.className='toast'+(err?' err':'');requestAnimationFrame(()=>{t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2800);});}
function openAdd(){document.getElementById('add-form').classList.add('open');document.getElementById('f-svc').focus();}
function closeAdd(){document.getElementById('add-form').classList.remove('open');}
function prefill(svc,kn){document.getElementById('f-svc').value=svc;document.getElementById('f-key').value=kn;document.getElementById('f-val').value='';openAdd();document.getElementById('f-val').focus();}
async function saveKey(){
  const svc=document.getElementById('f-svc').value.trim().toLowerCase();
  const kn=document.getElementById('f-key').value.trim().toLowerCase();
  const val=document.getElementById('f-val').value;
  if(!svc||!kn||!val){toast('All three fields required.',true);return;}
  const r=await fetch('/api/admin/api_keys/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:svc,key_name:kn,value:val})});
  const d=await r.json();
  if(r.ok){closeAdd();document.getElementById('f-svc').value='';document.getElementById('f-key').value='';document.getElementById('f-val').value='';_shown={};toast('✓ '+svc+'/'+kn+' saved');load();}
  else toast(d.message||'Save failed.',true);
}
async function delKey(svc,kn){
  if(!confirm('Delete '+svc+'/'+kn+'?\\n\\nBot will fall back to .env on next restart.')) return;
  const r=await fetch('/api/admin/api_keys/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:svc,key_name:kn})});
  const d=await r.json();
  if(r.ok){_shown={};toast('✓ '+svc+'/'+kn+' deleted');load();}
  else toast(d.message||'Delete failed.',true);
}
load();
</script>
</body>
</html>"""
    return html.encode("utf-8")


def is_bot_running():
    """Best-effort check for bot process."""
    try:
        if sys.platform == "win32":
            pids = find_bot_pids_windows()
            return len(pids) > 0
        out = subprocess.check_output(["ps", "-ef"], text=True)
        return "bot_engine.py" in out
    except Exception:
        return False


def find_bot_pids_windows():
    """Find PIDs for processes whose command line contains bot_engine.py."""
    try:
        import psutil

        bot_name = BOT_SCRIPT.name.lower()
        current_pid = os.getpid()
        pids = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                pid = int(info.get("pid") or 0)
                if pid == current_pid:
                    continue
                name = (info.get("name") or "").lower()
                if name not in ("python.exe", "pythonw.exe", "python"):
                    continue
                cmdline = [str(part) for part in (info.get("cmdline") or [])]
                if any(Path(part).name.lower() == bot_name for part in cmdline):
                    pids.append(pid)
            except Exception:
                continue
        if pids:
            return pids
    except Exception:
        pass

    try:
        bot_path = str(BOT_SCRIPT.resolve()).replace("'", "''").lower()
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$target = '"
                + bot_path
                + "'; "
                + "$current = "
                + str(os.getpid())
                + "; "
                + "Get-CimInstance Win32_Process | "
                + "Where-Object { "
                + "$_.ProcessId -ne $current -and "
                + "$_.Name -match '^(python|pythonw)\\.exe$' -and "
                + "$_.CommandLine -and "
                + "$_.CommandLine.ToLower().Contains($target) "
                + "} | "
                + "Select-Object -ExpandProperty ProcessId"
            ),
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
        return [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]
    except Exception:
        return []


def start_bot_process():
    """Start bot_engine.py if not already running."""
    if is_bot_running():
        return False, "Bot is already running."
    try:
        python_exe = str(BOT_PYTHON if BOT_PYTHON.exists() else Path(sys.executable))
        if sys.platform == "win32":
            # Launch through cmd /k so the bot has a visible console with live output.
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NEW_CONSOLE = 0x00000010
            flags = CREATE_NEW_CONSOLE | CREATE_NEW_PROCESS_GROUP
            launcher = ROOT / "StartBotEngine.bat"
            ps_launcher = ROOT / "StartBotEngine.ps1"
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-File",
                    str(ps_launcher if ps_launcher.exists() else launcher),
                ],
                cwd=str(ROOT),
                creationflags=flags,
            )
        else:
            subprocess.Popen(
                [python_exe, str(BOT_SCRIPT)],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        return True, "Bot start requested."
    except Exception as exc:
        return False, f"Failed to start bot: {exc}"


def open_project_terminal():
    """Open an interactive local shell rooted in the trading bot workspace."""
    try:
        if sys.platform == "win32":
            CREATE_NEW_CONSOLE = 0x00000010
            root = str(ROOT.resolve()).replace("'", "''")
            command = (
                f"Set-Location -LiteralPath '{root}'; "
                "$Host.UI.RawUI.WindowTitle = 'Trading Bot Workspace Shell'; "
                "Write-Host 'Trading bot workspace shell ready.' -ForegroundColor Cyan; "
                "Write-Host 'Root: ' -NoNewline -ForegroundColor DarkGray; "
                "Write-Host (Get-Location).Path; "
                "Write-Host 'Try: Get-Content .\\logs\\bot.log -Tail 80 -Wait' -ForegroundColor DarkGray"
            )
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-Command",
                    command,
                ],
                cwd=str(ROOT),
                creationflags=CREATE_NEW_CONSOLE,
            )
            return True, "PowerShell opened in the trading bot workspace."

        return True, f"Server is {sys.platform}; use SSH from your PC for an interactive shell."
    except Exception as exc:
        return False, f"Failed to open terminal: {exc}"


def open_hostinger_terminal():
    """Open a Windows PowerShell SSH session to Hostinger when possible."""
    command = f"ssh {HOSTINGER_SSH_TARGET}"
    try:
        if sys.platform == "win32":
            CREATE_NEW_CONSOLE = 0x00000010
            ps_command = (
                "$Host.UI.RawUI.WindowTitle = 'Hostinger SSH'; "
                "Write-Host 'Opening Hostinger SSH...' -ForegroundColor Cyan; "
                f"{command}"
            )
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-Command",
                    ps_command,
                ],
                cwd=str(ROOT),
                creationflags=CREATE_NEW_CONSOLE,
            )
            return True, f"PowerShell SSH opened: {command}", command
        return True, f"Dashboard is running on {sys.platform}; copy this on your PC: {command}", command
    except Exception as exc:
        return False, f"Failed to open Hostinger SSH: {exc}", command

def _terminal_enabled() -> bool:
    return str(os.environ.get("WEB_TERMINAL_ENABLED", "true")).strip().lower() not in {
        "0", "false", "no", "off", "disabled"
    }


def _terminal_close_session(session: dict) -> None:
    if not session:
        return
    try:
        proc = session.get("proc")
        if proc and proc.poll() is None:
            proc.terminate()
    except Exception:
        pass
    try:
        os.close(int(session.get("fd")))
    except Exception:
        pass


def _terminal_prune_locked() -> None:
    now = time.time()
    stale_ids = []
    for session_id, session in list(_terminal_sessions.items()):
        proc = session.get("proc")
        idle = now - float(session.get("last_access", now))
        if idle > TERMINAL_IDLE_SECONDS or (proc and proc.poll() is not None):
            stale_ids.append(session_id)
    for session_id in stale_ids:
        session = _terminal_sessions.pop(session_id, None)
        _terminal_close_session(session)


def _terminal_get(session_id: str, username: str | None = None):
    with _terminal_lock:
        _terminal_prune_locked()
        session = _terminal_sessions.get(str(session_id or ""))
        if not session:
            return None
        if username is not None and session.get("owner") != username:
            return None
        return session


def _terminal_read(session: dict) -> str:
    if not session:
        return ""
    if sys.platform == "win32":
        return ""
    try:
        import errno
        import select
        output = []
        fd = int(session["fd"])
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(fd, 65536)
            except OSError as exc:
                if exc.errno in (errno.EIO, errno.EAGAIN):
                    break
                raise
            if not chunk:
                break
            output.append(chunk.decode("utf-8", errors="replace"))
        session["last_access"] = time.time()
        return "".join(output)
    except Exception as exc:
        return f"\r\n[terminal read error: {exc}]\r\n"


def _terminal_start(kind: str = "hostinger", username: str = ""):
    if not _terminal_enabled():
        return False, {"error": "Web terminal disabled by WEB_TERMINAL_ENABLED"}
    if sys.platform == "win32":
        return False, {
            "error": "Embedded PTY terminal is available on Linux/Hostinger only. Use Hostinger SSH button on Windows.",
            "command": f"ssh {HOSTINGER_SSH_TARGET}",
        }
    try:
        import fcntl
        import pty
        owner = str(username or "")
        with _terminal_lock:
            _terminal_prune_locked()
            existing = [sid for sid, s in _terminal_sessions.items() if s.get("owner") == owner]
            if existing:
                return False, {"error": "A web terminal is already open for this user. Stop it first."}
            if len(_terminal_sessions) >= 3:
                return False, {"error": "Too many web terminal sessions are already open."}

        master_fd, slave_fd = pty.openpty()
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        shell = os.environ.get("SHELL", "/bin/bash") or "/bin/bash"
        command = f"cd {str(ROOT)!r}; exec {shell} -l"
        def _setup_child_pty():
            # Make the child shell a session leader with the PTY slave as its
            # controlling terminal. Without this, Ctrl-C can echo as ^C but fail
            # to deliver SIGINT to the foreground process (tail -f, journalctl -f).
            os.setsid()
            try:
                import termios
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except Exception:
                pass

        proc = subprocess.Popen(
            ["/bin/bash", "-lc", command],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(ROOT),
            close_fds=True,
            env={**os.environ, "TERM": "xterm-256color"},
            preexec_fn=_setup_child_pty,
        )
        os.close(slave_fd)
        session_id = secrets.token_urlsafe(32)
        with _terminal_lock:
            _terminal_sessions[session_id] = {
                "id": session_id,
                "fd": master_fd,
                "proc": proc,
                "created": time.time(),
                "last_access": time.time(),
                "kind": str(kind or "hostinger")[:32],
                "owner": owner,
            }
            session = _terminal_sessions[session_id]
        return True, {"session_id": session_id, "message": "Web terminal started.", "output": _terminal_read(session)}
    except Exception as exc:
        return False, {"error": f"Failed to start terminal: {exc}"}


def _terminal_resize(session_id: str, cols: int, rows: int, username: str = ""):
    session = _terminal_get(session_id, username)
    if not session:
        return False, {"error": "Terminal session not found."}
    try:
        if sys.platform == "win32":
            return True, {"ok": True}
        import fcntl
        import struct
        import termios
        cols = max(20, min(240, int(cols or 80)))
        rows = max(5, min(80, int(rows or 24)))
        fcntl.ioctl(int(session["fd"]), termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        session["last_access"] = time.time()
        return True, {"ok": True, "cols": cols, "rows": rows}
    except Exception as exc:
        return False, {"error": f"Terminal resize failed: {exc}"}

def _terminal_input(session_id: str, data: str, username: str = ""):
    session = _terminal_get(session_id, username)
    if not session:
        return False, {"error": "Terminal session not found."}
    try:
        raw = str(data or "").encode("utf-8", errors="replace")
        if len(raw) > TERMINAL_MAX_INPUT_BYTES:
            return False, {"error": "Terminal input chunk too large."}
        os.write(int(session["fd"]), raw)
        session["last_access"] = time.time()
        return True, {"ok": True}
    except Exception as exc:
        return False, {"error": f"Terminal input failed: {exc}"}


def _terminal_poll(session_id: str, username: str = ""):
    session = _terminal_get(session_id, username)
    if not session:
        return False, {"error": "Terminal session not found.", "closed": True}
    proc = session["proc"]
    output = _terminal_read(session)
    closed = proc.poll() is not None
    if closed:
        with _terminal_lock:
            session = _terminal_sessions.pop(session_id, None)
        _terminal_close_session(session)
    return True, {"output": output, "closed": closed}


def _terminal_stop(session_id: str, username: str = ""):
    session = _terminal_get(session_id, username)
    if not session:
        return True, {"ok": True, "message": "Terminal already closed."}
    with _terminal_lock:
        session = _terminal_sessions.pop(session_id, None)
    _terminal_close_session(session)
    return True, {"ok": True, "message": "Terminal closed."}
def stop_bot_process():
    """Stop bot_engine.py process(es)."""
    try:
        if sys.platform == "win32":
            pids = find_bot_pids_windows()
            if not pids:
                return False, "No bot_engine.py process found."
            killed = 0
            for pid in pids:
                result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    killed += 1
            if killed > 0:
                return True, f"Bot stop requested for {killed} process(es)."
            return False, "Matched bot process IDs but taskkill failed."
        else:
            result = subprocess.run(["pkill", "-f", "bot_engine.py"], check=False)
            if result.returncode == 0:
                return True, "Bot stop requested."
            return False, "No bot_engine.py process found."
    except Exception as exc:
        return False, f"Failed to stop bot: {exc}"


def sort_open_positions(rows, sort_by=None, sort_dir="desc"):
    key_map = {
        "opened": "entry_time",
        "symbol": "symbol",
        "type": "asset_class",
        "dir": "direction",
        "entry": "entry_price",
        "current": "current_price",
        "sl": "stop_loss",
        "tp": "take_profit",
        "pnlD": "unrealized_pnl",
        "pnlP": "pnl_pct",
        "toSL": "distance_to_sl",
        "toTP": "distance_to_tp",
    }
    field = key_map.get(sort_by or "opened", "entry_time")
    reverse = str(sort_dir or "desc").lower() != "asc"

    def value(row):
        raw = row.get(field)
        if field in ("asset_class", "direction", "entry_time", "symbol"):
            return str(raw or "").lower()
        try:
            return float(raw or 0)
        except Exception:
            return 0.0

    return sorted(rows, key=value, reverse=reverse)


def get_open_positions(sort_by=None, sort_dir="desc", enrich=True):
    """Return open positions using DB adapter when available, else SQLite fallback."""
    if enrich and monitor is not None:
        try:
            rows = monitor.get_positions_summary() or []
            positions = [
                {
                    "id": t.get("id"),
                    "trade_id": t.get("trade_id"),
                    "symbol": t.get("symbol") or t.get("ticker") or "?",
                    "asset_class": t.get("asset_class") or "crypto",
                    "side": t.get("direction") or t.get("side") or "long",
                    "direction": t.get("direction") or t.get("side") or "long",
                    "qty": float(t.get("quantity") or t.get("shares") or 0),
                    "entry_price": float(t.get("entry_price") or 0),
                    "current_price": float(t.get("current_price") or t.get("entry_price") or 0),
                    "stop_loss": float(t.get("stop_loss") or t.get("entry_price") or 0),
                    "take_profit": float(t.get("take_profit") or t.get("entry_price") or 0),
                    "unrealized_pnl": float(t.get("unrealized_pnl") or 0),
                    "pnl_pct": float(t.get("pnl_pct") or 0),
                    "distance_to_sl": float(t.get("distance_to_sl") or 0),
                    "distance_to_tp": float(t.get("distance_to_tp") or 0),
                    "entry_time": t.get("entry_time") or "",
                    "age_hours": float(t.get("age_hours") or 0),
                    "is_stuck": bool(t.get("is_stuck")),
                    "close_attempts": int(t.get("close_attempts") or 0),
                    "tp_hit_count": int(t.get("tp_hit_count") or 0),
                    "strategy_name": str(t.get("strategy_name") or "—"),
                }
                for t in rows
            ]
            return sort_open_positions(positions, sort_by, sort_dir)
        except Exception:
            pass

    if db is not None:
        try:
            rows = db.get_open_trades() or []
            positions = []
            for t in rows:
                entry_price = float(t.get("entry_price") or 0)
                if enrich:
                    raw_price = get_current_price(
                        t.get("symbol") or t.get("ticker") or "?",
                        t.get("asset_class") or "crypto",
                    )
                    # Price sanity gate: reject prices that deviate >80% from entry.
                    # Bad price feeds (e.g. Kraken returning a stale $0.05 for a
                    # $55 token) produce phantom -$1900 P&L that flips wildly.
                    # Mirror the same gate used in position_monitor._process_position.
                    if raw_price and entry_price > 0:
                        _dev = abs(raw_price - entry_price) / entry_price
                        current_price = raw_price if _dev <= 0.80 else entry_price
                    else:
                        current_price = raw_price or entry_price
                else:
                    current_price = float(t.get("current_price") or entry_price or 0)
                qty = float(t.get("quantity") or t.get("shares") or 0)
                direction = (t.get("direction") or t.get("side") or "long").lower()
                pnl = (current_price - entry_price) * qty
                if direction == "short":
                    pnl = -pnl
                pnl_pct = 0.0
                if entry_price:
                    raw_pct = ((current_price - entry_price) / entry_price) * 100
                    pnl_pct = raw_pct if direction == "long" else -raw_pct
                stop_loss = float(t.get("stop_loss") or entry_price or 0)
                take_profit = float(t.get("take_profit") or entry_price or 0)
                distance_to_sl = abs((current_price - stop_loss) / current_price * 100) if current_price else 0
                distance_to_tp = abs((take_profit - current_price) / current_price * 100) if current_price else 0
                positions.append({
                    "id": t.get("id"),
                    "trade_id": t.get("trade_id"),
                    "symbol": t.get("symbol") or t.get("ticker") or "?",
                    "asset_class": t.get("asset_class") or "crypto",
                    "side": direction,
                    "direction": direction,
                    "qty": qty,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "unrealized_pnl": round(pnl, 4),
                    "pnl_pct": round(pnl_pct, 4),
                    "distance_to_sl": distance_to_sl,
                    "distance_to_tp": distance_to_tp,
                    "entry_time": t.get("entry_time") or "",
                    "strategy_name": str(t.get("strategy_name") or "—"),
                })
            return sort_open_positions(positions, sort_by, sort_dir)
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
 #       conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, symbol, side, COALESCE(shares, quantity, 0), entry_price, entry_time
            FROM trades
            WHERE status='open'
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
        conn.close()
        positions = [
            {
                "id": r[0],
                "symbol": r[1],
                "side": r[2] or "",
                "qty": float(r[3] or 0),
                "entry_price": float(r[4] or 0),
                "entry_time": r[5] or "",
            }
            for r in rows
        ]
        return sort_open_positions(positions, sort_by, sort_dir)
    except Exception:
        return []


def _find_open_trade(position_id):
    if db is not None:
        try:
            for trade in db.get_open_trades() or []:
                if (
                    str(trade.get("id")) == str(position_id)
                    or str(trade.get("trade_id")) == str(position_id)
                ):
                    return trade
        except Exception:
            pass
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM trades WHERE status='open' AND (id=? OR trade_id=?)",
            (position_id, str(position_id)),
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _trade_indicators(trade_record) -> dict:
    value = (
        trade_record.get("indicators")
        or trade_record.get("indicators_json")
        or {}
    )
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _paper_futures_identity(trade_record):
    """Return (strategy, root symbol) only for scanner-owned paper trades."""
    broker = str(trade_record.get("broker") or "").strip().lower()
    strategy = str(trade_record.get("strategy_name") or "").strip().lower()
    trade_id = str(trade_record.get("trade_id") or "")
    if strategy not in ("emt", "eat"):
        if trade_id.startswith("EMT-PAPER-"):
            strategy = "emt"
        elif trade_id.startswith("EAT-PAPER-"):
            strategy = "eat"
    expected_broker = f"paper_{strategy}" if strategy else ""
    if strategy not in ("emt", "eat") or broker != expected_broker:
        return None
    indicators = _trade_indicators(trade_record)
    symbol = str(
        indicators.get("root_symbol")
        or trade_record.get("symbol")
        or ""
    ).split()[0].upper()
    return (strategy, symbol) if symbol else None


def _reconcile_orphaned_paper_trade(trade_record, strategy, symbol):
    """Close a DB-only paper row after the scanner confirms it is not active."""
    trade_id = str(trade_record.get("trade_id") or "")
    if db is not None:
        current = db.get_trade(trade_id)
        if current and str(current.get("status")) == "closed":
            return True, (
                f"{strategy.upper()} {symbol} paper trade was already closed."
            )
    status = _scanner_strategy_status(symbol)
    if not status.get("ok"):
        return False, (
            f"Scanner could not confirm {strategy.upper()} {symbol} state; "
            "the database row was left open."
        )
    strategy_state = (
        ((status.get("strategies") or {}).get(strategy) or {}).get("state") or {}
    )
    active = strategy_state.get("active_trade") or {}
    if str(active.get("trade_id") or "") == trade_id:
        return False, (
            f"{strategy.upper()} {symbol} still reports trade {trade_id} active; "
            "the database row was left open."
        )
    current_price = float(
        strategy_state.get("last_live_price")
        or trade_record.get("entry_price")
        or 0
    )
    if current_price <= 0:
        return False, f"No valid price is available to reconcile {trade_id}."
    indicators = _trade_indicators(trade_record)
    entry_price = float(trade_record.get("entry_price") or 0)
    quantity = float(trade_record.get("quantity") or 0)
    point_value = float(indicators.get("point_value") or 1)
    direction = str(trade_record.get("direction") or "long").lower()
    points = (
        entry_price - current_price
        if direction == "short"
        else current_price - entry_price
    )
    # Database.close_trade adds any previously recorded partial P&L itself.
    # Passing it here too would double count partial exits.
    pnl = round(points * point_value * quantity, 2)
    position_value = float(trade_record.get("position_value") or 0)
    pnl_pct = round(pnl / position_value * 100, 4) if position_value else 0.0
    if db is None:
        return False, "Database adapter is unavailable; orphan was left open."
    db.close_trade(
        trade_id,
        current_price,
        "manual_orphan_reconcile",
        pnl,
        pnl_pct,
    )
    updated = db.get_trade(trade_id)
    if not updated or str(updated.get("status")) != "closed":
        return False, f"Database did not confirm closure of orphan {trade_id}."
    recorded_pnl = float(updated.get("pnl") or pnl)
    return True, (
        f"Reconciled orphaned {strategy.upper()} {symbol} paper trade "
        f"@ {current_price:.2f} (estimated P&L ${recorded_pnl:.2f})."
    )


def close_position(position_id):
    """Close a position through its actual owning engine/executor."""
    try:
        trade_record = _find_open_trade(position_id)
        if not trade_record:
            return False, f"Position id {position_id} not found or already closed."

        paper_identity = _paper_futures_identity(trade_record)
        if paper_identity:
            strategy, root_symbol = paper_identity
            result = _scanner_close_strategy_trade({
                "strategy": strategy,
                "symbol": root_symbol,
                "trade_id": trade_record.get("trade_id"),
            })
            if result.get("ok"):
                closed = result.get("trade") or {}
                still_open = _find_open_trade(trade_record.get("trade_id"))
                if still_open:
                    # The engine closed but its DB mirror did not. Complete the
                    # paper-only reconciliation while scanner state proves the
                    # trade is no longer active.
                    return _reconcile_orphaned_paper_trade(
                        still_open, strategy, root_symbol
                    )
                pnl = float(
                    closed.get("pnl", closed.get("realized_pnl", 0)) or 0
                )
                return True, (
                    f"Closed {strategy.upper()} {root_symbol} paper trade "
                    f"@ {float(closed.get('exit_price') or 0):.2f} "
                    f"(P&L ${pnl:.2f})."
                )
            if result.get("code") == "trade_not_active":
                return _reconcile_orphaned_paper_trade(
                    trade_record, strategy, root_symbol
                )
            return False, str(
                result.get("error")
                or f"{strategy.upper()} scanner rejected the manual close."
            )

        symbol = trade_record["symbol"]
        asset_class = trade_record.get("asset_class", "crypto")
        current_price = get_current_price(symbol, asset_class) or trade_record.get("entry_price")
        if not current_price:
            return False, f"Could not get current price for {symbol}."

        from core.trade_executor import executor

        entry_price = float(trade_record.get("entry_price") or 0)
        qty = float(trade_record.get("quantity") or 0)
        direction = str(trade_record.get("direction") or "long").lower()
        strategy_name = str(trade_record.get("strategy_name") or "original").lower()
        current_price = float(current_price)
        if direction == "short":
            estimated_pnl = (entry_price - current_price) * qty
        else:
            estimated_pnl = (current_price - entry_price) * qty
        exit_reason = (
            "operator_profit_harvest"
            if estimated_pnl > 0 and strategy_name not in ("original", "manual")
            else "manual_close"
        )

        success = executor.close_trade(trade_record, current_price, exit_reason)
        if not success:
            return False, f"Executor returned failure for {symbol}."
        return True, f"Closed {symbol} @ ${float(current_price):.4f}."
    except Exception as exc:
        return False, f"Close failed: {exc}"


def request_close_position(position_id):
    """Start a manual close in the background so the dashboard stays usable."""
    trade_record = _find_open_trade(position_id)
    if trade_record and _paper_futures_identity(trade_record):
        # Scanner paper closes are quick and return a confirmed result. Running
        # them synchronously prevents the UI from claiming success before the
        # engine and central DB have actually closed the trade.
        return close_position(position_id)

    key = str(position_id)
    with _close_lock:
        if key in _close_requests:
            return True, f"Close already in progress for position {position_id}."
        _close_requests[key] = datetime.now()

    def worker():
        try:
            ok, msg = close_position(position_id)
            status = "OK" if ok else "FAILED"
            print(f"[manual close {status}] position={position_id}: {msg}", flush=True)
        except Exception as exc:
            print(f"[manual close ERROR] position={position_id}: {exc}", flush=True)
        finally:
            with _close_lock:
                _close_requests.pop(key, None)

    thread = threading.Timer(0.25, worker)
    thread.name = f"manual-close-{key}"
    thread.daemon = True
    thread.start()
    return True, f"Close requested for position {position_id}; broker close is running in the background."


def get_current_price(symbol, asset_class):
    try:
        from scanners.market_scanner import scanner
        return scanner.get_current_price(symbol, asset_class)
    except Exception:
        try:
            from scanners.market_scanner import MarketScanner
            market_scanner = MarketScanner()
            return market_scanner.get_current_price(symbol, asset_class)
        except Exception:
            return None


def get_manual_trade_config():
    brokers = ["alpaca", "coinbase", "kraken", "paper"]
    if getattr(_config, "IBKR_ENABLED", False):
        brokers.insert(0, "ibkr")
    return {
        "brokers": brokers,
        "default_broker": brokers[0],
        "asset_classes": ["stock", "crypto"],
        "directions": ["long", "short"],
        "default_size": 2000.0,
        "default_stop_loss_pct": 1.5,
        "default_take_profit_pct": 3.0,
        "default_strategy": "manual",
    }


# Per-run cancel context (intelligence.backtester.BacktestRunContext) — backtester
# parity patch step 2 (reports/agent_pipeline/20260717-085541/final_unified_report.md
# §6 item 2). Previously a bare module-global threading.Event was cleared
# unconditionally at the start of every new run, so a second run starting while
# a first was in flight could silently erase the first run's cancel signal.
# _bt_lock makes the "is one already running?" check-and-set atomic (closes a
# TOCTOU race between concurrent /api/backtest requests), and _bt_current_run
# lets /api/backtest/cancel target the actual in-flight run's own context
# instead of a shared global.
_bt_lock = threading.Lock()
_bt_running = threading.Event()
_bt_current_run = None  # BacktestRunContext | None

# Canonical list — see core/strategy_registry.py. Was previously a
# hand-maintained list missing 12 strategies backtester.py could already
# run (sfr_structural_fakeout, bmr_357, vbm_strategy, tema_crossover,
# pll_cycle_martingale, pll_conservative_eth_1h, td_day_trader_v3,
# td_gridbot_adx15, td_rsi_dip_spike_v4c, td_v6_bnb_adx, td_btc_v11,
# td_f40d_adx) — report 20260717-085541 item 10.
BACKTEST_STRATEGIES = sorted(_STRATEGY_MODULES.keys())


def _parse_backtest_days(raw):
    text = str(raw or "90").strip().lower()
    if text in ("1y", "1yr", "1 year"):
        return 365
    if text in ("2y", "2yr", "2 years"):
        return 730
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    return max(1, int(digits[0])) if digits else 90


def _load_watchlist_file(path):
    try:
        p = ROOT / path
        if not p.exists():
            return []
        return [
            line.strip() for line in p.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    except Exception:
        return []


def _unique_symbols(symbols, crypto=False):
    seen = set()
    out = []
    for raw in symbols or []:
        symbol = str(raw or "").strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        if crypto and "/" not in symbol:
            symbol = f"{symbol}/USD"
        if not crypto and ("/" in symbol or "-" in symbol):
            continue
        if symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def get_strategy_optimizer_params(strategy_name: str) -> list:
    """
    Introspect a strategy's params dataclass and return a list of optimizer-ready
    param descriptors: {name, default, min, max, step, is_int}.

    Skips string/bool fields (not optimizable numerically).
    Generates sensible default ranges from the dataclass default values.
    """
    # Canonical registry — see core/strategy_registry.py. Was previously a
    # third, independently-typed, smaller copy (20 entries) missing 6
    # strategies present in the dashboard's own BACKTEST_STRATEGIES list
    # (report 20260717-085541 item 10). Non-optimizable strategies (no
    # dataclass `params`) already no-op safely below, so widening this map
    # to the full registry carries no behavior risk.
    STRATEGY_MAP = _STRATEGY_MODULES
    if strategy_name not in STRATEGY_MAP:
        return []
    try:
        import importlib, dataclasses, math
        module_path, class_name = STRATEGY_MAP[strategy_name]
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        obj = cls()
        params = getattr(obj, 'params', None)
        if params is None or not dataclasses.is_dataclass(params):
            return []

        result = []
        for f in dataclasses.fields(params):
            val = getattr(params, f.name)
            if isinstance(val, bool) or isinstance(val, str):
                continue  # not numerically optimizable
            is_int = isinstance(val, int)
            is_float = isinstance(val, float)
            if not (is_int or is_float):
                continue

            if is_int:
                # For period/length-type params, range around default
                if val <= 0:
                    continue
                step  = max(1, val // 10)
                lo    = max(1, val // 2)
                hi    = val * 3
            else:
                # Float — pick step as ~10% of value, round nicely
                if val <= 0:
                    lo, hi, step = 0.5, 5.0, 0.5
                else:
                    magnitude = 10 ** math.floor(math.log10(val))
                    step = round(magnitude * 0.5, 4)
                    lo   = round(max(0.1, val * 0.4), 4)
                    hi   = round(val * 2.5, 4)

            result.append({
                "name":    f.name,
                "default": val,
                "min":     lo,
                "max":     hi,
                "step":    step,
                "is_int":  is_int,
            })
        return result
    except Exception as e:
        logger.warning(f"get_strategy_optimizer_params({strategy_name}): {e}")
        return []


def get_backtest_config():
    try:
        import config as cfg
    except Exception:
        cfg = None

    stock_symbols = []
    crypto_symbols = []
    if cfg is not None:
        stock_symbols.extend(getattr(cfg, "STOCK_WATCHLIST", []) or [])
        crypto_symbols.extend(getattr(cfg, "CRYPTO_WATCHLIST", []) or [])

    stock_symbols.extend(_load_watchlist_file("watchlists/stocks.txt"))
    stock_symbols.extend(_load_watchlist_file("watchlist/scanned_stocks.txt"))
    crypto_symbols.extend(_load_watchlist_file("watchlists/crypto.txt"))
    crypto_symbols.extend(_load_watchlist_file("watchlist/scanned_crypto.txt"))

    stocks = _unique_symbols(stock_symbols, crypto=False)
    crypto = _unique_symbols(crypto_symbols, crypto=True)
    return {
        "asset_classes": ["Stocks", "Crypto"],
        "strategies": ["ALL strategies", *BACKTEST_STRATEGIES],
        "behavior_profiles": [
            {
                "value": "isolated_v1",
                "label": "Legacy baseline (isolated_v1)",
                "description": "Preserves trusted historical backtest behavior.",
            },
            {
                "value": "live_parity_v2",
                "label": "Live parity (live_parity_v2)",
                "description": "Applies the reviewed P1-A lifecycle corrections.",
            },
        ],
        "timeframes": ["5m", "1h", "1d"],
        "durations": ["30d", "60d", "90d (3mo)", "180d (6mo)", "365d (1y)", "730d (2y)"],
        "symbols": {
            "Stocks": ["ALL", *stocks],
            "Crypto": ["ALL", *crypto],
        },
        "counts": {"stocks": len(stocks), "crypto": len(crypto)},
    }


def _backtest_result_payload(result):
    trades = list(getattr(result, "trades", []) or [])
    wins = [t for t in trades if getattr(t, "pnl", 0) > 0]
    losses = [t for t in trades if getattr(t, "pnl", 0) <= 0]
    avg_win = sum(float(getattr(t, "pnl", 0) or 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(float(getattr(t, "pnl", 0) or 0) for t in losses) / len(losses) if losses else 0
    start_cap = float(getattr(result, "starting_capital", 0) or 0)
    end_cap = float(getattr(result, "ending_capital", start_cap) or start_cap)
    start_date = getattr(result, "start_date", "")
    end_date = getattr(result, "end_date", "")
    stop_mode = getattr(result, "stop_mode", "") or (getattr(trades[0], "stop_mode", "") if trades else "") or "standard"
    win_rate = float(getattr(result, "win_rate", 0) or 0)
    profit_factor = float(getattr(result, "profit_factor", 0) or 0)
    max_drawdown = float(getattr(result, "max_drawdown_pct", 0) or 0)
    verdict = "GO" if win_rate >= 50 and profit_factor >= 1.2 and max_drawdown > -25 else "TUNE"
    equity_curve = list(getattr(result, "equity_curve", []) or [])
    sample_step = max(1, len(equity_curve) // 500)
    sampled_equity = [
        {
            "t": str(getattr(ep, "timestamp", ""))[:16],
            "e": float(getattr(ep, "equity", 0) or 0),
            "d": float(getattr(ep, "drawdown", 0) or 0),
            "r": float(getattr(ep, "daily_ret", 0) or 0),
        }
        for ep in equity_curve[::sample_step]
    ]
    return {
        "symbol": getattr(result, "symbol", ""),
        "strategy": getattr(result, "strategy_name", ""),
        "timeframe": getattr(result, "timeframe", ""),
        "behavior_profile": getattr(result, "behavior_profile", "isolated_v1"),
        "stop_mode": stop_mode,
        "stop": "2-Bar" if str(stop_mode).lower() in ("two_bar", "trailing") else "Standard",
        "start_date": start_date,
        "end_date": end_date,
        "period": f"{str(start_date)[:10]} -> {str(end_date)[:10]}",
        "starting_capital": start_cap,
        "ending_capital": end_cap,
        "wins": len(wins),
        "losses": len(losses),
        "wl": f"{len(wins)}W/{len(losses)}L",
        "verdict": verdict,
        "totalTrades": int(getattr(result, "total_trades", 0) or 0),
        "winRate": win_rate,
        "pnlD": round(end_cap - start_cap, 2),
        "pnlP": float(getattr(result, "total_return_pct", 0) or 0),
        "sharpe": float(getattr(result, "sharpe_ratio", 0) or 0),
        "sortino": float(getattr(result, "sortino_ratio", 0) or 0),
        "maxDD": max_drawdown,
        "profitFactor": profit_factor,
        "avgWin": round(avg_win, 2),
        "avgLoss": round(avg_loss, 2),
        "equity_curve": sampled_equity,
    }


# ---------------------------------------------------------------------------
# Optimizer subprocess state
# ---------------------------------------------------------------------------
_optimizer_progress = {
    "running":    False,
    "iteration":  0,
    "total":      0,
    "best_score": None,
    "strategy":   "",
    "method":     "",
    "cancelled":  False,
    "results":    None,
    "error":      None,
}
_opt_cancel  = threading.Event()
_opt_running = threading.Event()
_opt_proc    = None          # current subprocess.Popen handle
_opt_prog_file = None        # path to progress JSON file

def _opt_monitor(proc, progress_path: str):
    """
    Background thread: polls progress_path every 0.5s and merges into
    _optimizer_progress, then cleans up when the subprocess exits.
    """
    global _opt_proc, _optimizer_progress
    import time as _t, json as _j

    while proc.poll() is None:
        _t.sleep(0.5)
        try:
            with open(progress_path) as _f:
                data = _j.load(_f)
            # Merge into shared dict (preserve keys the worker doesn't write)
            for k in ('running','iteration','total','best_score','cancelled','error','results'):
                if k in data:
                    _optimizer_progress[k] = data[k]
        except Exception:
            pass

    # Process exited — do one final read
    try:
        with open(progress_path) as _f:
            data = _j.load(_f)
        for k in ('running','iteration','total','best_score','cancelled','error','results'):
            if k in data:
                _optimizer_progress[k] = data[k]
        if data.get('results') is None and not data.get('error'):
            import logging as _lg
            _lg.getLogger("dashboard.opt_monitor").warning(
                f"Final progress has no results and no error — worker may have been killed. "
                f"phase={data.get('phase')} iter={data.get('iteration')}/{data.get('total')}"
            )
    except Exception as _fe:
        import logging as _lg
        _lg.getLogger("dashboard.opt_monitor").error(
            f"Final progress read FAILED ({_fe}) — results lost, zombie state likely"
        )

    _optimizer_progress["running"] = False
    _opt_running.clear()
    _opt_proc = None
    try:
        os.unlink(progress_path)
    except Exception:
        pass

def run_optimize_api(payload):
    """
    Launch the optimizer in a subprocess (opt_worker.py) so the heavy
    simulation loop runs in its own Python interpreter with its own GIL,
    keeping the web server fully responsive during optimization.
    """
    global _opt_proc, _opt_prog_file

    import tempfile, json as _j, subprocess as _sp

    strategy   = str(payload.get("strategy") or "").strip()
    if not strategy:
        _optimizer_progress.update({"error": "strategy is required", "results": [], "running": False})
        _opt_running.clear(); return

    asset       = str(payload.get("asset") or "Crypto").lower()
    asset_class = "crypto" if asset.startswith("crypto") else "stock"
    timeframe   = str(payload.get("timeframe") or payload.get("tf") or "1h").strip()
    days        = int(payload.get("days") or 365)
    metric      = str(payload.get("metric")     or "profit_factor").strip()
    minimize    = bool(payload.get("minimize",  False))
    method      = str(payload.get("method")     or "annealing").strip()
    iterations  = int(payload.get("iterations") or 40)

    # Resolve symbols
    raw_syms = payload.get("symbols")
    if not raw_syms or raw_syms == "ALL":
        cfg_syms = get_backtest_config()["symbols"]
        key = "Crypto" if asset_class == "crypto" else "Stocks"
        import config as _cfg_mod
        symbols = [s for s in cfg_syms.get(key, []) if s != "ALL"][:20]
    elif isinstance(raw_syms, list):
        symbols = [s.strip().upper() for s in raw_syms if s.strip()]
    else:
        symbols = [s.strip().upper() for s in str(raw_syms).split(",") if s.strip()]
    if not symbols:
        _optimizer_progress.update({"error": "No symbols resolved", "results": [], "running": False})
        _opt_running.clear(); return

    raw_params = payload.get("params") or []
    if not raw_params:
        _optimizer_progress.update({"error": "params list is required", "results": [], "running": False})
        _opt_running.clear(); return

    # Write config file for worker
    cfg_data = {
        "strategy":    strategy,
        "symbols":     symbols,
        "params":      raw_params,
        "method":      method,
        "iterations":  iterations,
        "days":        days,
        "timeframe":   timeframe,
        "asset_class": asset_class,
        "metric":      metric,
        "minimize":    minimize,
    }
    try:
        cfg_fd, cfg_path = tempfile.mkstemp(suffix='.json', prefix='opt_cfg_')
        with os.fdopen(cfg_fd, 'w') as f:
            _j.dump(cfg_data, f)

        _fd, prog_path = tempfile.mkstemp(suffix='.json', prefix='opt_prog_')
        os.close(_fd)
        _opt_prog_file = prog_path
        # Seed the progress file so the monitor has something to read immediately
        import json as _jj
        with open(prog_path, 'w') as _pf:
            _jj.dump({"running": False, "iteration": 0, "total": iterations,
                      "best_score": None, "cancelled": False, "error": None,
                      "results": None, "phase": "starting"}, _pf)
    except Exception as e:
        _optimizer_progress.update({"error": f"Temp file failed: {e}", "results": [], "running": False})
        _opt_running.clear(); return

    # Initial progress state
    _optimizer_progress.update({
        "running":    False,
        "iteration":  0,
        "total":      iterations,
        "best_score": None,
        "strategy":   strategy,
        "method":     method,
        "cancelled":  False,
        "error":      None,
        "results":    None,
    })

    # Find the python executable (same venv as web_dashboard)
    python_exe = sys.executable
    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'intelligence', 'opt_worker.py')

    try:
        proc = _sp.Popen(
            [python_exe, '-u', worker_script, cfg_path, prog_path],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=_sp.PIPE, stderr=_sp.STDOUT,
        )
        _opt_proc = proc
        _opt_running.set()   # mark optimizer as active — cleared by monitor when done
        # Relay subprocess output directly to terminal
        def _relay_output(p):
            for line in iter(p.stdout.readline, b''):
                text = line.decode('utf-8', errors='replace').rstrip()
                if text:
                    print(f'[worker] {text}', flush=True)
            p.stdout.close()
        threading.Thread(target=_relay_output, args=(proc,), daemon=True).start()
    except Exception as e:
        _optimizer_progress.update({"error": f"Subprocess launch failed: {e}", "results": [], "running": False})
        _opt_running.clear()
        try: os.unlink(cfg_path)
        except: pass
        return

    # Monitor thread — reads progress file and relays to _optimizer_progress
    mon = threading.Thread(target=_opt_monitor, args=(proc, prog_path), daemon=True)
    mon.start()

    # Clean up config file after worker exits (monitor thread handles this)
    def _del_cfg():
        proc.wait()   # block until subprocess exits
        import time as _t; _t.sleep(2)
        try: os.unlink(cfg_path)
        except: pass
    threading.Thread(target=_del_cfg, daemon=True).start()


def run_backtest_api(payload):
    try:
        from intelligence.backtester import Backtester, _resolve_behavior_profile
        import config as cfg
    except Exception as exc:
        return False, f"Backtester unavailable: {exc}", {}

    asset = str(payload.get("asset") or "Stocks")
    symbol = str(payload.get("symbol") or "ALL").strip()
    strategy = str(payload.get("strategy") or "ALL strategies").strip()
    timeframe = str(payload.get("tf") or payload.get("timeframe") or "1h").strip()
    days = _parse_backtest_days(payload.get("duration") or payload.get("days"))
    capital = float(payload.get("cap") or payload.get("capital") or getattr(cfg, "STARTING_CAPITAL", 100000))
    stop_mode = "two_bar" if str(payload.get("mode") or "").lower() in ("trailing", "two_bar") else "standard"
    lookback = max(1, int(float(payload.get("lookback") or 2)))
    entry_side_filter = str(payload.get("side")         or "all").strip().lower()
    entry_mode_filter = str(payload.get("entry_mode")   or "all").strip().lower()
    initial_stop_mode = str(payload.get("initial_stop") or "auto").strip().lower()
    trail_mode        = str(payload.get("trail")        or "auto").strip().lower()
    try:
        behavior_profile = _resolve_behavior_profile(
            str(payload.get("behavior_profile") or "isolated_v1")
        )
    except (TypeError, ValueError) as exc:
        return False, str(exc), {"cancelled": False}
    _commission_raw   = payload.get("commission")
    _slippage_raw     = payload.get("slippage")
    commission_pct    = float(_commission_raw) if _commission_raw not in (None, "", "default") else None
    slippage_pct      = float(_slippage_raw)   if _slippage_raw   not in (None, "", "default") else None

    asset_class = "crypto" if asset.lower().startswith("crypto") or "/" in symbol else "stock"
    if asset_class == "crypto":
        if symbol.upper() == "ALL":
            symbols = [s for s in get_backtest_config()["symbols"]["Crypto"] if s != "ALL"]
        else:
            symbols = _unique_symbols([symbol], crypto=True)
    else:
        if symbol.upper() == "ALL":
            symbols = [s for s in get_backtest_config()["symbols"]["Stocks"] if s != "ALL"]
        else:
            symbols = _unique_symbols([symbol.upper()], crypto=False)
    strategies = BACKTEST_STRATEGIES if strategy == "ALL strategies" else [strategy]

    if not symbols:
        return False, "No symbols selected for backtest.", {}

    global _bt_current_run
    from intelligence.backtester import BacktestRunContext

    with _bt_lock:
        if _bt_running.is_set():
            return False, "Backtest already running — cancel first", {}
        run_ctx = BacktestRunContext()
        _bt_current_run = run_ctx
        _bt_running.set()

    results = []
    skipped = 0
    failures = []
    was_cancelled = False
    try:
        bt = Backtester(starting_capital=capital)
        for strat in strategies:
            if run_ctx.is_cancelled():
                break
            for sym in symbols:
                if run_ctx.is_cancelled():
                    break
                try:
                    if strat == "original_scorer":
                        result = bt.run(
                            sym, days, capital, timeframe, asset_class=asset_class,
                            stop_mode=stop_mode, two_bar_lookback=lookback,
                            commission_pct=commission_pct, slippage_pct=slippage_pct,
                            initial_stop_mode=initial_stop_mode, trail_mode=trail_mode,
                            entry_mode_filter=entry_mode_filter,
                            entry_side_filter=entry_side_filter,
                            behavior_profile=behavior_profile,
                            run_ctx=run_ctx,
                        )
                    else:
                        result = bt.run_strategy(
                            sym, strat, days, capital, timeframe, asset_class=asset_class,
                            stop_mode=stop_mode, two_bar_lookback=lookback,
                            commission_pct=commission_pct, slippage_pct=slippage_pct,
                            initial_stop_mode=initial_stop_mode, trail_mode=trail_mode,
                            entry_mode_filter=entry_mode_filter,
                            entry_side_filter=entry_side_filter,
                            behavior_profile=behavior_profile,
                            run_ctx=run_ctx,
                        )
                    if result and getattr(result, "total_trades", 0) > 0:
                        results.append(_backtest_result_payload(result))
                    else:
                        skipped += 1
                        failures.append(
                            f"{strat}/{sym}: "
                            f"{getattr(bt, 'last_failure_reason', '') or 'no trades matched'}"
                        )
                except Exception as _exc:
                    if type(_exc).__name__ == "_BacktestCancelled":
                        # Inner-loop cancel checkpoint fired — treat as cancelled
                        run_ctx.cancel()
                        break
                    skipped += 1
                    failure = f"{strat}/{sym}: {type(_exc).__name__}: {_exc}"
                    failures.append(failure)
                    logger.exception("Backtest run failed: %s", failure)

        was_cancelled = run_ctx.is_cancelled()
    finally:
        _bt_running.clear()
        with _bt_lock:
            if _bt_current_run is run_ctx:
                _bt_current_run = None

    if not results:
        if was_cancelled:
            return True, f"Cancelled — no runs completed.", {
                "skipped": skipped,
                "requested_runs": len(symbols) * len(strategies),
                "cancelled": True,
            }
        first_failure = failures[0] if failures else "no diagnostic was recorded"
        return False, (
            f"No results; {skipped} run(s) were skipped. "
            f"First reason: {first_failure}"
        ), {
            "skipped": skipped,
            "requested_runs": len(symbols) * len(strategies),
            "cancelled": False,
            "failures": failures[:100],
        }

    total_trades = sum(r["totalTrades"] for r in results)
    total_wins = sum(round(r["totalTrades"] * r["winRate"] / 100) for r in results)
    summary = {
        "totalTrades": total_trades,
        "winRate": round((total_wins / total_trades * 100) if total_trades else 0, 1),
        "pnlD": round(sum(r["pnlD"] for r in results), 2),
        "pnlP": round(sum(r["pnlP"] for r in results) / len(results), 2),
        "sharpe": round(sum(r["sharpe"] for r in results) / len(results), 2),
        "maxDD": round(sum(r["maxDD"] for r in results) / len(results), 2),
        "profitFactor": round(sum(r["profitFactor"] for r in results) / len(results), 2),
        "avgWin": round(sum(r["avgWin"] for r in results) / len(results), 2),
        "avgLoss": round(sum(r["avgLoss"] for r in results) / len(results), 2),
    }
    complete_msg = (
        f"Cancelled — partial results: {len(results)} run(s) completed, {skipped} skipped."
        if was_cancelled
        else f"Backtest complete: {len(results)} result(s), {skipped} skipped."
    )
    return True, complete_msg, {
        **summary,
        "results": results,
        "skipped": skipped,
        "requested_runs": len(symbols) * len(strategies),
        "cancelled": was_cancelled,
        "failures": failures[:100],
    }


def get_manual_trade_preview(params):
    symbol = (params.get("symbol") or [""])[0].strip().upper()
    asset_class = (params.get("asset") or params.get("asset_class") or ["stock"])[0].lower()
    direction = (params.get("dir") or params.get("direction") or ["long"])[0].lower()
    if not symbol:
        return False, "Symbol is required.", {}
    try:
        position_size = float((params.get("size") or params.get("position_size") or ["0"])[0] or 0)
        sl_pct = float((params.get("sl") or params.get("stop_loss_pct") or ["1.5"])[0] or 1.5)
        tp_pct = float((params.get("tp") or params.get("take_profit_pct") or ["3.0"])[0] or 3.0)
    except Exception:
        return False, "Position size, stop loss, and take profit must be numeric.", {}
    if asset_class not in ("stock", "crypto"):
        return False, f"Unsupported asset class: {asset_class}", {}
    if direction not in ("long", "short"):
        return False, f"Unsupported direction: {direction}", {}
    if position_size <= 0:
        return False, "Position size must be greater than 0.", {}

    entry = get_current_price(symbol, asset_class)
    if not entry:
        return False, f"Could not fetch live price for {symbol}.", {}
    if direction == "long":
        sl = entry * (1 - sl_pct / 100)
        tp = entry * (1 + tp_pct / 100)
    else:
        sl = entry * (1 + sl_pct / 100)
        tp = entry * (1 - tp_pct / 100)
    return True, "Preview ready.", {
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": direction,
        "entry_price": float(entry),
        "stop_loss": float(sl),
        "take_profit": float(tp),
        "quantity": float(position_size / entry),
        "position_size": position_size,
    }


def get_candles(symbol, asset_class, timeframe="5 Min", limit=100):
    """Return OHLC candles for the HTML chart."""
    import traceback
    try:
        limit = max(10, min(int(limit), 300))
    except Exception:
        limit = 100

    if asset_class == "stock":
        tf_map = {"1 Min": "1Min", "5 Min": "5Min", "15 Min": "15Min", "1 H": "1Hour", "4 H": "1Hour", "1 D": "1Day"}
        try:
            import alpaca_trade_api as tradeapi
            import config

            api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
            raw = api.get_bars(symbol, tf_map.get(timeframe, "5Min"), limit=limit, adjustment="raw").df
            if raw.empty:
                print(f"[get_candles] Alpaca returned empty DataFrame for {symbol}")
                return []
            raw.index = raw.index.astype(str)
            return [
                {
                    "time": str(idx),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
                for idx, row in raw.iterrows()
            ]
        except Exception as e:
            print(f"[get_candles] Alpaca error for {symbol}: {e}\n{traceback.format_exc()}")
            return []

    # Kraken native symbols → CCXT-normalized symbols
    _kraken_sym_map = {
        "XBT/USD": "BTC/USD", "XBT/EUR": "BTC/EUR",
        "XDG/USD": "DOGE/USD", "XDG/EUR": "DOGE/EUR",
        "XRP/USD": "XRP/USD",  # usually fine
    }
    ccxt_symbol = _kraken_sym_map.get(symbol, symbol)

    tf_map = {"1 Min": "1m", "5 Min": "5m", "15 Min": "15m", "1 H": "1h", "4 H": "4h", "1 D": "1d"}
    try:
        import ccxt

        exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 10000})
        rows = exchange.fetch_ohlcv(ccxt_symbol, tf_map.get(timeframe, "5m"), limit=limit)
        return [
            {
                "time": int(ts),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
            for ts, o, h, l, c, _v in rows
        ]
    except Exception as e:
        print(f"[get_candles] CCXT/Kraken error for {symbol}: {e}\n{traceback.format_exc()}")
        return []


# ---------------------------------------------------------------------------
def _scanner_snapshot(timeout: float = 1.5) -> dict:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8765/snapshot", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"scanner snapshot unavailable: {type(exc).__name__}: {exc}"}


def _parse_chart_time(value) -> Optional[int]:
    try:
        if isinstance(value, (int, float)):
            return int(value)
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
        return int(stamp.timestamp())
    except Exception:
        return None


def _fresh_emt_tick_bars(
    snapshot: dict, symbol: str, min_bars: int = 20, max_age_seconds: int = 300
) -> list:
    """Return EMT tick bars only when the cache is usable as a live chart."""
    state = (snapshot.get("emt_strategies") or {}).get(symbol) or {}
    if not state.get("enabled"):
        return []
    overlay = (snapshot.get("emt_overlays") or {}).get(symbol) or {}
    bars = overlay.get("tick_bars_data") or []
    if len(bars) < min_bars:
        return []
    timestamps = [
        timestamp
        for timestamp in (_parse_chart_time(bar.get("time")) for bar in bars)
        if timestamp is not None
    ]
    if not timestamps or max(timestamps) < int(time.time()) - max_age_seconds:
        return []
    return bars


def _scanner_bars_for_chart(
    symbol: str, timeframe: str, limit: int, snapshot: Optional[dict] = None
) -> list:
    snap = snapshot or _scanner_snapshot()
    if not snap.get("ok"):
        return []
    symbol = symbol.upper()
    tick_bars = _fresh_emt_tick_bars(snap, symbol)
    raw = tick_bars
    if not raw:
        raw = ((snap.get("bars") or {}).get(symbol) or [])
    rows = []
    for bar in raw:
        ts = _parse_chart_time(bar.get("time"))
        if not ts:
            continue
        try:
            rows.append({
                "time": ts,
                "open": float(bar.get("open") or 0),
                "high": float(bar.get("high") or 0),
                "low": float(bar.get("low") or 0),
                "close": float(bar.get("close") or 0),
                "volume": float(bar.get("volume") or 0),
            })
        except Exception:
            continue
    rows = [
        bar for bar in rows
        if min(bar["open"], bar["high"], bar["low"], bar["close"]) > 0
    ]
    rows.sort(key=lambda bar: bar["time"])
    if tick_bars:
        return rows[-limit:]
    size = {
        "1m": 1, "2m": 2, "3m": 3, "5m": 5, "15m": 15,
        "30m": 30, "1h": 60,
    }.get(str(timeframe), 1)
    if size > 1:
        bucketed = {}
        for bar in rows:
            bucket = bar["time"] - (bar["time"] % (size * 60))
            item = bucketed.setdefault(bucket, {
                "time": bucket,
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": 0,
            })
            item["high"] = max(item["high"], bar["high"])
            item["low"] = min(item["low"], bar["low"])
            item["close"] = bar["close"]
            item["volume"] += bar.get("volume", 0) or 0
        rows = [bucketed[key] for key in sorted(bucketed)]
    return rows[-limit:]

def _scanner_strategy_status(symbol: str) -> dict:
    try:
        import urllib.parse
        import urllib.request
        query = urllib.parse.urlencode({"symbol": str(symbol).upper()})
        with urllib.request.urlopen(
            f"http://127.0.0.1:8765/strategy/status?{query}", timeout=8.0
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "symbol": str(symbol).upper(),
            "error": f"scanner strategy status unavailable: {type(exc).__name__}: {exc}",
        }


def _scanner_configure_strategy(payload: dict) -> dict:
    secret = os.getenv("NINJA_BRIDGE_SECRET", "").strip()
    if not secret:
        return {"ok": False, "error": "NINJA_BRIDGE_SECRET is not configured"}
    body = json.dumps({**dict(payload or {}), "secret": secret}).encode("utf-8")
    try:
        import urllib.error
        import urllib.request
        request = urllib.request.Request(
            "http://127.0.0.1:8765/strategy/config",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=8.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8"))
        except Exception:
            result = {"error": f"scanner rejected configuration (HTTP {exc.code})"}
        return {"ok": False, **result}
    except Exception as exc:
        return {
            "ok": False,
            "error": f"scanner configuration unavailable: {type(exc).__name__}: {exc}",
        }


def _scanner_close_strategy_trade(payload: dict) -> dict:
    secret = os.getenv("NINJA_BRIDGE_SECRET", "").strip()
    if not secret:
        return {
            "ok": False,
            "code": "scanner_unavailable",
            "error": "NINJA_BRIDGE_SECRET is not configured",
        }
    body = json.dumps({**dict(payload or {}), "secret": secret}).encode("utf-8")
    try:
        import urllib.error
        import urllib.request
        request = urllib.request.Request(
            "http://127.0.0.1:8765/strategy/close",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=8.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8"))
        except Exception:
            result = {
                "error": f"scanner rejected manual close (HTTP {exc.code})"
            }
        return {"ok": False, **result}
    except Exception as exc:
        return {
            "ok": False,
            "code": "scanner_unavailable",
            "error": (
                "scanner manual close unavailable: "
                f"{type(exc).__name__}: {exc}"
            ),
        }


def get_emt_status() -> dict:
    status = _scanner_strategy_status("ES")
    emt = (status.get("strategies") or {}).get("emt") or {}
    return {
        "ok": bool(status.get("ok")),
        "bridge": status.get("bridge") or {},
        "emt": emt.get("state") or {},
        "overlay": emt.get("overlay") or {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **({"error": status.get("error")} if status.get("error") else {}),
    }
# Chart panel data — OHLCV bars + bot trade markers
# ---------------------------------------------------------------------------

_CHART_TF_ALPACA = {
    '1m': '1Min', '2m': '2Min', '3m': '3Min', '5m': '5Min',
    '15m': '15Min', '30m': '30Min',
    '1h': '1Hour', '4h': '4Hour', '1D': '1Day', '1W': '1Week',
}
_CHART_TF_CCXT = {
    '1m': '1m', '2m': '2m', '3m': '3m', '5m': '5m',
    '15m': '15m', '30m': '30m',
    '1h': '1h', '4h': '4h', '1D': '1d', '1W': '1w',
}
# IBKR bar size strings for historical data requests
_CHART_TF_IBKR = {
    '1m': '1 min', '2m': '2 mins', '3m': '3 mins', '5m': '5 mins',
    '15m': '15 mins', '30m': '30 mins',
    '1h': '1 hour', '4h': '4 hours', '1D': '1 day', '1W': '1 week',
}


def _chart_bars_alpaca(symbol, timeframe, limit):
    try:
        import alpaca_trade_api as tradeapi
        if not _config:
            return []
        api = tradeapi.REST(_config.ALPACA_API_KEY, _config.ALPACA_SECRET_KEY, _config.ALPACA_BASE_URL)
        tf  = _CHART_TF_ALPACA.get(timeframe, '5Min')
        raw = api.get_bars(symbol, tf, limit=limit, adjustment='raw').df
        if raw.empty:
            return []
        # Flatten MultiIndex columns (newer alpaca-trade-api versions)
        if hasattr(raw.columns, 'levels'):
            raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        bars = []
        for ts, r in raw.iterrows():
            try:
                bars.append({
                    'time': int(ts.timestamp()),
                    'open': float(r['open']), 'high': float(r['high']),
                    'low':  float(r['low']),  'close': float(r['close']),
                    'volume': float(r.get('volume', 0)),
                })
            except Exception:
                continue
        return bars
    except Exception as e:
        import logging; logging.getLogger(__name__).warning(f"[chart/alpaca] {symbol}: {e}")
        return []


def _chart_bars_ibkr(symbol, timeframe, limit, sec_type='STK', exchange='SMART'):
    # Reuse the bot's live executor singleton — don't create a new connection
    # per chart request (wastes clientIds and triggers event-loop errors).
    try:
        from core.trade_executor import executor as _tex
        ibkr = getattr(_tex, '_ibkr', None)
        if ibkr and ibkr.is_available():
            return ibkr.get_historical_bars(symbol, timeframe, limit,
                                            sec_type=sec_type, exchange=exchange)
    except Exception:
        pass
    # Fallback: yfinance (no connection needed).
    # For futures, caller handles symbol→yf mapping; for stocks/crypto pass as-is.
    return _chart_bars_yfinance(symbol, timeframe, limit)


def _resample_bars(bars_1m, target_minutes):
    """
    Resample a list of 1-minute OHLCV bars into N-minute bars.
    Used for timeframes brokers don't natively support (e.g. Kraken 2m/3m).
    bars_1m must be sorted ascending by time.
    """
    if not bars_1m or target_minutes <= 1:
        return bars_1m
    out = []
    bucket = None
    for b in bars_1m:
        # Snap timestamp to the start of the N-minute bucket
        ts      = int(b['time'])
        bucket_ts = ts - (ts % (target_minutes * 60))
        if bucket is None or bucket['time'] != bucket_ts:
            if bucket:
                out.append(bucket)
            bucket = {
                'time':   bucket_ts,
                'open':   b['open'],
                'high':   b['high'],
                'low':    b['low'],
                'close':  b['close'],
                'volume': b.get('volume', 0),
            }
        else:
            bucket['high']   = max(bucket['high'],  b['high'])
            bucket['low']    = min(bucket['low'],   b['low'])
            bucket['close']  = b['close']
            bucket['volume'] = bucket['volume'] + b.get('volume', 0)
    if bucket:
        out.append(bucket)
    return out


def _chart_bars_kraken(symbol, timeframe, limit):
    try:
        import json as _json
        import logging
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        # Kraken natively supports: 1,5,15,30,60,240,1440,10080 minutes
        # For 2m/3m we fetch 1m and resample in-house
        _resample_to = None
        if timeframe in ('2m', '3m'):
            _resample_to = 2 if timeframe == '2m' else 3
            fetch_interval = 1
            fetch_limit = limit * _resample_to + 10   # extra for clean boundaries
        else:
            fetch_interval = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '4h': 240, '1D': 1440, '1W': 10080,
            }.get(timeframe, 5)
            fetch_limit = limit

        pair = symbol.replace('/', '').replace('-', '').upper()
        if pair.startswith('BTC'):
            pair = pair.replace('BTC', 'XBT', 1)

        url = 'https://api.kraken.com/0/public/OHLC?' + urlencode({
            'pair': pair,
            'interval': fetch_interval,
        })
        req = Request(url, headers={'User-Agent': 'trading-bot-dashboard/1.0'})
        with urlopen(req, timeout=6) as resp:
            payload = _json.loads(resp.read().decode('utf-8'))
        if payload.get('error'):
            logging.getLogger(__name__).warning(f"[chart/kraken] {symbol}: {payload['error']}")
            return []
        result = payload.get('result') or {}
        data_key = next((k for k in result.keys() if k != 'last'), None)
        rows = result.get(data_key) or []
        rows = rows[-fetch_limit:]
        bars = [
            {'time': int(r[0]), 'open': float(r[1]), 'high': float(r[2]),
             'low': float(r[3]), 'close': float(r[4]), 'volume': float(r[6])}
            for r in rows
        ]
        if _resample_to:
            bars = _resample_bars(bars, _resample_to)
        return bars[-limit:]
    except Exception as e:
        logging.getLogger(__name__).warning(f"[chart/kraken] {symbol}: {e}")
        return []


def _chart_bars_coinbase(symbol, timeframe, limit):
    try:
        import logging
        import ccxt
        exc  = ccxt.coinbase({'enableRateLimit': True, 'timeout': 5000})
        tf   = _CHART_TF_CCXT.get(timeframe, '5m')
        rows = exc.fetch_ohlcv(symbol, tf, limit=limit)
        return [
            {'time': int(ts // 1000), 'open': float(o), 'high': float(h),
             'low': float(l), 'close': float(c), 'volume': float(v)}
            for ts, o, h, l, c, v in rows
        ]
    except Exception as e:
        logging.getLogger(__name__).warning(f"[chart/coinbase] {symbol}: {e}")
        return []


_YF_INTERVAL_MAP = {
    '1m': '1m', '2m': '2m', '3m': '5m',   # yfinance has no 3m → use 5m
    '5m': '5m', '15m': '15m', '30m': '30m',
    '1h': '1h', '4h': '1h', '1D': '1d', '1W': '1wk',
    # Sub-minute (not yet exposed in UI — framework only)
    '30s': '1m', '15s': '1m', '1s': '1m',
}

def _chart_bars_tradovate(symbol: str, timeframe: str, limit: int):
    """
    Return bars from the Tradovate real-time WebSocket cache.
    Returns [] if the feed is not running or has no data yet.
    Converts timeframe string ('1m','3m','5m'…) → element_size int.
    """
    global _tradovate_feed
    if not _tradovate_available or _tradovate_feed is None:
        return []

    # If feed stopped due to inactivity (but not auth failure), restart it automatically
    if not _tradovate_feed._running and not _tradovate_feed._auth_failed:
        _tradovate_feed._last_client_activity = __import__('time').time()
        _tradovate_feed.start()

    # Map dashboard symbol (e.g. "MES") → subscription name (e.g. "MESM6_5")
    tf_map = {'1m': 1, '2m': 2, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
              '1h': 60, '4h': 240, '1D': 1440}
    element_size = tf_map.get(timeframe, 5)

    base_name = TRADOVATE_SYMBOL_MAP.get(symbol)
    if not base_name:
        return []

    sub_name = base_name if element_size == 5 else f"{base_name}_{element_size}"

    # Dynamically subscribe if this timeframe wasn't pre-registered.
    # Prefer a known numeric contract ID; fall back to REST lookup; last resort string name.
    # Tradovate's md/getChart WS accepts both numeric IDs and string contract names.
    # Locked so concurrent chart requests for the same new symbol/timeframe
    # can't both pass the check-then-act and double-subscribe over the WS.
    with _tradovate_feed_lock:
        if sub_name not in _tradovate_feed._subscriptions:
            sym_id = TRADOVATE_SYMBOL_IDS.get(base_name)
            if sym_id is None:
                # Try REST lookup first (may fail with 401 if token has limited ACL)
                looked_up = _tradovate_feed.lookup_symbol_id(base_name)
                if looked_up:
                    TRADOVATE_SYMBOL_IDS[base_name] = looked_up
                    sym_id = looked_up
                    import logging as _lg
                    _lg.getLogger(__name__).info(
                        "Tradovate: REST lookup %s → id=%d (cached)", base_name, looked_up)
                else:
                    # Fall back to string contract name — the live WS accepts both formats
                    sym_id = base_name
                    import logging as _lg
                    _lg.getLogger(__name__).info(
                        "Tradovate: using string name %s (REST lookup unavailable)", base_name)
            _tradovate_feed.subscribe(sub_name, symbol_id=sym_id,
                                      element_size=element_size)
            # Send the subscription immediately if already authenticated
            if _tradovate_feed._authenticated and _tradovate_feed._ws:
                try:
                    _tradovate_feed._send_one_subscription(
                        _tradovate_feed._ws, sub_name,
                        _tradovate_feed._subscriptions[sub_name]
                    )
                except Exception:
                    pass  # will be sent on next reconnect

    bars = _tradovate_feed.get_bars(sub_name)
    return bars[-limit:] if bars else []


def _chart_bars_yfinance(symbol, timeframe, limit):
    try:
        import yfinance as yf
        from datetime import timedelta
        # yfinance uses BTC-USD format for crypto
        yfSym = symbol.replace('/', '-')
        interval = _YF_INTERVAL_MAP.get(timeframe, '5m')
        # Approximate period needed
        mins_per_bar = {
            '1s':1/60,'15s':0.25,'30s':0.5,
            '1m':1,'2m':2,'3m':3,'5m':5,'15m':15,'30m':30,
            '1h':60,'4h':240,'1D':1440,'1W':10080,
        }.get(timeframe, 5)
        total_days = max(2, (mins_per_bar * limit) // 1440 + 1)
        period_str = f"{min(total_days, 729)}d" if interval not in ('1d','1wk') else f"{min(total_days*2, 1800)}d"
        raw = yf.download(
            yfSym,
            period=period_str,
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
            timeout=6,
        )
        if raw.empty:
            return []
        # yfinance 0.2.x returns MultiIndex columns for single symbols: ('Open','TSLA')
        # Flatten so row['Open'] works instead of requiring row[('Open','TSLA')]
        if hasattr(raw.columns, 'levels'):
            raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
        bars = []
        for ts, row in raw.iterrows():
            try:
                t = int(ts.timestamp())
                bars.append({'time': t, 'open': float(row['Open']), 'high': float(row['High']),
                             'low': float(row['Low']), 'close': float(row['Close']),
                             'volume': float(row.get('Volume', 0))})
            except Exception:
                continue
        return bars[-limit:]
    except Exception:
        return []


def _futures_front_month_ticker(root: str) -> str:
    """
    Build the yfinance-style specific front-month contract ticker for a futures root.
    e.g.  GC  → 'GCM26'  (Gold June 2026)
          MGC → 'MGCM26'
          ES  → 'ESM26'
          CL  → 'CLM26'

    Month codes: F=Jan G=Feb H=Mar J=Apr K=May M=Jun
                 N=Jul Q=Aug U=Sep V=Oct X=Nov Z=Dec

    Contract schedules (typical front-month delivery months per asset class):
      Equities / FX / MBT / MET: Mar H / Jun M / Sep U / Dec Z  (quarterly)
      Energy (CL QM MCL NG QG RB HO): every month
      Metals (GC MGC SI SIL PL): Feb G / Apr J / Jun M / Aug Q / Oct V / Dec Z
      Copper (HG MHG): every month
      Rates (ZT ZF ZN ZB UB TN): Mar H / Jun M / Sep U / Dec Z
      Agri grains (ZC ZW ZS ZM ZL): Mar H / May K / Jul N / Sep U / Dec Z
      Livestock (LE HE): Feb G / Apr J / Jun M / Aug Q / Oct V / Dec Z
    """
    from datetime import date as _date

    today = _date.today()
    y, m = today.year, today.month

    # Which delivery months are valid for this root?
    _monthly   = {'CL','MCL','QM','NG','MNG','QG','RB','HO','HG','MHG'}
    _quarterly = {'ES','MES','NQ','MNQ','YM','MYM','RTY','M2K','NKD', 'MNK',
                  '6A','M6A','6B','M6B','6C','6E','M6E','6J','6S','E7','6M','6N',
                  'ZT','ZF','ZN','ZB','UB','TN','MBT','MET'}
    _metals    = {'GC','MGC','SI','SIL','PL'}
    _livestock = {'LE','HE'}
    _grains    = {'ZC','ZW','ZS','ZM','ZL'}

    if root in _monthly:
        delivery_months = list(range(1, 13))
    elif root in _quarterly:
        delivery_months = [3, 6, 9, 12]
    elif root in _metals:
        delivery_months = [2, 4, 6, 8, 10, 12]
    elif root in _livestock:
        delivery_months = [2, 4, 6, 8, 10, 12]
    elif root in _grains:
        delivery_months = [3, 5, 7, 9, 12]
    else:
        delivery_months = [3, 6, 9, 12]   # default quarterly

    # Find the nearest upcoming delivery month (>= current month)
    # Give 15 days lead time — front month is usually the next out by then
    check_month = m + 1 if today.day >= 15 else m
    check_year  = y
    if check_month > 12:
        check_month = 1
        check_year += 1

    for _ in range(13):
        if check_month in delivery_months:
            break
        check_month += 1
        if check_month > 12:
            check_month = 1
            check_year += 1

    _code = {1:'F',2:'G',3:'H',4:'J',5:'K',6:'M',
             7:'N',8:'Q',9:'U',10:'V',11:'X',12:'Z'}
    month_code = _code.get(check_month, 'M')
    year_code  = str(check_year)[-2:]

    return f"{root}{month_code}{year_code}"   # e.g. 'MGCM26', 'ESU26'


def _pattern_coords(pattern_name, bars):
    """Return drawing segments for frontend canvas overlay."""
    n = len(bars)
    if n < 5:
        return []
    times  = [b['time']                                      for b in bars]
    opens  = [float(b.get('open',  b.get('close', 0)) or 0) for b in bars]
    closes = [float(b.get('close') or 0)                     for b in bars]
    highs  = [float(b.get('high',  b.get('close', 0)) or 0) for b in bars]
    lows   = [float(b.get('low',   b.get('close', 0)) or 0) for b in bars]

    def lr(vals):
        n2 = len(vals)
        if n2 < 2: return vals[0], vals[-1]
        xs = list(range(n2)); mx = sum(xs)/n2; my = sum(vals)/n2
        num = sum((xs[i]-mx)*(vals[i]-my) for i in range(n2))
        den = sum((xs[i]-mx)**2 for i in range(n2)) or 1
        s = num/den
        return my - s*mx, my - s*mx + s*(n2-1)

    def seg(t1,p1,t2,p2): return {'type':'line','p1':{'time':t1,'price':p1},'p2':{'time':t2,'price':p2}}
    def hl(price):        return {'type':'hline','p1':{'time':times[0],'price':price},'p2':{'time':times[-1],'price':price}}
    def vl(t, price):     return {'type':'vline','p1':{'time':t,'price':price}}
    def rc(t1,p1,t2,p2, **extra):
        d = {'type':'rect','p1':{'time':t1,'price':p1},'p2':{'time':t2,'price':p2}}
        d.update(extra)
        return d
    def pivot_highs_idx(vals, window=4):
        return [(i, vals[i]) for i in range(window, len(vals)-window)
                if vals[i] == max(vals[i-window:i+window+1])]
    def pivot_lows_idx(vals, window=4):
        return [(i, vals[i]) for i in range(window, len(vals)-window)
                if vals[i] == min(vals[i-window:i+window+1])]

    segs = []
    pn = pattern_name

    if pn in ('Ascending Triangle','Descending Triangle','Symmetrical Triangle',
              'Rising Wedge','Falling Wedge'):
        h0,h1 = lr(highs); l0,l1 = lr(lows)
        segs += [seg(times[0],h0,times[-1],h1), seg(times[0],l0,times[-1],l1)]

    elif pn in ('Bull Flag','Bear Flag','Bull Pennant','Bear Pennant'):
        pe = n // 3
        segs.append(seg(times[0],closes[0],times[pe],closes[pe]))
        fh = max(highs[pe:]); fl = min(lows[pe:])
        segs.append(rc(times[pe],fh,times[-1],fl))

    elif pn in ('Head & Shoulders','Inv Head & Shoulders'):
        segs.append(hl(sum(lows[-n//2:]) / max(len(lows[-n//2:]),1)))  # approx neckline
        segs.append(vl(times[n//4], highs[n//4]))
        segs.append(vl(times[n//2], (highs[n//2] if pn=='Head & Shoulders' else lows[n//2])))
        segs.append(vl(times[3*n//4], highs[3*n//4]))

    elif pn in ('Double Top','Double Bottom'):
        if pn == 'Double Top':
            pivots = pivot_highs_idx(closes, window=4)
            if len(pivots) >= 2:
                (i1, p1), (i2, p2) = pivots[-2], pivots[-1]
                resistance = (p1 + p2) / 2
                valley = min(closes[i1:i2+1]) if i1 < i2 else min(closes)
                segs += [hl(resistance),
                         hl(valley),
                         vl(times[i1], p1),
                         vl(times[i2], p2),
                         seg(times[i1], p1, times[i2], p2)]
        else:
            pivots = pivot_lows_idx(closes, window=4)
            if len(pivots) >= 2:
                (i1, p1), (i2, p2) = pivots[-2], pivots[-1]
                support = (p1 + p2) / 2
                peak = max(closes[i1:i2+1]) if i1 < i2 else max(closes)
                segs += [hl(support),
                         hl(peak),
                         vl(times[i1], p1),
                         vl(times[i2], p2),
                         seg(times[i1], p1, times[i2], p2)]

    elif pn == 'Cup & Handle':
        cup_end = int(n*0.75)
        segs += [seg(times[0],closes[0],times[n//2],min(closes[:cup_end])),
                 seg(times[n//2],min(closes[:cup_end]),times[cup_end],closes[cup_end]),
                 rc(times[cup_end],max(highs[cup_end:]),times[-1],min(lows[cup_end:]))]

    elif pn == 'Consolidation Breakout':
        # Consolidation zone = the quiet range just before the breakout bar
        # Box covers last 8–12 bars of tight range; line shows the break out of it
        cb = max(0, n - 13)   # left edge of consolidation window
        ce = max(cb + 3, n - 2)  # right edge / where breakout begins
        box_h = max(highs[cb:ce])
        box_l = min(lows[cb:ce])
        segs += [rc(times[cb], box_h, times[ce - 1], box_l),
                 seg(times[ce - 1], closes[ce - 1], times[-1], closes[-1])]

    elif pn == 'Parabolic Acceleration':
        pts = [0, n//3, 2*n//3, n-1]
        for i in range(len(pts)-1):
            segs.append(seg(times[pts[i]],closes[pts[i]],times[pts[i+1]],closes[pts[i+1]]))

    elif pn in ('Volume Climax',
                'Shooting Star','Hammer','Gravestone Doji','Dragonfly Doji','Doji',
                'Bearish Engulfing','Bullish Engulfing',
                'Evening Star','Morning Star',
                'Three Black Crows','Three White Soldiers',
                'Bearish Exhaustion','Bullish Exhaustion'):
        num_c = (3 if pn in ('Evening Star','Morning Star',
                              'Three Black Crows','Three White Soldiers',
                              'Bearish Exhaustion','Bullish Exhaustion')
                 else 2 if pn in ('Bearish Engulfing','Bullish Engulfing')
                 else 1)
        # Highlight box spanning all signal candles.  Single-candle signals are
        # intentionally anchored to one bar; the frontend expands the pixel box.
        if len(times) >= num_c:
            if pn in ('Bearish Engulfing','Bullish Engulfing'):
                body_tops = [max(opens[i], closes[i]) for i in range(n - num_c, n)]
                body_bots = [min(opens[i], closes[i]) for i in range(n - num_c, n)]
                box_h = max(body_tops)
                box_l = min(body_bots)
            else:
                box_h  = max(highs[-num_c:])
                box_l  = min(lows[-num_c:])
            t_left = times[-1] if num_c == 1 else times[-num_c]
            segs.append(rc(t_left, box_h, times[-1], box_l, single_candle=(num_c == 1)))
        # Vline on each candle as well
        for i in range(num_c, 0, -1):
            if len(times) >= i:
                segs.append(vl(times[-i], closes[-i]))

    return segs


def _calc_fib_levels(bars):
    """
    Anchor point A = highest dollar-volume candle (liquidity candle) high.
    Anchor point B = lowest low after A in the lookback window.
    Returns retracement + extension levels plus anchor metadata, or None if no valid setup.
    """
    if len(bars) < 5:
        return None
    lookback = min(100, len(bars))
    recent   = bars[-lookback:]

    times  = [b['time']                                      for b in recent]
    highs  = [float(b.get('high',  b.get('close', 0)) or 0) for b in recent]
    lows   = [float(b.get('low',   b.get('close', 0)) or 0) for b in recent]
    vols   = [float(b.get('volume', 0) or 0)                 for b in recent]

    # Liquidity candle: highest price × volume (dollar volume)
    dvols   = [highs[i] * vols[i] for i in range(len(recent))]
    liq_idx = max(range(len(recent)), key=lambda i: dvols[i]) if any(v > 0 for v in dvols) \
              else highs.index(max(highs))

    anchor_high      = highs[liq_idx]
    anchor_high_time = times[liq_idx]

    # Swing low: lowest low at-or-after the liquidity candle
    after_lows  = lows[liq_idx:]
    after_times = times[liq_idx:]
    if len(after_lows) < 1:
        return None
    min_pos      = after_lows.index(min(after_lows))
    anchor_low   = after_lows[min_pos]
    anchor_low_time = after_times[min_pos]

    if anchor_high <= anchor_low:
        # No downswing from liquidity high — can't draw retracements
        return None

    diff = anchor_high - anchor_low

    retracements = {
        '0.0':   round(anchor_high,         6),
        '23.6':  round(anchor_high - diff * 0.236, 6),
        '38.2':  round(anchor_high - diff * 0.382, 6),
        '50.0':  round(anchor_high - diff * 0.500, 6),
        '61.8':  round(anchor_high - diff * 0.618, 6),
        '78.6':  round(anchor_high - diff * 0.786, 6),
        '100.0': round(anchor_low,          6),
    }
    extensions = {
        '127.2': round(anchor_high + diff * 0.272, 6),
        '161.8': round(anchor_high + diff * 0.618, 6),
        '200.0': round(anchor_high + diff * 1.000, 6),
    }
    return {
        'anchor_high':      anchor_high,
        'anchor_high_time': anchor_high_time,
        'anchor_low':       anchor_low,
        'anchor_low_time':  anchor_low_time,
        'diff':             round(diff, 6),
        'retracements':     retracements,
        'extensions':       extensions,
    }


_CONTRACT_SUFFIX_RE = re.compile(r'^([A-Z]{1,3})[FGHJKMNQUVXZ]\d{1,2}$')


def _contract_root(sym):
    # Futures trades are stored under their full contract code (e.g. "ESU6"),
    # while the chart is keyed by root symbol ("ES"). Strip a trailing
    # month-code+year only when the whole string matches that pattern, so
    # stock tickers (e.g. "BAC") are never mistaken for a contract of "BA".
    m = _CONTRACT_SUFFIX_RE.match(sym)
    return m.group(1) if m else sym


def _trade_markers_for_symbol(symbol):
    markers = []
    try:
        if db:
            trades = db.get_all_closed_trades(limit=500)
            for t in trades:
                if _contract_root((t.get('symbol') or '').upper()) != symbol:
                    continue
                entry_time = t.get('entry_time')
                if entry_time:
                    try:
                        et = datetime.fromisoformat(entry_time)
                        markers.append({
                            'time': int(et.timestamp()), 'type': 'entry',
                            'direction': t.get('direction', 'long'),
                            'price': float(t.get('entry_price', 0)),
                            'pnl': 0,
                        })
                    except Exception:
                        pass
                exit_time = t.get('exit_time')
                exit_price = t.get('exit_price')
                if exit_time and exit_price:
                    try:
                        xt = datetime.fromisoformat(exit_time)
                        pnl = float(t.get('pnl', 0) or 0)
                        markers.append({
                            'time': int(xt.timestamp()), 'type': 'exit',
                            'direction': t.get('direction', 'long'),
                            'price': float(exit_price), 'pnl': pnl,
                        })
                    except Exception:
                        pass
    except Exception:
        pass
    markers.sort(key=lambda m: m['time'])
    return markers


def _chart_open_positions_for_symbol(symbol):
    result = []
    try:
        for trade in get_open_positions(enrich=False) or []:
            trade_symbol = str(trade.get("symbol") or "").upper()
            if _contract_root(trade_symbol) != symbol:
                continue
            entry_time = trade.get("entry_time")
            entry_ts = None
            if entry_time:
                try:
                    entry_ts = int(datetime.fromisoformat(entry_time).timestamp())
                except Exception:
                    entry_ts = None
            result.append({
                "trade_id": trade.get("trade_id") or trade.get("id"),
                "symbol": trade_symbol or symbol,
                "direction": trade.get("direction") or trade.get("side") or "long",
                "entry_time": entry_time,
                "entry_ts": entry_ts,
                "entry_price": float(trade.get("entry_price") or 0),
                "stop_loss": float(trade.get("stop_loss") or 0),
                "take_profit": float(trade.get("take_profit") or 0),
                "current_price": float(trade.get("current_price") or trade.get("entry_price") or 0),
                "strategy_name": trade.get("strategy_name") or "",
            })
    except Exception:
        return []
    return result

def get_chart_data(symbol, timeframe='5m', limit=300, broker=None):
    symbol = symbol.upper().strip()
    is_crypto = '/' in symbol
    is_futures = symbol in FUTURES_SYMBOLS
    try:
        limit = max(50, min(int(limit), 1000))
    except Exception:
        limit = 300

    # Futures: symbols the NinjaTrader scanner tracks (its "bars" cache has an
    # entry for them) are served exclusively from that cache — they must never
    # poll Tradovate, IBKR, or yfinance, regardless of the toolbar broker
    # choice or whether a strategy engine is actively enabled for them.
    # External futures fallbacks can silently return wrong-instrument data
    # (e.g. raw "ES"/"MET" collide with the Eversource/MetLife stock tickers
    # on yfinance), which blocked real futures data from ever showing.
    # Symbols the scanner doesn't track at all (CL, NG, ZC, etc.) have no
    # cache entry and fall through to the external chain below.
    if is_futures:
        strategy_snap = _scanner_snapshot()
        scanner_tracks_symbol = bool(
            strategy_snap.get("ok") and symbol in (strategy_snap.get("bars") or {})
        )
        if scanner_tracks_symbol:
            ninja_bars = _scanner_bars_for_chart(
                symbol, timeframe, limit, snapshot=strategy_snap
            )
            uses_ticks = bool(_fresh_emt_tick_bars(strategy_snap, symbol))
            return {
                "bars": ninja_bars,
                "markers": _trade_markers_for_symbol(symbol),
                "open_positions": _chart_open_positions_for_symbol(symbol),
                "symbol": symbol,
                "timeframe": timeframe,
                "source": "ninja_strategy_cache",
                "feed_label": "EMT 610-tick" if uses_ticks else "Ninja 1-minute",
            }
        # Non-scanner-tracked futures: Tradovate real-time feed (if token active) → IBKR → yfinance
        # Try Tradovate WebSocket cache first (real-time, ~0 delay).
        # Always attempted unless user explicitly chose ibkr or yfinance in the toolbar.
        force_yfinance  = broker == 'yfinance'
        force_ibkr      = broker == 'ibkr'
        force_tradovate = broker == 'tradovate'
        if not force_yfinance and not force_ibkr:
            tv_bars = _chart_bars_tradovate(symbol, timeframe, limit)
            if tv_bars:
                tv_bars.sort(key=lambda b: b['time'])
                return {'bars': tv_bars[-limit:], 'markers': _trade_markers_for_symbol(symbol), 'open_positions': _chart_open_positions_for_symbol(symbol),
                        'symbol': symbol, 'timeframe': timeframe, 'source': 'tradovate_rt'}

        # When Tradovate is explicitly selected, skip IBKR (avoids 30s timeout)
        if force_yfinance or force_tradovate:
            bars = []   # skip straight to yfinance below
        else:
            meta = FUTURES_META[symbol]
            exchange = meta[0]
            bars = _chart_bars_ibkr(symbol, timeframe, limit, sec_type='FUT', exchange=exchange)
        if not bars:
            # Build yfinance ticker candidates in priority order:
            #  1. Override mapping (e.g. MGC → GC=F, MES → ES=F)
            #  2. Specific front-month contract (e.g. MGCM26, GCM26)
            #     — yfinance supports named contracts even when =F doesn't exist
            #  3. Standard continuous-contract format (symbol + '=F')
            yf_candidates = []
            override = FUTURES_YF_OVERRIDES.get(symbol)
            if override:
                yf_candidates.append(override)

            # Tier 2: specific front-month contract name
            front = _futures_front_month_ticker(symbol)
            if front and front not in yf_candidates:
                yf_candidates.append(front)

            # Tier 3: generic continuous contract
            std_ticker = symbol + '=F'
            if std_ticker not in yf_candidates:
                yf_candidates.append(std_ticker)

            for yf_sym in yf_candidates:
                bars = _chart_bars_yfinance(yf_sym, timeframe, limit)
                if bars:
                    break

        # Sort, dedup, return early — skip stock/crypto broker logic below
        bars.sort(key=lambda b: b['time'])
        seen_t: set = set()
        deduped = []
        for b in bars:
            if b['time'] not in seen_t:
                seen_t.add(b['time'])
                deduped.append(b)
        return {'bars': deduped[-limit:], 'markers': _trade_markers_for_symbol(symbol), 'open_positions': _chart_open_positions_for_symbol(symbol),
                'symbol': symbol, 'timeframe': timeframe}

    # Default broker by asset type
    if not broker:
        broker = 'kraken' if is_crypto else 'alpaca'

    _fetchers = {
        'alpaca':   _chart_bars_alpaca,
        'ibkr':     _chart_bars_ibkr,
        'kraken':   _chart_bars_kraken,
        'coinbase': _chart_bars_coinbase,
        'yfinance': _chart_bars_yfinance,
    }
    fetch = _fetchers.get(broker, _chart_bars_alpaca if not is_crypto else _chart_bars_kraken)
    bars = fetch(symbol, timeframe, limit)

    # Fallback if chosen broker returns nothing
    if not bars:
        if is_crypto:
            fallback = _chart_bars_yfinance if fetch is not _chart_bars_yfinance else None
        else:
            # yfinance is the universal stock fallback — don't retry Alpaca on Alpaca failure
            fallback = _chart_bars_yfinance if fetch is not _chart_bars_yfinance else None
        if fallback:
            bars = fallback(symbol, timeframe, limit)

    # Sort ascending — required by Lightweight Charts
    bars.sort(key=lambda b: b['time'])

    # Deduplicate — Alpaca/yfinance can emit two bars at the same timestamp
    # (e.g. DST boundary, or bar-boundary off-by-one).  LightweightCharts v4
    # aborts setData on CandlestickSeries if any duplicate timestamp exists.
    seen_t: set = set()
    deduped = []
    for b in bars:
        if b['time'] not in seen_t:
            seen_t.add(b['time'])
            deduped.append(b)
    bars = deduped

    # Trade markers for this symbol
    markers = _trade_markers_for_symbol(symbol)

    open_positions = []
    try:
        if db:
            for t in db.get_open_trades() or []:
                if (t.get('symbol') or '').upper() != symbol:
                    continue
                entry_time = t.get('entry_time')
                entry_ts = None
                if entry_time:
                    try:
                        entry_ts = int(datetime.fromisoformat(entry_time).timestamp())
                    except Exception:
                        entry_ts = None
                direction = t.get('direction', 'long')
                entry_price = float(t.get('entry_price') or 0)
                stop_loss = float(t.get('stop_loss') or 0)
                take_profit = float(t.get('take_profit') or 0)
                current_price = get_current_price(
                    t.get('symbol') or symbol,
                    t.get('asset_class') or ('crypto' if '/' in symbol else 'stock')
                ) or entry_price
                open_positions.append({
                    'trade_id': t.get('trade_id') or t.get('id'),
                    'symbol': t.get('symbol') or symbol,
                    'direction': direction,
                    'entry_time': entry_time,
                    'entry_ts': entry_ts,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'current_price': float(current_price or 0),
                    'strategy_name': t.get('strategy_name') or '',
                })
    except Exception:
        pass

    return {
        'bars': bars,
        'markers': markers,
        'open_positions': open_positions,
        'symbol': symbol,
        'timeframe': timeframe,
    }


# ── Futures symbol registry ──────────────────────────────────────────────────
# Maps CME/NYMEX/CBOT/COMEX symbol → (exchange, description, category)
# Exchange strings match IBKR's ContFuture routing.
# yfinance continuous contract ticker = symbol + '=F'
FUTURES_META = {
    # CME Equity Indices
    'ES':  ('CME',   'E-mini S&P 500',           'Equity'),
    'MES': ('CME',   'Micro E-mini S&P 500',      'Equity'),
    'NQ':  ('CME',   'E-mini NASDAQ 100',         'Equity'),
    'MNQ': ('CME',   'Micro E-mini NASDAQ 100',   'Equity'),
    'RTY': ('CME',   'E-mini Russell 2000',       'Equity'),
    'M2K': ('CME',   'Micro E-mini Russell 2000', 'Equity'),
    'NKD': ('CME',   'Nikkei 225',                'Equity'),
    'MNK': ('CME',   'Micro Nikkei 225',          'Equity'),
    'MBT': ('CME',   'Micro E-mini Bitcoin',      'Equity'),
    'MET': ('CME',   'Micro E-mini Ether',        'Equity'),
    # CBOT Equity
    'YM':  ('CBOT',  'Mini-DOW',                  'Equity'),
    'MYM': ('CBOT',  'Micro Mini-DOW',            'Equity'),
    # NYMEX Energy
    'CL':  ('NYMEX', 'Crude Oil',                 'Energy'),
    'MCL': ('NYMEX', 'Micro Crude Oil',           'Energy'),
    'QM':  ('NYMEX', 'E-mini Crude Oil',          'Energy'),
    'NG':  ('NYMEX', 'Natural Gas',               'Energy'),
    'MNG': ('NYMEX', 'Micro Henry Hub Nat Gas',   'Energy'),
    'QG':  ('NYMEX', 'E-mini Natural Gas',        'Energy'),
    'RB':  ('NYMEX', 'RBOB Gasoline',             'Energy'),
    'HO':  ('NYMEX', 'Heating Oil',               'Energy'),
    # NYMEX Metals
    'PL':  ('NYMEX', 'Platinum',                  'Metals'),
    # COMEX Metals
    'GC':  ('COMEX', 'Gold',                      'Metals'),
    'MGC': ('COMEX', 'Micro Gold',                'Metals'),
    'SI':  ('COMEX', 'Silver',                    'Metals'),
    'SIL': ('COMEX', 'Micro Silver',              'Metals'),
    'HG':  ('COMEX', 'Copper',                    'Metals'),
    'MHG': ('COMEX', 'Micro Copper',              'Metals'),
    # CME FX
    '6A':  ('CME',   'Australian Dollar',         'FX'),
    'M6A': ('CME',   'Micro AUD/USD',             'FX'),
    '6B':  ('CME',   'British Pound',             'FX'),
    'M6B': ('CME',   'Micro GBP/USD',             'FX'),
    '6C':  ('CME',   'Canadian Dollar',           'FX'),
    '6E':  ('CME',   'Euro FX',                   'FX'),
    'M6E': ('CME',   'Micro EUR/USD',             'FX'),
    '6J':  ('CME',   'Japanese Yen',              'FX'),
    '6S':  ('CME',   'Swiss Franc',               'FX'),
    'E7':  ('CME',   'E-mini Euro FX',            'FX'),
    '6M':  ('CME',   'Mexican Peso',              'FX'),
    '6N':  ('CME',   'New Zealand Dollar',        'FX'),
    # CBOT Financial / Interest Rates
    'ZT':  ('CBOT',  '2-Year Note',               'Rates'),
    'ZF':  ('CBOT',  '5-Year Note',               'Rates'),
    'ZN':  ('CBOT',  '10-Year Note',              'Rates'),
    'ZB':  ('CBOT',  '30-Year Bond',              'Rates'),
    'UB':  ('CBOT',  'Ultra-Bond',                'Rates'),
    'TN':  ('CBOT',  'Ultra-Note',                'Rates'),
    # CBOT Agricultural
    'ZC':  ('CBOT',  'Corn',                      'Agriculture'),
    'ZW':  ('CBOT',  'Wheat',                     'Agriculture'),
    'ZS':  ('CBOT',  'Soybean',                   'Agriculture'),
    'ZM':  ('CBOT',  'Soybean Meal',              'Agriculture'),
    'ZL':  ('CBOT',  'Soybean Oil',               'Agriculture'),
    # CME Agricultural (Livestock)
    'HE':  ('CME',   'Lean Hogs',                 'Agriculture'),
    'LE':  ('CME',   'Live Cattle',               'Agriculture'),
}

FUTURES_SYMBOLS = set(FUTURES_META.keys())

# ── yfinance ticker map for futures ─────────────────────────────────────────
# Most contracts → symbol + '=F'  (ES=F, GC=F, NQ=F, CL=F …)
# Micro contracts often have no yfinance coverage → fall back to the
# parent (standard-size) contract so the chart still shows real price data.
#
# Format: symbol → yfinance_ticker_to_try_first
# If that returns empty, _chart_bars_futures_yfinance tries symbol+'=F' as a
# last resort before giving up.
FUTURES_YF_OVERRIDES = {
    # ── Equity Indices ──────────────────────────────────────────────────
    'MES': 'ES=F',   # Micro E-mini S&P 500  → use E-mini
    'MNQ': 'NQ=F',   # Micro E-mini NASDAQ   → use E-mini
    'M2K': 'RTY=F',  # Micro Russell 2000    → use E-mini
    'MYM': 'YM=F',   # Micro Mini-DOW        → use Mini-DOW
    'MNK': 'NKD=F',  # Micro Nikeii          → use Mini-Nikeii
    # ── Energy ──────────────────────────────────────────────────────────
    'MCL': 'CL=F',   # Micro Crude Oil       → use CL
    # ── Metals ──────────────────────────────────────────────────────────
    'MGC': 'GC=F',   # Micro Gold            → use Gold
    'SIL': 'SI=F',   # Micro Silver          → use Silver
    'MHG': 'HG=F',   # Micro Copper          → use Copper
    # ── FX ──────────────────────────────────────────────────────────────
    'M6A': '6A=F',   # Micro AUD/USD         → use 6A
    'M6B': '6B=F',   # Micro GBP/USD         → use 6B
    'M6E': '6E=F',   # Micro EUR/USD         → use 6E
    # ── Crypto Futures ──────────────────────────────────────────────────
    'MBT': 'BTC-USD', # Micro Bitcoin        → spot BTC as proxy
    'MET': 'ETH-USD', # Micro Ether          → spot ETH as proxy
}


def _strategy_supported_symbols():
    try:
        strategy_config = json.loads(
            (ROOT / "ninjatrader_bridge" / "ninja_futures_config.json")
            .read_text(encoding="utf-8")
        )
        return {
            str(symbol).upper()
            for symbol in (strategy_config.get("contracts") or {})
        }
    except Exception:
        return set()


def get_chart_symbols():
    stocks = list(getattr(_config, 'STOCK_WATCHLIST', []) or [])
    crypto = list(getattr(_config, 'CRYPTO_WATCHLIST', []) or [])
    try:
        inj = get_injected_symbols()
        stocks = list(dict.fromkeys(stocks + inj.get('stocks', [])))
        crypto = list(dict.fromkeys(crypto + inj.get('crypto', [])))
    except Exception:
        pass
    strategy_contracts = _strategy_supported_symbols()
    futures = [
        {
            'symbol': sym,
            'type': 'futures',
            'name': meta[1],
            'category': meta[2],
            'strategy_supported': sym in strategy_contracts,
        }
        for sym, meta in FUTURES_META.items()
    ]
    return (
        [{'symbol': s, 'type': 'stock'} for s in stocks] +
        [{'symbol': s, 'type': 'crypto'} for s in crypto] +
        futures
    )

WATCHLIST_DIR = ROOT / "watchlist"
INJECTED_STOCKS_FILE = WATCHLIST_DIR / "scanned_stocks.txt"
INJECTED_CRYPTO_FILE = WATCHLIST_DIR / "scanned_crypto.txt"


def _read_symbol_file(path):
    try:
        if not path.exists():
            return []
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except Exception:
        return []


def get_injected_symbols():
    return {
        "stocks": _read_symbol_file(INJECTED_STOCKS_FILE),
        "crypto": _read_symbol_file(INJECTED_CRYPTO_FILE),
        "files": {
            "stocks": str(INJECTED_STOCKS_FILE),
            "crypto": str(INJECTED_CRYPTO_FILE),
        },
    }


def inject_symbols(kind, raw_symbols, replace=False):
    if isinstance(raw_symbols, str):
        symbols = raw_symbols.replace(",", "\n").splitlines()
    else:
        symbols = raw_symbols or []

    cleaned = []
    for symbol in symbols:
        value = str(symbol or "").strip().upper()
        if not value:
            continue
        if kind == "crypto" and "/" not in value:
            value = f"{value}/USD"
        if value not in cleaned:
            cleaned.append(value)

    if kind not in ("stocks", "stock", "crypto"):
        return False, f"Unsupported injection kind: {kind}", get_injected_symbols()
    if not cleaned:
        return False, "No valid symbols entered.", get_injected_symbols()

    path = INJECTED_CRYPTO_FILE if kind == "crypto" else INJECTED_STOCKS_FILE
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    if replace:
        # Replace mode: file becomes exactly the submitted list — anything else is removed
        path.write_text("\n".join(cleaned))
        label = "crypto pair" if kind == "crypto" else "stock"
        return True, f"Replaced with {len(cleaned)} {label}(s): {', '.join(cleaned)}", get_injected_symbols()
    else:
        # Append mode: merge new symbols in front, keep existing ones not in the new list
        existing = [s for s in _read_symbol_file(path) if s not in cleaned]
        path.write_text("\n".join(cleaned + existing))
        label = "crypto pair" if kind == "crypto" else "stock"
        return True, f"Added {len(cleaned)} {label}(s): {', '.join(cleaned)}", get_injected_symbols()


def clear_injected_symbols():
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    INJECTED_STOCKS_FILE.write_text("")
    INJECTED_CRYPTO_FILE.write_text("")
    return {"stocks": [], "crypto": []}


def _format_trade_time(raw):
    if not raw:
        return "—", None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed.strftime("%m/%d %H:%M"), parsed
    except Exception:
        return str(raw)[:16], None


def _normalize_trade_datetimes(entry_dt, exit_dt):
    if not entry_dt or not exit_dt:
        return entry_dt, exit_dt
    if entry_dt <= exit_dt:
        return entry_dt, exit_dt

    hours_ahead = (entry_dt - exit_dt).total_seconds() / 3600
    if 0 < hours_ahead <= 8.5:
        adjusted = entry_dt - timedelta(hours=7)
        if adjusted <= exit_dt:
            return adjusted, exit_dt
    return entry_dt, exit_dt


def _format_duration(entry_dt, exit_dt):
    if not entry_dt or not exit_dt:
        return "—"
    if entry_dt > exit_dt:
        return "—"
    minutes = int((exit_dt - entry_dt).total_seconds() / 60)
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60}m"
    return f"{minutes}m"


def get_today_trade_log():
    try:
        trades = db.get_trades_for_date(date.today().isoformat()) if db is not None else []
    except Exception:
        trades = []

    if not trades:
        try:
            conn = sqlite3.connect(DB_PATH)
 #           conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            trades = [dict(r) for r in conn.execute(
                "SELECT * FROM trades WHERE status='closed' AND date(exit_time)=? ORDER BY exit_time",
                (date.today().isoformat(),),
            ).fetchall()]
            conn.close()
        except Exception:
            trades = []

    rows = []
    for trade in trades:
        if trade.get("status") != "closed":
            continue
        opened, entry_dt = _format_trade_time(trade.get("entry_time"))
        closed, exit_dt = _format_trade_time(trade.get("exit_time"))
        entry_dt, exit_dt = _normalize_trade_datetimes(entry_dt, exit_dt)
        if entry_dt:
            opened = entry_dt.strftime("%m/%d %H:%M")
        if exit_dt:
            closed = exit_dt.strftime("%m/%d %H:%M")
        pnl = float(trade.get("pnl") or 0)
        pnl_pct = float(trade.get("pnl_pct") or 0)
        rows.append({
            "id": trade.get("id"),
            "trade_id": trade.get("trade_id"),
            "opened": opened,
            "closed": closed,
            "duration": _format_duration(entry_dt, exit_dt),
            "symbol": trade.get("symbol") or "?",
            "direction": str(trade.get("direction") or "").upper(),
            "strategy": trade.get("strategy_name") or "original",
            "entry_price": float(trade.get("entry_price") or 0),
            "exit_price": float(trade.get("exit_price") or 0),
            "reason": str(trade.get("exit_reason") or "").replace("_", " ").title(),
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "result": "Win" if pnl > 0 else "Loss",
            "tp_hit_count": int(trade.get("tp_hit_count") or 0),
            "_sort": trade.get("exit_time") or "",
        })

    rows.sort(key=lambda row: row["_sort"], reverse=True)
    for row in rows:
        row.pop("_sort", None)
    return rows


def get_overview_data():
    if db is None:
        return {}

    try:
        status = risk_manager.get_daily_status() if risk_manager else None
    except Exception:
        status = None

    cap = db.get_latest_capital() or {}
    open_trades = db.get_open_trades() or []
    closed_today = get_today_trade_log()
    wins_today = sum(1 for trade in closed_today if float(trade.get("pnl") or 0) > 0)
    losses_today = sum(1 for trade in closed_today if float(trade.get("pnl") or 0) <= 0)
    closed_trade_count = len(closed_today)
    win_rate = (wins_today / closed_trade_count * 100) if closed_trade_count else 0
    closed_today_pnl = sum(float(trade.get("pnl") or 0) for trade in closed_today)

    daily_summaries = db.get_daily_summaries(370) or []
    # trades/wins/losses/win_rate/pnl/fees are recomputed live from `trades`
    # rather than trusting daily_summaries' stored columns: that row is a
    # snapshot frozen at whatever moment bot_engine's _end_of_day() last ran
    # for that date, so any later trade correction/removal or late-settling
    # close (crypto runs past stock-market EOD) leaves it stale — drifting
    # from a live "sum(pnl) WHERE date(exit_time)=..." query by a different
    # amount per day. start_capital/capital (ending) stay from the snapshot
    # since those are genuine point-in-time facts, not derivable from trades.
    daily_perf = []
    for s in daily_summaries:
        trade_date = s.get("trade_date")
        day_trades = [t for t in db.get_trades_for_date(trade_date) if t.get("status") == "closed"]
        wins   = [t for t in day_trades if (t.get("pnl", 0) or 0) > 0]
        losses = [t for t in day_trades if (t.get("pnl", 0) or 0) <= 0]
        gross  = sum((t.get("pnl", 0) or 0) for t in day_trades)
        fees   = sum((t.get("fees_paid", 0) or 0) for t in day_trades)
        start_capital = float(s.get("starting_capital") or 0)
        daily_perf.append({
            "date":            trade_date,
            "trades":          len(day_trades),
            "wins":            len(wins),
            "losses":          len(losses),
            "win_rate":        (len(wins) / len(day_trades) * 100) if day_trades else 0.0,
            "pnl":             gross,
            "fees_paid":       fees,
            "net_pnl":         gross - fees,
            "pnl_pct":         (gross / start_capital * 100) if start_capital else 0.0,
            "start_capital":   start_capital,
            "capital":         float(s.get("ending_capital") or 0),
            "goal_met":        bool(s.get("goal_met")),
            "trading_halted":  bool(s.get("trading_halted")),
        })

    capital_history = [
        {
            "date": row["date"],
            "capital": row["capital"],
        }
        for row in reversed([
            {"date": s.get("trade_date"), "capital": float(s.get("ending_capital") or 0)}
            for s in daily_summaries
            if s.get("trade_date")
        ])
    ]
    if cap:
        today = date.today().isoformat()
        current_capital = float(cap.get("total_capital") or 0)
        if not capital_history or capital_history[-1]["date"] != today:
            capital_history.append({"date": today, "capital": current_capital})

    if status:
        trading_active = bool(status.trading_active)
        halt_reason = status.halt_reason or ""
        session_daily_pnl = float(status.pnl_today or 0)
        consecutive_losses = int(status.consecutive_losses or 0)
        status_trades_today = int(status.trades_today or 0)
        capital = float(status.capital or cap.get("total_capital") or 0)
        starting_capital_today = float(status.starting_capital_today or 0)
    else:
        session = db.get_session(date.today().isoformat()) or {}
        trading_active = not bool(session.get("trading_halted", 0))
        halt_reason = session.get("halt_reason") or ""
        session_daily_pnl = float(session.get("pnl_today") or 0)
        starting_capital_today = float(session.get("starting_capital_today") or 0)
        consecutive_losses = int(session.get("consecutive_losses") or 0)
        status_trades_today = int(session.get("trades_today") or 0)
        capital = float(cap.get("total_capital") or 0)

    daily_pnl = closed_today_pnl
    daily_pnl_pct = (daily_pnl / starting_capital_today * 100) if starting_capital_today else 0

    return {
        "trading_active": trading_active,
        "halt_reason": halt_reason,
        "bot_process_running": is_bot_running(),
        "capital": capital,
        "available_cash": float(cap.get("available_cash") or 0),
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "session_daily_pnl": session_daily_pnl,
        "open_positions": len(open_trades),
        "trades_today": closed_trade_count,        # matches Trade Log count
        "session_trades_today": status_trades_today, # session counter (since last bot start)
        "closed_trades_today": closed_trade_count,
        "wins_today": wins_today,
        "losses_today": losses_today,
        "win_rate_today": win_rate,
        "consecutive_losses": consecutive_losses,
        "capital_history": capital_history,
        "daily_performance": daily_perf,
    }


def get_quick_status(year=None):
    year = int(year or date.today().year)
    status = {}

    try:
        from intelligence.ml_scorer import ml_scorer
        status["ml"] = ml_scorer.get_status()
    except Exception:
        status["ml"] = {"stage": "unknown", "progress_pct": 0, "message": "ML scorer initializing."}

    try:
        status["tax"] = db.get_tax_year_summary(year) if db is not None else {}
    except Exception:
        status["tax"] = {}

    try:
        status["expenses"] = db.get_expense_summary(year) if db is not None else {}
    except Exception:
        status["expenses"] = {}

    try:
        from intelligence.condition_detector import condition_detector
        from scanners.market_scanner import scanner
        cond = condition_detector.get_spy_condition(scanner.stock_scanner)
        status["market_condition"] = {
            "condition": getattr(cond.condition, "value", str(cond.condition)),
            "confidence": float(cond.confidence or 0),
            "position_scalar": float(cond.position_scalar or 0),
            "should_trade": bool(cond.should_trade),
            "reason": cond.reason,
            "adx": float(cond.adx or 0),
            "atr_pct": float(cond.atr_pct or 0),
            "bb_width": float(cond.bb_width or 0),
        }
    except Exception:
        status["market_condition"] = {
            "condition": "unknown",
            "confidence": 0,
            "position_scalar": 0,
            "should_trade": True,
            "reason": "Condition detector initializing.",
            "adx": 0,
            "atr_pct": 0,
            "bb_width": 0,
        }

    status["year"] = year
    return status


def generate_daily_report():
    try:
        from reporting.report_generator import ReportGenerator

        generator = ReportGenerator()
        summary = generator.generate_daily_summary()
        if db is not None:
            db.save_daily_summary(summary)
        return True, "Daily report generated and saved.", {"summary": summary}
    except Exception as exc:
        return False, f"Report generation failed: {exc}", {}


def export_tax_csv(year):
    try:
        year = int(year or date.today().year)
        exports = ROOT / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        filepath = exports / f"tax_form_8949_{year}.csv"
        db.export_8949_csv(year, str(filepath))
        return True, f"Saved: {filepath}", {"path": str(filepath)}
    except Exception as exc:
        return False, f"Tax export failed: {exc}", {}


def process_withdrawal(amount, reason):
    try:
        result = risk_manager.process_withdrawal(float(amount or 0), str(reason or "Living expenses"))
        return bool(result.get("approved")), result.get("message", "Withdrawal processed."), result
    except Exception as exc:
        return False, f"Withdrawal failed: {exc}", {}


def record_expense(expense_date, category, amount, description, vendor, recurring):
    try:
        amount = float(amount or 0)
        if amount <= 0:
            return False, "Amount must be greater than 0.", {}
        if not description:
            return False, "Description is required.", {}
        category = str(category or "OTHER").upper()
        if category not in db.EXPENSE_CATEGORIES:
            category = "OTHER"
        expense_date = str(expense_date or date.today().isoformat())
        expense_id = db.record_expense(
            expense_date, category, amount, str(description),
            vendor=str(vendor) if vendor else None,
            recurring=bool(recurring),
        )
        return True, f"Expense recorded: ${amount:.2f} ({category}).", {"id": expense_id}
    except Exception as exc:
        return False, f"Expense recording failed: {exc}", {}


def retrain_ml():
    try:
        from intelligence.ml_scorer import ml_scorer

        success = bool(ml_scorer.retrain())
        msg = "Retrain complete." if success else "Retrain skipped: not enough closed trades yet."
        return True, msg, {"ml": ml_scorer.get_status()}
    except Exception as exc:
        return False, f"ML retrain failed: {exc}", {}


def chat_with_bot(message):
    text = str(message or "").strip()
    if not text:
        return False, "Message is required.", {}
    try:
        from intelligence.chat_interface import chat

        reply = chat.chat(text)
        return True, reply, {"reply": reply}
    except Exception as exc:
        return False, f"Chat failed: {exc}", {}


# Module-level Chronos pipeline cache — load once, reuse across all calls.
# Lock prevents double-load race condition under ThreadingHTTPServer.
# None = not yet loaded; pipeline object = ready.
import threading as _threading
_CHRONOS_PIPELINE  = None
_CHRONOS_LOAD_DONE = False   # True only once the load attempt has fully finished
_CHRONOS_LOCK      = _threading.Lock()


def _load_chronos_pipeline():
    """
    Load amazon/chronos-t5-base once and cache it.
    Returns the pipeline object or None if unavailable.

    Fixes vs. original:
      - device_map="cpu" removed — caused meta-tensor crash on some torch/accelerate
        combinations (Cannot copy out of meta tensor). CPU is the default anyway.
      - torch_dtype → dtype (torch_dtype deprecated in newer transformers).
      - Suppress the spurious lm_head.weight warning (known Chronos checkpoint quirk).
    """
    global _CHRONOS_PIPELINE, _CHRONOS_LOAD_DONE
    # Fast path — no lock needed once the load has actually finished
    if _CHRONOS_LOAD_DONE:
        return _CHRONOS_PIPELINE

    # Slow path — hold the lock for the whole load so concurrent callers block
    # here and get the real pipeline instead of racing ahead on a stale None.
    with _CHRONOS_LOCK:
        if _CHRONOS_LOAD_DONE:               # re-check inside lock
            return _CHRONOS_PIPELINE

        _log = logging.getLogger("dashboard.chronos")
        try:
            import warnings
            import torch
            from chronos import ChronosPipeline

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*torch_dtype.*deprecated.*")
                warnings.filterwarnings("ignore", message=".*lm_head.weight.*")
                warnings.filterwarnings("ignore", message=".*newly initialized.*")
                _CHRONOS_PIPELINE = ChronosPipeline.from_pretrained(
                    "amazon/chronos-t5-base",
                    dtype=torch.float32,   # removed device_map — CPU is default, avoids meta-tensor crash
                )
            _log.info("[Chronos] model loaded successfully (amazon/chronos-t5-base)")
        except Exception as e:
            _log.warning(f"[Chronos] model load failed, will use heuristic fallback: {e}")
            _CHRONOS_PIPELINE = None
        finally:
            _CHRONOS_LOAD_DONE = True

    return _CHRONOS_PIPELINE


def _chronos_predict(payload):
    """
    POST /api/chronos_predict
    Receives: { symbol, timeframe, bars: [{time,open,high,low,close}, ...] }
    Returns:  { direction: 'up'|'down'|'flat', confidence: float, model: str }

    Uses amazon/chronos-t5-base (cached after first load).
    Falls back to a heuristic if the model isn't available.
    """
    import numpy as np
    _log = logging.getLogger("dashboard.chronos")

    bars    = payload.get("bars") or []
    symbol  = payload.get("symbol", "?")
    tf      = payload.get("timeframe", "?")

    if len(bars) < 8:
        return {"direction": "flat", "confidence": 0.5, "model": "insufficient_data"}

    closes = np.array([float(b.get("close", 0)) for b in bars], dtype=np.float32)

    # ── Try Chronos T5 (cached pipeline) ────────────────────────────────────
    try:
        import torch
        pipeline = _load_chronos_pipeline()
        if pipeline is not None:
            context    = torch.tensor(closes[-64:]).unsqueeze(0)   # (1, seq)
            # Forecast 1 step, 20 samples → get a distribution
            forecast   = pipeline.predict(context, prediction_length=1, num_samples=20)
            # forecast shape: (1, 20, 1)
            samples    = forecast[0, :, 0].cpu().numpy()           # (20,)
            last_close = float(closes[-1])
            up_pct     = float(np.mean(samples > last_close))
            down_pct   = float(np.mean(samples < last_close))
            flat_pct   = 1.0 - up_pct - down_pct

            if up_pct >= down_pct and up_pct >= flat_pct:
                direction, confidence = "up",   up_pct
            elif down_pct >= up_pct and down_pct >= flat_pct:
                direction, confidence = "down", down_pct
            else:
                direction, confidence = "flat", flat_pct

            _log.info(f"[Chronos] {symbol}/{tf}: {direction} {confidence:.2%}")
            return {"direction": direction, "confidence": round(confidence, 3), "model": "chronos-t5-base"}

    except Exception as e:
        _log.warning(f"[Chronos] prediction error: {e}")

    # ── Heuristic fallback: momentum + mean-reversion composite ────────────
    try:
        # Simple: compare last 3 closes vs 10-bar EMA; RSI(7) direction
        n       = len(closes)
        w       = np.exp(np.linspace(-1, 0, min(10, n)))
        w      /= w.sum()
        ema10   = float(np.dot(w, closes[-len(w):]))
        recent  = float(np.mean(closes[-3:]))
        mom     = recent - ema10

        # RSI(7) last value
        delta   = np.diff(closes[-8:]) if n >= 8 else np.array([0.0])
        gain    = np.mean(np.where(delta > 0, delta, 0))
        loss    = np.mean(np.where(delta < 0, -delta, 0))
        rsi     = 50.0 if loss == 0 else 100.0 - 100.0 / (1 + gain / loss)

        score = 0.0
        if mom > 0: score += 0.4
        else:       score -= 0.4
        if rsi < 40: score += 0.3   # oversold → up
        if rsi > 60: score -= 0.3   # overbought → down

        if score > 0.1:   direction, confidence = "up",   min(0.55 + abs(score)*0.3, 0.75)
        elif score < -0.1: direction, confidence = "down", min(0.55 + abs(score)*0.3, 0.75)
        else:              direction, confidence = "flat", 0.50

        return {"direction": direction, "confidence": round(confidence, 3), "model": "heuristic"}
    except Exception as e2:
        _log.error(f"[Chronos] heuristic also failed: {e2}")
        return {"direction": "flat", "confidence": 0.5, "model": "error"}


def open_manual_trade(payload):
    """Open a manual trade and register it in the DB for bot management."""
    try:
        import uuid
        from datetime import datetime as dt

        symbol = str(payload.get("symbol") or "").strip().upper()
        if not symbol:
            return False, "Symbol is required.", {}

        asset_class = str(payload.get("asset") or payload.get("asset_class") or "stock").lower()
        direction = str(payload.get("dir") or payload.get("direction") or "long").lower()
        broker = str(payload.get("broker") or "ibkr").lower()
        strategy_label = str(payload.get("label") or payload.get("strategy") or "manual")
        position_size = float(payload.get("size") or payload.get("position_size") or 0)
        sl_pct = float(payload.get("sl") or payload.get("stop_loss_pct") or 1.5)
        tp_pct = float(payload.get("tp") or payload.get("take_profit_pct") or 3.0)
        overnight = bool(payload.get("overnight"))

        if asset_class not in ("stock", "crypto"):
            return False, f"Unsupported asset class: {asset_class}", {}
        if direction not in ("long", "short"):
            return False, f"Unsupported direction: {direction}", {}
        if position_size <= 0:
            return False, "Position size must be greater than 0.", {}

        entry = get_current_price(symbol, asset_class)
        if not entry:
            return False, f"Could not get live price for {symbol}.", {}

        qty = position_size / entry
        if direction == "long":
            sl = entry * (1 - sl_pct / 100)
            tp = entry * (1 + tp_pct / 100)
            side = "buy"
        else:
            sl = entry * (1 + sl_pct / 100)
            tp = entry * (1 - tp_pct / 100)
            side = "sell"

        broker_order_id = None
        actual_fill_price = entry

        if broker == "ibkr" and asset_class == "stock":
            try:
                from core.trade_executor import executor
                if not executor._ibkr or not executor._ibkr.is_available():
                    return False, "IBKR is not available. Check TWS is running on port 7497.", {}
                submit_qty = int(qty) if qty >= 1 else qty
                result = executor._ibkr.submit_order(
                    symbol=symbol,
                    qty=submit_qty,
                    side=side,
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                )
                if not result:
                    return False, f"IBKR rejected the order for {symbol}.", {}
                broker_order_id = result.get("broker_order_id")
                fill_price = result.get("filled_avg_price", 0)
                actual_fill_price = fill_price if fill_price and fill_price > 0 else entry
            except Exception as exc:
                return False, f"IBKR order error: {exc}", {}

        elif broker == "alpaca" and asset_class == "stock":
            try:
                from core.trade_executor import AlpacaExecutor
                alpaca_ex = AlpacaExecutor()
                submit_qty = int(qty) if qty >= 1 else qty
                result = alpaca_ex.submit_order(
                    symbol=symbol,
                    qty=submit_qty,
                    side=side,
                    stop_loss=round(sl, 2),
                    take_profit=round(tp, 2),
                )
                if not result:
                    return False, f"Alpaca rejected the order for {symbol}.", {}
                broker_order_id = result.get("broker_order_id")
                fill_price = result.get("filled_avg_price", 0)
                actual_fill_price = fill_price if fill_price and fill_price > 0 else entry
            except Exception as exc:
                return False, f"Alpaca order error: {exc}", {}

        if direction == "long":
            sl = actual_fill_price * (1 - sl_pct / 100)
            tp = actual_fill_price * (1 + tp_pct / 100)
        else:
            sl = actual_fill_price * (1 + sl_pct / 100)
            tp = actual_fill_price * (1 - tp_pct / 100)
        qty = position_size / actual_fill_price

        trade_id = str(uuid.uuid4())[:12]
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            INSERT INTO trades
                (trade_id, symbol, asset_class, direction, status,
                 entry_time, entry_price, quantity, position_value,
                 stop_loss, take_profit, pnl, pnl_pct,
                 signal_score, broker, strategy_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0,1.0,?,?)
            """,
            (
                trade_id,
                symbol,
                asset_class,
                direction,
                "open",
                dt.now().isoformat(),
                round(actual_fill_price, 6),
                round(qty, 6),
                round(position_size, 2),
                round(sl, 6),
                round(tp, 6),
                broker,
                strategy_label,
            ),
        )
        try:
            conn.execute(
                "UPDATE trades SET is_overnight=?, broker_order_id=? WHERE trade_id=?",
                (1 if overnight else 0, broker_order_id, trade_id),
            )
        except Exception:
            pass
        conn.commit()
        conn.close()

        return True, (
            f"{direction.upper()} {symbol} opened @ ${actual_fill_price:.6f} | "
            f"SL: ${sl:.6f} | TP: ${tp:.6f} | Qty: {qty:.4f} | Broker: {broker}"
        ), {"trade_id": trade_id, "entry_price": actual_fill_price, "quantity": qty}
    except Exception as exc:
        return False, f"Trade entry error: {exc}", {}


# =============================================================================
# Database browser helpers
# =============================================================================

_DB_TABLE_SEARCH = {
    "trades":           {"strategy":True,"status":True,"symbol":True,
                         "broker":True,"time_col":"exit_time"},
    "capital":          {"time_col":"timestamp"},
    "daily_summaries":  {"time_col":"trade_date"},
    "settlement_queue": {"time_col":"created_at"},
    "ai_signal_reviews":{"strategy":True,"symbol":True,"time_col":"timestamp"},
    "strategy_results": {"strategy":True,"time_col":"recorded_at"},
    "tax_ledger":       {"symbol":True,"time_col":"close_date"},
    "withdrawals":      {"time_col":"timestamp"},
    "chat_actions":     {"time_col":"timestamp"},
    "fund_events":      {"time_col":"timestamp"},
    "bot_state":        {},
    "session_state":    {},
}

_DB_CHOICES = {
    "trading": DB_PATH,
    "candles": ROOT / "data" / "candle_store.db",
}

def _db_path_for(db_key: str | None = None) -> Path:
    key = (db_key or "trading").strip().lower()
    if key in ("candle", "candle_store"):
        key = "candles"
    path = _DB_CHOICES.get(key, DB_PATH)
    if key == "candles" and not path.exists():
        try:
            from intelligence.candle_store import get_store as _get_candle_store
            _get_candle_store(str(path))
        except Exception:
            path.parent.mkdir(parents=True, exist_ok=True)
    return path

def _db_conn(db_key: str | None = None):
    c = sqlite3.connect(str(_db_path_for(db_key)))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=3000")
    c.row_factory = sqlite3.Row
    return c

def _db_valid_tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

def _db_valid_cols(conn, table: str):
    table_sql = _db_quote_identifier(table, _db_valid_tables(conn))
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table_sql})").fetchall()}

_DB_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _db_quote_identifier(name: str, valid_names: set[str]) -> str:
    """
    Return a safely-quoted SQLite identifier after two-layer validation.

    Layer 1 — allow-list: name must be a real table/column name returned by
               sqlite_master or PRAGMA table_info (never user input raw).
    Layer 2 — regex: name must match [A-Za-z_][A-Za-z0-9_]* (no special chars).
    Layer 3 — quoting: the name is double-quoted and internal quotes are escaped.

    SQLite does not support parameterized identifiers (only parameterized values),
    so this function is the correct defence for CWE-089 / CodeQL py/sql-injection
    when interpolating table or column names.  Callers must always pass a
    `valid_names` set sourced from the live schema, never from user input.
    """
    raw = str(name or "")
    if raw not in valid_names:
        raise ValueError(f"Unknown database identifier: {raw!r}")
    if not _DB_IDENTIFIER_RE.match(raw):
        raise ValueError(f"Identifier contains invalid characters: {raw!r}")
    return '"' + raw.replace('"', '""') + '"'

def _db_glob_to_regex(pattern: str) -> str:
    out, i = "", 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                out += ".*"
                i += 2
            else:
                out += r"[^/\\]*"
                i += 1
        elif ch == "?":
            out += r"[^/\\]"
            i += 1
        elif ch == "{":
            end = pattern.find("}", i + 1)
            if end > i:
                parts = [_db_glob_to_regex(p)[1:-1] for p in pattern[i + 1:end].split(",")]
                out += "(?:" + "|".join(parts) + ")"
                i = end + 1
            else:
                out += re.escape(ch)
                i += 1
        elif ch == "[":
            end = pattern.find("]", i + 1)
            if end > i:
                body = pattern[i + 1:end]
                if body.startswith("!"):
                    body = "^" + body[1:]
                out += "[" + body + "]"
                i = end + 1
            else:
                out += re.escape(ch)
                i += 1
        elif ch in ("/", "\\"):
            out += r"[/\\]"
            i += 1
        else:
            out += re.escape(ch)
            i += 1
    return "^" + out + "$"

def _db_like_pattern(pattern: str) -> str:
    s = pattern.replace("\\", "/")
    s = s.replace("%", r"\%").replace("_", r"\_")
    return s.replace("*", "%").replace("?", "_")

def _db_datetime_expr(col_sql: str) -> str:
    text_expr = f"REPLACE(SUBSTR(CAST({col_sql} AS TEXT), 1, 26), 'T', ' ')"
    return f"julianday({text_expr})"

def _db_normalize_datetime_filter(value: str) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("T", " ")
    # Forgive common typed variants like 2026:06:16:12:00:00 or
    # 2026-06-16:12:00:00 and normalize them before parsing.
    m = re.match(
        r"^(\d{4})[-:](\d{2})[-:](\d{2})(?:[ :](\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?)?$",
        raw,
    )
    if m:
        y, mo, d, hh, mm, ss, micro = m.groups()
        hh = hh or "00"
        mm = mm or "00"
        ss = ss or "00"
        micro = (micro or "0").ljust(6, "0")
        return f"{y}-{mo}-{d} {int(hh):02d}:{mm}:{ss}.{micro}"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")

def _db_normalize_datetime_range_end(value: str) -> str | None:
    raw = str(value or "").strip()
    normalized = _db_normalize_datetime_filter(raw)
    if not normalized:
        return None
    # datetime-local inputs normally stop at minutes. Treat the chosen ending
    # minute as inclusive, so 23:59 includes trades through 23:59:59.999999.
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{1,2}:\d{2}$", raw):
        try:
            parsed = datetime.fromisoformat(raw.replace("T", " "))
            parsed = parsed.replace(second=59, microsecond=999999)
            return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return normalized
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return f"{raw} 23:59:59.999999"
    return normalized

def _db_filter_where(filters: dict, valid_cols: set[str]):
    where, params = [], []
    for col, raw in (filters or {}).items():
        if col not in valid_cols:
            continue
        value = str(raw or "").strip()
        if not value:
            continue
        col_sql = _db_quote_identifier(col, valid_cols)
        num = re.match(r"^(<=|>=|<|>|==|=|!=)\s*(-?\d+(?:\.\d+)?)$", value)
        if num:
            op = "=" if num.group(1) in ("=", "==") else num.group(1)
            if op == "!=":
                op = "<>"
            where.append(f"CAST({col_sql} AS REAL) {op} ?")
            params.append(float(num.group(2)))
            continue
        dt_cmp = re.match(r"^(<=|>=|<|>|==|=|!=)\s*(.+)$", value)
        if dt_cmp:
            dt_value = _db_normalize_datetime_filter(dt_cmp.group(2))
            if dt_value:
                op = "=" if dt_cmp.group(1) in ("=", "==") else dt_cmp.group(1)
                if op == "!=":
                    op = "<>"
                where.append(f"{_db_datetime_expr(col_sql)} {op} julianday(?)")
                params.append(dt_value)
                continue
        dt_range = re.match(r"^(.+?)\s*\.\.\s*(.+)$", value)
        if dt_range:
            start = _db_normalize_datetime_filter(dt_range.group(1))
            end = _db_normalize_datetime_range_end(dt_range.group(2))
            if start and end:
                where.append(f"{_db_datetime_expr(col_sql)} BETWEEN julianday(?) AND julianday(?)")
                params.extend([start, end])
                continue
        lead = re.match(r"^([<>])\s*([a-z])$", value, re.I)
        if lead:
            where.append(f"LOWER(SUBSTR(CAST({col_sql} AS TEXT),1,1)) {lead.group(1)} ?")
            params.append(lead.group(2).lower())
            continue
        if any(ch in value for ch in "{}[]"):
            where.append(f"REGEXP(?, CAST({col_sql} AS TEXT))")
            params.append(_db_glob_to_regex(value))
        else:
            where.append(
                f"REPLACE(CAST({col_sql} AS TEXT), '\\', '/') LIKE ? ESCAPE '\\' COLLATE NOCASE"
            )
            params.append(_db_like_pattern(value))
    return where, params

def db_tables(db_key: str | None = None):
    rows = []
    try:
        with _db_conn(db_key) as c:
            tables = c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            valid = {t[0] for t in tables}
            for t in tables:
                name = t[0]
                table_sql = _db_quote_identifier(name, valid)
                cnt = c.execute(f"SELECT COUNT(*) FROM {table_sql}").fetchone()[0]
                rows.append({"name": name, "rows": cnt})
    except Exception as e:
        return {"error": str(e), "tables": [], "db": db_key or "trading"}
    return {"tables": rows, "db": db_key or "trading",
            "db_path": str(_db_path_for(db_key))}

def db_browse(table: str, limit: int = 500, offset: int = 0,
              db_key: str | None = None, filters: dict | None = None):
    # Whitelist: only real table names
    try:
        with _db_conn(db_key) as c:
            valid = _db_valid_tables(c)
    except Exception as e:
        return {"error": str(e)}
    if table not in valid:
        return {"error": f"Unknown table: {table}"}
    try:
        with _db_conn(db_key) as c:
            table_sql = _db_quote_identifier(table, valid)
            c.create_function(
                "REGEXP", 2,
                lambda pattern, value: bool(re.match(pattern, str(value or ""), re.I))
            )
            valid_cols = _db_valid_cols(c, table)
            where, params = _db_filter_where(filters or {}, valid_cols)
            clause = ("WHERE " + " AND ".join(where)) if where else ""
            cur  = c.execute(
                f"SELECT rowid, * FROM {table_sql} {clause} ORDER BY rowid DESC LIMIT ? OFFSET ?",
                (*params, limit, offset)
            )
            cols = [d[0] for d in cur.description]
            rows = [list(r) for r in cur.fetchall()]
        return {"table": table, "cols": cols, "rows": rows,
                "limit": limit, "offset": offset, "db": db_key or "trading",
                "filters": filters or {},
                "db_path": str(_db_path_for(db_key))}
    except Exception as e:
        return {"error": str(e)}

_QUICK_SQL = {
    # rowid is first column so the frontend edit-row feature works (applyResult strips it)
    "Open Today":      """SELECT rowid,trade_id,symbol,direction,status,strategy_name,entry_time,entry_price,stop_loss,take_profit,position_value,broker FROM trades WHERE status='open' AND DATE(entry_time)=DATE('now','localtime') ORDER BY entry_time DESC""",
    "Closed Today":    """SELECT rowid,trade_id,symbol,direction,status,strategy_name,entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,exit_reason,broker FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','localtime') ORDER BY exit_time DESC""",
    "All Open":        """SELECT rowid,trade_id,symbol,direction,status,strategy_name,entry_time,entry_price,stop_loss,take_profit,position_value,broker FROM trades WHERE status='open' ORDER BY entry_time DESC""",
    "Ghost Trades":    """SELECT rowid,trade_id,symbol,direction,status,strategy_name,entry_time,entry_price,position_value,broker,ROUND((julianday('now','localtime')-julianday(entry_time))*24,1) AS hours_open FROM trades WHERE status='open' AND entry_time<datetime('now','-8 hours','localtime') ORDER BY entry_time ASC""",
    "Capital Today":   """SELECT timestamp,total_capital,available_cash,invested_value,daily_pnl,total_pnl,note FROM capital WHERE DATE(timestamp)=DATE('now','localtime') ORDER BY timestamp DESC""",
    "Settlement Queue":"""SELECT rowid,* FROM settlement_queue ORDER BY rowid DESC LIMIT 300""",
    "By Strategy":     """SELECT rowid,trade_id,symbol,direction,status,strategy_name,entry_time,exit_time,entry_price,exit_price,pnl,broker FROM trades ORDER BY entry_time DESC LIMIT 500""",
    "Strategies":      """SELECT kind,name,UPPER(enabled) AS enabled,state_key FROM (
        SELECT 'strategy' AS kind,
               SUBSTR(key,10,LENGTH(key)-17) AS name,
               value AS enabled,
               key AS state_key
        FROM bot_state
        WHERE key LIKE 'strategy_%_enabled'
        UNION ALL
        SELECT 'scanner' AS kind, 'breakout_scanner' AS name,
               COALESCE((SELECT value FROM bot_state WHERE key='breakout_scanner_enabled'),'true') AS enabled,
               'breakout_scanner_enabled' AS state_key
        UNION ALL
        SELECT 'scanner', 'funding_scanner',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_funding_scanner_enabled'),'true'),
               'scanner_funding_scanner_enabled'
        UNION ALL
        SELECT 'scanner', 'gap_scanner',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_gap_scanner_enabled'),'true'),
               'scanner_gap_scanner_enabled'
        UNION ALL
        SELECT 'scanner', 'nr7_scanner',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_nr7_scanner_enabled'),'true'),
               'scanner_nr7_scanner_enabled'
        UNION ALL
        SELECT 'scanner', 'volume_surge',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_volume_surge_enabled'),'true'),
               'scanner_volume_surge_enabled'
        UNION ALL
        SELECT 'scanner', 'emt',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_emt_enabled'),'true'),
               'scanner_emt_enabled'
        UNION ALL
        SELECT 'scanner', 'eat',
               COALESCE((SELECT value FROM bot_state WHERE key='scanner_eat_enabled'),'true'),
               'scanner_eat_enabled'
        UNION ALL
        SELECT 'scanner', SUBSTR(key,9,LENGTH(key)-16),
               value, key
        FROM bot_state
        WHERE key GLOB 'scanner_emt_*_enabled'
           OR key GLOB 'scanner_eat_*_enabled'
    ) ORDER BY kind,name""",
    "Daily P&L":       """SELECT trade_date,daily_pnl,daily_pnl_pct,total_trades,winning_trades,losing_trades,win_rate,largest_win,largest_loss,starting_capital,ending_capital FROM daily_summaries ORDER BY trade_date DESC LIMIT 60""",
    "Yesterday Closed":"""SELECT rowid,trade_id,symbol,direction,strategy_name,entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,exit_reason,broker FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','-1 day','localtime') ORDER BY exit_time DESC""",
    "Signal Reviews":  """SELECT rowid,timestamp,symbol,direction,strategy_name,signal_score,decision,confidence,reasoning FROM ai_signal_reviews ORDER BY timestamp DESC LIMIT 200""",
    "Log Events":      """SELECT rowid,timestamp,severity,event_type,symbol,strategy_name,direction,decision,policy,source_file,line_no,message FROM log_events ORDER BY COALESCE(timestamp, imported_at) DESC, rowid DESC LIMIT 500""",
    "This Week Trades":"""SELECT rowid,trade_id,symbol,direction,strategy_name,entry_time,exit_time,entry_price,exit_price,pnl,pnl_pct,exit_reason,broker FROM trades WHERE status='closed' AND DATE(exit_time)>=DATE('now','-7 days','localtime') ORDER BY exit_time DESC""",
    "Strategy P&L":    """SELECT strategy_name,COUNT(*) AS trades,SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS wins,SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS losses,ROUND(100.0*SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS win_rate_pct,ROUND(SUM(pnl),2) AS total_pnl,ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),2) AS gross_wins,ROUND(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),2) AS gross_losses,ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)/NULLIF(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),0),3) AS profit_factor FROM trades WHERE status='closed' GROUP BY strategy_name ORDER BY total_pnl DESC""",
    "💰 Financials":   """SELECT label,value,detail FROM (SELECT 'Total Capital' AS label,'$'||printf('%.2f',total_capital) AS value,'Cash: $'||printf('%.2f',available_cash)||'   Invested: $'||printf('%.2f',invested_value) AS detail FROM capital ORDER BY timestamp DESC LIMIT 1) UNION ALL SELECT label,value,detail FROM (SELECT 'Daily P&L (tracker)' AS label,(CASE WHEN daily_pnl>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',daily_pnl) AS value,'Cumulative: '||(CASE WHEN total_pnl>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',total_pnl) AS detail FROM capital ORDER BY timestamp DESC LIMIT 1) UNION ALL SELECT 'In Open Trades',('$'||printf('%.2f',COALESCE(SUM(position_value),0))),(CAST(COUNT(*) AS TEXT)||' open positions') FROM trades WHERE status='open' UNION ALL SELECT 'In Settlement',('$'||printf('%.2f',COALESCE(SUM(amount),0))),(CAST(COUNT(*) AS TEXT)||' unsettled items') FROM settlement_queue WHERE settled=0 UNION ALL SELECT 'Today Closed P&L',((CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',COALESCE(SUM(pnl),0))),(CAST(COUNT(*) AS TEXT)||' trades  '||CAST(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS TEXT)||'W / '||CAST(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS TEXT)||'L') FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','localtime') UNION ALL SELECT 'Yesterday P&L',((CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',COALESCE(SUM(pnl),0))),(CAST(COUNT(*) AS TEXT)||' trades  '||CAST(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS TEXT)||'W / '||CAST(SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS TEXT)||'L') FROM trades WHERE status='closed' AND DATE(exit_time)=DATE('now','-1 day','localtime') UNION ALL SELECT 'This Week P&L',((CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',COALESCE(SUM(pnl),0))),(CAST(COUNT(*) AS TEXT)||' trades') FROM trades WHERE status='closed' AND DATE(exit_time)>=DATE('now','-7 days','localtime') UNION ALL SELECT 'This Month P&L',((CASE WHEN COALESCE(SUM(pnl),0)>=0 THEN '+' ELSE '' END)||'$'||printf('%.2f',COALESCE(SUM(pnl),0))),(CAST(COUNT(*) AS TEXT)||' trades') FROM trades WHERE status='closed' AND strftime('%Y-%m',exit_time)=strftime('%Y-%m','now','localtime')""",
}

def db_quick(label: str, db_key: str | None = None):
    if (db_key or "trading") not in ("", "trading"):
        return {"error": "Quick queries are only available for the trading database"}
    sql = _QUICK_SQL.get(label)
    if not sql:
        return {"error": f"Unknown quick query: {label}"}
    try:
        with _db_conn(db_key) as c:
            cur  = c.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = [list(r) for r in cur.fetchall()]
        return {"label": label, "cols": cols, "rows": rows}
    except Exception as e:
        return {"error": str(e)}

def db_search(data: dict):
    db_key = data.get("db", "trading")
    table = data.get("table", "trades")
    try:
        with _db_conn(db_key) as c:
            valid = _db_valid_tables(c)
    except Exception as e:
        return {"error": str(e)}
    if table not in valid:
        return {"error": f"Unknown table: {table}"}
    table_sql = _db_quote_identifier(table, valid)

    cfg    = _DB_TABLE_SEARCH.get(table, {})
    where, params = [], []

    if cfg.get("strategy") and data.get("strategy"):
        where.append("strategy_name LIKE ?")
        params.append(f"%{data['strategy']}%")
    if cfg.get("status") and data.get("status","any") != "any":
        where.append("status=?"); params.append(data["status"])
    if cfg.get("symbol") and data.get("symbol"):
        where.append("symbol LIKE ?"); params.append(f"%{data['symbol'].upper()}%")
    if cfg.get("broker") and data.get("broker","any") != "any":
        where.append("broker=?"); params.append(data["broker"])

    tcol = cfg.get("time_col")
    tf   = data.get("time","any")
    time_params = []
    if tcol and tf != "any":
        tcol_sql = _db_quote_identifier(tcol, {tcol})
        texpr = _db_datetime_expr(tcol_sql)
        if tf == "last 1h":
            where.append(f"{texpr} >= julianday('now','localtime','-1 hour')")
        elif tf == "last 4h":
            where.append(f"{texpr} >= julianday('now','localtime','-4 hours')")
        elif tf == "last 8h":
            where.append(f"{texpr} >= julianday('now','localtime','-8 hours')")
        elif tf == "today":
            where.append(f"{texpr} >= julianday(DATE('now','localtime'))")
            where.append(f"{texpr} < julianday(DATE('now','localtime','+1 day'))")
        elif tf == "yesterday":
            where.append(f"{texpr} >= julianday(DATE('now','localtime','-1 day'))")
            where.append(f"{texpr} < julianday(DATE('now','localtime'))")
        elif tf == "this week":
            where.append(f"{texpr} >= julianday('now','localtime','-7 days')")
        elif tf == "custom":
            # Custom date range from the datetime-local pickers (YYYY-MM-DDTHH:MM format).
            from_dt = (data.get("from_dt") or "").strip()
            to_dt   = (data.get("to_dt")   or "").strip()
            if from_dt:
                from_norm = _db_normalize_datetime_filter(from_dt)
                if from_norm:
                    where.append(f"{texpr} >= julianday(?)")
                    params.append(from_norm)
                    time_params.append(from_norm)
            if to_dt:
                to_norm = _db_normalize_datetime_range_end(to_dt)
                if to_norm:
                    where.append(f"{texpr} <= julianday(?)")
                    params.append(to_norm)
                    time_params.append(to_norm)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql    = f"SELECT rowid, * FROM {table_sql} {clause} ORDER BY rowid DESC LIMIT 2000"
    try:
        with _db_conn(db_key) as c:
            cur  = c.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = [list(r) for r in cur.fetchall()]
        return {
            "table": table,
            "cols": cols,
            "rows": rows,
            "db": db_key,
            "filters": {
                "time": tf,
                "from": data.get("from_dt") or "",
                "to": data.get("to_dt") or "",
                "normalized_time_params": time_params,
            },
        }
    except Exception as e:
        return {"error": str(e)}

def db_edit_row(data: dict):
    db_key   = data.get("db", "trading")
    table    = data.get("table","")
    rowid    = data.get("rowid")
    trade_id = data.get("trade_id")
    col      = data.get("col","")
    new_val  = data.get("value","")
    if not table or not col:
        return False, "Missing table/col"
    if rowid is None and not trade_id:
        return False, "Missing rowid/trade_id"
    try:
        with _db_conn(db_key) as c:
            valid = _db_valid_tables(c)
            if table not in valid:
                return False, f"Unknown table: {table}"
            table_sql = _db_quote_identifier(table, valid)
            cols = _db_valid_cols(c, table)
            if col not in cols:
                return False, f"Unknown column: {col}"
            col_sql = _db_quote_identifier(col, cols)
            if rowid is not None:
                c.execute(f"UPDATE {table_sql} SET {col_sql}=? WHERE rowid=?",
                          (new_val, rowid))
            else:
                # Fallback: quick-query views don't return rowid, use trade_id
                c.execute(f"UPDATE {table_sql} SET {col_sql}=? WHERE trade_id=?",
                          (new_val, trade_id))
            c.commit()
        ref = f"rowid={rowid}" if rowid is not None else f"trade_id={trade_id}"
        return True, f"Updated {table} {ref} {col}={new_val}"
    except Exception as e:
        return False, str(e)

def _db_blank_value_for(col_name: str, col_type: str):
    name = (col_name or "").lower()
    ctype = (col_type or "").upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    if name in ("key", "state_key"):
        return f"new_key_{stamp}"
    if "user" in name:
        return f"new_user_{stamp}"
    if name == "symbol":
        return f"NEW_{stamp}"
    if name == "timeframe":
        return "1m"
    if name in ("ts", "first_ts", "last_ts"):
        return int(time.time())
    if "time" in name or "date" in name or name.endswith("_at"):
        return now
    if "INT" in ctype:
        return 0
    if "REAL" in ctype or "FLOA" in ctype or "DOUB" in ctype or "NUM" in ctype:
        return 0.0
    return ""

def db_add_row(data: dict):
    db_key = data.get("db", "trading")
    table = data.get("table", "")
    if not table:
        return False, "Missing table", {}
    try:
        with _db_conn(db_key) as c:
            valid = _db_valid_tables(c)
            if table not in valid:
                return False, f"Unknown table: {table}", {}
            table_sql = _db_quote_identifier(table, valid)
            info = c.execute(f"PRAGMA table_info({table_sql})").fetchall()
            try:
                c.execute(f"INSERT INTO {table_sql} DEFAULT VALUES")
            except Exception:
                names, vals = [], []
                valid_cols = {col[1] for col in info}
                for col in info:
                    name, ctype, notnull, default, pk = col[1], col[2], col[3], col[4], col[5]
                    if pk == 1 and "INT" in (ctype or "").upper():
                        continue
                    if notnull or pk or default is None:
                        names.append(name)
                        vals.append(_db_blank_value_for(name, ctype))
                if not names:
                    return False, "Could not infer blank row columns", {}
                col_sql = ",".join(_db_quote_identifier(n, valid_cols) for n in names)
                qmarks = ",".join("?" for _ in names)
                c.execute(f"INSERT INTO {table_sql} ({col_sql}) VALUES ({qmarks})", vals)
            rowid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.commit()
            cur = c.execute(f"SELECT rowid, * FROM {table_sql} WHERE rowid=?", (rowid,))
            cols = [d[0] for d in cur.description]
            row = list(cur.fetchone() or [])
        return True, f"Added blank row to {table}", {"cols": cols, "row": row, "rowid": rowid}
    except Exception as e:
        return False, str(e), {}

def db_delete_rows(data: dict):
    db_key = data.get("db", "trading")
    table = data.get("table", "")
    rowids = data.get("rowids") or []
    try:
        rowids = [int(r) for r in rowids if r is not None]
    except Exception:
        return False, "Invalid rowids"
    if not table or not rowids:
        return False, "Missing table/rowids"
    try:
        with _db_conn(db_key) as c:
            valid = _db_valid_tables(c)
            if table not in valid:
                return False, f"Unknown table: {table}"
            table_sql = _db_quote_identifier(table, valid)
            qmarks = ",".join("?" for _ in rowids)
            cur = c.execute(f"DELETE FROM {table_sql} WHERE rowid IN ({qmarks})", rowids)
            c.commit()
        return True, f"Deleted {cur.rowcount} row(s) from {table}"
    except Exception as e:
        return False, str(e)

def db_flush_ghost(data: dict):
    trade_id    = data.get("trade_id","")
    entry_price = data.get("entry_price", 0)
    if not trade_id:
        return False, "Missing trade_id"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _db_conn() as c:
            c.execute("""UPDATE trades SET
                           status='closed', exit_time=?, exit_price=?,
                           exit_reason='manual_flush_ghost', pnl=0, pnl_pct=0
                         WHERE trade_id=?""",
                      (now_str, entry_price, trade_id))
            c.commit()
        return True, f"Flushed ghost trade {trade_id}"
    except Exception as e:
        return False, str(e)

def db_strategy_toggle(data: dict):
    key     = data.get("key","")
    enabled = data.get("enabled", True)
    if not key or not key.startswith("strategy_"):
        return False, "Invalid strategy key"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    val     = "true" if enabled else "false"
    try:
        with _db_conn() as c:
            c.execute("UPDATE bot_state SET value=?, updated=? WHERE key=?",
                      (val, now_str, key))
            c.commit()
        return True, f"{'Enabled' if enabled else 'Disabled'} {key}"
    except Exception as e:
        return False, str(e)


def _safe_log_path(path_value: str) -> Path:
    raw = Path(str(path_value or ""))
    path = raw if raw.is_absolute() else ROOT / raw
    path = path.resolve()
    root = ROOT.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Log path must stay inside the project folder")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")
    return path


def _read_log_context(path: Path, needle: str, context: int = 10,
                      prefer_line: int | None = None):
    context = max(0, min(int(context or 10), 100))
    needle = str(needle or "").strip()
    if not needle:
        raise ValueError("Missing log search text")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        return {"match_line": None, "lines": []}

    matches = []
    for idx, line in enumerate(lines, start=1):
        if needle in line:
            matches.append(idx)
    if not matches:
        # Fall back to a shorter escaped fragment in case the DB row was clipped.
        fragment = needle[:220]
        matches = [
            idx for idx, line in enumerate(lines, start=1)
            if fragment and fragment in line
        ]
    if not matches:
        # Final fallback: regex term search.
        try:
            rx = re.compile(needle, re.I)
            matches = [
                idx for idx, line in enumerate(lines, start=1)
                if rx.search(line)
            ]
        except re.error:
            matches = []
    if not matches:
        return {"match_line": None, "lines": []}

    if prefer_line:
        match_line = min(matches, key=lambda line_no: abs(line_no - prefer_line))
    else:
        match_line = matches[-1]
    start = max(1, match_line - context)
    end = min(len(lines), match_line + context)
    return {
        "match_line": match_line,
        "start_line": start,
        "end_line": end,
        "lines": [
            {
                "line_no": line_no,
                "text": lines[line_no - 1],
                "match": line_no == match_line,
            }
            for line_no in range(start, end + 1)
        ],
    }


def db_log_context(data: dict):
    context = int(data.get("context", 10) or 10)
    rowid = data.get("rowid")
    try:
        if rowid is not None:
            with _db_conn("trading") as c:
                row = c.execute(
                    "SELECT * FROM log_events WHERE rowid=?", (rowid,)
                ).fetchone()
            if not row:
                return False, f"log_events rowid not found: {rowid}", {}
            event = dict(row)
            path = _safe_log_path(event.get("source_file", ""))
            needle = event.get("raw_line") or event.get("message") or ""
            prefer_line = event.get("line_no")
        else:
            event = {}
            path = _safe_log_path(data.get("source_file", ""))
            needle = data.get("term") or data.get("message") or ""
            prefer_line = None

        result = _read_log_context(path, needle, context, prefer_line)
        if not result["lines"]:
            return False, "No matching line found in source log", {
                "source_file": str(path.relative_to(ROOT)),
                "event": event,
            }
        return True, "Log context loaded", {
            "source_file": str(path.relative_to(ROOT)),
            "event": event,
            **result,
        }
    except Exception as e:
        return False, str(e), {}


def build_snapshot():
    """Top-level status metrics."""
    if db is not None:
        cap = db.get_latest_capital() or {}
        open_trades = db.get_open_trades() or []
        try:
            session = db.get_session(date.today().isoformat()) or {}
        except Exception:
            session = {}
        halted = bool(session.get("trading_halted", 0))
        halt_reason = session.get("halt_reason") or ""
        return {
            "bot_status": "PAUSED" if halted else "ACTIVE",
            "trading_active": not halted,
            "halt_reason": halt_reason,
            "open_positions": len(open_trades),
            "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
            "bot_process_running": is_bot_running(),
            "snapshot_source": "live_db_adapter",
            "db_path": str(DB_PATH),
        }

    try:
        conn = sqlite3.connect(DB_PATH)
 #       conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_positions = int(cur.fetchone()[0])
        cur.execute("SELECT available_cash FROM capital ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        available_cash = float(row[0]) if row else 0.0
        conn.close()
        return {
            "bot_status": "UNKNOWN",
            "open_positions": open_positions,
            "available_cash": available_cash,
            "bot_process_running": is_bot_running(),
            "snapshot_source": "sqlite_fallback",
            "db_path": str(DB_PATH),
        }
    except Exception:
        return {
            "bot_status": "UNKNOWN",
            "open_positions": 0,
            "available_cash": 0.0,
            "bot_process_running": is_bot_running(),
            "snapshot_source": "error_fallback",
            "db_path": str(DB_PATH),
        }


def _clean_header_token(value: str, max_len: int = 255) -> str:
    value = str(value or "").replace("\r", "").replace("\n", "").strip()[:max_len]
    return value if re.fullmatch(r"[A-Za-z0-9._~!$&'()*+,;=:%\[\]-]+", value) else ""


def _same_origin_cors_value(origin: str, host: str) -> str:
    origin = str(origin or "").replace("\r", "").replace("\n", "").strip()
    host = _clean_header_token(host)
    if not origin or not host:
        return ""
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        return ""
    if _clean_header_token(parsed.netloc) != host:
        return ""
    return f"{parsed.scheme}://{host}"

def load_entry_html(prefer_modular=True):
    modular = HTML_ROOT / "Trading Dashboard.html"
    stage3 = HTML_ROOT / "index.html"
    if prefer_modular and modular.exists():
        return modular.read_bytes(), "modular"
    return stage3.read_bytes(), "stage3"


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        cors_origin = _same_origin_cors_value(
            self.headers.get("Origin", ""),
            self.headers.get("Host", ""),
        )
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _session_token(self) -> str:
        for part in self.headers.get("Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("session="):
                return part[8:]
        return ""

    def _authed(self) -> bool:
        return _valid_session(self._session_token())

    def _current_user(self) -> str:
        return _session_user(self._session_token())

    def _redirect(self, target: str):
        target = str(target or "/").replace("\r", "").replace("\n", "")
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc or not target.startswith("/"):
            target = "/"
        self.send_response(302)
        self.send_header("Location", target)
        self.end_headers()

    def _serve_html(self, content: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass  # Client disconnected mid-response — harmless

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ── Auth gate ─────────────────────────────────────────────────────────
        _static = path.startswith("/static/") or path.endswith((".css", ".js", ".ico", ".png"))

        if path == "/login":
            return self._serve_html(_LOGIN_PAGE())
        if path == "/setup":
            return self._serve_html(_SETUP_PAGE())
        if path == "/recover":
            return self._serve_html(_RECOVER_PAGE())

        if path == "/api/auth/logout":
            _revoke_session(self._session_token())
            self.send_response(302)
            self.send_header("Set-Cookie", "session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
            self.send_header("Location", "/login")
            self.end_headers()
            return

        if path == "/api/auth/users" and self._authed() and _is_admin(self._current_user()):
            users = _load_users()
            return self._json(200, {"users": [
                {"username": u, "role": v.get("role", "user"), "force_change": v.get("force_change", False)}
                for u, v in users.items()
            ]})

        if path == "/api-keys":
            if not self._authed():
                return self._redirect(f"/login?next=/api-keys")
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            return self._serve_html(_api_keys_page())

        if path == "/api/admin/api_keys" and self._authed() and _is_admin(self._current_user()):
            try:
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT service, key_name, value_enc, updated_at FROM api_keys ORDER BY service, key_name"
                ).fetchall()
                conn.close()
                keys = []
                for r in rows:
                    try:
                        val = _dec_hash(r["value_enc"]) if r["value_enc"] else ""
                    except Exception:
                        val = "⚠ decrypt failed"
                    keys.append({
                        "service":    r["service"],
                        "key_name":   r["key_name"],
                        "value":      val,
                        "updated_at": r["updated_at"][:19],
                    })
                return self._json(200, {"keys": keys})
            except Exception as e:
                return self._json(500, {"error": str(e)})

        # Redirect to setup if default credentials still active
        if _needs_setup() and path not in ("/setup",) and not _static:
            return self._redirect("/setup")

        if not self._authed() and not _static:
                return self._redirect(f"/login?next={quote(self.path, safe='/?=&')}")
        # ── End auth gate ─────────────────────────────────────────────────────

        if path == "/api/terminal/poll":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            params = parse_qs(parsed.query)
            ok, payload = _terminal_poll((params.get("id") or [""])[0], self._current_user())
            return self._json(200 if ok else 404, {"ok": ok, **payload})

        if path == "/api/snapshot":
            return self._json(200, build_snapshot())

        if path == "/api/open_positions":
            params = parse_qs(parsed.query)
            sort_by = (params.get("sort_by") or ["opened"])[0]
            sort_dir = (params.get("sort_dir") or ["desc"])[0]
            return self._json(200, {
                "positions": get_open_positions(sort_by, sort_dir),
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "db_path": str(DB_PATH),
            })

        if path == "/api/emt/status":
            return self._json(200, get_emt_status())


        if path == "/api/chart/strategy_status":
            params = parse_qs(parsed.query)
            symbol = (params.get("symbol") or [""])[0].strip().upper()
            if not symbol:
                return self._json(400, {"ok": False, "error": "symbol is required"})
            if symbol not in FUTURES_SYMBOLS:
                return self._json(400, {
                    "ok": False,
                    "error": "EMT and EAT are available only on futures charts",
                })
            status = _scanner_strategy_status(symbol)
            return self._json(200 if status.get("ok") else 503, status)
        if path == "/api/chart":
            params = parse_qs(parsed.query)
            symbol    = (params.get("symbol")    or ["BTC/USD"])[0].strip()
            timeframe = (params.get("timeframe") or ["5m"])[0].strip()
            limit     = (params.get("limit")     or ["300"])[0].strip()
            broker    = (params.get("broker")    or [""])[0].strip().lower() or None
            try:
                _cd = get_chart_data(symbol, timeframe, limit, broker)
                # Cache bars so /api/chart/patterns can use them without re-fetching
                if _cd.get("bars"):
                    _pattern_bars_cache[f"{symbol}/{timeframe}"] = _cd["bars"][-200:]
                return self._json(200, _cd)
            except Exception as _ce:
                import logging as _lg
                _lg.getLogger(__name__).error(f"[/api/chart] {symbol} crashed: {_ce}", exc_info=True)
                return self._json(200, {"bars": [], "markers": [], "symbol": symbol, "error": str(_ce)})

        if path == "/api/chart/symbols":
            return self._json(200, {"symbols": get_chart_symbols()})

        if path == "/api/chart/patterns":
            params    = parse_qs(parsed.query)
            symbol    = (params.get("symbol")    or ["BTC/USD"])[0].strip()
            timeframe = (params.get("timeframe") or ["5m"])[0].strip()
            try:
                if _PatternDetector is None:
                    return self._json(200, {"patterns": [], "error": "chart_patterns unavailable"})
                bars = _pattern_bars_cache.get(f"{symbol}/{timeframe}", [])
                if not bars:
                    return self._json(200, {"patterns": [], "symbol": symbol, "bar_count": 0,
                                            "note": "load chart first"})
                prices  = [float(b.get("close") or 0)  for b in bars]
                volumes = [float(b.get("volume") or 0) for b in bars]
                opens   = [float(b.get("open")  or 0)  for b in bars]
                bhighs  = [float(b.get("high")  or 0)  for b in bars]
                blows   = [float(b.get("low")   or 0)  for b in bars]
                all_candidates = _PatternDetector().detect(
                    prices, volumes, opens=opens, highs=bhighs, lows=blows, min_confidence=0.0)
                logging.getLogger(__name__).info(
                    f"[patterns] {symbol}/{timeframe}: {len(bars)} bars · "
                    + " | ".join(f"{r.name}={r.confidence:.2f}" for r in all_candidates)
                )
                results = [r for r in all_candidates if r.confidence >= 0.25]
                out = [{"name": r.name, "direction": r.direction, "confidence": round(r.confidence, 3),
                        "description": r.description, "drawings": _pattern_coords(r.name, bars)}
                       for r in results]
                return self._json(200, {"patterns": out, "symbol": symbol,
                                        "timeframe": timeframe, "bar_count": len(bars)})
            except Exception as _pe:
                logging.getLogger(__name__).error(f"[/api/chart/patterns] {symbol}: {_pe}", exc_info=True)
                return self._json(200, {"patterns": [], "error": str(_pe)})

        if path == "/api/chart/fib":
            params    = parse_qs(parsed.query)
            symbol    = (params.get("symbol")    or ["BTC/USD"])[0].strip()
            timeframe = (params.get("timeframe") or ["5m"])[0].strip()
            bars      = _pattern_bars_cache.get(f"{symbol}/{timeframe}", [])
            if not bars:
                return self._json(200, {"fib": None, "error": "load chart first"})
            try:
                fib = _calc_fib_levels(bars)
                return self._json(200, {"fib": fib, "symbol": symbol, "timeframe": timeframe})
            except Exception as _fe:
                logging.getLogger(__name__).error(f"[/api/chart/fib] {symbol}: {_fe}", exc_info=True)
                return self._json(200, {"fib": None, "error": str(_fe)})

        if path == "/api/theme":
            _theme_path = Path(__file__).parent / "config" / "theme.json"
            try:
                theme = json.loads(_theme_path.read_text()) if _theme_path.exists() else {}
            except Exception:
                theme = {}
            return self._json(200, {"theme": theme})

        if path == "/api/tradovate_status":
            if not _tradovate_available:
                return self._json(200, {"available": False, "connected": False})
            connected   = bool(_tradovate_feed and _tradovate_feed.is_connected())
            auth_failed = bool(_tradovate_feed and _tradovate_feed.is_auth_failed())
            running     = bool(_tradovate_feed and _tradovate_feed._running)
            bar_counts  = {}
            if _tradovate_feed:
                from core.tradovate_feed import _bar_cache, _cache_lock
                with _cache_lock:
                    bar_counts = {k: len(v) for k, v in _bar_cache.items()}
            return self._json(200, {
                "available":   True,
                "connected":   connected,
                "running":     running,
                "auth_failed": auth_failed,   # frontend can show "token expired" message
                "bar_counts":  bar_counts,
            })

        if path == "/api/candles":
            params = parse_qs(parsed.query)
            symbol = (params.get("symbol") or [""])[0].strip().upper()
            asset_class = (params.get("asset_class") or params.get("asset") or ["crypto"])[0].lower()
            timeframe = (params.get("timeframe") or ["5 Min"])[0]
            limit = (params.get("limit") or ["100"])[0]
            if not symbol:
                return self._json(400, {"error": "symbol is required"})
            return self._json(200, {"candles": get_candles(symbol, asset_class, timeframe, limit)})

        if path == "/api/injected_symbols":
            return self._json(200, get_injected_symbols())

        if path == "/api/trade_log/today":
            return self._json(200, {"trades": get_today_trade_log(), "db_path": str(DB_PATH)})

        if path == "/api/overview":
            return self._json(200, get_overview_data())

        if path == "/api/quick_status":
            params = parse_qs(parsed.query)
            year = (params.get("year") or [date.today().year])[0]
            return self._json(200, get_quick_status(year))

        # ── Database browser API ──────────────────────────────────────────
        if path == "/api/db/tables":
            params = parse_qs(parsed.query)
            db_key = (params.get("db") or ["trading"])[0]
            return self._json(200, db_tables(db_key))

        if path == "/api/db/browse":
            params = parse_qs(parsed.query)
            table  = (params.get("table") or ["trades"])[0]
            limit  = int((params.get("limit")  or ["500"])[0])
            offset = int((params.get("offset") or ["0"])[0])
            db_key = (params.get("db") or ["trading"])[0]
            try:
                filters = json.loads((params.get("filters") or ["{}"])[0] or "{}")
            except Exception:
                filters = {}
            return self._json(200, db_browse(table, limit, offset, db_key, filters))

        if path == "/api/db/quick":
            params = parse_qs(parsed.query)
            label  = (params.get("q") or [""])[0]
            db_key = (params.get("db") or ["trading"])[0]
            return self._json(200, db_quick(label, db_key))

        if path == "/api/db/strategy_pnl":
            # Strategy P&L summary — grouped by strategy_name, optional date range.
            # Query params: from/to are browser-local datetime strings (both optional).
            try:
                _qs   = parse_qs(parsed.query)
                _from = (_qs.get("from") or [""])[0].strip()
                _to   = (_qs.get("to")   or [""])[0].strip()
                _where = "WHERE status='closed'"
                _params = []
                if _from:
                    _from_norm = _db_normalize_datetime_filter(_from)
                    if _from_norm:
                        _where += f" AND {_db_datetime_expr('exit_time')} >= julianday(?)"
                        _params.append(_from_norm)
                if _to:
                    _to_norm = _db_normalize_datetime_range_end(_to)
                    if _to_norm:
                        _where += f" AND {_db_datetime_expr('exit_time')} <= julianday(?)"
                        _params.append(_to_norm)
                _sql = f"""
                    SELECT strategy_name,
                           COUNT(*) AS trades,
                           SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN pnl<=0 THEN 1 ELSE 0 END) AS losses,
                           ROUND(100.0*SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS win_rate_pct,
                           ROUND(SUM(pnl),2) AS total_pnl,
                           ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),2) AS gross_wins,
                           ROUND(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),2) AS gross_losses,
                           ROUND(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END)
                                 /NULLIF(ABS(SUM(CASE WHEN pnl<=0 THEN pnl ELSE 0 END)),0),3) AS profit_factor
                    FROM trades {_where}
                    GROUP BY strategy_name ORDER BY total_pnl DESC
                """
                import sqlite3 as _sq3
                with _sq3.connect(DB_PATH) as _c:
                    _cur  = _c.execute(_sql, _params)
                    _cols = [d[0] for d in _cur.description]
                    _rows = [list(r) for r in _cur.fetchall()]
                return self._json(200, {
                    "cols": _cols,
                    "rows": _rows,
                    "filters": {
                        "from": _from,
                        "to": _to,
                        "normalized": _params,
                    },
                })
            except Exception as _e:
                return self._json(500, {"error": str(_e)})

        if path == "/api/manual_trade/config":
            return self._json(200, get_manual_trade_config())

        if path == "/api/backtest/config":
            return self._json(200, get_backtest_config())

        if path == "/api/optimize/params":
            from urllib.parse import parse_qs as _pqs
            _qs = _pqs(parsed.query)
            strat = (_qs.get("strategy", [""])[0] or "").strip()
            if not strat:
                return self._json(400, {"ok": False, "error": "strategy required"})
            p = get_strategy_optimizer_params(strat)
            return self._json(200, {"ok": True, "strategy": strat, "params": p})

        if path == "/api/optimize/progress":
            _is_done = (not _optimizer_progress["running"]
                        and _optimizer_progress["results"] is not None)
            # Zombie state: not running, no results, no error, no active process
            # (happens when worker was killed mid-run).  Treat as done so the UI
            # stops polling and lets the user start a new run.
            _is_zombie = (not _optimizer_progress["running"]
                          and not _opt_running.is_set()
                          and _optimizer_progress["results"] is None
                          and not _optimizer_progress.get("error"))
            return self._json(200, {**_optimizer_progress,
                                    "cancel_pending": _opt_cancel.is_set(),
                                    "done": _is_done or _is_zombie,
                                    "zombie": _is_zombie})

        if path == "/api/candle_store":
            try:
                from intelligence.candle_store import get_store as _get_cs
                rows = _get_cs().list_available()
                return self._json(200, {"ok": True, "entries": rows})
            except Exception as _e:
                return self._json(200, {"ok": False, "error": str(_e), "entries": []})

        if path == "/api/manual_trade/preview":
            ok, msg, details = get_manual_trade_preview(parse_qs(parsed.query))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/" or path == "/index.html":
            page, mode = load_entry_html(prefer_modular=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Dashboard-Mode", mode)
            self._cors_headers()
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if path == "/stage3":
            page, _ = load_entry_html(prefer_modular=False)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors_headers()
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        rel_path = path.lstrip("/")
        if rel_path.startswith("static/"):
            rel_path = rel_path[len("static/"):]
        if rel_path:
            # Security: reject null bytes and any path-traversal segments before
            # resolution so static analysers can trace the guard (CodeQL CWE-022).
            # The .resolve() + .is_relative_to() check below is the primary defence;
            # this pre-check makes the intent explicit.
            _norm = rel_path.replace("\\", "/")
            # Also reject drive-letter ("C:/...") and UNC ("//server/share/...")
            # forms before any resolution: pathlib's `/` operator treats an
            # absolute/anchored RHS as a full replacement of the base path, and
            # merely calling .resolve()/.exists() on a UNC path can make Windows
            # attempt an outbound SMB connection (forced-authentication risk) even
            # though is_relative_to() would ultimately reject the result.
            if ("\x00" in rel_path or ".." in _norm.split("/")
                    or _norm.startswith("//") or re.match(r"^[A-Za-z]:", _norm)):
                self._json(404, {"error": "not found"})
                return
            html_root = HTML_ROOT.resolve()
            file_path = (html_root / rel_path).resolve()
            if file_path.is_relative_to(html_root) and file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                self.send_response(200)
                if file_path.suffix in (".jsx", ".js"):
                    mime = "text/javascript"
                elif file_path.suffix == ".css":
                    mime = "text/css"
                elif file_path.suffix == ".html":
                    mime = "text/html; charset=utf-8"
                else:
                    mime = "application/octet-stream"
                self.send_header("Content-Type", mime)
                self._cors_headers()
                self.send_header("Content-Length", str(len(content)))
                if file_path.suffix in (".jsx", ".js", ".html"):
                    self.send_header("Cache-Control", "no-store, max-age=0")
                    self.send_header("Pragma", "no-cache")
                self.end_headers()
                self.wfile.write(content)
                return

        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "Invalid Content-Length"})
        if length > MAX_POST_BYTES:
            return self._json(413, {"error": "Request body too large"})
        try:
            body_raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            data = json.loads(body_raw or "{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "Invalid JSON"})

        global _tradovate_feed, _tradovate_available

        # ── Tradovate debug ───────────────────────────────────────────────────
        if path == "/api/tradovate_debug":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            from core.tradovate_feed import _bar_cache, _cache_lock
            snap = {}
            if _tradovate_feed is not None:
                with _cache_lock:
                    for k, q in _bar_cache.items():
                        bars = list(q)
                        snap[k] = {"count": len(bars), "last_bar": bars[-1] if bars else None}
                return self._json(200, {
                    "connected":    _tradovate_feed.is_connected(),
                    "auth_failed":  _tradovate_feed.is_auth_failed(),
                    "running":      _tradovate_feed._running,
                    "ws_url":       _tradovate_feed._ws_url,
                    "subscriptions": list(_tradovate_feed._subscriptions.keys()),
                    "chart_id_map": {str(k): v for k, v in _tradovate_feed._chart_id_map.items()},
                    "cache": snap,
                })
            return self._json(200, {"status": "no_feed"})

        # ── Theme persistence ─────────────────────────────────────────────────
        if path == "/api/theme":
            _theme_path = Path(__file__).parent / "config" / "theme.json"
            theme = data.get("theme")
            if not isinstance(theme, dict):
                return self._json(400, {"ok": False, "error": "theme must be an object"})
            try:
                _theme_path.parent.mkdir(parents=True, exist_ok=True)
                _theme_path.write_text(json.dumps(theme, indent=2))
                return self._json(200, {"ok": True})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})

        # ── Tradovate real-time feed token ────────────────────────────────────
        if path == "/api/tradovate_token":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            if not _tradovate_available:
                return self._json(503, {"ok": False, "error": "tradovate_feed module not available"})
            token = data.get("token", "").strip()
            if not token:
                return self._json(400, {"ok": False, "error": "token is required"})

            # ── Auto-detect live vs demo from JWT payload ─────────────────────
            # JWT middle segment (payload) is base64url-encoded JSON.
            # envEndpoint.marketData tells us exactly which server to use.
            def _detect_use_live(jwt: str) -> bool:
                try:
                    import base64, json as _json
                    raw = jwt[jwt.index("eyJ"):]          # strip any Bearer prefix
                    parts = raw.split(".")
                    if len(parts) < 2:
                        return False
                    pad = parts[1] + "=="                  # fix base64 padding
                    payload = _json.loads(base64.urlsafe_b64decode(pad))
                    md_url = (payload.get("envEndpoint") or {}).get("marketData", "")
                    return "md-live" in md_url             # live account → live WS
                except Exception:
                    return False                           # default to demo

            _use_live = _detect_use_live(token)
            import logging as _lg2
            _lg2.getLogger(__name__).warning(
                "Tradovate token inject: use_live=%s", _use_live
            )

            # Lock guards create/recreate of the module-level feed so two
            # concurrent token posts can't each construct their own feed and
            # leak the loser's WebSocket/thread (TOCTOU on `_tradovate_feed is None`).
            with _tradovate_feed_lock:
                if _tradovate_feed is None:
                    from core.tradovate_feed import init_feed as _tv_init_feed
                    # init_feed pre-subscribes MESM6 + MNQM6 (1/3/5m each)
                    _tradovate_feed = _tv_init_feed(token=token, use_live=_use_live)
                else:
                    # If the user switched accounts (demo↔live), recreate the feed
                    # with the correct WS URL rather than reusing the old one
                    from core.tradovate_feed import WS_URL_LIVE, WS_URL_DEMO
                    _needed_url = WS_URL_LIVE if _use_live else WS_URL_DEMO
                    if _tradovate_feed._ws_url != _needed_url:
                        # Different endpoint — spin up a fresh feed instance
                        _tradovate_feed.stop()
                        import time as _time; _time.sleep(0.3)
                        from core.tradovate_feed import init_feed as _tv_init_feed2
                        _tradovate_feed = _tv_init_feed2(token=token, use_live=_use_live)
                    else:
                        # Same endpoint — reset auth and restart
                        _tradovate_feed.reset_auth(token)

                        # Ensure MNQM6 subscriptions exist
                        for _mnq_name, _mnq_es in [("MNQM6", 5), ("MNQM6_1", 1), ("MNQM6_3", 3)]:
                            if _mnq_name not in _tradovate_feed._subscriptions:
                                _tradovate_feed.subscribe(_mnq_name, symbol_id="MNQM6",
                                                          element_size=_mnq_es)

                        # Stop and restart so new token takes effect
                        _tradovate_feed.stop()
                        import time as _time; _time.sleep(0.3)
                        _tradovate_feed._authenticated = False
                        _tradovate_feed.start()

            # Pre-resolve contract IDs for all symbols in the map (background thread)
            # so the first chart request always has a numeric ID ready.
            def _prefetch_contract_ids(feed, sym_map, id_cache):
                import logging as _lg
                _log = _lg.getLogger(__name__)
                for root, contract_name in sym_map.items():
                    if contract_name not in id_cache:
                        cid = feed.lookup_symbol_id(contract_name)
                        if cid:
                            id_cache[contract_name] = cid
                            _log.info("Tradovate pre-fetch: %s → id=%d", contract_name, cid)
                        else:
                            _log.warning("Tradovate pre-fetch: could not resolve %s", contract_name)
            import threading as _threading
            _threading.Thread(
                target=_prefetch_contract_ids,
                args=(_tradovate_feed, TRADOVATE_SYMBOL_MAP, TRADOVATE_SYMBOL_IDS),
                name="tv-prefetch-ids",
                daemon=True,
            ).start()

            return self._json(200, {"ok": True, "message": "Tradovate feed started"})

        if path == "/api/tradovate_stop":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            # Called by the frontend when the indicator is toggled off or the
            # futures chart tab is closed — prevents zombie reconnect loops.
            if _tradovate_feed is not None:
                _tradovate_feed.stop()
                import logging as _lg; _lg.getLogger(__name__).info("TradovateFeed: stopped via /api/tradovate_stop")
            return self._json(200, {"ok": True, "message": "Tradovate feed stopped"})

        # ── Auth endpoints (no session required) ──────────────────────────────
        if path == "/api/auth/setup":
            # Only allowed while default admin/admin is still active
            if not _needs_setup():
                return self._json(403, {"ok": False, "message": "Setup already complete."})
            admin_pass = data.get("admin_password", "")
            username   = data.get("username", "").strip()
            password   = data.get("password", "")
            if len(admin_pass) < 8:
                return self._json(400, {"ok": False, "message": "Admin password must be at least 8 characters."})
            if not username or username.lower() == _ADMIN_DEFAULT:
                return self._json(400, {"ok": False, "message": "Choose a username other than 'admin'."})
            if len(password) < 8:
                return self._json(400, {"ok": False, "message": "Your password must be at least 8 characters."})
            users = _load_users()
            users[_ADMIN_DEFAULT] = {"hash": _hash_password(admin_pass), "role": "admin", "force_change": False}
            users[username]       = {"hash": _hash_password(password),   "role": "admin", "force_change": False}
            _save_users(users)
            token = _new_session(username)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie",
                f"session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}")
            body = json.dumps({"ok": True}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            import logging as _lg
            _lg.getLogger("dashboard.auth").info(
                f"[AUTH] Setup complete. Admin password changed. User created: {username!r}")
            return

        if path == "/api/auth/login":
            username = data.get("username", "").strip()
            password = data.get("password", "")
            ip = self.client_address[0] if self.client_address else "unknown"
            if _needs_setup():
                return self._json(403, {"ok": False, "message": "Complete first-time setup first."})
            retry_after = _login_retry_after(username, ip)
            if retry_after:
                return self._json(429, {"ok": False, "message": f"Too many login attempts. Try again in {retry_after}s."})
            ok_login = _auth_check(username, password)
            _record_login_attempt(username, ip, ok_login)
            if ok_login:
                token = _new_session(username)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie",
                    f"session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}")
                body = json.dumps({"ok": True}).encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json(401, {"ok": False, "message": "Invalid credentials"})
            return

        if path == "/api/auth/recover":
            tok_in   = data.get("token", "").strip()
            password = data.get("password", "")
            ip = self.client_address[0] if self.client_address else "unknown"
            retry_after = _recovery_retry_after(ip)
            if retry_after:
                return self._json(429, {"ok": False, "message": f"Too many recovery attempts. Try again in {retry_after}s."})
            if not tok_in or len(tok_in) > RECOVERY_TOKEN_MAX_CHARS:
                _record_recovery_attempt(ip, False)
                return self._json(401, {"ok": False, "message": "Invalid or expired recovery token."})
            if len(password) < 8:
                return self._json(400, {"ok": False, "message": "Password must be at least 8 characters."})
            if len(password) > PASSWORD_MAX_CHARS:
                return self._json(400, {"ok": False, "message": "Password is too long."})
            recovery_ok = secrets.compare_digest(tok_in, _RECOVERY_TOKEN)
            _record_recovery_attempt(ip, recovery_ok)
            if not recovery_ok:
                return self._json(401, {"ok": False, "message": "Invalid or expired recovery token."})
            users = _load_users()
            if not users:
                users = {}
            users[_ADMIN_DEFAULT] = {"hash": _hash_password(password), "role": "admin", "force_change": False}
            _save_users(users)
            import logging as _lg
            _lg.getLogger("dashboard.auth").warning("[AUTH] Admin password reset via recovery token.")
            return self._json(200, {"ok": True})

        if path == "/api/auth/change_password":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            username = data.get("username", "").strip() or self._current_user()
            old_pass = data.get("old_password", "")
            new_pass = data.get("new_password", "")
            if not _auth_check(username, old_pass):
                return self._json(401, {"ok": False, "message": "Current password incorrect."})
            if len(new_pass) < 8:
                return self._json(400, {"ok": False, "message": "New password must be at least 8 characters."})
            users = _load_users()
            users[username]["hash"]         = _hash_password(new_pass)
            users[username]["force_change"] = False
            _save_users(users)
            return self._json(200, {"ok": True})

        # ── Admin: reset any user's password ──────────────────────────────────
        if path == "/api/auth/admin/reset_password":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            target   = data.get("username", "").strip()
            new_pass = data.get("new_password", "")
            users    = _load_users()
            if target not in users:
                return self._json(404, {"ok": False, "message": f"User '{target}' not found."})
            if len(new_pass) < 8:
                return self._json(400, {"ok": False, "message": "New password must be at least 8 characters."})
            users[target]["hash"]         = _hash_password(new_pass)
            users[target]["force_change"] = True   # force them to change on next login
            _save_users(users)
            import logging as _lg
            _lg.getLogger("dashboard.auth").info(
                f"[AUTH] Admin {self._current_user()!r} reset password for {target!r}")
            return self._json(200, {"ok": True})

        # ── Admin: add user ────────────────────────────────────────────────────
        if path == "/api/auth/admin/add_user":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            username = data.get("username", "").strip()
            password = data.get("password", "")
            role     = data.get("role", "user")
            if not username:
                return self._json(400, {"ok": False, "message": "Username cannot be empty."})
            if len(password) < 8:
                return self._json(400, {"ok": False, "message": "Password must be at least 8 characters."})
            users = _load_users()
            if username in users:
                return self._json(409, {"ok": False, "message": f"User '{username}' already exists."})
            users[username] = {"hash": _hash_password(password), "role": role, "force_change": True}
            _save_users(users)
            return self._json(200, {"ok": True})

        # ── Admin: delete user ─────────────────────────────────────────────────
        if path == "/api/auth/admin/delete_user":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            username = data.get("username", "").strip()
            if username == _ADMIN_DEFAULT:
                return self._json(400, {"ok": False, "message": "Cannot delete the admin account."})
            if username == self._current_user():
                return self._json(400, {"ok": False, "message": "Cannot delete your own account."})
            users = _load_users()
            if username not in users:
                return self._json(404, {"ok": False, "message": f"User '{username}' not found."})
            del users[username]
            _save_users(users)
            return self._json(200, {"ok": True})

        # ── Admin: set / update an API key ────────────────────────────────────
        if path == "/api/admin/api_keys/set":
            if not self._authed() or not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            service  = data.get("service",  "").strip().lower()
            key_name = data.get("key_name", "").strip().lower()
            value    = data.get("value",    "").strip()
            if not service or not key_name:
                return self._json(400, {"ok": False, "message": "service and key_name are required"})
            if not value:
                return self._json(400, {"ok": False, "message": "value cannot be empty"})
            try:
                f   = _get_fernet()
                enc = f.encrypt(value.encode()).decode() if f else "plain:" + value
                now = datetime.now(timezone.utc).isoformat()
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("""
                    INSERT INTO api_keys (service, key_name, value_enc, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(service, key_name) DO UPDATE SET
                        value_enc=excluded.value_enc, updated_at=excluded.updated_at
                """, (service, key_name, enc, now))
                conn.commit(); conn.close()
                import logging as _lg
                _lg.getLogger("dashboard.auth").info(
                    f"[API_KEYS] {self._current_user()!r} set {service}/{key_name}")
                return self._json(200, {"ok": True})
            except Exception as e:
                return self._json(500, {"ok": False, "message": str(e)})

        # ── Admin: delete an API key ───────────────────────────────────────────
        if path == "/api/admin/api_keys/delete":
            if not self._authed() or not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            service  = data.get("service",  "").strip().lower()
            key_name = data.get("key_name", "").strip().lower()
            if not service or not key_name:
                return self._json(400, {"ok": False, "message": "service and key_name are required"})
            conn = sqlite3.connect(str(DB_PATH))
            cur  = conn.execute("DELETE FROM api_keys WHERE service=? AND key_name=?", (service, key_name))
            conn.commit(); conn.close()
            if cur.rowcount:
                return self._json(200, {"ok": True, "message": f"{service}/{key_name} deleted — will fall back to .env"})
            return self._json(404, {"ok": False, "message": "Key not found in DB"})

        # ── Candle Store routes ───────────────────────────────────────────────────
        if path == "/api/candle_store/fetch":
            # Fetch candles from yfinance and save to persistent store.
            # Payload: {symbols: ["BTC/USD", ...], timeframe: "1h", days: 365, asset_class: "crypto"}
            symbols     = data.get("symbols") or []
            timeframe   = data.get("timeframe", "1h")
            days        = int(data.get("days", 365))
            asset_class = data.get("asset_class", "crypto")
            if not symbols:
                return self._json(400, {"ok": False, "error": "No symbols provided"})

            def _do_fetch():
                from intelligence.backtester import Backtester
                from intelligence.candle_store import get_store as _gcs
                bt    = Backtester()
                store = _gcs()
                results = []
                for sym in symbols:
                    try:
                        if asset_class == "crypto":
                            df = bt.fetch_history_crypto(sym, days=days, timeframe=timeframe)
                        else:
                            df = bt.fetch_history(sym, days=days, timeframe=timeframe)
                        if df is not None and not df.empty:
                            n = store.save(sym, timeframe, df)
                            results.append({"symbol": sym, "ok": True, "bars": n})
                        else:
                            results.append({"symbol": sym, "ok": False, "error": "No data returned"})
                    except Exception as _fe:
                        results.append({"symbol": sym, "ok": False, "error": str(_fe)})
                return results

            try:
                fetch_results = _do_fetch()
                return self._json(200, {"ok": True, "results": fetch_results})
            except Exception as _e:
                return self._json(500, {"ok": False, "error": str(_e)})

        if path == "/api/candle_store/delete":
            # Delete cached data for one symbol/timeframe.
            # Payload: {symbol: "BTC/USD", timeframe: "1h"}
            symbol    = data.get("symbol", "")
            timeframe = data.get("timeframe", "1h")
            if not symbol:
                return self._json(400, {"ok": False, "error": "No symbol provided"})
            try:
                from intelligence.candle_store import get_store as _gcs
                n = _gcs().delete(symbol, timeframe)
                return self._json(200, {"ok": True, "deleted_bars": n,
                                        "message": f"Cleared {symbol}/{timeframe} ({n:,} bars)"})
            except Exception as _e:
                return self._json(500, {"ok": False, "error": str(_e)})

        if path == "/api/candle_store/sync_watchlist":
            # Remove cached symbols NOT on any active watchlist.
            try:
                import os as _os
                from intelligence.candle_store import get_store as _gcs
                _root = _os.path.dirname(_os.path.abspath(__file__))
                _watch_syms = set()
                for _wf in ["watchlists/crypto.txt", "watchlists/stocks.txt",
                            "watchlist/scanned_crypto.txt", "watchlist/scanned_stocks.txt"]:
                    _fp = _os.path.join(_root, _wf)
                    if _os.path.exists(_fp):
                        with open(_fp) as _fh:
                            for _line in _fh:
                                _s = _line.strip()
                                if _s and not _s.startswith('#'):
                                    _watch_syms.add(_s.upper())
                _cs = _gcs()
                _all = _cs.list_available()
                _all_syms = set(e["symbol"].upper() for e in _all)
                _orphans = _all_syms - _watch_syms
                _deleted_bars = 0
                for _sym in _orphans:
                    for _e in [e for e in _all if e["symbol"].upper() == _sym.upper()]:
                        _deleted_bars += _cs.delete(_e["symbol"], _e["timeframe"])
                return self._json(200, {
                    "ok": True,
                    "deleted_symbols": sorted(_orphans),
                    "remaining_symbols": sorted(_watch_syms & _all_syms),
                    "deleted_bars": _deleted_bars,
                    "watchlist_size": len(_watch_syms),
                })
            except Exception as _e:
                return self._json(500, {"ok": False, "error": str(_e)})

        if path == "/api/candle_store/flush_download":
            # Wipe ALL candles for given symbols then re-download fresh.
            # Payload: {symbols: [...], timeframe: "1h", days: 365, asset_class: "crypto"}
            _syms = data.get("symbols", [])
            _tf   = data.get("timeframe", "1h")
            _days = int(data.get("days", 365))
            if not _syms:
                return self._json(400, {"ok": False, "error": "No symbols provided"})
            try:
                from intelligence.candle_store import get_store as _gcs
                _cs = _gcs()
                _wiped = 0
                _all = _cs.list_available()
                for _e in _all:
                    if _e["symbol"] in _syms:
                        _wiped += _cs.delete(_e["symbol"], _e["timeframe"])
                from core.candle_manager import candle_manager as _cm
                _results = []
                for _sym in _syms:
                    try:
                        ok = _cm.prefetch(_sym, _tf, limit=max(300, _days * 24))
                        _results.append({"symbol": _sym, "ok": ok,
                                         "bars": len(_cm.get(_sym, _tf, limit=9999) or [])})
                    except Exception as _se:
                        _results.append({"symbol": _sym, "ok": False, "error": str(_se)})
                return self._json(200, {"ok": True, "wiped_bars": _wiped, "results": _results})
            except Exception as _e:
                return self._json(500, {"ok": False, "error": str(_e)})

        # ── Optimizer routes ─────────────────────────────────────────────────
        if path == "/api/optimize/cancel":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            was_running = _opt_running.is_set()
            _opt_cancel.set()
            # Kill the subprocess if one is running
            if _opt_proc is not None:
                try:
                    _opt_proc.terminate()
                except Exception:
                    pass
            return self._json(200, {"ok": True, "was_running": was_running,
                                    "message": "Cancel signal sent to optimizer"})

        if path == "/api/optimize":
            if not self._authed():
                return self._json(401, {"error": "Unauthorized"})
            _opt_cancel.clear()   # reset cancel flag so new run starts clean
            if _opt_running.is_set():
                return self._json(200, {"ok": False, "error": "Optimizer already running — cancel first", "results": []})
            _optimizer_progress.update({"running": False, "iteration": 0, "total": 0,
                                        "best_score": None, "cancelled": False,
                                        "results": None, "error": None})
            t = threading.Thread(target=run_optimize_api, args=(data,), daemon=True)
            t.start()
            return self._json(200, {"ok": True, "status": "started"})

        # ── Auth gate for all other POSTs ─────────────────────────────────────
        if not self._authed():
            return self._json(401, {"error": "Unauthorized"})
        # ── End auth gate ─────────────────────────────────────────────────────

        if path == "/api/chart/strategy_config":
            if not _is_admin(self._current_user()):
                return self._json(403, {
                    "ok": False,
                    "error": "Admin only",
                })
            symbol = str(data.get("symbol") or "").strip().upper()
            strategy = str(data.get("strategy") or "").strip().lower()
            if symbol not in FUTURES_SYMBOLS:
                return self._json(400, {
                    "ok": False,
                    "error": "EMT and EAT are available only on futures charts",
                })
            if strategy not in ("emt", "eat"):
                return self._json(400, {
                    "ok": False,
                    "error": "strategy must be EMT or EAT",
                })
            result = _scanner_configure_strategy({
                "symbol": symbol,
                "strategy": strategy,
                "settings": data.get("settings") or {},
            })
            return self._json(200 if result.get("ok") else 400, result)
        if path == "/api/chart/strategy_bulk_config":
            if not _is_admin(self._current_user()):
                return self._json(403, {
                    "ok": False,
                    "error": "Admin only",
                })
            strategy = str(data.get("strategy") or "").strip().lower()
            if strategy not in ("emt", "eat"):
                return self._json(400, {
                    "ok": False,
                    "error": "strategy must be EMT or EAT",
                })
            enabled = bool(data.get("enabled", True))
            symbols = sorted(_strategy_supported_symbols())
            results = {}
            for sym in symbols:
                results[sym] = _scanner_configure_strategy({
                    "symbol": sym,
                    "strategy": strategy,
                    "settings": {"enabled": enabled},
                })
            ok = bool(symbols) and all(r.get("ok") for r in results.values())
            return self._json(200, {
                "ok": ok,
                "strategy": strategy,
                "enabled": enabled,
                "results": results,
            })
        if path == "/api/terminal/start":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, payload = _terminal_start(str(data.get("kind") or "hostinger"), self._current_user())
            return self._json(200 if ok else 400, {"ok": ok, **payload})

        if path == "/api/terminal/input":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, payload = _terminal_input(str(data.get("id") or ""), str(data.get("data") or ""), self._current_user())
            return self._json(200 if ok else 404, {"ok": ok, **payload})

        if path == "/api/terminal/resize":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, payload = _terminal_resize(str(data.get("id") or ""), int(data.get("cols") or 80), int(data.get("rows") or 24), self._current_user())
            return self._json(200 if ok else 404, {"ok": ok, **payload})

        if path == "/api/terminal/stop":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, payload = _terminal_stop(str(data.get("id") or ""), self._current_user())
            return self._json(200 if ok else 404, {"ok": ok, **payload})

        if path == "/api/trades/manual":
            ok, msg, details = open_manual_trade(data)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/injected_symbols":
            ok, msg, symbols = inject_symbols(
                str(data.get("kind") or "").lower(),
                data.get("symbols"),
                replace=bool(data.get("replace", False)),
            )
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **symbols})

        if path == "/api/injected_symbols/clear":
            return self._json(200, {"ok": True, "message": "Injected symbols cleared.", **clear_injected_symbols()})

        if path == "/api/report/daily":
            ok, msg, details = generate_daily_report()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/tax/export":
            ok, msg, details = export_tax_csv(data.get("year"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/withdrawal":
            ok, msg, details = process_withdrawal(data.get("amount"), data.get("reason"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/expense":
            ok, msg, details = record_expense(
                data.get("expense_date"), data.get("category"), data.get("amount"),
                data.get("description"), data.get("vendor"), data.get("recurring"),
            )
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/ml/retrain":
            ok, msg, details = retrain_ml()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/backtest/cancel":
            running = _bt_running.is_set()
            with _bt_lock:
                ctx = _bt_current_run
            if ctx is not None:
                ctx.cancel()
            try:
                from intelligence.backtester import request_cancel
                request_cancel()  # also cancel the shared default context, for any CLI-triggered run
            except Exception:
                pass
            msg = "Cancel signal sent — waiting for next backtest checkpoint." if running else "Cancel signal set; no active backtest was marked running."
            return self._json(200, {"ok": True, "running": running, "message": msg})

        if path == "/api/chronos_predict":
            return self._json(200, _chronos_predict(data))

        if path == "/api/backtest":
            if _bt_running.is_set():
                return self._json(200, {"ok": False, "error": "Backtest already running — cancel first", "results": []})
            ok, msg, details = run_backtest_api(data)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        if path == "/api/chat":
            ok, msg, details = chat_with_bot(data.get("message"))
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        # ── Database browser POST actions ─────────────────────────────────────
        if path in ("/api/db/search", "/api/db/edit_row", "/api/db/add_row",
                    "/api/db/delete_rows", "/api/db/flush_ghost",
                    "/api/db/strategy_toggle", "/api/db/log_context"):
            if path == "/api/db/search":
                return self._json(200, db_search(data))
            if path == "/api/db/edit_row":
                ok, msg = db_edit_row(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg})
            if path == "/api/db/add_row":
                ok, msg, details = db_add_row(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})
            if path == "/api/db/delete_rows":
                ok, msg = db_delete_rows(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg})
            if path == "/api/db/flush_ghost":
                ok, msg = db_flush_ghost(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg})
            if path == "/api/db/strategy_toggle":
                ok, msg = db_strategy_toggle(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg})
            if path == "/api/db/log_context":
                ok, msg, details = db_log_context(data)
                return self._json(200 if ok else 400, {"ok": ok, "message": msg, **details})

        # ── Broker Panel API ──────────────────────────────────────────────────
        if path == "/api/broker_panel/accounts":
            try:
                from core.trade_executor import executor as _tex
                _ibkr_ok   = bool(getattr(_tex, '_ibkr',   None) and getattr(_tex._ibkr,   'is_available', lambda: False)())
                _kraken_ok = bool(getattr(_tex, '_kraken', None))
                _alpaca_ok = bool(getattr(_tex, '_alpaca', None))
            except Exception:
                _ibkr_ok = _kraken_ok = _alpaca_ok = False
            _accts = []
            if _kraken_ok:
                _accts.append({"broker": "kraken", "modes": ["live"]})
            if _alpaca_ok:
                _accts.append({"broker": "alpaca", "modes": ["paper", "live"]})
            if _ibkr_ok:
                _accts.append({"broker": "ibkr", "modes": ["live"]})
            if not _accts:
                _accts = [
                    {"broker": "kraken", "modes": ["live"]},
                    {"broker": "alpaca", "modes": ["paper", "live"]},
                    {"broker": "ibkr",   "modes": ["live"]},
                    {"broker": "paper",  "modes": ["paper"]},
                ]
            return self._json(200, {"accounts": _accts})

        if path == "/api/broker_panel/balance":
            params = parse_qs(parsed.query)
            _broker = (params.get("broker") or [""])[0].lower()
            try:
                from core.trade_executor import executor as _tex
                if _broker == "kraken":
                    _k = getattr(_tex, '_kraken', None)
                    if _k: return self._json(200, {"balance": _k.get_account_balance()})
                if _broker in ("alpaca", "paper"):
                    _a = getattr(_tex, '_alpaca', None)
                    if _a: return self._json(200, {"balance": _a.get_account_balance()})
                if _broker == "ibkr":
                    _i = getattr(_tex, '_ibkr', None)
                    if _i: return self._json(200, {"balance": _i.get_account_balance()})
                return self._json(200, {"balance": {}, "note": f"{_broker} not connected"})
            except Exception as _e:
                return self._json(200, {"balance": {}, "error": str(_e)})

        if path == "/api/broker_panel/positions":
            params = parse_qs(parsed.query)
            _broker = (params.get("broker") or [""])[0].lower()
            try:
                from core.trade_executor import executor as _tex
                if _broker == "kraken":
                    _k = getattr(_tex, '_kraken', None)
                    if _k: return self._json(200, {"positions": _k.get_open_positions()})
                if _broker in ("alpaca", "paper"):
                    _a = getattr(_tex, '_alpaca', None)
                    if _a: return self._json(200, {"positions": _a.get_open_positions()})
                if _broker == "ibkr":
                    _i = getattr(_tex, '_ibkr', None)
                    if _i: return self._json(200, {"positions": _i.get_open_positions()})
                return self._json(200, {"positions": []})
            except Exception as _e:
                return self._json(200, {"positions": [], "error": str(_e)})

        if path == "/api/broker_panel/history":
            return self._json(200, {"history": []})

        if path == "/api/broker_panel/price":
            params = parse_qs(parsed.query)
            _sym   = (params.get("symbol") or [""])[0].strip()
            _broker = (params.get("broker") or [""])[0].lower()
            try:
                _ac = "crypto" if "/" in _sym else "stock"
                _px = get_current_price(_sym, _ac)
                return self._json(200, {"price": _px, "symbol": _sym})
            except Exception as _e:
                return self._json(200, {"price": None, "error": str(_e)})

        if path == "/api/broker_panel/assets":
            return self._json(200, {"assets": []})

        if path == "/api/broker_panel/close":
            position_id = (
                data.get("trade_id")
                or data.get("position_id")
                or data.get("id")
            )
            if position_id is None and data.get("symbol"):
                symbol = str(data.get("symbol")).upper()
                try:
                    for trade in db.get_open_trades() or []:
                        if str(trade.get("symbol", "")).upper() == symbol:
                            position_id = trade.get("trade_id") or trade.get("id")
                            break
                except Exception:
                    position_id = None
            if position_id is None:
                return self._json(
                    400,
                    {"ok": False, "message": "position_id or trade_id is required"},
                )
            paper_futures = bool(
                _paper_futures_identity(_find_open_trade(position_id) or {})
            )
            ok, msg = request_close_position(position_id)
            status = 200 if ok and paper_futures else (202 if ok else 400)
            return self._json(status, {"ok": ok, "message": msg})

        if path == "/api/broker_panel/order":
            return self._json(200, {"ok": False, "message": "Direct order via broker panel not yet implemented."})

        if path != "/api/control":
            return self._json(404, {"error": "not found"})

        action = data.get("action")

        if action == "pause_trading":
            if risk_manager is not None:
                risk_manager.manual_halt("Paused via HTML dashboard")
                return self._json(200, {"ok": True, "message": "Trading paused."})
            return self._json(202, {"ok": False, "message": "Risk manager unavailable in fallback mode."})

        if action == "resume_trading":
            if risk_manager is not None:
                risk_manager.manual_resume()
                return self._json(200, {"ok": True, "message": "Trading resumed."})
            return self._json(202, {"ok": False, "message": "Risk manager unavailable in fallback mode."})

        if action == "start_bot":
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        if action == "stop_bot":
            ok, msg = stop_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        if action == "restart_bot":
            stop_bot_process()
            # light delay to reduce duplicate-start races
            try:
                import time
                time.sleep(2)
            except Exception:
                pass
            if is_bot_running():
                return self._json(400, {"ok": False, "message": "Bot still running after stop; restart aborted."})
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": f"Restart requested. {msg}"})

        if action == "open_db_panel":
            try:
                subprocess.Popen(
                    [str(BOT_PYTHON), str(ROOT / "db_panel.py")],
                    cwd=str(ROOT),
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                return self._json(200, {"ok": True, "message": "DB Panel launched."})
            except Exception as e:
                return self._json(500, {"ok": False, "message": str(e)})

        if action == "refresh_scan":
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})

        if action == "open_terminal":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, msg = open_project_terminal()
            return self._json(200 if ok else 400, {"ok": ok, "message": msg, "platform": sys.platform})

        if action == "open_hostinger_terminal":
            if not _is_admin(self._current_user()):
                return self._json(403, {"error": "Admin only"})
            ok, msg, command = open_hostinger_terminal()
            return self._json(200 if ok else 400, {
                "ok": ok, "message": msg, "command": command, "platform": sys.platform
            })

        if action == "close_position":
            position_id = data.get("position_id")
            if position_id is None:
                return self._json(400, {"ok": False, "message": "position_id is required"})
            paper_futures = bool(
                _paper_futures_identity(_find_open_trade(position_id) or {})
            )
            ok, msg = request_close_position(position_id)
            status = 200 if ok and paper_futures else (202 if ok else 400)
            return self._json(status, {"ok": ok, "message": msg})

        return self._json(400, {"error": f"Unknown action: {action}"})


if __name__ == "__main__":
    # Seed default admin/admin on very first start
    _ensure_admin_seeded()

    print(f"Starting dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    print(f"DB: {DB_PATH}", flush=True)
    print("=" * 60, flush=True)

    if _needs_setup():
        print("  FIRST-TIME SETUP REQUIRED", flush=True)
        print(f"  Default credentials:  admin / admin", flush=True)
        print(f"  Visit http://localhost:{WEB_DASHBOARD_PORT}/setup to get started.", flush=True)
    else:
        users = _load_users()
        print(f"  Auth enabled — accounts: {list(users.keys())}", flush=True)

    print(f"  Recovery token : {_RECOVERY_TOKEN}", flush=True)
    print(f"  Locked out?    : http://localhost:{WEB_DASHBOARD_PORT}/recover", flush=True)
    print("=" * 60, flush=True)

    server = ThreadingHTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    server.serve_forever()
