# Durable Event Identity Patch — Status (2026-07-17)

Follow-up to `CLAUDE_IMPLEMENTATION_HANDOFF_2026-07-17.md`. All 8 tasks complete, tested, committed, and pushed to `origin/main` in `integration_repo`.

## Deployed

- Commit `a6018af20` (on top of `7c3fff73d`), pushed to `origin/main`.
- Scope: commit + push only. The live running bot process was **not** restarted or reloaded.
- 9/9 new deterministic durability tests pass (`Scripts/test_breakout_event_durability.py`), plus all pre-existing suites remain green (55 + 8 + 30 tests).

## What it does

- Every breakout signal now carries a required `event_id`.
- Receiver atomically claims each `event_id` (INSERT ... ON CONFLICT DO NOTHING) before touching the executor. Replays of a non-terminal event never re-trigger a broker call; replays of a terminal event return the stored response verbatim; a payload-hash mismatch on the same `event_id` is rejected as a conflict.
- `client_order_id` / Kraken `userref` are derived deterministically from `event_id`, so orders can be found by broker-native identity after a crash or restart.
- Broker call results are classified tri-state (`pre_submission_rejected` → `submission_unknown` → `accepted` / `rejected_no_exposure`) so an ambiguous/unknown broker response is never treated as proof of no exposure — this was the core bug the patch closes (previously a `None` result could look identical to "definitely didn't submit").
- `reconcile_unresolved_breakout_events()` can look up Alpaca/IBKR/Kraken by that deterministic identity to resolve anything left in `SUBMISSION_UNKNOWN` after a crash.

## Known residual gaps (not dealbreakers — pre-existing, flagged for future work)

1. **Kraken reconciliation is best-effort.** `find_order_by_userref` is a bounded client-side scan — ccxt has no server-side userref filter for this exchange. Not authoritative.
2. **IBKR reconciliation is connection-scoped.** `find_order_by_ref` only sees orders known to the *current* persistent connection. A dropped/restarted connection loses visibility into prior orders.
3. **Reconciliation is not auto-wired.** `reconcile_unresolved_breakout_events()` exists and is tested but isn't called automatically on bot startup — needs an explicit hook if you want it to run without manual invocation.
4. **No `trades` row reconstruction.** If reconciliation finds a bare broker order with no matching local `trades` row, it deliberately does not synthesize one. This is a safety choice, not a bug.

## Explicitly deferred (do not start without a new go-ahead)

- Market-data Patches B–E
- Backtester parity plan
- Shared-lifecycle / Bollinger / SFR / BMR / VBM patches (gated on backtester parity)
- Restoring retries on the sender — it currently makes exactly one POST attempt per delivery. Do not re-enable retries before durable idempotency reaches the broker end-to-end (this patch is a prerequisite, not the full guarantee, given gaps #1–#3 above).
