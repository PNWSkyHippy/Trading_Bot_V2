@echo off
cd /d C:\Users\Linda\trading_bot_v2

echo.
echo ================================================================
echo   STRATEGY MATRIX BATCH  --  all 30 strategies
echo   Tool: tools\run_backtest_matrix.py
echo   Phase 2 overhaul 2026-05-26
echo ================================================================
echo.
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

echo [30/30] map_strategy  (backtest only -- disabled live)
python tools\run_backtest_matrix.py --asset crypto --strategy map_strategy--sides all --max-symbols 25 --max-combos 17

echo.
echo ================================================================
echo   ALL DONE -- check reports\backtest_matrix\ for CSVs
echo ================================================================
echo.
pause
