
# `MARKET_REGIME_CONTEXT_SPEC.md`

```md
# MARKET REGIME CONTEXT SPEC
**Status:** Deferred / Archive
**Priority:** High-value future enhancement
**Purpose:** Prevent the bot from trading mechanically against obvious broad-market conditions

---

## Problem

The current bot can be individually correct on signal logic while still being
context-blind to the broader market.

Examples:
- crypto longs during a broad BTC-led market dump
- aggressive stock longs on a clear SPY trend-down day
- overexposure in the wrong direction because signal quality is judged locally, not globally

This creates unnecessary losses even when the per-symbol logic is reasonable.

---

## Goal

Add a lightweight **market regime layer** that influences:
- whether longs are favored or blocked
- whether shorts are favored or blocked
- position size scalar
- alert severity / caution level

This should be a **bias / gating layer**, not a replacement for strategy logic.

---

## Design Principle

### Local signal decides **setup quality**
### Market regime decides **whether to trust it fully**

---

## Asset-Class Context Sources

### Crypto
Primary proxy:
- BTC/USD

Optional secondary context:
- ETH/USD
- crypto breadth proxy
- BTC dominance
- total market cap trend
- top-N breadth

### Stocks
Primary proxy:
- SPY

Optional secondary context:
- QQQ
- sector ETF relevant to symbol
- VIX
- breadth / advance-decline
- market internals

---

## Regime States

### Bullish
Broad market trending upward with supportive momentum.

### Bearish
Broad market trending downward with weak structure.

### Neutral / Choppy
No clean directional edge.

### Risk-Off / Panic
Fast deterioration, elevated volatility, abnormal downside pressure.

---

## Suggested First-Pass Logic

### Crypto
Use BTC/USD as master regime proxy.

Inputs:
- price vs EMA20 / EMA50 / EMA200
- ADX
- recent % change
- lower-high / lower-low structure
- volume expansion on downside
- optional 4h / 1h alignment

### Stocks
Use SPY as master regime proxy.

Inputs:
- price vs EMA20 / EMA50 / EMA200
- daily trend state
- intraday condition
- ADX / volatility
- market breadth if available

---

## Initial Actions by Regime

### Bullish
- allow longs normally
- reduce confidence in shorts
- optionally scale down short size

### Bearish
- allow shorts normally
- reduce confidence in longs
- optionally scale down long size

### Neutral
- allow both but reduce size
- require stronger per-symbol confirmation

### Risk-Off / Panic
- block new longs
- optionally block all new entries except strongest shorts
- tighten caution alerts for open positions

---

## First-Version Output Contract

A market context object should be produced periodically.

Example:

```json
{
  "asset_class": "crypto",
  "proxy_symbol": "BTC/USD",
  "regime": "bearish",
  "confidence": 0.82,
  "position_scalar": 0.50,
  "allow_longs": false,
  "allow_shorts": true,
  "reason": "BTC below 20/50 EMA, downside momentum accelerating, failed reclaim of prior support.",
  "timestamp": "2026-05-12T14:00:00Z"
}
Minimum Fields
Field	Type	Required	Notes
asset_class	str	yes	stock / crypto
proxy_symbol	str	yes	BTC/USD or SPY
regime	str	yes	bullish / bearish / neutral / risk_off
confidence	float	yes	0.0–1.0
position_scalar	float	yes	0.0–1.0
allow_longs	bool	yes	
allow_shorts	bool	yes	
reason	str	yes	
timestamp	str	yes	ISO UTC
How It Should Influence the Bot
1. Signal Filtering
Market regime can veto clearly bad-side entries.

Examples:

crypto longs blocked when BTC regime = bearish high-confidence
stock shorts reduced when SPY regime = bullish high-confidence
2. Position Sizing
Position scalar modifies size.

Examples:

bullish aligned trade: 1.00x
neutral trade: 0.75x
counter-regime trade: 0.50x
panic/risk-off trade: 0.00x to 0.25x
3. Open Position Alerts
When regime flips against open positions:

generate warnings
tighten management
notify user
Important Guardrail
Do not let regime logic become overly strict at first.

Bad version:

blocks almost everything
destroys sample size
creates false confidence
Good version:

gently biases sizing and filters only the worst context conflicts
Recommended Initial Policy
Crypto
if BTC regime = bearish high-confidence:
block new longs
allow shorts
warn on existing longs
Stocks
if SPY regime = bearish high-confidence:
reduce long size materially
only allow strongest long signals
warn on weak long setups
This alone would likely avoid many obvious bad trades.

Rollout Plan
Phase 1 — Advisory Only
Compute regime and log it. No trade blocking yet.

Phase 2 — Soft Influence
Use regime only to:

scale position size
add warning tags
mark counter-trend trades
Phase 3 — Hard Gate
Only after validation:

block clearly wrong-side entries in strong bearish/bullish regimes
Validation Plan
Measure before/after:

win rate by regime
expectancy by regime
long performance during bearish BTC/SPY
short performance during bullish BTC/SPY
PnL impact of counter-regime trades
Questions to answer:

Are counter-regime trades actually worse?
Does the filter improve expectancy?
Does it reduce too many good trades?
Suggested Dashboard Additions
Show:

current stock regime
current crypto regime
confidence
long/short allowance
position scalar
Examples:

CRYPTO REGIME: BEARISH (0.82) | longs blocked | shorts favored | size 0.50x
STOCK REGIME: NEUTRAL (0.56) | both allowed | size 0.75x
Future Expansion
Possible later add-ons:

sector regime for stocks
altcoin breadth for crypto
dominance / correlation map
news-driven regime override
volatility regime state
exchange-specific risk conditions
Current Decision
Deferred. Implement only after:

current strategy stack is validated
live execution stability is confirmed
enough trade data exists to test whether regime filtering truly improves outcomes

---

