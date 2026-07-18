"""
Lifecycle-correctness patch tests — backtester parity patch step 5
(reports/agent_pipeline/20260717-085541/final_unified_report.md §6, item 5).

Covers all four sub-patches to intelligence/backtester.py made in this step:

  1. Gap-through-stop fill correction (_close_trade): a stop-loss exit now
     fills at whichever is worse for the position, the bar's open or the
     nominal stop price — min(open, stop) for longs, max(open, stop) for
     shorts — instead of always booking at the nominal stop level.

  2. Early-loss one-shot latch + 3-bar confirmation (_simulate): live checks
     early-loss exactly once, in a 30-60min wall-clock window, latched via a
     DB flag; the backtester now mirrors this with a per-trade
     `_early_loss_checked` flag at the first bar crossing EARLY_LOSS_BARS,
     instead of re-checking every bar.

  3. Asset-class-aware performance-time-stop floors (_simulate): crypto uses
     PERF_FLOOR_2HR=0.0 (never cuts a merely-below-threshold-but-positive
     trade) and a fee-aware 5hr floor; stock floors stay effectively at the
     canonical PERF_2HR_PCT/PERF_5HR_PCT since the stock fee hurdle is
     negligible.

  4. Daily-budget position-value clamp (_simulate, entry sizing): a new
     position's size is shrunk proportionally to the loss budget remaining
     today, mirroring core/risk_manager.py's approve_trade — distinct from
     and complementary to the existing binary trading_halted circuit
     breaker.

Uses a minimal dummy strategy object and hand-crafted synthetic candle data
(same approach as the other backtester-patch test files this session) so
every scenario is deterministic and exercises _simulate()/_close_trade()
directly rather than depending on any real strategy's signal logic.
"""

import contextlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@contextlib.contextmanager
def _trailing_stop_disabled():
    """_check_exit_standard ratchets current_sl to price*(1 - TRAILING_STOP_PCT/100)
    on EVERY bar regardless of whether the trade is in profit (it only floors,
    never lowers) — with the real config value (1.5%) this immediately
    tightens the stop to ~1.5% below whatever the close is, which would hit
    on the very next down-bar and mask the early-loss/perf-floor logic these
    tests target. Not a bug in the patch under test — just orthogonal
    behavior this test suite needs to hold constant, so temporarily widen it
    to a no-op gap for the duration of these scenarios."""
    import config
    original = config.TRAILING_STOP_PCT
    config.TRAILING_STOP_PCT = 1000.0
    try:
        yield
    finally:
        config.TRAILING_STOP_PCT = original


class _DummyStrategy:
    """Fires exactly one TradeSignal on its first analyze() call, then never
    again — gives full control over entry timing for lifecycle tests."""

    def __init__(self, direction="long", sl_pct=50.0, tp_pct=50.0):
        self.strategy_name = "dummy_lifecycle_test"
        self.stop_loss_pct = sl_pct
        self.take_profit_pct = tp_pct
        self._direction = direction
        self._fired = False

    def analyze(self, symbol, candles, market_condition="unknown"):
        from strategies.base_strategy import TradeSignal
        if self._fired:
            return None
        self._fired = True
        return TradeSignal(
            symbol=symbol,
            direction=self._direction,
            score=0.9,
            strategy_name=self.strategy_name,
            stop_loss_pct=self.stop_loss_pct,
            take_profit_pct=self.take_profit_pct,
        )

    def check_custom_exit(self, symbol, candles, direction, meta):
        return None


def _flat_df(n, price=100.0, seed=1):
    """Flat/no-op price series used as filler before/after the bars a test
    actually cares about (small noise so indicators/window ops don't choke
    on zero variance)."""
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.RandomState(seed)
    noise = rng.randn(n) * 0.001
    close = price + noise
    return pd.DataFrame({
        "open": close, "high": close + 0.01, "low": close - 0.01,
        "close": close, "volume": 1000.0,
    }, index=idx)


# =============================================================================
# 1. Gap-through-stop fill correction
# =============================================================================

