"""
Deterministic tests for durable breakout-event identity: atomic claim,
fail-closed replay, restart-replay idempotency, broker reconciliation,
SUBMISSION_UNKNOWN never-resubmit, and trades.event_id uniqueness.

Covers the "Deterministic tests required" section of
Ron/Docs/CLAUDE_IMPLEMENTATION_HANDOFF_2026-07-17.md. Uses only a
disposable on-disk SQLite DB and fake/stub broker executors — never
IBKR live, never the production DB.

Run directly: python Scripts/test_breakout_event_durability.py
"""

import os
import sqlite3
import sys
import tempfile
import threading
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Offline shims (same recipe as test_broker_routing_safety.py) ───────────
_fernet_mod = types.ModuleType("cryptography.fernet")
_fernet_mod.InvalidToken = type("InvalidToken", (Exception,), {})
_fernet_mod.Fernet = type(
    "Fernet", (), {"__init__": lambda self, _key: None,
                    "decrypt": lambda self, value: value}
)
sys.modules.setdefault("cryptography", types.ModuleType("cryptography"))
sys.modules["cryptography.fernet"] = _fernet_mod

_dotenv_mod = types.ModuleType("dotenv")
_dotenv_mod.load_dotenv = lambda: None
sys.modules["dotenv"] = _dotenv_mod

_keyring_mod = types.ModuleType("keyring")
_keyring_mod.get_password = lambda *_args, **_kwargs: None
sys.modules["keyring"] = _keyring_mod


class _NoNetworkExchange:
    def __init__(self, *_args, **_kwargs):
        pass


_ccxt_mod = types.ModuleType("ccxt")
_ccxt_mod.kraken = _NoNetworkExchange
_ccxt_mod.coinbase = _NoNetworkExchange
sys.modules["ccxt"] = _ccxt_mod

_alpaca_mod = types.ModuleType("alpaca_trade_api")
_alpaca_mod.REST = _NoNetworkExchange
sys.modules["alpaca_trade_api"] = _alpaca_mod

import config

_tmp_dir = tempfile.TemporaryDirectory(prefix="breakout-event-durability-")
DB_PATH = os.path.join(_tmp_dir.name, "durability.db")
config.DB_PATH = DB_PATH
config.IBKR_ENABLED = False

import core.trade_executor as te_mod
from core.trade_executor import TradeExecutor
from core.breakout_receiver import BreakoutReceiver, ChecklistResult
from core.risk_manager import TradeApproval
from data.database import Database, db as real_db


# ── Shared fakes ─────────────────────────────────────────────────────────

class Patch:
    def __init__(self, obj, name, value):
        self.obj, self.name, self.value = obj, name, value

    def __enter__(self):
        self.had = hasattr(self.obj, self.name)
        self.old = getattr(self.obj, self.name, None)
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *_):
        if self.had:
            setattr(self.obj, self.name, self.old)
        else:
            delattr(self.obj, self.name)


class FakeBrokerManager:
    def __init__(self, enabled=None):
        self.enabled = {"alpaca": True, "kraken": True, **(enabled or {})}

    def get_broker(self, name):
        if name not in self.enabled:
            return None
        return {"name": name, "enabled": self.enabled[name]}

    def get_broker_balance(self, name):
        return {"balance": 10_000.0, "invested": 0.0, "available": 10_000.0}

    def update_broker_balance(self, *args):
        pass


class FakeRiskManager:
    def approve_trade(self, **kwargs):
        return TradeApproval(
            approved=True, reason="ok", quantity=1.0, position_value=100.0,
            stop_loss=95.0, take_profit=110.0, risk_amount=3.0,
        )

    def record_trade_result(self, *_args, **_kwargs):
        pass

    def manual_halt(self, reason):
        pass


class FakeStockBroker:
    def is_available(self):
        return True

    def submit_order(self, *args, **kwargs):
        return None


class FakeKrakenBroker:
    """Accepts every order, records calls, never actually hits ccxt."""

    def __init__(self, result=None):
        self.result = result
        self.submit_calls = []
        self.stop_calls = []

    def submit_order(self, *args, **kwargs):
        self.submit_calls.append((args, kwargs))
        if self.result is not None:
            return self.result
        return {
            "broker_order_id": f"KRAKEN-{len(self.submit_calls)}",
            "status": "closed", "filled_qty": 1.0, "filled_avg_price": 100.0,
        }

    def place_stop_order(self, *args, **kwargs):
        self.stop_calls.append((args, kwargs))
        return "STOP-1"

    def find_order_by_userref(self, userref, symbol=None):
        return None


