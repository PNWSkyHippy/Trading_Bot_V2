# Autonomous Day Trading AI — Project Summary

**Date:** April 17, 2026
**Project Location:** `C:\Users\Linda\trading_bot_v2`
**Status:** Running in paper trading mode (Alpaca stocks + Coinbase/Kraken crypto)
**Capital:** ~$100,214 (Alpaca paper account)

---

## Original Requirements

- Scans stocks, crypto, and futures for profitable opportunities
- Invests no more than **2% of total capital per trade**
- Uses a **1.5% stop-loss** and **3% take-profit** on every trade
- Dynamically raises take-profit if continued growth is expected
- Trails the stop-loss upward, staying **1.5% behind** the current price
- Targets at least **2% daily profit**, compounded each day
- Starting capital of **$100,000**
- **15% max daily loss** halts trading for the day
- **10 consecutive losing trades** halts trading for the day
- Provides **detailed daily reports** of all trades via email + SMS
- Shows real-time statistics: open trades, capital value, profit/loss ratios
- Includes a **chat interface** (Claude AI) to talk to the bot and issue commands
- Supports **monthly withdrawals** for living expenses
- Maintains **IRS Form 8949-compatible tax records**

---

## Project Architecture

```
trading_bot_v2/
├── bot_engine.py              ← MAIN ENTRY POINT
├── dashboard.py               ← Streamlit browser dashboard (port 8501)
├── config.py                  ← All settings, API keys, parameters
├── requirements.txt
├── symbol_params.json         ← Scalp master adaptive SL/TP per symbol
├── full_strategy_stress_test.py ← Adversarial backtest battery
├── .env                       ← API keys (never commit)
│
├── core/
│   ├── risk_manager.py        ← All risk rules enforced here
│   ├── trade_executor.py      ← Sends orders to brokers
│   ├── position_monitor.py    ← Watches open trades, trailing stops
│   ├── broker_manager.py      ← Multi-broker management
│   ├── inverse_etf_mapper.py  ← Maps bearish signals to inverse ETFs
│   └── kraken_executor.py     ← Kraken crypto trading
│
├── scanners/
│   └── market_scanner.py      ← Scans stocks + crypto, routes through strategy engine
│
├── strategies/
│   ├── base_strategy.py
│   ├── strategy_engine.py
│   ├── bollinger_breakout.py  ← ENABLED — Run C params, SMCI blacklisted
│   ├── mean_reversion.py      ← ENABLED — symbol whitelist added
│   ├── scalp_master.py        ← ENABLED — 8-symbol whitelist, adaptive SL/TP
│   ├── dca_accumulator.py     ← ENABLED
│   ├── rsi_momentum.py        ← DISABLED (negative expectancy)
│   ├── ema_crossover.py       ← DISABLED (fails slippage test)
│   ├── swing_trader.py        ← DISABLED (insufficient sample size)
│   └── grid_bot.py            ← DISABLED (confirmed abandon)
│
├── intelligence/
│   ├── claude_reviewer.py     ← Claude autonomous signal reviewer
│   │                             CURRENTLY DISABLED (API limit, resets May 1)
│   ├── chat_interface.py      ← Claude AI chat (commands + context)
│   ├── condition_detector.py  ← Market condition classifier
│   ├── ml_scorer.py           ← Random Forest ML model
│   └── backtester.py          ← Historical backtesting engine
│
├── reporting/
│   └── report_generator.py
│
├── data/
│   ├── database.py
│   └── trading_bot.db
│
├── watchlists/
│   ├── stocks.txt             ← 121 symbols (expanded from 21)
│   └── crypto.txt             ← 115 pairs (expanded from 30)
│
├── logs/
│   └── bot.log
└── exports/                   ← Tax CSVs
```

---

## Active Strategy Status

