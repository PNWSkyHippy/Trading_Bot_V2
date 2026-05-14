Patch intelligence/claude_reviewer.py.

Problem The current morning briefing asks Claude to assess market conditions without supplying enough real structured market data. That makes the reviewer too narrative-driven and not grounded enough for autonomous trading decisions.

We now have access to Massive.com API. Use it to build a deterministic morning market snapshot and feed that snapshot into Claude.

Goal Claude should no longer invent market context. Instead:

Python gathers real market data from Massive.com
claude_reviewer builds a structured snapshot
Claude interprets that snapshot into a morning briefing JSON
Required changes

Add a Massive.com market snapshot layer Create helper methods inside ClaudeReviewer to fetch recent aggregate bars from Massive.com for a small fixed market basket.
Use these symbols at minimum:

SPY
QQQ
IWM
DIA
Also include sector ETFs if data is available:

XLK
XLF
XLE
XLV
XLI
XLY
XLP
XLU
Implementation:

add a helper like _massive_headers() using config.MASSIVE_API_KEY or env fallback
add _fetch_massive_bars(symbol: str, multiplier: int = 5, timespan: str = "minute", lookback_days: int = 5)
use Massive.com aggregates endpoint
return clean ascending bars with open/high/low/close/volume/timestamp
safe fallback: return empty list on any error
Build a deterministic market snapshot Add a helper like:
_build_market_snapshot() -> Dict
It should compute, where possible:

spy_day_change_pct
qqq_day_change_pct
iwm_day_change_pct
dia_day_change_pct
spy_5d_change_pct
qqq_5d_change_pct
iwm_5d_change_pct
dia_5d_change_pct
breadth_up_count
breadth_down_count
strongest_sector
weakest_sector
sector_changes: dict of ETF -> pct change
market_regime_guess based on numeric facts only:
bullish / bearish / mixed / risk_off / risk_on
data_quality_ok boolean
snapshot_summary string built from facts, not AI
Use simple rules:

day change = last close vs first open of current session if available
5d change = latest close vs earliest close in fetched bars
breadth = how many of SPY/QQQ/IWM/DIA are positive on the day
strongest/weakest sector = highest/lowest daily pct among sector ETFs
risk_on example: SPY and QQQ positive, breadth >= 3
risk_off example: SPY and QQQ negative, breadth <= 1
mixed otherwise
If Massive data is missing or incomplete:

set data_quality_ok = False
fill conservative defaults
Feed the snapshot into the morning briefing prompt In _run_morning_briefing():
call _build_market_snapshot()
include the numeric snapshot explicitly in the prompt
tell Claude to base its answer ONLY on the supplied facts
Prompt should say clearly:

“Do not invent market data”
“Use only the snapshot below”
“If the snapshot is mixed or low quality, be conservative”
Also include recent bot stats if already available from db, but only if they are real and structured.

Tighten briefing output discipline Keep returning the same MarketContext schema:
allow_trading
conviction_score
market_sentiment
breadth_health
top_risk_score
hot_sectors
cold_sectors
active_themes
high_impact_events
earnings_today
max_exposure_pct
summary
But:

if Massive snapshot has data_quality_ok = False, briefing should default conservative
do not let missing external data produce optimistic context
Improve per-signal review prompt In _call_signal_review() include the computed market snapshot facts alongside the interpreted morning context.
For example include:

SPY day %
QQQ day %
IWM day %
DIA day %
breadth count
strongest sector
weakest sector
market_regime_guess
This gives Claude factual context when reviewing each signal.

Do NOT fabricate earnings/events Until there is a real data source for:
earnings today
high-impact events
do not ask Claude to guess them from scratch.

Use this rule:

if no real source is wired, set these lists empty
Claude may mention uncertainty in summary, but should not invent specific events
Keep conservative fallback behavior Do not change the safety philosophy:
any timeout/failure/parsing error => conservative fallback
only explicit successful parsing can allow trading
Important Do NOT redesign the whole reviewer. This patch is specifically to ground it in Massive.com market data.

Do NOT change:

public method names
SignalDecision / MarketContext dataclasses
conservative fallback behavior
API timeout logic
Optional cleanup If useful, store the last raw market snapshot on the reviewer object:

self._market_snapshot and expose it in get_status() for dashboard visibility.
Verify

python -m py_compile intelligence/claude_reviewer.py
force-run get_morning_context()
confirm logs show Massive snapshot fields being built
confirm Claude briefing prompt now contains real market facts
confirm fallback still works safely if Massive API fails
Expected

morning briefing is grounded in real market data
Claude interprets facts rather than inventing them
per-signal review has better context
reviewer becomes more useful as a smart filter / sizing layer