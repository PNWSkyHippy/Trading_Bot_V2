## graphify

For any question about this repo's architecture, structure, components, or how to add/modify/find
code, your first action should be `graphify query "<question>"` when `graphify-out/graph.json`
exists. Use `graphify path "<A>" "<B>"` for relationship questions and `graphify explain "<concept>"`
for focused-concept questions. These return a scoped subgraph, usually much smaller than the full
report or raw grep output.

Triggers: "how do I…", "where is…", "what does … do", "add/modify a <component>",
"explain the architecture", or anything that depends on how files or classes relate.

If `graphify-out/wiki/index.md` exists, use it for broad navigation. Read `graphify-out/GRAPH_REPORT.md`
only for broad architecture review or when query/path/explain do not surface enough context. Only read
source files when (a) modifying/debugging specific code, (b) the graph lacks the needed detail, or
(c) the graph is missing or stale.

Type `/graphify` in Copilot Chat to build or update the graph.

---

## Quick Reference — Pending Work

**Trading Bot Medium-Term Tasks** (from AGENTS.md)

- [ ] **May 1 rebuild**: Codex reviewer tiered architecture (pre-filter to 50, batch 4-5 signals, delta payloads) — target 15-25 API calls/day at $0.50-2/day
- [ ] **Momentum rider**: Reorder `check_exit_conditions()` → `calculate_trailing_stop()` in `core/position_monitor.py` to ride TP extensions
- [ ] **DCA Accumulator**: Add NVDA to blacklist
- [ ] **Dashboard capital**: Sync DB value vs live Alpaca in web_dashboard.py
- [ ] **Coinbase error**: Suppress non-base16 warnings (harmless but noisy)
- [ ] **ES assistant**: Codex.ai Project for prop firm trading

---

## Key Modules (see AGENTS.md for full details)

| Module | Purpose | Config |
|--------|---------|--------|
| `config.py` | Single source of truth for all parameters — change settings here, not inline | All tunable params |
| `core/risk_manager.py` | Every trade passes through. Enforces position sizing, stop-loss, circuit breakers — NEVER bypass | Max 2% position, 1.5% SL/TP |
| `core/position_monitor.py` | Runs every 30s; manages trailing stops. Known issue: exit checks before trailing calc | Fix pending |
| `strategies/strategy_engine.py` | Runs all strategies, deduplicates signals, auto-disables underperformers | 8 strategies total |
| `data/database.py` | SQLite wrapper — singleton `db` object imported everywhere | data/trading_bot.db |

---

## Environment & Running

- **Python 3.12** via `venv312` — always activate before running anything
- **Timezone**: Pacific Time (Spokane, WA) for `schedule.at()`, but market hours use ET via `ZoneInfo("America/New_York")`
- **Start bot**: `python bot_engine.py` or `start_bot.bat` (starts both engine + web dashboard)
- **Dashboard**: http://localhost:8125 (web_dashboard.py, not Streamlit)
