from pathlib import Path


PANEL_SOURCE = (
    Path(__file__).resolve().parent / "Html-Files" / "panels.jsx"
).read_text(encoding="utf-8")


def test_emt_frontend_defaults_to_five_am_pacific():
    assert "openingStart: '06:30'" not in PANEL_SOURCE
    assert "openingStart || '06:30'" not in PANEL_SOURCE
    assert "openingStart: '05:00'" in PANEL_SOURCE


def test_emt_timeframe_lock_is_indicator_driven_not_es_hardcoded():
    assert "const emtChartActive = isStrategyFuture" in PANEL_SOURCE
    assert "{emtChartActive ? (" in PANEL_SOURCE
    assert "{symbol === 'ES' ? (" not in PANEL_SOURCE


def test_chart_hydration_cannot_write_strategy_state_without_user_edit():
    guard = "if (!strategyUserEditRef.current[key]) return;"
    post = "panelApi('/api/chart/strategy_config'"
    assert guard in PANEL_SOURCE
    assert PANEL_SOURCE.index(guard) < PANEL_SOURCE.index(post)
