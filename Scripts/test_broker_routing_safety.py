"""Deterministic, offline tests for BrokerManager Patch 1 routing safety."""

import ast
import json
import os
import sys
import tempfile
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep this focused harness runnable in stripped CI/WSL environments without
# importing Windows-only wheels or constructing real broker clients.
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

# All module-level database initialization caused by imports below is routed to
# a disposable path, never data/trading_bot.db.
_tmp_dir = tempfile.TemporaryDirectory(prefix="broker-routing-tests-")
config.DB_PATH = os.path.join(_tmp_dir.name, "routing.db")
config.IBKR_ENABLED = False

import core.trade_executor as te_mod
from core.risk_manager import TradeApproval
from core.trade_executor import TradeExecutor


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
        self.balance_calls = []
        self.update_calls = []

    def get_broker(self, name):
        if name not in self.enabled:
            return None
        return {"name": name, "enabled": self.enabled[name]}

    def get_broker_balance(self, name):
        self.balance_calls.append(name)
        return {"balance": 10_000.0, "invested": 0.0, "available": 10_000.0}

    def update_broker_balance(self, *args):
        self.update_calls.append(args)


class FakeDB:
    def __init__(self):
        self.opened = []
        self.order_updates = []
        self.state = {}

    def open_trade(self, record):
        self.opened.append(record)
        return {"status": "inserted"}

    def get_latest_capital(self):
        return None

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def update_trade_order_ids(self, trade_id, stop_order_id=None, tp_order_id=None):
        self.order_updates.append((trade_id, stop_order_id, tp_order_id))


class AtomicFakeDB(FakeDB):
    def __init__(self, fail_second=False):
        super().__init__()
        self.fail_second = fail_second
        self.atomic_rollback_state = None

    @contextmanager
    def _conn(self):
        pending = []
        owner = self

        class Conn:
            def execute(self, _sql, params):
                pending.append(params)
                if owner.fail_second and len(pending) == 2:
                    raise RuntimeError("simulated second marker failure")

        try:
            yield Conn()
        except Exception:
            self.atomic_rollback_state = dict(self.state)
            raise
        else:
            for key, value, _updated in pending:
                self.state[key] = json.loads(value)


class FailingMarkerDB(FakeDB):
    def set_state(self, _key, _value):
        raise RuntimeError("simulated marker write failure")


class FakeRiskManager:
    def __init__(self, decisions=None):
        self.decisions = decisions or {}
        self.calls = []
        self.halt_calls = []

    def approve_trade(self, **kwargs):
        broker = kwargs["broker_name"]
        self.calls.append(broker)
        decision = self.decisions.get(broker, True)
        if isinstance(decision, TradeApproval):
            return decision
        if decision is False:
            return TradeApproval(approved=False, reason=f"No available cash on {broker}")
        return TradeApproval(
            approved=True,
            reason="ok",
            quantity=2.0,
            position_value=200.0,
            stop_loss=95.0,
            take_profit=110.0,
            risk_amount=3.0,
        )

    def record_trade_result(self, *_args, **_kwargs):
        pass

    def manual_halt(self, reason):
        self.halt_calls.append(reason)


class FakeStockBroker:
    def __init__(self, result=None, available=True, close_result=True):
        self.result = result if result is not None else {
            "broker_order_id": "ORDER-1",
            "status": "filled",
            "filled_qty": 2.0,
            "filled_avg_price": 100.0,
        }
        self.available = available
        self.close_result = close_result
        self.submit_calls = []
        self.close_calls = []

    def is_available(self):
        return self.available

    def submit_order(self, *args, **kwargs):
        self.submit_calls.append((args, kwargs))
        return dict(self.result) if isinstance(self.result, dict) else self.result

    def close_position(self, symbol):
        self.close_calls.append(symbol)
        return self.close_result


