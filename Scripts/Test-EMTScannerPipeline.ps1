[CmdletBinding()]
param(
    [int]$LocalPort = 8765,
    [int]$TunnelPort = 8766,
    [string]$SshTarget = "ronh@187.127.248.52",
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\emt_tunnel_key",
    [int]$HttpTimeoutSeconds = 20,
    [int]$StaleAfterSeconds = 150,
    [switch]$Remote,
    [switch]$Watch,
    [ValidateRange(5, 3600)]
    [int]$IntervalSeconds = 30
)

# Read-only end-to-end health check for:
# NinjaTrader -> local receiver :8765 -> SSH tunnel :8766 -> VPS receiver :8765.
# This script never restarts, kills, edits, or submits anything.

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$CoreSymbols = @("MES", "ES", "MNQ", "NQ", "MYM", "YM", "M2K", "RTY")
$AllSymbols = @($CoreSymbols + @("MGC", "GC", "NKD", "MBT", "MET", "MNK"))
$script:WorstExitCode = 0

function Write-Check {
    param(
        [ValidateSet("PASS", "WARN", "FAIL", "INFO")]
        [string]$Level,
        [string]$Message
    )
    $color = switch ($Level) {
        "PASS" { "Green" }
        "WARN" { "Yellow" }
        "FAIL" { "Red" }
        default { "Cyan" }
    }
    if ($Level -eq "WARN" -and $script:WorstExitCode -lt 1) { $script:WorstExitCode = 1 }
    if ($Level -eq "FAIL") { $script:WorstExitCode = 2 }
    Write-Host ("[{0}] {1}" -f $Level, $Message) -ForegroundColor $color
}

function Get-HttpJson {
    param([string]$Url)
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $value = Invoke-RestMethod -Uri $Url -TimeoutSec $HttpTimeoutSeconds
        $timer.Stop()
        return [pscustomobject]@{
            Ok = $true
            Value = $value
            Milliseconds = [math]::Round($timer.Elapsed.TotalMilliseconds)
            Error = $null
        }
    }
    catch {
        $timer.Stop()
        return [pscustomobject]@{
            Ok = $false
            Value = $null
            Milliseconds = [math]::Round($timer.Elapsed.TotalMilliseconds)
            Error = $_.Exception.Message
        }
    }
}

function Get-DynamicProperty {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Get-BarRow {
    param($Snapshot, [string]$Symbol, [string]$Prefix)
    $barsObject = Get-DynamicProperty $Snapshot "bars"
    $barValue = Get-DynamicProperty $barsObject $Symbol
    $bars = @($barValue)
    if ($bars.Count -eq 1 -and $null -eq $bars[0]) { $bars = @() }

    $lastBar = $null
    $lastBarText = "--"
    $barAge = $null
    if ($bars.Count -gt 0) {
        $lastBar = $bars[-1]
        if ($null -ne $lastBar.time) {
            try {
                $parsed = [datetime]::Parse(
                    [string]$lastBar.time,
                    [Globalization.CultureInfo]::InvariantCulture,
                    [Globalization.DateTimeStyles]::AssumeLocal
                )
                $lastBarText = $parsed.ToString("MM-dd HH:mm:ss")
                $barAge = [math]::Max(0, [math]::Round(((Get-Date) - $parsed).TotalSeconds, 1))
            }
            catch {
                $lastBarText = [string]$lastBar.time
            }
        }
    }

    $lastReceivedObject = Get-DynamicProperty $Snapshot "last_received"
    $receiveAge = Get-DynamicProperty $lastReceivedObject $Symbol
    if ($null -ne $receiveAge) { $receiveAge = [double]$receiveAge }
    # A resubscription can replay an old final historical candle right now. Its
    # receive age then looks fresh even though the candle itself is days old.
    # Use the older of the two ages so expired/silent contracts cannot pass.
    $effectiveAge = if ($null -ne $receiveAge -and $null -ne $barAge) {
        [math]::Max($receiveAge, $barAge)
    }
    elseif ($null -ne $receiveAge) {
        $receiveAge
    }
    else {
        $barAge
    }
    $status = if ($bars.Count -eq 0) {
        "NO_BARS"
    }
    elseif ($null -eq $effectiveAge) {
        "UNKNOWN"
    }
    elseif ($effectiveAge -le $StaleAfterSeconds) {
        "FRESH"
    }
    else {
        "STALE"
    }

    return [pscustomobject]@{
        Endpoint = $Prefix
        Symbol = $Symbol
        Bars = $bars.Count
        LastBar = $lastBarText
        ReceiveAgeSec = if ($null -eq $receiveAge) { "--" } else { [math]::Round($receiveAge, 1) }
        Status = $status
    }
}

function Test-BridgeFiles {
    $source = Join-Path $RepoRoot "ninjatrader_bridge\PythonFuturesBridge.cs"
    $installed = Join-Path $env:USERPROFILE "OneDrive\Documents\NinjaTrader 8\bin\Custom\AddOns\PythonFuturesBridge.cs"
    Write-Host "`nNINJATRADER ADDON FILE" -ForegroundColor White
    if (-not (Test-Path -LiteralPath $source)) {
        Write-Check FAIL "Source bridge is missing: $source"
        return
    }
    if (-not (Test-Path -LiteralPath $installed)) {
        Write-Check FAIL "Installed NinjaTrader bridge is missing: $installed"
        return
    }

    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $installedHash = (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
    if ($sourceHash -eq $installedHash) {
        Write-Check PASS "Installed PythonFuturesBridge.cs matches the repository source."
    }
    else {
        Write-Check FAIL "Installed PythonFuturesBridge.cs differs from the repository source. Ninja compiles the OneDrive AddOns copy."
        Write-Host "  source:    $source"
        Write-Host "  installed: $installed"
        Write-Host "  source modified:    $((Get-Item -LiteralPath $source).LastWriteTime)"
        Write-Host "  installed modified: $((Get-Item -LiteralPath $installed).LastWriteTime)"
    }

    $contractPattern = '\b(?:MES|ES|MNQ|NQ|MYM|YM|M2K|RTY|MGC|GC|NKD|MNK|MBT|MET)\s\d{2}-\d{2}\b'
    $sourceText = [System.IO.File]::ReadAllText($source)
    $installedText = [System.IO.File]::ReadAllText($installed)
    $sourceContracts = @([regex]::Matches($sourceText, $contractPattern) | ForEach-Object Value | Select-Object -Unique)
    $installedContracts = @([regex]::Matches($installedText, $contractPattern) | ForEach-Object Value | Select-Object -Unique)
    $contractDifference = Compare-Object $sourceContracts $installedContracts
    if ($contractDifference) {
        Write-Check WARN "Active-contract names differ between source and installed AddOn."
        $contractDifference | Format-Table InputObject, SideIndicator -AutoSize | Out-Host
        Write-Host "  <= only source; => only installed"
    }
}

function Test-NinjaTrader {
    Write-Host "`nNINJATRADER PROCESS" -ForegroundColor White
    $ninja = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "NinjaTrader*"
    })
    if ($ninja.Count -eq 0) {
        Write-Check FAIL "NinjaTrader process is not running."
    }
    else {
        Write-Check PASS ("NinjaTrader is running (PID {0})." -f (($ninja.Id -join ", ")))
    }
}

