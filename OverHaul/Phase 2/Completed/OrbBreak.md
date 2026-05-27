This one is the most audited and evidence-backed strategy in the entire batch — which makes it both easier to evaluate and more trustworthy than most.

My read on ORB Breakout
Overall verdict: Incubate/Candidate — best documented strategy in the batch, minimal fixes needed
Issues I found
Critical — 1) Not registered
Same as every other strategy.

Critical — 2) Not in TIME_STOP_EXEMPT — this one actually matters
For crypto ORB on 15m bars with a 3R target:

HARD_STOP_BARS = max(1, round(8.0 * bph)) at 15m = 8h × 4 bars/h = 32 bars = 8 hours
BTC at 3R with a structural ORB stop can easily take 8-20+ hours
The audit actually noted this: "Winners avg 1,340 bars (14 days!) in bear"
So a 32-bar generic hard stop will kill many valid 3R target trades before they complete.

This is a real distortion not just a cosmetic issue.

Critical — 3) preferred_initial_stop_mode and preferred_trail_mode missing from metadata
Both signals return structural_stop_price in metadata but neither declares:

"preferred_initial_stop_mode": "signal_structural",
"preferred_trail_mode":        "none",
The executor may not apply the structural stop correctly without these hints.

Important — 4) reviewer_exempt not set
Important — 5) ml_exempt and auto_disable_exempt likely not real framework fields
self.ml_exempt = True
self.auto_disable_exempt = True
Check base_strategy.py. If auto_disable_exempt is not defined there, it silently does nothing and the engine may still auto-disable based on historical poor WR.

Important — 6) ETH exclusion is defined inline instead of module-level
_ETH_EXCLUDED = {"ETHUSDT", "ETH-USDT", "ETHBUSD", "ETH/USDT"}
This is inside analyze(). Should be a module-level constant for visibility. Also may be missing ETH/USD format used by Kraken.

Important — 7) No check_custom_exit() — but VWAP exit is in backtester
The backtester already has:

if exit_reason is None and strategy_name == "orb_breakout":
    exit_reason = _bt_orb_vwap(df, i, trade)
So the VWAP cross exit is handled externally. However, there is no check_custom_exit() defined in the strategy itself.

For live execution, position_monitor._check_orb_vwap_exit() must exist. If it doesn't, live trades will hold until SL/TP only.

Minor — 8) stop_loss_pct = 1.5 and take_profit_pct = 3.2 at class level conflict with per-signal structural values
The class says these are v3 matrix sweep optimums. But the actual per-signal sl_pct and tp_pct are computed from structural ORB risk:

sl_pct = (risk / current_close) * 100
tp_pct = ((target_price - current_close) / current_close) * 100
The class-level values are fallbacks that may or may not match structural values. Add a comment clarifying they're overridden per signal.

Minor — 9) _ETH_EXCLUDED is missing some common formats
Current set:

{"ETHUSDT", "ETH-USDT", "ETHBUSD", "ETH/USDT"}
Missing: "ETH/USD" (Kraken format).

What is genuinely good
Best audit documentation in the entire batch — 5 iterations with explicit hypothesis, evidence, and decision trail
Structural stop is correctly computed from actual ORB risk
ETH exclusion is evidence-based and documented
Crypto short disable is evidence-based — not just a flag flip
EMA200 regime gate properly implemented
VWAP implementation is correct (cumulative reset per session)
Session bar handling with timezone normalization is solid
Whitelist toggle with configurable mode
Full metadata including all breakout-specific fields
logger.info() for signals and logger.debug() for skips is correct
Claude patch prompt
Patch strategies/orb_breakout.py and register it in the bot framework.

This strategy is the most audited in the batch. Fixes are targeted.
Do NOT change any entry logic, filters, or parameter values.
Do NOT change the ETH exclusion or crypto short disable.
Do NOT change the whitelist behavior.

Files to inspect and patch:
- strategies/orb_breakout.py
- intelligence/backtester.py
- strategies/strategy_engine.py
- strategies/base_strategy.py (inspect: reviewer_exempt, ml_exempt, auto_disable_exempt)
- core/position_monitor.py (inspect: whether _check_orb_vwap_exit exists for live parity)

========================================================
REQUIRED FIXES — IN PRIORITY ORDER
========================================================

1) Register in backtester.py strategy_map
Add if not already present:
    "orb_breakout": ("strategies.orb_breakout", "ORBBreakout"),

2) Register in strategy_engine.py
Add if not already present:
    from strategies.orb_breakout import ORBBreakout
    ORBBreakout(),

3) Add orb_breakout to TIME_STOP_EXEMPT in backtester.py
This is important for ORB — not just a standard registration fix.

Context: BTC crypto ORB targets 3R on 15m bars.
Backtester hard stop fires at 8h (32 bars on 15m).
Many valid 3R-target trades take longer than 8 hours.
The hard stop is killing winning trades before they hit target.

Add to TIME_STOP_EXEMPT:
    "orb_breakout",

4) Add preferred_initial_stop_mode and preferred_trail_mode to both signals
Both the long and short signal metadata blocks need these:

    "preferred_initial_stop_mode": "signal_structural",
    "preferred_trail_mode":        "none",

The structural_stop_price is already present — these hints tell the executor
to use it. Without them, the executor may default to percent-based behavior.

5) Add reviewer_exempt flag
Inspect base_strategy.py to confirm reviewer_exempt is a real field.
If yes, add to __init__:
    self.reviewer_exempt = True

6) Verify ml_exempt and auto_disable_exempt
Inspect base_strategy.py.

If ml_exempt is not defined there:
- Remove self.ml_exempt = True