| Strategy | Status | Timeframe | Key Feature |
|----------|--------|-----------|-------------|
| **bollinger_breakout** | ENABLED | 5m | Run C params (period=20, std=2.0, sq=0.04, ms=0.70), SMCI blacklisted |
| **mean_reversion** | ENABLED | 1h | Whitelist: NVDA,PLTR,MRVL,AMZN,INTC,AMD,META,TSLA,ALAB,NIO,MARA,IREN,CLS,CRWV,APLD,LUNR |
| **scalp_master** | ENABLED | 5m | Whitelist: META,PLTR,ALAB,AMZN,GOOGL,MSFT,IREN,INTV. Adaptive SL/TP via symbol_params.json |
| **dca_accumulator** | ENABLED | 1h | Buy dips 2% below EMA50, RSI<=45 |
| rsi_momentum | DISABLED | — | Negative expectancy confirmed |
| ema_crossover | DISABLED | — | Fails 1x slippage test |
| swing_trader | DISABLED | — | Insufficient sample size |
| grid_bot | DISABLED | — | Confirmed abandon |

---

## Full Adversarial Stress Test Results (April 16, 2026)

| Strategy | Score | Verdict | PF | Sharpe | 1.5x Slip | Action |
|----------|------:|---------|-----|--------|-----------|--------|
| DCA Accumulator | 47 | Refine | 1.494 | 5.57 | 1.263 PASS | KEEP |
| Bollinger Breakout | 44 | Refine | 1.380 | 9.58 | 1.076 PASS | KEEP |
| Scalp Master | 44 | Refine | 1.857 | 27.29 | 1.273 PASS | KEEP |
| EMA Crossover | 42 | Refine | 1.049 | 0.52 | 0.925 FAIL | DISABLED |
| Mean Reversion | 37 | Abandon | 0.999 | -0.42 | 0.884 FAIL | WHITELIST FIX APPLIED |
| Swing Trader | 32 | Abandon | 1.401 | -7.87 | 0.802 FAIL | DISABLED |

---

## Risk Management Settings

| Rule | Value |
|------|-------|
| Max position size | 2% of total capital |
| Stop-loss | 1.5% below entry |
| Take-profit | 3% above entry |
| Trailing stop | 1.5% behind current price |
| Daily loss ceiling | 15% |
| Consecutive loss halt | 10 losses |
| Max open positions | 30 |
| Min signal confidence | 0.65 |
| Stock EOD close | 3:45 PM ET (12:45 PT) weekdays |

---

## Scheduled Jobs

| Job | Schedule PT | ET | Description |
|-----|------------|-----|-------------|
| Stock scan | Every 60s | Mon-Fri 10:00-15:44 ET gated | ZoneInfo ET check |
| Crypto scan | Every 5 min | 24/7 | Always runs |
| Stock EOD close | 12:45 PT weekdays | 15:45 ET | Closes non-overnight stocks |
| Position monitor | Every 30s | 24/7 | Trailing stops |
| Capital sync | Every 15 min | 24/7 | Syncs Alpaca |
| EOD report | 14:00 PT | 17:00 ET | Email + SMS |
| ML retrain | 15:00 PT | 18:00 ET | Random Forest |

Machine is Pacific Time (Spokane WA). schedule.at() times are PT. Market hours use ZoneInfo ET in code.

---

## Claude Autonomous Reviewer (intelligence/claude_reviewer.py)

**Status: DISABLED** — API limit hit April 17. Resets May 1, 2026.

**Architecture:**
- Morning briefing once per hour (120 min cache) sets MarketContext
- Per-signal review: APPROVE / REJECT / SKIP
- Conservative fallback: ANY failure = SKIP, never default to APPROVE
- Level 2 autonomy: veto power only, cannot initiate trades

**Fixes needed before May 1 rebuild:**
1. Tiered architecture: rules engine filters 1000 to 50 candidates, Claude only reviews top 50
2. Batch signals: one API call evaluates 4-5 signals simultaneously
3. Morning briefing on schedule (10 AM ET) not triggered by first signal
4. Delta-only payloads: send only changed data
5. JSON-only responses: no narrative in auto mode
6. Target: 15-25 API calls/day at $0.50-2/day cost

