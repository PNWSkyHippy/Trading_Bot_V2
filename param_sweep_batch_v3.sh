#!/bin/bash
cd /mnt/c/Users/Linda/trading_bot_v2

PYTHON="venv312/Scripts/python.exe"
SCRIPT="./Scripts/param_sweep.py"

# ============================================================
#  PARAM SWEEP BATCH v3  (2026-05-25)
#  Fine-tune grid sweeps — tight ranges around v2 optima
#  Using --method matrix (exhaustive grid, not annealing)
#
#  v2 optima found:
#    orb_breakout        SL=2.1  TP=4.2   (stock 1h)
#    adaptive_regime     SL=2.1  TP=4.2   (stock 1h)
#    bollinger_squeeze   SL=3.5  TP=10.3  (stock 1h)
#    btc_v6_chandelier   atr=7.0 rsi=35   (stock 1h)
#    btc_v6_chandelier   atr=5.5 rsi=45   (crypto 1d)
#    rsi_dip_simple      os=30   exit=80  (stock 1d)
#    rsi_dip_simple      os=26   exit=82.5 (crypto 1d)
# ============================================================

# -----------------------------------------------------------
# orb_breakout -- tight matrix around 2.1/4.2
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy orb_breakout \
    --param stop_loss_pct=1.5:2.8:0.1 \
    --param take_profit_pct=3.2:5.5:0.15 \
    --symbols MSFT,META,GOOGL,AMZN \
    --timeframe 1h --days 365 --asset-class stock \
    --direction both \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# adaptive_regime -- tight matrix around 2.1/4.2
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy adaptive_regime \
    --param stop_loss_pct=1.5:2.8:0.1 \
    --param take_profit_pct=3.2:5.5:0.15 \
    --symbols CHPT,TSLA,LRCX,PLTR,ACHR,RIVN,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction long \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# bollinger_squeeze stocks -- tight matrix around 3.5/10.3
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy bollinger_squeeze \
    --param stop_loss_pct=2.8:4.2:0.15 \
    --param take_profit_pct=8.5:12.5:0.25 \
    --symbols TSLA,AMD,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction both \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# btc_v6_chandelier stocks -- tight matrix around atr=7.0 rsi=35
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy btc_v6_chandelier \
    --param atr_mult=5.5:8.0:0.25 \
    --param rsi_thresh=30.0:42.5:2.5 \
    --symbols CLSK,MARA,CRM,NOC,OPEN,TSLA,NVDA \
    --timeframe 1h --days 365 --asset-class stock \
    --direction long \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# btc_v6_chandelier crypto -- tight matrix around atr=5.5 rsi=45
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy btc_v6_chandelier \
    --param atr_mult=4.0:7.0:0.25 \
    --param rsi_thresh=37.5:52.5:2.5 \
    --symbols FIL/USD,HT/USD,AXS/USD,BTC/USD,ETH/USD,SOL/USD \
    --timeframe 1d --days 365 --asset-class crypto \
    --direction long \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# rsi_dip_simple stocks -- tight matrix around os=30 exit=80
# (PF=19.5 consistency=1.00 -- nail this down precisely)
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy rsi_dip_simple \
    --param rsi_oversold=24.0:36.0:1.0 \
    --param rsi_exit=72.0:88.0:2.0 \
    --symbols AMAT,BIIB,LUNR,MPWR,NVDA,AMD,TSLA \
    --timeframe 1d --days 730 --asset-class stock \
    --direction long \
    --method matrix \
    --metric profit_factor

# -----------------------------------------------------------
# rsi_dip_simple crypto -- tight matrix around os=26 exit=82.5
# -----------------------------------------------------------
$PYTHON $SCRIPT --strategy rsi_dip_simple \
    --param rsi_oversold=20.0:32.0:1.0 \
    --param rsi_exit=75.0:90.0:2.0 \
    --symbols BTC/USD,ETH/USD,SOL/USD,BONK/USD,TRUMP/USD \
    --timeframe 1d --days 730 --asset-class crypto \
    --direction long \
    --method matrix \
    --metric profit_factor