function Test-TunnelTask {
    Write-Host "`nSSH TUNNEL TASK" -ForegroundColor White
    try {
        $task = Get-ScheduledTask -TaskName "EMT Hostinger Tunnel" -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName "EMT Hostinger Tunnel" -ErrorAction Stop
        $level = if ($task.State -eq "Running") { "PASS" } else { "WARN" }
        Write-Check $level ("Task state={0}; last run={1}; last result=0x{2:X}" -f $task.State, $info.LastRunTime, $info.LastTaskResult)
    }
    catch {
        Write-Check WARN "Could not read Task Scheduler state ($($_.Exception.Message)). Run PowerShell as Administrator for this check."
    }

    $logPath = Join-Path $RepoRoot "logs\emt_tunnel.log"
    if (Test-Path -LiteralPath $logPath) {
        $lastLog = Get-Content -LiteralPath $logPath -Tail 1
        Write-Host "  tunnel log: $lastLog"
    }
    else {
        Write-Check WARN "Tunnel log not found: $logPath"
    }
}

function Test-Endpoint {
    param([string]$Name, [int]$Port)
    Write-Host ("`n{0} ENDPOINT (127.0.0.1:{1})" -f $Name.ToUpperInvariant(), $Port) -ForegroundColor White
    $health = Get-HttpJson "http://127.0.0.1:$Port/health"
    if (-not $health.Ok) {
        Write-Check FAIL ("/health failed after {0} ms: {1}" -f $health.Milliseconds, $health.Error)
        return $null
    }

    $bridge = $health.Value.bridge
    $heartbeatLevel = if ($bridge.alive -and [double]$bridge.age_seconds -le 75) { "PASS" } else { "FAIL" }
    Write-Check $heartbeatLevel ("HTTP {0} ms; heartbeat alive={1}, age={2}s, subscriptions={3}" -f `
        $health.Milliseconds, $bridge.alive, $bridge.age_seconds, $bridge.subscriptions)

    $snapshot = Get-HttpJson "http://127.0.0.1:$Port/snapshot"
    if (-not $snapshot.Ok) {
        Write-Check FAIL ("/snapshot failed after {0} ms: {1}" -f $snapshot.Milliseconds, $snapshot.Error)
        return $null
    }
    if ($snapshot.Milliseconds -gt 5000) {
        Write-Check WARN ("/snapshot is slow: {0} ms" -f $snapshot.Milliseconds)
    }
    else {
        Write-Check PASS ("/snapshot replied in {0} ms" -f $snapshot.Milliseconds)
    }

    $rows = foreach ($symbol in $AllSymbols) {
        Get-BarRow -Snapshot $snapshot.Value -Symbol $symbol -Prefix $Name
    }
    $rows | Format-Table Symbol, Bars, LastBar, ReceiveAgeSec, Status -AutoSize | Out-Host

    $freshCore = @($rows | Where-Object { $_.Symbol -in $CoreSymbols -and $_.Status -eq "FRESH" })
    if ($freshCore.Count -gt 0) {
        Write-Check PASS ("Live one-minute flow exists on {0} core symbol(s): {1}" -f $freshCore.Count, (($freshCore.Symbol) -join ", "))
    }
    else {
        Write-Check FAIL "No core futures symbol has received a fresh one-minute bar. Heartbeats alone are not sufficient."
    }

    $emt = $snapshot.Value.emt
    $eat = $snapshot.Value.eat
    Write-Host ("  EMT {0}: phase={1}; 610t bars={2}; {3}" -f $emt.symbol, $emt.phase, $emt.tick_bars, $emt.status_message)
    Write-Host ("  EAT {0}: phase={1}; {2}" -f $eat.symbol, $eat.phase, $eat.status_message)
    return [pscustomobject]@{ Health = $health.Value; Snapshot = $snapshot.Value; Rows = $rows }
}

function Test-RemoteService {
    if (-not $Remote) { return }
    Write-Host "`nHOSTINGER SYSTEMD (READ ONLY)" -ForegroundColor White
    $ssh = Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe"
    if (-not (Test-Path -LiteralPath $ssh)) {
        Write-Check FAIL "Windows OpenSSH client not found: $ssh"
        return
    }
    if (-not (Test-Path -LiteralPath $SshKeyPath)) {
        Write-Check FAIL "SSH key not found: $SshKeyPath"
        return
    }
    $remoteCommand = "systemctl is-active emt-scanner.service; systemctl show emt-scanner.service -p MainPID -p NRestarts -p ActiveEnterTimestamp --no-pager"
    $output = & $ssh -o BatchMode=yes -o ConnectTimeout=8 -i $SshKeyPath $SshTarget $remoteCommand 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Check FAIL "SSH/systemd check failed (exit $LASTEXITCODE): $($output -join ' ')"
        return
    }
    if ($output[0] -eq "active") {
        Write-Check PASS "emt-scanner.service is active."
    }
    else {
        Write-Check FAIL "emt-scanner.service state is $($output[0])."
    }
    $output | Select-Object -Skip 1 | ForEach-Object { Write-Host "  $_" }
}

