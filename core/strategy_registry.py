"""
=============================================================
  STRATEGY REGISTRY — canonical source of truth
=============================================================
Backtester parity patch, step 1 of the sequence in
reports/agent_pipeline/20260717-085541/final_unified_report.md §6.

Before this module existed, three independently-maintained copies of
"which strategies exist and what module/class implements them" had drifted:
  - intelligence/backtester.py's own strategy_map (39 keys, 6 of them
    exact-duplicate re-declarations of an earlier key in the same dict)
  - web_dashboard.py's BACKTEST_STRATEGIES list (missing several strategies
    that backtester.py could already run, including ecb_strategy, which
    wasn't in backtester.py's map at all despite being selectable elsewhere)
  - web_dashboard.py's get_strategy_optimizer_params() STRATEGY_MAP (a third,
    smaller, independently-typed copy)

And TIME_STOP_EXEMPT existed as two separately-maintained set literals
(core/position_monitor.py and intelligence/backtester.py) that had already
drifted apart once before (a prior audit's comment in position_monitor.py
says the two "MUST mirror" each other) and had drifted apart again — the
backtester's copy exempted 11 strategies from generic lifecycle time stops
that live does not exempt.

This module makes each of those a single canonical definition. Consumers
import from here instead of re-declaring their own copy.

Why: report 20260717-085541 item 10 traces the exact "strategy missing from
dashboard/backtester/optimizer" symptom to this drift, and item 5's third
bullet traces backtest results being systematically biased toward clipping
trades early to the TIME_STOP_EXEMPT drift specifically.
"""

from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# Canonical (module_path, class_name) registry.
#
# This is the union of every strategy previously reachable from any of the
# three drifted copies. All of these modules/classes were already confirmed
# importable (they were live in at least one of the three prior lists);
# adding a strategy here makes it consistently reachable from backtester,
# dashboard dropdown, and optimizer everywhere instead of inconsistently.
# ---------------------------------------------------------------------------
STRATEGY_MODULES: Dict[str, Tuple[str, str]] = {
    "rsi_momentum":            ("strategies.rsi_momentum",            "RSIMomentum"),
    "bollinger_breakout":      ("strategies.bollinger_breakout",      "BollingerBreakout"),
    "bollinger_squeeze":       ("strategies.bollinger_squeeze",       "BollingerSqueeze"),
    "ema_crossover":           ("strategies.ema_crossover",           "EMACrossover"),
    "mean_reversion":          ("strategies.mean_reversion",          "MeanReversion"),
    "scalp_master":            ("strategies.scalp_master",            "ScalpMaster"),
    "swing_trader":            ("strategies.swing_trader",            "SwingTrader"),
    "grid_bot":                ("strategies.grid_bot",                "GridBot"),
    "dca_accumulator":         ("strategies.dca_accumulator",         "DCAAccumulator"),
    "vwap_momentum":           ("strategies.vwap_momentum",           "VWAPMomentum"),
    "vwap_confirmed_orb":      ("strategies.vwap_confirmed_orb",      "VwapConfirmedOrb"),
    "hammer_reversal":         ("strategies.hammer_reversal",         "HammerReversal"),
    "orb_breakout":            ("strategies.orb_breakout",            "ORBBreakout"),
    "adaptive_regime":         ("strategies.adaptive_regime",         "AdaptiveRegime"),
    "ecb_strategy":            ("strategies.ecb_strategy",            "ECBStrategy"),
    "vdmr_strategy":           ("strategies.vdmr_strategy",           "VDMRStrategy"),
    "vtmr_strategy":           ("strategies.vtmr_strategy",           "VTMRStrategy"),
    "rsi_dip_spike_v4":        ("strategies.rsi_dip_spike_v4",        "RSIDipSpikeV4Strategy"),
    "mr_02_vef":               ("strategies.mr_02_vef_strategy",      "MR02VEFStrategy"),
    "mr_03_fbs":               ("strategies.mr_03_fbs_strategy",      "MR03FBSStrategy"),
    "mr_04_fvg":               ("strategies.mr_04_fvg_strategy",      "MR04FVGStrategy"),
    "btc_v6_chandelier":       ("strategies.btc_v6_chandelier",       "BTCV6ChandelierStrategy"),
    "rsi_dip_simple":          ("strategies.rsi_dip_simple",          "RSIDipSimpleStrategy"),
    "pll_cycle":               ("strategies.pll_cycle",               "PLLCycleStrategy"),
    "pll_cycle_martingale":    ("strategies.pll_cycle",               "PLLCycleMartingaleStrategy"),
    "pll_conservative_eth_1h": ("strategies.pll_cycle",               "PLLConservativeETHStrategy"),
    "td_day_trader_v3":        ("strategies.traderdev_day_trader_v3", "TraderDevDayTraderV3Strategy"),
    "td_gridbot_adx15":        ("strategies.traderdev_gridbot_adx15", "TraderDevGridBotADX15"),
    "td_rsi_dip_spike_v4c":    ("strategies.traderdev_rsi_dip_spike_v4c", "TraderDevRSIDipSpikeV4CStrategy"),
    "td_v6_bnb_adx":           ("strategies.traderdev_v6_bnb_adx",    "TraderDevV6BNBADXStrategy"),
    "td_btc_v11":              ("strategies.traderdev_btc_v11",       "TraderDevBTCV11Strategy"),
    "td_f40d_adx":             ("strategies.traderdev_f40d_adx",      "TraderDevF40DADXStrategy"),
    "kds_mean_reversion":      ("strategies.kds_mean_reversion",      "KDSMeanReversionStrategy"),
    "ema_ribbon_breakout":     ("strategies.ema_ribbon_breakout",     "EMARibbonBreakoutStrategy"),
    "rcr_mean_reversion":      ("strategies.rcr_mean_reversion",      "RCRMeanReversionStrategy"),
    "fels_strategy":           ("strategies.fels_strategy",           "FELSStrategy"),
    "sfr_structural_fakeout":  ("strategies.sfr_structural_fakeout",  "SFRStrategy"),
    "tema_crossover":          ("strategies.tema_crossover",          "TEMACrossoverStrategy"),
    "bmr_357":                 ("strategies.bmr357_strategy",         "BMR357Strategy"),
    "vbm_strategy":            ("strategies.vbm_strategy",            "VBMStrategy"),
}

