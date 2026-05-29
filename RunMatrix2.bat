@echo off
cd /d C:\Users\Linda\trading_bot_v2

echo.
echo ================================================================
echo   STRATEGY MATRIX BATCH  --  all 30 strategies
echo   Tool: tools\run_backtest_matrix.py
echo   Phase 2 overhaul 2026-05-26
echo ================================================================
echo.


	echo Map 
python tools\run_backtest_matrix.py --asset stock --strategy btc_v6_chandelier --sides all --max-symbols 25 --max-combos 17 --timeframe 5m
python tools\run_backtest_matrix.py --asset stock --strategy btc_v6_chandelier --sides all --max-symbols 25 --max-combos 17 --timeframe 1h
python tools\run_backtest_matrix.py --asset stock --strategy rsi_dip_spike_v4 --sides all --max-symbols 25 --max-combos 17 --timeframe 5m
python tools\run_backtest_matrix.py --asset stock --strategy mr_03_fbs --sides all --max-symbols 25 --max-combos 17 --timeframe 5m
python tools\run_backtest_matrix.py --asset stock --strategy rsi_dip_simple --sides all --max-symbols 25 --max-combos 17 --timeframe 1h

echo.
echo ================================================================
echo   ALL DONE -- check reports\backtest_matrix\ for CSVs
echo ================================================================
echo.
pause
