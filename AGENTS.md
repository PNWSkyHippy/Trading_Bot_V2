# AGENTS.md

** If running inside project DecentClone, then use DecentClone/AgentDecent.md as authority not this file **

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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
| `intelligence/claude_reviewer.py` | Codex autonomous signal reviewer — **currently disabled** |
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

## Codex Reviewer (intelligence/claude_reviewer.py)

**Status: DISABLED** — API limit hit April 17, 2026. Resets May 1, 2026.

Before the May 1 rebuild, the architecture must change:
1. Rules engine pre-filters ~1000 candidates to ~50 before Codex sees them
2. Batch 4-5 signals per API call
3. Morning briefing fires on schedule (10 AM ET), not on first signal
4. Delta-only payloads (send only changed context)
5. JSON-only responses in auto mode (no narrative)
6. Target: 15-25 API calls/day at $0.50-2/day

Current design: conservative fallback — any failure = SKIP, never default to APPROVE. Level 2 autonomy: veto power only, cannot initiate trades.

---

## Pending Work

1. Deevlop main game logic for AI, Goals, graphics
1a. high priority develop opening scren graphics to be displayed imediately to over up this horrible 5 minute delay o tunnel graphs loading
    Lets make  a game logo openig vide montager welcome to Astral Drifdt showing cutaway sceense of action in tunnels, in bonus leve,s im space levels with background musi cgoing
2. Build out 10 levels of the galaga bonus leve, 10 of the pacman bonus level and 10 of the defender bonus level
3. Build out 30 levels of tunnel maps 
4. Build out 30 levels of open space (Space station , ugrades, repair bays, space runner guild taks boards
4a. Develop cino-graphci high res high detail deep space (nebluas , galaxies, black holes, planets, asteroid fields, as predone  images made to be sequenced into mp4 format for
    precorded sequences and simulaed 60fps ray tracing, ie load a scene with wrap around texuture and ray trace every image view in full 360.shown on  vifewfporf format depending where player looks
4b. Develop repair station at space station, repair hull, upgrade rockets, emps, oil slicks, etc quantity and strength based on player level. Devise ship upgrades for cash hull strength laser strength, shield regen speed, ship  accelleration and max speed upgradse.
4c. along these lines Develop strategy for exp VS level gaining  and for cash generation in all tunnel , bonus leve, space level endeavors rewards for accompishments, loot sold at space station collect do missons, coin picked up for loot stashess in game---
4d. Deveop high res custom image tiles for al tunnel and bonus level game walls fllors ceilings. Where possible 
   and appropriate develop still imaged ray trace sequences through the image seuqnces simlulating movement and 
   display as a roll of tiles in game (Tunnels). I want to totally eliminate the problem of gaps where one
   image  begins and another ends by premaking an entire tunnels maps worth of imagry into one big long image sequnece that can be laid down anf ignoe all tunnel segment bounaries all together.

5. Develop the etire  start to finish gameplan,  loading screen, charcter generation, starting map, opening splash screen, beginning game montage video sequence describing
  game play and goals and how to access help ad move about the game. perhaps a tutorial level
6. Revamp and createcustom sound effects utilizing dosplar effect sound technique for all bullet engine,s lasers explosions rocket emisons scrapes bumps, button activate, portal usages
6a. Also develop overal game themr bakground music to be choosable from 1-5 choices or turnred off

## Coding Conventions
- use skill /code-check on every code chage made, no shortcuts, adhere to the skill
- 4-space indentation, no tab
- In PowerShell `-c` commands, use semicolons to separate statements (newlines get scrambled)
- Streamlit dashboard on port 8501; any secondary Streamlit app uses `--server.port 8502`