# ---------------------------------------------------------------------------
# Time-stop exemption set — canonical value is core/position_monitor.py's
# live set (the actual trading system), NOT the backtester's previously
# independent, over-broad copy. Live behavior is unchanged by this file
# existing (position_monitor.py's effective set is numerically identical
# to what it declared inline before); only the backtester's copy shrinks
# to match, closing report item 5's eleven-strategy over-exemption drift.
# ---------------------------------------------------------------------------
TIME_STOP_EXEMPT: FrozenSet[str] = frozenset({
    "grid_bot", "dca_accumulator",
    "rsi_dip_spike_v4",
    "hammer_reversal",
    "mr_02_vef", "mr_03_fbs",
    "pll_cycle", "pll_cycle_martingale",
    "scalp_master",
    "rsi_dip_simple", "breakout_scanner",
    "rcr_mean_reversion", "funding_scanner",
    "btc_v6_chandelier",
    "orb_breakout",
    "vwap_confirmed_orb",
    "ema_crossover",
    "rsi_momentum",
    "bollinger_breakout",
    "vwap_momentum",
    "fels_strategy",
    "swing_trader",
    "mean_reversion",
    "bmr_357",
    "vtmr_strategy",
})

# ---------------------------------------------------------------------------
# Lifecycle threshold constants — canonical values match
# core/position_monitor.py's live module-level constants (not config.py's
# EARLY_LOSS_MIN_PCT, which is stale/shadowed and no longer read by
# position_monitor.py itself). Backtester.py previously re-declared these
# as separate literals commented "exact mirrors of position_monitor
# constant values" — now there is exactly one place they can drift from.
# ---------------------------------------------------------------------------
EARLY_LOSS_MIN_PCT: float = -0.5
PERF_CHECK_2HR_MIN_PCT: float = 0.2
PERF_CHECK_5HR_MIN_PCT: float = 1.0
