# Quarterly Hourly Log Scan


## 2026-06-16 08:02:12 Pacific Daylight Time - ISSUES FOUND

- Scan window: last 2,000,000 bytes per log file
- Unresolved issue markers before this scan: 0

### Log Files
- `logs\bot.log` size=89,018,270 last_write=2026-06-16 08:02:12 Pacific Daylight Time matches=40
- `logs\scanner_signals.log` size=90,159,778 last_write=2026-06-16 08:02:05 Pacific Daylight Time matches=40
- `scanner.log` size=21,807,056 last_write=2026-06-16 08:02:13 Pacific Daylight Time matches=0
- `logs\watchdog_ibkr.log` size=151,055 last_write=2026-06-16 02:02:18 Pacific Daylight Time matches=40
- `logs\web_dashboard_stderr.log` size=2,561,834 last_write=2026-05-17 21:50:20 Pacific Daylight Time matches=17
- `logs\web_dashboard_stdout.log` size=3,066 last_write=2026-05-17 18:10:46 Pacific Daylight Time matches=9

### Issues
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:00:34 [ERROR] yfinance: $TRUMP-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:31 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  CRV/USD  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:47 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NMR/USD  reason=Hard check failed: Volume spike 0.68x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:52 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  GODS/USD  reason=Hard check failed: Volume spike 0.49x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  HNT/USD  reason=Hard check failed: Volume spike 0.69x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:08 [ERROR] yfinance: $TRUMP-USD: possibly delisted; no price data found  (period=30d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:20 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  JTO/USD  reason=Hard check failed: Volume spike 0.77x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:10:19 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  BONK/USD  reason=Hard check failed: Price $0.000005 below MIN_PRICE_CRYPTO $0.0001 — micro-cap rejected`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 18:01:04 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: XMR/USD LONG score=0.683 | tf=1h | MR-02 VEF: ATR spike 1.55x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 18:33:00 [INFO] core.position_monitor: [EARLY LOSS EXIT] XMR/USD: P&L -0.66% at 30min AND still moving wrong direction — thesis failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:09:49 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.wrapper: Error 326, reqId -1: Unable to connect as the client id is already in use. Retry with a unique client id.`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.client: Peer closed connection. clientId 3 already in use?`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [ERROR] ib_insync.client: API connection failed: TimeoutError()`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [WARNING] core.ibkr_executor: IBKR clientId 3 connect error: `
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:39:26 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:50:00 [INFO] core.position_monitor: [PIVOT EXIT] SUSHI/USD: LONG broke below S1=0.1796 (current=0.1790) — structural support failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/1h unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 01:07:06 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: JUP/USD LONG score=0.841 | tf=1h | MR-02 VEF: ATR spike 1.79x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:14 [ERROR] core.trade_executor: Alpaca bracket order failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Alpaca plain market order also failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Order submission failed for SPCX`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:20 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  TSLL  reason=Hard check failed: Trend reversed — 2/3 recent candles bullish on SHORT signal (TSLL/5m)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 07:20:28 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  FLYT  reason=Hard check failed: FLYT reversed +1.61% from signal price (limit +0.5%)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 09:09:11 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: OCEAN/USD LONG score=0.723 | tf=1h | MR-02 VEF: ATR spike 1.61x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: close_position failed for KLAC: position not found: KLAC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close KLAC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] KLAC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close position KLAC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:07:17 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.855 | tf=1h | MR-02 VEF: ATR spike 1.81x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:45:07 [WARNING] core.trade_executor: close_position failed for KLAC: insufficient qty available for order (requested: 7, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:54 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LRCX  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  AMAT  reason=Hard check failed: Volume spike 1.04x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BBAI  reason=Hard check failed: Volume spike 0.80x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:08 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  SOFI  reason=Hard check failed: Volume spike 1.05x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:10 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NIO  reason=Hard check failed: Volume spike 0.67x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:12 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.84x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:15 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIVN  reason=Hard check failed: Volume spike 0.63x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:21 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  REGN  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:23 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIIB  reason=Hard check failed: Volume spike 0.86x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:25 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NVAX  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:29 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RKLB  reason=Hard check failed: Volume spike 1.08x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:30 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  ASTS  reason=Hard check failed: Volume spike 0.93x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:33 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LMT  reason=Hard check failed: Volume spike 0.98x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:37 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  IREN  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:41:41,915 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:43:16,922 [WATCHDOG] ERROR Port 7497 still not responding after 90s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:45:22,715 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-21 06:00:40,914 [WATCHDOG] INFO Port 7497 responding again after 1 failed check(s)`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:01:37,242 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:04:52,436 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:06:29,763 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #2`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:09:44,862 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:11:21,826 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #3`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:14:35,571 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:16:12,943 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #4`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:19:27,807 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:21:04,721 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #5`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:24:19,273 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:25:56,127 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #6`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:29:12,133 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:30:48,713 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #7`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:34:02,199 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:35:39,011 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #8`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:38:51,608 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:40:28,564 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #9`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:43:41,359 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:45:17,995 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #10`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:48:31,822 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:50:07,917 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #11`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:53:20,451 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:54:57,359 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #12`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:58:10,514 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:59:47,451 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #13`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:03:00,527 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:04:37,455 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #14`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:07:49,596 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:09:26,496 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #15`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:12:39,823 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:14:16,744 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #16`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:17:30,136 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:19:06,734 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #17`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:22:19,105 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:23:56,235 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #18`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:27:09,664 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`

### Patch Diff For Approval
Existing uncommitted Python/PowerShell diff is present. Review before applying any new fix:

```diff
diff --git a/chart_patterns.py b/chart_patterns.py
index 45f3ded89..58cdb45e2 100644
--- a/chart_patterns.py
+++ b/chart_patterns.py
@@ -400,21 +400,26 @@ class PatternDetector:
 
         # Last two significant highs
         p1, p2 = ph[-2], ph[-1]
+        if p2[0] - p1[0] < 6: return None
         diff   = abs(p1[1]-p2[1]) / max(p1[1], p2[1])
-        if diff > 0.025: return None   # peaks must be within 2.5%
+        if diff > 0.018: return None   # peaks must be genuinely similar
 
         # Valley between them
         valley = min(prices[p1[0]:p2[0]+1]) if p1[0] < p2[0] else None
         if valley is None: return None
         pullback = (max(p1[1],p2[1]) - valley) / max(p1[1],p2[1])
-        if pullback < 0.02: return None   # meaningful trough between
+        if pullback < 0.03: return None   # meaningful trough between
 
-        # Current price should be declining from second top
+        prior = self._prior_trend(prices[:p1[0]+1]) if p1[0] >= 8 else self._prior_trend(prices)
+        if prior < 0.001: return None
+
+        # Confirmed double top should be breaking or retesting below the neckline.
         cur_drop = (p2[1] - prices[-1]) / p2[1]
-        confirming = cur_drop > 0.005
+        confirming = prices[-1] <= valley * 1.005
+        if not confirming: return None
 
-        score = 0.35 + 0.30*(diff<0.01) + 0.20*(pullback>0.04) + 0.15*confirming
-        desc  = f"Two peaks at {p1[1]:.2f}/{p2[1]:.2f} ({diff:.1%} apart). Valley={valley:.2f}."
+        score = 0.45 + 0.25*(diff<0.01) + 0.20*(pullback>0.045) + 0.10*(cur_drop>0.02)
+        desc  = f"Two similar peaks at {p1[1]:.2f}/{p2[1]:.2f} ({diff:.1%} apart), neckline={valley:.2f}, confirmed below neckline."
         return PatternResult("Double Top", min(score,1.0), "SHORT", desc, score)
 
     def _double_bottom(self, prices, volumes):
@@ -422,19 +427,25 @@ class PatternDetector:
         if len(pl) < 2: return None
 
         t1, t2 = pl[-2], pl[-1]
+        if t2[0] - t1[0] < 6: return None
         diff   = abs(t1[1]-t2[1]) / max(t1[1], t2[1])
-        if diff > 0.025: return None
+        if diff > 0.018: return None
 
         peak  = max(prices[t1[0]:t2[0]+1]) if t1[0] < t2[0] else None
         if peak is None: return None
         bounce = (peak - min(t1[1],t2[1])) / peak
-        if bounce < 0.02: return None
+        if bounce < 0.03: return None
+
+        prior = self._prior_trend(prices[:t1[0]+1]) if t1[0] >= 8 else self._prior_trend(prices)
+        if prior > -0.001: return None
 
+        # Confirmed double bottom should be breaking or retesting above the neckline.
         cur_rise = (prices[-1] - t2[1]) / t2[1]
-        confirming = cur_rise > 0.005
+        confirming = prices[-1] >= peak * 0.995
+        if not confirming: return None
 
-        score = 0.35 + 0.30*(diff<0.01) + 0.20*(bounce>0.04) + 0.15*confirming
-        desc  = f"Two troughs at {t1[1]:.2f}/{t2[1]:.2f} ({diff:.1%} apart). Peak={peak:.2f}."
+        score = 0.45 + 0.25*(diff<0.01) + 0.20*(bounce>0.045) + 0.10*(cur_rise>0.02)
+        desc  = f"Two similar troughs at {t1[1]:.2f}/{t2[1]:.2f} ({diff:.1%} apart), neckline={peak:.2f}, confirmed above neckline."
         return PatternResult("Double Bottom", min(score,1.0), "LONG", desc, score)
 
     def _cup_and_handle(self, prices, volumes):
@@ -593,9 +604,9 @@ class PatternDetector:
         prev_bull  = c1 > o1
         curr_bear  = c2 < o2
         engulfs    = o2 >= c1 and c2 <= o1   # current body wraps prior body
-        if not (prev_bull and curr_bear and engulfs): return None
-
         size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
+        if not (prev_bull and curr_bear and engulfs and size_ratio >= 1.05): return None
+
         score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)>0)
         return PatternResult("Bearish Engulfing", min(score,1.0), "SHORT",
             f"Bearish candle engulfs prior bullish ({size_ratio:.1f}x size).", score)
@@ -607,9 +618,9 @@ class PatternDetector:
         prev_bear  = c1 < o1
         curr_bull  = c2 > o2
         engulfs    = o2 <= c1 and c2 >= o1
-        if not (prev_bear and curr_bull and engulfs): return None
-
         size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
+        if not (prev_bear and curr_bull and engulfs and size_ratio >= 1.05): return None
+
         score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)<0)
         return PatternResult("Bullish Engulfing", min(score,1.0), "LONG",
             f"Bullish candle engulfs prior bearish ({size_ratio:.1f}x size).", score)
diff --git a/config.py b/config.py
index eb8ec2c63..41baca66f 100644
--- a/config.py
+++ b/config.py
@@ -109,7 +109,10 @@ ANTHROPIC_API_KEY   = _db_key("anthropic", "api_key",    _decrypt(os.getenv("ANT
 
 COINDESK_API_KEY    = _db_key("coindesk",  "api_key",    _decrypt(os.getenv("COINDESK_API_KEY", "gAAAAABqE0y3UHrVHis66FBSmi3Lv8jIv6xodP02_6aOL7pDcUX_4eMa7ViRVhRz3jcw188fDzS8vIUB6zH_oFcjdLwyAhPj5KyxviSJWtITJsTU2kR5RcPHd7hS8mjVC6EkeTthL9EpjM-vXzcMw20UIOX7xHkVA8BP6S8IWSCty02KGt5kU5k=")))
 
-ALPHA_VANTAGE_KEY   = _db_key("alpha_vantage", "api_key", _decrypt(os.getenv("ALPHA_VANTAGE_KEY", "")))
+ALPHA_VANTAGE_KEY   = _db_key(
+    "alphavantage", "api_key",
+    _db_key("alpha_vantage", "api_key", _decrypt(os.getenv("ALPHA_VANTAGE_KEY", "")))
+)
 
 KRAKEN_ENABLED      = True
 
@@ -138,7 +141,7 @@ IBKR_TRADE_ENABLED  = False  # SAFETY LOCK â€” set True only when ready to execu
                               # While False: IBKR connected for display only, all stock trades route Alpaca paper
 
 CLAUDE_REVIEWER_ENABLED = True
-CLAUDE_REVIEWER_MODE = "Strict"
+CLAUDE_REVIEWER_MODE = "advisory"
 CLAUDE_REVIEWER_APPLY_SIZE_ADVICE = True
 
 # Contrarian scanner mode â€” invert selected scanner signal directions after
@@ -146,7 +149,7 @@ CLAUDE_REVIEWER_APPLY_SIZE_ADVICE = True
 # Source-specific flags let each scanner be tested independently.
 BREAKOUT_CONTRARIAN_MODE = True
 BREAKOUT_SCANNER_CONTRARIAN = True
-FUNDING_SCANNER_CONTRARIAN  = True
+FUNDING_SCANNER_CONTRARIAN  = False
 GAP_SCANNER_CONTRARIAN      = False
 
 BREAKOUT_CONTRARIAN_SOURCE_FLAGS = {
diff --git a/core/position_monitor.py b/core/position_monitor.py
index 86728b49b..5950164c1 100644
--- a/core/position_monitor.py
+++ b/core/position_monitor.py
@@ -71,7 +71,9 @@ STALE_THRESHOLD_SEC = 3 * 60 * 60       # 3 hours before ADX/DI stale check fire
 # ADX threshold below which trend is considered stalled
 ADX_STALE_THRESHOLD = 25.0
 
-PM_DEBUG = True
+PM_DEBUG = False
+
+
 
 # â”€â”€ NEW: Time-based exit thresholds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 # Performance-contingent: close if profit is below threshold after N hours.
diff --git a/intelligence/claude_reviewer.py b/intelligence/claude_reviewer.py
index 6e48bf06f..9c7f123c7 100644
--- a/intelligence/claude_reviewer.py
+++ b/intelligence/claude_reviewer.py
@@ -84,9 +84,10 @@ REVIEW_INDICATOR_KEYS = (
 _SYSTEM_PROMPT = (
     "You are the signal-review layer of an autonomous day trading bot. "
     "You have VETO power only â€” you cannot initiate trades. "
-    "Respond with ONLY a valid JSON array. No markdown, no explanation, no surrounding text. "
-    "Each element corresponds to one signal in the order provided. "
-    "For each signal output: "
+    "Respond with ONLY the JSON shape requested by the user prompt. "
+    "No markdown, no explanation, no surrounding text. "
+    "For signal-review prompts, each array element corresponds to one signal in the order provided. "
+    "For each signal-review item output: "
     "{\"symbol\": \"SYM\", \"decision\": \"APPROVE|REJECT|SKIP\", "
     "\"confidence\": 0-100, \"reasoning\": \"one clear sentence\"}. "
     "Decision rules: "
@@ -209,6 +210,120 @@ def _round_for_prompt(value):
     return value
 
 
+def _pct_change(current: float, previous: float) -> Optional[float]:
+    try:
+        if previous == 0:
+            return None
+        return ((float(current) - float(previous)) / float(previous)) * 100
+    except Exception:
+        return None
+
+
+def _summarize_bars(symbol: str, bars) -> Dict:
+    close = bars["close"]
+    last_close = float(close.iloc[-1])
+    first_close = float(close.iloc[0])
+    prev_close = float(close.iloc[-2]) if len(close) >= 2 else first_close
+    sma20 = float(close.tail(20).mean()) if len(close) >= 20 else None
+    return {
+        "symbol": symbol,
+        "bars": int(len(bars)),
+        "last_timestamp": str(bars.index[-1]),
+        "last_close": round(last_close, 4),
+        "change_from_first_bar_pct": _round_for_prompt(_pct_change(last_close, first_close)),
+        "last_bar_change_pct": _round_for_prompt(_pct_change(last_close, prev_close)),
+        "above_sma20": None if sma20 is None else bool(last_close > sma20),
+    }
+
+
+def _fetch_alpha_movers() -> Dict:
+    if not getattr(config, "ALPHA_VANTAGE_KEY", ""):
+        return {"enabled": False, "reason": "missing_alpha_vantage_key"}
+
+    try:
+        import urllib.parse
+        import urllib.request
+
+        url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode({
+            "function": "TOP_GAINERS_LOSERS",
+            "apikey": config.ALPHA_VANTAGE_KEY,
+        })
+        with urllib.request.urlopen(url, timeout=10) as response:
+            data = json.loads(response.read(200000))
+
+        if "Note" in data:
+            return {"enabled": True, "error": "rate_limit", "message": data["Note"][:200]}
+        if "Information" in data:
+            return {"enabled": True, "error": "api_message", "message": data["Information"][:200]}
+        if "Error Message" in data:
+            return {"enabled": True, "error": "api_error", "message": data["Error Message"][:200]}
+
+        def _top(rows):
+            output = []
+            for row in rows[:5]:
+                output.append({
+                    "ticker": row.get("ticker", ""),
+                    "price": row.get("price", ""),
+                    "change_pct": row.get("change_percentage", ""),
+                    "volume": row.get("volume", ""),
+                })
+            return output
+
+        return {
+            "enabled": True,
+            "last_updated": data.get("last_updated", ""),
+            "top_gainers": _top(data.get("top_gainers", [])),
+            "top_losers": _top(data.get("top_losers", [])),
+            "most_active": _top(data.get("most_actively_traded", [])),
+        }
+    except Exception as exc:
+        return {"enabled": True, "error": type(exc).__name__, "message": str(exc)[:200]}
+
+
+def _build_market_snapshot() -> Dict:
+    snapshot = {
+        "generated_at": datetime.now().isoformat(timespec="seconds"),
+        "equity_index_proxies": [],
+        "market_condition": None,
+        "alpha_vantage_movers": None,
+        "errors": [],
+    }
+
+    try:
+        from scanners.market_scanner import StockScanner
+        from intelligence.condition_detector import condition_detector
+
+        stock_scanner = StockScanner()
+        for symbol in ("SPY", "QQQ", "IWM", "DIA"):
+            try:
+                bars = stock_scanner.get_bars(symbol, timeframe="5Min", limit=100)
+                if bars is None or bars.empty:
+                    snapshot["errors"].append(f"{symbol}: no 5Min bars")
+                    continue
+                snapshot["equity_index_proxies"].append(_summarize_bars(symbol, bars))
+            except Exception as exc:
+                snapshot["errors"].append(f"{symbol}: {type(exc).__name__}: {exc}")
+
+        try:
+            report = condition_detector.get_spy_condition(stock_scanner)
+            snapshot["market_condition"] = {
+                "condition": report.condition.value,
+                "should_trade": bool(report.should_trade),
+                "reason": report.reason,
+                "adx": report.adx,
+                "atr_pct": report.atr_pct,

```

### Process Health - 2026-06-16 08:02:16 -07:00
- OK: bot_engine.py running as PID(s): 5388, 36000
- OK: web_dashboard.py running as PID(s): 12200, 29220
- OK: BreakoutScanner.py running as PID(s): 16824, 1076
- OK: launch-watchdog.ps1 / watchdog_ibkr.py running as PID(s): 39944, 10244
- Alert: triple beep attempted because this scan found unresolved issues.

## 2026-06-16 08:02:43 Pacific Daylight Time - ISSUES FOUND

- Scan window: last 2,000,000 bytes per log file
- Unresolved issue markers before this scan: 120

### Log Files
- `logs\bot.log` size=89,023,142 last_write=2026-06-16 08:02:44 Pacific Daylight Time matches=40
- `logs\scanner_signals.log` size=90,159,778 last_write=2026-06-16 08:02:05 Pacific Daylight Time matches=40
- `scanner.log` size=21,815,134 last_write=2026-06-16 08:02:45 Pacific Daylight Time matches=0
- `logs\watchdog_ibkr.log` size=151,055 last_write=2026-06-16 02:02:18 Pacific Daylight Time matches=40
- `logs\web_dashboard_stderr.log` size=2,561,834 last_write=2026-05-17 21:50:20 Pacific Daylight Time matches=17
- `logs\web_dashboard_stdout.log` size=3,066 last_write=2026-05-17 18:10:46 Pacific Daylight Time matches=9

### Issues
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:00:34 [ERROR] yfinance: $TRUMP-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:31 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  CRV/USD  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:47 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NMR/USD  reason=Hard check failed: Volume spike 0.68x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:05:52 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  GODS/USD  reason=Hard check failed: Volume spike 0.49x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  HNT/USD  reason=Hard check failed: Volume spike 0.69x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:08 [ERROR] yfinance: $TRUMP-USD: possibly delisted; no price data found  (period=30d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:06:20 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  JTO/USD  reason=Hard check failed: Volume spike 0.77x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 17:10:19 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  BONK/USD  reason=Hard check failed: Price $0.000005 below MIN_PRICE_CRYPTO $0.0001 — micro-cap rejected`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 18:01:04 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: XMR/USD LONG score=0.683 | tf=1h | MR-02 VEF: ATR spike 1.55x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 18:33:00 [INFO] core.position_monitor: [EARLY LOSS EXIT] XMR/USD: P&L -0.66% at 30min AND still moving wrong direction — thesis failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:09:49 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.wrapper: Error 326, reqId -1: Unable to connect as the client id is already in use. Retry with a unique client id.`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.client: Peer closed connection. clientId 3 already in use?`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [ERROR] ib_insync.client: API connection failed: TimeoutError()`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [WARNING] core.ibkr_executor: IBKR clientId 3 connect error: `
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:39:26 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:50:00 [INFO] core.position_monitor: [PIVOT EXIT] SUSHI/USD: LONG broke below S1=0.1796 (current=0.1790) — structural support failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/1h unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 01:07:06 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: JUP/USD LONG score=0.841 | tf=1h | MR-02 VEF: ATR spike 1.79x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:14 [ERROR] core.trade_executor: Alpaca bracket order failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Alpaca plain market order also failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Order submission failed for SPCX`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:20 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  TSLL  reason=Hard check failed: Trend reversed — 2/3 recent candles bullish on SHORT signal (TSLL/5m)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 07:20:28 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  FLYT  reason=Hard check failed: FLYT reversed +1.61% from signal price (limit +0.5%)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 09:09:11 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: OCEAN/USD LONG score=0.723 | tf=1h | MR-02 VEF: ATR spike 1.61x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: close_position failed for KLAC: position not found: KLAC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close KLAC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] KLAC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close position KLAC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:07:17 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.855 | tf=1h | MR-02 VEF: ATR spike 1.81x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:45:07 [WARNING] core.trade_executor: close_position failed for KLAC: insufficient qty available for order (requested: 7, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:54 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LRCX  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  AMAT  reason=Hard check failed: Volume spike 1.04x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BBAI  reason=Hard check failed: Volume spike 0.80x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:08 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  SOFI  reason=Hard check failed: Volume spike 1.05x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:10 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NIO  reason=Hard check failed: Volume spike 0.67x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:12 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.84x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:15 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIVN  reason=Hard check failed: Volume spike 0.63x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:21 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  REGN  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:23 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIIB  reason=Hard check failed: Volume spike 0.86x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:25 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NVAX  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:29 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RKLB  reason=Hard check failed: Volume spike 1.08x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:30 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  ASTS  reason=Hard check failed: Volume spike 0.93x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:33 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LMT  reason=Hard check failed: Volume spike 0.98x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:37 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  IREN  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:41:41,915 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:43:16,922 [WATCHDOG] ERROR Port 7497 still not responding after 90s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:45:22,715 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-21 06:00:40,914 [WATCHDOG] INFO Port 7497 responding again after 1 failed check(s)`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:01:37,242 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:04:52,436 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:06:29,763 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #2`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:09:44,862 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:11:21,826 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #3`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:14:35,571 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:16:12,943 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #4`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:19:27,807 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:21:04,721 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #5`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:24:19,273 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:25:56,127 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #6`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:29:12,133 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:30:48,713 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #7`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:34:02,199 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:35:39,011 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #8`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:38:51,608 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:40:28,564 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #9`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:43:41,359 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:45:17,995 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #10`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:48:31,822 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:50:07,917 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #11`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:53:20,451 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:54:57,359 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #12`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:58:10,514 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:59:47,451 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #13`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:03:00,527 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:04:37,455 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #14`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:07:49,596 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:09:26,496 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #15`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:12:39,823 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:14:16,744 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #16`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:17:30,136 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:19:06,734 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #17`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:22:19,105 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:23:56,235 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #18`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:27:09,664 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`

### Patch Diff For Approval
Existing uncommitted Python/PowerShell diff is present. Review before applying any new fix:

```diff
diff --git a/chart_patterns.py b/chart_patterns.py
index 45f3ded89..58cdb45e2 100644
--- a/chart_patterns.py
+++ b/chart_patterns.py
@@ -400,21 +400,26 @@ class PatternDetector:
 
         # Last two significant highs
         p1, p2 = ph[-2], ph[-1]
+        if p2[0] - p1[0] < 6: return None
         diff   = abs(p1[1]-p2[1]) / max(p1[1], p2[1])
-        if diff > 0.025: return None   # peaks must be within 2.5%
+        if diff > 0.018: return None   # peaks must be genuinely similar
 
         # Valley between them
         valley = min(prices[p1[0]:p2[0]+1]) if p1[0] < p2[0] else None
         if valley is None: return None
         pullback = (max(p1[1],p2[1]) - valley) / max(p1[1],p2[1])
-        if pullback < 0.02: return None   # meaningful trough between
+        if pullback < 0.03: return None   # meaningful trough between
 
-        # Current price should be declining from second top
+        prior = self._prior_trend(prices[:p1[0]+1]) if p1[0] >= 8 else self._prior_trend(prices)
+        if prior < 0.001: return None
+
+        # Confirmed double top should be breaking or retesting below the neckline.
         cur_drop = (p2[1] - prices[-1]) / p2[1]
-        confirming = cur_drop > 0.005
+        confirming = prices[-1] <= valley * 1.005
+        if not confirming: return None
 
-        score = 0.35 + 0.30*(diff<0.01) + 0.20*(pullback>0.04) + 0.15*confirming
-        desc  = f"Two peaks at {p1[1]:.2f}/{p2[1]:.2f} ({diff:.1%} apart). Valley={valley:.2f}."
+        score = 0.45 + 0.25*(diff<0.01) + 0.20*(pullback>0.045) + 0.10*(cur_drop>0.02)
+        desc  = f"Two similar peaks at {p1[1]:.2f}/{p2[1]:.2f} ({diff:.1%} apart), neckline={valley:.2f}, confirmed below neckline."
         return PatternResult("Double Top", min(score,1.0), "SHORT", desc, score)
 
     def _double_bottom(self, prices, volumes):
@@ -422,19 +427,25 @@ class PatternDetector:
         if len(pl) < 2: return None
 
         t1, t2 = pl[-2], pl[-1]
+        if t2[0] - t1[0] < 6: return None
         diff   = abs(t1[1]-t2[1]) / max(t1[1], t2[1])
-        if diff > 0.025: return None
+        if diff > 0.018: return None
 
         peak  = max(prices[t1[0]:t2[0]+1]) if t1[0] < t2[0] else None
         if peak is None: return None
         bounce = (peak - min(t1[1],t2[1])) / peak
-        if bounce < 0.02: return None
+        if bounce < 0.03: return None
+
+        prior = self._prior_trend(prices[:t1[0]+1]) if t1[0] >= 8 else self._prior_trend(prices)
+        if prior > -0.001: return None
 
+        # Confirmed double bottom should be breaking or retesting above the neckline.
         cur_rise = (prices[-1] - t2[1]) / t2[1]
-        confirming = cur_rise > 0.005
+        confirming = prices[-1] >= peak * 0.995
+        if not confirming: return None
 
-        score = 0.35 + 0.30*(diff<0.01) + 0.20*(bounce>0.04) + 0.15*confirming
-        desc  = f"Two troughs at {t1[1]:.2f}/{t2[1]:.2f} ({diff:.1%} apart). Peak={peak:.2f}."
+        score = 0.45 + 0.25*(diff<0.01) + 0.20*(bounce>0.045) + 0.10*(cur_rise>0.02)
+        desc  = f"Two similar troughs at {t1[1]:.2f}/{t2[1]:.2f} ({diff:.1%} apart), neckline={peak:.2f}, confirmed above neckline."
         return PatternResult("Double Bottom", min(score,1.0), "LONG", desc, score)
 
     def _cup_and_handle(self, prices, volumes):
@@ -593,9 +604,9 @@ class PatternDetector:
         prev_bull  = c1 > o1
         curr_bear  = c2 < o2
         engulfs    = o2 >= c1 and c2 <= o1   # current body wraps prior body
-        if not (prev_bull and curr_bear and engulfs): return None
-
         size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
+        if not (prev_bull and curr_bear and engulfs and size_ratio >= 1.05): return None
+
         score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)>0)
         return PatternResult("Bearish Engulfing", min(score,1.0), "SHORT",
             f"Bearish candle engulfs prior bullish ({size_ratio:.1f}x size).", score)
@@ -607,9 +618,9 @@ class PatternDetector:
         prev_bear  = c1 < o1
         curr_bull  = c2 > o2
         engulfs    = o2 <= c1 and c2 >= o1
-        if not (prev_bear and curr_bull and engulfs): return None
-
         size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
+        if not (prev_bear and curr_bull and engulfs and size_ratio >= 1.05): return None
+
         score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)<0)
         return PatternResult("Bullish Engulfing", min(score,1.0), "LONG",
             f"Bullish candle engulfs prior bearish ({size_ratio:.1f}x size).", score)
diff --git a/config.py b/config.py
index eb8ec2c63..41baca66f 100644
--- a/config.py
+++ b/config.py
@@ -109,7 +109,10 @@ ANTHROPIC_API_KEY   = _db_key("anthropic", "api_key",    _decrypt(os.getenv("ANT
 
 COINDESK_API_KEY    = _db_key("coindesk",  "api_key",    _decrypt(os.getenv("COINDESK_API_KEY", "gAAAAABqE0y3UHrVHis66FBSmi3Lv8jIv6xodP02_6aOL7pDcUX_4eMa7ViRVhRz3jcw188fDzS8vIUB6zH_oFcjdLwyAhPj5KyxviSJWtITJsTU2kR5RcPHd7hS8mjVC6EkeTthL9EpjM-vXzcMw20UIOX7xHkVA8BP6S8IWSCty02KGt5kU5k=")))
 
-ALPHA_VANTAGE_KEY   = _db_key("alpha_vantage", "api_key", _decrypt(os.getenv("ALPHA_VANTAGE_KEY", "")))
+ALPHA_VANTAGE_KEY   = _db_key(
+    "alphavantage", "api_key",
+    _db_key("alpha_vantage", "api_key", _decrypt(os.getenv("ALPHA_VANTAGE_KEY", "")))
+)
 
 KRAKEN_ENABLED      = True
 
@@ -138,7 +141,7 @@ IBKR_TRADE_ENABLED  = False  # SAFETY LOCK â€” set True only when ready to execu
                               # While False: IBKR connected for display only, all stock trades route Alpaca paper
 
 CLAUDE_REVIEWER_ENABLED = True
-CLAUDE_REVIEWER_MODE = "Strict"
+CLAUDE_REVIEWER_MODE = "advisory"
 CLAUDE_REVIEWER_APPLY_SIZE_ADVICE = True
 
 # Contrarian scanner mode â€” invert selected scanner signal directions after
@@ -146,7 +149,7 @@ CLAUDE_REVIEWER_APPLY_SIZE_ADVICE = True
 # Source-specific flags let each scanner be tested independently.
 BREAKOUT_CONTRARIAN_MODE = True
 BREAKOUT_SCANNER_CONTRARIAN = True
-FUNDING_SCANNER_CONTRARIAN  = True
+FUNDING_SCANNER_CONTRARIAN  = False
 GAP_SCANNER_CONTRARIAN      = False
 
 BREAKOUT_CONTRARIAN_SOURCE_FLAGS = {
diff --git a/core/position_monitor.py b/core/position_monitor.py
index 86728b49b..5950164c1 100644
--- a/core/position_monitor.py
+++ b/core/position_monitor.py
@@ -71,7 +71,9 @@ STALE_THRESHOLD_SEC = 3 * 60 * 60       # 3 hours before ADX/DI stale check fire
 # ADX threshold below which trend is considered stalled
 ADX_STALE_THRESHOLD = 25.0
 
-PM_DEBUG = True
+PM_DEBUG = False
+
+
 
 # â”€â”€ NEW: Time-based exit thresholds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 # Performance-contingent: close if profit is below threshold after N hours.
diff --git a/intelligence/claude_reviewer.py b/intelligence/claude_reviewer.py
index 6e48bf06f..9c7f123c7 100644
--- a/intelligence/claude_reviewer.py
+++ b/intelligence/claude_reviewer.py
@@ -84,9 +84,10 @@ REVIEW_INDICATOR_KEYS = (
 _SYSTEM_PROMPT = (
     "You are the signal-review layer of an autonomous day trading bot. "
     "You have VETO power only â€” you cannot initiate trades. "
-    "Respond with ONLY a valid JSON array. No markdown, no explanation, no surrounding text. "
-    "Each element corresponds to one signal in the order provided. "
-    "For each signal output: "
+    "Respond with ONLY the JSON shape requested by the user prompt. "
+    "No markdown, no explanation, no surrounding text. "
+    "For signal-review prompts, each array element corresponds to one signal in the order provided. "
+    "For each signal-review item output: "
     "{\"symbol\": \"SYM\", \"decision\": \"APPROVE|REJECT|SKIP\", "
     "\"confidence\": 0-100, \"reasoning\": \"one clear sentence\"}. "
     "Decision rules: "
@@ -209,6 +210,120 @@ def _round_for_prompt(value):
     return value
 
 
+def _pct_change(current: float, previous: float) -> Optional[float]:
+    try:
+        if previous == 0:
+            return None
+        return ((float(current) - float(previous)) / float(previous)) * 100
+    except Exception:
+        return None
+
+
+def _summarize_bars(symbol: str, bars) -> Dict:
+    close = bars["close"]
+    last_close = float(close.iloc[-1])
+    first_close = float(close.iloc[0])
+    prev_close = float(close.iloc[-2]) if len(close) >= 2 else first_close
+    sma20 = float(close.tail(20).mean()) if len(close) >= 20 else None
+    return {
+        "symbol": symbol,
+        "bars": int(len(bars)),
+        "last_timestamp": str(bars.index[-1]),
+        "last_close": round(last_close, 4),
+        "change_from_first_bar_pct": _round_for_prompt(_pct_change(last_close, first_close)),
+        "last_bar_change_pct": _round_for_prompt(_pct_change(last_close, prev_close)),
+        "above_sma20": None if sma20 is None else bool(last_close > sma20),
+    }
+
+
+def _fetch_alpha_movers() -> Dict:
+    if not getattr(config, "ALPHA_VANTAGE_KEY", ""):
+        return {"enabled": False, "reason": "missing_alpha_vantage_key"}
+
+    try:
+        import urllib.parse
+        import urllib.request
+
+        url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode({
+            "function": "TOP_GAINERS_LOSERS",
+            "apikey": config.ALPHA_VANTAGE_KEY,
+        })
+        with urllib.request.urlopen(url, timeout=10) as response:
+            data = json.loads(response.read(200000))
+
+        if "Note" in data:
+            return {"enabled": True, "error": "rate_limit", "message": data["Note"][:200]}
+        if "Information" in data:
+            return {"enabled": True, "error": "api_message", "message": data["Information"][:200]}
+        if "Error Message" in data:
+            return {"enabled": True, "error": "api_error", "message": data["Error Message"][:200]}
+
+        def _top(rows):
+            output = []
+            for row in rows[:5]:
+                output.append({
+                    "ticker": row.get("ticker", ""),
+                    "price": row.get("price", ""),
+                    "change_pct": row.get("change_percentage", ""),
+                    "volume": row.get("volume", ""),
+                })
+            return output
+
+        return {
+            "enabled": True,
+            "last_updated": data.get("last_updated", ""),
+            "top_gainers": _top(data.get("top_gainers", [])),
+            "top_losers": _top(data.get("top_losers", [])),
+            "most_active": _top(data.get("most_actively_traded", [])),
+        }
+    except Exception as exc:
+        return {"enabled": True, "error": type(exc).__name__, "message": str(exc)[:200]}
+
+
+def _build_market_snapshot() -> Dict:
+    snapshot = {
+        "generated_at": datetime.now().isoformat(timespec="seconds"),
+        "equity_index_proxies": [],
+        "market_condition": None,
+        "alpha_vantage_movers": None,
+        "errors": [],
+    }
+
+    try:
+        from scanners.market_scanner import StockScanner
+        from intelligence.condition_detector import condition_detector
+
+        stock_scanner = StockScanner()
+        for symbol in ("SPY", "QQQ", "IWM", "DIA"):
+            try:
+                bars = stock_scanner.get_bars(symbol, timeframe="5Min", limit=100)
+                if bars is None or bars.empty:
+                    snapshot["errors"].append(f"{symbol}: no 5Min bars")
+                    continue
+                snapshot["equity_index_proxies"].append(_summarize_bars(symbol, bars))
+            except Exception as exc:
+                snapshot["errors"].append(f"{symbol}: {type(exc).__name__}: {exc}")
+
+        try:
+            report = condition_detector.get_spy_condition(stock_scanner)
+            snapshot["market_condition"] = {
+                "condition": report.condition.value,
+                "should_trade": bool(report.should_trade),
+                "reason": report.reason,
+                "adx": report.adx,
+                "atr_pct": report.atr_pct,

```

## 2026-06-16 08:31:27 Pacific Daylight Time - ISSUES FOUND

- Scan window: last 2,000,000 bytes per log file
- Unresolved issue markers before this scan: 240

### Log Files
- `logs\bot.log` size=89,357,164 last_write=2026-06-16 08:31:27 Pacific Daylight Time matches=40
- `logs\scanner_signals.log` size=90,216,235 last_write=2026-06-16 08:31:21 Pacific Daylight Time matches=40
- `scanner.log` size=21,924,428 last_write=2026-06-16 08:31:28 Pacific Daylight Time matches=0
- `logs\watchdog_ibkr.log` size=151,055 last_write=2026-06-16 02:02:18 Pacific Daylight Time matches=40
- `logs\web_dashboard_stderr.log` size=2,561,834 last_write=2026-05-17 21:50:20 Pacific Daylight Time matches=17
- `logs\web_dashboard_stdout.log` size=3,066 last_write=2026-05-17 18:10:46 Pacific Daylight Time matches=9

### Issues
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:09:49 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.wrapper: Error 326, reqId -1: Unable to connect as the client id is already in use. Retry with a unique client id.`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:39 [ERROR] ib_insync.client: Peer closed connection. clientId 3 already in use?`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [ERROR] ib_insync.client: API connection failed: TimeoutError()`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:30:44 [WARNING] core.ibkr_executor: IBKR clientId 3 connect error: `
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:39:26 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\bot.log: 2026-06-15 21:50:00 [INFO] core.position_monitor: [PIVOT EXIT] SUSHI/USD: LONG broke below S1=0.1796 (current=0.1790) — structural support failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $REZ-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['REZ-USD']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] REZ/USD/1h unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/15m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: $NOT-USD: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [ERROR] yfinance: ['NOT-USD']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:16 [WARNING] core.candle_manager: [CandleManager] NOT/USD/1h unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [ERROR] yfinance: $LISTA-USD: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [ERROR] yfinance: ['LISTA-USD']: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [WARNING] core.candle_manager: [CandleManager] LISTA/USD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [ERROR] yfinance: $LISTA-USD: possibly delisted; no price data found  (period=5d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 00:07:17 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:14 [ERROR] core.trade_executor: Alpaca bracket order failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Alpaca plain market order also failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Order submission failed for SPCX`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:20 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  TSLL  reason=Hard check failed: Trend reversed — 2/3 recent candles bullish on SHORT signal (TSLL/5m)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 07:20:28 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  FLYT  reason=Hard check failed: FLYT reversed +1.61% from signal price (limit +0.5%)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 09:09:11 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: OCEAN/USD LONG score=0.723 | tf=1h | MR-02 VEF: ATR spike 1.61x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: close_position failed for KLAC: position not found: KLAC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close KLAC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] KLAC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close position KLAC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:07:17 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.855 | tf=1h | MR-02 VEF: ATR spike 1.81x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:45:07 [WARNING] core.trade_executor: close_position failed for KLAC: insufficient qty available for order (requested: 7, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:54 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LRCX  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  AMAT  reason=Hard check failed: Volume spike 1.04x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BBAI  reason=Hard check failed: Volume spike 0.80x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:08 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  SOFI  reason=Hard check failed: Volume spike 1.05x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:10 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NIO  reason=Hard check failed: Volume spike 0.67x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:12 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.84x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:15 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIVN  reason=Hard check failed: Volume spike 0.63x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:21 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  REGN  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:23 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIIB  reason=Hard check failed: Volume spike 0.86x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:25 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NVAX  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:29 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RKLB  reason=Hard check failed: Volume spike 1.08x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:30 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  ASTS  reason=Hard check failed: Volume spike 0.93x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:33 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LMT  reason=Hard check failed: Volume spike 0.98x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:37 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  IREN  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:39 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIOT  reason=Hard check failed: Volume spike 0.60x below minimum 1.2x`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:41:41,915 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:43:16,922 [WATCHDOG] ERROR Port 7497 still not responding after 90s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:45:22,715 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-21 06:00:40,914 [WATCHDOG] INFO Port 7497 responding again after 1 failed check(s)`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:01:37,242 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:04:52,436 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:06:29,763 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #2`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:09:44,862 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:11:21,826 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #3`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:14:35,571 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:16:12,943 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #4`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:19:27,807 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:21:04,721 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #5`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:24:19,273 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:25:56,127 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #6`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:29:12,133 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:30:48,713 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #7`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:34:02,199 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:35:39,011 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #8`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:38:51,608 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:40:28,564 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #9`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:43:41,359 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:45:17,995 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #10`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:48:31,822 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:50:07,917 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #11`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:53:20,451 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:54:57,359 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #12`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:58:10,514 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:59:47,451 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #13`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:03:00,527 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:04:37,455 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #14`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:07:49,596 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:09:26,496 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #15`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:12:39,823 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:14:16,744 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #16`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:17:30,136 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:19:06,734 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #17`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:22:19,105 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:23:56,235 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #18`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:27:09,664 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`

### Patch Diff For Approval
Existing uncommitted Python/PowerShell changes are present. Review them before applying any new fix. The quarterly scan no longer inlines the full diff.

- `chart_patterns.py`
- `config.py`
- `core/position_monitor.py`
- `intelligence/claude_reviewer.py`
- `web_dashboard.py`

## 2026-06-16 14:01:10 Pacific Daylight Time - ISSUES FOUND

- Scan window: last 2,000,000 bytes per log file
- Unresolved issue markers before this scan: 360

### Log Files
- `logs\bot.log` size=92,303,155 last_write=2026-06-16 14:01:06 Pacific Daylight Time matches=40
- `logs\scanner_signals.log` size=90,654,435 last_write=2026-06-16 14:00:36 Pacific Daylight Time matches=40
- `scanner.log` size=23,032,536 last_write=2026-06-16 14:00:22 Pacific Daylight Time matches=1
- `logs\watchdog_ibkr.log` size=151,055 last_write=2026-06-16 02:02:18 Pacific Daylight Time matches=40
- `logs\web_dashboard_stderr.log` size=2,561,834 last_write=2026-05-17 21:50:20 Pacific Daylight Time matches=17
- `logs\web_dashboard_stdout.log` size=3,066 last_write=2026-05-17 18:10:46 Pacific Daylight Time matches=9

### Issues
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:03:26 [ERROR] yfinance: $ENPH: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:03:26 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:03:26 [ERROR] yfinance: ['ENPH']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:04 [ERROR] yfinance: $BNTX: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:04 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:04 [ERROR] yfinance: ['BNTX']: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:25 [WARNING] core.candle_manager: [CandleManager] BNTX/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:45 [ERROR] yfinance: $GILD: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:45 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:05:45 [ERROR] yfinance: ['GILD']: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:06:06 [WARNING] core.candle_manager: [CandleManager] GILD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:06:41 [ERROR] yfinance: $NVAX: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:06:41 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:06:41 [ERROR] yfinance: ['NVAX']: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:07:01 [ERROR] yfinance: $BIIB: possibly delisted; no price data found  (period=4d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:07:01 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:07:01 [ERROR] yfinance: ['BIIB']: possibly delisted; no price data found  (period=4d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:08:24 [ERROR] yfinance: $RKLB: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:08:24 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:08:24 [ERROR] yfinance: ['RKLB']: possibly delisted; no price data found  (period=14d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:08:45 [WARNING] core.candle_manager: [CandleManager] RKLB/1h unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: $HOOD: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: ['HOOD']: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [WARNING] core.candle_manager: [CandleManager] HOOD/5m unreachable on all sources — logged`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: $INJ-USD: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: $NMR-USD: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: `
- [UNRESOLVED] `logs\bot.log: 1 Failed download:`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: ['INJ-USD']: possibly delisted; no price data found  (period=3d)`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 10:40:33 [ERROR] yfinance: ['NMR-USD']: possibly delisted; no price data found  (period=2d)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:14 [ERROR] core.trade_executor: Alpaca bracket order failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Alpaca plain market order also failed for SPCX: asset "SPCX" cannot be sold short`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:15 [ERROR] core.trade_executor: Order submission failed for SPCX`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:40:20 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  TSLL  reason=Hard check failed: Trend reversed — 2/3 recent candles bullish on SHORT signal (TSLL/5m)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:46:00 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:47:32 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: close_position failed for INTC: position not found: INTC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close INTC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] INTC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 06:49:01 [ERROR] core.trade_executor: Failed to close position INTC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 07:20:28 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  FLYT  reason=Hard check failed: FLYT reversed +1.61% from signal price (limit +0.5%)`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 09:09:11 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: OCEAN/USD LONG score=0.723 | tf=1h | MR-02 VEF: ATR spike 1.61x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: close_position failed for KLAC: position not found: KLAC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close KLAC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] KLAC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close position KLAC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:07:17 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.855 | tf=1h | MR-02 VEF: ATR spike 1.81x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:45:07 [WARNING] core.trade_executor: close_position failed for KLAC: insufficient qty available for order (requested: 7, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:54 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LRCX  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  AMAT  reason=Hard check failed: Volume spike 1.04x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BBAI  reason=Hard check failed: Volume spike 0.80x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:08 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  SOFI  reason=Hard check failed: Volume spike 1.05x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:10 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NIO  reason=Hard check failed: Volume spike 0.67x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:12 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.84x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:15 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIVN  reason=Hard check failed: Volume spike 0.63x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:21 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  REGN  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:23 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIIB  reason=Hard check failed: Volume spike 0.86x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:25 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NVAX  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:29 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RKLB  reason=Hard check failed: Volume spike 1.08x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:30 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  ASTS  reason=Hard check failed: Volume spike 0.93x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:33 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LMT  reason=Hard check failed: Volume spike 0.98x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:37 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  IREN  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:39 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIOT  reason=Hard check failed: Volume spike 0.60x below minimum 1.2x`
- [UNRESOLVED] `scanner.log: 2026-06-16 10:51:33,538 | ERROR | Alpaca snapshot error: HTTPSConnectionPool(host='paper-api.alpaca.markets', port=443): Max retries exceeded with url: /v2/assets?status=active&asset_class=us_equity (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x000002636448AC00>, 'Connection to paper-api.alpaca.markets timed out. (connect timeout=None)'))`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:41:41,915 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:43:16,922 [WATCHDOG] ERROR Port 7497 still not responding after 90s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:45:22,715 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-21 06:00:40,914 [WATCHDOG] INFO Port 7497 responding again after 1 failed check(s)`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:01:37,242 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:04:52,436 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:06:29,763 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #2`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:09:44,862 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:11:21,826 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #3`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:14:35,571 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:16:12,943 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #4`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:19:27,807 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:21:04,721 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #5`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:24:19,273 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:25:56,127 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #6`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:29:12,133 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:30:48,713 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #7`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:34:02,199 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:35:39,011 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #8`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:38:51,608 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:40:28,564 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #9`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:43:41,359 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:45:17,995 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #10`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:48:31,822 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:50:07,917 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #11`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:53:20,451 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:54:57,359 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #12`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:58:10,514 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:59:47,451 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #13`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:03:00,527 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:04:37,455 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #14`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:07:49,596 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:09:26,496 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #15`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:12:39,823 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:14:16,744 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #16`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:17:30,136 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:19:06,734 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #17`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:22:19,105 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:23:56,235 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #18`

### Patch Diff For Approval
Existing uncommitted Python/PowerShell changes are present. Review them before applying any new fix. The quarterly scan no longer inlines the full diff.

- `chart_patterns.py`
- `config.py`
- `core/position_monitor.py`
- `intelligence/claude_reviewer.py`
- `web_dashboard.py`

### Process Health - 2026-06-16 14:01:12 -07:00
- OK: bot_engine.py running as PID(s): 5388, 36000
- OK: web_dashboard.py running as PID(s): 12200, 29220
- OK: BreakoutScanner.py running as PID(s): 16824, 1076
- OK: launch-watchdog.ps1 / watchdog_ibkr.py running as PID(s): 39944, 10244
- Alert: triple beep attempted because this scan found unresolved issues.

## 2026-06-16 20:08:56 Pacific Daylight Time - ISSUES FOUND

- Scan window: last 2,000,000 bytes per log file
- Unresolved issue markers before this scan: 480

### Log Files
- `logs\bot.log` size=92,887,400 last_write=2026-06-16 20:08:37 Pacific Daylight Time matches=40
- `logs\scanner_signals.log` size=91,001,172 last_write=2026-06-16 20:05:31 Pacific Daylight Time matches=40
- `scanner.log` size=23,948,888 last_write=2026-06-16 20:07:24 Pacific Daylight Time matches=2
- `logs\watchdog_ibkr.log` size=154,590 last_write=2026-06-16 20:05:43 Pacific Daylight Time matches=40
- `logs\web_dashboard_stderr.log` size=2,561,834 last_write=2026-05-17 21:50:20 Pacific Daylight Time matches=17
- `logs\web_dashboard_stdout.log` size=3,066 last_write=2026-05-17 18:10:46 Pacific Daylight Time matches=9

### Issues
- [UNRESOLVED] `logs\bot.log: 2026-06-16 11:01:51 [INFO] core.position_monitor: [PIVOT EXIT] TAKE/USD: SHORT broke above R1=0.0191 (current=0.0193) — structural resistance failed, closing`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:09:10 [WARNING] core.trade_executor: close_position failed for MSFT: insufficient qty available for order (requested: 5, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:09:10 [ERROR] core.trade_executor: Failed to close MSFT: internal server error occurred`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:09:10 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] MSFT: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:09:10 [ERROR] core.trade_executor: Failed to close position MSFT`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:09:10 [WARNING] core.position_monitor: Close attempt 1/8 failed for MSFT | reason=stop_loss | next retry in 60s`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:19:54 [WARNING] core.trade_executor: close_position failed for MSFT: request timed out — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:22:04 [ERROR] core.trade_executor: Failed to close MSFT: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:22:04 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] MSFT: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:22:04 [ERROR] core.trade_executor: Failed to close position MSFT`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:22:04 [WARNING] core.position_monitor: Close attempt 2/8 failed for MSFT | reason=stop_loss | next retry in 60s`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:27:28 [WARNING] core.trade_executor: close_position failed for AMZN: request timed out — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:29:38 [ERROR] core.trade_executor: Failed to close AMZN: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:29:38 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] AMZN: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:29:38 [ERROR] core.trade_executor: Failed to close position AMZN`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:29:38 [WARNING] core.position_monitor: Close attempt 1/8 failed for AMZN | reason=stop_loss | next retry in 60s`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:42:11 [ERROR] core.trade_executor: Alpaca bracket order failed for BABA: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:44:20 [ERROR] core.trade_executor: Alpaca plain market order also failed for BABA: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:44:20 [ERROR] core.trade_executor: Order submission failed for BABA`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:49:20 [WARNING] core.trade_executor: close_position failed for AMZN: request timed out — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:51:30 [ERROR] core.trade_executor: Failed to close AMZN: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:51:30 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] AMZN: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:51:30 [ERROR] core.trade_executor: Failed to close position AMZN`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:51:30 [ERROR] BotEngine: EOD close FAILED for AMZN`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:55:50 [WARNING] core.trade_executor: close_position failed for HAL: request timed out — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:58:00 [ERROR] core.trade_executor: Failed to close HAL: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:58:00 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] HAL: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:58:00 [ERROR] core.trade_executor: Failed to close position HAL`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 12:58:00 [ERROR] BotEngine: EOD close FAILED for HAL`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:02:20 [WARNING] core.trade_executor: close_position failed for MSFT: request timed out — trying manual market order`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:04:31 [ERROR] core.trade_executor: Failed to close MSFT: request timed out`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:04:31 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] MSFT: trying IBKR as well`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:04:31 [ERROR] core.trade_executor: Failed to close position MSFT`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:04:31 [ERROR] BotEngine: EOD close FAILED for MSFT`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:04:31 [INFO] BotEngine: Stock EOD close: 0 closed, 0 overnight skipped, 3 failed: ['AMZN', 'HAL', 'MSFT']`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:05:52 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  MSFT  reason=Hard check failed: Already have open position on MSFT`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  PANW  reason=Hard check failed: Volume spike 0.60x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:06:13 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.66x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.16x below minimum 1.2x`
- [UNRESOLVED] `logs\bot.log: 2026-06-16 13:06:18 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  MP  reason=Hard check failed: Volume spike 0.55x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: close_position failed for KLAC: position not found: KLAC — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close KLAC: position does not exist`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [WARNING] core.trade_executor: [ALPACA CLOSE FAILED] KLAC: trying IBKR as well`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 11:38:52 [ERROR] core.trade_executor: Failed to close position KLAC`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:07:17 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.855 | tf=1h | MR-02 VEF: ATR spike 1.81x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 12:45:07 [WARNING] core.trade_executor: close_position failed for KLAC: insufficient qty available for order (requested: 7, available: 0) — trying manual market order`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:54 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LRCX  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:05:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  AMAT  reason=Hard check failed: Volume spike 1.04x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BBAI  reason=Hard check failed: Volume spike 0.80x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:08 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  SOFI  reason=Hard check failed: Volume spike 1.05x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:10 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NIO  reason=Hard check failed: Volume spike 0.67x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:12 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LI  reason=Hard check failed: Volume spike 0.84x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:14 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  XPEV  reason=Hard check failed: Volume spike 1.02x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:15 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIVN  reason=Hard check failed: Volume spike 0.63x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:21 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  REGN  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:23 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIIB  reason=Hard check failed: Volume spike 0.86x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:25 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NVAX  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:29 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RKLB  reason=Hard check failed: Volume spike 1.08x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:30 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  ASTS  reason=Hard check failed: Volume spike 0.93x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:33 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  LMT  reason=Hard check failed: Volume spike 0.98x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:37 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  IREN  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:39 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  RIOT  reason=Hard check failed: Volume spike 0.60x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:41 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  OKLO  reason=Hard check failed: Volume spike 0.73x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:43 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  HIVE  reason=Hard check failed: Volume spike 0.85x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:46 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  CIFR  reason=Hard check failed: Volume spike 0.95x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:49 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BABA  reason=Hard check failed: Volume spike 0.90x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:51 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  JD  reason=Hard check failed: Volume spike 0.83x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:53 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  BIDU  reason=Hard check failed: Volume spike 0.56x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:56 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  GS  reason=Hard check failed: Volume spike 0.65x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 13:06:58 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  MS  reason=Hard check failed: Volume spike 0.70x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 15:17:46 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SNX/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 1.93x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:05:31 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  CRV/USD  reason=Hard check failed: Volume spike 0.78x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:05:47 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  NMR/USD  reason=Hard check failed: Volume spike 0.68x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:05:52 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  GODS/USD  reason=Hard check failed: Volume spike 0.49x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:06:04 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  HNT/USD  reason=Hard check failed: Volume spike 0.69x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:06:20 [INFO] scanners.base_scanner: [NR7Scanner] Signal REJECTED  JTO/USD  reason=Hard check failed: Volume spike 0.77x below minimum 1.2x`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 17:10:19 [INFO] scanners.base_scanner: [GapScanner] Signal REJECTED  BONK/USD  reason=Hard check failed: Price $0.000005 below MIN_PRICE_CRYPTO $0.0001 — micro-cap rejected`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 18:01:04 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: XMR/USD LONG score=0.683 | tf=1h | MR-02 VEF: ATR spike 1.55x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 21:09:49 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `logs\scanner_signals.log: 2026-06-15 21:39:26 [INFO] strategies.strategy_engine: [mr_02_vef] Signal: SUSHI/USD LONG score=0.880 | tf=1h | MR-02 VEF: ATR spike 2.36x MA | failed bear continuation | above SMA200`
- [UNRESOLVED] `scanner.log: 2026-06-16 10:51:33,538 | ERROR | Alpaca snapshot error: HTTPSConnectionPool(host='paper-api.alpaca.markets', port=443): Max retries exceeded with url: /v2/assets?status=active&asset_class=us_equity (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x000002636448AC00>, 'Connection to paper-api.alpaca.markets timed out. (connect timeout=None)'))`
- [UNRESOLVED] `scanner.log: 2026-06-16 20:05:31,379 | WARNING | coinbase init failed: index out of range`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:41:41,915 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:43:16,922 [WATCHDOG] ERROR Port 7497 still not responding after 90s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-20 16:45:22,715 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-21 06:00:40,914 [WATCHDOG] INFO Port 7497 responding again after 1 failed check(s)`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:01:37,242 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #1`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:04:52,436 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:06:29,763 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #2`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:09:44,862 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:11:21,826 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #3`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:14:35,571 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:16:12,943 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #4`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:19:27,807 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:21:04,721 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #5`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:24:19,273 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:25:56,127 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #6`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:29:12,133 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:30:48,713 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #7`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:34:02,199 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:35:39,011 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #8`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:38:51,608 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:40:28,564 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #9`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:43:41,359 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:45:17,995 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #10`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:48:31,822 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:50:07,917 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #11`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:53:20,451 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:54:57,359 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #12`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:58:10,514 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 06:59:47,451 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #13`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:03:00,527 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:04:37,455 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #14`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:07:49,596 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:09:26,496 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #15`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:12:39,823 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:14:16,744 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #16`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:17:30,136 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:19:06,734 [WATCHDOG] ERROR IBKR unresponsive for 3 checks � initiating restart #17`
- [UNRESOLVED] `logs\watchdog_ibkr.log: 2026-05-22 07:22:19,105 [WATCHDOG] ERROR Port 7497 still not responding after 180s � will retry next cycle`

### Patch Diff For Approval
Existing uncommitted Python/PowerShell changes are present. Review them before applying any new fix. The quarterly scan no longer inlines the full diff.

- `chart_patterns.py`
- `config.py`
- `core/position_monitor.py`
- `intelligence/claude_reviewer.py`
- `web_dashboard.py`

### Process Health - 2026-06-16 20:08:57 -07:00
- OK: bot_engine.py running as PID(s): 36452, 40452
- OK: web_dashboard.py running as PID(s): 41792, 34168
- OK: BreakoutScanner.py running as PID(s): 25884, 23704
- OK: launch-watchdog.ps1 / watchdog_ibkr.py running as PID(s): 22136, 18428
- Alert: triple beep attempted because this scan found unresolved issues.
