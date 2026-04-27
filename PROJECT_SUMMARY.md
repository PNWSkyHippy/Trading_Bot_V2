# Autonomous Day Trading Bot V2 — Project Summary

**Last Updated:** April 26, 2026  
**Project Location:** `C:\Users\Linda\trading_bot_v2`  
**Status:** Running in paper trading mode (Alpaca stocks + Kraken crypto paper sim)  
**Python:** 3.12, venv312, Streamlit dashboard port 8501

---

## Current Architecture

```
trading_bot_v2/
├── bot_engine.py              ← MAIN ENTRY POINT
├── dashboard.py               ← Streamlit browser dashboard
├── config.py                  ← All settings, API keys, parameters
├── requirements.txt
├── .env                       ← API keys (not committed to git)
│
├── core/
│   ├── risk_manager.py
│   ├── trade_executor.py      ← Routes crypto to Kraken, stocks to Alpaca/IBKR
│   ├── position_monitor.py    ← Exit logic: trailing stop, time stops, pivot break
│   ├── broker_manager.py      ← Per-broker capital tracking
│   └── kraken_executor.py     ← Kraken crypto (paper mode = local simulation)
│
├── scanners/
│   ├── market_scanner.py      ← Main scanner — routes through strategy engine
│   └── daily_market_scanner.py← 4:30 PM ET scan, writes temp watchlist files
│
├── strategies/
│   ├── base_strategy.py       ← Abstract base — stock_enabled/crypto_enabled flags
│   ├── strategy_engine.py     ← Orchestrates all strategies, asset class filtering
│   ├── rsi_momentum.py        ← DISABLED (poor live performance)
│   ├── bollinger_breakout.py  ← ENABLED stocks only (crypto_enabled=False)
│   ├── ema_crossover.py       ← DISABLED
│   ├── mean_reversion.py      ← DISABLED
│   ├── scalp_master.py        ← ENABLED
│   ├── swing_trader.py        ← DISABLED
│   ├── grid_bot.py            ← ENABLED — primary crypto strategy, reviewer_exempt
│   ├── dca_accumulator.py     ← ENABLED
│   ├── vwap_momentum.py       ← ENABLED
│   ├── hammer_reversal.py     ← ENABLED
│   └── orb_breakout.py        ← ENABLED
│
├── intelligence/
│   ├── chat_interface.py      ← Haiku chat + pre-parse commands + watchlist queries
│   ├── claude_reviewer.py     ← Signal reviewer — crypto bypasses market hours gate
│   ├── condition_detector.py
│   ├── ml_scorer.py
│   └── backtester.py
│
├── reporting/
│   └── report_generator.py
│
├── data/
│   ├── database.py
│   └── trading_bot.db
│
├── watchlists/
│   ├── stocks.txt             ← Master stock watchlist
│   └── crypto.txt             ← Master crypto watchlist
│
├── watchlist/
│   ├── scanned_stocks.txt     ← Temp: daily scanner results (stocks)
│   └── scanned_crypto.txt     ← Temp: daily scanner results (crypto)
│
├── logs/bot.log
│
└── Utility Scripts (project root):
    ├── check_trades.py        ← Last 20 closed trades with entry/exit/reason
    ├── todays_stats.py        ← Today's P&L by asset class and strategy
    ├── weekly_stats.py        ← 7-day breakdown by day/asset/strategy/broker
    ├── clear_stuck_trades.py  ← Resets stuck/failed close flags
    ├── force_close_paper_trades.py ← Force-closes ghost DB positions
    ├── flush_log.py           ← Clears bot.log keeping last 50 lines
    └── git_push.py            ← Quick git add/commit/push
```

---

## Brokers

| Broker | Type | Mode | Status |
|--------|------|------|--------|
| **Alpaca** | Stocks | Paper | Active — `https://paper-api.alpaca.markets` |
| **IBKR** | Stocks | Paper | Active — TWS must be running manually (port 7497) |
| **Kraken** | Crypto | Paper | Active — paper mode simulated LOCALLY (Kraken has no sandbox) |
| **Coinbase** | Crypto | — | DEPRECATED — Coinbase Pro API shut down, Advanced Trade auth incompatible |

