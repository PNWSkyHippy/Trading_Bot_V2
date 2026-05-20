"""Stage-2 web dashboard bridge.

Run: python web_dashboard.py
"""
import json
import logging
import os
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

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
logger = logging.getLogger(__name__)

risk_manager = None
db = None
try:
    from data.database import db as _db
    db = _db
except Exception:
    logger.warning("database module unavailable; snapshot fallback enabled", exc_info=True)
    db = None

try:
    from core.risk_manager import risk_manager as _risk_manager
    risk_manager = _risk_manager
except Exception:
    logger.warning("risk_manager unavailable; control pause/resume may degrade", exc_info=True)
    risk_manager = None


def is_bot_running():
    try:
        if sys.platform == "win32":
            return len(find_bot_pids_windows()) > 0
        out = subprocess.check_output(["ps", "-ef"], text=True)
        return "bot_engine.py" in out
    except Exception:
        return False


def find_bot_pids_windows():
    """Find bot_engine.py process IDs using psutil command-line matching."""
    try:
        import psutil

        current_pid = os.getpid()
        bot_name = BOT_SCRIPT.name.lower()
        pids = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                pid = int(info.get("pid") or 0)
                if pid == current_pid:
                    continue
                name = (info.get("name") or "").lower()
                if "python" not in name:
                    continue
                cmdline = [str(part) for part in (info.get("cmdline") or [])]
                if any(Path(part).name.lower() == bot_name for part in cmdline):
                    pids.append(pid)
            except Exception:
                continue
        return pids
    except Exception:
        return []


def start_bot_process():
    if is_bot_running():
        return False, "Bot is already running."
    try:
        creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        subprocess.Popen([sys.executable, str(BOT_SCRIPT)], cwd=str(ROOT), creationflags=creationflags)
        return True, "Bot start requested."
    except Exception as exc:
        return False, f"Failed to start bot: {exc}"


def stop_bot_process():
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


def build_snapshot():
    if db is not None:
        try:
            cap = db.get_latest_capital() or {}
            open_trades = db.get_open_trades() or []
            halted = bool(getattr(risk_manager, "trading_halted", False)) if risk_manager else False
            return {
                "bot_status": "PAUSED" if halted else "ACTIVE",
                "open_positions": len(open_trades),
                "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
                "bot_process_running": is_bot_running(),
                "snapshot_source": "live_db_adapter",
                "db_path": str(DB_PATH),
            }
        except Exception:
            logger.error("snapshot_adapter_failed db=%s", DB_PATH, exc_info=True)

    try:
        conn = sqlite3.connect(DB_PATH)
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
        logger.error("snapshot_query_failed db=%s", DB_PATH, exc_info=True)
        return {
            "bot_status": "UNKNOWN",
            "open_positions": 0,
            "available_cash": 0.0,
            "bot_process_running": is_bot_running(),
            "snapshot_source": "error_fallback",
            "db_path": str(DB_PATH),
            "degraded": True,
            "error_code": "SNAPSHOT_DB_UNAVAILABLE",
        }


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/snapshot":
            return self._json(200, build_snapshot())
        if self.path == "/" or self.path == "/index.html":
            page = (HTML_ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        if self.path.startswith("/src/") or self.path.startswith("/static/src/"):
            rel_path = self.path.lstrip("/")
            if rel_path.startswith("static/"):
                rel_path = rel_path[len("static/"):]
            root = HTML_ROOT.resolve()
            candidate = (root / rel_path).resolve()
            if root not in candidate.parents and candidate != root:
                return self._json(403, {"error": "forbidden"})
            if candidate.exists() and candidate.is_file():
                content = candidate.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/control":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            return self._json(400, {"ok": False, "message": f"Invalid JSON: {exc.msg}"})
        if not isinstance(data, dict):
            return self._json(400, {"ok": False, "message": "Payload must be a JSON object."})
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
            if is_bot_running():
                return self._json(400, {"ok": False, "message": "Bot still running after stop; restart aborted."})
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": f"Restart requested. {msg}"})

        if action == "refresh_scan":
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})

        return self._json(400, {"error": f"Unknown action: {action}"})


WEB_DASHBOARD_PORT = 8125

if __name__ == "__main__":
    print(f"Starting HTML dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server = HTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    print(f"Serving HTML dashboard at http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server.serve_forever()
