# Autonomous Day Trading AI — Project Summary

**Date:** April 20, 2026
**Project Location:** `C:\Users\Linda\trading_bot_v2`
**GitHub:** https://github.com/PNWSkyHippy/Trading_Bot_V2 (private)
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

---

## Active Strategy Status

| Strategy | Status | Timeframe | Key Feature |
|----------|--------|-----------|-------------|
| **bollinger_breakout** | ENABLED | 5m/1h | Triple filter: OBV + EMA50 + RSI direction. Stock blacklist: SMCI. Crypto blacklist: 18 pairs |
| **mean_reversion** | ENABLED | 1h | Stock whitelist: NVDA,PLTR,MRVL,AMZN,INTC,AMD,META,TSLA,ALAB,NIO,MARA,IREN,CLS,CRWV,APLD,LUNR |
| **scalp_master** | ENABLED | 5m | Stock whitelist: META,PLTR,ALAB,AMZN,GOOGL,MSFT,IREN,INTV |
| **dca_accumulator** | ENABLED | 1h | Buy dips 2% below EMA50, RSI<=45 |
| rsi_momentum | DISABLED | — | Negative expectancy |
| ema_crossover | DISABLED | — | Fails slippage test |
| swing_trader | DISABLED | — | Insufficient sample size |
| grid_bot | DISABLED | — | Confirmed abandon |

---

## Bollinger Breakout — Triple Filter Stack (Added April 20, 2026)

All three filters must pass before any signal is generated:

1. **OBV Confirmation** — On-Balance Volume must be rising (long) or falling (short) over 3 bars
2. **EMA50 Trend Filter** — Price must be above EMA50 for longs, below for shorts
3. **RSI Direction Filter** — RSI must be rising (long) or falling (short) over 3 bars

**Stock Blacklist:** SMCI (extreme intraday volatility)

**Crypto Blacklist (Apr 2026 backtest — 365d 1h):**
TON/USD, AGIX/USD, HOT/USD, STRK/USD, EOS/USD, OCEAN/USD, REN/USD, MKR/USD, BAL/USD, HT/USD, XMR/USD, GT/USD, ARB/USD, BCH/USD, XTZ/USD, RLC/USD, FLOW/USD, OKB/USD

---

## Crypto Backtest Results (April 19, 2026 — 365d 1h, 115 pairs)

**Bollinger Breakout** — only strategy that fires on crypto (mean_reversion and scalp_master are stock-only via whitelist, DCA fired on 3 pairs and lost on all)

Top performing crypto pairs for bollinger:
JUP, WLD, DASH, CBETH, WIF, OP, RETH, TIA, FIL, BONK, PYTH, SEI, AVAX, ALGO, ADA, ETH, SOL

**Note:** Backtest did not include OBV/EMA50/RSI filters — live results should be better than backtest shows.

---

## Dashboard — Crypto Backtesting Added

- Asset Class toggle (Stocks / Crypto) added to backtest panel
- Crypto symbols populate from watchlists/crypto.txt
- Uses yfinance with BTC/USD → BTC-USD conversion (no exchange API needed)
- backtester.py: fetch_history_crypto() added, run_all() supports asset_class parameter
- market_scanner.py: get_ohlcv default limit raised from 100 to 210 bars

---

## TP Hit Count — Dashboard Display

- DB column: tp_hit_count INTEGER DEFAULT 0 (added to trades table)
- position_monitor.py writes tp_hit_count on every momentum extension
- Dashboard Take Profit column shows: $X.XXXX 🔴 *1 / *2 / *3 when extensions active

---

## Known Bugs (Pending Fix)

1. **1-2 letter ticker bracket orders** — GE, BE, V, ON etc. silently rejected by Alpaca. Bot records as open, Alpaca never accepts. Fix: detect len(symbol) <= 2, fall back to simple market order + manual SL/TP via position monitor
2. **use_container_width deprecation** — Streamlit warning, harmless until Dec 2025 deadline
3. **Coinbase Non-base16 error** — harmless, falls back to paper mode
4. **Dashboard capital display** — shows DB value not live Alpaca balance

---

## U-Shape Widget (Pine Script — TradingView)

Separate from the trading bot. ES/MES futures trading assistant widget.

**File:** UShapedWidget.txt in repo root

**Current settings:**
- Lookback: 20 bars, Threshold: 18pts, Bandwidth: 10pts
- RSI: length=14, 5-second bars, thresholds 45 long / 55 short
- MACD: 3/10/4 on 5-second source bars, requires 3 consecutive bars in direction
- Signals: GO LONG (green triangle) / GO SHORT (red triangle)

**Known issues:**
- False arrows firing when RSI appears in wrong zone — root cause: request.security("5S") returning previous completed bar not current. Fix: change lookahead=barmerge.lookahead_off to lookahead_on
- MACD panel on separate chart updates every 10 seconds vs 1 second on main chart — moved MACD to main panel as workaround

**Pending fix:**
```pine
rsi_src_5s = request.security(syminfo.tickerid, "5S", close,
             gaps=barmerge.gaps_on, lookahead=barmerge.lookahead_on)
```

---

## ES Trading Assistant (Claude.ai Project)

Separate Claude.ai Project with system prompt for prop firm ES/MES trading.
- 5 conditions: Widget color, SPY direction, Dow spike, RSI quadrant, MACD direction
- Response format: GO or NO, 2 lines max
- RSI thresholds: <=48 long, >=52 short (based on prop firm training videos)
- Used manually during trading session — automated webhook version planned

**Prop firm eval status:** In progress. Lost first trade April 20 due to trailing drawdown rule (unrealized high watermark). Rule now understood, lockout switch removed.

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
| Stock scan | Every 60s | Mon-Fri 10:00-15:44 ET | ZoneInfo ET check |
| Crypto scan | Every 5 min | 24/7 | Always runs |
| Stock EOD close | 12:45 PT weekdays | 15:45 ET | Closes non-overnight stocks |
| Position monitor | Every 30s | 24/7 | Trailing stops + tp_hit_count |
| Capital sync | Every 15 min | 24/7 | Syncs Alpaca |
| EOD report | 14:00 PT | 17:00 ET | Email + SMS |
| ML retrain | 15:00 PT | 18:00 ET | Random Forest |

---

## Pending Work

1. **May 1** — Claude reviewer tiered rebuild
2. **Widget RSI lookahead fix** — change lookahead_off to lookahead_on
3. **1-2 letter ticker fix** — bracket order fallback for short symbols
4. **Momentum rider mode** — reorder exit logic in position_monitor
5. **Dashboard capital display** — DB value vs live Alpaca
6. **use_container_width** — replace with width='stretch'/'content'
7. **Webhook automation** — Pine Script → Python middleware → Alpaca for ES trades
8. **DCA Accumulator NVDA blacklist**

---

## Technical Notes

- Python 3.12, venv at venv312
- 4-space indentation, no tabs
- PowerShell: multiline -c commands fail — always use script files instead
- Streamlit port 8501
- GitHub: https://github.com/PNWSkyHippy/Trading_Bot_V2 (private)
- .env excluded from git — PGP encrypt for cloud backup
- User background: BASIC, COBOL, C, C++, Pascal, mainframe assembly, Spokane WA