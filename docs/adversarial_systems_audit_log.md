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

### 2026-06-28 - Kraken Broker Registry Rejoined Execution Routing
- Scope inspected: continued from the Kraken balance lifecycle handoff. Checked `core/broker_manager.py`, `core/trade_executor.py`, `core/risk_manager.py`, `core/kraken_executor.py`, `config.py`, `bot_engine.py` references, current `bot_state` rows in `data/trading_bot.db`, `reports/night_watch/latest_digest.json`, and recent `logs/bot.log` Kraken/broker-balance lines.
- Evidence: `config.KRAKEN_ENABLED=True` and `config.KRAKEN_PAPER_MODE=True`; `TradeExecutor._get_broker_name()` routes every crypto signal to `kraken`; recent log lines on 2026-06-28 show `core.breakout_receiver` injecting crypto with `preferred_broker=kraken` and `core.trade_executor` opening Kraken trades. Before this pass, persisted `registered_brokers` was last updated 2026-04-29 and contained only `alpaca` and `coinbase`; `broker_balance_kraken` existed separately and was updated by trade open/close bookkeeping, not by the periodic `sync_all_balances()` registry loop. Recent periodic sync evidence showed repeated Alpaca balance updates but no Kraken sync participation.
- Finding fixed: broker registration had drifted from execution routing. A fresh broker manager loaded the stale registry, so `sync_all_balances()` and capital breakdowns could omit the same Kraken broker that risk and execution use for crypto. This kept Kraken paper/live balance lifecycle dependent on side effects instead of the configured broker source of truth.
- Files touched: `core/broker_manager.py`; `docs/adversarial_systems_audit_log.md`. Runtime state touched: importing `core.broker_manager` after the patch migrated `registered_brokers` in `data/trading_bot.db` to include `kraken` because `KRAKEN_ENABLED=True`.
- Verification: `venv312\\Scripts\\python.exe -m py_compile core\\broker_manager.py` passed. A focused runtime check imported `broker_manager`, confirmed brokers `['alpaca', 'coinbase', 'kraken']`, confirmed `kraken.paper=True`, ran `broker_manager.sync_all_balances()`, and confirmed the `broker_balance_kraken` row stayed unchanged in paper mode (`2026-06-28T03:04:58.499991` before and after) while `registered_brokers` now includes Kraken.
- Next starting point: inspect live-mode Kraken safety before any future `KRAKEN_PAPER_MODE=False` switch: verify `_sync_kraken()` warning behavior with bad credentials, confirm risk rejects Kraken trades if live balance sync fails or returns zero, and decide whether live Kraken sync should mark the cached broker balance stale/untrusted after a failed fetch instead of leaving the last good value available.

### 2026-06-29 - Live Kraken Balance Failures Now Fail Closed
- Scope inspected: continued from the live-mode Kraken safety handoff. Checked `core/broker_manager.py` `_sync_kraken()`, `BrokerManager.get_broker_balance()`, `update_broker_balance()`, `sync_all_balances()`, `core/risk_manager.py` per-broker approval, `core/trade_executor.py` broker hint and post-open balance updates, `bot_engine.py` capital sync, current `bot_state` broker rows in `data/trading_bot.db`, and recent `logs/bot.log` Kraken/broker-balance/capital-sync lines.
- Evidence: current runtime config is still `KRAKEN_ENABLED=True` and `KRAKEN_PAPER_MODE=True`; recent log lines on 2026-06-29 show paper Kraken trades updating `broker_balance_kraken`, and scheduled capital sync skipping Kraken live sync in paper mode while preserving local paper balance. The live-mode path in `_sync_kraken()` would previously only log `Kraken sync error` on exception and leave the last cached `broker_balance_kraken.available` readable by `RiskManager.approve_trade()`. A zero/empty Kraken USD response would write a zero balance, but without marking why that broker cash source was untrusted.
- Finding fixed: live Kraken cash sync failures could leave stale cached available cash eligible for future risk approval after a failed live fetch. `_sync_kraken()` now marks `broker_balance_kraken` as `status="unavailable"` with `available=0.0` and `last_known_available` when live sync raises or returns zero USD/ZUSD. Successful `update_broker_balance()` clears the state back to `status="ok"`. `RiskManager.approve_trade()` now rejects any broker balance with `status="unavailable"` before sizing.
- Files touched: `core/broker_manager.py`, `core/risk_manager.py`, `docs/adversarial_systems_audit_log.md`.
- Verification: `venv312\\Scripts\\python.exe -m py_compile core\\broker_manager.py core\\risk_manager.py` passed. A focused runtime check monkeypatched `ccxt.kraken` and `config.KRAKEN_PAPER_MODE=False` against a fake in-memory DB: synthetic live outage marked Kraken unavailable and preserved `last_known_available`; `approve_trade(..., broker_name="kraken")` returned `approved=False` with `Broker balance unavailable for kraken`; synthetic zero USD/ZUSD balance marked unavailable; synthetic good ZUSD balance restored `status="ok"` and `available=100.0`. The real SQLite state was inspected but not mutated by the synthetic test.
- Next starting point: audit the high-frequency Kraken stop-order ratchet path. Recent logs show repeated cancel/place cycles for the same paper stop roughly every 30 seconds; inspect `core/position_monitor.py` and `core/kraken_executor.py` for duplicate stop replacement, idempotency, and live-mode rate-limit/order-state safety before any `KRAKEN_PAPER_MODE=False` switch.
