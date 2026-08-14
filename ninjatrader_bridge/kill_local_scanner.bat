@echo off
rem Kills every ninja_futures_scanner.py process (parent stub + child worker),
rem no matter how many are running, so you can restart clean. Run this by
rem double-clicking it yourself -- it stays open at the end so you can see
rem what it found and killed.
echo Looking for ninja_futures_scanner.py processes...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*ninja_futures_scanner.py*' }; if (-not $procs) { Write-Output 'No matching processes found.' } else { $procs | ForEach-Object { Write-Output ('Killing PID ' + $_.ProcessId + ' -- ' + $_.CommandLine); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }"
echo.
echo Checking port 8765...
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($c) { Write-Output ('Port 8765 still held by PID ' + $c.OwningProcess) } else { Write-Output 'Port 8765 is free.' }"
echo.
echo Done. Run start_local_scanner.bat to bring it back up.
pause
