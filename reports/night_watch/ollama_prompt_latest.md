You are a local night-watch analyst for Linda's trading bot.

You do not trade. You do not give financial advice. You summarize operational,
logging, monitoring, and software reliability risks from a deterministic digest.

Rules:
- Treat the JSON digest as source of truth for counts.
- Do not invent trades, prices, files, or code changes.
- Separate operational emergencies from ordinary strategy losses.
- Prefer concrete next checks and patch targets.
- If a code patch is needed, describe the likely files/functions, but do not
  write a full diff unless the digest clearly proves the bug.
- Keep the report compact enough to paste into Codex/Claude.


Analyze this deterministic night-watch digest and produce:

1. Executive status: OK / WATCH / ACTION NEEDED
2. Highest priority issues, ordered by operational risk
3. Strategy-performance warnings that may justify disabling or investigating
4. Data-pipeline or logging anomalies that look like bugs
5. Exact next command/check for Linda
6. Small prompt to paste into Codex/Claude if a patch investigation is needed

Digest JSON:
```json
{
  "generated_at": "2026-06-18T19:05:59-07:00",
  "tail_bytes": 5000000,
  "findings": [
    {
      "severity": "HIGH",
      "title": "Errors or exceptions in recent logs",
      "detail": "2585 recent critical/error/exception lines found.",
      "evidence": [
        "2026-06-18 06:37:49 [ERROR] yfinance: $OCEAN-USD: possibly delisted; no price data found  (period=14d)",
        "2026-06-18 06:37:49 [ERROR] yfinance:",
        "2026-06-18 06:37:49 [ERROR] yfinance: ['OCEAN-USD']: possibly delisted; no price data found  (period=14d)",
        "2026-06-18 06:37:49 [ERROR] yfinance: $AGIX-USD: possibly delisted; no price data found  (period=3d)",
        "2026-06-18 06:37:49 [ERROR] yfinance:"
      ]
    },
    {
      "severity": "MEDIUM",
      "title": "Timeouts or connection problems",
      "detail": "658 recent timeout/connection lines found.",
      "evidence": [
        "2026-06-18 06:37:49 [WARNING] core.candle_manager: [CandleManager] OCEAN/USD/1h unreachable on all sources \u2014 logged",
        "2026-06-18 06:37:49 [WARNING] core.candle_manager: [CandleManager] AGIX/USD/5m unreachable on all sources \u2014 logged",
        "2026-06-18 06:37:49 [WARNING] core.candle_manager: [CandleManager] AGIX/USD/15m unreachable on all sources \u2014 logged",
        "2026-06-18 06:37:49 [WARNING] core.candle_manager: [CandleManager] AGIX/USD/1h unreachable on all sources \u2014 logged",
        "2026-06-18 06:37:49 [WARNING] core.candle_manager: [CandleManager] NMR/USD/5m unreachable on all sources \u2014 logged"
      ]
    },
    {
      "severity": "MEDIUM",
      "title": "Missing or zero volume baseline events",
      "detail": "1721 recent zero-volume/baseline events found.",
      "evidence": [
        "2026-06-18 06:40:58 [INFO] core.breakout_receiver: [BREAKOUT RECV] ES/USD LONG esc=2 move=+8.12% age=2s vol=0.00x broker=kraken source_broker=kraken stop=0.02313 bars_since=4",
        "2026-06-18 06:41:02 [INFO] core.breakout_receiver: [BREAKOUT RECV] PUFFER/USD LONG esc=1 move=+2.54% age=2s vol=0.00x broker=kraken source_broker=kraken stop=0.018153 bars_since=4",
        "2026-06-18 06:41:03 [WARNING] core.breakout_receiver:   [HARD] [FAIL] No volume baseline available (0.00x) \u2014 cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation.",
        "2026-06-18 06:41:03 [INFO] core.breakout_receiver: [BREAKOUT RECV] CHECKLIST REJECTED ES/USD \u2014 Hard check failed: No volume baseline available (0.00x) \u2014 cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation.",
        "2026-06-18 06:41:06 [WARNING] core.breakout_receiver:   [HARD] [FAIL] No volume baseline available (0.00x) \u2014 cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation."
      ]
    },
    {
      "severity": "MEDIUM",
      "title": "breakout_scanner is losing today",
      "detail": "19 trades, win_rate=36.8%, pnl=$-195.83, pf=0.527"
    }
  ],
  "log_counts": {
    "critical_error": 2585,
    "timeout_connection": 658,
    "position_monitor": 1552,
    "zero_volume_baseline": 1721,
    "checklist_rejected": 1999,
    "disabled_activity": 1442,
    "executor_rejected": 207,
    "trade_open": 165,
    "trade_closed": 136,
    "sender_rejected": 272,
    "manual_command": 38
  },
  "rejection_reasons": {
    "missing_volume_baseline": 479,
    "other": 736,
    "volume_below_minimum": 316,
    "wick_rejection": 220,
    "price_reversed_or_drift": 243,
    "min_price": 5,
    "sender_volume_below_minimum": 7,
    "sender_wick_rejection": 13,
    "sender_missing_volume_baseline": 52,
    "sender_other": 164,
    "sender_bad_quote_currency": 8,
    "sender_price_reversed_or_drift": 28
  },
  "examples": {
    "critical_error": [
      "2026-06-18 06:37:49 [ERROR] yfinance: $OCEAN-USD: possibly delisted; no price data found  (period=14d)",
      "2026-06-18 06:37:49 [ERROR
...TRUNCATED...
```
