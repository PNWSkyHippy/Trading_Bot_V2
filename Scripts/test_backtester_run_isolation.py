"""
Run-isolation tests — backtester parity patch step 2
(reports/agent_pipeline/20260717-085541/final_unified_report.md §5, item 10).

Proves BacktestRunContext gives concurrent backtest runs independent cancel
state: cancelling one run cannot bleed into another run's context (the bug
the step-2 patch closed, where a bare module-global threading.Event was
shared by every run). Uses synthetic in-memory candle data pre-seeded into
Backtester._candle_cache so runs are fast, deterministic, and need no
network access or the real candle_store.db.
"""

import sys
import threading
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SYMBOL_A = "SYNTH_ISO_A"
SYMBOL_B = "SYNTH_ISO_B"
SYMBOL_C = "SYNTH_ISO_C"
DAYS = 999
TIMEFRAME = "1h"
STRATEGY = "rsi_momentum"


def _make_synthetic_df(n=1500, seed=0):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.RandomState(seed)
    price = 100 + np.cumsum(rng.randn(n) * 0.05)
    price = np.maximum(price, 1.0)
    return pd.DataFrame({
        "open": price,
        "high": price + 0.15,
        "low": price - 0.15,
        "close": price,
        "volume": 1000.0,
    }, index=idx)


def _seeded_backtester(symbol, seed):
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    bt._candle_cache[(symbol, DAYS, TIMEFRAME)] = _make_synthetic_df(seed=seed)
    return bt


def test_run_context_isolation_basic():
    """Two BacktestRunContext instances never share underlying cancel state."""
    from intelligence.backtester import BacktestRunContext

    ctx1 = BacktestRunContext()
    ctx2 = BacktestRunContext()
    assert ctx1.id != ctx2.id
    assert not ctx1.is_cancelled() and not ctx2.is_cancelled()

    ctx1.cancel()
    assert ctx1.is_cancelled()
    assert not ctx2.is_cancelled(), "cancelling ctx1 must not affect ctx2"

    ctx1.clear()
    assert not ctx1.is_cancelled()


def test_default_context_isolated_from_explicit_context():
    """request_cancel()/clear_cancel() only ever touch the shared default
    context — a caller-supplied BacktestRunContext must be unaffected."""
    from intelligence.backtester import BacktestRunContext, request_cancel, clear_cancel

    explicit_ctx = BacktestRunContext()
    clear_cancel()  # make sure default starts clean regardless of test order
    try:
        request_cancel()
        assert not explicit_ctx.is_cancelled(), (
            "request_cancel() must only cancel the shared default context, "
            "never a caller-supplied BacktestRunContext"
        )
    finally:
        clear_cancel()


def test_concurrent_runs_cancel_isolation():
    """Report §5 item 10: two controlled concurrent runs — cancel run A,
    prove run B continues unaffected and A actually stops; then start run C
    afterward with verifiably clean state."""
    from intelligence.backtester import BacktestRunContext

    bt_a = _seeded_backtester(SYMBOL_A, seed=1)
    bt_b = _seeded_backtester(SYMBOL_B, seed=2)

    ctx_a = BacktestRunContext()
    ctx_b = BacktestRunContext()

    both_started = threading.Barrier(2)
    results = {}

    def run_a():
        both_started.wait()
        # Cancel A right as it starts, before B has a chance to observe it.
        ctx_a.cancel()
        results["a"] = bt_a.run_strategy(
            SYMBOL_A, STRATEGY, days=DAYS, starting_capital=10_000.0,
            timeframe=TIMEFRAME, asset_class="crypto", run_ctx=ctx_a,
        )

    def run_b():
        both_started.wait()
        results["b"] = bt_b.run_strategy(
            SYMBOL_B, STRATEGY, days=DAYS, starting_capital=10_000.0,
            timeframe=TIMEFRAME, asset_class="crypto", run_ctx=ctx_b,
        )

    t_a = threading.Thread(target=run_a)
    t_b = threading.Thread(target=run_b)
    t_a.start()
    t_b.start()
    t_a.join(timeout=30)
    t_b.join(timeout=30)

    assert not t_a.is_alive() and not t_b.is_alive(), "runs did not finish in time"
    assert ctx_a.is_cancelled(), "run A's own context must show cancelled"
    assert results["a"] is None, "a cancelled run must return None, not a result"
    assert not ctx_b.is_cancelled(), "run B's context must be untouched by run A's cancel"
    assert results["b"] is not None, "run B must complete normally despite A being cancelled concurrently"

    # Run C afterward — verifiably clean state, using a fresh context.
    bt_c = _seeded_backtester(SYMBOL_C, seed=3)
    ctx_c = BacktestRunContext()
    assert not ctx_c.is_cancelled()
    result_c = bt_c.run_strategy(
        SYMBOL_C, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto", run_ctx=ctx_c,
    )
    assert not ctx_c.is_cancelled(), "run C must not inherit any stale cancel state"
    assert result_c is not None, "run C must complete normally with clean context"


def main():
    tests = [
        test_run_context_isolation_basic,
        test_default_context_isolated_from_explicit_context,
        test_concurrent_runs_cancel_isolation,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} backtester run-isolation tests passed")


if __name__ == "__main__":
    main()