def test_gap_through_stop_fills_at_worse_of_open_and_stop_long():
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    idx = pd.date_range("2024-01-01", periods=2, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "open":  [100.0, 90.0],   # bar 1 gaps down through stop=95
        "high":  [100.0, 92.0],
        "low":   [99.0,  88.0],
        "close": [99.5,  89.0],
        "volume": [1000.0, 1000.0],
    }, index=idx)
    trade = {
        "symbol": "TEST", "direction": "long", "quantity": 10.0,
        "entry_price": 100.0, "position_value": 1000.0,
        "current_sl": 95.0, "current_tp": 110.0,
        "stop_loss": 95.0, "take_profit": 110.0,
        "signal_score": 0.9, "entry_idx": 0,
        "entry_date": str(idx[0]), "entry_metadata": {},
    }
    _, bt_trade = bt._close_trade(trade, price=df.iloc[1]["close"],
                                   reason="stop_loss", idx=1, df=df,
                                   strategy_name="test")
    assert bt_trade.exit_price == 90.0, (
        f"expected fill at gapped open (90.0), got {bt_trade.exit_price}"
    )


def test_no_gap_stop_loss_still_fills_at_nominal_stop_long():
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    idx = pd.date_range("2024-01-01", periods=2, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "open":  [100.0, 96.0],   # bar 1 opens ABOVE stop=95 — no gap
        "high":  [100.0, 96.5],
        "low":   [99.0,  94.0],   # low touches stop intrabar
        "close": [99.5,  94.5],
        "volume": [1000.0, 1000.0],
    }, index=idx)
    trade = {
        "symbol": "TEST", "direction": "long", "quantity": 10.0,
        "entry_price": 100.0, "position_value": 1000.0,
        "current_sl": 95.0, "current_tp": 110.0,
        "stop_loss": 95.0, "take_profit": 110.0,
        "signal_score": 0.9, "entry_idx": 0,
        "entry_date": str(idx[0]), "entry_metadata": {},
    }
    _, bt_trade = bt._close_trade(trade, price=df.iloc[1]["close"],
                                   reason="stop_loss", idx=1, df=df,
                                   strategy_name="test")
    assert bt_trade.exit_price == 95.0, (
        f"no-gap stop exit must still fill at nominal stop (95.0), got {bt_trade.exit_price}"
    )


def test_gap_through_stop_fills_at_worse_of_open_and_stop_short():
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    idx = pd.date_range("2024-01-01", periods=2, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "open":  [100.0, 110.0],  # bar 1 gaps UP through short stop=105
        "high":  [100.0, 112.0],
        "low":   [99.0,  109.0],
        "close": [99.5,  111.0],
        "volume": [1000.0, 1000.0],
    }, index=idx)
    trade = {
        "symbol": "TEST", "direction": "short", "quantity": 10.0,
        "entry_price": 100.0, "position_value": 1000.0,
        "current_sl": 105.0, "current_tp": 90.0,
        "stop_loss": 105.0, "take_profit": 90.0,
        "signal_score": 0.9, "entry_idx": 0,
        "entry_date": str(idx[0]), "entry_metadata": {},
    }
    _, bt_trade = bt._close_trade(trade, price=df.iloc[1]["close"],
                                   reason="stop_loss", idx=1, df=df,
                                   strategy_name="test")
    assert bt_trade.exit_price == 110.0, (
        f"expected fill at gapped open (110.0), got {bt_trade.exit_price}"
    )


def test_take_profit_exit_still_fills_at_nominal_tp_unaffected():
    """Sanity check: the gap-fill correction is scoped to reason=='stop_loss'
    only — take_profit exits must be untouched (still fill at the TP level,
    per the pre-existing Opus 2026-05-29 resting-limit-order behavior)."""
    from intelligence.backtester import Backtester
    bt = Backtester(starting_capital=10_000.0)
    idx = pd.date_range("2024-01-01", periods=2, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "open":  [100.0, 120.0],  # gaps way past TP=110
        "high":  [100.0, 121.0],
        "low":   [99.0,  119.0],
        "close": [99.5,  120.5],
        "volume": [1000.0, 1000.0],
    }, index=idx)
    trade = {
        "symbol": "TEST", "direction": "long", "quantity": 10.0,
        "entry_price": 100.0, "position_value": 1000.0,
        "current_sl": 95.0, "current_tp": 110.0,
        "stop_loss": 95.0, "take_profit": 110.0,
        "signal_score": 0.9, "entry_idx": 0,
        "entry_date": str(idx[0]), "entry_metadata": {},
    }
    _, bt_trade = bt._close_trade(trade, price=df.iloc[1]["close"],
                                   reason="take_profit", idx=1, df=df,
                                   strategy_name="test")
    assert bt_trade.exit_price == 110.0, (
        f"take_profit fill must stay at nominal TP (110.0), got {bt_trade.exit_price}"
    )


