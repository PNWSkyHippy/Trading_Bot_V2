@echo off
cd /d C:\Users\Linda\trading_bot_v2

echo.
echo ================================================================
echo   PARAM SWEEP PASS 1 BATCH 2  --  14 strategies, parallel windows
echo   Method : zoom  (coarse 6-bucket -^> fine +-5 around winner)
echo   Launch AFTER RunMatrix.bat finishes strategies 9+ results
echo   Review matrix CSVs first -- comment out PF ^< 1.2 blocks
echo ================================================================
echo.

echo [9] kds_mean_reversion  1d crypto/stock
start "kds_mean_reversion 1d" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy kds_mean_reversion ^
    --param kds_thresh=1.0:3.5:0.25 ^
    --param rsi_os=25.0:45.0:2.0 ^
    --param rsi_ob=55.0:78.0:2.0 ^
    --param sl_mult=1.0:3.0:0.25 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD,AVAX/USD,NVDA,META,TSLA,MSFT ^
    --timeframe 1d --days 365 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [10] ema_ribbon_breakout  1d
start "ema_ribbon_breakout 1d" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy ema_ribbon_breakout ^
    --param adx_min=18.0:30.0:1.0 ^
    --param atr_mult=2.0:5.0:0.25 ^
    --param sl_pct=3.0:9.0:0.5 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT,AMD,INTC ^
    --timeframe 1d --days 365 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [11] rcr_mean_reversion  1d
start "rcr_mean_reversion 1d" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy rcr_mean_reversion ^
    --param z_thresh=1.0:2.5:0.1 ^
    --param stop_atr_k=0.5:2.5:0.25 ^
    --param ac_thresh=-0.20:0.00:0.02 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD,NVDA,META,TSLA,MSFT,AMD ^
    --timeframe 1d --days 365 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [12] ecb_strategy  1h -- entropy collapse breakout
start "ecb_strategy 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy ecb_strategy ^
    --param stop_loss_pct=1.0:3.0:0.2 ^
    --param take_profit_pct=2.0:6.0:0.25 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT ^
    --timeframe 1h --days 180 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [16] swing_trader  stock 1h -- SIGNAL_TUNING stop/tp
start "swing_trader 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy swing_trader ^
    --param stop_loss_pct=1.5:4.0:0.2 ^
    --param take_profit_pct=3.0:9.0:0.3 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM ^
    --timeframe 1h --days 365 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [17] mean_reversion  1h -- SIGNAL_TUNING stop/tp
start "mean_reversion 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy mean_reversion ^
    --param stop_loss_pct=1.0:3.5:0.2 ^
    --param take_profit_pct=2.5:7.0:0.25 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,NVDA,META,TSLA,MSFT,AMD ^
    --timeframe 1h --days 180 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [20] pll_cycle  1d -- PLL cycle detector
start "pll_cycle 1d" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy pll_cycle ^
    --param lock_thresh=0.5:2.0:0.1 ^
    --param sl_pct=2.0:6.0:0.5 ^
    --param center_period=60:120:5 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD ^
    --timeframe 1d --days 365 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [21] mr_02_vef  1h -- volatility exhaustion fade
start "mr_02_vef 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy mr_02_vef ^
    --param sl_mult=1.0:3.5:0.25 ^
    --param tp_mult=1.0:3.5:0.25 ^
    --param atr_spike=1.0:2.5:0.1 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT ^
    --timeframe 1h --days 180 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [23] vdmr_strategy  1h -- velocity deceleration mean reversion
start "vdmr_strategy 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy vdmr_strategy ^
    --param z_entry_thresh=1.5:3.0:0.1 ^
    --param sl_atr_mult=0.5:2.0:0.1 ^
    --param er_max=0.25:0.60:0.05 ^
    --symbols BTC/USD,ETH/USD,SOL/USD,NVDA,META,TSLA,MSFT ^
    --timeframe 1h --days 180 --asset-class crypto ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [24] vwap_confirmed_orb  stock 15m
start "vwap_confirmed_orb 15m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy vwap_confirmed_orb ^
    --param stop_loss_pct=1.0:3.0:0.2 ^
    --param take_profit_pct=2.0:6.0:0.25 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM,SNOW,DDOG ^
    --timeframe 15m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [25] rsi_momentum  stock 15m -- SIGNAL_TUNING stop/tp
start "rsi_momentum 15m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy rsi_momentum ^
    --param stop_loss_pct=1.0:3.5:0.2 ^
    --param take_profit_pct=2.5:7.0:0.25 ^
    --symbols NVDA,META,TSLA,MSFT,AMD,INTC,BTC/USD,ETH/USD,SOL/USD ^
    --timeframe 15m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [26] bollinger_breakout  stock 15m -- SIGNAL_TUNING stop/tp
start "bollinger_breakout 15m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy bollinger_breakout ^
    --param stop_loss_pct=1.5:4.0:0.2 ^
    --param take_profit_pct=3.0:9.0:0.3 ^
    --symbols NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM ^
    --timeframe 15m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [27] hammer_reversal  1h -- wide stop by design, sweep tp
start "hammer_reversal 1h" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy hammer_reversal ^
    --param stop_loss_pct=4.0:12.0:0.5 ^
    --param take_profit_pct=3.0:10.0:0.5 ^
    --symbols NVDA,META,TSLA,MSFT,AMD,BTC/USD,ETH/USD,SOL/USD ^
    --timeframe 1h --days 180 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo [28] scalp_master  stock 5m -- SIGNAL_TUNING tight stops
start "scalp_master 5m" venv312\Scripts\python.exe Scripts\param_sweep.py ^
    --strategy scalp_master ^
    --param stop_loss_pct=0.5:2.0:0.1 ^
    --param take_profit_pct=0.8:3.5:0.1 ^
    --symbols NVDA,META,TSLA,MSFT,AMD,INTC,BTC/USD,ETH/USD ^
    --timeframe 5m --days 60 --asset-class stock ^
    --direction both ^
    --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 ^
    --metric profit_factor

echo.
echo All 14 windows launched -- check each window for progress
echo Results saved to: reports\param_sweep\
echo.
