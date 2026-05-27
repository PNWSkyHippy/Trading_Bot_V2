Set-Location C:\Users\Linda\trading_bot_v2

$PYTHON = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\param_sweep.py"

$STOCKS = "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS"
$CRYPTO = "BTC/USD,ETH/USD,SOL/USD,BNB/USD,XRP/USD,LTC/USD,BCH/USD,ADA/USD,AVAX/USD,DOT/USD"

Write-Host ""
Write-Host "================================================================"
Write-Host "  PARAM SWEEP PASS 1  --  strategies 9-22, parallel background"
Write-Host "  Launch after RunMatrix.bat finishes strategies 9+ results"
Write-Host "  Review matrix CSVs first -- comment out PF < 1.2 blocks"
Write-Host "================================================================"
Write-Host ""

$jobs = @()

# ── [9] kds_mean_reversion  1d crypto/stock -- had selective edge prev runs
Write-Host "[9] Launching kds_mean_reversion..."
$jobs += Start-Job -Name "kds_mean_reversion" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy kds_mean_reversion `
        --param kds_thresh=1.0:3.5:0.25 `
        --param rsi_os=25.0:45.0:2.0 `
        --param rsi_ob=55.0:78.0:2.0 `
        --param sl_mult=1.0:3.0:0.25 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD,AVAX/USD,NVDA,META,TSLA,MSFT" `
        --timeframe 1d --days 365 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [10] ema_ribbon_breakout  1d -- daily only, short edge was strong
Write-Host "[10] Launching ema_ribbon_breakout..."
$jobs += Start-Job -Name "ema_ribbon_breakout" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy ema_ribbon_breakout `
        --param adx_min=18.0:30.0:1.0 `
        --param atr_mult=2.0:5.0:0.25 `
        --param sl_pct=3.0:9.0:0.5 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT,AMD,INTC" `
        --timeframe 1d --days 365 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [11] rcr_mean_reversion  1d -- autocorrelation reversal
Write-Host "[11] Launching rcr_mean_reversion..."
$jobs += Start-Job -Name "rcr_mean_reversion" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy rcr_mean_reversion `
        --param z_thresh=1.0:2.5:0.1 `
        --param stop_atr_k=0.5:2.5:0.25 `
        --param ac_thresh=-0.20:0.00:0.02 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD,NVDA,META,TSLA,MSFT,AMD" `
        --timeframe 1d --days 365 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [12] ecb_strategy  1h -- entropy collapse breakout
Write-Host "[12] Launching ecb_strategy..."
$jobs += Start-Job -Name "ecb_strategy" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy ecb_strategy `
        --param stop_loss_pct=1.0:3.0:0.2 `
        --param take_profit_pct=2.0:6.0:0.25 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT" `
        --timeframe 1h --days 180 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [16] swing_trader  -- SIGNAL_TUNING stop/tp
Write-Host "[16] Launching swing_trader..."
$jobs += Start-Job -Name "swing_trader" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy swing_trader `
        --param stop_loss_pct=1.5:4.0:0.2 `
        --param take_profit_pct=3.0:9.0:0.3 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM" `
        --timeframe 1h --days 365 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [17] mean_reversion  -- SIGNAL_TUNING stop/tp
Write-Host "[17] Launching mean_reversion..."
$jobs += Start-Job -Name "mean_reversion" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy mean_reversion `
        --param stop_loss_pct=1.0:3.5:0.2 `
        --param take_profit_pct=2.5:7.0:0.25 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,NVDA,META,TSLA,MSFT,AMD" `
        --timeframe 1h --days 180 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [20] pll_cycle  1d -- PLL cycle detector (base, no martingale)
Write-Host "[20] Launching pll_cycle..."
$jobs += Start-Job -Name "pll_cycle" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy pll_cycle `
        --param lock_thresh=0.5:2.0:0.1 `
        --param sl_pct=2.0:6.0:0.5 `
        --param center_period=60:120:5 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,ADA/USD" `
        --timeframe 1d --days 365 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [21] mr_02_vef  1h -- volatility exhaustion fade
