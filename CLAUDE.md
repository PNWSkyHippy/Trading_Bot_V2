# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Environment

- **Python 3.12** via `venv312` — always activate before running anything
- **Platform:** Windows 11, PowerShell. Machine timezone is **Pacific Time (Spokane, WA)**
- **API keys** live in `.env` (never commit). Loaded via `python-dotenv` in `config.py`

```bash
# Activate venv (PowerShell)
venv312\Scripts\activate

# Or one-liner (use semicolons in PowerShell -c, not newlines)
venv312\Scripts\activate; python bot_engine.py
```

---

## Running the Bot

```bash
# Main bot engine (normal)
python bot_engine.py

# Main bot engine (verbose signal debugging — log files grow fast)
python bot_engine.py --verbose

# Dashboard (separate terminal — web console)
python web_dashboard.py

# Auto-start both (double-click or run from cmd)
start_bot.bat
```

Dashboard at http://localhost:8125. Replaces the old Streamlit dashboard.py.

---

## Backtesting

```bash
# All strategies, 2 years of data
python intelligence/backtester.py --all --days 730

# Single symbol
python intelligence/backtester.py --symbol AAPL --days 730

# Full adversarial stress test
python full_strategy_stress_test.py
```

---

## Utility Scripts

```bash
# Check settlement status (T+2 cash account tracking)
python -c "from core.settlement_tracker import settlement_tracker; import json; print(json.dumps(settlement_tracker.get_settlement_status(), indent=2))"

# Flush/fix DB records
python flush_closed_trade.py
python flush_session.py
python flush_trade.py

# Unhalt bot (if circuit breaker tripped)
python UnHaltBot.py
```

---

## Architecture

### Data Flow

```
market_scanner.py
    → strategy_engine.py         (runs all enabled strategies, deduplicates)
        → [bollinger_breakout, mean_reversion, scalp_master, dca_accumulator, ...]
    → intelligence/claude_reviewer.py  (DISABLED — API limit, resets May 1 2026)
    → risk_manager.py            (position sizing, circuit breakers — NEVER bypass)
    → trade_executor.py          (sends orders to Alpaca / Kraken)
    → database.py                (SQLite: data/trading_bot.db)
```

`bot_engine.py` is the scheduler. It wires jobs via the `schedule` library (times are PT — the machine's local clock). Market hours are enforced inside `_run_stock_scan()` using `ZoneInfo("America/New_York")` — this is the authoritative gate, not the scheduler.

### Key Modules

| File | Purpose |
|------|---------|
| `config.py` | Single source of truth for all parameters — change settings here, not inline |
| `core/risk_manager.py` | Every trade passes through here. Enforces position sizing, stop-loss, circuit breakers |
| `core/position_monitor.py` | Runs every 30s; manages trailing stops. **Known issue:** `check_exit_conditions()` fires before `calculate_trailing_stop()`, so TP extensions don't ride momentum |
| `core/broker_manager.py` | Multi-broker abstraction (Alpaca stocks, Kraken crypto) |
| `core/settlement_tracker.py` | T+2 cash account tracking to avoid PDT violations |
| `data/database.py` | SQLite wrapper — singleton `db` object imported everywhere |
| `strategies/strategy_engine.py` | Runs all 8 strategy instances, deduplicates signals, auto-disables underperformers |
| `strategies/base_strategy.py` | `BaseStrategy` and `TradeSignal` dataclasses — all strategies extend this |
| `intelligence/ml_scorer.py` | Random Forest signal scorer; retrains daily at 18:00 ET |
| `intelligence/condition_detector.py` | Market condition classifier (trending/ranging/volatile) |
| `intelligence/claude_reviewer.py` | Claude autonomous signal reviewer — **currently disabled** |
| `intelligence/chat_interface.py` | Conversational interface for bot commands via dashboard |

### Strategy Status

| Strategy | Status | Notes |
|----------|--------|-------|
| `bollinger_breakout` | ENABLED | Run C params (period=20, std=2.0). SMCI blacklisted |
| `mean_reversion` | ENABLED | Symbol whitelist only: NVDA, PLTR, MRVL, AMZN, INTC, AMD, META, TSLA, ALAB, NIO, MARA, IREN, CLS, CRWV, APLD, LUNR |
| `scalp_master` | ENABLED | 8-symbol whitelist: META, PLTR, ALAB, AMZN, GOOGL, MSFT, IREN, INTV. Adaptive SL/TP via `symbol_params.json` |
| `dca_accumulator` | ENABLED | Buy dips 2% below EMA50, RSI ≤ 45. NVDA blacklist pending |
| `rsi_momentum` | DISABLED | Negative expectancy confirmed |
| `ema_crossover` | DISABLED | Fails 1.5× slippage test |
| `swing_trader` | DISABLED | Insufficient sample size |
| `grid_bot` | DISABLED | Abandoned |

Strategy enabled/disabled state is persisted in the DB using the key pattern `strategy_{name}_enabled`.

### Risk Rules (from config.py — do not bypass)

- Max position: 2% of total capital
- Stop-loss: 1.5% below entry; trailing stop: 1.5% behind current price
- Take-profit: 3% above entry
- Daily loss ceiling: 15% → halts trading
- Consecutive loss halt: 10 losses
- Max open positions: 30
- Minimum signal confidence: 0.65
- Stock EOD close: 3:45 PM ET (12:45 PT) — skips `is_overnight=1` positions

### Timezone Handling (Critical)

The machine runs Pacific Time. `schedule.at()` calls in `bot_engine.py` use **PT**. Market hours checks inside scan functions use `ZoneInfo("America/New_York")` for real ET enforcement. Do not conflate the two — always note both times when modifying scheduled jobs.

### Scalp Master Adaptive SL/TP

`symbol_params.json` at project root stores per-symbol SL/TP. Recalculates after every 20 closed scalp trades per symbol. File writes are atomic and thread-safe. Minimum R:R of 2.5 is always enforced.

---

## Claude Reviewer (intelligence/claude_reviewer.py)

**Status: DISABLED** — API limit hit April 17, 2026. Resets May 1, 2026.

Before the May 1 rebuild, the architecture must change:
1. Rules engine pre-filters ~1000 candidates to ~50 before Claude sees them
2. Batch 4-5 signals per API call
3. Morning briefing fires on schedule (10 AM ET), not on first signal
4. Delta-only payloads (send only changed context)
5. JSON-only responses in auto mode (no narrative)
6. Target: 15-25 API calls/day at $0.50-2/day

Current design: conservative fallback — any failure = SKIP, never default to APPROVE. Level 2 autonomy: veto power only, cannot initiate trades.

---

## Pending Work

1. May 1: Claude reviewer tiered rebuild (see above)
2. Momentum rider mode — reorder `check_exit_conditions()` / `calculate_trailing_stop()` in `position_monitor.py`
3. DCA Accumulator: add NVDA to blacklist
4. Fix dashboard capital display (DB value vs live Alpaca sync)
5. ~~`use_container_width` deprecation warnings in `dashboard.py`~~ — migrated to web_dashboard.py
6. Coinbase non-base16 error (harmless but noisy)
7. ES trading assistant Claude.ai Project for prop firm

---

## Coding Conventions

- 4-space indentation, no tabs
- All tunable parameters belong in `config.py` — no magic numbers in module code
- `db` is a module-level singleton from `data/database.py`; import it directly
- In PowerShell `-c` commands, use semicolons to separate statements (newlines get scrambled)
- Streamlit dashboard on port 8501; any secondary Streamlit app uses `--server.port 8502`
