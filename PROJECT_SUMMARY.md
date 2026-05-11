# Trading Bot V2 — Project Summary & Session Handoff
**Last Updated:** 2026-05-03
**Purpose:** Compact handoff document for new Claude sessions. Read this first.
**Full reference:** See TECHNICAL_REFERENCE.md for complete documentation.

---

## Project In One Paragraph
Ron's autonomous trading bot scans stocks (Alpaca) and crypto (Kraken) every 60s/5min,
runs signals through 11 strategies, applies ML scoring, enforces risk rules, and executes
trades through IBKR (stocks, paper port 7497) with Alpaca fallback. Crypto goes through
Kraken paper mode (simulated locally). A Streamlit dashboard shows live positions, P&L,
and candlestick charts per position. Ron is on a TopStep combine — $2,438 profit so far,
$619 from funded trader status. Bot is in paper trading mode.

**Stack:** Python 3.12, venv312, SQLite, Streamlit, ib_insync, ccxt, alpaca-trade-api
**Location:** C:\Users\Linda\trading_bot_v2
**GitHub:** PNWSkyHippy/Trading_Bot_V2 (private)
**Owner:** Ron (Windows username is Linda)

---

## Current Bot Status
- ✅ Running in paper mode — IBKR stocks + Kraken crypto
- ✅ Multi-timeframe candle system — strategies fetch own TF bars
- ✅ IBC headless Gateway — auto-starts on boot, ReadOnlyApi=no
- ✅ Haiku model for signal reviews (was accidentally Sonnet — fixed, big cost saving)
- ✅ Fernet encryption for ANTHROPIC_API_KEY — BASE_KEY in Windows Credential Manager
- ✅ Dashboard charts per position — 5min/1hr/1day + Entry/SL/TP lines
- ✅ Consecutive losses and halt status fixed to always read fresh from DB
- ✅ Stablecoin injection blocked — 3 layers of protection
- ✅ Both IBKR and Alpaca tried on every stock close (dual-broker fix)
- ⚠️ BreakoutScanner.py GUI — signals fire in logs but not showing in GUI text widget yet

---

## Strategy Status
| Strategy | Status | Candle TF | Notes |
|---|---|---|---|
| grid_bot | ✅ ENABLED [NO-AUTO-DISABLE][ML-EXEMPT] | 5Min/1h | Best performer |
| mean_reversion | ✅ ENABLED [NO-AUTO-DISABLE] | 5Min | Stocks only, 79.8% win rate |
| bollinger_breakout | ✅ ENABLED [NO-AUTO-DISABLE] | 5Min | Stocks only |
| scalp_master | ✅ ENABLED | 5Min/1h | |
| swing_trader | ✅ ENABLED | **1Hour** | Now on correct TF |
| dca_accumulator | ✅ ENABLED | **1Hour** | Major crypto + blue chips |
| vwap_momentum | ✅ ENABLED | **1Hour** | Stocks only |
| hammer_reversal | ✅ ENABLED | 5Min/1h | Monitor live |
| rsi_momentum | ❌ DISABLED | — | Backtest confirmed dead |
| ema_crossover | ❌ DISABLED | — | Backtest confirmed dead |
| orb_breakout | ❌ DISABLED | — | Pending backtest |

---

## Recent Fixes (Last 2 Sessions)
1. **Haiku model fix** — claude_reviewer.py was using Sonnet 4.5 (expensive), switched to Haiku
2. **Fernet encryption** — ANTHROPIC_API_KEY encrypted in .env, BASE_KEY in Windows Credential Manager via keyring
3. **Dashboard session fix** — consecutive_losses and halt status now always read fresh from DB
4. **Dual-broker close** — stock close now tries BOTH IBKR and Alpaca regardless of DB broker field
5. **Invalid pair infinite loop fix** — position_monitor checks Kraken markets, force-closes invalid pairs in DB
6. **Stablecoin injection** — 3-layer fix: daily scanner exclusion, price stability guard, INJECT_BLACKLIST
7. **Watchlist txt files** — inject_scan_results_into_config() now reads from human-editable txt files (not JSON)
8. **BreakoutScanner.py** — complete rewrite fixing 15 bugs (wrong imports, scope errors, hardcoded keys, duplicate code)
9. **GitHub secret scanning** — encrypt_key.py had live API key, rotated, file cleaned, added to .gitignore

---

