# QuarterHourly Log Scan Report
**Generated:** 2026-05-25 11:40 PT  
**Source:** `logs/bot.log` (354,301 lines)  
**Scanners.log:** Not yet present (user noted typo — will appear in future scans)  
**Ghost trade check:** N/A — market closed (Sunday)

---

## FINDINGS

---

### [HIGH] FundingScanner — `current_price/entry_price is zero or missing` — ALL Coinbase signals rejected
**Time:** 11:24:39 and 11:29:40 and 11:34:41 (repeating every 5 min)  
**Affected symbols:** BNB/USD, LTC/USD, AAVE/USD, XBT/USD, ETH/USD — every Coinbase funding signal  
**Detail:** FundingScanner is generating signals via Coinbase but sending `stop=0.0`, `vol=1.00x`, `bars_since=0` with no price data in the payload. The breakout receiver hard-fails every single one on `current_price/entry_price is zero or missing`. No Coinbase funding signals have executed today.  
**Impact:** Entire FundingScanner → Coinbase signal pipeline is dead. All signals pass every other check but fail price sanity.  
**Root cause:** Coinbase payload is not including `current_price` / `entry_price` fields. Likely a Coinbase API response change or a missing field mapping in the funding scanner's signal construction.  
**Status:** 🔴 HIGH PRIORITY — Not auto-resolved (requires code fix in funding scanner payload builder)  
**Action needed:** Check `scanners/funding_scanner.py` — the signal dict sent to breakout_receiver is missing price fields.

---

### [HIGH] Bybit API — 403 Forbidden (repeating)
**Time:** 11:29:39, 11:34:40  
**Log:** `[FUNDING] Bybit fetch error: 403 Client Error: Forbidden for url: https://api.bybit.com/v5/market/tickers?category=linear`  
**Detail:** Bybit funding rate endpoint returning 403. This could be IP ban, API key expired, geo-block, or Bybit rate limiting. The FundingScanner falls back to Coinbase (which has its own issue above), so no Bybit funding signals are executing either.  
**Status:** 🔴 HIGH PRIORITY — Dual funding scanner failure (Bybit 403 + Coinbase no price)  
**Action needed:** Check if Bybit API key is still valid / not expired. Test endpoint manually. May need key rotation or header update.

---

### [MEDIUM] Massive.com API — 429 Rate Limit on morning snapshot (every restart)
**Time:** 11:33:29–11:33:30 (and previously at 17:24:23–17:24:24 on May 17)  
**Log:** `[Massive] SPY 429 in morning snapshot — falling back to yfinance` (x5 symbols: SPY, QQQ, IWM, DIA, RSP)  
**Detail:** Every time the bot starts and builds the morning briefing, Massive.com returns 429 for all market snapshot symbols. The fallback to yfinance works correctly and briefing completes, so no trading impact. However this is hitting rate limits consistently — the Massive API session may be initializing too fast or the plan limits are being reached.  
**Status:** 🟡 MEDIUM — Fallback works, no trading impact, but wasting API quota and slowing briefing  
**Action needed:** Add a short delay between Massive snapshot calls, or cache the morning snapshot for the session rather than re-fetching on each restart.

---

### [MEDIUM] IBKR clientId 2 collision on restart
**Time:** 17:14:27 (May 17 — present on every restart)  
**Log:** `Error 326, reqId -1: Unable to connect as the client id is already in use. Retry with a unique client id.`  
**Detail:** On restart, clientId 2 is already in use (stale connection from previous session). Bot correctly falls back to clientId 3 and connects successfully. No trading impact — IBKR paper account DUQ511882 is connected.  
**Status:** 🟡 MEDIUM — Self-resolving via fallback, but adds ~5s to startup and logs confusing errors  
**Action needed:** Either add a TWS/Gateway disconnect-on-startup step, or implement clientId auto-increment that persists across restarts.

---

### [MEDIUM] Price sanity false positives — OCEAN/USD and ZRO/USD
**Time:** 17:16:47 and 17:55:11 (May 17)  
**Log:**  
- `[PRICE SANITY] OCEAN/USD: live=$0.661832 is 449.7% from entry=$0.1204 — likely bad price feed, skipping`  
- `[PRICE SANITY] ZRO/USD: live=$0.000043 is 100.0% from entry=$1.2695 — likely bad price feed, skipping`  
**Detail:** Position monitor is seeing prices wildly different from entry — OCEAN at 449% from entry, ZRO showing near-zero ($0.000043 vs $1.27 entry). The sanity check correctly skips these rather than triggering false stops. ZRO near-zero looks like a Kraken data feed glitch (decimal point error). OCEAN may have been a legitimate move or stale data.  
**Status:** 🟡 MEDIUM — Sanity check is working as designed, but ZRO=$0.000043 suggests a data feed issue worth monitoring  
**Action needed:** Monitor recurrence. If ZRO consistently shows bad prices, add it to a feed-exclusion list.

---

