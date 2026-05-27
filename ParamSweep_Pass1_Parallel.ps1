Set-Location C:\Users\Linda\trading_bot_v2

$PYTHON = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\param_sweep.py"

# Stock symbols from today's matrix run (all 25 from watchlist)
$STOCKS = "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS"

Write-Host ""
Write-Host "================================================================"
Write-Host "  PARAM SWEEP PASS 1  --  8 strategies, parallel background jobs"
Write-Host "  Method : zoom  (coarse 6-bucket -> fine +-5 steps around winner)"
Write-Host "  Symbols: 25 stock watchlist (matrix confirmed edge on all)"
Write-Host "  NOTE   : safe to run alongside RunMatrix.bat -- cached candles"
Write-Host "================================================================"
Write-Host ""

$jobs = @()

# ── [1] btc_v6_chandelier  stock 5m  PF=1.99  WR=57%  460 trades  PRIORITY ──
Write-Host "[1] Launching btc_v6_chandelier (stock 5m)..."
$jobs += Start-Job -Name "btc_v6_chandelier" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy btc_v6_chandelier `
        --param atr_mult=2.0:6.5:0.25 `
        --param rsi_thresh=30.0:58.0:2.0 `
        --param ema_fast=8:25:1 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 5m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [2] rsi_dip_simple  stock 5m  PF=1.72  WR=56%  592 trades  PRIORITY ──
Write-Host "[2] Launching rsi_dip_simple (stock 5m)..."
$jobs += Start-Job -Name "rsi_dip_simple" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy rsi_dip_simple `
        --param rsi_oversold=15.0:38.0:1.0 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 5m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [3] rsi_dip_spike_v4  stock 5m  PF=1.56  WR=66%  284 trades  PRIORITY ──
Write-Host "[3] Launching rsi_dip_spike_v4 (stock 5m)..."
$jobs += Start-Job -Name "rsi_dip_spike_v4" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy rsi_dip_spike_v4 `
        --param rsi_oversold=25.0:45.0:2.0 `
        --param rsi_overbought=68.0:88.0:2.0 `
        --param sl_atr_mult=1.5:3.5:0.25 `
        --param tp_atr_mult=1.5:3.5:0.25 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 5m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [4] mr_03_fbs  stock 5m  PF=1.38  WR=58%  552 trades ──────────────────
Write-Host "[4] Launching mr_03_fbs (stock 5m)..."
$jobs += Start-Job -Name "mr_03_fbs" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy mr_03_fbs `
        --param sl_mult=1.0:3.5:0.25 `
        --param tp_mult=1.0:3.5:0.25 `
        --param atr_len=8:21:1 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 5m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [5] adaptive_regime  stock 15m  PF=1.40  WR=46%  48 trades ───────────
Write-Host "[5] Launching adaptive_regime (stock 15m)..."
$jobs += Start-Job -Name "adaptive_regime" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy adaptive_regime `
        --param stop_loss_pct=1.0:3.0:0.1 `
        --param take_profit_pct=2.5:6.0:0.25 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 15m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [6] vwap_momentum  stock 15m  PF=1.72  WR=47%  36 trades ─────────────
Write-Host "[6] Launching vwap_momentum (stock 15m)..."
$jobs += Start-Job -Name "vwap_momentum" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy vwap_momentum `
        --param stop_loss_pct=0.8:2.5:0.1 `
        --param take_profit_pct=1.5:4.5:0.15 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 15m --days 60 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [7] rsi_dip_simple  stock 1h  PF=2.66  WR=49%  55 trades ─────────────
Write-Host "[7] Launching rsi_dip_simple 1h (stock 1h)..."
$jobs += Start-Job -Name "rsi_dip_simple_1h" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy rsi_dip_simple `
        --param rsi_oversold=15.0:38.0:1.0 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 1h --days 180 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

# ── [8] btc_v6_chandelier  stock 1h  PF=2.36  WR=51%  80 trades ──────────
Write-Host "[8] Launching btc_v6_chandelier 1h (stock 1h)..."
$jobs += Start-Job -Name "btc_v6_chandelier_1h" -ScriptBlock {
    Set-Location C:\Users\Linda\trading_bot_v2
    & venv312\Scripts\python.exe .\Scripts\param_sweep.py `
        --strategy btc_v6_chandelier `
        --param atr_mult=2.0:6.5:0.25 `
        --param rsi_thresh=30.0:58.0:2.0 `
        --param ema_fast=8:25:1 `
        --symbols "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS" `
        --timeframe 1h --days 180 --asset-class stock `
        --direction both `
        --method zoom --zoom-coarse-buckets 6 --zoom-fine-window 5 `
        --metric profit_factor 2>&1
}

Write-Host ""
Write-Host "All 8 jobs launched. Monitoring progress..."
Write-Host "(RunMatrix.bat can continue running in parallel -- no API conflicts)"
Write-Host ""

# ── Live progress loop ─────────────────────────────────────────────────────
while ($jobs | Where-Object { $_.State -eq "Running" }) {
    $running   = ($jobs | Where-Object { $_.State -eq "Running" }).Count
    $completed = ($jobs | Where-Object { $_.State -eq "Completed" }).Count
    $failed    = ($jobs | Where-Object { $_.State -eq "Failed" }).Count
    Write-Host "  $(Get-Date -Format 'HH:mm:ss')  Running: $running  Completed: $completed  Failed: $failed"
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "================================================================"
Write-Host "  ALL PASS 1 JOBS COMPLETE"
Write-Host "================================================================"
Write-Host ""

# ── Print results summary ──────────────────────────────────────────────────
foreach ($job in $jobs) {
    Write-Host "--- $($job.Name) [$($job.State)] ---"
    Receive-Job -Job $job | Select-Object -Last 20
    Write-Host ""
}

Remove-Job -Job $jobs
Write-Host "Results in: reports\param_sweep\"
Write-Host ""
pause
