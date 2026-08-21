# EAT Strategy — Draft Spec

**Status:** DRAFT / concept only — recovered from notes typed in `MimjaTrderATM.txt` on
2026-07-24 that were never saved, plus a Claude chat the same night where the rules were
being clarified. Reconstructed from Pieces LTM (OCR + conversation capture). Fill in the
`[ ]` gaps below and correct anything the OCR/recall got wrong before this goes anywhere
near code.

Source of the idea: a seminar you took on 2026-07-24.

## Instruments

- MNQ (Micro Nasdaq) — 50 cents/tick
- MGC (Micro Gold)
- MES (Micro S&P) — $1/tick

`[MNQ ]` Confirm which of these it's actually meant to trade — notes list all three but don't
pin down one, or whether it's meant to run on all simultaneously.


## Trade times
- NY Time begin at 5am PST/8am EST, run for an hour after collectig openg cadle so till 605 to 615 PST**
- Tokyo Time - Run  new run at 230PM PST (90 miute before tokyo market opens) no dayliht savings so always that time
- London Time - Run a new run at 10:30 PM PST (90 before lodnon opens at 12am PST) During daylight savings start at 11:30PM PST instead


## Setup — "the box"

1. **Inner box:** high and low of the first 5 minute candle at **5:00 AM PST**, wicks included —
   timeframe is conditional, not fixed:
   - Watch the first **5-min** candle close, and check its range in ticks.
   - Needed range is **100–250 ticks**. Under 100 is too small; over 300 is too big.
   - If the 5-min candle's range is **< 100 ticks** (too small), skip it and instead wait
     for the first **15-min** bar to close, then use that as the inner box.
   - `[ no fall back no trade till nxt session inn that case]` Not stated: if the 15-min bar is *also* under 100 ticks, is there a further
     fallback (30-min?), or do you just not trade that session?
   - `[ No traqdes that session no need to watch 15 arket woo volitle]` Not stated: what happens if the 5-min candle comes in **over 300 ticks** — does
     the session get skipped outright (per the risk filter below), or do you still fall
     back to check the 15-min bar in case it's calmer?
2. Move to the **1-minute chart**.
3. **Outer box:** inner box expanded by a **30-tick buffer** on both sides:
   - Outer high = inner high + 30 ticks
   - Outer low = inner low − 30 ticks
4. **Buffer zone:** the space between the inner box edge and the outer box edge, on both
   the top and the bottom.

## Entry trigger

- Wait for a **1-min candle to close** inside a buffer zone — a wick poking into the zone
  does not count, only a closed candle.
- Close in the **top** buffer zone → go **long**.
- Close in the **bottom** buffer zone → go **short**.

This is a breakout-confirmation-by-close setup (distinct from a plain box breakout —
it's requiring the market to close past the inner box, but still hold inside the buffer
rather than crashing through it, before triggering).

## Stop loss

- **Long:** SL at the bottom of the inner box.
  - Exception: if any wick closed *into* the buffer loqe buffer in the past 20 makesinutes (rather than the
    body), SL goes at that wick's poiny nsdie lower buffer.
- **Short:** mirror image — SL at the top of the inner box, or the wick of aythig closing i the upper buffer last 20 minutes.

`[ ]` Not fully spelled out in the notes: does this SL rule also apply to the outer/opposite
side, or only the side you entered from? Written as the side you entered from.
This is an alway SL rule, bascillay eettig the SL at 120-220 ticks
## Take profit / runner

