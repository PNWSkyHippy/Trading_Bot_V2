Set-Location C:\Users\Linda\trading_bot_v2

$PYTHON  = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\param_sweep.py"
$STOCKS  = "NVDA,META,TSLA,MSFT,NFLX,AMD,INTC,MRVL,ALAB,QCOM,TXN,LRCX,KLAC,AMAT,MU,ON,MPWR,PLTR,CRM,SNOW,DDOG,NET,NOW,CRWD,ZS"
$LOGDIR  = "reports\param_sweeps"

Write-Host ""
Write-Host "================================================================"
Write-Host "  PARAM SWEEP PASS 1 v2  --  5 priority stock strategies"
Write-Host "  Method : zoom (coarse 6-bucket -> fine +-5 window)"
Write-Host "  Symbols: 25 stock watchlist"
Write-Host "  Output : $LOGDIR\<strategy>_pass1.log  +  .csv  +  .json"
Write-Host "  NOTE   : runs SEQUENTIALLY -- safe to leave overnight"
Write-Host "================================================================"
Write-Host ""

$start = Get-Date

# ── helper: run one sweep, log stdout+stderr to file ─────────────────────────
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
# [1] btc_v6_chandelier  stock 5m  — matrix PF 1.99 / 460 trades  PRIORITY
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# [5] mr_03_fbs  stock 5m  — matrix PF 1.38 / 552 trades  WR 58%
# ─────────────────────────────────────────────────────────────────────────────
Run-Sweep "mr_03_fbs 5m" "$LOGDIR\mr_03_fbs_5m_pass1_r2.log" @(
    "--strategy", "mr_03_fbs",
    "--param", "sl_mult=1.0:3.5:0.50",
    "--param", "tp_mult=1.0:3.5:0.50",
    "--param", "atr_len=7:21:3:int",
    "--symbols", $STOCKS,
    "--timeframe", "5m", "--days", "60", "--asset-class", "stock",
    "--direction", "both",
    "--method", "zoom", "--zoom-coarse-buckets", "6", "--zoom-fine-window", "5",
    "--metric", "profit_factor"
)

# ─────────────────────────────────────────────────────────────────────────────
$total = [int]((Get-Date) - $start).TotalMinutes
Write-Host "================================================================"
Write-Host "  ALL PASS 1 v2 SWEEPS COMPLETE  ($total min total)"
Write-Host "  CSVs + JSONs in : reports\param_sweeps\"
Write-Host "  Logs in         : reports\param_sweeps\*_pass1.log"
Write-Host "  Next: run ParamSweep_Pass2.ps1 (built from these results)"
Write-Host "================================================================"
Write-Host ""
pause
