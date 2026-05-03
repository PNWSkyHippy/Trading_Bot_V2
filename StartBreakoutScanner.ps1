Start-Process python `
  -ArgumentList ".\BreakoutScanner.py" `
  -RedirectStandardOutput "scanner.log" `
  -RedirectStandardError "scanner_errors.log" `
  -WindowStyle Hidden