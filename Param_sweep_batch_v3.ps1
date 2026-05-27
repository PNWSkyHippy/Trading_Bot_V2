Set-Location C:\Users\Linda\trading_bot_v2

$PYTHON = "venv312\Scripts\python.exe"
$SCRIPT = ".\Scripts\param_sweep.py"

# ============================================================
#  PARAM SWEEP BATCH v3  --  all 30 strategies
#  Phase 2 overhaul 2026-05-26
#
#  HOW TO USE:
#    1. Run run-matrix.bat first and review the CSVs
#    2. Comment out any block where matrix showed PF < 1.3
#    3. For each kept block, swap --symbols with top-edge
#       symbols from that strategy's matrix CSV
#    4. Run this script
#
#  Results: reports\param_sweep\<strategy>_<date>.json
# ============================================================

Write-Host ""
Write-Host "================================================================"
Write-Host "  PARAM SWEEP BATCH v3  --  all 30 strategies"
Write-Host "================================================================"
Write-Host ""

# ============================================================
#  CONFIRMED PERFORMERS  (previously tuned -- re-validate)
# ============================================================

# [1] adaptive_regime  |  stocks 1h long
Write-Host "[1/30] adaptive_regime"
& $PYTHON $SCRIPT --strategy adaptive_regime `
    --param stop_loss_pct=1.5:2.8:0.1 `
    --param take_profit_pct=3.2:5.5:0.15 `
    --symbols CHPT,TSLA,LRCX,PLTR,ACHR,RIVN,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method grid --metric profit_factor

# [2] orb_breakout  |  stocks 1h both
Write-Host "[2/30] orb_breakout"
& $PYTHON $SCRIPT --strategy orb_breakout `
    --param stop_loss_pct=1.5:2.8:0.1 `
    --param take_profit_pct=3.2:5.5:0.15 `
    --symbols MSFT,META,GOOGL,AMZN `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method grid --metric profit_factor

# [3] bollinger_squeeze  |  stocks 1h both
Write-Host "[3/30] bollinger_squeeze"
& $PYTHON $SCRIPT --strategy bollinger_squeeze `
    --param stop_loss_pct=2.8:4.2:0.15 `
    --param take_profit_pct=8.5:12.5:0.25 `
    --symbols TSLA,AMD,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method grid --metric profit_factor

# [4] rsi_dip_spike_v4  |  best live performer
Write-Host "[4/30] rsi_dip_spike_v4"
& $PYTHON $SCRIPT --strategy rsi_dip_spike_v4 `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.5:10.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,NVDA,TSLA `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction long `
    --method annealing --iterations 80 --metric profit_factor

# [5] btc_v6_chandelier  |  stocks 1h long
Write-Host "[5/30] btc_v6_chandelier (stocks)"
& $PYTHON $SCRIPT --strategy btc_v6_chandelier `
    --param atr_mult=3.0:6.0:0.25 `
    --param rsi_thresh=38.0:52.0:2.0 `
    --symbols CLSK,MARA,CRM,NOC,TSLA,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 80 --metric profit_factor

# [5b] btc_v6_chandelier  |  crypto 1d long
Write-Host "[5b/30] btc_v6_chandelier (crypto)"
& $PYTHON $SCRIPT --strategy btc_v6_chandelier `
    --param atr_mult=3.0:6.0:0.25 `
    --param rsi_thresh=38.0:52.0:2.0 `
    --symbols BTC/USD,ETH/USD,SOL/USD `
    --timeframe 1d --days 365 --asset-class crypto `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [6] rsi_dip_simple  |  stocks 1d long
Write-Host "[6/30] rsi_dip_simple (stocks)"
& $PYTHON $SCRIPT --strategy rsi_dip_simple `
    --param rsi_oversold=22.0:38.0:1.0 `
    --param rsi_exit=68.0:88.0:2.0 `
    --symbols AMAT,BIIB,LUNR,MPWR,NVDA,AMD,TSLA `
    --timeframe 1d --days 730 --asset-class stock `
    --direction long `
    --method annealing --iterations 80 --metric profit_factor

# [6b] rsi_dip_simple  |  crypto 1d long
Write-Host "[6b/30] rsi_dip_simple (crypto)"
& $PYTHON $SCRIPT --strategy rsi_dip_simple `
    --param rsi_oversold=22.0:38.0:1.0 `
    --param rsi_exit=68.0:88.0:2.0 `
    --symbols BTC/USD,ETH/USD,SOL/USD `
    --timeframe 1d --days 730 --asset-class crypto `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [7] vwap_momentum  |  stocks 1h both