Write-Host "[21] Launching mr_02_vef...")
$jobs += Start-Job -Name "mr_02_vef" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy mr_02_vef `
        --param sl_mult=1.0:3.5:0.25 `
        --param tp_mult=1.0:3.5:0.25 `
        --param atr_spike=1.0:2.5:0.1 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,BNB/USD,NVDA,META,TSLA,MSFT" `
        --timeframe 1h --days 180 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [23] vdmr_strategy  1h -- velocity deceleration mean reversion
Write-Host "[23] Launching vdmr_strategy..."
$jobs += Start-Job -Name "vdmr_strategy" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy vdmr_strategy `
        --param z_entry_thresh=1.5:3.0:0.1 `
        --param sl_atr_mult=0.5:2.0:0.1 `
        --param er_max=0.25:0.60:0.05 `
        --symbols "BTC/USD,ETH/USD,SOL/USD,NVDA,META,TSLA,MSFT" `
        --timeframe 1h --days 180 --asset-class crypto `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [24] vwap_confirmed_orb  stock 5m/15m
Write-Host "[24] Launching vwap_confirmed_orb..."
$jobs += Start-Job -Name "vwap_confirmed_orb" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy vwap_confirmed_orb `
        --param stop_loss_pct=1.0:3.0:0.2 `
        --param take_profit_pct=2.0:6.0:0.25 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM,SNOW,DDOG" `
        --timeframe 15m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [25] rsi_momentum  -- SIGNAL_TUNING stop/tp
Write-Host "[25] Launching rsi_momentum..."
$jobs += Start-Job -Name "rsi_momentum" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy rsi_momentum `
        --param stop_loss_pct=1.0:3.5:0.2 `
        --param take_profit_pct=2.5:7.0:0.25 `
        --symbols "NVDA,META,TSLA,MSFT,AMD,INTC,BTC/USD,ETH/USD,SOL/USD" `
        --timeframe 15m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [26] bollinger_breakout  -- SIGNAL_TUNING stop/tp
Write-Host "[26] Launching bollinger_breakout..."
$jobs += Start-Job -Name "bollinger_breakout" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy bollinger_breakout `
        --param stop_loss_pct=1.5:4.0:0.2 `
        --param take_profit_pct=3.0:9.0:0.3 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,PLTR,CRM" `
        --timeframe 15m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [27] hammer_reversal  -- wide stop by design, sweep tp
Write-Host "[27] Launching hammer_reversal...")
$jobs += Start-Job -Name "hammer_reversal" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy hammer_reversal `
        --param stop_loss_pct=4.0:12.0:0.5 `
        --param take_profit_pct=3.0:10.0:0.5 `
        --symbols "NVDA,META,TSLA,MSFT,AMD,BTC/USD,ETH/USD,SOL/USD" `
        --timeframe 1h --days 180 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [28] scalp_master  -- SIGNAL_TUNING tight stops
Write-Host "[28] Launching scalp_master...")
$jobs += Start-Job -Name "scalp_master" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy scalp_master `
        --param stop_loss_pct=0.5:2.0:0.1 `
        --param take_profit_pct=0.8:3.5:0.1 `
        --symbols "NVDA,META,TSLA,MSFT,AMD,INTC,BTC/USD,ETH/USD" `
        --timeframe 5m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

Write-Host ""
Write-Host "All batch-2 jobs launched ($($jobs.Count) strategies)."
Write-Host "Monitoring -- updates every 30s..."
Write-Host ""

while ($jobs | Where-Object { $_.State -eq "Running" }) {
    $running   = ($jobs | Where-Object { $_.State -eq "Running" }).Count
    $completed = ($jobs | Where-Object { $_.State -eq "Completed" }).Count
    $failed    = ($jobs | Where-Object { $_.State -eq "Failed" }).Count
    Write-Host "  $(Get-Date -Format 'HH:mm:ss')  Running: $running  Completed: $completed  Failed: $failed"
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "================================================================"
Write-Host "  ALL PASS 1 BATCH-2 JOBS COMPLETE"
Write-Host "================================================================"
Write-Host ""

foreach ($job in $jobs) {
    Write-Host "--- $($job.Name) [$($job.State)] ---"
    Receive-Job -Job $job | Select-Object -Last 15
    Write-Host ""
}

Remove-Job -Job $jobs
Write-Host "Results in: reports\param_sweep\"
Write-Host ""
pause
