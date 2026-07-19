"""Focused behavior-delta tests for the independently implementable P1-A fixes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import intelligence.backtester as bt_module
from core.strategy_registry import (
    EARLY_LOSS_LIFECYCLE_EXEMPT,
    TIME_STOP_EXEMPT,
)
from intelligence.backtester import Backtester
from intelligence.backtest_ledger import RunLedger


def _frame(rows=100, price=100.0, freq="1h"):
    index = pd.date_range("2026-01-02", periods=rows, freq=freq, tz="UTC")
    return pd.DataFrame({
        "open": price,
        "high": price + 1.0,
        "low": price - 1.0,
        "close": price,
        "volume": 1000.0,
    }, index=index)


class _AlwaysSignalStrategy:
    stop_loss_pct = 50.0
    take_profit_pct = 50.0
    params = {}

    def __init__(self, score=0.9, exit_immediately=False):
        self.score = score
        self.exit_immediately = exit_immediately

    def analyze(self, _symbol, _window, _condition):
        return SimpleNamespace(
            direction="long",
            score=self.score,
            metadata={},
            stop_loss_pct=None,
            take_profit_pct=None,
        )

    def check_custom_exit(self, *_args, **_kwargs):
        return "test_flat_exit" if self.exit_immediately else None


class _OneShotStrategy(_AlwaysSignalStrategy):
    def __init__(self, direction="long", score=0.9):
        super().__init__(score=score)
        self.direction = direction
        self.calls = 0

    def analyze(self, _symbol, _window, _condition):
        self.calls += 1
        if self.calls != 1:
            return None
        signal = super().analyze(_symbol, _window, _condition)
        signal.direction = self.direction
        return signal


def _simulate(bt, frame, strategy, **overrides):
    kwargs = dict(
        symbol="TEST",
        df=frame,
        strategy_name="test_strategy",
        strategy_obj=strategy,
        starting_capital=10_000.0,
        timeframe="5m",
        asset_class="crypto",
        commission_pct=0.0,
        slippage_pct=0.0,
        trail_mode="none",
        skip_equity_curve=True,
        behavior_profile=bt_module.BEHAVIOR_LIVE_PARITY_V2,
    )
    kwargs.update(overrides)
    return bt._simulate(**kwargs)


def _bare_backtester():
    bt = Backtester.__new__(Backtester)
    bt.starting_capital = 10_000.0
    bt._candle_cache = {}
    bt.ta = None
    bt.yf = None
    bt.ccxt = None
    return bt


def test_early_loss_policy_is_narrow_and_separate_from_time_stops():
    assert EARLY_LOSS_LIFECYCLE_EXEMPT == frozenset({
        "vtmr_strategy", "bmr_357", "orb_breakout",
    })
    assert len(TIME_STOP_EXEMPT) == 25
    assert EARLY_LOSS_LIFECYCLE_EXEMPT < TIME_STOP_EXEMPT
    for strategy in TIME_STOP_EXEMPT:
        expected = strategy in {"vtmr_strategy", "bmr_357", "orb_breakout"}
        assert (strategy in EARLY_LOSS_LIFECYCLE_EXEMPT) is expected


def test_early_loss_simulation_matches_all_25_members_plus_control():
    frame = _frame(42, freq="5min")
    frame["close"] = np.linspace(100.0, 90.0, len(frame))
    frame["open"] = frame["close"]
    frame["high"] = frame["close"] + 0.05
    frame["low"] = frame["close"] - 0.05
    frame["volume"] = 0.0  # prevent ORB VWAP from preempting this lifecycle test
    names = sorted(TIME_STOP_EXEMPT) + ["non_exempt_control"]
    for name in names:
        result = _simulate(
            _bare_backtester(), frame, _OneShotStrategy(), strategy_name=name
        )
        assert result.total_trades == 1, name
        reason = result.trades[0].exit_reason
        if name in EARLY_LOSS_LIFECYCLE_EXEMPT:
            assert reason == "backtest_end", (name, reason)
        else:
            assert reason == "early_loss", (name, reason)


def test_current_live_strategy_ledger_deltas_are_explicit_per_profile():
    # Read-only Hostinger bot_state snapshot, 2026-07-19, intersected with
    # StrategyEngine's actually-instantiated classes. Stale enabled keys for
    # marc_strategy/vdmr_strategy are intentionally excluded because the live
    # engine never instantiates them.
    live_strategies = {
        "bmr_357", "bollinger_breakout", "hammer_reversal",
        "orb_breakout", "pll_cycle", "scalp_master", "vwap_momentum",
    }
    frame = _frame(42, freq="5min")
    frame["close"] = np.linspace(100.0, 90.0, len(frame))
    frame["open"] = frame["close"]
    frame["high"] = frame["close"] + 0.05
    frame["low"] = frame["close"] - 0.05
    frame["volume"] = 0.0

    manifests = {}
    for name in sorted(live_strategies):
        profile_reasons = {}
        for profile in (
            bt_module.BEHAVIOR_ISOLATED_V1,
            bt_module.BEHAVIOR_LIVE_PARITY_V2,
        ):
            ledger = RunLedger(f"{name}-{profile}")
            _simulate(
                _bare_backtester(), frame, _OneShotStrategy(),
                strategy_name=name, behavior_profile=profile, ledger=ledger,
            )
            exits = ledger.events_by_type("exit")
            assert len(exits) == 1, (name, profile, exits)
            profile_reasons[profile] = exits[0].payload["exit_reason"]
        manifests[name] = profile_reasons

    assert set(manifests) == live_strategies
    for name, reasons in manifests.items():
        legacy = reasons[bt_module.BEHAVIOR_ISOLATED_V1]
        corrected = reasons[bt_module.BEHAVIOR_LIVE_PARITY_V2]
        # isolated_v1 intentionally retains the old trail_mode="none" bug,
        # so this adverse path ratchets and then stops out for every strategy.
        assert legacy == "stop_loss", (name, reasons)
        if name in EARLY_LOSS_LIFECYCLE_EXEMPT:
            assert corrected == "backtest_end", (name, reasons)
        else:
            assert corrected == "early_loss", (name, reasons)


def test_consecutive_loss_breaker_matches_configured_boundary():
    limit = config.MAX_CONSECUTIVE_LOSSES
    assert not bt_module._consecutive_loss_halt_reached(limit - 1)
    assert bt_module._consecutive_loss_halt_reached(limit)
    assert bt_module._consecutive_loss_halt_reached(limit + 1)


def test_consecutive_loss_breaker_changes_replay_at_exact_live_limit():
    frame = _frame(80, freq="5min")
    corrected = _simulate(
        _bare_backtester(), frame, _AlwaysSignalStrategy(exit_immediately=True)
    )
    with patch.object(bt_module, "_consecutive_loss_halt_reached", return_value=False):
        legacy = _simulate(
            _bare_backtester(), frame, _AlwaysSignalStrategy(exit_immediately=True)
        )
    assert corrected.total_trades == config.MAX_CONSECUTIVE_LOSSES
    assert legacy.total_trades > corrected.total_trades


def test_replay_session_reset_uses_live_pacific_calendar_boundary():
    # Read-only Hostinger verification on 2026-07-19 returned both
    # `PDT -0700` and `America/Los_Angeles`; this is not a workstation guess.
    assert bt_module._live_session_date("2026-07-18T06:59:59Z") == "2026-07-17"
    assert bt_module._live_session_date("2026-07-18T07:00:00Z") == "2026-07-18"


def test_behavior_profile_defaults_to_legacy_and_rejects_unknown_values():
    assert bt_module._resolve_behavior_profile(
        bt_module.BEHAVIOR_ISOLATED_V1
    ) == bt_module.BEHAVIOR_ISOLATED_V1
    assert bt_module._resolve_behavior_profile(
        bt_module.BEHAVIOR_LIVE_PARITY_V2
    ) == bt_module.BEHAVIOR_LIVE_PARITY_V2
    try:
        bt_module._resolve_behavior_profile("mystery")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown behavior profile was accepted")


def test_signal_confidence_is_finite_and_uses_live_threshold():
    threshold = config.SIGNAL_TUNING.get(
        "min_signal_confidence", config.MIN_SIGNAL_CONFIDENCE
    )
    assert not bt_module._signal_meets_min_confidence(threshold - 0.001)
    assert bt_module._signal_meets_min_confidence(threshold)
    for invalid in (None, "bad", float("nan"), float("inf"), -float("inf")):
        assert not bt_module._signal_meets_min_confidence(invalid)


def test_confidence_gate_removes_legacy_subthreshold_trade():
    frame = _frame(50)
    threshold = config.SIGNAL_TUNING.get(
        "min_signal_confidence", config.MIN_SIGNAL_CONFIDENCE
    )
    score = float(threshold) - 0.01
    corrected = _simulate(_bare_backtester(), frame, _AlwaysSignalStrategy(score))
    with patch.object(bt_module, "_signal_meets_min_confidence", return_value=True):
        legacy = _simulate(_bare_backtester(), frame, _AlwaysSignalStrategy(score))
    assert corrected.total_trades == 0
    assert legacy.total_trades == 1


def test_low_rate_integrity_violations_are_quarantined_not_simulated():
    frame = _frame(100)
    bad_time = frame.index[50]
    frame.loc[bad_time, "high"] = 1.0
    bt = _bare_backtester()
    legacy = bt._validate_ohlcv(
        frame.copy(), "TEST", "1h", bt_module.BEHAVIOR_ISOLATED_V1
    )
    clean = bt._validate_ohlcv(
        frame.copy(), "TEST", "1h", bt_module.BEHAVIOR_LIVE_PARITY_V2
    )
    assert legacy is not None
    assert len(legacy) == 100
    assert bad_time in legacy.index
    assert clean is not None
    assert len(clean) == 99
    assert bad_time not in clean.index


def test_trail_none_leaves_stop_unchanged_while_percent_ratchets():
    bt = _bare_backtester()
    row = pd.Series({"low": 99.0, "high": 110.0, "close": 108.0})
    no_trail = {"direction": "long", "current_sl": 90.0, "current_tp": 120.0}
    percent = dict(no_trail)
    assert bt._check_exit_standard(no_trail, row, 0.015, 0.03, False) is None
    assert bt._check_exit_standard(percent, row, 0.015, 0.03, True) is None
    assert no_trail["current_sl"] == 90.0
    assert percent["current_sl"] > 90.0


def test_simulation_trail_dispatch_long_short_and_two_bar_regression():
    for direction in ("long", "short"):
        frame = _frame(48, freq="5min")
        closes = np.linspace(100.0, 106.0, len(frame))
        if direction == "short":
            closes = closes[::-1]
        frame["open"] = closes
        frame["close"] = closes
        frame["high"] = closes + 0.05
        frame["low"] = closes - 0.05

        ledgers = {}
        for trail_mode in ("none", "percent", "two_bar"):
            ledger = RunLedger(f"{direction}-{trail_mode}")
            _simulate(
                _bare_backtester(), frame, _OneShotStrategy(direction),
                trail_mode=trail_mode, ledger=ledger,
            )
            ledgers[trail_mode] = ledger.events_by_type("level_mutation")

        assert ledgers["none"] == [], direction
        assert len(ledgers["percent"]) > 0, direction
        assert len(ledgers["two_bar"]) > 0, direction

        legacy = RunLedger(f"legacy-{direction}-none")
        _simulate(
            _bare_backtester(), frame, _OneShotStrategy(direction),
            trail_mode="none", ledger=legacy,
            behavior_profile=bt_module.BEHAVIOR_ISOLATED_V1,
        )
        assert len(legacy.events_by_type("level_mutation")) > 0, direction


class _FakeTA:
    def rsi(self, _close, _period):
        return pd.Series([70.0])

    def macd(self, _close):
        hist = pd.Series([-1.0, -1.0])
        return hist, hist, hist

    def ema(self, _close, period):
        values = {9: 90.0, 21: 100.0, 50: 110.0}
        return pd.Series([values[period]])

    def bollinger_bands(self, _close, _period, _std):
        pct = pd.Series([0.90])
        return pct, pct, pct


def test_high_rsi_branch_awards_the_reachable_stronger_short_score():
    bt = _bare_backtester()
    bt.ta = _FakeTA()
    direction, score, _ = bt._score_bar(
        _frame(30), 29, bt_module.BEHAVIOR_LIVE_PARITY_V2
    )
    assert direction == "short"
    assert score == 0.65


def test_stale_adx_is_prefix_invariant_and_available_past_2000_rows():
    rng = np.random.default_rng(7)
    closes = 100.0 + np.cumsum(rng.normal(0.0, 0.4, 2200))
    full = _frame(2200)
    full["open"] = closes
    full["close"] = closes
    full["high"] = closes + 0.5
    full["low"] = closes - 0.5
    trade = {"direction": "long"}
    long_result = bt_module._bt_stale_adx(full, 2100, trade)
    suffix = full.iloc[2000:].copy()
    short_result = bt_module._bt_stale_adx(suffix, 100, trade)
    assert long_result == short_result
    replay_values = bt_module._compute_adx_di_50(full, 2100)
    assert replay_values is not None

    # Independent transcription of live PositionMonitor._get_adx_di():
    # request/take the most recent 50 bars, then pandas_ta.adx(length=14).
    import pandas_ta as ta
    live_window = full.iloc[:2101].tail(50)
    live_df = ta.adx(
        live_window["high"].astype(float),
        live_window["low"].astype(float),
        live_window["close"].astype(float),
        length=14,
    )
    live_values = (
        float(live_df[[c for c in live_df if c.startswith("ADX_")][0]].iloc[-1]),
        float(live_df[[c for c in live_df if c.startswith("DMP_")][0]].iloc[-1]),
        float(live_df[[c for c in live_df if c.startswith("DMN_")][0]].iloc[-1]),
    )
    assert np.allclose(replay_values, live_values, rtol=0.0, atol=1e-12)


if __name__ == "__main__":
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} P1-A behavior tests passed")