class FakeKrakenBroker:
    def __init__(self, manager):
        self.manager = manager
        self.submit_calls = []
        self.stop_calls = []

    def submit_order(self, *args, **kwargs):
        self.submit_calls.append((args, kwargs))
        # Simulate an operator disabling future entries immediately after the
        # entry reaches Kraken. Protection for this exposure must still run.
        self.manager.enabled["kraken"] = False
        return {
            "broker_order_id": "KRAKEN-1", "status": "closed",
            "filled_qty": 2.0, "filled_avg_price": 100.0,
        }

    def place_stop_order(self, *args, **kwargs):
        self.stop_calls.append((args, kwargs))
        return "STOP-1"


class FakeAlerts:
    def trade_opened(self, _payload):
        pass

    def trade_closed(self, _payload):
        pass


def stock_signal(symbol="AAPL"):
    return SimpleNamespace(
        symbol=symbol,
        direction="long",
        asset_class="stock",
        current_price=100.0,
        score=0.9,
        indicators={"strategy_name": "manual"},
    )


def short_stock_signal(symbol="AAPL"):
    value = stock_signal(symbol)
    value.direction = "short"
    return value


def crypto_signal(symbol="BTC/USD"):
    return SimpleNamespace(
        symbol=symbol,
        direction="long",
        asset_class="crypto",
        current_price=100.0,
        score=0.9,
        indicators={"strategy_name": "manual"},
    )


def make_executor(manager, risk, ibkr=None, alpaca=None):
    with Patch(config, "IBKR_ENABLED", False):
        executor = TradeExecutor(
            db_ref=FakeDB(), risk_manager_ref=risk, broker_manager_ref=manager
        )
    executor._ibkr = ibkr
    executor.alpaca = alpaca or FakeStockBroker()
    return executor


def execute(executor, signal=None):
    with Patch(te_mod, "_stock_entries_allowed_now", lambda: True), \
         Patch(te_mod, "alert_manager", FakeAlerts()), \
         Patch(te_mod, "settlement_tracker", None):
        return executor.execute_signal(signal or stock_signal())


def safe_ibkr_zero_result(**changes):
    result = {
        "status": "not_submitted", "filled_qty": 0.0,
        "filled_avg_price": 0.0, "safe_to_fallback": True,
        "order_submitted": False, "broker_order_id": None,
        "child_orders": {},
    }
    result.update(changes)
    return result


def test_ibkr_display_only_selects_and_approves_alpaca():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(available=True)
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", False):
        assert execute(executor)
    assert risk.calls == ["alpaca"]
    assert len(alpaca.submit_calls) == 1
    assert not ibkr.submit_calls


def test_ibkr_trade_enabled_approval_and_execution_match():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(available=True)
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor)
    assert risk.calls == ["ibkr"]
    assert len(ibkr.submit_calls) == 1
    assert not alpaca.submit_calls


def test_ibkr_unavailable_selects_alpaca_before_submission():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(available=False)
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor)
    assert risk.calls == ["alpaca"]
    assert len(alpaca.submit_calls) == 1
    assert not ibkr.submit_calls


def test_proven_zero_exposure_ibkr_failure_gets_fresh_alpaca_approval():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(result=safe_ibkr_zero_result(
        status="definitive_no_exposure"
    ))
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor)
    assert risk.calls == ["ibkr", "alpaca"]
    assert len(ibkr.submit_calls) == 1
    assert len(alpaca.submit_calls) == 1


def test_ambiguous_pending_partial_rejected_or_canceled_never_falls_back():
    cases = [
        None,
        {"status": "submission_uncertain", "filled_qty": 0.0},
        {"status": "pending", "filled_qty": 0.0},
        {"status": "partiallyfilled", "filled_qty": 1.0},
        {"status": "rejected", "filled_qty": 0.0},
        {"status": "cancelled", "filled_qty": 0.0},
    ]
    for result in cases:
        manager = FakeBrokerManager()
        risk = FakeRiskManager()
        ibkr = FakeStockBroker(result=result)
        # FakeStockBroker uses its default fill for None, so override submit.
        if result is None:
            ibkr.submit_order = lambda *_args, **_kwargs: None
        alpaca = FakeStockBroker()
        executor = make_executor(manager, risk, ibkr, alpaca)
        with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
            execute(executor)
        assert risk.calls == ["ibkr"], result
        assert not alpaca.submit_calls, result