class FakeKrakenBrokerRejects(FakeKrakenBroker):
    """Simulates a broker call whose outcome is unknown (returns None)."""

    def submit_order(self, *args, **kwargs):
        self.submit_calls.append((args, kwargs))
        return None


class FakeAlerts:
    def trade_opened(self, _payload):
        pass

    def trade_closed(self, _payload):
        pass


REQUIRED = dict(
    asset_class="crypto", direction="long", entry_price=100.0,
    current_price=100.0, move_pct=3.0, volume_spike=2.0,
    confidence=0.9, escalation=1, signal_source="breakout_scanner",
)


def _payload(event_id, symbol, **overrides):
    p = dict(REQUIRED)
    p["symbol"] = symbol
    p["event_id"] = event_id
    p["timestamp"] = datetime.now(timezone.utc).isoformat()
    p.update(overrides)
    return p


def _bypass_checklist(self, p, signal_age_sec):
    return ([ChecklistResult.ok("bypassed for test")], [])


def _make_executor(kraken_broker):
    manager = FakeBrokerManager({"kraken": True})
    risk = FakeRiskManager()
    executor = TradeExecutor(db_ref=real_db, risk_manager_ref=risk, broker_manager_ref=manager)
    executor._ibkr = None
    executor.alpaca = FakeStockBroker()
    executor.kraken = kraken_broker
    return executor


def _make_receiver(executor):
    receiver = BreakoutReceiver()
    receiver.set_executor(executor)
    return receiver


def _exec_ctx():
    return (
        Patch(config, "KRAKEN_ENABLED", True),
        Patch(config, "KRAKEN_PAPER_MODE", False),
        Patch(te_mod, "alert_manager", FakeAlerts()),
    )


class _MultiPatch:
    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.__enter__()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.__exit__(*exc)


def _trade(event_id, trade_id, symbol="TESTA/USD"):
    return {
        "trade_id": trade_id, "symbol": symbol, "asset_class": "crypto",
        "direction": "long", "entry_time": "2026-07-17T12:00:00",
        "entry_price": 100.0, "quantity": 1.0, "position_value": 100.0,
        "stop_loss": 95.0, "take_profit": 110.0, "signal_score": 0.9,
        "indicators": {}, "broker": "kraken", "broker_order_id": "ORD-X",
        "strategy_name": "test", "entry_timeframe": "5m", "event_id": event_id,
    }


# ── Tests ────────────────────────────────────────────────────────────────

def test_concurrent_claim_single_winner():
    db_a = Database(DB_PATH)
    db_b = Database(DB_PATH)
    event_id = "EVT-CONCURRENT-CLAIM"
    payload_hash = "fixed-hash-a"
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(20)

    def worker(i):
        d = db_a if i % 2 == 0 else db_b
        barrier.wait()
        r = d.claim_breakout_event(
            event_id, payload_hash, "BTC/USD", "long", "breakout_scanner", f"co-{i}"
        )
        with lock:
            results.append(r["status"])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("claimed") == 1, results
    assert results.count("replay_in_progress") == 19, results
    print("[1/9] 20 concurrent claims across 2 Database instances -> exactly 1 claimed, 19 fail closed")


def test_concurrent_receive_signal_one_trade_one_broker_call():
    kraken = FakeKrakenBroker()
    executor = _make_executor(kraken)
    receiver = _make_receiver(executor)
    event_id = "EVT-END-TO-END"
    symbol = "ETHDUR/USD"
    payload = _payload(event_id, symbol)

    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()
        r = receiver.receive_signal(dict(payload))
        with lock:
            results.append(r)

    with _MultiPatch(list(_exec_ctx()) + [Patch(BreakoutReceiver, "_run_checklist", _bypass_checklist)]):
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    accepted = [r for r in results if r.get("accepted")]
    assert len(accepted) == 1, [r.get("failure_class") for r in results]
    assert len(kraken.submit_calls) == 1, len(kraken.submit_calls)

    ev = real_db.get_breakout_event(event_id)
    assert ev["state"] == "ACCEPTED", ev
    trades = [t for t in (real_db.get_open_trades() or []) if t["symbol"] == symbol]
    assert len(trades) == 1, trades
    print("[2/9] 20 concurrent receive_signal calls (same event) -> 1 trade, 1 broker call, event ACCEPTED")

    return executor, receiver, kraken, event_id, symbol, payload, accepted[0]["trade_id"]


