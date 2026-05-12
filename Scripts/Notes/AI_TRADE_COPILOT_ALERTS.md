1) AI_TRADE_COPILOT_ALERTS.md
# AI TRADE COPILOT ALERTS
**Status:** Deferred / Archive
**Priority:** Future enhancement after core engine validation
**Purpose:** Add "human-touch" AI assistance without giving AI direct trade control

---

## Goal

Use AI as a **trade co-pilot**, not a pilot.

The AI should:
- review open trades
- review market context
- review chart behavior
- review major news/headline risk
- detect possible thesis failure or opportunity
- send **alerts/recommendations to the user**

The AI should **not** initially:
- auto-close positions
- auto-modify stop loss
- auto-add to positions
- auto-take profit
- override risk manager autonomously

---

## Why This Design

This gives the best balance of:
- mechanical system consistency
- human judgment
- AI contextual assistance
- reduced risk of bad autonomous decisions

The bot remains rules-based.
The AI becomes a **discretionary advisor layer**.

---

## Phase Rollout

### Phase 1 — Read-Only Advisories
AI only generates alerts:
- no execution
- no broker calls
- no DB trade changes
- user sees recommendation and decides manually

### Phase 2 — One-Click Suggested Actions
AI may attach a recommended action:
- close trade
- move stop to breakeven
- trim partial size
- do not add
- hold

User must still approve manually.

### Phase 3 — Narrow Auto-Action (Optional)
Only after proven useful:
- allow auto-actions on a very limited whitelist
- examples:
  - hard-news invalidation
  - extreme market regime breakdown
  - direct thesis break confirmed by multiple signals

Not recommended until long paper-validation period is complete.

---

## Core Alert Types

### 1. EXIT WARNING
Trade thesis appears to be weakening.

Examples:
- BTC/SPY regime turned against trade
- lower high / lower low developing
- trend exhaustion
- volume collapse near resistance
- reversal candle cluster
- news invalidation

### 2. TAKE PROFIT SUGGESTED
Trade is in profit, but momentum appears to be fading.

Examples:
- weakening trend
- rejection at resistance
- divergence
- large move already made
- market context deteriorating

### 3. MOVE STOP UP
Trade has enough profit cushion to protect capital.

Examples:
- move stop to breakeven
- move stop under/over local structure
- lock in partial gain

### 4. DO NOT ADD
Trade is still open but the dip/add opportunity is poor quality.

Examples:
- dip is breakdown, not healthy pullback
- volume pattern weak
- regime unstable
- correlated market rolling over

### 5. ADD-ON OPPORTUNITY
Optional future alert only.
Trade is working and pullback is constructive.

### 6. MARKET REGIME WARNING
Broad market changed materially against current trade basket.

Examples:
- BTC loses key support
- SPY breaks down
- breadth collapses
- sector leadership flips

### 7. NEWS RISK ALERT
Major news or event likely invalidates setup.

Examples:
- earnings guidance shock
- SEC / legal action
- exchange incident
- macro rate surprise
- token unlock / exploit / hack

### 8. THESIS BROKEN
High-confidence alert that original setup logic no longer holds.

This is stronger than EXIT WARNING.

---

## Inputs the AI Should Review

### Trade State
- symbol
- asset_class
- direction
- entry_price
- current_price
- pnl_pct
- stop_loss
- take_profit
- bars_held
- strategy_name
- entry_timeframe
- entry metadata / indicators_json

### Market Context
- BTC trend and key levels for crypto
- SPY / QQQ / sector ETF trend for stocks
- daily market condition
- recent volatility regime
- breadth / dominance context if available

### Chart Context
- current timeframe chart
- lower timeframe momentum
- nearby support/resistance
- volume trend
- wick rejection
- trend continuation vs exhaustion structure

### News Context
- major headlines
- earnings/events calendar
- exchange outages
- macro surprise
- sector-specific catalysts

---

## Output Contract

AI should produce a structured recommendation object.

Example:

```json
{
  "symbol": "SOL/USD",
  "trade_id": "abc123",
  "action": "EXIT_SUGGESTED",
  "urgency": "high",
  "confidence": 0.84,
  "reason": "BTC lost intraday support, SOL formed lower high on 15m, volume fading into resistance.",
  "supporting_factors": [
    "BTC regime bearish",
    "Lower high on lower timeframe",
    "Momentum weakening",
    "Trade already +2.6%"
  ],
  "suggested_user_action": "Close manually or tighten stop aggressively",
  "timestamp": "2026-05-12T14:30:00Z"
}
Minimum Fields
Field	Type	Required	Notes
symbol	str	yes	
trade_id	str	yes	
action	str	yes	enum
urgency	str	yes	low / medium / high
confidence	float	yes	0.0–1.0
reason	str	yes	plain-English explanation
supporting_factors	list[str]	yes	1–5 concise bullets
suggested_user_action	str	yes	
timestamp	str	yes	ISO UTC
Allowed Action Enum
HOLD
EXIT_WARNING
EXIT_SUGGESTED
TAKE_PROFIT_SUGGESTED
MOVE_STOP_UP
DO_NOT_ADD
ADD_ON_OPPORTUNITY
MARKET_REGIME_WARNING
NEWS_RISK_ALERT
THESIS_BROKEN
Guardrails
Must Not
bypass risk_manager
place broker orders directly in Phase 1
widen stop loss beyond original intended risk
add to losers automatically
reverse positions automatically
act without timestamped rationale
Should
be advisory only first
include confidence + reason
include supporting factors
degrade safely if context missing
never silently act
Triggering Model
AI should run:

on new trade open
periodically for open trades (ex: every 15–30 min)
immediately after major market regime change
immediately after important news event
on demand from dashboard
Not every 10 seconds. This is a context layer, not an execution loop.

UI Recommendations
Dashboard should show:

alert badge
symbol
action
urgency
confidence
short reason
button to expand full rationale
Optional controls:

Dismiss
Snooze
Mark as handled
Apply manually
Validation Plan
Before any execution authority:

Run advisory-only in paper mode
Log every AI recommendation
Compare with what user would have done
Measure:
saved losses
improved exits
false alarms
harmful interventions
Only then consider one-click or auto-actions
Success Criteria
This feature is successful if it:

catches thesis breaks earlier than static exits
reduces avoidable giveback
improves trade management quality
helps the user make faster, better discretionary decisions
does not increase operational risk
Current Decision
Deferred. Do not implement until:

live core engine is stable
strategy edge is validated
token/API cost is justified by trading results

---
