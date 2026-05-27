@echo off
cd /d C:\Users\Linda\trading_bot_v2

echo.
echo ================================================================
echo   STRATEGY MATRIX BATCH  --  all 30 strategies
echo   Tool: tools\run_backtest_matrix.py
echo   Phase 2 overhaul 2026-05-26
echo ================================================================
echo.

echo [1/30]  adaptive_regime
python tools\run_backtest_matrix.py --asset stock  --strategy adaptive_regime      --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy adaptive_regime      --sides all --max-symbols 25 --max-combos 17

echo [2/30]  orb_breakout
python tools\run_backtest_matrix.py --asset stock  --strategy orb_breakout         --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy orb_breakout         --sides all --max-symbols 25 --max-combos 17

echo [3/30]  bollinger_squeeze
python tools\run_backtest_matrix.py --asset stock  --strategy bollinger_squeeze    --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy bollinger_squeeze    --sides all --max-symbols 25 --max-combos 17

echo [4/30]  rsi_dip_spike_v4
python tools\run_backtest_matrix.py --asset stock  --strategy rsi_dip_spike_v4    --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy rsi_dip_spike_v4    --sides all --max-symbols 25 --max-combos 17

echo [5/30]  btc_v6_chandelier
python tools\run_backtest_matrix.py --asset stock  --strategy btc_v6_chandelier   --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy btc_v6_chandelier   --sides all --max-symbols 25 --max-combos 17

echo [6/30]  rsi_dip_simple
python tools\run_backtest_matrix.py --asset stock  --strategy rsi_dip_simple      --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy rsi_dip_simple      --sides all --max-symbols 25 --max-combos 17

echo [7/30]  vwap_momentum
python tools\run_backtest_matrix.py --asset stock  --strategy vwap_momentum       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy vwap_momentum       --sides all --max-symbols 25 --max-combos 17

echo [8/30]  mr_03_fbs
python tools\run_backtest_matrix.py --asset stock  --strategy mr_03_fbs           --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy mr_03_fbs           --sides all --max-symbols 25 --max-combos 17

echo [9/30]  kds_mean_reversion
python tools\run_backtest_matrix.py --asset stock  --strategy kds_mean_reversion  --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy kds_mean_reversion  --sides all --max-symbols 25 --max-combos 17

echo [10/30] ema_ribbon_breakout
python tools\run_backtest_matrix.py --asset stock  --strategy ema_ribbon_breakout --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy ema_ribbon_breakout --sides all --max-symbols 25 --max-combos 17

echo [11/30] rcr_mean_reversion
python tools\run_backtest_matrix.py --asset stock  --strategy rcr_mean_reversion  --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy rcr_mean_reversion  --sides all --max-symbols 25 --max-combos 17

echo [12/30] ecb_strategy
python tools\run_backtest_matrix.py --asset stock  --strategy ecb_strategy        --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy ecb_strategy        --sides all --max-symbols 25 --max-combos 17

echo [13/30] cbae_strategy
python tools\run_backtest_matrix.py --asset stock  --strategy cbae_strategy       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy cbae_strategy       --sides all --max-symbols 25 --max-combos 17

echo [14/30] rare_strategy
python tools\run_backtest_matrix.py --asset stock  --strategy rare_strategy       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy rare_strategy       --sides all --max-symbols 25 --max-combos 17

echo [15/30] fels_strategy
python tools\run_backtest_matrix.py --asset stock  --strategy fels_strategy       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy fels_strategy       --sides all --max-symbols 25 --max-combos 17

echo [16/30] swing_trader
python tools\run_backtest_matrix.py --asset stock  --strategy swing_trader        --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy swing_trader        --sides all --max-symbols 25 --max-combos 17

echo [17/30] mean_reversion
python tools\run_backtest_matrix.py --asset stock  --strategy mean_reversion      --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy mean_reversion      --sides all --max-symbols 25 --max-combos 17

echo [18/30] dca_accumulator
python tools\run_backtest_matrix.py --asset stock  --strategy dca_accumulator     --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy dca_accumulator     --sides all --max-symbols 25 --max-combos 17

echo [19/30] grid_bot
python tools\run_backtest_matrix.py --asset stock  --strategy grid_bot            --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy grid_bot            --sides all --max-symbols 25 --max-combos 17

echo [20/30] pll_cycle
python tools\run_backtest_matrix.py --asset stock  --strategy pll_cycle           --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy pll_cycle           --sides all --max-symbols 25 --max-combos 17

echo [21/30] mr_02_vef
python tools\run_backtest_matrix.py --asset stock  --strategy mr_02_vef           --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy mr_02_vef           --sides all --max-symbols 25 --max-combos 17

echo [22/30] mr_04_fvg
python tools\run_backtest_matrix.py --asset stock  --strategy mr_04_fvg           --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy mr_04_fvg           --sides all --max-symbols 25 --max-combos 17

echo [23/30] vdmr_strategy
python tools\run_backtest_matrix.py --asset stock  --strategy vdmr_strategy       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy vdmr_strategy       --sides all --max-symbols 25 --max-combos 17

echo [24/30] vwap_confirmed_orb
python tools\run_backtest_matrix.py --asset stock  --strategy vwap_confirmed_orb  --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy vwap_confirmed_orb  --sides all --max-symbols 25 --max-combos 17

echo [25/30] rsi_momentum
python tools\run_backtest_matrix.py --asset stock  --strategy rsi_momentum        --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy rsi_momentum        --sides all --max-symbols 25 --max-combos 17

echo [26/30] bollinger_breakout
python tools\run_backtest_matrix.py --asset stock  --strategy bollinger_breakout  --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy bollinger_breakout  --sides all --max-symbols 25 --max-combos 17

echo [27/30] hammer_reversal
python tools\run_backtest_matrix.py --asset stock  --strategy hammer_reversal     --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy hammer_reversal     --sides all --max-symbols 25 --max-combos 17

echo [28/30] scalp_master
python tools\run_backtest_matrix.py --asset stock  --strategy scalp_master        --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy scalp_master        --sides all --max-symbols 25 --max-combos 17

echo [29/30] ema_crossover
python tools\run_backtest_matrix.py --asset stock  --strategy ema_crossover       --sides all --max-symbols 25 --max-combos 17
python tools\run_backtest_matrix.py --asset crypto --strategy ema_crossover       --sides all --max-symbols 25 --max-combos 17

echo [30/30] pll_cycle_martingale  (backtest only -- disabled live)
python tools\run_backtest_matrix.py --asset crypto --strategy pll_cycle_martingale --sides all --max-symbols 25 --max-combos 17

echo.
echo ================================================================
echo   ALL DONE -- check reports\backtest_matrix\ for CSVs
echo ================================================================
echo.
pause
