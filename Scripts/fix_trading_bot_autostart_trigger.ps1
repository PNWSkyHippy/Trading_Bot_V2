# Run this script from an elevated ("Run as Administrator") PowerShell prompt.
#
# "Trading Bot Auto Start" was registered with a BootTrigger but a principal
# LogonType of InteractiveToken. That combination never actually fires: a
# boot trigger runs before any interactive session token exists, so the task
# silently never launches (Get-ScheduledTaskInfo shows LastRunTime "never
# run" since the task's creation, even across multiple reboots). This
# replaces the boot trigger with an AtLogOn trigger for the same user,
# mirroring the working "EMT Hostinger Tunnel" task already in this repo
# (Scripts/install_emt_hostinger_tunnel.ps1), which uses the same pattern
# successfully.

$ErrorActionPreference = "Stop"

$taskName = "Trading Bot Auto Start"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$existing = Get-ScheduledTask -TaskName $taskName
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser

Set-ScheduledTask -TaskName $taskName -Trigger $trigger | Out-Null

Write-Host "Updated trigger for '$taskName' to AtLogOn ($currentUser)."
schtasks /query /tn $taskName /xml