### Important Notes
- `KRAKEN_PAPER_MODE = True` — simulates fills locally, uses real Kraken prices
- Coinbase is completely removed from trade execution (auth format incompatible)
- IBKR launches TWS manually — IBC automation not yet working
- All fund inject/withdraw operations are informational only

---

## Strategy Status (as of Apr 26, 2026)

| Strategy | Status | Asset Class | Notes |
|----------|--------|-------------|-------|
| rsi_momentum | DISABLED | — | Poor live performance |
| bollinger_breakout | ENABLED | **Stocks only** | `crypto_enabled=False` — bleeds -$860 on crypto vs +$1,064 on stocks |
| ema_crossover | DISABLED | — | |
| mean_reversion | DISABLED | — | |
| scalp_master | ENABLED | Both | |
| swing_trader | DISABLED | — | |
| **grid_bot** | **ENABLED** | **Crypto primary** | `reviewer_exempt=True` — 53% WR, +$291 today. Star performer |
| dca_accumulator | ENABLED | Both | |
| vwap_momentum | ENABLED | Both | |
| hammer_reversal | ENABLED | Both | |
| orb_breakout | ENABLED | Stocks | ORB window 9:45-10:15 ET |

### Key Strategy Flags (base_strategy.py)
- `stock_enabled` / `crypto_enabled` — per-asset-class on/off
- `ml_exempt` — skip ML score blending
- `auto_disable_exempt` — never auto-disable based on win rate
- `reviewer_exempt` — skip Claude reviewer (Grid Bot uses non-standard indicators)

---

## Stop Mode Settings

```python
STOCK_STOP_MODE    = "standard"   # standard % stop — adequate for stocks
CRYPTO_STOP_MODE   = "two_bar"    # 2-Bar trailing stop — proven superior
TWO_BAR_LOOKBACK_N = 2            # N=2 recommended
```

**Backtest results (Apr 2026) that drove this decision:**
- Standard stop: 0 GO signals, 35% WR, avg PF 0.74
- 2-Bar N=2: 4 GO signals, 50% WR, avg PF 144.81
- Grid Bot 2-Bar: 75% WR, Sharpe 22, PF 8.54 (BTC 5min)
- DCA 2-Bar: 64% WR, +3.27% (BTC 1hr/365d)

---

## Position Monitor Exit Logic (priority order)

1. STUCK check — skip if exceeded 3 close attempts
2. EOD close — 15:45 ET stocks
3. Stop-loss
4. ORB VWAP cross exit
5. Early loss (20 min check) — `EARLY_LOSS_MIN_PCT = -0.3`
6. Perf time stop 1hr — `PERF_CHECK_1HR_MIN_PCT = 0.2` (lowered from 0.5)
7. Perf time stop 3hr — `PERF_CHECK_3HR_MIN_PCT = 1.5`
8. Hard time stop — `HARD_TIME_STOP_HOURS = 3.5`
9. Take-profit + momentum rider (up to 3 extensions)
10. Pivot point break (S1/R1) — after 30 min
11. Stale ADX/DI check — after 3 hrs
12. Trailing stop update + logging

---

## Claude Reviewer (claude_reviewer.py)

- **Enabled** — requires `ANTHROPIC_API_KEY` in `.env`
- **Crypto bypass** — `allow_trading=False` from morning briefing does NOT block crypto (crypto runs 24/7)
- **reviewer_exempt** — Grid Bot bypasses review entirely (no standard indicators to evaluate)
- **Model:** claude-sonnet-4-5
- **Fallback:** Any failure/timeout = SKIP (conservative)

---

## Weekly Performance (Apr 19-26, 2026)

