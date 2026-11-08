# CS101 / PY104 - Week 1 Master Reference: Professional Software Engineering Foundations

Welcome to the CS101 / PY104 Week 1 Master Reference Guide. This authoritative document synthesizes all core programming concepts, mental models, memory mechanics, execution state traces, and defensive engineering practices from this module into a self-contained reference guide. Designed for software engineering rigor, this guide moves beyond basic execution to establish professional standards in modular function design, control flow, and software architecture.

---

## Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

---

## 1. Abstract Foundations & Core Theory

Professional software engineering requires transitioning from unstructured scripts ("making code run") to engineered systems ("building maintainable software"). This section formalizes the core theoretical building blocks introduced in Week 1.

### Core Terminology & Theoretical Definitions

* **Modularity:** The architectural practice of organizing software logic into small, single-purpose, self-contained components (functions or modules). Modularity ensures each logical rule has exactly one source of truth.
* **Duplication Tax:** The exponential maintenance overhead incurred when code blocks or calculation rules are copy-pasted across a codebase. Every duplicate block represents a potential point of failure when business logic updates.
* **Tangled Flow:** A structural anti-pattern where logic for a single feature or concept (e.g., user authentication or discount calculation) is scattered across disparate sections of a file, forcing developers to scan the entire script to reason about a single concern.
* **Single Responsibility Principle (SRP):** A fundamental software design principle dictating that a function or module should have one, and only one, reason to change. Applied to functions, SRP dictates that a routine should perform a single computation, user interaction, or formatting task—never a mixture.
* **The Return Contract:** The explicit agreement of a function to yield a computed data object back to its caller via the `return` statement. Unlike `print()`, which produces a display side-effect on the console output stream, `return` passes data back into the runtime environment for further composition, transformation, or persistence.
* **Function Pipeline:** A design pattern wherein functions are chained sequentially such that the evaluation output of function f(x) is passed directly as the input parameter to function g(x), forming g(f(x)).
* **Main Orchestrator (`main()`):** The central coordinating routine responsible for directing program workflow: collecting raw inputs, invoking specialized helper functions in strict sequence, and handling final user-facing output presentation.
* **Entry Point Guard (`if __name__ == "__main__":`):** A conditional boundary check that inspects Python's built-in `__name__` variable. It guarantees that execution logic inside `main()` triggers only when the module is executed directly as a standalone script, preventing unintended side-effects when imported by external modules.
* **Guard Clause:** A conditional check positioned at the very top of a function body that evaluates input boundary conditions (e.g., type checks, zero divisors, invalid ranges). If invalid data is detected, the guard exits early (often returning `None`), protecting the "happy path" logic below.

### Architectural Component Comparison Matrix

| Feature / Spec | Helper Function | Main Orchestrator (`main()`) | Guard Clause |
| :--- | :--- | :--- | :--- |
| **Primary Definition** | Focused sub-routine performing a single mathematical or logical calculation | High-level coordinating routine controlling overall application control flow | Early conditional assertion at function top validating input parameters |
| **Syntax / Delimiters** | `def helper_name(param1, param2):` terminating in `return` | `def main():` sequencing input, calls, and output | `if not isinstance(var, type): return None` |
| **Primary Responsibility** | Encapsulate domain math, transformations, or discrete evaluation rules | Sequence program steps: prompt input, call helpers, print final summary | Intercept boundary edge cases and prevent execution of invalid logic |
| **Console I/O Boundary** | Pure computation; strictly no `input()` or `print()` calls | Manages console interactions (`input()` calls and formatted `print()`) | Silent boundary intercept; returns safe fallback object without printing |
| **Composition & Reuse** | Highly composable; can be called by multiple orchestration paths | Non-composable; acts as the terminal entry point of application execution | Embedded directly within helpers or orchestrators at entry points |
| **Common Runtime Failure** | `TypeError` if caller supplies incorrect argument types or counts | `UnboundLocalError` / `TypeError` if helper return values are uncaptured | Traps runtime errors (`ZeroDivisionError`, `TypeError`) before they occur |

