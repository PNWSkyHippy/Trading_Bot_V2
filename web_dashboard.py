"""Stage-2 web dashboard bridge.

Run: python web_dashboard.py
"""
import json
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent

DEFAULT_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Trading Bot V2 Web Dashboard</title>
  <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" src="./src/App.jsx"></script>
</body>
</html>
"""

DEFAULT_APP_JSX = """const { useEffect, useState } = React;

function App() {
  const [snapshot, setSnapshot] = useState({ bot_status: "UNKNOWN", open_positions: 0, available_cash: 0 });

  useEffect(() => {
    fetch('/api/snapshot')
      .then((r) => r.json())
      .then(setSnapshot)
      .catch(() => {});
  }, []);

  return <div style={{fontFamily:'Arial', padding:'16px'}}>
    <h1>Trading Bot Dashboard</h1>
    <p>Status: {snapshot.bot_status}</p>
    <p>Open positions: {snapshot.open_positions}</p>
    <p>Available cash: ${Number(snapshot.available_cash || 0).toFixed(2)}</p>
  </div>;
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
"""


def resolve_html_root():
    preferred = ROOT / "Html-Files"
    fallback = ROOT / "HTML-Files"

    if (preferred / "index.html").exists():
        return preferred
    if (fallback / "index.html").exists():
        return fallback

    preferred.mkdir(parents=True, exist_ok=True)
    src_dir = preferred / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    index_file = preferred / "index.html"
    app_file = src_dir / "App.jsx"

    if not index_file.exists():
        index_file.write_text(DEFAULT_INDEX_HTML, encoding="utf-8")
    if not app_file.exists():
        app_file.write_text(DEFAULT_APP_JSX, encoding="utf-8")

    print("HTML dashboard files were missing; generated baseline files under Html-Files/.", flush=True)
    return preferred


HTML_ROOT = resolve_html_root()

DB_PATH = ROOT / "trading_bot.db"
BOT_SCRIPT = ROOT / "bot_engine.py"

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


def is_bot_running():
    try:
        out = subprocess.check_output(["ps", "-ef"], text=True)
        return "bot_engine.py" in out
    except Exception:
        return False


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
                result = subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True)
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

def get_open_positions():
    if db is not None:
        try:
            rows = db.get_open_trades() or []
            positions = []
            for t in rows:
                positions.append({
                    "id": t.get("id"),
                    "symbol": t.get("symbol") or t.get("ticker") or "?",
                    "side": t.get("side") or "",
                    "qty": float(t.get("shares") or t.get("quantity") or 0),
                    "entry_price": float(t.get("entry_price") or 0),
                    "entry_time": t.get("entry_time") or "",
                })
            return positions
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_PATH)
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
        return [
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
    except Exception:
        return []


def close_position(position_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE trades SET status='closed' WHERE id=? AND status='open'", (position_id,))
        updated = cur.rowcount
        conn.commit()
        conn.close()
        if updated:
            return True, f"Closed position id {position_id}."
        return False, f"Position id {position_id} not found or already closed."
    except Exception as exc:
        return False, f"Close failed: {exc}"


def build_snapshot():
    if db is not None:
        cap = db.get_latest_capital() or {}
        open_trades = db.get_open_trades() or []
        halted = bool(getattr(risk_manager, "trading_halted", False)) if risk_manager else False
        return {
            "bot_status": "PAUSED" if halted else "ACTIVE",
            "open_positions": len(open_trades),
            "available_cash": float(cap.get("available_cash", 0.0) or 0.0),
            "bot_process_running": is_bot_running(),
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
        open_positions = int(cur.fetchone()[0])
        cur.execute("SELECT available_cash FROM capital ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        available_cash = float(row[0]) if row else 0.0
        conn.close()
        return {"bot_status": "UNKNOWN", "open_positions": open_positions, "available_cash": available_cash, "bot_process_running": is_bot_running()}
    except Exception:
        return {"bot_status": "UNKNOWN", "open_positions": 0, "available_cash": 0.0, "bot_process_running": is_bot_running()}




def load_entry_html(prefer_modular=True):
    modular = HTML_ROOT / "Trading Dashboard.html"
    stage3 = HTML_ROOT / "index.html"
    if prefer_modular and modular.exists():
        return modular.read_bytes(), "modular"
    return stage3.read_bytes(), "stage3"


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
        if self.path == "/api/open_positions":
            return self._json(200, {"positions": get_open_positions()})
        if self.path == "/" or self.path == "/index.html":
            page, mode = load_entry_html(prefer_modular=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Dashboard-Mode", mode)
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        if self.path == "/stage3":
            page, _ = load_entry_html(prefer_modular=False)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        rel_path = self.path.lstrip("/")
        if rel_path.startswith("static/"):
            rel_path = rel_path[len("static/"):]
        if rel_path:
            file_path = HTML_ROOT / rel_path
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                self.send_response(200)
                if file_path.suffix == ".jsx" or file_path.suffix == ".js":
                    mime = "text/javascript"
                elif file_path.suffix == ".css":
                    mime = "text/css"
                elif file_path.suffix == ".html":
                    mime = "text/html; charset=utf-8"
                else:
                    mime = "application/octet-stream"
                self.send_header("Content-Type", mime)
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
            ok, msg = start_bot_process()
            return self._json(200 if ok else 400, {"ok": ok, "message": f"Restart requested. {msg}"})

        if action == "refresh_scan":
            return self._json(200, {"ok": True, "message": "Scan refresh request received."})

        if action == "close_position":
            position_id = data.get("position_id")
            if position_id is None:
                return self._json(400, {"ok": False, "message": "position_id is required"})
            ok, msg = close_position(position_id)
            return self._json(200 if ok else 400, {"ok": ok, "message": msg})

        return self._json(400, {"error": f"Unknown action: {action}"})


WEB_DASHBOARD_PORT = 8125

if __name__ == "__main__":
    print(f"Starting HTML dashboard on http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server = HTTPServer(("0.0.0.0", WEB_DASHBOARD_PORT), Handler)
    print(f"Serving HTML dashboard at http://localhost:{WEB_DASHBOARD_PORT}", flush=True)
    server.serve_forever()