Write-Host "[7/30] vwap_momentum"
& $PYTHON $SCRIPT --strategy vwap_momentum `
    --param stop_loss_pct=0.8:3.0:0.2 `
    --param take_profit_pct=1.5:6.0:0.25 `
    --symbols AMZN,TSLA,MSFT,GOOGL,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [8] mr_03_fbs  |  8 params -- zoom method
Write-Host "[8/30] mr_03_fbs"
& $PYTHON $SCRIPT --strategy mr_03_fbs `
    --param bb_len=10:60:2:int `
    --param bb_mult=0.7:4.0:0.5 `
    --param snap_bars=1:6:1:int `
    --param ma_len=100:600:20:int `
    --param atr_len=7:42:1:int `
    --param tp_mult=0.6:3.5:0.25 `
    --param sl_mult=0.8:4.5:0.25 `
    --param max_bars=18:108:3:int `
    --symbols AAPL,NVDA,AMD,TSLA,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method zoom --iterations 80 --metric profit_factor

# ============================================================
#  PHASE 2 NEW / OVERHAULED
#  Update --symbols from matrix CSV results before running
# ============================================================

# [9] kds_mean_reversion  |  daily both
Write-Host "[9/30] kds_mean_reversion"
& $PYTHON $SCRIPT --strategy kds_mean_reversion `
    --param sl_mult=0.8:3.5:0.25 `
    --param kds_thresh=1.2:4.0:0.25 `
    --param rsi_os=25.0:45.0:2.5 `
    --param rsi_ob=55.0:75.0:2.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,NVDA,TSLA `
    --timeframe 1d --days 365 --asset-class crypto `
    --direction both `
    --method zoom --iterations 80 --metric profit_factor

# [10] ema_ribbon_breakout  |  1h both (chandelier exit)
Write-Host "[10/30] ema_ribbon_breakout"
& $PYTHON $SCRIPT --strategy ema_ribbon_breakout `
    --param adx_min=15.0:35.0:2.5 `
    --param atr_mult=2.0:5.0:0.25 `
    --param sl_pct=3.0:10.0:0.5 `
    --symbols NVDA,TSLA,AMD,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method zoom --iterations 80 --metric profit_factor

# [11] rcr_mean_reversion  |  1h crypto both
Write-Host "[11/30] rcr_mean_reversion"
& $PYTHON $SCRIPT --strategy rcr_mean_reversion `
    --param stop_loss_pct=1.5:5.0:0.25 `
    --param take_profit_pct=3.0:10.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [12] ecb_strategy
Write-Host "[12/30] ecb_strategy"
& $PYTHON $SCRIPT --strategy ecb_strategy `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [13] cbae_strategy
Write-Host "[13/30] cbae_strategy"
& $PYTHON $SCRIPT --strategy cbae_strategy `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [14] rare_strategy
Write-Host "[14/30] rare_strategy"
& $PYTHON $SCRIPT --strategy rare_strategy `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [15] fels_strategy
Write-Host "[15/30] fels_strategy"
& $PYTHON $SCRIPT --strategy fels_strategy `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [16] swing_trader  |  stocks 1d long
Write-Host "[16/30] swing_trader"
& $PYTHON $SCRIPT --strategy swing_trader `
    --param stop_loss_pct=1.5:5.0:0.25 `
    --param take_profit_pct=3.0:10.0:0.5 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1d --days 730 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [17] mean_reversion  |  stocks 1h
Write-Host "[17/30] mean_reversion"
& $PYTHON $SCRIPT --strategy mean_reversion `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,AAPL,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [18] dca_accumulator  |  crypto 1d long
Write-Host "[18/30] dca_accumulator"
& $PYTHON $SCRIPT --strategy dca_accumulator `
    --param stop_loss_pct=2.0:8.0:0.5 `
    --param take_profit_pct=4.0:15.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,NVDA `
    --timeframe 1d --days 730 --asset-class crypto `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [19] grid_bot  |  crypto 1h both