---

## 2. Real-World Mental Models & Conceptual Mapping

To establish strong intuition for software engineering concepts, we map abstract syntax to physical mental models.

### Analogy 1: The Assembly Line Conveyor Belt (Function Pipelines)
Think of data transformation as a manufacturing assembly line. Raw materials (user input) enter the conveyor belt at stage one. 

```
[ Raw String Input: "100" ]
            |
            v  float()
[ Numeric Value: 100.0 ]
            |
            v  add_tax(price, 0.08)
[ Intermediate Object: 108.0 ]
            |
            v  apply_discount(108.0, 10)
[ Final Computed Total: 97.2 ]
            |
            v  format_currency(97.2)
[ Formatted Output String: "$97.20" ]
```

Each station on the assembly line is a **single-job function**. Station 1 does not attempt to paint the car while welding the frame; it performs its exact task and pushes the modified object to Station 2.

### Analogy 2: The Project Manager and Specialized Craftsmen (Orchestration vs Delegation)
In a professional enterprise:
* **The Project Manager (`main()`):** Speaks directly with the client (collects user input), assigns tasks to specialist craftsmen, receives completed work, and delivers the final project (prints the result). The manager does not perform manual electrical wiring or plumbing.
* **Specialized Craftsmen (Helper Functions):** Highly skilled specialists (e.g., `calculate_tax()`, `compute_grade()`). They do not speak to the client or manage office logistics; they receive exact raw materials (parameters), execute their craft, and hand back finished components (`return`).

```
+-------------------------------------------------------------------------+
|                         main() [Orchestrator]                           |
|  1. Prompts Client: input()                                             |
|  2. Delegates to Craftsman 1: add_tax(100.0, 0.08)                      |
|  3. Delegates to Craftsman 2: apply_discount(108.0, 10)                 |
|  4. Delivers Final Result: print("$97.20")                              |
+-------------------------------------------------------------------------+
             |                                         |
             v (passes parameters)                     v (passes parameters)
+-------------------------+               +-------------------------------+
|   add_tax() [Helper]    |               |   apply_discount() [Helper]   |
| Computes: price + tax   |               | Computes: price - discount    |
| Returns: 108.0          |               | Returns: 97.2                 |
+-------------------------+               +-------------------------------+
```

### Analogy 3: The VIP Security Bouncer (Guard Clauses)
Before guests enter a private venue, a security bouncer stands at the door:
1. **Check 1:** Do you have an ID? (Type validation: `isinstance(x, (int, float))`)
2. **Check 2:** Are you on the ban list? (Value boundary: `x <= 0` or `divisor == 0`)

If any check fails, the bouncer immediately turns the guest away (`return None`). Only valid guests who pass all checks enter the VIP room (the "happy path" calculation logic).

```
   Incoming Input Arguments
              |
              v
  +-----------------------+
  | Guard 1: Valid Type?  | --- NO ---> [ Return None Immediately ]
  +-----------------------+
              | YES
              v
  +-----------------------+
  | Guard 2: Non-Zero?    | --- NO ---> [ Return None Immediately ]
  +-----------------------+
              | YES
              v
  +-------------------------------------------------------------+
  |                    THE HAPPY PATH                           |
  | Execute core business logic and return valid calculation    |
  +-------------------------------------------------------------+
```

---

## 3. Idiomatic Python Implementation & State Tracing

Every code snippet in this section illustrates professional Python coding standards. Step-by-step state changes, variable values, and terminal outputs are annotated directly inline.

### 3.1 Console I/O, Type Casting, and Input Processing

```python
def capture_numeric_price() -> float:
    # Prompt user for input and cast safely to floating-point number
    raw_prompt: str = "150.50"  # Simulated console input: "150.50"
    # State: raw_prompt = "150.50" (type: str)

    parsed_price: float = float(raw_prompt)
    # Evaluation: float("150.50") -> 150.5
    # State: parsed_price = 150.5 (type: float)

    return parsed_price
    # Returns: 150.5
```

