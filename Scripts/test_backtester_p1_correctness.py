"""Deterministic regression tests for the approved P1-B/P1-C fixes."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import intelligence.backtester as bt_module
from intelligence.backtester import Backtester, TF_CONFIG
from intelligence.optimizer import StrategyOptimizer


def _frame(rows=48, price=100.0):
    index = pd.date_range("2026-01-02", periods=rows, freq="1h", tz="UTC")
    return pd.DataFrame({
        "open": price,
        "high": price + 1.0,
        "low": price - 1.0,
        "close": price,
        "volume": 1000.0,
    }, index=index)


class _Ticker:
    def __init__(self, owner):
        self.owner = owner

    def history(self, **_kwargs):
        self.owner.calls += 1
        return self.owner.frame.copy()


class _YF:
    def __init__(self, frame):
        self.frame = frame
        self.calls = 0

    def Ticker(self, _symbol):
        return _Ticker(self)


class _Strategy:
    stop_loss_pct = 50.0
    take_profit_pct = 50.0
    params = {}

    def __init__(self, direction="none"):
        self.direction = direction
        self.calls = 0

    def analyze(self, _symbol, _window, _condition):
        self.calls += 1
        if self.calls != 1:
            return None
        return SimpleNamespace(
            direction=self.direction,
            score=0.9,
            metadata={},
            stop_loss_pct=None,
            take_profit_pct=None,
        )

    def check_custom_exit(self, *_args, **_kwargs):
        return None


def _bare_backtester(frame=None):
    bt = Backtester.__new__(Backtester)
    bt.starting_capital = 10_000.0
    bt._candle_cache = {}
    bt.yf = _YF(_frame() if frame is None else frame)
    bt.ccxt = None
    bt.ta = None
    return bt


def test_stock_15m_annualization_uses_regular_session_count():
    assert TF_CONFIG["15m"]["bars_per_day"] == 26
    assert TF_CONFIG["15m"]["annualise"] == 252 * 26
    assert TF_CONFIG["15m"]["annualise_crypto"] == 365 * 96


def test_starting_capital_is_not_falsy_defaulted_and_rejects_invalid():
    bt = _bare_backtester()
    assert bt._resolve_starting_capital(None) == 10_000.0
    for value in (0, -1, float("nan"), float("inf"), "bad"):
        try:
            bt._resolve_starting_capital(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid capital accepted: {value!r}")


def test_poisoned_none_memory_cache_retries_fetch_and_recovers():
    bt = _bare_backtester()
    key = ("TEST", 30, "1h")
    bt._candle_cache[key] = None
    with patch.object(bt_module, "_candle_store", None):
        result = bt.fetch_history("TEST", 30, "1h")
    assert result is not None
    assert bt.yf.calls == 1
    assert isinstance(bt._candle_cache[key], pd.DataFrame)


def test_invalid_memory_cache_is_revalidated_before_use():
    valid = _frame()
    invalid = valid.copy()
    invalid.iloc[0, invalid.columns.get_loc("high")] = 1.0
    bt = _bare_backtester(valid)
    key = ("TEST", 30, "1h")
    bt._candle_cache[key] = invalid
    with patch.object(bt_module, "_candle_store", None):
        result = bt.fetch_history("TEST", 30, "1h")
    assert result is not None
    assert bt.yf.calls == 1, "invalid cache must fall through to a clean fetch"
    assert float(result.iloc[0]["high"]) == 101.0


def test_param_override_restores_absent_key_on_success_and_exception():
    key = "__p1_absent_override_test__"
    config.SIGNAL_TUNING.pop(key, None)
    frame = _frame()
    bt = _bare_backtester(frame)
    strategy = _Strategy()
    bt.fetch_history = lambda *_a, **_k: frame
    bt._load_strategy = lambda _name: strategy

    def successful(*_args, **_kwargs):
        assert config.SIGNAL_TUNING[key] == 123
        return "ok"

    bt._simulate = successful
    assert bt.run_strategy("TEST", "fake", param_overrides={key: 123}) == "ok"
    assert key not in config.SIGNAL_TUNING

    def failing(*_args, **_kwargs):
        assert config.SIGNAL_TUNING[key] == 456
        raise RuntimeError("forced")

    bt._simulate = failing
    try:
        bt.run_strategy("TEST", "fake", param_overrides={key: 456})
    except RuntimeError:
        pass
    else:
        raise AssertionError("forced simulation error was swallowed")
    assert key not in config.SIGNAL_TUNING


def test_param_overrides_are_process_serialized():
    key = "__p1_concurrent_override_test__"
    config.SIGNAL_TUNING.pop(key, None)
    frame = _frame()
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    seen = []

    def make_bt(expected, first=False):
        bt = _bare_backtester(frame)
        bt.fetch_history = lambda *_a, **_k: frame
        bt._load_strategy = lambda _name: _Strategy()

        def simulate(*_args, **_kwargs):
            seen.append(config.SIGNAL_TUNING[key])
            if first:
                first_entered.set()
                assert release_first.wait(2.0)
            else:
                second_entered.set()
            assert config.SIGNAL_TUNING[key] == expected
            return expected

        bt._simulate = simulate
        return bt

    first = make_bt(1, first=True)
    second = make_bt(2)
    t1 = threading.Thread(
        target=lambda: first.run_strategy("A", "fake", param_overrides={key: 1})
    )
    t2 = threading.Thread(
        target=lambda: second.run_strategy("B", "fake", param_overrides={key: 2})
    )
    t1.start()
    assert first_entered.wait(1.0)
    t2.start()
    time.sleep(0.1)
    assert not second_entered.is_set(), "second override entered shared config concurrently"
    release_first.set()
    t1.join(2.0)
    t2.join(2.0)
    assert not t1.is_alive() and not t2.is_alive()
    assert seen == [1, 2]
    assert key not in config.SIGNAL_TUNING


def test_optimizer_keeps_equity_only_for_sharpe():
    calls = []

    class FakeBT:
        def run_strategy(self, **kwargs):
            calls.append(kwargs)
            return None

    optimizer = StrategyOptimizer(FakeBT())
    optimizer._run_combo("fake", ["A"], {}, {}, "profit_factor")
    optimizer._run_combo("fake", ["A"], {}, {}, "sharpe")
    assert calls[0]["skip_equity_curve"] is True
    assert calls[1]["skip_equity_curve"] is False


def test_invalid_direction_never_becomes_short():
    bt = _bare_backtester()
    result = bt._simulate(
        "TEST", _frame(), "fake", _Strategy("buy"), 10_000.0, "1h",
        asset_class="stock", commission_pct=0.0, slippage_pct=0.0,
    )
    assert result.total_trades == 0


def test_terminal_equity_matches_post_liquidation_capital():
    bt = _bare_backtester()
    frame = _frame(rows=23)
    result = bt._simulate(
        "TEST/USD", frame, "bmr_357", _Strategy("long"), 10_000.0, "1h",
        asset_class="crypto", commission_pct=0.0, slippage_pct=0.0,
        trail_mode="none",
    )
    assert result.total_trades == 1
    assert result.trades[0].exit_reason == "backtest_end"
    assert result.equity_curve[-1].bar_index == len(frame)
    assert result.equity_curve[-1].equity == result.ending_capital


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} P1-B/P1-C correctness tests passed")


if __name__ == "__main__":
    main()
