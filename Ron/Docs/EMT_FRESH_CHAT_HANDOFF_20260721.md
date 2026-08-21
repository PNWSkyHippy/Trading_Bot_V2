# EMT / NinjaTrader Fresh-Task Handoff

Date: 2026-07-21 Pacific Time
User: Ron
Workspace: `C:\Users\Linda\Trading_Bot_V2`

## Immediate instruction for the next task

Continue the EMT/NinjaTrader work from the files on disk. Inspect before editing. Do not recreate completed work, do not start persistent processes, and do not stage, commit, push, or modify unrelated dirty files without Ron's approval.

The previous giant task caused high ChatGPT desktop CPU/memory use. Keep the new task compact and avoid verbose process listings.

## Goal

Build an advisory and automated-paper EMT (Easy Money Trade) strategy around ES futures:

- Use a 610-tick chart/feed.
- Record the 09:30-09:45 ET opening range.
- Require both price and the Keltner midline to break the range.
- Wait for a retracement to the Keltner midline.
- Veto shorts on a current double-bottom/W and longs on a current double-top/M.
- Require a small reversal confirmation after the retracement.
- Paper trade one ES contract with an exact 2-point stop and 2-point target initially.
- Run initially for 60 minutes after the opening range; keep parameters configurable.
- Leave all real order routing absent/disabled.
- forward the NinjaTrader feed securely to Hostinger through an SSH tunnel, without publicly exposing a receiver port.

## Local-only files already created or changed

The root `ninjatrader_bridge/` directory is locally excluded from Git. This is intentional for the home-box prototype.

- `ninjatrader_bridge/emt_strategy.py`
  - Deterministic `EMTStrategyEngine`.
  - States: BUILDING_RANGE, WAIT_BREAKOUT, WAIT_RETRACE, RETRACE_TOUCHED, IN_TRADE, SESSION_DONE.
  - Historical tick bars warm indicators only and cannot create trades.
  - Uses shared pivots from root `chart_patterns.py`, with ES-specific tolerances, only as a current-setup W/M veto.
  - Exact two-point paper bracket and ES point-value calculation.
  - Protects against falsely exiting from pre-entry high/low on the entry bar.
  - If a later bar spans both stop and target, applies pessimistic stop-first handling.
  - Writes a local JSONL paper ledger.
  - Contains no broker/order endpoint.

- `ninjatrader_bridge/ninja_futures_scanner.py`
  - Instantiates EMT from JSON configuration.
  - Sends ES minute bars to the opening-range logic.
  - Adds authenticated `/ingest/emt/bar` for 610-tick bars.
  - Adds EMT state to `/health`, `/snapshot`, and the console summary.

- `ninjatrader_bridge/ninja_futures_config.json`
  - Existing secret was preserved; never print or commit it.
  - Contains the new `emt` block: ES 09-26, 610 ticks, ET market times, one contract, two-point stop/target, 60-minute window, paper-only.

- `ninjatrader_bridge/PythonEMTBridge.cs`
  - Separate NinjaTrader AddOn, market-data only.
  - Initially subscribes to ES 09-26 with 610-tick `BarsRequest`.
  - Sends historical completed bars and throttled live snapshots to local EMT ingestion.
  - Uses an ordered bounded sender queue to avoid asynchronous reordering/thread floods.
  - The `SharedSecret` placeholder must be manually set to the same value as local JSON before installing.
  - Has not yet been compiled inside NinjaTrader.

- `ninjatrader_bridge/EMTStrategyIndicator.cs`
  - Advisory-only indicator; no order or account access.
  - Works on whichever instrument chart it is attached to, but expects a 610-tick chart.
  - Draws Keltner channel/opening range and issues L1 breakout, L2 retracement, and L3 ready alerts.
  - Includes current-setup W/M veto logic.
  - Has not yet been compiled inside NinjaTrader.

- `ninjatrader_bridge/test_emt_strategy.py`
  - Current deterministic Python suite passed 11/11.

## Verification already completed

- Python compilation passed for `emt_strategy.py` and `ninja_futures_scanner.py`.
- Eleven EMT tests passed, covering opening range, dual price/midline breakout, retracement/confirmation, exact bracket, $100 ES target at one contract, same-entry-bar protection, historical-data no-trade behavior, current W veto, old-W exclusion, session ending, malformed OHLC rejection, and ledger OPEN/CLOSE events.

## Next safe work

1. Inspect the five local EMT files and current filesystem state.
2. Add missing symmetry tests: long path, exact -$100 per cotract stop, both-hit stop-first, and near-miss W/M cases.
3. Statically review both C# files for likely NinjaTrader API compile errors.
4. Give Ron exact manual copy/compile steps for NinjaTrader; do not silently install or start it.
5. Note the bot iplementation is t ru on histingerm,now , not later. design the authenticated SSH-forwarded Hostinger receiver. The home PC and NinjaTrader must remain running because Hostinger cannot originate Ninja's licensed feed itself.
   as thee is no unix port of ninja trader available, If not an SSH tunnel of th data from rons hoe pc runing ninja trader the other avenue is direct API calls to 
   mimja trader over the internet bypassing the need to ue the hoe brewed pipelie at all. Eventually this will be placig live trades more then likey via
   ninjarader platform so it will evetually need api acces anyways. for innitial tests howevr jut hovelig the data over sh tto a drop file on hsttinger for hthe bot to paper tradee
   off is sufficient . Disregrd any plans to run this on his computer , he wants it run on hostinger where he was 24 7 uptime, fast internet, spare cpu and memory to spare
   This is for the EMT__srtategy.py implementation where the bot actually places trades werr talking about, the live real time data feed still needs to come 
   from ninjatrader running on Rons pc and the scanner pipeline fetching the data
   



