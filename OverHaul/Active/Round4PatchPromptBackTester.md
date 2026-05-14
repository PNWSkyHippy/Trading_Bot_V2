Patch BreakoutScanner.py.

Problem BreakoutDetector was replaced with a new API that exposes:

detect_breakout(price_data) -> BreakoutSignal | None
But MarketScanner._process_symbol() still calls old removed methods:

self.detector.score(pd)
self.detector.vol_spike(pd)
self.detector.momentum_val(pd)
This means new symbol detection is broken / inconsistent.

Required fix Update MarketScanner._process_symbol() to use the new detector API correctly.

Current broken pattern After the escalation/watchlist checks, the code still does:

sc = self.detector.score(pd)
manual threshold check
manual BreakoutSignal construction using removed helper methods
Replace that whole section with this logic

Call: sig = self.detector.detect_breakout(pd)

Log signal check using sig.confidence if sig exists, else 0.0: [SIGNAL CHECK] {broker} {sym} score=... threshold=...

If sig is None, return

If sig.confidence < watchlist_min_score, return

Set: sig.broker = broker

Add it directly to the watchlist: self.watchlist.add(sig)

Important

Do NOT manually reconstruct BreakoutSignal in _process_symbol().
detect_breakout() already returns a fully populated BreakoutSignal.
Preserve the existing escalation and watchlist promotion logic before this section.
Preserve existing logging style.
Also clean up Remove the duplicate optional import blocks near the top of the file:

alert_sound import block appears twice
chart_patterns import block appears twice
Do not change anything else.

Verify

python -m py_compile BreakoutScanner.py
Start scanner and confirm no AttributeError referencing:
score
vol_spike
momentum_val
Expected

New symbols are evaluated through detect_breakout()
Watchlist additions continue working
No old-method AttributeErrors remain
