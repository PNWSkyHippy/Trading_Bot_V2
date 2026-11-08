# PFC-101 - Master Reference: Prop Firm Futures Trading Execution & Risk Systems

*This document synthesizes all core concepts, mental models, risk engine architecture, execution logic, bracket mechanics, and state tracing from the Prop Firm Futures Combine curriculum into an authoritative, publication-grade self-contained reference guide.*

---

## Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Prop Implementation & State Tracing](#3-idiomatic-prop-implementation--state-tracing)
4. [Defensive Trading & Common Traps](#4-defensive-trading--common-traps)
5. [Prop Trading Mechanics, References & Scope](#5-prop-trading-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)

---

## 1. Abstract Foundations & Core Theory

### Primary Operational Variables & Definitions

* **Account Capital ($C$):** The total liquidated equity in the trading account at any given timestamp $t$.
* **Realized PnL ($\Delta P_{\text{realized}}$):** Closed trade cash flow resulting from completed buy/sell executions.
* **Unrealized PnL ($\Delta P_{\text{unrealized}}$):** Floating paper gain or loss on open positions based on current mark-to-market prices.
* **High Water Mark ($HWM_t$):** The maximum peak equity achieved by the account during the evaluation lifecycle:
  $$HWM_t = \max_{0 \le k \le t} (C_k + \Delta P_{\text{unrealized}, k})$$
* **Dynamic Trailing Drawdown Floor ($TDD_t$):** A ratcheting capital threshold calculated relative to peak equity ($HWM_t$) minus a firm-defined maximum allowable drawdown distance ($D_{\max}$):
  $$TDD_t = HWM_t - D_{\max}$$
  *Invariant:* $TDD_t$ is monotonically non-decreasing ($\frac{d TDD}{dt} \ge 0$). It increases when $HWM_t$ rises, but remains permanently locked at its highest level when equity retraces.
* **Static Daily Loss Limit ($DLL$):** A hard daily circuit-breaker calculated from the start-of-day balance ($C_{\text{SOD}}$) minus the maximum allowable daily loss ($L_{\text{daily}}$):
  $$\text{Threshold}_{\text{DLL}} = C_{\text{SOD}} - L_{\text{daily}}$$
  If current equity breaches this threshold at any point during the session, all open orders are immediately canceled, positions are liquidated, and trading permission is revoked for the remainder of the session.
* **Per-Trade Risk Cap ($R$):** The maximum dollar amount allocated to a single trade idea, defined prior to order entry as a hard ceiling.
* **Invalidation Distance ($S_{\text{ticks}}$):** The price distance in ticks between the execution price and the technical invalidation level (structural swing high/low where the setup's thesis is disproven).
* **Tick Value ($V_{\text{tick}}$):** The dollar value per minimum price increment per contract (e.g., $1.25 per 0.25 tick for Micro E-mini S&P 500 / MES, or $12.50 per 0.25 tick for E-mini S&P 500 / ES).
* **Derived Contract Size ($N$):** The calculated maximum whole number of contracts allowed for entry:
  $$N = \left\lfloor \frac{R}{S_{\text{ticks}} \times V_{\text{tick}}} \right\rfloor$$
  *Invariant:* Fractional contract sizes are unconditionally rounded down to prevent exceeding $R$.

---

### Side-by-Side Comparison Matrix

| Feature / Spec | Static Daily Loss Limit (DLL) | Dynamic Trailing Drawdown (TDD) | Invalidation Sizing Engine |
| :--- | :--- | :--- | :--- |
| **Primary Definition** | Intraday hard circuit-breaker based on start-of-day equity. | Ratcheting risk floor calculated from peak unrealized account equity. | Mathematical sizing algorithm deriving contract quantity from stop distance. |
| **Mathematical Formula** | $C_{\text{SOD}} - L_{\text{daily}}$ | $HWM_t - D_{\max}$ | $\lfloor R / (S_{\text{ticks}} \times V_{\text{tick}}) \rfloor$ |
| **Trigger Benchmark** | Realized + Unrealized Intraday PnL | Intraday Peak Mark-to-Market Equity | Pre-trade Risk Cap ($R$) vs Stop Distance ($S$) |
| **State Mutability** | Fixed at Start-of-Day; resets every 24 hours at market close. | Monotonically Increasing (Climbs with peak equity, never decreases). | Dynamic per setup; calculated prior to order transmission. |
| **Permitted Operations** | Query intraday equity; trigger emergency liquidation when breached. | Continuous mark-to-market tracking; ratchet floor upward on equity highs. | Measure chart ticks; divide risk budget; round down contract count. |
| **Common Runtime Trap** | Assuming DLL resets instantly after taking a profit. | Holding open gains without scaling, allowing floating profit to collapse into TDD floor. | Sizing by desired contract count first and stretching stop loss to fit. |

---

## 2. Real-World Mental Models & Conceptual Mapping

### 1. The One-Way Ratchet Elevator (Dynamic Trailing Drawdown)
Imagine riding an elevator up a skyscraper with a mechanical floor beneath you fitted with a **one-way ratchet gear**. 

* When you start at floor 10, the safety floor is locked at floor 7 (giving you 3 floors of room).
* As the elevator climbs to floor 15, the ratchet gear clicks upward continuously, bringing the safety floor up to floor 12.
* If the elevator stops and begins falling back toward floor 12, **the safety floor does not lower**. It remains permanently frozen at floor 12.
* If you step down to floor 12, you crash into the floor and are disqualified instantly—even though floor 12 is higher than where you started the morning.

```
[ ACCOUNT EQUITY VS TRAILING DRAWDOWN FLOOR ]

Equity ($)
  ^
  |          Peak Equity ($52,500)
  |             / \
$52,500 +----- / ---\ ------------------- (Peak locked)
  |           /      \  Unrealized
  |          /        \ Re-trace
  |         /          \
$50,500 +--/------------X <--- LIQUIDATION TRIGGER!
  |       /              \     (Equity hits frozen TDD Floor)
  |      /   Trailing     \
$50,000 +   Drawdown Floor \
  |    /    Ratchets Up     \
$48,000 +---------------------\---------- (Initial TDD Floor)
  +-------------------------------------> Time
```

---

### 2. The Emergency Bush Plane Payload (Invalidation Position Sizing)
Operating a bush plane in volatile territory requires strict compliance with an emergency fuel budget.

* You are given an absolute limit of **50 gallons of emergency fuel** ($R = \$50$).
* You do not load 5 heavy crates ($N = 5$) and then hope an airstrip is nearby.
* Instead, you locate the **nearest emergency landing strip** on the map (Technical Invalidation Level) and measure the distance ($S_{\text{ticks}}$).
* If the strip is 10 miles away ($S = 10$ ticks), you can safely carry 4 crates.
* If severe weather forces you to select a strip 40 miles away ($S = 40$ ticks), your fuel math dictates you can carry only 1 crate.
* **The terrain determines the distance, and the distance dictates the payload.**

---

### 3. The Harbor Navigation Tri-Level Scope (Multi-Timeframe Hierarchy)
Guiding a container ship safely into port requires three distinct navigational views that must never be confused or transposed:

```
+-------------------------------------------------------------------+
| 1. CONTEXT TIMEFRAME (Macro Chart / Hourly)                      |
|    - Defines Oceanic Tide & Weather (Trend, Range, Reversal Risk) |
|    - Determines Directional Permission (Long-Only / Short-Only)   |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
| 2. PRIMARY TIMEFRAME (Structure Chart / 5-Min)                    |
|    - Maps Dredged Channels & Sandbars (Key Swing Levels, S/R)     |
|    - Defines Setup Geometry & Invalidation Points                 |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
| 3. TRIGGER TIMEFRAME (Execution Chart / 1-Min or Tick)            |
|    - Engine Control & Binoculars (Momentum & Confirmation)        |
|    - Timing Order Entry at Intent Confirmation                    |
+-------------------------------------------------------------------+
```

---

## 3. Idiomatic Prop Implementation & State Tracing

### 1. Dynamic Position Sizing & Invalidation Floor Engine

```python
# Fenced Reference Block: Position Sizing & Invalidation Engine
import math

def calculate_combine_position_size(
    account_balance: float,
    daily_loss_limit_remaining: float,
    per_trade_risk_cap: float,
    entry_price: float,
    invalidation_price: float,
    tick_size: float = 0.25,
    tick_value: float = 1.25  # MES Micro Contract
) -> dict:
    """
    Calculates combine-safe contract size based on technical invalidation stop distance.
    Enforces per-trade risk cap and daily loss remaining budget.
    """
    # Step 1: Calculate raw stop distance in price and ticks
    price_distance = abs(entry_price - invalidation_price)  # state: 4850.0 - 4845.0 = 5.0 pts
    stop_ticks = price_distance / tick_size                 # state: 5.0 / 0.25 = 20.0 ticks
    cost_per_contract = stop_ticks * tick_value             # state: 20.0 * $1.25 = $25.00
    
    # Step 2: Determine effective risk ceiling (min of trade cap & daily remaining)
    effective_risk_cap = min(per_trade_risk_cap, daily_loss_limit_remaining)  # state: min($100, $300) = $100.00
    
    # Step 3: Compute raw contracts and apply mandatory floor rounding
    raw_contracts = effective_risk_cap / cost_per_contract  # state: $100.00 / $25.00 = 4.0
    allowed_contracts = math.floor(raw_contracts)           # state: math.floor(4.0) = 4
    
    # Step 4: Calculate actual dollar risk under whole contract sizing
    actual_dollar_risk = allowed_contracts * cost_per_contract  # state: 4 * $25.00 = $100.00
    
    # Step 5: Check validity invariant
    is_valid_setup = allowed_contracts >= 1 and actual_dollar_risk <= effective_risk_cap
    
    return {
        "stop_ticks": int(stop_ticks),
        "cost_per_contract": cost_per_contract,
        "effective_risk_cap": effective_risk_cap,
        "allowed_contracts": allowed_contracts,
        "actual_dollar_risk": actual_dollar_risk,
        "is_valid_setup": is_valid_setup
    }

# --- Execution Trace ---
# Setup: Long Entry at 4850.00, Invalidation Low at 4842.50 (7.50 pts / 30 ticks)
# Inputs: Balance=$50,000, DLL Remaining=$150, Per Trade Cap=$100
trace_result = calculate_combine_position_size(
    account_balance=50000.00,
    daily_loss_limit_remaining=150.00,
    per_trade_risk_cap=100.00,
    entry_price=4850.00,
    invalidation_price=4842.50,
    tick_size=0.25,
    tick_value=1.25
)

# Step-by-Step Trace Outputs:
# price_distance = abs(4850.00 - 4842.50) -> 7.50 pts
# stop_ticks = 7.50 / 0.25 -> 30.0 ticks
# cost_per_contract = 30.0 * 1.25 -> $37.50
# effective_risk_cap = min(100.0, 150.0) -> $100.00
# raw_contracts = 100.0 / 37.50 -> 2.666...
# allowed_contracts = math.floor(2.666) -> 2 contracts
# actual_dollar_risk = 2 * $37.50 -> $75.00
# Output dict: {'stop_ticks': 30, 'allowed_contracts': 2, 'actual_dollar_risk': 75.0, 'is_valid_setup': True}
```

---

### 2. Automated Bracket & OCO Order State Manager

```python
# Fenced Reference Block: Bracket & OCO Order Manager
from dataclasses import dataclass
from enum import Enum

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass
class OrderLeg:
    order_id: str
    order_type: str  # "LIMIT" or "STOP"
    price: float
    quantity: int
    status: OrderStatus = OrderStatus.PENDING

class BracketOCOManager:
    """
    Manages automated entry with attached OCO (One-Cancels-Other) Stop-Loss and Take-Profit legs.
    Ensures execution safety and automated cancellation of opposite legs.
    """
    def __init__(self, symbol: str, quantity: int, entry_price: float, stop_price: float, target_price: float):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_order = OrderLeg("ORD_ENTRY", "LIMIT", entry_price, quantity)
        self.stop_leg = OrderLeg("LEG_STOP", "STOP", stop_price, quantity)
        self.target_leg = OrderLeg("LEG_TARGET", "LIMIT", target_price, quantity)
        self.is_position_active = False

    def trigger_entry_fill(self) -> str:
        """Simulates fill of primary entry order and activates OCO child legs."""
        self.entry_order.status = OrderStatus.FILLED
        self.is_position_active = True
        return f"[STATE CHANGE] Entry FILLED at {self.entry_order.price}. OCO Legs Active: Stop @ {self.stop_leg.price}, Target @ {self.target_leg.price}"

    def process_price_update(self, current_price: float) -> str:
        """Evaluates price action against active OCO legs."""
        if not self.is_position_active:
            return "[IDLE] Position inactive."

        # Check Stop-Loss Trigger
        if current_price <= self.stop_leg.price:
            self.stop_leg.status = OrderStatus.FILLED
            self.target_leg.status = OrderStatus.CANCELLED  # OCO Logic
            self.is_position_active = False
            return f"[OCO EXECUTION] Stop-Loss FILLED at {current_price}. Target Leg CANCELLED automatically."

        # Check Take-Profit Trigger
        if current_price >= self.target_leg.price:
            self.target_leg.status = OrderStatus.FILLED
            self.stop_leg.status = OrderStatus.CANCELLED  # OCO Logic
            self.is_position_active = False
            return f"[OCO EXECUTION] Take-Profit FILLED at {current_price}. Stop Leg CANCELLED automatically."

        return f"[HOLDING] Current Price: {current_price}. Active Stop: {self.stop_leg.price}, Active Target: {self.target_leg.price}"

# --- Execution Trace ---
# Setup: Buy MES 2 contracts at 4850.00, Stop at 4842.50, Target at 4865.00
manager = BracketOCOManager("MES", 2, 4850.00, 4842.50, 4865.00)
# Trace 1: Entry Fills -> Entry status = FILLED, position_active = True
# Trace 2: Price moves to 4858.00 -> Status: HOLDING
# Trace 3: Price moves to 4865.25 -> Target FILLED, Stop CANCELLED automatically
```

---

## 4. Defensive Trading & Common Traps

### 1. The Revenge Re-Entry Trap (Post-Loss Impulse)

```python
# INCORRECT: Re-entering immediately upon stop-out to recoup loss
def process_trade_outcome_incorrect(last_trade_pnl, daily_pnl, current_setup):
    if last_trade_pnl < 0:
        # BUG: Doubling position size immediately to "get money back"
        next_contract_size = current_setup['size'] * 2  
        # BUG: Bypassing pre-market filter checks
        execute_trade(current_setup['symbol'], next_contract_size)
        # Result: Violates Daily Loss Limit via emotional escalation

# CORRECT: Enforcing mandatory cool-down and process reset
def process_trade_outcome_correct(last_trade_pnl, daily_pnl, max_daily_loss, current_setup, journal_log):
    if last_trade_pnl < 0:
        journal_log.append("STOP_OUT: Executing mandatory 15-minute cool-down protocol.")
        
        # Check if daily loss cap is reached or threatened
        if abs(daily_pnl + last_trade_pnl) >= (max_daily_loss * 0.80):
            return "DECISION: PAUSE_TRADING - Approaching 80% of Daily Loss Limit."
            
        # Require one-sentence rule confirmation test before next signal
        if not passes_one_sentence_rule_test(current_setup):
            return "DECISION: PASS_TRADE - Failed rule confirmation test."
            
        # Re-calculate size conservatively using baseline formula
        return "DECISION: PERMITTED - Proceed to sizing engine with standard per-trade cap."
```

---

### 2. The Stop-Widening / "Giving It Room" Trap

```python
# INCORRECT: Modifying stop-loss downward when price threatens invalidation level
def handle_approaching_stop_incorrect(position, current_price):
    if current_price - position.stop_loss <= 1.0:
        # BUG: Moving stop farther away without recalculating risk
        position.stop_loss -= 5.0  # "Giving the market room to breathe"
        # Result: Transforms a controlled $100 loss into an uncontrolled $350 account blow-up!

# CORRECT: Treating Stop Loss as an Immutable Contract Parameter
def handle_approaching_stop_correct(position, current_price):
    # INVARIANT: Stop-loss price bound at entry is strictly IMMUTABLE against expansion
    original_invalidation_stop = position.initial_stop_price
    
    if current_price <= original_invalidation_stop:
        # Accept technical invalidation cleanly
        execute_market_close(position)
        return "EXIT: Technical invalidation confirmed. Loss accepted per risk plan."
    
    return "HOLD: Trade remaining within planned invalidation boundaries."
```

---

### 3. The Chasing Breakouts / Chop Zone Trap

```python
# INCORRECT: Buying market after 4 extended candles into resistance
def evaluate_breakout_entry_incorrect(candle_series):
    if candle_series.last_4_candles_are_green():
        # BUG: Buying at the top of an extended move without structural pullback
        return "BUY MARKET"  # Result: High likelihood of buying the exact exhaustion peak

# CORRECT: Filtering setups through multi-timeframe rejection & pullback rules
def evaluate_breakout_entry_correct(context_trend, primary_structure, trigger_candle):
    # Rule 1: Must align with higher-timeframe context
    if context_trend != "BULLISH":
        return "PASS: Macro context not aligned."
        
    # Rule 2: Must enter on pullback re-test, not chase impulse peak
    if not primary_structure.is_at_retest_level():
        return "PASS: Price extended; waiting for structural pullback re-test."
        
    # Rule 3: Trigger candle must show intent confirmation
    if not trigger_candle.shows_rejection_and_momentum():
        return "PASS: Trigger candle lacks clear rejection confirmation."
        
    return "GO: Setup passed all multi-timeframe filters."
```

---

## 5. Prop Trading Mechanics, References & Scope

### Platform Memory, State Mutation, and Scope Architecture

```
+-------------------------------------------------------------------------+
|                      GLOBAL ACCOUNT STATE ENGINE                        |
|                                                                         |
|  - Start-of-Day Balance (C_SOD): $50,000.00                              |
|  - High Water Mark (HWM): $52,000.00                                    |
|  - Trailing Drawdown Floor (TDD): $50,000.00 (Monotonically Locked)    |
|  - Intraday Daily Loss Limit (DLL): $48,500.00 (Static Circuit Breaker) |
+-------------------------------------------------------------------------+
                                    ^
                                    | Mark-to-Market Feed (Mutates HWM)
                                    v
+-------------------------------------------------------------------------+
|                       LOCAL TRADE SCOPE MANAGER                         |
|                                                                         |
|  - Current Active Position: Long 2 MES @ 4850.00                        |
|  - Immutable Invalidation Stop: 4842.50 (Bound at Entry)                |
|  - Dynamic Target Leg 1: 4857.50 (Mutates position on Scale-Out)        |
|  - Dynamic Target Leg 2: 4865.00 (Runner Target)                        |
+-------------------------------------------------------------------------+
```

#### 1. Scope Segregation: Global Engine vs Local Trade Scope
* **Global Account State:** Maintains master risk invariant boundaries ($DLL$, $TDD$, $HWM$). It reads unrealized tick updates continuously. If floating unrealized loss touches either $DLL$ or $TDD$, Global Scope overrides Local Scope, issuing an immediate `CANCEL_ALL_AND_FLATTEN` signal.
* **Local Trade Scope:** Encapsulates setup-specific variables (entry price, stop price, target price). Local trade logic cannot mutate Global Risk Parameters.

#### 2. Variable Binding and Immutability Invariants
* **Immutable Bindings:** The `invalidation_stop_price` parameter is bound as an **immutable constant** upon trade execution. Once created, software logic prevents any modification that expands the stop distance.
* **Mutable State Transitions:** Take-profit targets and trailing stop levels are **mutable objects**. Upon reaching Target 1, a state transition event fires:
  1. Position size mutates ($N \to N/2$).
  2. Realized PnL updates Global Account State.
  3. Stop Loss leg mutates from `Invalidation_Level` to `Breakeven_Price` (if earned by structure).

---

## 6. Practical Integration / Mini Case Study

### Complete Production-Grade Script: `PropFirmCombineRiskEngine`

```python
# Fenced Reference Block: Prop Firm Combine Risk Engine & Execution Manager
import math
from datetime import datetime

class PropFirmCombineRiskEngine:
    """
    Production-grade Prop Firm Combine Risk & Execution Engine.
    Integrates account state tracking, position sizing, multi-timeframe alignment,
    bracket order generation, and post-trade review auditing.
    """
    def __init__(self, start_balance: float, max_trailing_drawdown: float, daily_loss_limit: float):
        self.start_balance = start_balance
        self.current_balance = start_balance
        self.high_water_mark = start_balance
        self.max_trailing_drawdown = max_trailing_drawdown
        self.daily_loss_limit = daily_loss_limit
        
        # Calculate initial risk boundaries
        self.trailing_floor = self.high_water_mark - self.max_trailing_drawdown
        self.daily_loss_floor = self.start_balance - self.daily_loss_limit
        
        self.is_account_locked = False
        self.trade_history = []

    def update_account_equity(self, current_equity: float):
        """Updates equity, ratchets high water mark, and verifies risk floors."""
        if self.is_account_locked:
            return "ACCOUNT_LOCKED: Trading halted due to prior risk violation."

        self.current_balance = current_equity
        
        # Ratchet High Water Mark & Trailing Drawdown Floor
        if current_equity > self.high_water_mark:
            self.high_water_mark = current_equity
            self.trailing_floor = self.high_water_mark - self.max_trailing_drawdown

        # Check Hard Risk Floor Breaches
        if current_equity <= self.daily_loss_floor:
            self.is_account_locked = True
            return f"CRITICAL VIOLATION: Daily Loss Limit breached (${current_equity:.2f} <= ${self.daily_loss_floor:.2f}). Account LOCKED."

        if current_equity <= self.trailing_floor:
            self.is_account_locked = True
            return f"CRITICAL VIOLATION: Trailing Drawdown Floor breached (${current_equity:.2f} <= ${self.trailing_floor:.2f}). Account LOCKED."

        return f"ACCOUNT OK: Equity=${current_equity:.2f}, HWM=${self.high_water_mark:.2f}, TDD Floor=${self.trailing_floor:.2f}, DLL Floor=${self.daily_loss_floor:.2f}"

    def evaluate_and_size_entry(
        self,
        context_bias: str,
        primary_structure: str,
        trigger_confirmed: bool,
        news_event_active: bool,
        per_trade_cap: float,
        entry_price: float,
        invalidation_price: float,
        tick_size: float = 0.25,
        tick_value: float = 1.25
    ) -> dict:
        """Runs pre-trade filters, multi-timeframe alignment check, and calculates precise sizing."""
        if self.is_account_locked:
            return {"decision": "REJECT", "reason": "Account is locked due to risk limit breach."}

        # Filter 1: News Caution
        if news_event_active:
            return {"decision": "REJECT", "reason": "High-impact news event active. Stand aside."}

        # Filter 2: Multi-Timeframe Alignment
        if context_bias != primary_structure or not trigger_confirmed:
            return {"decision": "REJECT", "reason": "Multi-timeframe misalignment or unconfirmed trigger."}

        # Calculate Risk Parameters
        price_distance = abs(entry_price - invalidation_price)
        stop_ticks = price_distance / tick_size
        cost_per_contract = stop_ticks * tick_value

        # Calculate remaining risk room
        remaining_daily_risk = self.current_balance - self.daily_loss_floor
        effective_cap = min(per_trade_cap, remaining_daily_risk)

        if cost_per_contract > effective_cap:
            return {"decision": "REJECT", "reason": f"Stop distance cost (${cost_per_contract:.2f}) exceeds risk cap (${effective_cap:.2f})."}

        contracts = math.floor(effective_cap / cost_per_contract)
        if contracts < 1:
            return {"decision": "REJECT", "reason": "Calculated size rounds down to 0 contracts."}

        total_risk = contracts * cost_per_contract

        # Generate Bracket Order Geometry
        target_1 = entry_price + (price_distance * 1.5) if context_bias == "BULLISH" else entry_price - (price_distance * 1.5)
        target_2 = entry_price + (price_distance * 3.0) if context_bias == "BULLISH" else entry_price - (price_distance * 3.0)

        return {
            "decision": "PERMITTED",
            "contracts": contracts,
            "entry_price": entry_price,
            "stop_loss": invalidation_price,
            "target_1": target_1,
            "target_2": target_2,
            "total_risk_dollars": total_risk,
            "stop_ticks": int(stop_ticks)
        }


# =====================================================================
# SYSTEM EXECUTION TRACE & SIMULATION
# =====================================================================
if __name__ == "__main__":
    print("=== PROP FIRM COMBINE RISK ENGINE SIMULATION ===\n")
    
    # Initialize Engine: $50,000 Account, $2,000 Dynamic Trailing Drawdown, $1,000 Daily Loss Limit
    engine = PropFirmCombineRiskEngine(start_balance=50000.0, max_trailing_drawdown=2000.0, daily_loss_limit=1000.0)
    print(engine.update_account_equity(50000.0))
    
    print("\n--- TEST 1: Evaluating High-Probability Trade Setup ---")
    setup_1 = engine.evaluate_and_size_entry(
        context_bias="BULLISH",
        primary_structure="BULLISH",
        trigger_confirmed=True,
        news_event_active=False,
        per_trade_cap=150.0,
        entry_price=4850.00,
        invalidation_price=4842.50  # 7.50 pts = 30 ticks = $37.50/contract
    )
    print("Setup 1 Result:", setup_1)
    
    print("\n--- TEST 2: Trade Execution & Winning Equity Update ---")
    # Simulate winning trade (+ $450 profit)
    print(engine.update_account_equity(50450.0))
    
    print("\n--- TEST 3: Evaluating Setup After Win (Trailing Floor Ratcheted) ---")
    setup_2 = engine.evaluate_and_size_entry(
        context_bias="BULLISH",
        primary_structure="BEARISH",  # Misaligned structure!
        trigger_confirmed=True,
        news_event_active=False,
        per_trade_cap=150.0,
        entry_price=4860.00,
        invalidation_price=4850.00
    )
    print("Setup 2 Result (Misaligned Context):", setup_2)

    print("\n--- TEST 4: Simulating Intraday Drawdown & Safety Lock ---")
    # Simulate equity drawdown touching trailing floor ($50,450 peak -> $48,400 equity)
    # Note: High Water Mark reached $50,450. Trailing Floor ratcheted up to $50,450 - $2,000 = $48,450!
    status = engine.update_account_equity(48400.0)
    print("Equity Update Result:", status)
    
    print("\n--- TEST 5: Attempting Entry on Locked Account ---")
    setup_3 = engine.evaluate_and_size_entry(
        context_bias="BULLISH",
        primary_structure="BULLISH",
        trigger_confirmed=True,
        news_event_active=False,
        per_trade_cap=150.0,
        entry_price=4845.00,
        invalidation_price=4840.00
    )
    print("Setup 3 Result (Post-Lock Attempt):", setup_3)
```

---

*End of Reference Document.*