- **TP1:** close roughly **half of contracts** at a **100-tick gain** beyond the box
  (measured from the **box**, not from the buffer and not from entry price). This locks in
  a chunk of profit early. (Earlier draft said "100 points" — that appears to just mean 100
  ticks; the original notes' own tick-value math right after that line only makes sense in
  ticks.)
  - **Odd-lot split rule** (since 50/50 doesn't divide evenly on odd contract counts): sell
    the ceiling half, keep the floor half —
    - 1 contract → close all at TP1 (no runner).
    - 2 → sell 1, keep 1.
    - 3 → sell 2, keep 1.
    - 4 → sell 2, keep 2.
    - 5 → sell 3, keep 2.
    - Pattern: sell = ceil(n/2), keep = floor(n/2).
- **Runner (remaining 50%):** no fixed TP2. Instead, once price is up 100 ticks (the TP1
  point), arm a **trailing stop in 30 ticks** behind price and let it ride until the trail
  is hit. Treat the tick distance as tunable — backtest before locking a value in.
  - Rationale: keeps the upside of a big move while the TP1 partial has already locked in
    a gain, so the runner can add a lot of extra profit on the trades that run far, without
    needing manual monitoring or a discretionary "first significant drawback" call.
  - Candidate trail distance: **30 ticks**, matching the buffer zone size — picked as a
    reasonable starting guess before charts have actually been reviewed. 10 ticks was the
    first idea but was dropped as likely too tight (routine noise/pullback right after TP1
    fires could stop the runner before it has a chance to run). Still needs real backtesting
    once charts are looked at — 30 is a placeholder, not a validated value.
  - `[ ]` Does the trailing stop only arm after TP1 fires (on the runner half), or does it
    replace the original inner-box SL from the moment of entry?
  - **P&L scenarios**, assuming the 30-tick trail arms once price hits the 100-tick TP1
    point:
    - **Worst case:** 100-tick win on the first 50% (TP1), and the runner's trail gets hit
      almost immediately for a **70-tick win** on the second 50% (100 − 30 = 70 floor,
      not a scratch or a loss).
    - **Best case:** 100-tick win on the first 50%, and the runner's trail doesn't catch up
      to it for a long time — **unlimited** upside on the second 50%.

## Risk filters

- **Needed/valid range for the inner box: 100–250 ticks.**
- **< 100 ticks** → too small — falls back to the 15-min bar (see setup above), doesn't
  invalidate the trade by itself.
- **> 300 ticks** → too big → don't trade the session at all.
- **250–300 ticks** → gray zone carried over from the original notes ("200+, be more
  careful") — still tradeable but size down. Exactly he danger her is still going for 100 tick gain but SL is now
  potentially 200-250 ticks so # of contracts and position size must be limited.
  - `[ 200-250 is still tradabe afrtr 250 call it no trade
  ]` Double-check this band still applies now that the clean 100–250 "needed range"
    has been defined — it may be that 250–300 should just fold into "too big" instead.
- `[ ]` No explicit contract-size formula given for the caution zone — "be more careful"
  wasn't quantified.

## Open questions (unresolved as of last session)

1. ~~5-min vs 15-min bar for the inner box~~ — resolved: conditional on the 5-min candle's
   range, see above. Still open: fallback beyond 15-min if that's also under 100 ticks.
   See notes above
2. Is this a **new standalone MNQ/MGC/MES strategy**, or a modification/variant bolted onto
   the existing EMT setup? The assistant asked this directly and it wasn't answered before
     As this is a fifferent chrt, different time frames it shoulld be it own seperate srtategy however
     it wil shre the scanner tunnele nijatrader  sto o hostimgr for data, and will share code that if
     this indicator is added to any chart in web dash , it will be run on thtt chart and sisplay its buy ell ststus like EMT does
     om the chat if visble. Both EMT a EAT will need to be made idicaor opttios that can be applied
     to the currectly loaded chart and keep ruing using their ruleet even if chart is swapped for another
     to remove the code fro runing the srtat on a symbol youd load tht chart 
     ad remove/ssiable the indicaotor.. so to claify ti will alwy run on MNQ unes unechcked but can also ru on other sybol if 
     added to those chart. EMT needs to be updated to feture the ame behvior but with ES as its default but can be adde t other symbol via charts
     
     the session ended.
3. Do you want this actually built into `trading_bot_v2` next, or just kept as a logged
   concept until it's designed properly (backtest first, etc.)?
   Id like this actualy coded. Ive begu tsting it myweelf maually and had googd success.
4. Entry mechanics: market order right at the 1-min candle close, or next-bar open?
    As soon as 1 miut candle cclose iside buffer open trde no waiting,
5. Session/time filter: does the box only get traded once (the first touch of a buffer
   zone), or can it re-trigger later in the session? No end-of-day/exit-by-time rule noted.
   marked zoe and buffer rmain ttis but it can retriggr by reentring the zone and leaving again within  60 miute ttime frame so 5:05 start 6-5 for
   the NY market.
6. No mention of what happens if price closes through *both* buffer zones without
   triggering (gap moves) — no invalidation rule specified. if no cadle llcoses add candle passes past the buffer sit it out no trade

## Not yet done

- No backtest, no code, no strategy number assigned in `trading_bot_v2`.
- Nothing here has been checked against the 0.62% round-trip fee floor that's killed other
  sub-fee-target strategies (see fee hurdle notes) — TP1 of 100 points on MNQ/MES is likely
  fine on that front given the tick value, but worth checking once instrument is confirmed.