def test_replay_same_payload_returns_identical_response(executor, receiver, kraken, event_id, payload, trade_id):
    r1 = receiver.receive_signal(dict(payload))
    r2 = receiver.receive_signal(dict(payload))
    assert r1 == r2, (r1, r2)
    assert r1.get("trade_id") == trade_id
    assert len(kraken.submit_calls) == 1
    print("[3/9] replay of same event_id/payload -> identical stored response, no re-execution")


def test_replay_different_payload_conflict(receiver, kraken, event_id, payload):
    before_calls = len(kraken.submit_calls)
    conflicting = dict(payload)
    conflicting["current_price"] = payload["current_price"] + 5.0
    r = receiver.receive_signal(conflicting)
    assert r["accepted"] is False
    assert r["failure_class"] == "event_conflict", r
    assert len(kraken.submit_calls) == before_calls
    print("[4/9] replay of same event_id with different payload -> conflict, executor never called")


def test_restart_replay_idempotent(event_id, payload):
    kraken2 = FakeKrakenBroker()
    executor2 = _make_executor(kraken2)
    receiver2 = _make_receiver(executor2)

    r = receiver2.receive_signal(dict(payload))
    assert r["accepted"] is True
    assert len(kraken2.submit_calls) == 0
    print("[5/9] fresh receiver/executor objects (simulated restart) replay terminal event -> no new broker call")


def test_timeout_then_reconcile_finds_one_order():
    from core.event_identity import hash_breakout_payload, derive_client_order_id

    event_id = "EVT-TIMEOUT-RECONCILE"
    symbol = "SOLDUR/USD"
    payload = _payload(event_id, symbol)
    payload_hash = hash_breakout_payload(payload)
    client_order_id = derive_client_order_id(event_id)

    claim = real_db.claim_breakout_event(
        event_id, payload_hash, symbol, "long", "breakout_scanner", client_order_id
    )
    assert claim["status"] == "claimed"
    assert real_db.mark_breakout_event_submitting(event_id) is True
    # Simulate: broker accepted the order but the process died/timed out before
    # the response was persisted. Nothing else touches breakout_event_execution.

    found_order = {"broker_order_id": "RECONCILED-1", "status": "closed",
                    "filled_qty": 1.0, "filled_avg_price": 100.0}

    class ReconcileKraken(FakeKrakenBroker):
        def find_order_by_userref(self, userref, symbol=None):
            return found_order

    kraken = ReconcileKraken()
    executor = _make_executor(kraken)
    executor.alpaca = None  # force fallthrough past the alpaca lookup

    counts = executor.reconcile_unresolved_breakout_events()
    assert counts["checked"] >= 1
    assert counts["confirmed_accepted"] >= 1
    assert counts["still_unresolved"] == 0, counts

    ev = real_db.get_breakout_event(event_id)
    assert ev["state"] == "ACCEPTED", ev
    assert ev["broker_order_id"] == "RECONCILED-1"

    # Replay must not re-submit — event is now terminal.
    receiver = _make_receiver(executor)
    r = receiver.receive_signal(dict(payload))
    assert len(kraken.submit_calls) == 0
    assert r.get("accepted") is True
    print("[6/9] SUBMITTING event with lost response -> reconciliation finds broker order, replay does not resubmit")


def test_submission_unknown_never_resubmits():
    kraken = FakeKrakenBrokerRejects()
    executor = _make_executor(kraken)
    receiver = _make_receiver(executor)
    event_id = "EVT-SUBMISSION-UNKNOWN"
    symbol = "ADADUR/USD"
    payload = _payload(event_id, symbol)

    with _MultiPatch(list(_exec_ctx()) + [Patch(BreakoutReceiver, "_run_checklist", _bypass_checklist)]):
        r1 = receiver.receive_signal(dict(payload))

    assert r1["accepted"] is False
    assert r1["failure_class"] == "submission_unknown", r1
    assert len(kraken.submit_calls) == 1

    ev = real_db.get_breakout_event(event_id)
    assert ev["state"] == "SUBMISSION_UNKNOWN", ev

    # Replay must fail closed, never re-submit.
    r2 = receiver.receive_signal(dict(payload))
    assert r2["accepted"] is False
    assert r2["failure_class"] == "event_in_progress", r2
    assert len(kraken.submit_calls) == 1, "SUBMISSION_UNKNOWN must never trigger a second broker call"
    print("[7/9] SUBMISSION_UNKNOWN event -> replay fails closed, never auto-resubmits")


def test_trades_event_id_uniqueness():
    dup_event = "EVT-TRADE-UNIQUE"
    assert real_db.open_trade(_trade(dup_event, "TR-UNIQUE-1"))["status"] == "inserted"
    raised = False
    try:
        real_db.open_trade(_trade(dup_event, "TR-UNIQUE-2"))
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "second trade with duplicate event_id (different trade_id) must violate the partial unique index"
    print("[8/9] trades.event_id partial unique index enforced across distinct trade_id rows")