If auto_disable_exempt is not defined there:
- Add it as a recognized field in base_strategy.py with a default of False
  OR remove it from orb_breakout.py and document the concern in a comment

The intent of auto_disable_exempt is important:
The engine reads old WR history and would auto-disable the strategy based on
pre-audit data with 44.3% WR. If this flag cannot be honored by the engine,
the comment must explain what the user should do manually (clear old trade
history or raise the WR threshold).

Do not silently remove auto_disable_exempt without addressing the underlying
risk it was created to protect against.

7) Move ETH exclusion to module-level constant and add missing formats
Current (inline in analyze):
    _ETH_EXCLUDED = {"ETHUSDT", "ETH-USDT", "ETHBUSD", "ETH/USDT"}

Move to module level (after imports):
    # ETH excluded after 5-iteration audit — no ORB edge found on ETH
    # 00:00 UTC ORB stalls at 2R and mean-reverts; negative expectancy at 3R target
    ETH_ORB_EXCLUDED = {
        "ETHUSDT", "ETH-USDT", "ETHBUSD",
        "ETH/USDT", "ETH/USD",   # add Kraken format
    }

Update the check in analyze() to use ETH_ORB_EXCLUDED.

8) Clarify class-level stop_loss_pct and take_profit_pct
Current:
    self.stop_loss_pct   = 1.5   # v3 matrix sweep optimum 2026-05-25
    self.take_profit_pct = 3.2   # v3 matrix sweep optimum 2026-05-25

These are overridden per-signal by the structural sl_pct/tp_pct computed
inside analyze(). Add a comment making this explicit:

    self.stop_loss_pct   = 1.5   # fallback only — overridden per-signal by structural ORB stop
    self.take_profit_pct = 3.2   # fallback only — overridden per-signal by structural ORB risk × R_MULT

9) Verify live VWAP exit parity
The backtester has:
    if exit_reason is None and strategy_name == "orb_breakout":
        exit_reason = _bt_orb_vwap(df, i, trade)

Inspect core/position_monitor.py to confirm whether _check_orb_vwap_exit()
or equivalent exists for the live path.

If it does not exist:
- Add it following the same logic as _bt_orb_vwap in backtester.py
- Only fires for trades where indicators["strategy_name"] == "orb_breakout"
- VWAP computed as session cumulative (reset at midnight UTC for crypto)
- Long: close < VWAP → exit
- Short: close > VWAP → exit

If it already exists:
- Confirm it uses the same session-anchored VWAP logic (not a rolling VWAP)
- Add a comment confirming parity with backtester

This is important: if live VWAP exit is missing, live ORB trades hold
until SL/TP while backtest exits on VWAP cross — creating drift.

========================================================
DO NOT CHANGE
========================================================

- Entry logic (all 9 conditions for long)
- ETH exclusion decision
- Crypto short disable decision
- EMA200 regime gate (crypto only — Iter5)
- Whitelist behavior (USE_WHITELIST toggle)
- Vol filter values (1.2x stock, 1.5x crypto)
- R_MULT values (2.0 stock, 3.0 crypto)
- ORB bar counts (6 stock, 4 crypto)
- Structural stop at orb_low/orb_high
- Session VWAP implementation
- All parameter constants
- Strategy audit comments and changelog

========================================================
VALIDATION
========================================================

Compile:
python -m py_compile strategies/orb_breakout.py

Run BTC crypto (primary validated symbol):
python intelligence/backtester.py --symbol BTC/USD \
    --strategy orb_breakout --days 59 --tf 15m \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Target: results should be consistent with audit findings
- PF around 1.4-1.5
- WR around 60-65%
- Sharpe around 1.5+

Run SOL (secondary validated symbol):
python intelligence/backtester.py --symbol SOL/USD \
    --strategy orb_breakout --days 59 --tf 15m \
    --asset-class crypto \
    --initial-stop signal_structural --trail-stop none

Confirm ETH is silently excluded:
python intelligence/backtester.py --symbol ETH/USD \
    --strategy orb_breakout --days 30 --tf 15m \
    --asset-class crypto
(should produce zero trades or explicit exclusion log)

Run stock basket:
python intelligence/backtester.py --all \
    --strategy orb_breakout --days 30 --tf 5m \
    --asset-class stock \
    --initial-stop signal_structural --trail-stop none

Exit reason check:
- stop_loss and take_profit should appear
- vwap_cross should appear (from _bt_orb_vwap in backtester)
- eod_close may appear for stocks
- Generic lifecycle stops should NOT dominate
  (if hard_time_stop appears frequently, TIME_STOP_EXEMPT was not applied)

Key verification — TIME_STOP_EXEMPT effect:
Before fix: hard_time_stop would kill BTC trades before 3R target
After fix: trades should hold to SL/TP/VWAP exits only

Deliverables:
1. Patched strategy file
2. Patched backtester.py (TIME_STOP_EXEMPT + registration)
3. Patched strategy_engine.py
4. Position monitor VWAP exit status (exists / added / confirmed parity)
5. BTC and SOL validation results — comparison to audit findings
6. ETH exclusion confirmation (zero trades)
7. Final classification: Watchlist / Incubate / Candidate
My pre-patch classification
Concept: solid — ORB is a well-established institutional strategy
Code quality: best in the batch for session handling and audit documentation
Implementation completeness: 88% — registration and metadata hints are the gaps
Evidence base: best in the batch — 5 iterations, explicit WR/PF/Sharpe, OOS robustness test
Salvageable: yes — already the most complete
Candidate potential — if the post-patch BTC results reproduce the audit findings (PF ~1.5, Sharpe ~1.59), this is the closest to production-ready of everything you've shown.

The TIME_STOP_EXEMPT fix is the most strategically important one here because it's actively distorting backtest results for the intended 3R target.