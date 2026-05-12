# CLAUDE CODE — BREAKOUT PHASE 8A
**Focus:** BreakoutScanner owns setup analysis and payload enrichment

## Goal
Refactor `BreakoutScanner.py` so the scanner itself computes and attaches the data the bot needs, instead of relying on `breakout_sender.py` / `breakout_receiver.py` to guess or reconstruct it later.

The current pipeline is self-blocking because the receiver expects RSI / trend / market-context data that the scanner never reliably sends.

---

## Current confirmed problems

### 1) `BreakoutSignal` has no explicit `direction`
`breakout_sender.py` currently does:
```python
direction = getattr(signal, "direction", "long")
But BreakoutSignal does not define direction, so signals can silently default to "long".

This is correctness-critical.

2) AlertSystem._build_candle_data() is the wrong place for analysis
The alert system is trying to reconstruct RSI / market context after the fact.

That is backwards.

The scanner has the freshest data and should compute setup context before sending.

3) signal.price_history / signal.volume_history are never populated
Receiver-side soft checks depend on data that is not actually being attached to the signal.

4) market_pct_change path is broken
AlertSystem._build_candle_data() checks:

if hasattr(self, "price_history"):
But AlertSystem has no price_history attribute.

5) SMA200 is too heavy / unreliable for this pipeline
Do not make breakout execution depend on scanner supplying sma200. This scanner is meant to catch moves early and act fast. If trend alignment is kept, it must be computed upstream and treated as optional metadata, not a hard dependency for execution.

Required architectural direction
Scanner should own:
direction
latest closed candle OHLC
RSI
volume spike
market context
optional trend context
breakout metadata
any pre-send trust checks
Sender should only serialize and send
Receiver should only fast-gate execution
Required code changes in BreakoutScanner.py
A. Extend BreakoutSignal
Add at minimum:

direction: str = "long"
enrichment: Dict[str, Any] = field(default_factory=dict)
Optional but recommended:

breakout_level: float = 0.0
bars_since_breakout: int = 0
distance_from_breakout_pct: float = 0.0
Do not remove existing fields.

B. Set direction explicitly in _process_symbol()
When creating BreakoutSignal, set direction explicitly.

Preferred priority:

If chart pattern module produced a clear direction (pd._pattern_dir), use it
Else infer from momentum sign
Else default to "long" only as true last resort
Suggested logic:

positive breakout / bullish pattern / positive momentum -> "long"
negative breakout / bearish pattern / negative momentum -> "short"
Do not leave direction implicit.

C. Populate signal enrichment at creation time
Create a helper such as:

def _build_signal_enrichment(self, pd: PriceData, broker: str) -> Dict[str, Any]:
This helper should compute and return a dict containing as many of these as possible:

Required
candle_open
candle_high
candle_low
candle_close
rsi
market_pct_change
volume_spike
pattern
breakout_level
bars_since_breakout
distance_from_breakout_pct
Optional
sma200
structural_stop_price
If a field cannot be computed safely, omit it or set it to None — do not fake values.

Attach the dict to:

signal.enrichment = {...}
D. Use latest CLOSED bar for OHLC
For candle anatomy:

use the most recent completed bar from historical data
do not use the current tick as candle close if the candle is still forming
This is especially important for wick rejection and breakout distance.

E. Populate price_history and volume_history
When signal is created, copy the detector history into the signal so it exists if still needed elsewhere:

signal.price_history = list(self.detector.price_history.get(sym, []))
signal.volume_history = list(self.detector.volume_history.get(sym, []))
Do not leave these empty if the detector has history.

F. Compute RSI in scanner, not alert system
Add a lightweight RSI helper if needed and compute it from recent closes.

Attach it into signal.enrichment["rsi"].

G. Compute market context in scanner
For crypto:

use BTC/USD recent move as market proxy
For stocks:

use SPY recent move if easily available
if not available, set market_pct_change=None
Do not make scanner fail just because market context is unavailable.

Attach:

signal.enrichment["market_pct_change"] = ...
H. Optional trend context
If cheap and reliable, compute and attach one of:

sma200
ema50
ema20
But do not make scanner slower or fragile to support this. If not practical, leave as None.

I. Move pre-send quality checks upstream
Before calling sender, scanner should already know whether the setup is worth sending.

At minimum, keep these upstream in scanner logic:

volume spike threshold
wick rejection when OHLC available
gap/exhaustion filter
breakout still near trigger level
direction correctness
If some of these already exist elsewhere, consolidate rather than duplicate.

J. Simplify AlertSystem._build_candle_data()
This method should no longer be the source of truth.

Preferred end state:

sender reads signal.enrichment
AlertSystem._build_candle_data() becomes a thin compatibility shim or is removed
no analytical logic should live there
Rules
Preserve GUI behavior
Preserve watchlist/escalation behavior
Do not break CSV logging
Do not redesign the whole scanner UI
Keep scanning fast
Avoid extra network calls if the same bars already exist locally
Prefer attaching enrichment once at signal creation instead of recomputing repeatedly
Deliverables
Provide:

summary
files changed
exact fields now attached to BreakoutSignal
exact payload-ready enrichment fields produced by scanner
verification steps
note any fields intentionally left optional
Verification checklist
Must confirm all of the following after patch:

1. Direction is explicit
Search:

grep -n "direction" BreakoutScanner.py
Expected:

BreakoutSignal has a direction field
_process_symbol() sets it explicitly
2. Enrichment exists
Search:

grep -n "enrichment" BreakoutScanner.py
Expected:

signal enrichment is built and attached before sender runs
3. RSI is scanner-owned
Search:

grep -n "rsi" BreakoutScanner.py
Expected:

RSI computed in scanner, not only in sender/receiver
4. AlertSystem no longer invents analysis
Search:

grep -n "_build_candle_data" BreakoutScanner.py
Expected:

method removed or reduced to compatibility-only behavior
5. Market context attached
Search:

grep -n "market_pct_change" BreakoutScanner.py
Acceptance criteria
No breakout signal reaches sender without explicit direction
Scanner attaches usable enrichment before send
RSI and market context no longer depend on AlertSystem guessing
Breakout pipeline is no longer starved of data before receiver evaluation

---

# 2) `prompts/CLAUDE_CODE_BREAKOUT_8B_SENDER_PAYLOAD.md`

```md
# CLAUDE CODE — BREAKOUT PHASE 8B
**Focus:** Sender must serialize the scanner's enriched signal correctly

## Goal
Patch `breakout_sender.py` so it stops guessing and simply forwards the enriched breakout signal cleanly and consistently to the bot API.

The scanner should be the source of truth.
The sender should be a transport layer.

---

## Current confirmed problems

### 1) Silent default to long
Current code:
```python
direction = getattr(signal, "direction", "long")
If scanner forgot to attach direction, sender silently turns it into a long.

This must not happen.

2) Sender still tries to reconstruct missing data
Current code still tries to derive OHLC from signal.history or partial candle_data.

That is fragile.

3) Broker bug was patched, but payload quality is still weak
Broker is no longer the main blocker. Payload completeness now is.