function Invoke-PipelineCheck {
    $script:WorstExitCode = 0
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host ("EMT/EAT PIPELINE HEALTH  {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")) -ForegroundColor Cyan
    Write-Host "Heartbeat health and market-bar health are evaluated separately." -ForegroundColor DarkGray
    Test-NinjaTrader
    Test-BridgeFiles
    Test-TunnelTask
    $local = Test-Endpoint -Name "local" -Port $LocalPort
    $hostinger = Test-Endpoint -Name "hostinger-through-tunnel" -Port $TunnelPort
    Test-RemoteService

    Write-Host "`nVERDICT" -ForegroundColor White
    if ($null -eq $local) {
        Write-Check FAIL "Local receiver is unavailable. Start the local scanner before troubleshooting the tunnel."
    }
    elseif ($null -eq $hostinger) {
        Write-Check FAIL "Local receiver works but Hostinger-through-tunnel does not. Troubleshoot port 8766/tunnel/VPS service."
    }
    else {
        $localFresh = @($local.Rows | Where-Object { $_.Symbol -in $CoreSymbols -and $_.Status -eq "FRESH" }).Count
        $remoteFresh = @($hostinger.Rows | Where-Object { $_.Symbol -in $CoreSymbols -and $_.Status -eq "FRESH" }).Count
        if ($localFresh -eq 0) {
            Write-Check FAIL "Bars stop before the tunnel: inspect Ninja connection, installed AddOn, active contracts, and Ninja Output."
        }
        elseif ($remoteFresh -eq 0) {
            Write-Check FAIL "Bars are fresh locally but stale remotely: inspect the 8766 tunnel, Hostinger latency, and emt-scanner.service."
        }
        else {
            Write-Check PASS "Fresh bars reach both the local scanner and Hostinger."
        }
    }
    Write-Host ("Exit severity: {0} (0 healthy, 1 warning, 2 failure)" -f $script:WorstExitCode)
    return $script:WorstExitCode
}

if ($Watch) {
    while ($true) {
        Clear-Host
        $null = Invoke-PipelineCheck
        Write-Host "`nRepeating in $IntervalSeconds seconds. Ctrl+C stops monitoring."
        Start-Sleep -Seconds $IntervalSeconds
    }
}
else {
    $exitCode = Invoke-PipelineCheck
    exit $exitCode
}