def test_ibkr_submission_uncertain_persists_marker_and_halts_without_trade():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    result = {
        "status": "submission_uncertain", "filled_qty": 0.0,
        "broker_order_id": "IU1", "order_submitted": True,
        "child_orders": {"stop": {"order_id": "S1", "status": "PendingSubmit"}},
    }
    executor = make_executor(manager, risk, FakeStockBroker(result=result), FakeStockBroker())
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor) is None
    assert executor._db.opened == []
    assert executor._db.state["ibkr_reconciliation_order_IU1"]["status"] == "submission_uncertain"
    assert risk.halt_calls


def test_ibkr_pending_zero_fill_persists_marker_and_halts_without_trade():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    result = {
        "status": "pendingsubmit", "filled_qty": 0.0,
        "broker_order_id": "IP1", "order_submitted": True,
    }
    executor = make_executor(manager, risk, FakeStockBroker(result=result), FakeStockBroker())
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor) is None
    assert executor._db.opened == []
    assert "ibkr_reconciliation_symbol_AAPL" in executor._db.state
    assert risk.halt_calls


def test_ibkr_partial_fill_tracks_only_confirmed_exposure_and_never_falls_back():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    result = {
        "status": "partiallyfilled", "filled_qty": 0.5,
        "filled_avg_price": 101.0, "requested_qty": 2.0,
        "broker_order_id": "IPART", "order_submitted": True,
        "child_orders": {
            "stop": {"order_id": "S2", "status": "PreSubmitted"},
            "take_profit": {"order_id": "T2", "status": "PreSubmitted"},
        },
    }
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, FakeStockBroker(result=result), alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor) is None
    assert len(executor._db.opened) == 1
    trade = executor._db.opened[0]
    assert trade["quantity"] == 0.5
    assert trade["position_value"] == 50.5
    assert trade["quantity"] != 2.0
    assert trade["indicators"]["ibkr_child_orders"]["stop"]["order_id"] == "S2"
    assert not alpaca.submit_calls
    assert risk.halt_calls


def test_ibkr_definitive_reject_cancel_expire_create_no_trade_or_fallback():
    for status in ("rejected", "cancelled", "canceled", "expired"):
        manager = FakeBrokerManager()
        risk = FakeRiskManager()
        alpaca = FakeStockBroker()
        result = {
            "status": status, "filled_qty": 0.0, "filled_avg_price": 0.0,
            "broker_order_id": f"I-{status}",
        }
        executor = make_executor(manager, risk, FakeStockBroker(result=result), alpaca)
        with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
            assert execute(executor) is None
        assert executor._db.opened == []
        assert not alpaca.submit_calls
        assert not risk.halt_calls


def test_ibkr_confirmed_full_fill_records_actual_quantity_and_value():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    result = {
        "status": "filled", "filled_qty": 0.75, "filled_avg_price": 102.0,
        "requested_qty": 2.0, "broker_order_id": "IFULL",
    }
    executor = make_executor(manager, risk, FakeStockBroker(result=result), FakeStockBroker())
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor)
    assert len(executor._db.opened) == 1
    trade = executor._db.opened[0]
    assert trade["quantity"] == 0.75
    assert trade["entry_price"] == 102.0
    assert trade["position_value"] == 76.5


def test_ibkr_to_alpaca_short_fallback_reruns_shortability():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(result=safe_ibkr_zero_result())
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    calls = []

    def can_short(symbol, broker):
        calls.append((symbol, broker))
        return True

    with Patch(config, "IBKR_ENABLED", True), \
         Patch(config, "IBKR_TRADE_ENABLED", True), \
         Patch(te_mod.exchange_capabilities, "can_short", can_short):
        assert execute(executor, short_stock_signal())
    assert calls == [("AAPL", "ibkr"), ("AAPL", "alpaca")]
    assert risk.calls == ["ibkr", "alpaca"]
    assert len(alpaca.submit_calls) == 1