### 3.2 Single Responsibility Principle (SRP) & Pure Functions

```python
def calculate_subtotal(quantity: int, unit_price: float) -> float:
    # Calculate raw subtotal without I/O side effects (Pure Math Job)
    subtotal: float = quantity * unit_price
    # State: quantity = 4, unit_price = 25.0
    # Evaluation: 4 * 25.0 -> 100.0
    # State: subtotal = 100.0 (type: float)

    return subtotal
    # Returns: 100.0


def format_subtotal_display(subtotal: float) -> str:
    # Format numeric subtotal for display (Formatting Job)
    formatted_string: str = f"Subtotal: ${subtotal:.2f}"
    # Evaluation: f"Subtotal: ${100.0:.2f}" -> "Subtotal: $100.00"
    # State: formatted_string = "Subtotal: $100.00" (type: str)

    return formatted_string
    # Returns: "Subtotal: $100.00"
```

### 3.3 Guard Clauses & Defensive Filtering (The 6 Edge-Case Buckets)

The six primary edge-case buckets that software engineers guard against are:
1. **Empty:** `""` or `[]`
2. **Zero:** `0` or `0.0`
3. **Negative:** `-1` or `-99.9`
4. **Extreme / Big:** `10_000_000`
5. **None:** `None`
6. **Wrong Type:** `"abc"` passed to numeric math

```python
def safe_calculate_velocity(distance: float, time: float) -> float | None:
    # Calculate velocity (distance / time) with complete edge-case guarding
    # Guard Bucket 6 & 5: Wrong Type / None
    if not isinstance(distance, (int, float)) or not isinstance(time, (int, float)):
        return None  # State: Trapped invalid type (e.g. str or None)

    # Guard Bucket 2 & 3: Zero / Negative Time
    if time <= 0:
        return None  # State: Trapped zero or negative time value

    # Guard Bucket 3: Negative Distance
    if distance < 0:
        return None  # State: Trapped negative distance

    # Happy Path Logic
    velocity: float = distance / time
    # State (for distance=100.0, time=20.0): 100.0 / 20.0 -> 5.0
    return velocity
    # Terminal Output / Return: 5.0
```

### 3.4 Function Pipelines & Composition

```python
def add_sales_tax(amount: float, tax_rate_percent: float) -> float:
    # Pipeline Stage 1: Add sales tax to base price
    tax_multiplier: float = 1.0 + (tax_rate_percent / 100.0)
    # Evaluation for (100.0, 8.0): 1.0 + (8.0 / 100.0) -> 1.08
    return amount * tax_multiplier
    # Returns: 100.0 * 1.08 = 108.0


def apply_promotional_discount(amount: float, discount_percent: float) -> float:
    # Pipeline Stage 2: Apply percentage discount to taxed price
    discount_multiplier: float = 1.0 - (discount_percent / 100.0)
    # Evaluation for (108.0, 10.0): 1.0 - (10.0 / 100.0) -> 0.90
    return amount * discount_multiplier
    # Returns: 108.0 * 0.90 = 97.2


# Execution Trace - Sequential Variables vs Nested Calls
base_price: float = 100.0  # State: base_price = 100.0

# Approach A: Sequential Intermediate Variables (Explicit State)
stage1_price: float = add_sales_tax(base_price, 8.0)
# State: stage1_price = 108.0

stage2_price: float = apply_promotional_discount(stage1_price, 10.0)
# State: stage2_price = 97.2

# Approach B: Nested Call Composition (Inner evaluation runs first)
nested_final_price: float = apply_promotional_discount(
    add_sales_tax(base_price, 8.0), 10.0
)
# Inner Evaluation: add_sales_tax(100.0, 8.0) -> 108.0
# Outer Evaluation: apply_promotional_discount(108.0, 10.0) -> 97.2
# State: nested_final_price = 97.2
```

