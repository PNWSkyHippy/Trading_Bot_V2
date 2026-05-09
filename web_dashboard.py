"""Stage-2 web dashboard bridge.

Run: python web_dashboard.py
"""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
HTML_ROOT = ROOT / "Html-Files"
DB_PATH = ROOT / "trading_bot.db"

risk_manager = None
db = None
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


def build_snapshot():
    if db is not None:
        cap = db.get_latest_capital() or {}
        open_trades = db.get_open_trades() or []
        halted = bool(getattr(risk_manager, "trading_halted", False)) if risk_manager else False
        return {
            "bot_status": "PAUSED" if halted else "ACTIVE",
            "open_positions": len(open_trades),
            "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
        }

    # Fallback mode for environments missing python deps (e.g., cryptography).
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_positions = int(cur.fetchone()[0])
        cur.execute("SELECT available_cash FROM capital ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        available_cash = float(row[0]) if row else 0.0
        conn.close()
        return {"bot_status": "UNKNOWN", "open_positions": open_positions, "available_cash": available_cash}
    except Exception:
        return {"bot_status": "UNKNOWN", "open_positions": 0, "available_cash": 0.0}


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
            file_path = HTML_ROOT / rel_path
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
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
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        action = data.get("action")
        if action == "pause_trading":
            if risk_manager is not None:
                risk_manager.manual_halt("Paused via HTML dashboard")
                return self._json(200, {"ok": True, "message": "Trading paused."})
            return self._json(202, {"ok": False, "message": "Risk manager unavailable in fallback mode."})
        if action == "refresh_scan":
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})
        return self._json(400, {"error": f"Unknown action: {action}"})


WEB_DASHBOARD_PORT = 8125

if __name__ == "__main__":
    print(f"Starting HTML dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server = HTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    print(f"Serving HTML dashboard at http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server.serve_forever()