def test_non_shortable_alpaca_fallback_submits_no_order():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    ibkr = FakeStockBroker(result=safe_ibkr_zero_result())
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    calls = []

    def can_short(symbol, broker):
        calls.append((symbol, broker))
        return broker == "ibkr"

    with Patch(config, "IBKR_ENABLED", True), \
         Patch(config, "IBKR_TRADE_ENABLED", True), \
         Patch(te_mod.exchange_capabilities, "can_short", can_short):
        assert execute(executor, short_stock_signal()) is None
    assert calls == [("AAPL", "ibkr"), ("AAPL", "alpaca")]
    assert risk.calls == ["ibkr"]
    assert not alpaca.submit_calls


def test_manual_resume_does_not_bypass_ibkr_symbol_marker():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, None, alpaca)
    executor._db.state["ibkr_reconciliation_symbol_AAPL"] = {
        "reconciliation_required": True,
    }
    with Patch(config, "IBKR_ENABLED", False), Patch(config, "IBKR_TRADE_ENABLED", False):
        assert execute(executor) is None
    assert risk.calls == []
    assert not alpaca.submit_calls


def test_same_ibkr_order_handled_twice_creates_one_provisional_trade():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    executor = make_executor(manager, risk)
    result = {
        "status": "partiallyfilled", "filled_qty": 0.5,
        "filled_avg_price": 101.0, "requested_qty": 2.0,
        "broker_order_id": "IDEMP-1", "order_submitted": True,
        "child_orders": {},
    }
    approval = risk.approve_trade(broker_name="ibkr")
    executor._handle_ibkr_reconciliation_required(
        stock_signal(), approval, result, has_confirmed_exposure=True
    )
    executor._handle_ibkr_reconciliation_required(
        stock_signal(), approval, result, has_confirmed_exposure=True
    )
    assert len(executor._db.opened) == 1
    assert len(executor._db.state) == 2
    assert len(risk.halt_calls) == 2


def test_ibkr_marker_transaction_rolls_back_pair_before_fallback():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    executor = make_executor(manager, risk)
    executor._db = AtomicFakeDB(fail_second=True)
    result = {
        "status": "pending", "filled_qty": 0.0, "filled_avg_price": 0.0,
        "broker_order_id": "ATOMIC-1", "order_submitted": True,
        "child_orders": {},
    }
    approval = risk.approve_trade(broker_name="ibkr")
    executor._handle_ibkr_reconciliation_required(
        stock_signal(), approval, result, has_confirmed_exposure=False
    )
    assert executor._db.atomic_rollback_state == {}
    assert set(executor._db.state) == {
        "ibkr_reconciliation_symbol_AAPL",
        "ibkr_reconciliation_order_ATOMIC-1",
    }


def test_ibkr_marker_write_failure_still_halts():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    executor = make_executor(manager, risk)
    executor._db = FailingMarkerDB()
    result = {
        "status": "pending", "filled_qty": 0.0, "filled_avg_price": 0.0,
        "broker_order_id": "FAIL-1", "order_submitted": True,
        "child_orders": {},
    }
    approval = risk.approve_trade(broker_name="ibkr")
    executor._handle_ibkr_reconciliation_required(
        stock_signal(), approval, result, has_confirmed_exposure=False
    )
    assert risk.halt_calls