### [LOW] Structural stop on wrong side of fill — recurring pattern
**Time:** 17:08:35 through 17:08:39 (May 17) and throughout  
**Log:** `[STOP REFRESH] ETH/USD: fresh structural stop $2173.32 is on the wrong side of fill price $2118.97 (long) — falling back to percent-based stop` (multiple symbols)  
**Detail:** Structural stops computed at signal time are above the fill price on longs — meaning the signal's ATR stop was above entry, which is invalid. The fallback to percent-based stop is working correctly. This is a systematic issue with certain strategies (grid_bot primarily) generating structural stops that don't validate against fill price.  
**Status:** 🟢 LOW — Fallback working, no money lost, but strategy stop quality is degraded for these trades  
**Action needed:** Review structural stop computation in grid_bot / dca_accumulator — ensure stop is always below fill for longs before submitting.

---

### [LOW] ENJ/USD short blocked — not margin-eligible on Kraken
**Time:** 11:33:35  
**Log:** `[SHORT BLOCKED] ENJ/USD on kraken: not margin-eligible — short signal dropped`  
**Detail:** mr_03_fbs generated a valid short signal on ENJ/USD but ENJ is not on Kraken's margin pair list (555 pairs checked). Signal correctly dropped. Normal behavior — not all signals will find an eligible broker.  
**Status:** 🟢 LOW — Working as designed. No action needed.

---

### [INFO] New strategies firing correctly — first signals today
**Time:** 11:29:54 – 11:33:14  
**Detail:** All 3 new strategies generated live signals within minutes of first scan after restart:  
- `rcr_mean_reversion` → NEAR/USD SHORT, LDO/USD SHORT, WLD/USD SHORT, REN/USD LONG, TRUMP/USD SHORT  
- `kds_mean_reversion` → DOT/USD SHORT, ARB/USD SHORT, OP/USD SHORT, LDO/USD SHORT, SAND/USD SHORT, FIL/USD SHORT, AR/USD SHORT, WIF/USD SHORT, MELANIA/USD SHORT, ZRX/USD SHORT, ANKR/USD SHORT  
- `ema_ribbon_breakout` → JTO/USD LONG  
- `btc_v6_chandelier` → REN/USD LONG  
All signals were generated, passed to ML/filter layer, and processed correctly. ✅

---

### [INFO] DRIFT/USD — Active trade, trailing stop ratcheted
**Time:** 11:25:17 and 11:30:14  
**Log:** `[BREAKOUT FAST-FAIL] DRIFT/USD: P&L +0.44% at 10min >= 0.1% — breakout confirmed, holding`  
`[TRAILING STOP] DRIFT/USD LONG | SL ratcheted #2 $0.0337 → $0.0342 | Locked in +1.02% gain`  
**Detail:** DRIFT/USD long position opened, confirmed as breakout (not false breakout), trailing stop ratcheted twice — gain of +1.02% locked in as of last log entry.  
**Status:** ℹ️ INFO — Trade running normally, stop protecting profit.

---

### [INFO] Market sentiment — BULLISH this morning
**Time:** 11:33:34  
**Log:** `[SNAPSHOT] SPY +0.39% | QQQ +0.42% | 9/9 sectors green | lead=Semiconductors | lag=Consumer Staples`  
`Morning briefing complete: conviction=72 sentiment=BULLISH allow_trading=True top_risk=28`  
**Detail:** All 9 sectors green, conviction 72/100, allow_trading=True. Strong bullish open. (Note: Sunday — US markets closed, this is crypto-only sentiment based on ETF proxies.)

---

### [INFO] Bot restart — 27 strategies loaded cleanly
**Time:** 11:24:37  
**Log:** `Strategy engine loaded: 19 enabled, 8 disabled`  
**Detail:** Clean startup, all 27 strategies registered. pll_cycle_martingale confirmed disabled in DB at 11:27:46.

---

## SUMMARY TABLE

| # | Finding | Priority | Auto-Resolved |
|---|---------|----------|---------------|
| 1 | FundingScanner Coinbase — no price in payload, ALL signals rejected | 🔴 HIGH | ❌ No |
| 2 | Bybit API 403 Forbidden — funding rate fetch failing | 🔴 HIGH | ❌ No |
| 3 | Massive.com 429 on every morning snapshot | 🟡 MEDIUM | ❌ No (fallback works) |
| 4 | IBKR clientId 2 collision on restart | 🟡 MEDIUM | ✅ Auto-fallback to clientId 3 |
| 5 | Price sanity glitch — ZRO/USD near-zero price feed | 🟡 MEDIUM | ✅ Sanity check skipped correctly |
| 6 | Structural stop wrong side of fill — percent fallback used | 🟢 LOW | ✅ Fallback working |
| 7 | ENJ/USD short blocked — not margin-eligible | 🟢 LOW | ✅ By design |
| 8 | New strategies (kds/rcr/ema_ribbon/btc_v6) firing live | ℹ️ INFO | ✅ Working correctly |
| 9 | DRIFT/USD long — +1.02% locked, trailing stop active | ℹ️ INFO | ✅ Running normally |
| 10 | Morning sentiment BULLISH 72/100, 9/9 sectors green | ℹ️ INFO | ✅ |

---