---

## 4. Defensive Programming & Common Traps

This section documents common execution bugs, runtime exceptions, and anti-patterns encountered by developers, paired with idiomatic fixes.

### Trap 1: The Print vs Return Traversal Bug (`TypeError`)

```python
# INCORRECT: Function prints value but returns implicit None
def calculate_tax_bad(price: float) -> float:
    tax = price * 0.08
    print(tax)  # Displays 8.0 to console, but function returns None!


def main_bad():
    base = 100.0
    tax_amount = calculate_tax_bad(base)  # State: tax_amount = None
    total = base + tax_amount
    # RUNTIME EXCEPTION: TypeError: unsupported operand type(s) for +: 'float' and 'NoneType'


# CORRECT: Function returns computed value to caller
def calculate_tax_good(price: float) -> float:
    tax: float = price * 0.08
    return tax  # Yields float object back to caller


def main_good():
    base: float = 100.0
    tax_amount: float = calculate_tax_good(base)  # State: tax_amount = 8.0
    total: float = base + tax_amount  # Evaluation: 100.0 + 8.0 -> 108.0
    print(f"Total: ${total:.2f}")  # Terminal Output: "Total: $108.00"
```

### Trap 2: Direct Arithmetic on Raw Strings (`TypeError`)

```python
# INCORRECT: Attempting math on string input
def process_order_bad():
    raw_quantity = "5"  # Simulated input()
    raw_price = "10.0"  # Simulated input()
    total = raw_quantity * raw_price
    # RUNTIME EXCEPTION: TypeError: can't multiply sequence by non-int of type 'str'


# CORRECT: Explicit conversion to numeric primitives
def process_order_good():
    raw_quantity: str = "5"
    raw_price: str = "10.0"
    quantity: int = int(raw_quantity)  # State: quantity = 5
    unit_price: float = float(raw_price)  # State: unit_price = 10.0
    total: float = quantity * unit_price  # Evaluation: 5 * 10.0 -> 50.0
    return total  # Returns: 50.0
```

### Trap 3: Unprotected Division and Missing Type Checks (`ZeroDivisionError`)

```python
# INCORRECT: Unprotected division crashes on edge case 0
def compute_ratio_bad(a, b):
    return a / b  # Crashes if b == 0 or if a/b are strings


# RUNTIME EXCEPTION when b = 0: ZeroDivisionError: division by zero
# RUNTIME EXCEPTION when a = "10": TypeError: unsupported operand type(s) for /: 'str' and 'int'


# CORRECT: Defensive Guard Clauses at boundary
def compute_ratio_good(a: float, b: float) -> float | None:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None  # Traps wrong type safely
    if b == 0:
        return None  # Traps zero divisor safely
    return a / b  # Executes only when inputs are valid numbers
```

### Trap 4: Entry Point Double Execution / Unintended Script Execution

```python
# INCORRECT: Calling main() unconditionally at module level
def main():
    print("Executing core script logic...")


main()  # Call executed automatically upon import by external files!


# CORRECT: Idiomatic Entry Point Guard
def main():
    print("Executing core script logic...")


if __name__ == "__main__":
    main()  # Triggered ONLY when file is run directly (python file.py)
```

---

## 5. Python Memory Mechanics, References & Scope

Understanding Python's runtime execution model requires peering into how Python manages namespaces, stack frames, and object references in heap memory.

### Key Memory Principles
1. **Dynamic Typing & Variable Binding:** In Python, variables are not typed storage containers. A variable name is merely a symbolic reference (a name tag or pointer) bound to a typed object residing in heap memory.
2. **Assignment (`=`) Behavior:** Assignment evaluates the right-hand expression to produce an object in heap memory, then binds the name on the left-hand side to that object's memory address.
3. **Pass-by-Object-Reference:** When arguments are passed into functions, Python binds local parameter names inside the function's stack frame to the existing objects in heap memory.
4. **Scope Resolution & Call Stack:** Local variables exist only within their function's stack frame. When a function returns, its frame is popped off the stack, and local bindings are deallocated.

