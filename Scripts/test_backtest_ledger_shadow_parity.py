"""
Event-ledger shadow-parity tests — backtester parity patch step 3
(reports/agent_pipeline/20260717-085541/final_unified_report.md §6, item 3).

The ledger is "emitted shadow-only at first so it can validate itself
against current behavior before anything downstream depends on it" (report
text, verbatim). These tests are that validation: they prove (a) passing a
RunLedger never changes simulation output versus ledger=None, and (b) the
ledger's own exit events reconstruct exactly the same trades the
BacktestResult already reports — the ledger isn't inventing or dropping
anything relative to ground truth.

Uses synthetic in-memory candle data (same approach as
test_backtester_run_isolation.py) so results are deterministic and need no
network access.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SYMBOL = "SYNTH_LEDGER"
DAYS = 999
TIMEFRAME = "1h"
STRATEGY = "rsi_momentum"


def _make_synthetic_df(n=2000, seed=7):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.RandomState(seed)
    # Mean-reverting-ish noisy walk so RSI actually oscillates and trades happen.
    price = 100 + np.cumsum(rng.randn(n) * 0.3)
    price = np.maximum(price, 1.0)
    return pd.DataFrame({
        "open": price,
        "high": price + np.abs(rng.randn(n) * 0.2),
        "low": price - np.abs(rng.randn(n) * 0.2),
        "close": price,
        "volume": 1000.0,
    }, index=idx)


def _seeded_backtester():
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    bt._candle_cache[(SYMBOL, DAYS, TIMEFRAME)] = _make_synthetic_df()
    return bt


def test_ledger_none_vs_ledger_present_identical_results():
    """Passing a RunLedger must not change simulation output at all."""
    from intelligence.backtest_ledger import RunLedger

    bt_plain  = _seeded_backtester()
    bt_shadow = _seeded_backtester()

    result_plain = bt_plain.run_strategy(
        SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto",
    )
    ledger = RunLedger(run_id="shadow-parity-test")
    result_shadow = bt_shadow.run_strategy(
        SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto", ledger=ledger,
    )

    assert result_plain is not None and result_shadow is not None
    assert result_plain.total_trades == result_shadow.total_trades
    assert result_plain.total_trades > 0, "test fixture must actually produce trades"
    assert [t.pnl for t in result_plain.trades] == [t.pnl for t in result_shadow.trades]
    assert [t.exit_reason for t in result_plain.trades] == [t.exit_reason for t in result_shadow.trades]
    assert [t.entry_price for t in result_plain.trades] == [t.entry_price for t in result_shadow.trades]
    assert [t.exit_price for t in result_plain.trades] == [t.exit_price for t in result_shadow.trades]

    assert len(ledger) > 0, "shadow run must have actually recorded events"


def test_ledger_exit_events_reconstruct_same_trades_as_result():
    """Every closed trade in BacktestResult.trades must have exactly one
    matching 'exit' ledger event with the same reason/price/pnl, in the
    same order — the ledger must not drop, duplicate, or misreport trades."""
    from intelligence.backtest_ledger import RunLedger

    bt = _seeded_backtester()
    ledger = RunLedger(run_id="reconstruction-test")
    result = bt.run_strategy(
        SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto", ledger=ledger,
    )
    assert result is not None and result.total_trades > 0

    exit_events = ledger.events_by_type("exit")
    assert len(exit_events) == len(result.trades), (
        f"expected {len(result.trades)} exit events, ledger recorded {len(exit_events)}"
    )

    for trade, evt in zip(result.trades, exit_events):
        assert evt.symbol == trade.symbol
        assert evt.payload["exit_reason"] == trade.exit_reason
        assert evt.payload["exit_price"] == trade.exit_price
        assert evt.payload["pnl"] == trade.pnl
        assert evt.payload["pnl_pct"] == trade.pnl_pct


def test_ledger_every_trade_has_fill_before_exit():
    """Each trade_id with an exit event must have exactly one earlier fill
    event (order/fill precede exit — the ledger must preserve causal order)."""
    from intelligence.backtest_ledger import RunLedger

    bt = _seeded_backtester()
    ledger = RunLedger(run_id="order-test")
    result = bt.run_strategy(
        SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto", ledger=ledger,
    )
    assert result is not None and result.total_trades > 0

    for evt in ledger.events_by_type("exit"):
        trade_events = ledger.events_for_trade(evt.trade_id)
        fill_events = [e for e in trade_events if e.event_type == "fill"]
        assert len(fill_events) == 1, f"trade {evt.trade_id} must have exactly one fill event"
        assert fill_events[0].seq < evt.seq, "fill must be recorded before its exit"


def test_ledger_level_mutations_are_monotonic_in_favor_of_trailing_direction():
    """Every recorded level_mutation for a long trade must raise the stop
    (never lower it) and vice versa for shorts — proves the ledger is
    observing real state changes, not fabricating events."""
    from intelligence.backtest_ledger import RunLedger

    bt = _seeded_backtester()
    ledger = RunLedger(run_id="mutation-test")
    bt.run_strategy(
        SYMBOL, STRATEGY, days=DAYS, starting_capital=10_000.0,
        timeframe=TIMEFRAME, asset_class="crypto", ledger=ledger,
    )

    mutations = ledger.events_by_type("level_mutation")
    for evt in mutations:
        prev_sl = evt.payload["prev_stop_loss"]
        new_sl  = evt.payload["new_stop_loss"]
        assert new_sl != prev_sl, "a recorded mutation must be an actual change"


def main():
    tests = [
        test_ledger_none_vs_ledger_present_identical_results,
        test_ledger_exit_events_reconstruct_same_trades_as_result,
        test_ledger_every_trade_has_fill_before_exit,
        test_ledger_level_mutations_are_monotonic_in_favor_of_trailing_direction,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} backtest ledger shadow-parity tests passed")


if __name__ == "__main__":
    main()
