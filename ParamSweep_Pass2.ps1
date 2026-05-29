Set-Location C:\Users\Linda\trading_bot_v2

$PYTHON  = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\param_sweep.py"
$STOCKS  = "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS"
$LOGDIR  = "reports\param_sweeps"

Write-Host ""
Write-Host "================================================================"
Write-Host "  PARAM SWEEP PASS 2  --  rsi_dip_simple only"
Write-Host "  btc_v6_chandelier + rsi_dip_spike_v4 removed (not needed)"
Write-Host "  Symbols: 25 stock watchlist"
Write-Host "================================================================"
Write-Host ""

$start = Get-Date

function Run-Sweep {
    param([string]$Label, [string]$LogFile, [string[]]$CmdArgs)
    Write-Host "$(Get-Date -Format 'HH:mm:ss')  START  $Label"
    $t0 = Get-Date
    & $PYTHON $SCRIPT @CmdArgs 2>&1 | Tee-Object -FilePath $LogFile
    $elapsed = [int]((Get-Date) - $t0).TotalSeconds
    Write-Host "$(Get-Date -Format 'HH:mm:ss')  DONE   $Label  (${elapsed}s)"
    Write-Host ""
}

# ─────────────────────────────────────────────────────────────────────────────
# [1] rsi_dip_simple  1h   (~2,040 combos, matrix)
#     All 3 params near/at boundaries -- ranges extended in relevant direction
# ─────────────────────────────────────────────────────────────────────────────
Run-Sweep "rsi_dip_simple 1h Pass2" "$LOGDIR\rsi_dip_simple_1h_pass2.log" @(
    "--strategy", "rsi_dip_simple",
    "--param", "rsi_oversold=9.0:23.0:1.0",
    "--param", "rsi_exit=79.0:95.0:1.0",
    "--param", "sl_atr_mult=0.75:2.5:0.25",
    "--symbols", $STOCKS,
    "--timeframe", "1h", "--days", "180", "--asset-class", "stock",
    "--direction", "both",
    "--method", "matrix",
    "--metric", "profit_factor"
)

# ─────────────────────────────────────────────────────────────────────────────
$total = [int]((Get-Date) - $start).TotalMinutes
Write-Host "================================================================"
Write-Host "  PASS 2 COMPLETE  ($total min total)"
Write-Host "  CSVs + JSONs in : reports\param_sweeps\"
Write-Host "  Next: Scripts\combine_sweep_results.ps1 to review winners"
Write-Host "================================================================"
Write-Host ""
pause