### Namespace to Heap Memory Layout Diagram

```
[ Local Stack Frame: main() ]               [ Heap Memory (Typed Objects) ]
+---------------------------+               +-----------------------------+
| price_ref                 | ------------> | PyFloatObject               |
|                           |               |   value: 100.0              |
|                           |               |   ref_count: 2              |
+---------------------------+               +-----------------------------+
              |                                            ^
              | (Passes reference)                         |
              v                                            |
[ Local Stack Frame: add_tax() ]                           |
+---------------------------+                              |
| price (parameter)         | -----------------------------+
|                           |
| tax_rate (parameter)      | ------------> | PyFloatObject               |
|                           |               |   value: 8.0                |
|                           |               +-----------------------------+
|                           |
| total_result              | ------------> | PyFloatObject               |
|                           |               |   value: 108.0              |
+---------------------------+               +-----------------------------+
```

---

## 6. Practical Integration / Mini Case Study

This case study integrates all core principles into a robust, professional transaction calculator module (`transaction_processor.py`). It enforces guard clauses across all six edge-case buckets, utilizes single-purpose helpers, chains a function pipeline, uses an orchestrator `main()`, and concludes with the `if __name__ == "__main__":` entry point guard.

```python
"""
transaction_processor.py
A professional Python transaction processing module demonstrating modular architecture,
guard clauses, function pipelines, and entry point protection.
"""


# --- HELPER 1: Guarded Tax Calculation ---
def calculate_tax(price: float, tax_rate_percent: float) -> float | None:
    # Calculate price with tax added. Guards against: Wrong Type, None, Negative numbers.
    # Guard 1: Type Validation (Wrong Type / None)
    if not isinstance(price, (int, float)) or not isinstance(
        tax_rate_percent, (int, float)
    ):
        return None

    # Guard 2: Negative Value Checks
    if price < 0 or tax_rate_percent < 0:
        return None

    # Happy Path Calculation
    tax_multiplier: float = 1.0 + (tax_rate_percent / 100.0)
    return price * tax_multiplier


# --- HELPER 2: Guarded Discount Application ---
def apply_discount(
    taxed_price: float, discount_percent: float
) -> float | None:
    # Apply percentage discount to a price. Guards against: Wrong Type, None, Out-of-bounds percentages.
    # Guard 1: Type Validation
    if not isinstance(taxed_price, (int, float)) or not isinstance(
        discount_percent, (int, float)
    ):
        return None

    # Guard 2: Range Validation (Discount between 0% and 100%, price >= 0)
    if taxed_price < 0 or discount_percent < 0 or discount_percent > 100:
        return None

    # Happy Path Calculation
    discount_multiplier: float = 1.0 - (discount_percent / 100.0)
    return taxed_price * discount_multiplier


# --- HELPER 3: Currency Display Formatter ---
def format_currency(amount: float) -> str | None:
    # Format a floating point number as USD currency string
    if not isinstance(amount, (int, float)) or amount < 0:
        return None
    return f"${amount:.2f}"


# --- MAIN ORCHESTRATOR ---
def main() -> None:
    # Orchestrate transaction user input, pipeline calls, and output presentation
    print("=== PROFESSIONAL TRANSACTION PROCESSOR ===")

    # Step 1: Simulate or collect user inputs (Simulated for diagnostic execution)
    raw_price_str: str = "200.0"
    raw_tax_str: str = "7.5"
    raw_discount_str: str = "15.0"

    # Step 2: Convert and validate input types at boundary
    try:
        base_price: float = float(raw_price_str)
        tax_rate: float = float(raw_tax_str)
        discount_pct: float = float(raw_discount_str)
    except ValueError:
        print("Error: Input conversion failed. Invalid numeric format.")
        return

    # Step 3: Execute Function Pipeline
    # Pipeline Stage A: Add Tax
    price_after_tax: float | None = calculate_tax(base_price, tax_rate)
    if price_after_tax is None:
        print("Error: Tax calculation failed due to invalid arguments.")
        return

    # Pipeline Stage B: Apply Discount
    final_price: float | None = apply_discount(price_after_tax, discount_pct)
    if final_price is None:
        print("Error: Discount application failed due to invalid arguments.")
        return

    # Pipeline Stage C: Format Display Output
    formatted_total: str | None = format_currency(final_price)
    if formatted_total is None:
        print("Error: Currency formatting failed.")
        return

    # Step 4: Display Summary Output
    print(f"Base Price:    ${base_price:.2f}")
    print(f"After Tax:     ${price_after_tax:.2f}")
    print(f"Final Total:   {formatted_total}")
    print("==========================================")


# --- ENTRY POINT GUARD ---
if __name__ == "__main__":
    main()
```