Write-Host "[19/30] grid_bot"
& $PYTHON $SCRIPT --strategy grid_bot `
    --param stop_loss_pct=1.0:5.0:0.25 `
    --param take_profit_pct=2.0:10.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,BNB/USD `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [20] pll_cycle  |  crypto 1h both
Write-Host "[20/30] pll_cycle"
& $PYTHON $SCRIPT --strategy pll_cycle `
    --param stop_loss_pct=1.5:5.0:0.25 `
    --param take_profit_pct=3.0:10.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [21] pll_cycle_martingale  |  backtest only -- disabled live
Write-Host "[21/30] pll_cycle_martingale"
& $PYTHON $SCRIPT --strategy pll_cycle_martingale `
    --param stop_loss_pct=1.5:5.0:0.25 `
    --param take_profit_pct=3.0:10.0:0.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# ============================================================
#  WATCHLIST / MARGINAL  (comment out if matrix shows PF < 1.3)
# ============================================================

# [22] mr_02_vef
Write-Host "[22/30] mr_02_vef"
& $PYTHON $SCRIPT --strategy mr_02_vef `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [23] mr_04_fvg  (live loser -- only run if matrix shows edge)
Write-Host "[23/30] mr_04_fvg"
& $PYTHON $SCRIPT --strategy mr_04_fvg `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [24] vdmr_strategy
Write-Host "[24/30] vdmr_strategy"
& $PYTHON $SCRIPT --strategy vdmr_strategy `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,BTC/USD,ETH/USD `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [25] vwap_confirmed_orb
Write-Host "[25/30] vwap_confirmed_orb"
& $PYTHON $SCRIPT --strategy vwap_confirmed_orb `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,AMZN `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# ============================================================
#  LEGACY  (comment out if not worth the compute time)
# ============================================================

# [26] rsi_momentum
Write-Host "[26/30] rsi_momentum"
& $PYTHON $SCRIPT --strategy rsi_momentum `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [27] bollinger_breakout
Write-Host "[27/30] bollinger_breakout"
& $PYTHON $SCRIPT --strategy bollinger_breakout `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [28] hammer_reversal
Write-Host "[28/30] hammer_reversal"
& $PYTHON $SCRIPT --strategy hammer_reversal `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1d --days 730 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 --metric profit_factor

# [29] scalp_master
Write-Host "[29/30] scalp_master"
& $PYTHON $SCRIPT --strategy scalp_master `
    --param stop_loss_pct=0.5:2.5:0.1 `
    --param take_profit_pct=0.8:4.0:0.2 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

# [30] ema_crossover
Write-Host "[30/30] ema_crossover"
& $PYTHON $SCRIPT --strategy ema_crossover `
    --param stop_loss_pct=1.0:4.0:0.25 `
    --param take_profit_pct=2.0:8.0:0.5 `
    --symbols NVDA,TSLA,MSFT,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 --metric profit_factor

Write-Host ""
Write-Host "================================================================"
Write-Host "  SWEEP DONE -- check reports\param_sweep\ for results"
Write-Host "  Apply best params to strategy files then restart bot"
Write-Host "================================================================"
Write-Host ""