```
Total: 1219 trades | P&L: +$284.76

By day:
  Apr 26: 346 trades | 48.0% WR | +$149.54  (Grid Bot dominant, 2-Bar active)
  Apr 25:  80 trades | 32.5% WR | -$160.27
  Apr 24: 166 trades | 31.3% WR | -$555.72
  Apr 23: 159 trades | 47.2% WR | +$1,349.14
  Apr 22: 164 trades | 46.3% WR | +$891.30
  Apr 21:  64 trades | 34.4% WR | -$30.72
  Apr 20: 151 trades | 34.4% WR | -$671.48
  Apr 19:  89 trades | 32.6% WR | -$687.04

By asset class:
  STOCKS: 151 trades | 29.1% WR | +$1,178 (Bollinger carrying stocks)
  CRYPTO: 1068 trades | 42.5% WR | -$893 (Bollinger was destroying crypto — now disabled)

By strategy (highlights):
  grid_bot:              214 trades | 53.3% WR | +$291 ✅
  bollinger_breakout (stocks): 123 trades | 30.9% WR | +$1,064 ✅
  bollinger_breakout (crypto): 773 trades | 39.2% WR | -$860 ❌ NOW DISABLED FOR CRYPTO

By broker:
  alpaca:   142 trades | 31.0% WR | +$1,251
  coinbase: 183 trades | 53.0% WR | +$238  (paper sim, pre-deprecation)
  kraken:    87 trades | 40.2% WR | -$419  (new, still establishing)
  paper:    805 trades | 39.8% WR | -$806  (old Bollinger crypto)
```

---

## Haiku Chat Commands (pre-parsed, no API call needed)

### Watchlist
- `"what stocks are you watching"` / `"what crypto are you watching"`
- `"show watchlist"` / `"show injected symbols"`
- `"is BTC/USD being watched"` / `"is AAPL in watchlist"`
- `"reload watchlist"` / `"refresh watchlist"`

### Strategies
- `"enable grid_bot"` / `"disable bollinger_breakout"`
- `"list strategies"` / `"strategy stats"`

### Trading
- `"pause trading"` / `"resume trading"`
- `"show my stats"` / `"capital breakdown"`
- `"morning scan"` / `"top setups"`

---

## Filesystem Connector
Claude now has direct read/write access to `C:\Users\Linda\trading_bot_v2` via the Filesystem MCP connector. No more file uploads needed — Claude can read and write files directly.

---

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Crypto scan | Every 5 min, 24/7 | Threaded — won't block scheduler |
| Stock scan | Every 60s, Mon-Fri 10:00-15:44 ET | Threaded |
| Position monitor | Every 30s, 24/7 | Checks exits, trailing stops |
| Capital sync | Every 15 min | Syncs broker balances |
| EOD stock close | 15:45 ET weekdays | Closes all stock positions |
| EOD report | 17:00 ET daily | Email report |
| Daily scanner | 16:30 ET weekdays | Scans top stocks + crypto, updates watchlists |
| ML retrain | 18:00 ET daily | Retrains Random Forest |
| Weekly log | Sunday 00:00 PT | Weekly trade export |

---

## Known Open Issues

1. **Grid Bot reviewer_exempt** — using ADX+BB signals not readable by Claude. Re-evaluate after 50+ live trades. Consider populating RSI/volume in metadata.

2. **Bollinger crypto_enabled=False** — disabled based on Apr 2026 data. Re-evaluate monthly. Consider crypto-specific variant with tighter filters.

3. **HARD_TIME_STOP_HOURS = 3.5** — kills profitable trades. Consider bypassing if pnl >= 2.0%.

4. **PERF_CHECK_1HR_MIN_PCT = 0.2** — lowered from 0.5 today, monitor effect on trade quality.

5. **Coinbase fully removed** — when Coinbase fixes their Advanced Trade API key generation (portal was broken Apr 26), consider adding back as secondary crypto broker.

6. **IBKR IBC automation** — still launching TWS manually. IBC double-session loop unresolved.

7. **Per-broker capital display** — broker_manager.py has the infrastructure but dashboard doesn't show per-broker breakdown yet.

8. **Daily scanner crypto** — runs weekdays only. Should run 7 days for crypto.

9. **Hard time stop bypass** — profitable trades getting killed at 3.5hr. Proposed: bypass if pnl >= 2.0%.

10. **Dashboard overhaul** — planned full trading terminal with TradingView charts, draggable panels, manual trade entry, per-broker stats. Multi-session project.

---

## Technical Notes

- **Python indentation:** 4-space, no tabs
- **Linda's background:** BASIC, COBOL, C, C++, Pascal, mainframe assembly
- **Timezone:** Bot uses ET for market hours, Linda is in Spokane WA (PT)
- **Git:** Local `python git_push.py` for cloud backup
- **Filesystem MCP:** Claude has direct read/write access to project directory
- **GitHub connector:** Disconnected (was causing tool refresh loop every 60s)