def test_contradictory_safe_fallback_claims_reconcile_instead():
    contradictions = [
        {"order_submitted": True},
        {"broker_order_id": "CONTRADICT-1"},
        {"child_orders": {"stop": {"status": "Submitted", "transmit": False}}},
        {"child_orders": {"take_profit": {"status": "not_submitted", "transmit": True}}},
    ]
    for changes in contradictions:
        manager = FakeBrokerManager()
        risk = FakeRiskManager()
        alpaca = FakeStockBroker()
        executor = make_executor(
            manager, risk, FakeStockBroker(result=safe_ibkr_zero_result(**changes)), alpaca
        )
        with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
            assert execute(executor) is None
        assert not alpaca.submit_calls
        assert risk.halt_calls
        assert executor._db.opened == []


def test_invalid_ibkr_fill_values_never_persist_trade_or_fallback():
    invalid_cases = [
        {"filled_qty": float("nan"), "filled_avg_price": 100.0},
        {"filled_qty": float("inf"), "filled_avg_price": 100.0},
        {"filled_qty": -1.0, "filled_avg_price": 100.0},
        {"filled_qty": "bad", "filled_avg_price": 100.0},
        {"filled_qty": 1.0, "filled_avg_price": float("nan")},
        {"filled_qty": 1.0, "filled_avg_price": float("inf")},
        {"filled_qty": 1.0, "filled_avg_price": -5.0},
        {"filled_qty": 1.0, "filled_avg_price": "bad"},
    ]
    for index, values in enumerate(invalid_cases):
        manager = FakeBrokerManager()
        risk = FakeRiskManager()
        alpaca = FakeStockBroker()
        result = {
            "status": "filled", "broker_order_id": f"INVALID-{index}",
            "safe_to_fallback": True, "order_submitted": False,
            "child_orders": {}, **values,
        }
        executor = make_executor(manager, risk, FakeStockBroker(result=result), alpaca)
        with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
            assert execute(executor) is None
        assert executor._db.opened == []
        assert not alpaca.submit_calls
        assert risk.halt_calls
        marker = executor._db.state[f"ibkr_reconciliation_order_INVALID-{index}"]
        assert marker["confirmed_filled_qty"] is None
        assert marker["confirmed_filled_avg_price"] is None


def test_alpaca_fallback_approval_rejects_without_order():
    manager = FakeBrokerManager()
    risk = FakeRiskManager({"alpaca": False})
    ibkr = FakeStockBroker(result=safe_ibkr_zero_result())
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, ibkr, alpaca)
    with Patch(config, "IBKR_ENABLED", True), Patch(config, "IBKR_TRADE_ENABLED", True):
        assert execute(executor) is None
    assert risk.calls == ["ibkr", "alpaca"]
    assert not alpaca.submit_calls


def test_disabled_entry_broker_cannot_receive_new_order():
    manager = FakeBrokerManager({"alpaca": False})
    risk = FakeRiskManager()
    alpaca = FakeStockBroker()
    executor = make_executor(manager, risk, None, alpaca)
    with Patch(config, "IBKR_ENABLED", False), Patch(config, "IBKR_TRADE_ENABLED", False):
        assert execute(executor) is None
    assert risk.calls == []
    assert not alpaca.submit_calls


def test_disabled_entry_broker_can_close_existing_position():
    manager = FakeBrokerManager({"alpaca": False})
    risk = FakeRiskManager()
    alpaca = FakeStockBroker(close_result=True)
    executor = make_executor(manager, risk, None, alpaca)
    trade = {
        "trade_id": "T1", "symbol": "AAPL", "direction": "long",
        "quantity": 1.0, "entry_price": 100.0, "asset_class": "stock",
        "broker": "alpaca", "position_value": 100.0, "strategy_name": "manual",
    }
    # Stop after proving close routing remains available; downstream trade
    # accounting is outside Patch 1 and intentionally not exercised here.
    executor._db.get_latest_capital = lambda: None
    executor._db.close_trade = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("close routing proved")
    )
    try:
        executor.close_trade(trade, 101.0, "test")
    except RuntimeError as exc:
        assert str(exc) == "close routing proved"
    assert alpaca.close_calls == ["AAPL"]


