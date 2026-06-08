$all = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and
    $_.CommandLine -notlike '*Claude*' -and
    $_.CommandLine -notlike '*vscode*' -and
    $_.CommandLine -notlike '*black-formatter*' -and
    $_.CommandLine -notlike '*polygon-mcp*' -and
    $_.CommandLine -notlike '*windows-mcp*'
} | ForEach-Object {
    $script = switch -Regex ($_.CommandLine.ToLower()) {
        'bot_engine'       { 'bot_engine' }
        'web_dashboard'    { 'web_dashboard' }
        'watchdog_ibkr'    { 'watchdog_ibkr' }
        'breakoutscanner'  { 'breakout_scanner' }
        'breakout_scanner' { 'breakout_scanner' }
        'market_scanner'   { 'market_scanner' }
        'funding_scanner'  { 'funding_scanner' }
        default            { 'other' }
    }
    [PSCustomObject]@{
        ProcessId  = $_.ProcessId
        MB         = [math]::Round($_.WorkingSetSize/1MB,1)
        Started    = $_.CreationDate
        StartedFmt = $_.CreationDate.ToString('HH:mm:ss')
        Script     = $script
        CommandLine= $_.CommandLine
    }
}

$newestByScript = @{}
foreach ($p in $all) {
    if (-not $newestByScript.ContainsKey($p.Script) -or $p.Started -gt $newestByScript[$p.Script]) {
        $newestByScript[$p.Script] = $p.Started
    }
}

Write-Host ''
Write-Host '  PID    MB       Started   Script          STATUS' -ForegroundColor Cyan
Write-Host '  ---    --       -------   ------          ------' -ForegroundColor DarkGray

$zombiePids = @()

foreach ($p in ($all | Sort-Object MB -Descending)) {
    $newest = $newestByScript[$p.Script]
    $ageSec = ($newest - $p.Started).TotalSeconds

    if ($ageSec -gt 5) {
        $status = 'ZOMBIE  <-- KILL'
        $color  = 'Red'
        $zombiePids += $p.ProcessId
    } elseif ($p.MB -gt 10) {
        $status = 'REAL    (keep)'
        $color  = 'Green'
    } else {
        $status = 'launcher(normal)'
        $color  = 'DarkYellow'
    }

    Write-Host ("  {0,-6} {1,-8} {2,-9} {3,-15} {4}" -f $p.ProcessId, $p.MB, $p.StartedFmt, $p.Script, $status) -ForegroundColor $color
}

Write-Host ''
if ($zombiePids.Count -gt 0) {
    Write-Host '  Zombies detected - kill with:' -ForegroundColor Red
    Write-Host "  Stop-Process -Id $($zombiePids -join ', ') -Force" -ForegroundColor Yellow
} else {
    Write-Host '  No zombies. All clean.' -ForegroundColor Green
}
Write-Host ''