# =============================================================================
# 2. Early-loss one-shot latch + 3-bar confirmation
# =============================================================================

def _run_dummy_simulate(price_path, direction="long", sl_pct=50.0, tp_pct=50.0,
                         asset_class="crypto", timeframe="15m"):
    """Build a df whose closes/opens follow `price_path` starting right at
    entry (bar min_bars+1, since min_bars==20 for these df lengths), run
    _simulate() with the one-shot dummy strategy, and return the result."""
    from intelligence.backtester import Backtester

    n_lead = 20        # bars before entry (min_bars for len(df) in [30,83])
    n_path = len(price_path)
    n_tail = 5          # trailing bars so the last real bar isn't used for entry
    n = n_lead + 1 + n_path + n_tail   # +1: entry-signal bar itself

    lead = _flat_df(n_lead, price=price_path[0], seed=3)
    idx_full = pd.date_range(lead.index[-1] + pd.Timedelta(minutes=15),
                              periods=n - n_lead, freq="15min", tz="UTC")

    # Row n_lead: the bar the signal fires ON (entry executes NEXT bar's open).
    sig_row = pd.DataFrame({
        "open": [price_path[0]], "high": [price_path[0] + 0.01],
        "low": [price_path[0] - 0.01], "close": [price_path[0]],
        "volume": [1000.0],
    }, index=[idx_full[0]])

    path_rows = []
    for j, p in enumerate(price_path):
        path_rows.append({
            "open": p, "high": p + 0.01, "low": p - 0.01,
            "close": p, "volume": 1000.0,
        })
    path_df = pd.DataFrame(path_rows, index=idx_full[1:1 + n_path])

    tail = _flat_df(n_tail, price=price_path[-1], seed=5)
    tail.index = idx_full[1 + n_path: 1 + n_path + n_tail]

    df = pd.concat([lead, sig_row, path_df, tail])
    df.index = pd.date_range("2024-01-01", periods=len(df), freq="15min", tz="UTC")

    bt = Backtester(starting_capital=10_000.0)
    strategy_obj = _DummyStrategy(direction=direction, sl_pct=sl_pct, tp_pct=tp_pct)
    with _trailing_stop_disabled():
        result = bt._simulate(
            "SYNTH_LIFECYCLE", df, "dummy_lifecycle_test", strategy_obj,
            starting_capital=10_000.0, timeframe=timeframe,
            asset_class=asset_class,
            commission_pct=0.0, slippage_pct=0.0,
        )
    return result


def test_early_loss_fires_once_on_confirmed_decline():
    """Long entry, price drops >0.5% and keeps declining for 3 confirming
    closes right at the 30min (2-bar, 15m tf) mark — must exit 'early_loss'."""
    # entry_price = 100 (bars_held=0). EARLY_LOSS_BARS=2 (15m tf, crypto) —
    # the check fires at bars_held==2. The 3-bar confirmation window reads
    # closes at bars_held 0,1,2 directly from df, so those three bars must
    # themselves be strictly declining (100 -> 99.5 -> 99.0) to read as
    # "still_wrong", with bars_held==2's pnl_pct (-1.0%) below -0.5%.
    price_path = [100.0, 99.5, 99.0, 98.0, 97.0, 96.5, 96.0]
    result = _run_dummy_simulate(price_path, direction="long",
                                  sl_pct=50.0, tp_pct=50.0)
    assert result is not None and result.total_trades == 1, (
        f"expected exactly 1 trade, got {result.total_trades if result else None}"
    )
    trade = result.trades[0]
    assert trade.exit_reason == "early_loss", (
        f"expected early_loss exit, got {trade.exit_reason}"
    )


