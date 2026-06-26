# Adversarial Systems Audit Log

Purpose: spend small daily passes finding cross-module failures that ordinary code review misses.

Focus areas:
- Duplicated sources of truth: config, DB state, env, dashboard controls, scripts.
- Shared mutable state across scheduler threads, scanners, receiver, risk, executor, and position monitor.
- Silent failures: `except Exception: pass`, debug-only errors, stale state, missing fields, network/API timeouts.
- Gates that should run but do not: market hours, reviewer mode, strategy enabled flags, broker availability, risk, settlement, cooldowns.
- Missing/dirty payload fields between scanners, senders, receivers, strategies, and execution.
- Recovery behavior after reboot, bad API key, slow network, stale DB value, locked DB, unavailable broker, and partial order failure.

## Case Studies Already Found

### 2026-06-24 - Stock Scan Overlap
- Symptom: stock scans showed start events every 60s while old scans were still active for 4000+ seconds.
- Root cause: `bot_engine._run_singleton_job()` had a stock-scan exception that allowed overlapping stock scans.
- Fix: restored singleton skip behavior for all jobs.
- Files: `bot_engine.py`

### 2026-06-24 - Alpaca Cash Split-Brain
- Symptom: Alpaca dashboard showed about $99k cash, but stock trades were rejected with `No available cash on alpaca: $0.00`.
- Root cause: `core.broker_manager._sync_alpaca()` used stale `registered_brokers` credentials from DB instead of current encrypted/config credentials. Sync failed silently, leaving stale `broker_balance_alpaca` with impossible invested value.
- Fix: Alpaca sync now uses current `config.py` credentials and logs sync failures as warnings. Sync repaired state to balance/available about $99,154.91 and invested $0.
- Files: `core/broker_manager.py`

## Current Queue

1. Audit all broker/key/config source-of-truth paths.
2. Audit risk-manager broker cash checks against stale or impossible broker states.
3. Audit scheduler singleton handling and long-running jobs.
4. Audit stock scan pipeline from market-hours gate to strategy signals to execution.
5. Audit Claude/Haiku reviewer modes and any strict/advisory mismatch.
6. Audit scanner enabled flags and DB/script naming mismatches.
7. Audit payload fields from breakout/funding/gap scanners into receiver and trade records.

### 2026-06-26 - Broker Cash Failure Must Fail Closed
- Scope inspected: broker/config/DB state paths across `core/broker_manager.py`, `core/risk_manager.py`, `core/trade_executor.py`, `bot_engine.py`, the live SQLite state, and the latest bot log.
- Evidence: the persisted `registered_brokers` state contains only `alpaca` and `coinbase`, while `TradeExecutor._get_broker_name()` routes every crypto signal to `kraken` when `KRAKEN_ENABLED=True`. `sync_all_balances()` only iterates registered brokers, so the persisted Kraken balance ($95,243.80; available $74,669.75) is not periodically refreshed. Its last update was 2026-06-25 12:48:28, versus Alpaca's successful startup sync at 2026-06-25 05:53:37. The prior Alpaca stale-cash symptom is also present in the 2026-06-22 log digest.
- Finding fixed: `RiskManager.approve_trade()` caught every per-broker cash-check exception and continued with theoretical capital. A locked/corrupt DB or state-read failure could therefore approve an order without a trustworthy broker cash limit.
- Files touched: `core/risk_manager.py`.
- Verification: `venv312\\Scripts\\python.exe -m py_compile core\\risk_manager.py` passed. A focused runtime check replaced `get_broker_balance()` with a raising function; `approve_trade(..., broker_name="alpaca")` returned `approved=False` with `Broker balance unavailable for alpaca`.
- Next starting point: trace the Kraken balance lifecycle end-to-end. Decide whether the registered-broker default/migration should include Kraken and whether its sync must use current `config` credentials (as Alpaca now does), while preserving intentional broker disablement and paper-mode behavior. Then verify no execution path can use stale broker cash after a sync failure.
