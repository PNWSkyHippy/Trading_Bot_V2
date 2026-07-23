$ErrorActionPreference = "Stop"

$taskName = "EMT Hostinger Tunnel"
$runnerPath = Join-Path $PSScriptRoot "run_emt_hostinger_tunnel.ps1"
$powershellPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Tunnel runner not found: $runnerPath"
}

$action = New-ScheduledTaskAction -Execute $powershellPath -Argument `
    "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runnerPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Keeps NinjaTrader's local EMT feed connected to Hostinger." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Host "Installed and started scheduled task: $taskName"