### Complete Execution Trace Table for `transaction_processor.py`

| Line # | Statement Executed | Local Variables & State Changes | Evaluated Result / Output |
| :--- | :--- | :--- | :--- |
| `81` | `main()` invoked | Scope enters `main()` frame | Orchestration begins |
| `86` | `raw_price_str = "200.0"` | `raw_price_str: "200.0"` | Literal string assignment |
| `92` | `base_price = float("200.0")` | `base_price: 200.0` | String cast to `float` |
| `93` | `tax_rate = float("7.5")` | `tax_rate: 7.5` | String cast to `float` |
| `94` | `discount_pct = float("15.0")` | `discount_pct: 15.0` | String cast to `float` |
| `100` | `calculate_tax(200.0, 7.5)` | Scope enters `calculate_tax()` | Guards pass (`200.0 >= 0`) |
| `18` | `200.0 * (1 + 7.5/100)` | `tax_multiplier: 1.075` | `200.0 * 1.075 -> 215.0` |
| `100` | `price_after_tax = 215.0` | `price_after_tax: 215.0` | Assigned return value |
| `106` | `apply_discount(215.0, 15.0)` | Scope enters `apply_discount()` | Guards pass (`15.0 <= 100`) |
| `45` | `215.0 * (1 - 15.0/100)` | `discount_multiplier: 0.85` | `215.0 * 0.85 -> 182.75` |
| `106` | `final_price = 182.75` | `final_price: 182.75` | Assigned return value |
| `112` | `format_currency(182.75)` | Scope enters `format_currency()` | `f"${182.75:.2f}" -> "$182.75"` |
| `112` | `formatted_total = "$182.75"` | `formatted_total: "$182.75"` | Assigned return string |
| `118` | `print(...)` statements | Reading scope variables | Console Output printed |

#### Final Terminal Output
```
=== PROFESSIONAL TRANSACTION PROCESSOR ===
Base Price:    $200.00
After Tax:     $215.00
Final Total:   $182.75
==========================================
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

This section presents four diagnostic tracing challenges involving order of operations, guard short-circuiting, scope behavior, and pipeline composition.

### Challenge A: Nested Pipeline Evaluation Order

```python
def fn_alpha(x: int) -> int:
    return x + 3


def fn_beta(y: int) -> int:
    return y * 2


def fn_gamma(z: int) -> int:
    return z - 5


# Diagnostic Call
initial_val: int = 4
result_a: int = fn_gamma(fn_beta(fn_alpha(initial_val)))
print(f"Result A: {result_a}")
```

#### Line-by-Line Execution Trace
1. `initial_val` is initialized to `4`.
2. Evaluation of `fn_gamma(fn_beta(fn_alpha(4)))` begins from the innermost parentheses:
   * **Step 1 (Innermost):** `fn_alpha(4)` executes -> 4 + 3 = 7.
   * **Step 2 (Middle):** `fn_beta(7)` executes -> 7 * 2 = 14.
   * **Step 3 (Outermost):** `fn_gamma(14)` executes -> 14 - 5 = 9.
3. `result_a` is bound to integer object `9`.

#### Final Terminal Output
```
Result A: 9
```

---

### Challenge B: Guard Clause Short-Circuit Trapping

```python
def process_data(val) -> str:
    # Guard 1: Type check
    if not isinstance(val, (int, float)):
        return "ERROR: INVALID_TYPE"

    # Guard 2: Boundary check
    if val <= 0:
        return "ERROR: NON_POSITIVE"

    return f"VALID: {val * 2}"