**40 Skills available in ~/.claude/Skills/ for reviewer v2:**
- Daily open: market-environment-analysis, market-news-analyst, economic-calendar-fetcher, earnings-calendar, market-breadth-analyzer, market-top-detector, ftd-detector, sector-analyst, theme-detector, exposure-coach, stanley-druckenmiller
- Per signal: us-stock-analysis, technical-analyst, earnings-trade-analyzer, institutional-flow-tracker
- Pre-execution: position-sizer
- Weekly: macro-regime-detector, backtest-expert

---

## Key Bugs Fixed This Session

1. **ETF Price Mismatch** — MSFT->TQQQ used MSFT price for TQQQ. Fixed: fetch real ETF price after remap in market_scanner.py
2. **Stock scan after hours** — schedule library has no TZ. Fixed: ZoneInfo ET check inside _run_stock_scan()
3. **Stock EOD close missing** — stocks open all weekend. Fixed: _close_stocks_eod() at 12:45 PT
4. **Claude reviewer retry storm** — failed briefings retried every scan. Fixed: cache failures 120 min
5. **Ghost positions** — APLD etc in DB not in Alpaca. Cleaned via SQL UPDATE
6. **Strategy state persistence** — key format mismatch. Fixed: consistent strategy_{name}_enabled
7. **Manual closes polluting stats** — fixed: skip when exit_reason == manual_close
8. **Position monitor after hours** — stock price fetches failing. Fixed: _stock_market_open() check

---

## !Day_Trade Overnight Flag

- DB column: is_overnight INTEGER DEFAULT 0
- Dashboard checkbox: Hold Overnight in manual trade form
- EOD close skips is_overnight=1 positions
- Bot-generated trades always is_overnight=0

---

## Scalp Master Adaptive SL/TP

- File: symbol_params.json (project root)
- Recalculates every 20 closed scalp trades per symbol
- new_sl = avg_actual_loss * 0.85
- new_tp = max(avg_actual_win * 0.90, new_sl * 2.5)
- MIN_RR = 2.5 enforced always
- Thread-safe atomic file writes

---

## Trailing Stop / TP Extension — Known Issue

In position_monitor._process_position(), check_exit_conditions() fires BEFORE calculate_trailing_stop(). This means trades close AT the TP price instead of extending. To ride momentum moves the order needs reversing — extend TP first, then check exit against new levels.

Momentum Rider Mode (not yet built): flip is_overnight=True on strong momentum, switch to trailing-stop-only mode, reorder exit logic.

---

## Performance Goals vs Reality

- Goal: 2% daily = ~$2,004/day on $100k
- Need: ~60 completed trades/day at 66% win rate
- Before expansion: 30-50 trades/day, 43-50% win rate
- After Claude reviewer (disabled): 3-4 trades/day
- After watchlist expansion: 26 positions open within one session
- Best single day: ~0.7% ($700) on April 16, 2026

---

## Pending Work

1. May 1: Claude reviewer tiered rebuild
2. Momentum rider mode (reorder exit logic)
3. DCA Accumulator NVDA blacklist
4. Monitor expanded watchlist signal quality
5. ES trading assistant Claude.ai Project for prop firm
6. Fix dashboard capital display (DB value vs live Alpaca)
7. use_container_width deprecation warnings in dashboard.py
8. Coinbase Non-base16 error (harmless but noisy)

---

## Technical Notes

- Python 3.12, venv at venv312
- 4-space indentation, no tabs
- PowerShell: use semicolons on one line for -c commands (multiline gets scrambled)
- Streamlit port 8501, other apps use --server.port 8502
- Close old browser tabs before restart to avoid React error 185
- User background: BASIC, COBOL, C, C++, Pascal, mainframe assembly
