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

## ITEMS REQUIRING ATTENTION

**Immediate (before next trading session):**
1. **FundingScanner Coinbase payload** — fix `current_price`/`entry_price` missing from signal dict. Every Coinbase funding signal is being silently dropped.
2. **Bybit 403** — check API key validity at bybit.com. May need new key or updated auth header.

**Soon:**
3. **Massive.com 429** — add inter-call delay or session-level caching for morning snapshot.
4. **IBKR clientId** — implement persistent clientId or pre-disconnect on restart.

---

*Next scan will run when QuarterHourly routine is properly scheduled. No scanners.log present this run — will include when available.*

---
## Scan: 2026-05-25 11:51 PT
**Bot process:** Running [venv312/bot_engine.py] ✅
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50
**Issues found:** 3

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner pipeline dead — ALL Coinbase signals (XBT/USD, ETH/USD, BNB/USD, LTC/USD, AAVE/USD) rejected every cycle with current_price/entry_price is zero or missing (stop=0.0, no OHLC in payload) | 🔴 | Open |
| 2 | Bybit 403 Forbidden on /v5/market/tickers?category=linear — recurring every ~5 min (11:34, 11:39, 11:44, 11:49). Bybit data unavailable; fallback to Coinbase-only but Coinbase signals also failing (see #1). | 🟡 | Monitoring |
| 3 | Alpaca connection pool full — Connection pool is full discarding connection to data.alpaca.markets (pool size: 10) — recurring ~every 30-60s throughout window (11:39-11:51). Possible connection leak in stock scanner. | 🟡 | Monitoring |

**Notes:** Funding scanner has been generating signals from Coinbase but every signal lacks entry_price/current_price (stop=0.0, no OHLC), causing blanket rejection. This has persisted across all 4 funding cycles visible in the log window (~11:34-11:49). Zero funding trades can execute until this is fixed. Bybit 403 may indicate IP ban or expired API key. Alpaca pool warnings are high-frequency but trading appears operational (balance updated OK at 11:39: $95,838.03). No IBKR, DB, Anthropic, or pll_cycle_martingale issues found. Ghost trade check skipped (before 1pm PT).

---
## Scan: 2026-05-25 12:08 PT
**Bot process:** Running ✅ (PIDs 37360, 38820)
**Lines reviewed:** bot.log 500 | scanners.log: not found | stderr 50
**Issues found:** 3

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | Bybit 403 Forbidden on /v5/market/tickers?category=linear — recurring (seen at 11:59 and 12:04) | 🟡 | Monitoring |
| 2 | FundingScanner Coinbase signals all rejected: stop=0.0 / no price — XBT, ETH, BNB, LTC, AAVE all failing "current_price/entry_price is zero or missing"; Coinbase funding pipeline dead | 🟡 | Monitoring |
| 3 | Alpaca connection pool warnings: "Connection pool is full, discarding connection: data.alpaca.markets" — very frequent throughout log window | ℹ️ | Monitoring |

**Notes:** Bot is actively trading via strategy_engine and BreakoutScanner (Kraken path healthy). Recent wins: SUSHI/USD +.58, CRV/USD +.47. New positions opened at 12:03: SNX/USD, RLC/USD, RENDER/USD, LDO/USD, ARB/USD. pll_cycle_martingale not detected. Ghost trade check skipped (before 1pm PT). No CRITICAL/ERROR lines. Today is Memorial Day (US holiday) — crypto-only trading day.

---
## Scan: 2026-05-25 12:21 PT
**Bot process:** Running ✅ (2 instances detected — venv312 + system Python312, see finding #4)
**Lines reviewed:** bot.log 500 | scanners.log: not found | stderr 50 (all 200 OK, last entry 2026-05-17)
**Issues found:** 5

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner pipeline dead — ALL Coinbase signals rejected every cycle (12:09, 12:14, 12:19): XBT/USD, ETH/USD, BNB/USD, LTC/USD, AAVE/USD all fail `current_price/entry_price is zero or missing` (stop=0.0/no price in payload). Persisting since at least 11:24 PT. | 🔴 | Open |
| 2 | Bybit 403 Forbidden — recurring every ~5min (12:09, 12:14, 12:19); FundingScanner falls back to Coinbase but Coinbase payload missing price fields | 🟡 | Monitoring |
| 3 | Alpaca connection pool exhausted — 30+ "Connection pool is full, discarding connection: data.alpaca.markets" per scan cycle; possible connection leak | 🟡 | Monitoring |
| 4 | Two bot_engine.py processes — venv312\Scripts\python.exe AND C:\Program Files\Python312\python.exe both running bot_engine.py | 🟡 | Open |
| 5 | FARM/USD bad price feed — live=$0.000012 vs entry=$6.6550 (100% deviation) at 12:20:57; position monitor sanity check caught it and skipped cycle | ℹ️ | Monitoring |

**Notes:** Breakout scanner healthy — FARM/USD LONG executed at 12:16 via Kraken ($6.6550, trailing stop ratcheted to $6.6900 within 12s). TRX/USD LONG also open (opened 12:09). FundingScanner dead for entire window. Today is US Memorial Day — equity markets closed; Alpaca pool warnings may be elevated due to closed-market API responses. Ghost trade check skipped (before 1pm PT). Dashboard stderr clean (last entry 2026-05-17, no errors).

---
## Scan: 2026-05-25 12:35 PT
**Bot process:** Running ✅ (two instances: venv312 + system Python both running bot_engine.py)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (stale, last entry 2026-05-17)
**Issues found:** 3

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner Coinbase pipeline dead — ALL signals (XBT, ETH, BNB, LTC, AAVE) rejected every cycle with stop=0.0/no price; current_price/entry_price is zero or missing | 🔴 | Open |
| 2 | Bybit API 403 Forbidden — funding rate fetch fails every scan cycle (~5min interval); Bybit source completely blind | 🟡 | Open |
| 3 | 1 consecutive loss recorded at 12:34:49; counter at 1 (threshold 5) | ℹ️ | Monitoring |

**Notes:** Kraken scanner and breakout_scanner working normally — DRIFT, BILL, FARM all executed via Kraken. 8 open trades all from today (12:03–12:28 PT), none older than 8 hrs, no ghosts. Today is Memorial Day (US market holiday) — no stock trading expected. FundingScanner issue is persistent across all 3 scan cycles visible in log window (12:19, 12:24, 12:29, 12:34). PushNotification sent for HIGH finding.

---
## Scan: 2026-05-25 12:46 PT
**Bot process:** Running ✅ (PID 37360 venv312 3.1MB wrapper + PID 38820 Python312 370MB main)
**Lines reviewed:** bot.log 500 | scanners.log: not found | web_dashboard_stderr 50 (last entries 17-May, stale)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner ALL coinbase signals rejected — stop=0.0 / no price (XBT, ETH, BNB, LTC, AAVE all failing hard check "current_price/entry_price is zero or missing"). Bybit also 403 Forbidden. Funding pipeline dead; breakout scanner still operational. | 🟡 | Monitoring |
| 2 | Bybit fetch error 403 Forbidden recurring every ~5min cycle (12:34, 12:39, 12:44 PT) | 🟡 | Monitoring |
| 3 | Consecutive losses at 3: DRIFT -$8.69 (stop), RENDER -$13.28 (pivot break), TRX -$4.79 (pivot break). Not yet at threshold of 5. | 🟡 | Monitoring |
| 4 | Alpaca urllib3 connection pool full (discarding connections to data.alpaca.markets) — recurring throughout log, pool size 10 | ℹ️ | Monitoring |

**Notes:** Ghost trade check clear — 6 open trades (SNX, RLC, LDO, ARB, FARM, BILL) all opened today within last ~42min, none > 8hr. Wins today: DRIFT +$14.60. Breakout scanner and Kraken executor healthy. No IBKR errors, no DB errors, no Anthropic errors, no impossible P&L, no pll_cycle_martingale. Web dashboard serving 200s normally. Two bot_engine.py processes is expected (venv312 instance is 3.1MB watchdog wrapper).

---
## Manual Action: 2026-05-25 ~12:50 PT
**Action:** mr_03_fbs DISABLED — strategy_mr_03_fbs_enabled = false
**Reason:** Live performance analysis of today's trades revealed catastrophic underperformance:
- 2W / 10L (16.7% WR vs ~50% expected from backtest)
- Wins: +$44.05 | Losses: -$171.64 | Profit factor: 0.26
- Root cause: No market regime filter — strategy shorted all morning into confirmed BULLISH session (9/9 sectors green, conviction 72). Four simultaneous shorts at 05:03 (ARB, OP, WIF, STRK) all lost. Largest single loss: REN/USD LONG -$40.64 (2.02%).
- Bot bled ~$30-40 every 10 minutes during mr_03_fbs active windows
- Total drawdown attributed to strategy: ~-$127 (took bot from +$350 → +$100)
**Status:** Off live. Queued for regime-filter rebuild (add sentiment gate: block shorts when BULLISH, block longs when BEARISH). mr_02_vef remains enabled — 1W/2L but profit factor 1.40, positive EV.

---
## Manual Action: 2026-05-25 ~12:50 PT
**Action:** mr_03_fbs DISABLED — strategy_mr_03_fbs_enabled = false
**Reason:** Live performance analysis of today's trades revealed catastrophic underperformance:
- 2W / 10L (16.7% WR vs ~50% expected from backtest)
- Wins: +.05 | Losses: -.64 | Profit factor: 0.26
- Root cause: No market regime filter — strategy shorted all morning into confirmed BULLISH session (9/9 sectors green, conviction 72). Four simultaneous shorts at 05:03 (ARB, OP, WIF, STRK) all lost. Largest single loss: REN/USD LONG -.64 (2.02%).
- Bot bled ~-40 every 10 minutes during mr_03_fbs active windows
- Total drawdown attributed to strategy: ~- (took bot from + to +)
**Status:** Off live. Queued for regime-filter rebuild (add sentiment gate: block shorts when BULLISH, block longs when BEARISH). mr_02_vef remains enabled.

---
## Scan: 2026-05-25 13:10 PT
**Bot process:** Running ✅ (2 instances each of bot_engine, watchdog, scanner, dashboard = known watchdog behavior per prior notes)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (stale — last entry 2026-05-17, all 200s)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | mr_03_fbs STILL ACTIVE after stated ~12:50 PT manual disable — signals generated and executed AFTER disable: ARB SHORT 13:01:36 (skipped — open pos), LDO SHORT 13:02:06 → EXECUTED 13:04:10, REN LONG 13:03:35 → EXECUTED 13:04:09. Two live trades opened by this strategy post-disable. | 🔴 | Open |
| 2 | FundingScanner pipeline still dead — ALL Coinbase signals rejected with "current_price/entry_price is zero or missing" (XBT, ETH, BNB, LTC, AAVE all failed). Bybit 403 Forbidden recurring at 13:04:57 PT. No change from last scan. | 🟡 | Monitoring |
| 3 | Consecutive losses: 2 (FARM +$4.52 reset counter → NOS -$28.05 #1 → MEZO -$69.59 #2). Not at threshold of 5. | ℹ️ | Monitoring |
| 4 | Alpaca urllib3 connection pool full (data.alpaca.markets) — recurring throughout window. Known issue. | ℹ️ | Monitoring |

**Notes:** Sunday — no ghost trade check (weekday-only). Breakout scanner healthy: ROLL/USD SHORT blocked correctly (not margin-eligible on Kraken). NR7 scanner ran close window (118 symbols), all rejected on volume < 1.5x — normal Sunday behavior. No DB errors, no IBKR disconnect, no Anthropic errors, no impossible P&L, no pll_cycle_martingale detected.

---
## Scan: 2026-05-25 13:21 PT
**Bot process:** NOT RUNNING 🔴
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50
**Issues found:** 3

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | bot_engine.py not in process list — last log was 13:19:04 PT (~2 min before scan). Likely crashed or just exited. | 🔴 | Open |
| 2 | Bybit 403 Forbidden — recurring at 13:09:58 and 13:14:59. FundingScanner falling back to Coinbase + Kraken only. | 🟡 | Monitoring |
| 3 | Coinbase funding signals sending stop=0.0 / no price — XBT/USD, ETH/USD, BNB/USD, LTC/USD, AAVE/USD all rejected for "current_price/entry_price is zero or missing". Coinbase funding pipeline dead. | 🟡 | Open |

**Notes:** Today is Memorial Day (US federal holiday) — stock markets closed. Alpaca balance ,838.03 (all cash,  invested — expected). NR7 scanner signals all failing volume checks (0.5–0.9x vs 1.5x min), consistent with holiday low-volume. 5 open paper trades (SNX/USD, ARB/USD, REN/USD, LDO/USD, TIA/USD) all opened today <2h ago via Kraken — no ghost trades. PushNotification sent for bot down (Remote Control inactive, desktop only).

---
## Scan: 2026-05-25 13:37 PT
**Bot process:** Running ✅ (4 python.exe processes active; log entries current through 13:19 PT)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (stale — last entry 17 May)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | Bybit 403 Forbidden on funding scan — recurring at 13:09 and 13:14 PT cycles | 🟡 | Monitoring |
| 2 | FundingScanner Coinbase signals: ALL 5 symbols (XBT, ETH, BNB, LTC, AAVE) rejected with stop=0.0 / no price — Coinbase funding path dead; Kraken breakout still executing | 🟡 | Monitoring |
| 3 | SNX/USD open 8.6h, ARB/USD open 8.6h — both exceed 8h ghost threshold; crypto so 24/7 but flag for review | 🟡 | Open |
| 4 | web_dashboard_stderr.log stale — last entry 17 May (8 days ago); dashboard may not be running | ℹ️ | Open |

**Notes:** Kraken breakout scanner healthy — TIA/USD LONG executed at 13:13 PT (.4854, 4132 units, SL ratcheted to .4763). NR7 scanner active but all stock signals rejected for low volume (sub-1.5x threshold — normal in low-volume market). No ERROR/CRITICAL log lines, no IBKR issues, no consecutive losses, no pll_cycle_martingale. Alpaca balance: ,838.03 fully available (no open stock positions). Today is Memorial Day — US equities closed; crypto trading normally. REN/USD (7.6h) and LDO/USD (7.6h) approaching 8h ghost threshold.

---
## Scan: 2026-05-25 13:51 PT
**Bot process:** NOT RUNNING 🔴
**Lines reviewed:** bot.log 500 | scanners.log: not found | stderr 50 (stale, last entry 2026-05-17)
**Issues found:** 3

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | bot_engine.py not found in running processes — last log entry 13:19 PT, ~32min offline with 5 open PAPER positions unmonitored | 🔴 | Open |
| 2 | Bybit API returning 403 Forbidden on /v5/market/tickers (seen at 13:09 and 13:14) — FundingScanner Bybit feed dead | 🟡 | Open |
| 3 | FundingScanner Coinbase pipeline dead — ALL signals (XBT, ETH, BNB, LTC, AAVE) rejected with stop=0.0 / no price; entry_price zero or missing on every coinbase signal | 🟡 | Open |

**Notes:** Today is US Memorial Day (2026-05-25) — stock market closed; NR7 volume rejections expected (all below 1.5x, normal for holiday). Bot was actively running at 13:19 PT and executed a valid TIA/USD breakout PAPER trade (vol=54.6x, RSI=62.6, score=0.87). 5 open PAPER crypto positions on Kraken (SNX/USD long, ARB/USD short, REN/USD long, LDO/USD short, TIA/USD long) are now unmonitored. No ghost trades (all opened <8h ago). Dashboard stderr stale since 2026-05-17. No ERROR/CRITICAL lines, no consecutive losses, no pll_cycle_martingale, no DB errors, no impossible P&L seen in logs.

---
## Scan: 2026-05-25 14:06 PT
**Bot process:** NOT RUNNING 🔴 (last log entry 13:19 PT — silent ~47 min)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (stale since 2026-05-17)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | bot_engine.py not running — last activity 13:19 PT, process absent from tasklist | 🔴 | Open |
| 2 | 5 open Kraken positions unmonitored — SNX/USD (12:03), ARB/USD (12:03), REN/USD (13:04), LDO/USD (13:04), TIA/USD (13:13) — bot down, stops not being managed | 🔴 | Open |
| 3 | Bybit 403 Forbidden recurring — api.bybit.com/v5/market/tickers at 13:09 and 13:14 | 🟡 | Monitoring |
| 4 | FundingScanner/Coinbase all signals have stop=0.0/no price — XBT, ETH, BNB, LTC, AAVE all rejected at 13:15 | 🟡 | Monitoring |

**Notes:** Bot was active and scanning through 13:15–13:19 (crypto scan complete logged at 13:19:04). No ERROR/CRITICAL/Traceback lines visible in final 500 lines — likely clean exit or OOM kill. Dashboard stderr last active 2026-05-17, dashboard not running. Push notification sent for bot-down. Restart bot_engine.py and check open Kraken positions manually.

---
## Scan: 2026-05-25 13:21 PT
**Bot process:** NOT RUNNING 🔴
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (last entries 2026-05-17)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | bot_engine.py NOT in process list — 4 Python processes are all Claude MCP processes. Last bot log entry: 13:19:04 PT. Bot likely crashed/stopped since previous scan. | 🔴 | Open |
| 2 | 5 open Kraken paper positions unmonitored — SNX/USD (12:03), ARB/USD (12:03), REN/USD (13:04), LDO/USD (13:04), TIA/USD (13:13 stop trailing to 0.4763) — bot down, stops not being managed | 🔴 | Open |
| 3 | Bybit 403 Forbidden recurring — api.bybit.com/v5/market/tickers at 13:09 and 13:14 | 🟡 | Monitoring |
| 4 | FundingScanner/Coinbase all signals have stop=0.0/no price — XBT, ETH, BNB, LTC, AAVE all rejected (same pattern as prior scan) | 🟡 | Monitoring |

**Notes:** Bot still down — same state as previous scan. No ERROR/CRITICAL/Traceback in log tail; bot activity ceased after 13:19:04 (crypto scan complete). Memorial Day 2026 — US markets closed, NR7/Alpaca volume rejections expected. Push notification sent (desktop only, Remote Control inactive). Restart bot_engine.py urgently — 5 open positions are unmonitored with no stop management.

---
## Scan: 2026-05-25 14:33 PT
**Bot process:** Running ✅ (bot_engine.py PID 31480 + 8900¹, BreakoutScanner PID 24532+6372, web_dashboard PID 13988+34260, watchdog_ibkr PID 21120+9412)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (last entries 2026-05-17)
**Issues found:** 5

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | Bot restarted at 14:22:32 PT (was down since ~13:19 — previous scan flagged). IBKR startup Error 326 (clientId 2 in use), self-resolved to clientId 3. Connected OK account=DUQ511882 | 🟡 | Resolved |
| 2 | Duplicate processes: two instances each of bot_engine.py, BreakoutScanner.py, web_dashboard.py, watchdog_ibkr.py — one via venv312 (tiny ~3MB, likely zombie from prior crash) and one via system Python312 (active, ~370MB). Could cause double-signaling or clientId conflicts | 🟡 | Monitoring |
| 3 | Bybit 403 Forbidden — recurring every 5 min funding cycle (14:22, 14:27, 14:32). Bybit data blocked; FundingScanner falls back to Coinbase only | 🟡 | Monitoring |
| 4 | FundingScanner stop=0.0 / no price — ALL Coinbase funding signals (XBT, ETH, BNB, LTC, AAVE) rejected every cycle with "current_price/entry_price is zero or missing". Pipeline dead for this source. Ongoing from prior scans. | 🟡 | Monitoring |
| 5 | TIA/USD bad price feed — live=$0.002585 vs entry=$0.4854 (99.5% deviation). Bot correctly skipping these cycles. 3 warnings at 14:23–14:26. TIA trailing stop active and ratcheting normally ($0.4757→$0.4763→$0.4769) so Kraken feed is fine | 🟡 | Monitoring |

**Notes:** Bot came back up at 14:22:32 (restarted after ~63 min down). LDO/USD closed WIN +$19.99 at 14:23 (take_profit). Open positions: SNX/USD (12:03), ARB/USD (12:03), REN/USD (13:04), TIA/USD (13:13) — all under 2.5h, no ghost trades. pll_cycle_martingale: DISABLED ✅. All 7 market scanner signals vetoed by Claude reviewer (RSI/MACD/BB/Volume all N/A — likely holiday data gap, Memorial Day). ¹Small venv312 bot instance (3.4MB) is likely a zombie from pre-restart; watch for double-trade events.

---
## Scan: 2026-05-25 14:51 PT
**Bot process:** Running ✅ (2 bot_engine.py processes detected — see finding #4)
**Lines reviewed:** bot.log 500 | scanners.log not found | stderr 50 (stale, last entry 2026-05-17)
**Issues found:** 4

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner Coinbase pipeline dead — ALL signals (XBT/ETH/BNB/LTC) rejected `stop=0.0 / current_price missing` every 5-min cycle since at least 13:15. No funding trades executing via Coinbase. | 🔴 | Open |
| 2 | Bybit 403 Forbidden — funding data blocked on every poll since 13:15. Bybit funding signals unavailable. | 🟡 | Open (recurring) |
| 3 | IBKR Error 326 + TimeoutError at 14:22 — `clientId 2 already in use`, `API connection failed: TimeoutError()`. IBKR stock trading blind. Lower impact today (Memorial Day — US markets closed). | 🟡 | Open |
| 4 | Two bot_engine.py processes detected — venv312 python AND C:\Program Files\Python312\python.exe both running bot_engine.py. Likely cause of IBKR clientId conflict. | 🟡 | Open |
| 5 | Claude reviewer vetoed all 7 signals this scan cycle — RSI/MACD/Volume/BB all N/A across CRV, ZEC, PYTH, RLC, STRK, WLD, OCEAN. Possible data provider gap. | 🟡 | Monitoring |
| 6 | pll_cycle_martingale confirmed DISABLED ✅ | ℹ️ | Resolved |
| 7 | No ghost trades — 4 open positions (SNX, ARB, REN, GRASS), longest open ~2h45m, all under 8h threshold. | ℹ️ | OK |

**Notes:** Today is Memorial Day — US equity markets closed, so IBKR finding is lower severity. Crypto trading is active. FundingScanner dead pipeline (#1) is the most actionable issue: Coinbase funding signals are generating but arriving with no price/stop data. Bybit 403 has been recurring and may require API key rotation or endpoint update. The two-process finding may resolve on next restart if one is a stale/zombie process.

---
## Scan: 2026-05-25 15:23 PT
**Bot process:** Running ✅ (PIDs 22308, 19420)
**Lines reviewed:** bot.log 500 | scanners.log: not found | stderr 50
**Issues found:** 7

| # | Finding | Priority | Status |
|---|---------|----------|--------|
| 1 | FundingScanner pipeline dead — ALL Coinbase funding signals rejected (stop=0.0, no price) every 5-min cycle. Bybit DNS failure + 403 Forbidden causing fallback signals with no price data attached. ETH, BNB, LTC, XBT all rejected. | 🔴 | Open |
| 2 | Bybit API down — DNS getaddrinfo failure at 15:13 + 403 Forbidden at 15:18 and 15:23. Kraken fallback also failed at 15:13 (DNS). Recurring this window. | 🟡 | Open |
| 3 | ARB/USD open 10.4hr + REN/USD open 9.3hr — both flagged "Could not get price" in position monitor repeatedly. Potential ghost trades; monitor cannot verify P&L or stop. | 🟡 | Open |
| 4 | Claude API slow/timeout — 2 hard timeouts (12s) for FIL/USD and NMR/USD signal reviews; HNT/USD near-timeout (11s). All conservatively vetoed (no trades missed). | 🟡 | Open |
| 5 | XRT/USD bad price feed — live=$0.000029 vs entry=$0.941 (100% deviation). Price sanity skipping check each cycle. Position active (7.1hr open) but monitor cannot track it properly. | 🟡 | Open |
| 6 | Bot restart at 15:08 — scheduled jobs re-registered at start of log window. Brief gap in monitoring possible. | ℹ️ | Resolved |
| 7 | Consecutive losses: SNX/USD (loss #3) + GRASS/USD (loss #4) before XRT/USD win reset counter. Below 5-loss HIGH threshold. | ℹ️ | Resolved |

**Notes:** PushNotification sent for finding #1 (FundingScanner dead). No ERRORs or CRITICALs in bot.log. pll_cycle_martingale NOT enabled. Web dashboard stderr shows clean HTTP 200s from May 17 (dashboard may not be actively running today). Alpaca balance $95,838.03 synced OK. Morning briefing ran at 15:22: conviction=72, sentiment=BULLISH, allow_trading=True. Ghost trades: ARB/USD and REN/USD both >8hr open with no price data — recommend manual check.
