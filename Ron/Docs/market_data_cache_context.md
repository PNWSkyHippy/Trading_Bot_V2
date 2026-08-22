# Live market-data caching and scan-latency investigation

## Observed production problem

On Hostinger, the stock scheduler is configured to launch every 60 seconds, but completed
stock scans take roughly 87–285 seconds. The scheduler therefore repeatedly reports that a
stock scan was skipped because the previous run is still active. Stock execution itself is
working through Alpaca, but the scan cadence is slow and variable.

Production evidence from 2026-07-16:

- Stock watchlist: 118 symbols.
- Crypto watchlist: 84 symbols.
- CandleManager refresh: 588 successful plus 18 failed fetches per pass.
- Refresh duration grew from about 580 seconds before the stock session to about 887 seconds
  during it.
- The nominal refresh interval is 300 seconds. When a pass exceeds that interval, the current
  worker waits zero seconds and immediately begins another full pass.
- Individual stock scans ranged from about 87 seconds to 285 seconds.
- No enabled stock strategy requires one-minute candles. The shortest declared stock
  timeframe is five minutes, with other strategies using 15-minute, hourly, and daily bars.

## Confirmed call multiplication and cache concerns

Review these claims independently; do not simply accept them:

1. `StockScanner.get_current_price()` calls Alpaca `get_position(symbol)` for every watchlist
   symbol. Nearly all symbols are not held, so it then calls `get_latest_trade(symbol)`,
   creating up to roughly two sequential requests per symbol before strategy evaluation.
2. Alpaca SDK 3.2.0 supports `list_positions()` and `get_latest_trades(List[str])`, so scan-
   scoped batching may replace hundreds of sequential quote/position calls.
3. The scanner checks live price before determining whether any closed candle is new. It can
   therefore repeat quote traffic on four out of five one-minute launches even though the
   fastest strategy consumes closed five-minute bars.
4. CandleManager refreshes every configured symbol across fixed 5m/15m/1h timeframes
   serially and force-fetches rather than checking whether that timeframe is due.
5. Candle fetchers construct new Alpaca/CCXT clients repeatedly instead of reusing safe
   clients or sessions.
6. `CandleStore.has_data()` uses crypto-style 24-hour bars-per-day coverage calculations for
   stocks and calendar-day cutoffs. A 300-row stock cache can therefore be rejected even when
   it contains enough recent rows for a requested strategy window, causing duplicate external
   fetches despite the background refresh.
7. The existing cache freshness allowance can accept a last candle up to 48 hours old. That
   is unsuitable as the live-entry freshness contract.
8. Refresh and scanner cache-miss paths can fetch/write the same symbol/timeframe
   concurrently; SQLite WAL protects database consistency but does not deduplicate external
   requests.
9. Stock storage is namespaced as `SYMBOL/stock`, while at least one invalidation path may use
   the raw symbol.
10. Existing providers may include or exclude a forming bar. Blindly removing the final row
    can discard a valid closed candle; retaining it blindly can introduce look-ahead behavior.

## Required multi-file scope

Treat these files and all relevant callers as one system:

- `scanners/market_scanner.py`
- `core/candle_manager.py`
- `intelligence/candle_store.py`
- `bot_engine.py`
- `config.py`
- Enabled strategy timeframe/candle-limit declarations
- Position monitor, risk, reconciliation, and execution callers that consume current prices
  or candles

## Safety invariants

This is live trading infrastructure, not a generic performance refactor.

- Preserve a strict closed-bar contract. New entries must fail closed when candle age,
  timestamp parsing, quote freshness, or batch completeness is uncertain.
- Keep three data classes separate:
  1. Persistent CLOSED-candle caching for strategy analysis.
  2. Scan-scoped batch quotes for entry screening only.
  3. Broker-authoritative held-position prices for stops, trailing exits, reconciliation,
     exposure, sizing, and order decisions.
- Never allow an entry quote cache or candle close to supply open-position protection or exit
  decisions.
- A partial batch response must not promote missing or malformed symbols. NaN, infinity, zero,
  negative, stale, or unparseable prices must be rejected per symbol.
- Do not silently serve stale candles when a refresh fails.
- Preserve strategy-declared timeframes and candle limits, including daily bars.
- Do not persist evaluated-bar state unless downstream signal/order idempotency is proven.
- Avoid unbounded concurrency and rate-limit bursts.
- Add per-symbol/timeframe single-flight behavior if concurrent scanner and refresh callers
  can otherwise duplicate the same external fetch.

## Required output and debate goals

Each agent must:

1. Reproduce or reject every numbered claim with exact code evidence.
2. Quantify the current external-call count and minimum/observed scan latency.
3. Identify any additional correctness or performance defects.
4. Propose a prioritized patch sequence, separating low-risk immediate changes from deeper
   refresh/cache redesign.
5. Compare at least these options:
   - Longer stock scheduler interval only.
   - New-closed-bar gating before quotes.
   - Batch quotes and one bulk positions request per scan.
   - Direct latest-row cache loading with timeframe/session-aware freshness.
   - Per-key single-flight fetch deduplication.
   - Timeframe-due refresh scheduling.
   - Reused clients and bounded/batched Alpaca candle retrieval.
6. State failure behavior for API errors, partial results, stale data, restarts, market-session
   boundaries, weekends/holidays, and SQLite lock contention.
7. Provide deterministic equivalence, boundary, concurrency, and failure tests.

During cross-review and Stage 3, debate disagreements until a single safe implementation plan
is reached. Do not edit production code during the audit pipeline.
