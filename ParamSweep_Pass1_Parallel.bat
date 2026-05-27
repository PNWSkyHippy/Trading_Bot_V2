@echo off
cd /d C:\Users\Linda\trading_bot_v2

echo.
echo ================================================================
echo   PARAM SWEEP PASS 1  --  8 strategies, parallel windows
echo   Method : zoom  (coarse 6-bucket -^> fine +-5 around winner)
echo   Symbols: 25 stock watchlist
echo   Each strategy opens its own window -- all run simultaneously
echo ================================================================
echo.

echo [1] btc_v6_chandelier  stock 5m  (PF=1.99, 460 trades)
start "btc_v6_chandelier 5m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy btc_v6_chandelier ^
    --param atr_mult=2.0:6.5:0.25 ^
    --param rsi_thresh=30.0:58.0:2.0 ^
    --param ema_fast=8:25:1 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 5m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [2] rsi_dip_simple  stock 5m  (PF=1.72, 592 trades)
start "rsi_dip_simple 5m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy rsi_dip_simple ^
    --param rsi_oversold=15.0:38.0:1.0 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 5m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [3] rsi_dip_spike_v4  stock 5m  (PF=1.56, WR=66%, 284 trades)
start "rsi_dip_spike_v4 5m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy rsi_dip_spike_v4 ^
    --param rsi_oversold=25.0:45.0:2.0 ^
    --param rsi_overbought=68.0:88.0:2.0 ^
    --param sl_atr_mult=1.5:3.5:0.25 ^
    --param tp_atr_mult=1.5:3.5:0.25 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 5m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [4] mr_03_fbs  stock 5m  (PF=1.38, WR=58%, 552 trades)
start "mr_03_fbs 5m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy mr_03_fbs ^
    --param sl_mult=1.0:3.5:0.25 ^
    --param tp_mult=1.0:3.5:0.25 ^
    --param atr_len=8:21:1 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 5m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [5] adaptive_regime  stock 15m  (PF=1.40)
start "adaptive_regime 15m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy adaptive_regime ^
    --param stop_loss_pct=1.0:3.0:0.1 ^
    --param take_profit_pct=2.5:6.0:0.25 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 15m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [6] vwap_momentum  stock 15m  (PF=1.72)
start "vwap_momentum 15m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy vwap_momentum ^
    --param stop_loss_pct=0.8:2.5:0.1 ^
    --param take_profit_pct=1.5:4.5:0.15 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 15m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [7] rsi_dip_simple  stock 1h  (PF=2.66)
start "rsi_dip_simple 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy rsi_dip_simple ^
    --param rsi_oversold=15.0:38.0:1.0 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 1h --days 180 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [8] btc_v6_chandelier  stock 1h  (PF=2.36)
start "btc_v6_chandelier 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy btc_v6_chandelier ^
    --param atr_mult=2.0:6.5:0.25 ^
    --param rsi_thresh=30.0:58.0:2.0 ^
    --param ema_fast=8:25:1 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS ^
    --timeframe 1h --days 180 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo.
echo All 8 windows launched -- check each window for progress
echo Results saved to: reports\param_sweep\
echo.
