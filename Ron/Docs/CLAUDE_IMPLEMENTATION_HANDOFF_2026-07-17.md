# Claude implementation handoff — 2026-07-17

Ron wants the existing approved work implemented incrementally. Do not start another broad audit and do not revisit already-finished patches unless a deterministic regression proves a problem.

## Environment and authority

- Work only in: `C:\Users\Linda\Trading_Bot_V2\Ron\integration_repo`
- WSL path: `/mnt/c/Users/Linda/Trading_Bot_V2/Ron/integration_repo`
- Branch: `main` only. Do not create a feature branch.
- Begin with `git fetch origin && git status --short --branch && git rev-parse --short HEAD`.
- Expected starting HEAD: `7c3fff73d` or a newer `origin/main` containing it.
- The original `C:\Users\Linda\Trading_Bot_V2` checkout is dirty. Do not stage, restore, delete, or overwrite anything there.
- Use Windows Python 3.12 at `C:\Users\Linda\Trading_Bot_V2\venv312\Scripts\python.exe` for final verification.
- Everything automated is paper-only. Never weaken safety gates on that basis.
- Do not stage, commit, or push until Ron reviews your final diff and test evidence.

## Already deployed — preserve exactly

- Patch A market-data foundation through `c804c33b0`.
- BreakoutScanner fixes: `576648015`, `2f685f7e2`.
- Breakout sender containment: `522061c07`.
- Receiver request-local drift: `7c3fff73d`.
- Sender deliberately performs one POST attempt. Timeout means delivery outcome unknown. Do not restore retries before durable idempotency reaches the broker.

## Your task: receiver durable event identity, atomic claim, and reconciliation

Implement this as one carefully bounded coordinated patch across the API, database, receiver, trade execution, and broker adapters. A database-only dedup table is insufficient if broker submission can succeed before the process records the result.

### Required behavior

1. Add a required stable `event_id` to sender events. It must be minted once per semantic source event and reused for every delivery attempt. Different escalation levels are distinct child events.
2. Retain and validate `event_id` in `api_server.BreakoutSignalPayload`. Move the route's minimum-escalation rejection behind the receiver's durable claim so the rejection becomes replayable.
3. Add a fresh-schema and idempotent-migration table similar to:

```sql
CREATE TABLE breakout_event_execution (
    event_id            TEXT PRIMARY KEY,
    payload_sha256      TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    direction           TEXT NOT NULL,
    signal_source       TEXT NOT NULL,
    state               TEXT NOT NULL,
    client_order_id     TEXT NOT NULL UNIQUE,
    broker_order_id     TEXT,
    trade_id            TEXT,
    response_json       TEXT,
    last_error          TEXT,
    created_at_utc      TEXT NOT NULL,
    updated_at_utc      TEXT NOT NULL,
    terminal_at_utc     TEXT
);
```

Use states at least `CLAIMED`, `SUBMITTING`, `ACCEPTED`, `PRE_SUBMISSION_REJECTED`, and `SUBMISSION_UNKNOWN`. Never age-delete an unresolved identity.

4. Add atomic DB methods:
   - `claim_breakout_event(...)`: `INSERT ... ON CONFLICT(event_id) DO NOTHING`, then inspect the existing row in the same transaction. Same ID/same hash returns replay; same ID/different hash returns permanent conflict.
   - `mark_breakout_event_submitting(...)`: conditional `CLAIMED -> SUBMITTING` update committed before any broker call.
   - `finish_breakout_event(...)`: conditional state transition and stored response written before returning HTTP.
   - `get_breakout_event(...)`: recovery/status lookup.
5. Canonicalize and strictly validate an immutable payload before hashing. Reject NaN/Infinity. Do not hash receiver scratch fields or mutable transport-only noise.
6. The receiver must claim before checklist/policy execution. A completed duplicate returns the stored response without rerunning checklist or executor. A `CLAIMED`, `SUBMITTING`, or `SUBMISSION_UNKNOWN` replay must fail closed and must not submit again.
7. Add `event_id` to `trades` and a partial unique index where non-null. Carry it through `open_trade` and reconciliation.
8. Derive a deterministic `client_order_id` from `event_id`. Carry it through `TradeExecutor` and into broker-native identity:
   - Alpaca `client_order_id`
   - IBKR `orderRef`
   - Kraken supported client/user reference (`userref` or the adapter's authoritative equivalent)
9. Broker results must distinguish proven pre-submission rejection, accepted/submitted, and submission unknown. Never treat a generic `None` as proof that no exposure exists.
10. On restart or replay of `SUBMITTING`/`SUBMISSION_UNKNOWN`, query the broker by deterministic client identity. Attach the existing broker order/trade when found; otherwise remain blocked/unknown. Never resubmit because the local trades row is missing.

### Deterministic tests required

- Twenty simultaneous calls through at least two receiver/Database instances produce one claim, one executor call, one broker order, and one trade.
- Same event/same payload replays the identical stored response.
- Same event/different payload returns conflict and never calls executor.
- Process restart replay remains idempotent.
- Broker accepts, response times out, process restarts: reconciliation finds one order and no second order is submitted.
- Crash/failpoints after claim, after `SUBMITTING`, after broker acceptance, and before/after trade-row persistence.
- `SUBMISSION_UNKNOWN` never automatically resubmits.
- `trades.event_id` uniqueness is proven.
- Existing scanner, sender, receiver, Kraken fill-resolution, broker-routing, and database identity suites remain green.
- Tests use disposable DBs/fake brokers and must not connect to IBKR or modify the live DB.

## Stop condition

Stop after presenting:

- Exact changed-file list and full diff/stat.
- Schema and state-transition explanation.
- Test commands and complete pass counts.
- Any unresolved broker limitation, especially Kraken client-reference lookup.
- `git status --short` proving nothing unrelated was touched.

Do not stage, commit, push, enable retries, or begin market-data Patch B without Ron's approval.

## Queue after this patch

1. Market-data Patches B-E, one at a time with paper observation gaps.
2. Backtester parity plan from `reports/agent_pipeline/20260717-085541/final_unified_report.md`.
3. Shared lifecycle and Bollinger/SFR/BMR/VBM patches, followed by matrix tests only after backtester parity is proven.
