#!/usr/bin/env bash
set -euo pipefail

cd /opt/trading_bot_v2

echo
echo ================================================================
echo  STRATEGY MATRIX BATCH -- VTM-R crypto
echo  Tool: tools/run_backtest_matrix.py
echo  Kraken/CCXT fallback writes usable candles into CandleStore
echo ================================================================
echo

echo [VTM-R] crypto
venv312/bin/python tools/run_backtest_matrix.py --asset crypto --strategy bmr_357 --timeframes 5m,15,1h --sides all --max-symbols 25 --max-combos 17 --days 180
venv312/bin/python tools/run_backtest_matrix.py --asset crypto --strategy sfr_structural_fakeout --timeframes 5m,15,1h --sides all --max-symbols 25 --max-combos 17 --days 180
venv312/bin/python tools/run_backtest_matrix.py --asset crypto --strategy bollinger_breakout --timeframes 5m,15,1h --sides all --max-symbols 25 --max-combos 17 --days 180



echo
echo ================================================================
echo  ALL DONE -- check reports/backtest_matrix/ for CSVs
echo ================================================================
echo
