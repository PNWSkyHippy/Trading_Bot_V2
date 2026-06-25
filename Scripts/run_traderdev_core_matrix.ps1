param(
    [string[]]$Strategies = @(
        "bollinger_squeeze",
        "btc_v6_chandelier",
        "rsi_dip_simple",
        "pll_cycle",
        "pll_cycle_martingale"
    ),
    [string]$Symbols = "BTC/USD,ETH/USD,SOL/USD,BNB/USD",
    [string]$Timeframes = "1h",
    [string]$Directions = "long,short,both",
    [int]$Days = 365,
    [string]$Label = "traderdev_core",
    [int]$MinTrades = 2
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

foreach ($strategy in $Strategies) {
    Write-Host "=== $strategy ===" -ForegroundColor Cyan
    & "$root\venv312\Scripts\python.exe" "$root\Scripts\strategy_matrix.py" `
        --strategy $strategy `
        --crypto-only `
        --symbols-crypto $Symbols `
        --timeframes $Timeframes `
        --directions $Directions `
        --days $Days `
        --label $Label `
        --min-trades $MinTrades
}
