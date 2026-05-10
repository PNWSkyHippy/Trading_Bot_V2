Set-Location $PSScriptRoot
Start-Process python `
  -ArgumentList "`"$PSScriptRoot\BreakoutScanner.py`"" `
  -WorkingDirectory $PSScriptRoot `
  -RedirectStandardOutput "$PSScriptRoot\scanner_stdout.log" `
  -RedirectStandardError "$PSScriptRoot\scanner_errors.log" `
  -WindowStyle Hidden