def test_early_loss_does_not_fire_when_price_stabilizes():
    """Long entry dips below -0.5% at the check bar but the 3-bar window is
    NOT monotonically declining (stabilizes) — must NOT exit early_loss, and
    must never re-check on a later bar (one-shot latch)."""
    # closes: 100 (entry), 100 (bar1), 98.5 (bar2, pnl<-0.5%, check fires,
    # window=[100,100,98.5] not monotonic-down -> no exit), then a further
    # decline afterward that would trip early_loss if re-checked — proving
    # the latch prevents a second evaluation.
    price_path = [100.0, 100.0, 98.5, 90.0, 85.0, 80.0, 75.0]
    result = _run_dummy_simulate(price_path, direction="long",
                                  sl_pct=90.0, tp_pct=90.0)
    assert result is not None and result.total_trades == 1
    trade = result.trades[0]
    assert trade.exit_reason != "early_loss", (
        f"early_loss must not fire once the latch's single check already passed, "
        f"got {trade.exit_reason}"
    )


# =============================================================================
# 3. Asset-class-aware performance-time-stop floors
# =============================================================================

def test_crypto_slow_green_trade_survives_2hr_floor():
    """Crypto: pnl sits at +0.1% (below the OLD flat 0.2% floor, but above
    the NEW crypto floor of 0.0) at the 2hr (PERF_2HR_BARS, tf=1h -> 2 bars)
    mark — must NOT be cut by perf_time_stop_1hr."""
    entry = 100.0
    # bars_held=1: flat. bars_held=2 (2hr mark): pnl_pct = +0.1%.
    price_path = [entry, entry, entry * 1.001, entry * 1.001, entry * 1.001]
    result = _run_dummy_simulate(price_path, direction="long",
                                  sl_pct=50.0, tp_pct=50.0,
                                  asset_class="crypto", timeframe="1h")
    assert result is not None and result.total_trades == 1
    trade = result.trades[0]
    assert trade.exit_reason != "perf_time_stop_1hr", (
        f"crypto floor is 0.0 — a +0.1% trade must survive the 2hr check, "
        f"got {trade.exit_reason}"
    )


def test_stock_same_slow_green_trade_is_cut_by_2hr_floor():
    """Stock: the same +0.1% pnl at the 2hr mark IS below the stock floor
    (max(0.2, fee+0.10)=0.2) — must be cut, proving the asset-class branch
    actually differentiates (this isn't just 'floor always 0')."""
    entry = 100.0
    price_path = [entry, entry, entry * 1.001, entry * 1.001, entry * 1.001]
    result = _run_dummy_simulate(price_path, direction="long",
                                  sl_pct=50.0, tp_pct=50.0,
                                  asset_class="stock", timeframe="1h")
    assert result is not None and result.total_trades == 1
    trade = result.trades[0]
    assert trade.exit_reason == "perf_time_stop_1hr", (
        f"stock floor (~0.2%) must cut a +0.1% trade at the 2hr mark, "
        f"got {trade.exit_reason}"
    )


# =============================================================================
# 4. Daily-budget position-value clamp
# =============================================================================

