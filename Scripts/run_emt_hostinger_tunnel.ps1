param(
    [string]$SshTarget = "ronh@187.127.248.52",
    [int]$LocalPort = 8766,
    [int]$RemotePort = 8765
)
# LocalPort used to be 8765, the same port the local scanner
# (start_local_scanner.bat) binds directly. Only one of the two could ever
# actually be listening at a time; whichever process won the race locked the
# other out completely (confirmed in logs/emt_tunnel.log: the supervisor
# repeatedly found 8765 already held by the local scanner and just backed
# off). The tunnel now forwards local 8766 -> the VPS's own 8765 so both can
# run at once. NinjaScript now posts to both 127.0.0.1:8765 (local) and
# 127.0.0.1:8766 (this tunnel) independently.

$ErrorActionPreference = "Stop"
$logDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) "logs"
$logPath = Join-Path $logDirectory "emt_tunnel.log"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Write-TunnelLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Value "$timestamp $Message"
}

function Get-PortOwner {
    $listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $LocalPort `
        -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $listener) {
        return $null
    }

    return Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
}

function Test-TunnelHealthy {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(3000)
        if ($connected -and $client.Connected) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    }
    catch {
        return $false
    }
}

Write-TunnelLog "EMT tunnel supervisor started."

while ($true) {
    $owner = Get-PortOwner
    if ($null -ne $owner) {
        if ($owner.ProcessName -eq "ssh") {
            # A listening ssh process can still be a dead/zombie tunnel (channel
            # silently died server-side while the local socket stayed bound).
            # Give it a grace period after start, then actively probe it; a
            # port that accepts nothing but claims to LISTEN gets killed so the
            # loop below spawns a fresh tunnel.
            $ageSeconds = ((Get-Date) - $owner.StartTime).TotalSeconds
            if ($ageSeconds -gt 30 -and -not (Test-TunnelHealthy -Port $LocalPort)) {
                Write-TunnelLog "Tunnel PID $($owner.Id) is listening but not accepting connections (zombie); killing and restarting."
                Stop-Process -Id $owner.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
                continue
            }

            # A manually started tunnel may already own the port. Leave it alone;
            # this supervisor will take over if that tunnel exits.
            Start-Sleep -Seconds 10
            continue
        }

        Write-TunnelLog "Port $LocalPort is occupied by $($owner.ProcessName) (PID $($owner.Id)); waiting."
        Start-Sleep -Seconds 30
        continue
    }

    $arguments = @(
        "-N",
        "-T",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-L", "127.0.0.1:${LocalPort}:127.0.0.1:${RemotePort}",
        $SshTarget
    )

    try {
        Write-TunnelLog "Opening tunnel to $SshTarget."
        $process = Start-Process -FilePath "$env:WINDIR\System32\OpenSSH\ssh.exe" `
            -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
        Write-TunnelLog "SSH exited with code $($process.ExitCode); retrying in 5 seconds."
    }
    catch {
        Write-TunnelLog "SSH launch failed: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 5
}
