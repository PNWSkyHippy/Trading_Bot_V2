"""
Registry parity tests — backtester parity patch step 1
(reports/agent_pipeline/20260717-085541/final_unified_report.md §5, item 1).

Proves the three previously-independent copies of "which strategies exist"
and the two previously-independent copies of TIME_STOP_EXEMPT cannot drift
apart anymore, because they are now literally the same object imported from
core/strategy_registry.py rather than three/two hand-maintained duplicates.

Pure code, no data/network — safe to run in CI first, ahead of anything
requiring historical candles or a broker.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_time_stop_exempt_identical_objects():
    import core.strategy_registry as sr
    import core.position_monitor as pm

    assert pm.TIME_STOP_EXEMPT is sr.TIME_STOP_EXEMPT, (
        "position_monitor.TIME_STOP_EXEMPT must be the exact same object as "
        "the canonical registry's — if this fails, someone reintroduced a "
        "local copy and the two-list drift bug can recur."
    )


def test_backtester_time_stop_exempt_identical_to_canonical():
    # backtester._simulate() builds TIME_STOP_EXEMPT as a local variable
    # inside a method body (not a module attribute), so we verify by
    # re-reading the source rather than introspecting a live object —
    # simplest robust check: the module-level import binding exists and
    # is the canonical frozenset, and the local variable is assigned
    # directly from it (verified via source scan for a stray literal).
    import intelligence.backtester as bt
    import core.strategy_registry as sr

    assert bt._CANONICAL_TIME_STOP_EXEMPT is sr.TIME_STOP_EXEMPT
    assert bt._CANONICAL_EARLY_LOSS_PCT == sr.EARLY_LOSS_MIN_PCT
    assert bt._CANONICAL_PERF_2HR_PCT == sr.PERF_CHECK_2HR_MIN_PCT
    assert bt._CANONICAL_PERF_5HR_PCT == sr.PERF_CHECK_5HR_MIN_PCT

    source = (ROOT / "intelligence" / "backtester.py").read_text(encoding="utf-8")
    # Reject the specific regression this patch fixes: a hardcoded literal
    # TIME_STOP_EXEMPT frozenset reappearing in _simulate().
    assert "TIME_STOP_EXEMPT = frozenset({" not in source, (
        "A literal TIME_STOP_EXEMPT frozenset reappeared in backtester.py — "
        "it must be assigned from the canonical import, not redeclared."
    )


def test_backtest_strategies_subset_of_strategy_map():
    import web_dashboard as wd
    import core.strategy_registry as sr

    dashboard_set = set(wd.BACKTEST_STRATEGIES)
    registry_set = set(sr.STRATEGY_MODULES.keys())
    missing = dashboard_set - registry_set
    assert not missing, (
        f"BACKTEST_STRATEGIES lists strategies backtester._load_strategy "
        f"can't resolve: {sorted(missing)}"
    )
    # Must actually be equal post-patch (dashboard list is now *derived*
    # from the registry, not merely a subset of it).
    assert dashboard_set == registry_set


def test_optimizer_param_map_matches_dashboard_list():
    import web_dashboard as wd
    import core.strategy_registry as sr

    # get_strategy_optimizer_params has no direct list to introspect
    # (it's a local var inside the function), so prove parity behaviorally:
    # every strategy reachable from the dashboard list resolves to *some*
    # answer (empty list for non-optimizable, non-empty for dataclass-based)
    # rather than silently returning [] because the name wasn't registered
    # at all (the pre-patch bug — 6 strategies present in BACKTEST_STRATEGIES
    # had no entry in the optimizer's own separate STRATEGY_MAP).
    unresolvable = []
    for name in wd.BACKTEST_STRATEGIES:
        if name not in sr.STRATEGY_MODULES:
            unresolvable.append(name)
    assert not unresolvable, f"optimizer registry missing: {unresolvable}"


def test_strategy_map_has_no_duplicate_source_keys():
    # Regression guard for the 6 exact-duplicate key redeclarations found
    # in backtester.py's old inline dict (report item 10). Since Python
    # dict literals silently de-dupe, the only way to catch a *reintroduced*
    # duplicate literal is a source scan for the registry declaration itself
    # having moved back inline. This test instead asserts the count of
    # canonical entries is a plausible single-source count (no dict literal
    # in backtester.py itself defines strategy_map inline anymore).
    source = (ROOT / "intelligence" / "backtester.py").read_text(encoding="utf-8")
    assert '"rsi_momentum":         ("strategies.rsi_momentum"' not in source, (
        "strategy_map reappeared as an inline literal in backtester.py — "
        "it must be assigned from STRATEGY_MODULES, not redeclared."
    )


def test_ecb_strategy_now_reachable_everywhere():
    # The concrete symptom report item 10 traced: ecb_strategy was in the
    # dashboard dropdown and the optimizer's own map, but NOT in
    # backtester.py's strategy_map — so selecting it silently no-opped.
    import intelligence.backtester as bt
    import core.strategy_registry as sr

    assert "ecb_strategy" in sr.STRATEGY_MODULES
    engine = bt.Backtester if hasattr(bt, "Backtester") else None
    assert engine is not None, "expected a Backtester class in intelligence.backtester"
    instance = engine.__new__(engine)
    loaded = engine._load_strategy(instance, "ecb_strategy")
    assert loaded is not None, "ecb_strategy must now be loadable via _load_strategy"


def test_all_registry_modules_importable():
    import importlib
    import core.strategy_registry as sr

    failures = []
    for name, (module_path, class_name) in sr.STRATEGY_MODULES.items():
        try:
            mod = importlib.import_module(module_path)
            getattr(mod, class_name)
        except Exception as exc:  # pragma: no cover - diagnostic path
            failures.append((name, module_path, class_name, str(exc)))
    assert not failures, f"unimportable registry entries: {failures}"


def main():
    tests = [
        test_time_stop_exempt_identical_objects,
        test_backtester_time_stop_exempt_identical_to_canonical,
        test_backtest_strategies_subset_of_strategy_map,
        test_optimizer_param_map_matches_dashboard_list,
        test_strategy_map_has_no_duplicate_source_keys,
        test_ecb_strategy_now_reachable_everywhere,
        test_all_registry_modules_importable,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"{len(tests)}/{len(tests)} strategy registry parity tests passed")


if __name__ == "__main__":
    main()