def test_daily_budget_clamp_shrinks_position_after_prior_losses():
    """Simulate a losing trade earlier in the same calendar day that eats
    most of the daily loss budget, then confirm a second entry's position
    size is clamped to the loss budget remaining rather than the plain
    capital*max_position_pct sizing.

    With the default MAX_POSITION_PCT (2%), a single trade's max possible
    loss is capped at 2% of capital — far too small to meaningfully dent a
    15% daily budget (MAX_DAILY_LOSS_PCT) no matter how it exits. To
    exercise the clamp deterministically without dozens of synthetic
    losing trades, MAX_POSITION_PCT is temporarily widened so one
    gap-through-stop loss can consume most of today's budget, then
    restored. The math below is chosen so trade #1's loss lands at exactly
    14% of starting capital (daily budget 15%, so $100 of budget remains)
    and trade #2's unclamped risk clearly exceeds that $100 remainder.
    """
    from intelligence.backtester import Backtester
    import config

    class _TwoShotStrategy:
        """Fires signal #1 on its very first analyze() call, then again on
        a specific later call index chosen to land well after trade #1 has
        already closed (already_in would otherwise silently swallow it)."""
        def __init__(self, fire_at_calls=(0, 5)):
            self.strategy_name = "dummy_two_shot"
            self.stop_loss_pct = 5.0
            self.take_profit_pct = 50.0
            self._call_idx = -1
            self._fire_at_calls = set(fire_at_calls)

        def analyze(self, symbol, candles, market_condition="unknown"):
            from strategies.base_strategy import TradeSignal
            self._call_idx += 1
            if self._call_idx not in self._fire_at_calls:
                return None
            return TradeSignal(
                symbol=symbol, direction="long", score=0.9,
                strategy_name=self.strategy_name,
                stop_loss_pct=self.stop_loss_pct,
                take_profit_pct=self.take_profit_pct,
            )

        def check_custom_exit(self, symbol, candles, direction, meta):
            return None

    n_lead = 20
    # call idx 0 -> bar i=20 (signal #1). Entry #1 at i=21, open=100, SL=95.
    # i=22: price gaps to 72 -> stop_loss hit, gap-fill exit_price=72 (sub-1
    # patch), qty=50 (pos_val=5000 at 50% MAX_POSITION_PCT) -> pnl=-1400
    # (exactly 14% of the $10,000 starting capital).
    # call idx 5 -> bar i=25 (signal #2, well after trade #1 already closed).
    # Entry #2 at i=26, open=72. Unclamped pos_val would be ~43% of
    # capital-after-loss ($8600*0.5=$4300); remaining daily budget is only
    # $100 ($1500 - $1400 already lost) -> clamp must shrink it to
    # $100 / 0.05 = $2000.
    prices = (
        [100.0] * n_lead
        + [100.0, 100.0, 72.0]
        + [72.0] * 10
    )
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="15min", tz="UTC")
    df = pd.DataFrame({
        "open": prices, "high": [p + 0.01 for p in prices],
        "low": [p - 0.01 for p in prices], "close": prices,
        "volume": 1000.0,
    }, index=idx)

    bt = Backtester(starting_capital=10_000.0)
    strategy_obj = _TwoShotStrategy()
    _orig_max_pos = config.MAX_POSITION_PCT
    config.MAX_POSITION_PCT = 50.0
    try:
        with _trailing_stop_disabled():
            result = bt._simulate(
                "SYNTH_CLAMP", df, "dummy_two_shot", strategy_obj,
                starting_capital=10_000.0, timeframe="15m", asset_class="crypto",
                commission_pct=0.0, slippage_pct=0.0,
            )
    finally:
        config.MAX_POSITION_PCT = _orig_max_pos

    assert result is not None and result.total_trades == 2, (
        f"expected 2 trades (loser + clamped second entry), got "
        f"{result.total_trades if result else None}"
    )
    trade1, trade2 = result.trades[0], result.trades[1]
    assert trade1.pnl < 0, "first trade must be the realized loser that burns the daily budget"
    assert abs(trade1.pnl - (-1400.0)) < 1.0, (
        f"expected trade #1's loss to be -1400.0 (14% of capital) by design, got {trade1.pnl}"
    )

    unclamped_pos_val = 4300.0   # capital-after-loss (8600) * 0.5
    assert trade2.position_value < unclamped_pos_val, (
        f"second entry's position_value ({trade2.position_value}) must be "
        f"clamped below the unclamped size (~{unclamped_pos_val}) given the "
        f"prior realized loss ate into today's remaining loss budget"
    )
    assert abs(trade2.position_value - 2000.0) < 1.0, (
        f"expected clamp to shrink position_value to remaining_budget(100)/"
        f"effective_sl_pct(0.05) = 2000.0, got {trade2.position_value}"
    )


def main():
    tests = [
        test_gap_through_stop_fills_at_worse_of_open_and_stop_long,
        test_no_gap_stop_loss_still_fills_at_nominal_stop_long,
        test_gap_through_stop_fills_at_worse_of_open_and_stop_short,
        test_take_profit_exit_still_fills_at_nominal_tp_unaffected,
        test_early_loss_fires_once_on_confirmed_decline,
        test_early_loss_does_not_fire_when_price_stabilizes,
        test_crypto_slow_green_trade_survives_2hr_floor,
        test_stock_same_slow_green_trade_is_cut_by_2hr_floor,
        test_daily_budget_clamp_shrinks_position_after_prior_losses,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} lifecycle-correctness patch tests passed")


if __name__ == "__main__":
    main()
