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
