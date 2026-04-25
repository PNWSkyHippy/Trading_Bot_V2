# Trading Bot V2 — Project Summary
Last updated: April 24, 2026 (End of Session 4)

## Project Overview
Autonomous day trading bot. Paper trading → live trading transition.
- **Repo:** https://github.com/PNWSkyHippy/Trading_Bot_V2 (private)
- **Location:** C:\users\linda\trading_bot_v2
- **Stack:** Python 3.12, venv312, Streamlit port 8501, SQLite
- **Status:** Paper trading IBKR + Alpaca stocks, Kraken crypto paper
- **Capital:** ~$50,523 prop firm combine (target $53,000 for funded account)

---

## Architecture

### Core Files
| File | Purpose |
|---|---|
| `bot_engine.py` | Main entry point, scheduler, all timed jobs |
| `dashboard.py` | Streamlit dashboard port 8501 |
| `config.py` | All settings — position sizes, stop loss %, watchlists |
| `.env` | API keys (never committed) |
| `data/trading_bot.db` | SQLite database |

### Key Modules
| File | Purpose |
|---|---|
| `core/risk_manager.py` | ALL risk rules — position sizing, stops, daily limits |
| `core/position_monitor.py` | Watches open trades — trailing stops, stale check, VWAP exit, stuck trade throttle |
| `core/trade_executor.py` | Routes orders to correct broker, bracket order handling |
| `core/ibkr_executor.py` | IBKR integration — persistent connection clientId=2, port 7497 paper |
| `core/settlement_tracker.py` | T+1 settlement tracking for IBKR cash account |
| `core/broker_manager.py` | Multi-broker management |
| `data/database.py` | All DB operations including session_state, starting_capital_today |
| `intelligence/chat_interface.py` | Haiku chatbot with pre-parse layer |
| `intelligence/backtester.py` | Backtesting engine with 2-bar trailing stop mode |
| `intelligence/ml_scorer.py` | Random Forest ML model |
| `intelligence/condition_detector.py` | Market condition classifier |
| `reporting/weekly_tradelog.py` | Weekly CSV trade log exporter |
| `reporting/analyze_trades.py` | Performance analyzer (Opus 4, integrated) |
| `reporting/report_generator.py` | Daily HTML email report |

### Strategies (11 total)
| Strategy | Status | Notes |
|---|---|---|
| rsi_momentum | Disabled | |
| bollinger_breakout | **Enabled** | OBV triple filter |
| ema_crossover | Disabled | |
| mean_reversion | Disabled | 21% WR, -$396 — killed |
| scalp_master | **Enabled** | |
| swing_trader | Disabled | |
| grid_bot | Disabled | |
| dca_accumulator | **Enabled** | |
| vwap_momentum | **Enabled** | VWAP + EMA 5/13/34 |
| hammer_reversal | **Enabled** | SOL/USD only, 5-filter stack: RSI+Stoch+BB+Hammer+OBV |
| orb_breakout | **Enabled** | GO whitelist stocks, 5m bars, VWAP exit |

### ORB GO Whitelist
META, TSLA, MSFT, AMD, MRVL, ALAB, PLTR, CRWV, IREN, CLS, AMZN, GOOGL, AAPL, SPY, QQQ

### ORB TUNE (excluded)
NVDA, INTC, NIO, APLD, MARA

---

## Broker Setup

### IBKR (Primary Stock Broker)
- Paper account: DUQ511882
- Live account: approved, deposit hold until April 28
- TWS must be running before bot starts
- Port 7497 (paper), 7496 (live)
- ClientId=2 (1 causes conflict with TWS)
- Read-Only API must be UNCHECKED in TWS settings
- `IBKR_ENABLED = True` in config.py
- `IBKR_PAPER_MODE = True` until live flip
- First successful trades: OPEN LONG +$5.44, CRWV SHORT +$15.04 (Apr 24)
- IBC installed at C:\IBC — partially configured, needs IB Gateway installer to work

### Alpaca (Fallback Stock Broker)
- Live account approved
- Paper URL: https://paper-api.alpaca.markets
- Live URL: https://api.alpaca.markets
- Fallback when IBKR unreachable

### Kraken (Crypto — disabled)
- KRAKEN_ENABLED = False
- All crypto currently paper simulation

### Coinbase
- Connected, paper mode

---

## Key Bugs Fixed This Session

### P&L Restart Bug
- **Root cause:** `starting_cap = capital - pnl_today` drifted on restart
- **Fix:** `set_starting_capital_today()` locks capital ONCE at first call each day in session_state
- **Files:** `data/database.py`, `core/risk_manager.py`, `dashboard.py`

### IBKR Persistent Connection
- **Root cause:** `is_available()` was connecting/disconnecting on every trade check, causing clientId conflicts
- **Fix:** Persistent connection held all session. `is_available()` just checks `isConnected()`
- **File:** `core/ibkr_executor.py`

### Bracket Order Ghost Fix
- **Root cause:** Alpaca bracket orders lock shares, close attempt fails with "insufficient qty"
- **Fix:** `cancel_open_orders()` before close, 0.5s wait, then close
- **File:** `core/trade_executor.py`

### PSQ Infinite Retry Loop
- **Root cause:** Failed close left trade open in DB, stale check retried every 30s forever
- **Fix:** `_attempt_close()` tracks failed attempts. After `MAX_CLOSE_ATTEMPTS=3` flags STUCK
- **File:** `core/position_monitor.py`

### Haiku Enable/Disable Strategy
- **Root cause:** Haiku second-guessed simple commands, denied strategy existence
- **Fix:** Pre-parse layer detects enable/disable/morning scan BEFORE sending to Haiku
- **File:** `intelligence/chat_interface.py`

---

## New Features This Session

