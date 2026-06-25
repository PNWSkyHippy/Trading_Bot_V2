# Night Watch Digest

- Generated: 2026-06-22T20:42:31-07:00
- Tail bytes per log: 5,000,000

## Findings
- [HIGH] Errors or exceptions in recent logs: 412 recent critical/error/exception lines found.
  - evidence: `2026-06-22 04:52:54 [ERROR] yfinance: $CLSK: possibly delisted; no price data found  (period=3d)`
  - evidence: `2026-06-22 04:52:54 [ERROR] yfinance:`
  - evidence: `2026-06-22 04:52:54 [ERROR] yfinance: ['CLSK']: possibly delisted; no price data found  (period=3d)`
- [MEDIUM] Timeouts or connection problems: 151 recent timeout/connection lines found.
  - evidence: `2026-06-22 04:55:04 [WARNING] core.candle_manager: [CandleManager] KKR/1h unreachable on all sources — logged`
  - evidence: `2026-06-22 17:49:43 [WARNING] core.candle_manager: [CandleManager] RUNE/USD/15m unreachable on all sources — logged`
  - evidence: `2026-06-22 17:49:53 [WARNING] core.candle_manager: [CandleManager] BAL/USD/15m unreachable on all sources — logged`
- [MEDIUM] Missing or zero volume baseline events: 180 recent zero-volume/baseline events found.
  - evidence: `2026-06-22 07:23:47 [WARNING] core.breakout_receiver:   [HARD] [FAIL] No volume baseline available (1.00x, source=unknown, current_volume=None, avg_volume=None) — cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation.`
  - evidence: `2026-06-22 07:23:47 [INFO] core.breakout_receiver: [BREAKOUT RECV] CHECKLIST REJECTED ME/USD — Hard check failed: No volume baseline available (1.00x, source=unknown, current_volume=None, avg_volume=None) — cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation.`
  - evidence: `2026-06-22 07:23:47 [INFO] scanners.market_scanner: [REENTRY] ME/USD: REJECTED — Hard check failed: No volume baseline available (1.00x, source=unknown, current_volume=None, avg_volume=None) — cannot confirm breakout volume. Rejecting to prevent thin-float / micro-cap entries with no liquidity confirmation.`
- [MEDIUM] No stock trades recorded today: DB shows zero stock trades opened/closed today. Check market-hours gate, scanner, reviewer, and broker path.

## Log Counts
- checklist_rejected: 1873
- critical_error: 412
- disabled_activity: 2580
- executor_rejected: 191
- manual_command: 38
- position_monitor: 2298
- sender_rejected: 249
- timeout_connection: 151
- trade_closed: 150
- trade_open: 182
- zero_volume_baseline: 180

## Rejection Reasons
- other: 1055
- volume_below_minimum: 317
- wick_rejection: 245
- price_reversed_or_drift: 205
- sender_other: 191
- missing_volume_baseline: 48
- sender_price_reversed_or_drift: 16
- sender_wick_rejection: 15
- sender_volume_below_minimum: 14
- sender_bad_quote_currency: 9
- sender_missing_volume_baseline: 4
- min_price: 3

## Strategy Stats Today
- breakout_scanner: trades=32 wins=11 losses=21 wr=34.4% pnl=$17.14 pf=1.03

## Open Trades
- Count: 0

## Files
- logs\bot.log size=128,380,782 last_write=2026-06-22T20:42:11-07:00 tail_lines=49934
- logs\scanner_signals.log size=99,976,836 last_write=2026-06-22T20:38:43-07:00 tail_lines=42886
- scanner.log size=48,061,748 last_write=2026-06-22T20:42:05-07:00 tail_lines=51242
- logs\watchdog_ibkr.log size=171,258 last_write=2026-06-22T07:09:28-07:00 tail_lines=1996
- logs\web_dashboard_stderr.log size=2,561,834 last_write=2026-05-17T21:50:20-07:00 tail_lines=31116
- logs\web_dashboard_stdout.log size=3,066 last_write=2026-05-17T18:10:46-07:00 tail_lines=41
