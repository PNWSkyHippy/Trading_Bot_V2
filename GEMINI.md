# GEMINI.md

This file provides foundational mandates, project architecture, building/running instructions, and development conventions for the Gemini CLI and developer agents working in the `trading-bot-v2` workspace.

---

## 1. Project Overview

This workspace is a hybrid environment containing two major, highly integrated components:
1. **Autonomous Day Trading Bot (Trading Bot v2):** A Python-based algorithmic trading system that scans markets, evaluates strategies, scores signals with Machine Learning (Random Forest), enforces strict risk rules, and executes orders across multiple brokers (Alpaca, ccxt/Kraken, IBKR).
2. **Trading Skills Framework (`claud-skills`):** An extensive suite of specialized AI agent skills. Each skill packages domain-specific prompts (`SKILL.md`), references, scripts, and assets to assist with quantitative and qualitative trading tasks (e.g., sector rotation analysis, backtesting, technical charting, macro regime detection).

### 1.1 Core Technologies
- **Python Version:** Python 3.12 (Trading Bot) & Python 3.9+ (Skills Framework)
- **Database:** SQLite (`data/trading_bot.db`)
- **Key Broker APIs:** Alpaca Trade API, CCXT (Kraken/Coinbase), `ib-insync` (IBKR)
- **Technical Analysis & Data:** `pandas-ta`, `numpy`, `yfinance`
- **Dashboard & API:** Custom Threading HTTP Server serving HTML-based frontend (port `8125`), Streamlit (fallback, port `8501`), FastAPI/Uvicorn (port `8000`)
- **AI/ML Integration:** `scikit-learn` (Random Forest scorer), `anthropic` (Claude/Gemini integration for trade reviews, currently disabled/configured for morning briefings)

---

## 2. Directory Layout & Architecture

### 2.1 Workspace Structure
```
C:\Users\Linda\Trading_Bot_V2\
├── config.py                  # Single source of truth for bot parameters & Fernet decryption
├── bot_engine.py              # Main scheduler & entry point of the trading bot
├── web_dashboard.py           # Web dashboard engine serving port 8125
├── start_bot.bat              # Batch script to activate venv & start bot_engine.py
├── StartWebDashboard.bat      # Batch script to launch HTML dashboard bridge
├── core/                      # Key trading bot components
│   ├── risk_manager.py        # Central safety gate (position sizing, SL/TP, circuit breakers)
│   ├── position_monitor.py    # Trailing stops, profit-taking, and active position lifecycle
│   ├── broker_manager.py      # Multi-broker routing abstraction
│   ├── settlement_tracker.py  # Cash settlement and PDT avoidance
│   └── strategy_registry.py   # Registry of available strategies
├── strategies/                # Bot strategy modules extending BaseStrategy
├── intelligence/              # Machine learning (ml_scorer.py) and chat interfaces
├── claud-skills/              # Specialized agent skills codebase
│   ├── skills/                # 50+ modular skills (e.g., sector-analyst, macro-regime-detector)
│   │   └── <skill-name>/      # Standardized structure: SKILL.md, references/, scripts/, assets/
│   ├── docs/                  # Bilingual (EN/JA) catalog and site documentation
│   └── scripts/               # Quality control, testing, and generation scripts
└── venv312/                   # Python virtual environment (3.12)
```

### 2.2 Bot Data Flow Architecture
```
bot_engine.py (Scheduler)
   └─→ scanners/market_scanner.py (Scan & Fetch Market Data)
        └─→ strategies/strategy_engine.py (Run all enabled strategies & deduplicate)
             └─→ intelligence/claude_reviewer.py (Codex automated signal review - disabled/morning briefing)
                  └─→ core/risk_manager.py (Enforce strict position limits & safety rules)
                       └─→ core/trade_executor.py (Order routing to Alpaca / Kraken / IBKR)
                            └─→ data/database.py (Persist state to data/trading_bot.db)
```

---

## 3. Building, Running, and Testing

Always activate the local virtual environment before running any commands or utilities.

### 3.1 Activating the Environment (PowerShell)
```powershell
# Semicolon-based one-liner for PowerShell
C:\Users\Linda\Trading_Bot_V2\venv312\Scripts\activate; python bot_engine.py
```