# Diagnostic Inputs
out_1 = process_data("50")
out_2 = process_data(-10)
out_3 = process_data(25)

print(f"1: {out_1} | 2: {out_2} | 3: {out_3}")
```

#### Line-by-Line Execution Trace
1. `process_data("50")`: Argument `"50"` is `str`. Guard 1 triggers (`not isinstance("50", (int, float))` is `True`). Returns `"ERROR: INVALID_TYPE"` immediately. Guard 2 is skipped.
2. `process_data(-10)`: Argument `-10` is `int`. Guard 1 passes. Guard 2 triggers (`-10 <= 0` is `True`). Returns `"ERROR: NON_POSITIVE"`.
3. `process_data(25)`: Argument `25` is `int`. Guard 1 passes (`True`). Guard 2 passes (`25 <= 0` is `False`). Reaches Happy Path -> evaluates `f"VALID: {25 * 2}"` -> returns `"VALID: 50"`.

#### Final Terminal Output
```
1: ERROR: INVALID_TYPE | 2: ERROR: NON_POSITIVE | 3: VALID: 50
```

---

### Challenge C: Variable Reassignment & Scope Isolation

```python
def increment_counter(count: int) -> int:
    count = count + 1
    return count


main_count: int = 10
returned_count: int = increment_counter(main_count)

print(f"main_count: {main_count} | returned_count: {returned_count}")
```

#### Line-by-Line Execution Trace
1. `main_count` is assigned `10` in module scope.
2. `increment_counter(main_count)` is called, passing reference to `10`. Local parameter `count` inside function frame is bound to `10`.
3. Inside function frame: `count + 1` evaluates to `11`. Local name `count` is rebound to new integer object `11`. Module-level `main_count` remains untouched at `10`.
4. Function returns `11`, which is assigned to `returned_count` in module scope.
5. `main_count` evaluates to `10`; `returned_count` evaluates to `11`.

#### Final Terminal Output
```
main_count: 10 | returned_count: 11
```

---

### Challenge D: Pipeline Non-Commutative Operations

```python
def add_flat_fee(amount: float) -> float:
    return amount + 15.0


def apply_percent_discount(amount: float) -> float:
    return amount * 0.80  # 20% discount


start_price: float = 100.0

# Pipeline 1: Fee First, Then Discount
p1_result = apply_percent_discount(add_flat_fee(start_price))

# Pipeline 2: Discount First, Then Fee
p2_result = add_flat_fee(apply_percent_discount(start_price))

print(f"Pipeline 1: {p1_result:.2f} | Pipeline 2: {p2_result:.2f}")
```

#### Line-by-Line Execution Trace
1. `start_price` initialized to `100.0`.
2. **Pipeline 1 (`p1_result`):**
   * Inner call: `add_flat_fee(100.0)` -> 100.0 + 15.0 = 115.0.
   * Outer call: `apply_percent_discount(115.0)` -> 115.0 * 0.80 = 92.0.
   * `p1_result` = `92.0`.
3. **Pipeline 2 (`p2_result`):**
   * Inner call: `apply_percent_discount(100.0)` -> 100.0 * 0.80 = 80.0.
   * Outer call: `add_flat_fee(80.0)` -> 80.0 + 15.0 = 95.0.
   * `p2_result` = `95.0`.

#### Final Terminal Output
```
Pipeline 1: 92.00 | Pipeline 2: 95.00
```

---

*CS101 / PY104 Week 1 Master Reference Guide. All code examples verified for syntax and runtime validity.*