def test_disabled_entry_broker_can_still_protect_submitted_position():
    manager = FakeBrokerManager({"kraken": True})
    risk = FakeRiskManager()
    executor = make_executor(manager, risk)
    kraken = FakeKrakenBroker(manager)
    executor.kraken = kraken
    with Patch(config, "KRAKEN_ENABLED", True), \
         Patch(config, "KRAKEN_PAPER_MODE", False), \
         Patch(te_mod, "alert_manager", FakeAlerts()):
        assert executor.execute_signal(crypto_signal())
    assert len(kraken.submit_calls) == 1
    assert manager.enabled["kraken"] is False
    assert len(kraken.stop_calls) == 1


def test_injected_broker_manager_is_used():
    manager = FakeBrokerManager()
    risk = FakeRiskManager()
    executor = make_executor(manager, risk, None, FakeStockBroker())
    with Patch(config, "IBKR_ENABLED", False), Patch(config, "IBKR_TRADE_ENABLED", False):
        assert execute(executor)
    assert manager.balance_calls == ["alpaca"]
    assert len(manager.update_calls) == 1


def test_bot_engine_uses_shared_broker_manager_singleton():
    tree = ast.parse((ROOT / "bot_engine.py").read_text(encoding="utf-8"))
    imported_singleton = False
    assigned_singleton = False
    constructs_manager = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.broker_manager":
            imported_singleton |= any(alias.name == "broker_manager" for alias in node.names)
            constructs_manager |= any(alias.name == "BrokerManager" for alias in node.names)
        if isinstance(node, ast.Assign):
            if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
                    and node.targets[0].attr == "broker_manager"):
                assigned_singleton |= isinstance(node.value, ast.Name) and node.value.id == "broker_manager"
                constructs_manager |= isinstance(node.value, ast.Call)
    assert imported_singleton
    assert assigned_singleton
    assert not constructs_manager


def run_case(fn):
    try:
        fn()
        print(f"PASS  {fn.__name__}")
        return True
    except Exception as exc:
        print(f"FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
        return False


if __name__ == "__main__":
    cases = [
        test_ibkr_display_only_selects_and_approves_alpaca,
        test_ibkr_trade_enabled_approval_and_execution_match,
        test_ibkr_unavailable_selects_alpaca_before_submission,
        test_proven_zero_exposure_ibkr_failure_gets_fresh_alpaca_approval,
        test_ambiguous_pending_partial_rejected_or_canceled_never_falls_back,
        test_ibkr_submission_uncertain_persists_marker_and_halts_without_trade,
        test_ibkr_pending_zero_fill_persists_marker_and_halts_without_trade,
        test_ibkr_partial_fill_tracks_only_confirmed_exposure_and_never_falls_back,
        test_ibkr_definitive_reject_cancel_expire_create_no_trade_or_fallback,
        test_ibkr_confirmed_full_fill_records_actual_quantity_and_value,
        test_ibkr_to_alpaca_short_fallback_reruns_shortability,
        test_non_shortable_alpaca_fallback_submits_no_order,
        test_manual_resume_does_not_bypass_ibkr_symbol_marker,
        test_same_ibkr_order_handled_twice_creates_one_provisional_trade,
        test_ibkr_marker_transaction_rolls_back_pair_before_fallback,
        test_ibkr_marker_write_failure_still_halts,
        test_contradictory_safe_fallback_claims_reconcile_instead,
        test_invalid_ibkr_fill_values_never_persist_trade_or_fallback,
        test_alpaca_fallback_approval_rejects_without_order,
        test_disabled_entry_broker_cannot_receive_new_order,
        test_disabled_entry_broker_can_close_existing_position,
        test_disabled_entry_broker_can_still_protect_submitted_position,
        test_injected_broker_manager_is_used,
        test_bot_engine_uses_shared_broker_manager_singleton,
    ]
    results = [run_case(case) for case in cases]
    print(f"\n{sum(results)}/{len(results)} passed")
    raise SystemExit(0 if all(results) else 1)