### 3.2 Running the Bot & Dashboard
*   **Main Bot Engine:**
    ```bash
    python bot_engine.py            # Normal mode
    python bot_engine.py --verbose  # Verbose debug logging (Warning: log files grow rapidly!)
    ```
*   **Launch via Script:** Run `start_bot.bat` to launch the bot engine with auto-restart safeguards in case of crashes.
*   **HTML Web Dashboard:** Run `StartWebDashboard.bat` or `python web_dashboard.py` to start the dashboard server. View it locally at `http://localhost:8125`.

### 3.3 Backtesting Strategies
*   **All Strategies (e.g., 2 years / 730 days of data):**
    ```bash
    python intelligence/backtester.py --all --days 730
    ```
*   **Single Stock/Ticker:**
    ```bash
    python intelligence/backtester.py --symbol AAPL --days 730
    ```
*   **Adversarial Stress Testing:**
    ```bash
    python full_strategy_stress_test.py
    ```

### 3.4 Verification & Testing
The workspace contains extensive unit and integration tests across both the core bot and the skills framework.

*   **Running Core Bot / Utilities Tests:**
    Tests are located inside the `Scripts/` folder and root. Run via `pytest`:
    ```bash
    pytest Scripts/test_database_trade_identity.py
    pytest Scripts/test_stock_calendar_authority.py
    ```
*   **Running Skills Framework Tests:**
    Run inside the `claud-skills` directory:
    ```bash
    cd claud-skills
    pytest
    ```
    To run all skills tests using the pre-push test harness:
    ```bash
    bash claud-skills/scripts/run_all_tests.sh
    ```

---

## 4. Development & Coding Conventions

To maintain architectural integrity and prevent regressions, you must adhere to the following standards:

### 4.1 Global Coding Standards
- **Python Style:** 4-space indentation, no tabs. Strictly enforce line-length limit of `132` (bot engine) or `100` (skills codebase).
- **No Magic Numbers:** All tunable parameters and settings must live in `config.py`. Never inline settings inside modules.
- **Database Access:** `db` is a module-level singleton exported by `data/database.py`. Always import and use it directly instead of creating new connection managers.
- **Timezone Safety:** The Windows host machine operates on **Pacific Time (PT)**.
  - Schedulers (`schedule.at()` in `bot_engine.py`) use **Pacific Time (PT)**.
  - Market hour checks use `ZoneInfo("America/New_York")` to enforce **Eastern Time (ET)**.
  - Always verify both timezones when modifying scheduled tasks or calendar authority rules.

### 4.2 Security & Credential Protection
- **Fernet Decryption:** All sensitive API keys in `.env` are Fernet-encrypted. `config.py` handles runtime decryption automatically via helper functions.
- **OS Credential Keyring:** Fernet decryption keys can be stored securely in the OS Keyring (`trading_bot_v2`, `fernet_key`).
- **Committing:** Never commit `.env` or plain-text secrets. Use `Scripts/setup_encryption.py` to encrypt new keys.

### 4.3 Test-Driven Development (TDD)
- **TDD Workflow:** Always write or update test suites before implementing bug fixes or new features. Confirm test failure, implement the minimal solution to pass, and refactor while keeping tests green.
- **Test Integrity:** If modifying stateful parts of the trading engine, verify behavior against existing integration test scripts inside `Scripts/` (such as `test_lifecycle_correctness_patch.py`).

### 4.4 Skills Framework Conventions (`claud-skills/`)
Each skill must strictly match the standardized structural contract:
1.  **Directory Location:** Must reside in `claud-skills/skills/<skill-name>/`.
2.  **SKILL.md Contract:** Must contain YAML frontmatter with `name` (matching directory name) and `description` (defining triggers).
3.  **Documentation Completeness:** Creating or editing a skill requires generating documentation in both English and Japanese. Run:
    ```bash
    python claud-skills/scripts/generate_skill_docs.py --skill <skill-name>
    ```
    Commit checks are enforced via local pre-commit hooks (`docs-completeness` and `skill-frontmatter`).
4.  **Ruff Linting:** Linting is enforced via `ruff` checks before every push. Avoid silencing warnings; resolve them explicitly.
