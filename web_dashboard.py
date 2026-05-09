"""Stage-2 web dashboard bridge.

Run: python web_dashboard.py
Open: http://localhost:8080
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from data.database import db
from core.risk_manager import risk_manager

ROOT = Path(__file__).parent
HTML_ROOT = ROOT / "Html-Files"


def build_snapshot():
    cap = db.get_latest_capital() or {}
    open_trades = db.get_open_trades() or []
    halted = bool(getattr(risk_manager, "trading_halted", False))
    return {
        "bot_status": "PAUSED" if halted else "ACTIVE",
        "open_positions": len(open_trades),
        "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
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
        if self.path.startswith("/static/"):
            rel = self.path[len('/static/'):]
            file_path = HTML_ROOT / rel
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                ctype = "text/plain"
                if file_path.suffix in {".js", ".jsx"}:
                    ctype = "text/javascript"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
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
            risk_manager.manual_halt("Paused via HTML dashboard")
            return self._json(200, {"ok": True, "message": "Trading paused."})
        if action == "refresh_scan":
            # Stage 2 hook: UI wiring only; scanner execution can move in stage 3.
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})
        return self._json(400, {"error": f"Unknown action: {action}"})


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