## Known Active Issues
- **BreakoutScanner GUI alerts not showing** — signals fire in logs/console but don't appear in tkinter text widget. `_process_alerts` routes via `root.after()` but alerts still not reaching GUI. Last fix attempt: wired `alert_system.gui` reference in `_start_scanner` before `scanner.start()`. Needs further debugging.
- **GitHub MCP 404** — GitHub connector connected but returns 404 on private repo. Tried fine-grained and classic tokens. Still unresolved.
- **Alpaca ghost positions** — occasional IBKR hiccup causes fallback to Alpaca, leaving positions on Alpaca not tracked in DB. Dual-broker close fix should prevent future occurrences. Manual cleanup at market open when found.

---

## Key Files
| File | Purpose |
|---|---|
| bot_engine.py | Main entry point |
| web_dashboard.py | Web console dashboard (replaces dashboard.py) |
| config.py | All settings, loads encrypted keys |
| strategies/strategy_engine.py | run_strategies_multi_tf() |
| scanners/market_scanner.py | Fetches bars per TF, reuses across strategies |
| scanners/daily_market_scanner.py | 13:30 PT EOD scan, writes watchlist txt files |
| core/trade_executor.py | Dual-broker close logic |
| core/position_monitor.py | Invalid pair detection, force-close |
| intelligence/claude_reviewer.py | Haiku signal review |
| BreakoutScanner.py | Standalone breakout scanner (separate from bot) |
| watchlist/scanned_crypto.txt | Human-editable daily scan results (edit + restart) |
| watchlist/scanned_stocks.txt | Human-editable daily scan results |
| data/daily_scan_results.json | Output-only archive (not read by bot) |
| Scripts/clear_stuck_trades.py | Reset STUCK flags |
| Scripts/reset_gridbot_stats.py | Clear grid_bot win/loss |
| Scripts/store_fernet_key.py | One-time: store Fernet key in Windows vault |

---

## Emergency Commands
```powershell
# Clear stuck trades
python Scripts\clear_stuck_trades.py

# Reset grid_bot stats after mass infrastructure failures
python Scripts\reset_gridbot_stats.py

# Check what's open in DB
python Scripts\check_open_trades.py

# Push to GitHub
python git_push.py "your message here"

# Start bot
python bot_engine.py

# Start dashboard (separate terminal)
python web_dashboard.py

# Start BreakoutScanner GUI
python BreakoutScanner.py

# Start BreakoutScanner console
python BreakoutScanner.py --console
```

---

## Watchlist Architecture
- `watchlists/crypto.txt` — master crypto list (manual edit)
- `watchlists/stocks.txt` — master stock list (manual edit)
- `watchlist/scanned_crypto.txt` — daily scanner output (human-editable, READ by bot on startup)
- `watchlist/scanned_stocks.txt` — daily scanner output (human-editable, READ by bot on startup)
- `data/daily_scan_results.json` — archive only, NOT read by bot

To remove a bad pair from injection: edit `watchlist/scanned_crypto.txt`, delete the line, restart bot.

---

## Broker Routing
- **Stocks:** IBKR first (paper port 7497) → Alpaca fallback
- **Crypto:** Kraken via ccxt (paper = simulated locally)
- **Stock close:** Tries BOTH IBKR and Alpaca regardless of DB broker field
- **Ghost trades:** If neither broker has position, marks closed in DB (stops retry loop)
- **Invalid crypto pairs:** Checks Kraken markets on close failure, force-closes in DB

---

## TopStep Combine Status
- Friday: +$1,220 | Monday: +$650 | Tuesday: +$568 = ~$2,438 total
- ~$619 from funded trader status
- Funded account rules: 2 contracts to start, floor rises from $48k to $50k then stays
- Transition fee: $150 one-time
- Ron trades ES futures 5min scalping: EMA5/EMA8-21/VWAP/SuperTrend(7)/MACD

---

## BreakoutScanner.py Status
Standalone scanner (not part of bot) created by Kimmy AI → ChatGPT → fixed by Claude.
- Location: C:\Users\Linda\trading_bot_v2\BreakoutScanner.py
- Console mode working: signals firing (ORCA +6.19%, OPEN +8.51%, TAO +4.60% etc)
- GUI: tkinter launches, Start button works, but alerts not appearing in text widget
- Next fix needed: debug why `root.after(0, gui.add_alert, ...)` isn't reaching the widget
- Config: scanner_config.json (API keys go here)
- Dependencies: yfinance (--no-deps), alpaca-trade-api, ccxt