### Morning Scan Command
- Triggers: "morning scan", "what should I trade", "top setups", "best setups"
- Scans ORB whitelist stocks for moves ≥0.3% with volume ≥1.2x average
- Returns top 5 sorted by move×volume with direction, price, guidance

### Stale Position Sell-Off (ADX/DI)
- After 3 hours open: check ADX
- ADX < 25 (stalled) → close immediately
- ADX ≥ 25: direction mismatch → close; aligned → hold
- Validated live: NU closed on first attempt

### ORB VWAP Cross Exit
- ORB trades skip fixed TP — ride until price crosses back below VWAP (long) or above VWAP (short)
- Safety ceiling TP still applies at 10-15%

### OBV Filter on Hammer Reversal
- OBV must be rising for last 3 consecutive bars before signal fires
- Prevents signals on bounce attempts in waterfall selloffs

### 2-Bar Trailing Stop (Pine Script Port)
- `TwoBarStop` class in `intelligence/backtester.py`
- `initial_stop()`: lowest low of prior N bars at entry (no lookahead)
- `update_stop()`: ratchets up on new N-bar high, never down
- `check_stop_hit()`: intrabar logic, fills at stop price not close
- N=2 default, configurable 1-20
- Dashboard backtest panel: radio button Standard vs 2-Bar, lookback N input

### Weekly Trade Log Exporter
- File: `reporting/weekly_tradelog.py`
- Runs every Sunday midnight PT via scheduler, covers previous Sun-Sat
- Output: `reports/MM-DD-YYYY_MM-DD-YYYY_tradelog.csv`
- Columns: Symbol, Entry Date, Entry Time, Entry Price, Exit Date, Exit Time, Exit Price, Shares, P&L, Direction, Strategy, Broker, Exit Reason, Hold Duration

### Performance Analyzer
- File: `reporting/analyze_trades.py` (Opus 4 generated, integrated)
- 7-section report: Overall stats, by setup, by time of day (full 24h), by day of week (full 7 days), pattern detection, summary, recommendations
- Min trades threshold: 10
- Usage: `python reporting/analyze_trades.py reports/04-19-2026_04-25-2026_tradelog.csv --output reports/analysis.txt`

---

## Monday Checklist (April 27)
1. Start TWS first, wait for full load
2. Approve API connection dialog in TWS
3. Start bot: `python bot_engine.py`
4. Watch for `IBKR connected: port=7497 paper clientId=2`
5. Confirm stock trades routing to IBKR not Alpaca
6. Run full IBKR paper session

## Tuesday/Wednesday (April 28-29)
- IBKR deposit hold clears April 28
- Flip to live: `IBKR_PAPER_MODE = False` in config.py
- Update `.env` with live DU account number
- TWS: switch to port 7496

---

## Key Analysis Findings (Apr 12-18 backtest data, 716 trades)

**Time of day:**
- 00:00-09:30 overnight: -$1,067 over 263 trades (35.7% WR) — biggest drain (crypto paper)
- 10:30-11:30: best hour +$558 (52% WR)
- 11:30-12:30: 84% WR, +$556
- 13:30-14:30: 87% WR, +$191

**Day of week:**
- Tuesday: +$1,219 (61% WR) ⭐
- Thursday: +$1,081 (47% WR) ⭐
- Sunday: -$911, Monday: -$185, Wednesday: -$179, Friday: -$187, Saturday: -$187

**Strategy performance:**
- mean_reversion: 21% WR, -$396 — KILLED
- bollinger_breakout: quietly bleeding, needs monitoring
- manual trades: -$230 from one -$376 outlier

---

## Pending Items

### High Priority
1. **IBC / IB Gateway** — needs IB Gateway installer (not TWS). IBC at C:\IBC configured but fails because TWS installed without version subfolder structure IBC expects.
2. **IBKR MAX_RECONNECT_ATTEMPTS** — increase from 3 to 5 for market-close hiccup resilience
3. **Alpaca ghost cleanup** — 6 positions (PSQ, MSFT, GEM, NIO, NFLX, SOFI) still open at Alpaca from Apr 23. Close manually at 9:30 AM Monday April 27.

### Strategy Work
4. **BTC on Hammer whitelist** — add back once SOL shows WR ≥55% over 20+ live trades
5. **Overnight crypto drain** — disable crypto scanning 00:00-06:00 ET? -$1,067 in that block

### Distribution / Future
6. **Dashboard login** — password protection for distribution
7. **Distribution cleanup script** — blank .env, cleared DB, removed personal screenshots
8. **Unusual Whales MCP** — $50/month, multi-model Opus/Sonnet/Haiku architecture (finish book first)
9. **Morning scan — add crypto candidates** — currently stocks only
10. **Walk-forward backtesting** — proper out-of-sample validation

---

## Key File Locations
- DB path: `data/trading_bot.db`
- Reports folder: `reports/`
- Logs: `logs/bot.log`
- IBC: `C:\IBC\` (config.ini configured, needs IB Gateway installer)
- TWS: `C:\Jts\` (auto-updating) and `C:\Jts\1019\` (offline copy for IBC)
- venv: `venv312\Scripts\activate`

## Chat Commands Quick Reference
- `morning scan` — top ORB candidates
- `enable/disable <strategy>` — pre-parsed, bypasses Haiku
- `list strategies` — all 11 with ON/OFF status
- `pause trading` / `resume trading`
- `strategy stats` — win rate and P&L per strategy
- See `CHAT_COMMANDS.md` for full list

## Reference Documents
- `README.md` — installer guide
- `REFERENCE_DOCS.md` — index of all files
- `CHAT_COMMANDS.md` — all chat commands
- `strategies/INTEGRATION_GUIDE.py` — how to add a strategy
- `data/BROKER_INTEGRATION_GUIDE.py` — how to add a broker
