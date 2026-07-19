"""Deterministic API/UI contract tests for versioned backtest behavior."""

from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import intelligence.backtester as backtester_module
import web_dashboard


class _FakeBacktester:
    calls = []

    def __init__(self, starting_capital=100000):
        self.starting_capital = starting_capital

    def run_strategy(self, symbol, strategy_name, *args, **kwargs):
        self.calls.append((symbol, strategy_name, kwargs))
        trade = SimpleNamespace(pnl=10.0, stop_mode="standard")
        return SimpleNamespace(
            symbol=symbol,
            strategy_name=strategy_name,
            timeframe="1h",
            behavior_profile=kwargs["behavior_profile"],
            start_date="2026-01-01",
            end_date="2026-01-02",
            starting_capital=100000.0,
            ending_capital=100010.0,
            total_return_pct=0.01,
            total_trades=1,
            win_rate=100.0,
            profit_factor=999.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            stop_mode="standard",
            trades=[trade],
            equity_curve=[],
        )


class _NoDataBacktester:
    def __init__(self, starting_capital=100000):
        self.starting_capital = starting_capital
        self.last_failure_reason = "historical data unavailable for requested window"

    def run_strategy(self, symbol, strategy_name, *args, **kwargs):
        return None


def _run(payload, backtester_cls=_FakeBacktester):
    original = backtester_module.Backtester
    _FakeBacktester.calls.clear()
    backtester_module.Backtester = backtester_cls
    try:
        return web_dashboard.run_backtest_api(payload)
    finally:
        backtester_module.Backtester = original


def test_config_advertises_both_versioned_profiles():
    profiles = web_dashboard.get_backtest_config()["behavior_profiles"]
    assert [item["value"] for item in profiles] == [
        "isolated_v1", "live_parity_v2"
    ]


def test_api_defaults_to_legacy_profile_and_returns_it():
    ok, _, details = _run({
        "asset": "Stocks", "symbol": "AAPL",
        "strategy": "bollinger_breakout", "duration": "30d",
    })
    assert ok
    assert _FakeBacktester.calls[0][2]["behavior_profile"] == "isolated_v1"
    assert details["results"][0]["behavior_profile"] == "isolated_v1"


def test_api_forwards_live_parity_profile_and_returns_it():
    ok, _, details = _run({
        "asset": "Stocks", "symbol": "AAPL",
        "strategy": "bollinger_breakout", "duration": "30d",
        "behavior_profile": "live_parity_v2",
    })
    assert ok
    assert _FakeBacktester.calls[0][2]["behavior_profile"] == "live_parity_v2"
    assert details["results"][0]["behavior_profile"] == "live_parity_v2"


def test_api_rejects_unknown_profile_before_starting_a_run():
    ok, message, details = _run({
        "asset": "Stocks", "symbol": "AAPL",
        "strategy": "bollinger_breakout",
        "behavior_profile": "mystery",
    })
    assert not ok
    assert "behavior_profile must be one of" in message
    assert details == {"cancelled": False}
    assert not _FakeBacktester.calls


def test_api_reports_data_failure_instead_of_misleading_empty_result():
    ok, message, details = _run({
        "asset": "Crypto", "symbol": "ETH/USD",
        "strategy": "bmr_357", "duration": "365d",
        "timeframe": "1h", "behavior_profile": "live_parity_v2",
    }, _NoDataBacktester)
    assert not ok
    assert "No results" in message
    assert "historical data unavailable" in message
    assert details["skipped"] == 1
    assert details["failures"] == [
        "bmr_357/ETH/USD: historical data unavailable for requested window"
    ]


def test_panel_defaults_to_legacy_and_exposes_both_choices():
    source = (ROOT / "Html-Files" / "panels.jsx").read_text(encoding="utf-8")
    assert "behavior_profile: 'isolated_v1'" in source
    assert "value: 'live_parity_v2'" in source
    assert "JSON.stringify(form)" in source


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} behavior-profile dashboard tests passed")
