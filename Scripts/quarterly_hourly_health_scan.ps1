param(
    [switch]$NoRestart
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ReportPath = Join-Path $Root "reports\QuarterlyHourlyLohScan.md"
$Python = Join-Path $Root "venv312\Scripts\python.exe"

Set-Location $Root

function Add-ReportLine {
    param([string]$Line = "")
    Add-Content -LiteralPath $ReportPath -Value $Line -Encoding UTF8
}

function Test-CommandLineRunning {
    param([string]$Needle)
    $escaped = [Regex]::Escape($Needle)
    $matches = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -and $_.CommandLine -match $escaped }
    return @($matches)
}

function Play-TripleBeep {
    try {
        for ($i = 0; $i -lt 3; $i++) {
            [Console]::Beep(880, 250)
            Start-Sleep -Milliseconds 140
        }
    } catch {
        try {
            Add-Type -AssemblyName System.Media
            for ($i = 0; $i -lt 3; $i++) {
                [System.Media.SystemSounds]::Exclamation.Play()
                Start-Sleep -Milliseconds 450
            }
        } catch {
            # Audio alert failed; report logging still records the issue.
        }
    }
}

function Start-RepoScript {
    param(
        [string]$Label,
        [string]$ScriptName
    )
    $scriptPath = Join-Path $Root $ScriptName
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        Add-ReportLine "- [UNRESOLVED] Cannot restart $Label because `$ScriptName` was not found."
        return $false
    }
    if ($NoRestart) {
        Add-ReportLine "- Test mode: restart skipped for $Label using $ScriptName."
        return $false
    }
    try {
        if ([IO.Path]::GetExtension($scriptPath) -ieq ".bat") {
            Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $scriptPath) -WorkingDirectory $Root -WindowStyle Hidden
        } else {
            Start-Process -FilePath "pwsh.exe" -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", $scriptPath
            ) -WorkingDirectory $Root -WindowStyle Hidden
        }
        Add-ReportLine "- Restart attempted for $Label using $ScriptName."
        return $true
    } catch {
        Add-ReportLine "- [UNRESOLVED] Restart failed for $Label using `$ScriptName`: $($_.Exception.Message)"
        return $false
    }
}

if (-not (Test-Path -LiteralPath (Split-Path -Parent $ReportPath))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $ReportPath) -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $ReportPath)) {
    "# Quarterly Hourly Log Scan`n" | Set-Content -LiteralPath $ReportPath -Encoding UTF8
}

& $Python "Scripts\quarterly_hourly_log_scan.py"
$AnalyzerExit = $LASTEXITCODE

& $Python "Scripts\night_watch_log_digest.py" --archive
$NightWatchExit = $LASTEXITCODE

& $Python "Scripts\night_watch_rollup.py" --period week
$WeeklyRollupExit = $LASTEXITCODE

& $Python "Scripts\night_watch_rollup.py" --period month
$MonthlyRollupExit = $LASTEXITCODE

$OllamaExit = 0
$OllamaModel = if ($env:OLLAMA_NIGHT_WATCH_MODEL) { $env:OLLAMA_NIGHT_WATCH_MODEL } else { "llama3:latest" }
$OllamaEnabled = ($env:ENABLE_OLLAMA_NIGHT_WATCH -eq "1")
if ($OllamaEnabled) {
    $OllamaTimeout = if ($env:OLLAMA_NIGHT_WATCH_TIMEOUT) { [int]$env:OLLAMA_NIGHT_WATCH_TIMEOUT } else { 180 }
    & $Python "Scripts\ollama_night_watch_summary.py" --model $OllamaModel --timeout $OllamaTimeout
    $OllamaExit = $LASTEXITCODE
}

$Now = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
Add-ReportLine ""
Add-ReportLine "### Process Health - $Now"
Add-ReportLine "- Night watch deterministic digest exit code: $NightWatchExit"
Add-ReportLine "- Night watch weekly rollup exit code: $WeeklyRollupExit"
Add-ReportLine "- Night watch monthly rollup exit code: $MonthlyRollupExit"
if (-not $OllamaEnabled) {
    Add-ReportLine "- Ollama night watch summary skipped. Set ENABLE_OLLAMA_NIGHT_WATCH=1 to run local model summaries."
    $SkippedSummary = Join-Path $Root "reports\night_watch\ollama_summary_latest.md"
    @(
        "# Ollama Night Watch Summary",
        "",
        "- Status: SKIPPED",
        "- Reason: ENABLE_OLLAMA_NIGHT_WATCH is not set to 1.",
        "- Deterministic digest: reports\night_watch\latest_digest.md",
        "",
        "Run manually when wanted:",
        "",
        '```powershell',
        '$env:ENABLE_OLLAMA_NIGHT_WATCH="1"',
        'venv312\Scripts\python.exe Scripts\ollama_night_watch_summary.py --model llama3:latest --timeout 180',
        '```'
    ) | Set-Content -LiteralPath $SkippedSummary -Encoding UTF8
} elseif ($OllamaExit -eq 0) {
    $OllamaReportLine = "- Ollama night watch summary OK using {0}: reports\night_watch\ollama_summary_latest.md" -f $OllamaModel
    Add-ReportLine -Line $OllamaReportLine
} else {
    $OllamaReportLine = "- Ollama night watch summary failed or timed out using {0}; deterministic digest is still available at reports\night_watch\latest_digest.md" -f $OllamaModel
    Add-ReportLine -Line $OllamaReportLine
}

$checks = @(
    @{ Label = "bot_engine.py"; Needle = "bot_engine.py"; Launcher = "start_bot.bat" },
    @{ Label = "web_dashboard.py"; Needle = "web_dashboard.py"; Launcher = "launch-www.ps1" },
    @{ Label = "BreakoutScanner.py"; Needle = "BreakoutScanner.py"; Launcher = "launch-break.ps1" },
    @{ Label = "launch-watchdog.ps1 / watchdog_ibkr.py"; Needle = "watchdog_ibkr.py"; Launcher = "launch-watchdog.ps1" }
)

$HadIssue = ($AnalyzerExit -ne 0) -or ($NightWatchExit -ne 0)
foreach ($check in $checks) {
    $running = Test-CommandLineRunning -Needle $check.Needle
    if ($running.Count -gt 0) {
        $pids = ($running | Select-Object -ExpandProperty ProcessId) -join ", "
        Add-ReportLine "- OK: $($check.Label) running as PID(s): $pids"
    } else {
        $HadIssue = $true
        Add-ReportLine "- [UNRESOLVED] $($check.Label) was not running."
        $started = Start-RepoScript -Label $check.Label -ScriptName $check.Launcher
        if ($started) {
            Start-Sleep -Seconds 5
            $after = Test-CommandLineRunning -Needle $check.Needle
            if ($after.Count -gt 0) {
                $pids = ($after | Select-Object -ExpandProperty ProcessId) -join ", "
                Add-ReportLine "- Restart verified for $($check.Label) as PID(s): $pids"
            } else {
                Add-ReportLine "- [UNRESOLVED] Restart was attempted for $($check.Label), but it was still not detected after 5 seconds."
            }
        }
    }
}

if ($HadIssue) {
    Add-ReportLine "- Alert: triple beep attempted because this scan found unresolved issues."
    Play-TripleBeep
    exit 2
}

Add-ReportLine "- Process health OK; no audible alert needed."
exit 0
