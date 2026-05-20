import http.client
import json
import sqlite3
import threading
from contextlib import contextmanager

import web_dashboard as wd


@contextmanager
def _run_server(handler_cls):
    server = wd.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _post(port, path, body, content_type="application/json"):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", path, body=body, headers={"Content-Type": content_type})
    response = conn.getresponse()
    payload = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(payload)


def _get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    payload = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(payload)


def test_control_start_bot_success(monkeypatch):
    monkeypatch.setattr(wd, "start_bot_process", lambda: (True, "Bot start requested."))

    with _run_server(wd.Handler) as server:
        status, body = _post(server.server_port, "/api/control", json.dumps({"action": "start_bot"}))

    assert status == 200
    assert body["ok"] is True
    assert "Bot start requested" in body["message"]


def test_control_rejects_invalid_json():
    with _run_server(wd.Handler) as server:
        status, body = _post(server.server_port, "/api/control", '{"action"', "application/json")

    assert status == 400
    assert body["ok"] is False
    assert "Invalid JSON" in body["message"]


def test_control_rejects_non_object_json():
    with _run_server(wd.Handler) as server:
        status, body = _post(server.server_port, "/api/control", "[]", "application/json")

    assert status == 400
    assert body["ok"] is False
    assert "JSON object" in body["message"]


def test_control_restart_aborts_if_bot_still_running(monkeypatch):
    monkeypatch.setattr(wd, "stop_bot_process", lambda: (True, "Bot stop requested."))
    monkeypatch.setattr(wd, "is_bot_running", lambda: True)

    with _run_server(wd.Handler) as server:
        status, body = _post(server.server_port, "/api/control", json.dumps({"action": "restart_bot"}))

    assert status == 400
    assert body["ok"] is False
    assert "restart aborted" in body["message"].lower()


def test_control_unknown_action_returns_400():
    with _run_server(wd.Handler) as server:
        status, body = _post(server.server_port, "/api/control", json.dumps({"action": "not_real"}))

    assert status == 400
    assert "Unknown action" in body.get("error", "")


def test_static_path_traversal_is_forbidden():
    with _run_server(wd.Handler) as server:
        status, body = _get(server.server_port, "/src/../../README.md")

    assert status == 403
    assert body["error"] == "forbidden"


def test_build_snapshot_prefers_db_adapter(monkeypatch):
    class FakeDB:
        @staticmethod
        def get_latest_capital():
            return {"available_cash": 123.45}

        @staticmethod
        def get_open_trades():
            return [{"id": 1}, {"id": 2}]

    class FakeRisk:
        trading_halted = True

    monkeypatch.setattr(wd, "db", FakeDB())
    monkeypatch.setattr(wd, "risk_manager", FakeRisk())
    monkeypatch.setattr(wd, "is_bot_running", lambda: True)

    snapshot = wd.build_snapshot()
    assert snapshot["bot_status"] == "PAUSED"
    assert snapshot["open_positions"] == 2
    assert snapshot["available_cash"] == 123.45
    assert snapshot["bot_process_running"] is True
    assert snapshot["snapshot_source"] == "live_db_adapter"


def test_build_snapshot_sqlite_fallback_success(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, status TEXT)")
    conn.execute("INSERT INTO trades (status) VALUES ('open')")
    conn.execute("INSERT INTO trades (status) VALUES ('closed')")
    conn.execute("CREATE TABLE capital (id INTEGER PRIMARY KEY, available_cash REAL)")
    conn.execute("INSERT INTO capital (available_cash) VALUES (999.5)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(wd, "db", None)
    monkeypatch.setattr(wd, "DB_PATH", db_file)
    monkeypatch.setattr(wd, "is_bot_running", lambda: False)

    snapshot = wd.build_snapshot()
    assert snapshot["snapshot_source"] == "sqlite_fallback"
    assert snapshot["open_positions"] == 1
    assert snapshot["available_cash"] == 999.5
    assert snapshot["bot_process_running"] is False


def test_build_snapshot_sqlite_exception_sets_degraded(monkeypatch):
    monkeypatch.setattr(wd, "db", None)
    monkeypatch.setattr(wd.sqlite3, "connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("db down")))
    monkeypatch.setattr(wd, "is_bot_running", lambda: False)

    snapshot = wd.build_snapshot()
    assert snapshot["snapshot_source"] == "error_fallback"
    assert snapshot["degraded"] is True
    assert snapshot["error_code"] == "SNAPSHOT_DB_UNAVAILABLE"
    assert snapshot["open_positions"] == 0
    assert snapshot["available_cash"] == 0.0
