Set-Location C:\Users\Linda\trading_bot_v2

$STOCKS  = ".\watchlists\stocks.txt"
$CRYPTO  = ".\watchlists\crypto.txt"
$PYTHON  = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\strategy_matrix.py"

Write-Host ""
Write-Host "================================================================"
Write-Host "  STRATEGY MATRIX BATCH  --  all 30 strategies"
Write-Host "  Phase 2 overhaul 2026-05-26"
Write-Host "  Output: reports\strategy_matrix\"
Write-Host "================================================================"
Write-Host ""

Write-Host "[1/30]  adaptive_regime"
& $PYTHON $SCRIPT --strategy adaptive_regime         --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[2/30]  orb_breakout"
& $PYTHON $SCRIPT --strategy orb_breakout            --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[3/30]  bollinger_squeeze"
& $PYTHON $SCRIPT --strategy bollinger_squeeze       --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[4/30]  rsi_dip_spike_v4"
& $PYTHON $SCRIPT --strategy rsi_dip_spike_v4        --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[5/30]  btc_v6_chandelier"
& $PYTHON $SCRIPT --strategy btc_v6_chandelier       --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[6/30]  rsi_dip_simple"
& $PYTHON $SCRIPT --strategy rsi_dip_simple          --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[7/30]  vwap_momentum"
& $PYTHON $SCRIPT --strategy vwap_momentum           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[8/30]  mr_03_fbs"
& $PYTHON $SCRIPT --strategy mr_03_fbs               --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[9/30]  kds_mean_reversion"
& $PYTHON $SCRIPT --strategy kds_mean_reversion      --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[10/30] ema_ribbon_breakout"
& $PYTHON $SCRIPT --strategy ema_ribbon_breakout     --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[11/30] rcr_mean_reversion"
& $PYTHON $SCRIPT --strategy rcr_mean_reversion      --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[12/30] ecb_strategy"
& $PYTHON $SCRIPT --strategy ecb_strategy            --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[13/30] cbae_strategy"
& $PYTHON $SCRIPT --strategy cbae_strategy           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[14/30] rare_strategy"
& $PYTHON $SCRIPT --strategy rare_strategy           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[15/30] fels_strategy"
& $PYTHON $SCRIPT --strategy fels_strategy           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[16/30] swing_trader"
& $PYTHON $SCRIPT --strategy swing_trader            --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[17/30] mean_reversion"
& $PYTHON $SCRIPT --strategy mean_reversion          --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[18/30] dca_accumulator"
& $PYTHON $SCRIPT --strategy dca_accumulator         --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[19/30] grid_bot"
& $PYTHON $SCRIPT --strategy grid_bot               --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[20/30] pll_cycle"
& $PYTHON $SCRIPT --strategy pll_cycle               --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[21/30] pll_cycle_martingale"
& $PYTHON $SCRIPT --strategy pll_cycle_martingale    --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[22/30] mr_02_vef"
& $PYTHON $SCRIPT --strategy mr_02_vef               --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[23/30] mr_04_fvg"
& $PYTHON $SCRIPT --strategy mr_04_fvg               --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[24/30] vdmr_strategy"
& $PYTHON $SCRIPT --strategy vdmr_strategy           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[25/30] vwap_confirmed_orb"
& $PYTHON $SCRIPT --strategy vwap_confirmed_orb      --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[26/30] rsi_momentum"
& $PYTHON $SCRIPT --strategy rsi_momentum            --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[27/30] bollinger_breakout"
& $PYTHON $SCRIPT --strategy bollinger_breakout      --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[28/30] hammer_reversal"
& $PYTHON $SCRIPT --strategy hammer_reversal         --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[29/30] scalp_master"
& $PYTHON $SCRIPT --strategy scalp_master            --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host "[30/30] ema_crossover"
& $PYTHON $SCRIPT --strategy ema_crossover           --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

Write-Host ""
Write-Host "================================================================"
Write-Host "  ALL DONE -- check reports\strategy_matrix\ for CSVs"
Write-Host "  Then update Param_sweep_batch_v3.ps1 symbols from results"
Write-Host "================================================================"
Write-Host ""
