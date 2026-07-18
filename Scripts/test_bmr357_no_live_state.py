"""
BMR-357 no-live-state test — backtester parity patch step 4
(reports/agent_pipeline/20260717-085541/final_unified_report.md §5 item 2,
§6 item 4).

Bug: BMR357Strategy._btc_momentum_active() used to reach into the live
core.candle_manager singleton for any non-BTC/USD symbol, regardless of what
historical timestamp a backtest replay was simulating. That made backtest
results depend on wall-clock live state instead of the historical data being
replayed — cold vs. warm candle_manager cache could silently change which
trades fired.

The fix (intelligence/backtester.py run_strategy()/_simulate() +
strategies/bmr357_strategy.py) injects a timestamp-aligned historical BTC
window per bar and forbids the live-singleton path entirely once backtest
mode is flagged (requires_historical_btc_context), failing the BTC-momentum
gate closed rather than falling back to live state.

This test proves it directly: backtest a non-BTC crypto symbol twice with
completely different (and even failing) live candle_manager states in
between, and assert (a) trade lists are byte-identical and non-zero, and
(b) the live candle_manager singleton's .get() is never called at all.

Uses synthetic in-memory candle data (same approach as the other
backtester-patch test files this session) so results are deterministic and
need no network access.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SYMBOL = "SYNTH_BMR"
DAYS = 999
TIMEFRAME = "15m"
STRATEGY = "bmr_357"


def _make_oscillating_df(n=3000, seed=11):
    """Repeating sharp-crash / slow-recovery cycles so price repeatedly
    breaches BB(20, 2.25std) with RSI confirmation at the bottom of each
    crash — needed to actually generate BMR-357 mean-reversion entries, not
    just sit flat. A smooth sine wave doesn't do this: its 20-bar-window
    deviation from its own rolling mean stays too small to breach the band."""
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.RandomState(seed)
    price = np.zeros(n)
    price[0] = 100.0
    cycle = 50
    for i in range(1, n):
        phase = i % cycle
        if phase < 4:
            price[i] = price[i - 1] * 0.975  # ~2.5%/bar drop for 4 bars
        else:
            price[i] = price[i - 1] + (100.0 - price[i - 1]) * 0.06  # slow recovery
        price[i] += rng.randn() * 0.02
    price = np.maximum(price, 1.0)
    noise = np.abs(rng.randn(n) * 0.05)
    return pd.DataFrame({
        "open": price,
        "high": price + noise,
        "low": price - noise,
        "close": price,
        "volume": 5000.0,
    }, index=idx)


def _make_volatile_btc_df(n=3000, seed=22):
    """BTC series with frequent >=1% consecutive-close moves so the
    momentum gate (min_btc_move_pct=1.0 by default) actually opens
    regularly instead of blocking every bar."""
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.RandomState(seed)
    price = 40000 + np.cumsum(rng.randn(n) * 250.0)
    price = np.maximum(price, 100.0)
    noise = np.abs(rng.randn(n) * 30.0)
    return pd.DataFrame({
        "open": price,
        "high": price + noise,
        "low": price - noise,
        "close": price,
        "volume": 100.0,
    }, index=idx)


def _seeded_backtester():
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    bt._candle_cache[(SYMBOL, DAYS, TIMEFRAME)] = _make_oscillating_df()
    bt._candle_cache[("BTC/USD", DAYS, TIMEFRAME)] = _make_volatile_btc_df()
    return bt


def _run(monkeypatch_get):
    """Run one backtest with core.candle_manager.candle_manager.get()
    monkeypatched to `monkeypatch_get`, returning (result, call_count)."""
    import core.candle_manager as cm_module

    calls = {"n": 0}

    def _tracked_get(symbol, timeframe, limit=200):
        calls["n"] += 1
        return monkeypatch_get(symbol, timeframe, limit)

    original_get = cm_module.candle_manager.get
    cm_module.candle_manager.get = _tracked_get
    try:
        bt = _seeded_backtester()
        result = bt.run_strategy(
            SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
            timeframe=TIMEFRAME, asset_class="crypto",
        )
    finally:
        cm_module.candle_manager.get = original_get
    return result, calls["n"]


def test_cold_vs_warm_live_cache_produces_identical_trades():
    """Report §5 item 2's exact test: backtest a non-BTC symbol twice with
    different live candle_manager states in between; results must be
    identical and non-zero, and the live singleton must never be touched."""

    def _cold(symbol, timeframe, limit):
        raise RuntimeError("candle_manager cold — no live data available")

    def _warm_but_contaminated(symbol, timeframe, limit):
        # Deliberately implausible/contaminated data: if this were ever
        # actually read, it would produce a huge momentum reading (~50%)
        # and change which bars pass the BTC-momentum gate.
        idx = pd.date_range("2030-01-01", periods=3, freq="15min", tz="UTC")
        return pd.DataFrame({
            "open": [10.0, 10.0, 15.0], "high": [10.0, 10.0, 15.0],
            "low": [10.0, 10.0, 15.0], "close": [10.0, 10.0, 15.0],
            "volume": [1.0, 1.0, 1.0],
        }, index=idx)

    result_cold, calls_cold = _run(_cold)
    result_warm, calls_warm = _run(_warm_but_contaminated)

    assert calls_cold == 0, "live candle_manager.get() must never be called during backtest replay"
    assert calls_warm == 0, "live candle_manager.get() must never be called during backtest replay"

    assert result_cold is not None and result_warm is not None
    assert result_cold.total_trades == result_warm.total_trades
    assert result_cold.total_trades > 0, "test fixture must actually produce BMR-357 trades"

    assert [t.pnl for t in result_cold.trades] == [t.pnl for t in result_warm.trades]
    assert [t.entry_price for t in result_cold.trades] == [t.entry_price for t in result_warm.trades]
    assert [t.exit_price for t in result_cold.trades] == [t.exit_price for t in result_warm.trades]
    assert [t.exit_reason for t in result_cold.trades] == [t.exit_reason for t in result_warm.trades]


def test_btc_symbol_itself_unaffected_by_backtest_mode():
    """Backtesting BTC/USD itself with bmr_357 must still work (uses its own
    candles directly, per the symbol.upper() == 'BTC/USD' branch) and must
    not touch the live singleton either."""
    from intelligence.backtester import Backtester

    def _should_not_be_called(symbol, timeframe, limit):
        raise AssertionError("candle_manager.get() must not be called when backtesting BTC/USD itself")

    import core.candle_manager as cm_module
    original_get = cm_module.candle_manager.get
    cm_module.candle_manager.get = _should_not_be_called
    try:
        bt = Backtester(starting_capital=10_000.0)
        bt._candle_cache[("BTC/USD", DAYS, TIMEFRAME)] = _make_oscillating_df(seed=33)
        result = bt.run_strategy(
            "BTC/USD", STRATEGY, days=DAYS, starting_capital=10_000.0,
            timeframe=TIMEFRAME, asset_class="crypto",
        )
    finally:
        cm_module.candle_manager.get = original_get

    assert result is not None


def main():
    tests = [
        test_cold_vs_warm_live_cache_produces_identical_trades,
        test_btc_symbol_itself_unaffected_by_backtest_mode,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} bmr_357 no-live-state tests passed")


if __name__ == "__main__":
    main()
