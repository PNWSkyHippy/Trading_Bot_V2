import time

import web_dashboard


def _bar(timestamp, price=100.0):
    return {
        "time": timestamp,
        "open": price,
        "high": price + 1,
        "low": price - 1,
        "close": price,
        "volume": 10,
    }


def _snapshot(minute_bars, tick_bars):
    return {
        "ok": True,
        "bars": {"NQ": minute_bars},
        "emt_strategies": {"NQ": {"enabled": True}},
        "emt_overlays": {"NQ": {"tick_bars_data": tick_bars}},
    }


def test_stale_emt_ticks_fall_back_to_minute_bars():
    now = int(time.time())
    minutes = [_bar(now - (24 - index) * 60) for index in range(25)]
    stale_ticks = [_bar(now - 3600 - index) for index in range(20)]
    bars = web_dashboard._scanner_bars_for_chart(
        "NQ", "5m", 300, snapshot=_snapshot(minutes, stale_ticks)
    )
    assert len(bars) >= 5
    assert bars[-1]["time"] > now - 600


def test_fresh_emt_ticks_are_used_when_cache_is_ready():
    now = int(time.time())
    minutes = [_bar(now - (24 - index) * 60) for index in range(25)]
    ticks = [_bar(now - (19 - index) * 10) for index in range(20)]
    bars = web_dashboard._scanner_bars_for_chart(
        "NQ", "5m", 300, snapshot=_snapshot(minutes, ticks)
    )
    assert len(bars) == 20
    assert bars[-1]["time"] == ticks[-1]["time"]
