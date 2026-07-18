"""
CandleStore incremental-refresh retention test — Step 6 (Patch B data
contract), reconstructing a fix documented in
reports/agent_pipeline/20260716-082429/final_unified_report.md §14 that was
lost from the working tree (confirmed via git forensics: the file's only
recent commit, bbabe2d4, only touches the F11 timezone helpers and never
carried this fix forward; no stash, no other checkout holds it).

Bug: CandleStore.save()'s prune step deleted every cached row older than the
*oldest row of the incoming batch* (intelligence/candle_store.py, prior to
this patch). A routine short incremental refresh (e.g. a 300-bar hourly
top-up starting a few days ago) would therefore silently erase most of a
much longer existing backtest-window cache (e.g. a 720-bar/30-day hourly
history) on every save, because the batch's own first_ts is recent.

Fix: prune relative to a fixed per-timeframe retention horizon (import
`_RETENTION_DAYS`) measured back from the newest bar now on file, not from
the incoming batch's oldest row.

This test proves the fix directly: seed the store with a long-window
history, then perform a short incremental "top-up" save covering only the
last few bars, and assert the long history survives.
"""

import sys
import tempfile
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _hourly_df(start, n, price=100.0):
    idx = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({
        "open": price, "high": price + 0.1, "low": price - 0.1,
        "close": price, "volume": 10.0,
    }, index=idx)


def _make_store():
    from intelligence.candle_store import CandleStore
    tmp_dir = tempfile.mkdtemp(prefix="candle_store_retention_test_")
    db_path = os.path.join(tmp_dir, "test_candles.db")
    return CandleStore(db_path=db_path)


def test_short_incremental_refresh_does_not_erase_long_history():
    store = _make_store()

    # Seed a 720-bar (30-day) hourly backtest-window cache ending "now" so
    # CandleStore.load()'s real-wall-clock freshness cutoff includes it.
    end = pd.Timestamp.utcnow().tz_localize(None).floor("h")
    start = end - pd.Timedelta(hours=719)
    long_df = _hourly_df(start, 720)
    written = store.save("SYNTH/USD", "1h", long_df)
    assert written == 720

    before = store.load("SYNTH/USD", "1h", days=60)
    assert before is not None and len(before) == 720

    # Now perform a routine short incremental refresh: just the most recent
    # 5 bars, continuing on directly from the seeded history (no gap) so the
    # "newest bar on file" doesn't change and the retention window stays
    # anchored where it was.
    refresh_start = long_df.index[-1] + pd.Timedelta(hours=1)
    short_df = _hourly_df(refresh_start, 5)
    written2 = store.save("SYNTH/USD", "1h", short_df)
    assert written2 == 5

    after = store.load("SYNTH/USD", "1h", days=60)
    assert after is not None
    assert len(after) == 725, (
        f"expected all 720 original bars + 5 new bars to survive, got {len(after)} "
        "— the incremental refresh incorrectly pruned older history"
    )


def test_retention_horizon_still_prunes_bars_beyond_the_window():
    store = _make_store()

    # Seed bars far older than the 1h retention horizon (730 days), plus a
    # recent batch ending "now". A single save() call carrying both an
    # ancient and a recent bar should retain only what's within the horizon
    # of the newest bar in that same save.
    now = pd.Timestamp.utcnow().tz_localize(None).floor("h")
    ancient_df = _hourly_df(now - pd.Timedelta(days=2000), 3)
    recent_df = _hourly_df(now - pd.Timedelta(hours=2), 3)
    combined = pd.concat([ancient_df, recent_df])

    store.save("SYNTH2/USD", "1h", combined)

    all_rows = store.load("SYNTH2/USD", "1h", days=5000)
    assert all_rows is not None
    assert len(all_rows) == 3, (
        f"expected only the 3 recent bars to survive pruning beyond the "
        f"retention horizon, got {len(all_rows)}"
    )
    assert all_rows.index.min() >= recent_df.index.min().tz_localize(None)


def test_two_widely_separated_incremental_refreshes_both_survive():
    """Two short refreshes in a row, each covering only their own recent
    tail, must not prune each other — proving the horizon tracks the
    newest bar on file across repeated incremental saves, not just once."""
    store = _make_store()

    end = pd.Timestamp.utcnow().tz_localize(None).floor("h") - pd.Timedelta(hours=20)
    start = end - pd.Timedelta(hours=499)
    base_df = _hourly_df(start, 500)
    store.save("SYNTH3/USD", "1h", base_df)

    refresh1_start = base_df.index[-1] + pd.Timedelta(hours=1)
    refresh1_df = _hourly_df(refresh1_start, 10)
    store.save("SYNTH3/USD", "1h", refresh1_df)

    refresh2_start = refresh1_df.index[-1] + pd.Timedelta(hours=1)
    refresh2_df = _hourly_df(refresh2_start, 10)
    store.save("SYNTH3/USD", "1h", refresh2_df)

    result = store.load("SYNTH3/USD", "1h", days=60)
    assert result is not None
    assert len(result) == 520, (
        f"expected 500 base + 10 + 10 incremental bars to all survive, got {len(result)}"
    )


def main():
    tests = [
        test_short_incremental_refresh_does_not_erase_long_history,
        test_retention_horizon_still_prunes_bars_beyond_the_window,
        test_two_widely_separated_incremental_refreshes_both_survive,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} candle store incremental retention tests passed")


if __name__ == "__main__":
    main()
