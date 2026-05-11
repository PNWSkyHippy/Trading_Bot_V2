
```BREAKOUT_RECEIVER_PATCH_BRIEF.md
Please patch breakout scanner + receiver around the actual current bug and data contract issues.

Goals:
1. Fix malformed payload / Signal-construction failures
2. Move slow thesis-building logic into the scanner
3. Keep receiver fast and execution-focused
4. Preserve alerting even when auto-trade eligibility fails

Required changes:

- Add a strict required-field validator at the top of breakout_receiver.receive_signal()
- Distinguish 3 failure classes in logs and API response:
  1) invalid payload
  2) checklist rejection
  3) injection/runtime exception

- Do NOT pass `broker=` into `scanners.market_scanner.Signal(...)` unless the Signal dataclass is explicitly extended to support it.
- If broker preference is still wanted, place it in:
  `signal.indicators["preferred_broker"]`

- Move these computations to the scanner side and include them in payload:
  - breakout_level
  - bars_since_breakout
  - distance_from_breakout_pct
  - structural_stop_price
  - volume_spike
  - optional RSI / trend / market context

- Receiver should remain responsible only for:
  - required field validation
  - freshness / TTL
  - no open position
  - cooldown
  - halted-state check
  - current price drift sanity
  - structural stop sanity
  - risk manager handoff
  - executor handoff

- Add structured logging for every inbound signal:
  symbol, tier, timestamp, signal_age_sec, bars_since_breakout,
  distance_from_breakout_pct, volume_spike, current_price,
  structural_stop_price, accepted/rejected, reject_reason

- Preserve alert-only behavior:
  A malformed or under-specified payload should still be allowed to appear in logs/UI,
  but should be marked `execution_eligible=False` and not auto-traded.

Please implement against the actual code, not assumptions:
- missing RSI currently does NOT reject
- missing SMA200 currently does NOT reject
- missing market context currently does NOT reject
- missing candle OHLC currently does NOT reject
- missing volume_spike DOES reject
- passing unsupported `broker=` to Signal(...) likely throws injection-time exception