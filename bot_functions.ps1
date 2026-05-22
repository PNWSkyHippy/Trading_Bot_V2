# Bot shell functions - sourced by launch scripts
# No venv activation here (python called by full path in launch scripts)

$env:PYGAME_HIDE_SUPPORT_PROMPT = "hide"

function go-bot {
    Set-Location "C:\users\linda\trading_bot_v2"
}

function run-bot {
    go-bot
    $existing = & ".\venv312\Scripts\python.exe" -c @"
import os, psutil
me = os.getpid()
target = os.path.abspath('bot_engine.py').lower()
hits = []
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['pid'] == me:
            continue
        name = (p.info.get('name') or '').lower()
        if name not in ('python.exe', 'pythonw.exe', 'python3.exe'):
            continue
        args = p.info.get('cmdline') or []
        if '-c' in args:
            continue
        if any(os.path.abspath(a).lower() == target for a in args):
            hits.append(str(p.info['pid']))
    except Exception:
        pass
print(','.join(hits))
"@
    if ($existing) {
        Write-Host "bot_engine.py already running as PID(s): $existing" -ForegroundColor Yellow
        Write-Host "Not starting another copy." -ForegroundColor Yellow
        return
    }
    & ".\venv312\Scripts\python.exe" bot_engine.py
}

function bot-pids {
    go-bot
    & ".\venv312\Scripts\python.exe" -c @"
import os, psutil, datetime
target = os.path.abspath('bot_engine.py').lower()
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
    try:
        name = (p.info.get('name') or '').lower()
        args = p.info.get('cmdline') or []
        if name in ('python.exe', 'pythonw.exe', 'python3.exe') and '-c' not in args and any(os.path.abspath(a).lower() == target for a in args):
            cmd = ' '.join(args)
            print(p.info['pid'], p.info['name'], datetime.datetime.fromtimestamp(p.info['create_time']).strftime('%H:%M:%S'), cmd)
    except Exception:
        pass
"@
}

function run-break {
    go-bot
    & ".\venv312\Scripts\python.exe" BreakoutScanner.py
}

function run-breakk { run-break }

function run-www {
    go-bot
    & ".\venv312\Scripts\python.exe" web_dashboard.py
}

function stop-trading {
    go-bot
    & ".\venv312\Scripts\python.exe" -c @"
import os, time, psutil

root = os.path.abspath(r'C:\users\linda\trading_bot_v2').lower()
targets = {
    'bot_engine.py',
    'BreakoutScanner.py',
    'web_dashboard.py',
}

def find_trading_processes():
    matches = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            name = (p.info.get('name') or '').lower()
            if name not in ('python.exe', 'pythonw.exe', 'python3.exe'):
                continue
            args = p.info.get('cmdline') or []
            if '-c' in args:
                continue
            cwd = os.path.abspath(p.info.get('cwd') or '').lower()
            for arg in args:
                script = os.path.basename(arg)
                if script in targets:
                    full = os.path.abspath(arg).lower()
                    if cwd == root or full.startswith(root + os.sep):
                        matches.append((p, script, ' '.join(args)))
                        break
        except Exception:
            pass
    return matches

matches = find_trading_processes()

if not matches:
    print('No trading Python processes found.')
    raise SystemExit(0)

for p, script, cmd in matches:
    try:
        print(f'Stopping {script} PID {p.pid}...')
        p.terminate()
    except Exception as e:
        print(f'Could not terminate PID {p.pid}: {e}')

print('Waiting 5 seconds, then rescanning...')
time.sleep(5)
alive = find_trading_processes()

if alive:
    print('')
    print('WARNING: trading Python process(es) still running:')
    for p, script, cmd in alive:
        print(f'  PID {p.pid}: {script}')
        print(f'    {cmd}')
    ids = ','.join(str(p.pid) for p, _, _ in alive)
    print('')
    print('If these are stale/duplicated, run:')
    print(f'  Stop-Process -Id {ids} -Force')
    print('')
    print('Then check with:')
    print('  bot-pids')
else:
    print('All trading Python processes stopped.')

print('stop-trading complete.')
"@
}

function start-trading {
    $p = "C:\users\linda\trading_bot_v2"

    $wtArgs = (
        "new-tab --title `"CONSOLE`" powershell ; " +
        "split-pane --vertical --size 0.65 --title `"MAIN BOT`" pwsh -NoProfile -NoExit -File `"$p\launch-bot.ps1`" ; " +
        "split-pane --horizontal --size 0.75 --title `"BREAKOUT`" pwsh -NoProfile -NoExit -File `"$p\launch-break.ps1`" ; " +
        "split-pane --horizontal --size 0.667 --title `"WEB DASHBOARD`" pwsh -NoProfile -NoExit -File `"$p\launch-www.ps1`" ; " +
        "split-pane --horizontal --size 0.5 --title `"IBKR WATCHDOG`" pwsh -NoProfile -NoExit -File `"$p\launch-watchdog.ps1`""
    )

    Start-Process wt -ArgumentList $wtArgs
}

function tail-bot {
    Set-Location C:\users\linda\trading_bot_v2
    Get-Content .\logs\bot.log -Wait -Tail 80
}

function tail-trades {
    Set-Location C:\users\linda\trading_bot_v2
    Get-Content .\logs\bot.log -Wait -Tail 120 |
        Select-String -Pattern "TRADE OPEN|TRADE CLOSED|APPROVED|REJECTED|BREAKOUT RECV|ERROR|WARNING"
}

function scanner_logs { Select-String -Path logs\bot.log -Pattern "TRADE OPEN" | Select-Object -Last 10 }
function scanner_logs2 { Select-String -Path C:\users\linda\trading_bot_v2\scanner.log -Pattern "SENDER" | Select-Object -Last 10 }
function fda { fd -i -p -a $args }
function s { rg $args }
function db-panel { & "C:\users\linda\trading_bot_v2\venv312\Scripts\python.exe" "C:\users\linda\trading_bot_v2\db_panel.py" }

function list-shorts {
    Write-Host "go-bot           - return to home directory"
    Write-Host "run-bot          - run the bot engine"
    Write-Host "run-www          - run WWW front end"
    Write-Host "run-break        - run Breakout Scanner"
    Write-Host "run-dash         - run streamlit dashboard"
    Write-Host "stop-trading     - stops bot, scanner, and web dashboard"
    Write-Host "start-trading    - splits window, runs all programs"
    Write-Host "tail-bot         - tails bot.log"
    Write-Host "tail-trades      - tails bot.log for trade events"
    Write-Host "bot-pids         - show running bot PIDs"
    Write-Host "fda              - search files: fd -i -a <file>"
    Write-Host "s                - shortcut for rg"
}
