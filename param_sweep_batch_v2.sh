#!/bin/bash
cd /mnt/c/Users/Linda/trading_bot_v2

PYTHON="venv312/Scripts/python.exe"
SCRIPT="./Scripts/param_sweep.py"

# ============================================================
#  PARAM SWEEP BATCH v2  (2026-05-25)
#
#  Part A: Initial sweeps that crashed before saving
#          btc_v6_chandelier + rsi_dip_simple
#
#  Part B: Fine-tune grids for confirmed winners
#          orb_breakout, adaptive_regime, bollinger_squeeze
# ============================================================

# ============================================================
#  PART A -- Missing initial sweeps
# ============================================================

# btc_v6_chandelier -- stocks 1h long
$PYTHON $SCRIPT --strategy btc_v6_chandelier \
    --param atr_mult=2.5:8.0:0.5 \
    --param rsi_thresh=35.0:55.0:2.5 \
    --symbols CLSK,MARA,CRM,NOC,OPEN,TSLA,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction long \
    --method annealing --iterations 60 \
    --metric profit_factor

# btc_v6_chandelier -- crypto 1d long
$PYTHON $SCRIPT --strategy btc_v6_chandelier \
    --param atr_mult=2.5:8.0:0.5 \
    --param rsi_thresh=35.0:55.0:2.5 \
    --symbols FIL/USD,HT/USD,AXS/USD,BTC/USD,ETH/USD,SOL/USD \
    --timeframe 1d --days 365 --asset-class crypto \
    --direction long \
    --method annealing --iterations 60 \
    --metric profit_factor

# rsi_dip_simple -- stocks 1d long (730 days)
$PYTHON $SCRIPT --strategy rsi_dip_simple \
    --param rsi_oversold=22.0:45.0:2.0 \
    --param rsi_exit=65.0:90.0:2.5 \
    --symbols AMAT,BIIB,LUNR,MPWR,NVDA,AMD,TSLA \
    --timeframe 1d --days 730 --asset-class stock \
    --direction long \
    --method annealing --iterations 60 \
    --metric profit_factor

# rsi_dip_simple -- crypto 1d long (730 days)
$PYTHON $SCRIPT --strategy rsi_dip_simple \
    --param rsi_oversold=22.0:45.0:2.0 \
    --param rsi_exit=65.0:90.0:2.5 \
    --symbols BTC/USD,ETH/USD,SOL/USD,BONK/USD,TRUMP/USD \
    --timeframe 1d --days 730 --asset-class crypto \
    --direction long \
    --method annealing --iterations 60 \
    --metric profit_factor

# ============================================================
#  PART B -- Fine-tune grids (tight range, exhaustive grid)
# ============================================================

# orb_breakout -- avg PF=8.73 at 2.1/4.2
$PYTHON $SCRIPT --strategy orb_breakout \
    --param stop_loss_pct=1.5:2.8:0.1 \
    --param take_profit_pct=3.2:5.5:0.15 \
    --symbols MSFT,META,GOOGL,AMZN \
    --timeframe 1h --days 365 --asset-class stock \
    --direction both \
    --method grid \
    --metric profit_factor

# adaptive_regime -- avg PF=6.87 at 2.1/4.2
$PYTHON $SCRIPT --strategy adaptive_regime \
    --param stop_loss_pct=1.5:2.8:0.1 \
    --param take_profit_pct=3.2:5.5:0.15 \
    --symbols CHPT,TSLA,LRCX,PLTR,ACHR,RIVN,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction long \
    --method grid \
    --metric profit_factor

# bollinger_squeeze stocks -- avg PF=3.59 at 3.5/10.3
$PYTHON $SCRIPT --strategy bollinger_squeeze \
    --param stop_loss_pct=2.8:4.2:0.15 \
    --param take_profit_pct=8.5:12.5:0.25 \
    --symbols TSLA,AMD,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction both \
    --method grid \
    --metric profit_factor