def test_crash_failpoints():
    from core.event_identity import hash_breakout_payload, derive_client_order_id

    kraken = FakeKrakenBroker()
    executor = _make_executor(kraken)
    receiver = _make_receiver(executor)

    # Failpoint 1: crash after claim, before SUBMITTING.
    ev1 = "EVT-CRASH-AFTER-CLAIM"
    p1 = _payload(ev1, "CRASH1/USD")
    h1 = hash_breakout_payload(p1)
    c1 = derive_client_order_id(ev1)
    assert real_db.claim_breakout_event(ev1, h1, "CRASH1/USD", "long", "breakout_scanner", c1)["status"] == "claimed"
    r1 = receiver.receive_signal(dict(p1))
    assert r1["accepted"] is False and r1["failure_class"] == "event_in_progress"
    assert len(kraken.submit_calls) == 0

    # Failpoint 2: crash after SUBMITTING, before any terminal state.
    ev2 = "EVT-CRASH-AFTER-SUBMITTING"
    p2 = _payload(ev2, "CRASH2/USD")
    h2 = hash_breakout_payload(p2)
    c2 = derive_client_order_id(ev2)
    real_db.claim_breakout_event(ev2, h2, "CRASH2/USD", "long", "breakout_scanner", c2)
    real_db.mark_breakout_event_submitting(ev2)
    r2 = receiver.receive_signal(dict(p2))
    assert r2["accepted"] is False and r2["failure_class"] == "event_in_progress"
    assert len(kraken.submit_calls) == 0

    # Failpoint 3: crash after broker acceptance, before a trades row exists
    # (e.g. reconciliation found the order but no local trade could be
    # reconstructed). Replay must return the terminal state, never resubmit.
    ev3 = "EVT-CRASH-ACCEPTED-NO-TRADE-ROW"
    p3 = _payload(ev3, "CRASH3/USD")
    h3 = hash_breakout_payload(p3)
    c3 = derive_client_order_id(ev3)
    real_db.claim_breakout_event(ev3, h3, "CRASH3/USD", "long", "breakout_scanner", c3)
    real_db.mark_breakout_event_submitting(ev3)
    real_db.finish_breakout_event(ev3, "ACCEPTED", broker_order_id="ORD-NO-ROW")
    r3 = receiver.receive_signal(dict(p3))
    assert r3["accepted"] is True
    assert len(kraken.submit_calls) == 0

    # Failpoint 4: crash after the trades row is persisted but before the
    # breakout_event_execution row is finalized (still SUBMITTING). Replay
    # must still fail closed rather than trusting the pre-existing trade row.
    ev4 = "EVT-CRASH-TRADE-ROW-BEFORE-FINALIZE"
    p4 = _payload(ev4, "CRASH4/USD")
    h4 = hash_breakout_payload(p4)
    c4 = derive_client_order_id(ev4)
    real_db.claim_breakout_event(ev4, h4, "CRASH4/USD", "long", "breakout_scanner", c4)
    real_db.mark_breakout_event_submitting(ev4)
    real_db.open_trade(_trade(ev4, "TR-CRASH4", symbol="CRASH4/USD"))
    r4 = receiver.receive_signal(dict(p4))
    assert r4["accepted"] is False and r4["failure_class"] == "event_in_progress"
    assert len(kraken.submit_calls) == 0

    print("[9/9] 4 crash failpoints (after-claim, after-SUBMITTING, accepted-no-row, row-before-finalize) all fail closed")


def run():
    for suffix in ("", "-shm", "-wal"):
        try:
            os.remove(DB_PATH + suffix)
        except FileNotFoundError:
            pass
    real_db._init_db()

    test_concurrent_claim_single_winner()
    executor, receiver, kraken, event_id, symbol, payload, trade_id = \
        test_concurrent_receive_signal_one_trade_one_broker_call()
    test_replay_same_payload_returns_identical_response(executor, receiver, kraken, event_id, payload, trade_id)
    test_replay_different_payload_conflict(receiver, kraken, event_id, payload)
    test_restart_replay_idempotent(event_id, payload)
    test_timeout_then_reconcile_finds_one_order()
    test_submission_unknown_never_resubmits()
    test_trades_event_id_uniqueness()
    test_crash_failpoints()

    print("9/9 breakout event durability checks passed")


if __name__ == "__main__":
    run()
