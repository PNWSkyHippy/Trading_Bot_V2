# PY104: Complete Course Master Reference & Technical Manual

*Welcome blurb: The complete, unabridged compilation of all 4 weeks of Python Foundations, covering console I/O, primitives, memory mechanics, control structures, and collections.*

## Master Course-Wide Index

- **Course Overview & Cross-Reference**
  - Welcome & Course Scope
  - Unified Course Cross-Reference Matrix
- **PART I: WEEK 1 - Professional Software Engineering Foundations**
  - 1. Abstract Foundations & Core Theory
    - Core Terminology & Theoretical Definitions
    - Architectural Component Comparison Matrix
  - 2. Real-World Mental Models & Conceptual Mapping
    - Analogy 1: The Assembly Line Conveyor Belt (Function Pipelines)
    - Analogy 2: The Project Manager and Specialized Craftsmen (Orchestration vs Delegation)
    - Analogy 3: The VIP Security Bouncer (Guard Clauses)
  - 3. Idiomatic Python Implementation & State Tracing
    - 3.1 Console I/O, Type Casting, and Input Processing
    - 3.2 Single Responsibility Principle (SRP) & Pure Functions
    - 3.3 Guard Clauses & Defensive Filtering (The 6 Edge-Case Buckets)
    - 3.4 Function Pipelines & Composition
  - 4. Defensive Programming & Common Traps
    - Trap 1: The Print vs Return Traversal Bug (TypeError)
    - Trap 2: Direct Arithmetic on Raw Strings (TypeError)
    - Trap 3: Unprotected Division and Missing Type Checks (ZeroDivisionError)
    - Trap 4: Entry Point Double Execution / Unintended Script Execution
  - 5. Python Memory Mechanics, References & Scope
    - Key Memory Principles
    - Namespace to Heap Memory Layout Diagram
  - 6. Practical Integration / Mini Case Study
    - transaction_processor.py
    - Complete Execution Trace Table for transaction_processor.py
    - Final Terminal Output
  - 7. Step-by-Step Code Tracing Challenges & Diagnostics
    - Challenge A: Nested Pipeline Evaluation Order
    - Challenge B: Guard Clause Short-Circuit Trapping
    - Challenge C: Variable Reassignment & Scope Isolation
    - Challenge D: Pipeline Non-Commutative Operations
- **PART II: WEEK 2 - Dictionaries, Data Retrieval, and Loop Integration**
  - 1. Abstract Foundations & Core Theory
    - Primary Data Types, Operations, and Keywords
    - Side-by-Side Comparison Matrix
  - 2. Real-World Mental Models & Conceptual Mapping
    - Analogy 1: The Labeled Drawer Array vs. Unmarked Storage Cubbies
    - Analogy 2: Parallel List Index Juggling vs. Single Bound File Folders
    - Analogy 3: The Assembly Line and the Station Specialist
  - 3. Idiomatic Python Implementation & State Tracing
    - Domain A: Dictionary Creation, Direct Access, and Safe Lookup
    - Domain B: Dictionary Iteration Views (.keys(), .values(), .items())
    - Domain C: Advanced Dictionary Patterns (Counting, Accumulation, Grouping)
    - Domain D: Loop Control, State Tracking, and Short-Circuiting
    - Domain E: Modular Loop Processing via Helper Functions
  - 4. Defensive Programming & Common Traps
    - Trap 1: Missing Key Direct Access (KeyError)
    - Trap 2: Attempting Value Assignment to Method Call
    - Trap 3: Tuple Iteration Bug vs. Full Index Range Scanning
    - Trap 4: Set Literal Instantiation Mismatch in Data Structures
    - Trap 5: Omitting Return Statements in Modular Helper Functions
  - 5. Python Memory Mechanics, References & Scope
    - Variable Bindings and the Object Heap
    - Dictionary Hash Tables & Mutability Invariants
  - 6. Practical Integration / Mini Case Study
    - E-Commerce Audit & Telemetry Processor
  - 7. Step-by-Step Code Tracing Challenges & Diagnostics
    - Challenge A: Safe Lookup & State Mutation Order
    - Challenge B: Short-Circuit Loop with Accumulator & Flag State
    - Challenge C: Multi-Pattern Counting & Grouping Diagnostic
    - Challenge D: Helper Function Delegation & List Transformation
- **PART III: WEEK 3 - Advanced Data Structures, Filtering, Grouping & Functional Pipelines**
  - 1. Abstract Foundations & Core Theory
    - Primary Data Structures and Operations
    - Side-by-Side Comparison Matrix
  - 2. Real-World Mental Models & Conceptual Mapping
    - 1. The Spreadsheet Table vs. The Labeled Storage Bins
    - 2. The Linear Grid Search vs. The Phonebook Index
    - 3. The Conveyor Belt Assembly Line (Functional Pipelines & Helpers)
    - Concept Visualizations
  - 3. Idiomatic Python Implementation & State Tracing
    - Topic 1: The Scan-Test-Store Filter Pattern
    - Topic 2: Incremental Grouping (Building a Dictionary of Lists)
    - Topic 3: Building a Dictionary Index to Replace Nested Loops
    - Topic 4: Functional Pipelines & Call Chaining
    - Topic 5: Loop Skeleton vs. Per-Item Helper Interaction
  - 4. Defensive Programming & Common Traps
    - Trap 1: KeyError from Accessing Uninitialized Dictionary Buckets
    - Trap 2: KeyError and Shape Mismatch in Dictionary Lookups
    - Trap 3: Mathematical Multiplier Errors (Percentage vs. Decimal)
    - Trap 4: Variable Shadowing Built-in Functions
    - Trap 5: Moving Iteration Control into a Per-Item Helper
  - 5. Python Memory Mechanics, References & Scope
    - Dynamic Typing and Variable Binding
    - Composite Structures as Reference Containers
    - Function Scope and Object Mutability
    - Heap Memory & Namespaces Diagram
  - 6. Practical Integration / Mini Case Study
    - Integrated Retail Order & Inventory State Manager
  - 7. Step-by-Step Code Tracing Challenges & Diagnostics
    - Challenge A: Nested Pipeline with State Mutability & Decimals
    - Challenge B: Incremental Grouping with Key Initializations
    - Challenge C: Dictionary Index vs. Nested Loop Comparison Counter
    - Challenge D: Dual Accumulators in Loop Skeleton with Per-Item Helper
- **PART IV: WEEK 4 - Foundations of Software Engineering & The Full Development Pipeline**
  - 1. Abstract Foundations & Core Theory
    - Specification & The Four Pillars ("Thinking Before Typing")
    - Acceptance Criteria & Definition of "Done"
    - Pseudocode: The Plain-Language Recipe
    - Incremental Implementation & Micro-Verification Loops
    - Pipeline Integration & Helper Function Orchestration
    - Side-by-Side Architectural Comparison Matrix
  - 2. Real-World Mental Models & Conceptual Mapping
    - Conceptual Analogy 1: The Subway Sandwich Recipe
    - Conceptual Analogy 2: Quality Assurance & Customs Border Control
    - Conceptual Analogy 3: Factory Assembly Line & Helper Relay
    - Figure 2.1: The Full Development Pipeline Architecture
    - Figure 2.2: The Micro-Verification Loop
  - 3. Idiomatic Python Implementation & State Tracing
    - Topic A: Translating Pseudocode to Python Flow
    - Topic B: Boundary Verification & Acceptance Criteria Enforcement
    - Topic C: Incremental Implementation with Assert Stubs
  - 4. Defensive Programming & Common Traps
    - Trap 1: F-String Quote Reuse Syntax Error
    - Trap 2: Dictionary Accumulator Reset Bug
    - Trap 3: Global Parameter Shadowing in Helper Functions
    - Trap 4: Work Inside the Iteration Loop (Loop Misplacement)
  - 5. Python Memory Mechanics, References & Scope
    - Dynamic Typing, Variable Binding, and Namespace Mapping
    - Memory Visualization Diagram
  - 6. Practical Integration / Mini Case Study
    - CS101 Module 4: Automated Shopping Cart & Shipping Pipeline System
  - 7. Step-by-Step Code Tracing Challenges & Diagnostics
    - Challenge A: Boundary Evaluation in Multi-Branch Logic
    - Challenge B: Dictionary Frequency Counter State Mutation
    - Challenge C: Conditional Filtering and Accumulation Trace
    - Challenge D: Nested Helper Dispatch & Summary Aggregation

## Unified Course Cross-Reference Matrix

| Concept / Paradigm | Primitives & Console I/O (Week 1) | Dictionaries & Loop Control (Week 2) | Advanced Structures & Pipelines (Week 3) | Full Engineering Pipeline (Week 4) |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Data Constructs** | Primitive types (`int`, `float`, `str`, `bool`) | Dictionaries (`dict`), key-value pairs, list sequences | Nested structures (`List[Dict]`, `Dict[List]`, `Dict[Key, Dict]`) | Input records, domain constants, summary manifests |
| **Data Access Pattern** | Direct variable access & explicit type casting | Key-based hash lookup ($O(1)$) vs index search ($O(N)$) | Direct primary index jump ($O(1)$) vs scan-test-store filter | Guarded parameter access & validated dictionary lookups |
| **Control Flow Mechanics** | Guard clauses, early return, function pipelines | `for` loops, `break` short-circuiting, boolean flags | Scan-test-store filtering, category grouping, pipeline chaining | Spec-driven conditional branches, assertion boundary checks |
| **Scope & Modular Design** | Single Responsibility Principle (SRP), helper functions, `main()` orchestrator, `if __name__ == "__main__":` guard | Loop skeleton with helper delegation, pure transformers | Separation of iteration skeleton from per-item helper processing | Pure helper functions, main pipeline orchestrator, module domain constants |
| **Memory & Binding Model** | Stack frame allocation, dynamic variable binding to heap primitives | Mutable dict objects on heap, hashable immutable keys, in-place key mutation | Memory reference containers, pass-by-assignment mutable mutation | Call-by-object-reference across stack frames, local vs global scope isolation |
| **Defensive Engineering** | 6 Edge-case buckets (empty, zero, negative, extreme, None, wrong type) | Safe lookup (`.get()`), membership checks (`in`), return statement preservation | KeyError protection, safe bucket initialization, decimal multiplier precision | 4-Pillar specification, acceptance criteria, micro-verification `assert` testing |

---
## PART I: WEEK 1 - Professional Software Engineering Foundations

### CS101 / PY104 - Week 1 Master Reference: Professional Software Engineering Foundations
Welcome to the CS101 / PY104 Week 1 Master Reference Guide. This authoritative document synthesizes all core programming concepts, mental models, memory mechanics, execution state traces, and defensive engineering practices from this module into a self-contained reference guide. Designed for software engineering rigor, this guide moves beyond basic execution to establish professional standards in modular function design, control flow, and software architecture.

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

--------------------------------------------------------------------------------

#### 1. Abstract Foundations & Core Theory
Professional software engineering requires transitioning from unstructured scripts ("making code run") to engineered systems ("building maintainable software"). This section formalizes the core theoretical building blocks introduced in Week 1.

##### Core Terminology & Theoretical Definitions
*   **Modularity:** The architectural practice of organizing software logic into small, single-purpose, self-contained components (functions or modules). Modularity ensures each logical rule has exactly one source of truth.
*   **Duplication Tax:** The exponential maintenance overhead incurred when code blocks or calculation rules are copy-pasted across a codebase. Every duplicate block represents a potential point of failure when business logic updates.
*   **Tangled Flow:** A structural anti-pattern where logic for a single feature or concept (e.g., user authentication or discount calculation) is scattered across disparate sections of a file, forcing developers to scan the entire script to reason about a single concern.
*   **Single Responsibility Principle (SRP):** A fundamental software design principle dictating that a function or module should have one, and only one, reason to change. Applied to functions, SRP dictates that a routine should perform a single computation, user interaction, or formatting task—never a mixture.
*   **The Return Contract:** The explicit agreement of a function to yield a computed data object back to its caller via the return statement. Unlike print(), which produces a display side-effect on the console output stream, return passes data back into the runtime environment for further composition, transformation, or persistence.
*   **Function Pipeline:** A design pattern wherein functions are chained sequentially such that the evaluation output of function f(x) is passed directly as the input parameter to function g(x), forming g(f(x)).
*   **Main Orchestrator (** `main()` **):** The central coordinating routine responsible for directing program workflow: collecting raw inputs, invoking specialized helper functions in strict sequence, and handling final user-facing output presentation.
*   **Entry Point Guard (** `if __name__ == "__main__":` **):** A conditional boundary check that inspects Python's built-in __name__ variable. It guarantees that execution logic inside main() triggers only when the module is executed directly as a standalone script, preventing unintended side-effects when imported by external modules.
*   **Guard Clause:** A conditional check positioned at the very top of a function body that evaluates input boundary conditions (e.g., type checks, zero divisors, invalid ranges). If invalid data is detected, the guard exits early (often returning None), protecting the "happy path" logic below.

##### Architectural Component Comparison Matrix
| Feature / Spec | Helper Function | Main Orchestrator (main()) | Guard Clause |
| ------ | ------ | ------ | ------ |
| **Primary Definition** | Focused sub-routine performing a single mathematical or logical calculation | High-level coordinating routine controlling overall application control flow | Early conditional assertion at function top validating input parameters |
| **Syntax / Delimiters** | def helper_name(param1, param2): terminating in return | def main(): sequencing input, calls, and output | if not isinstance(var, type): return None |
| **Primary Responsibility** | Encapsulate domain math, transformations, or discrete evaluation rules | Sequence program steps: prompt input, call helpers, print final summary | Intercept boundary edge cases and prevent execution of invalid logic |
| **Console I/O Boundary** | Pure computation; strictly no input() or print() calls | Manages console interactions (input() calls and formatted print()) | Silent boundary intercept; returns safe fallback object without printing |
| **Composition & Reuse** | Highly composable; can be called by multiple orchestration paths | Non-composable; acts as the terminal entry point of application execution | Embedded directly within helpers or orchestrators at entry points |
| **Common Runtime Failure** | TypeError if caller supplies incorrect argument types or counts | UnboundLocalError / TypeError if helper return values are uncaptured | Traps runtime errors (ZeroDivisionError, TypeError) before they occur |

--------------------------------------------------------------------------------

#### 2. Real-World Mental Models & Conceptual Mapping
To establish strong intuition for software engineering concepts, we map abstract syntax to physical mental models.

##### Analogy 1: The Assembly Line Conveyor Belt (Function Pipelines)
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

##### Analogy 2: The Project Manager and Specialized Craftsmen (Orchestration vs Delegation)
In a professional enterprise:
*   **The Project Manager (** `main()` **):** Speaks directly with the client (collects user input), assigns tasks to specialist craftsmen, receives completed work, and delivers the final project (prints the result). The manager does not perform manual electrical wiring or plumbing.
*   **Specialized Craftsmen (Helper Functions):** Highly skilled specialists (e.g., calculate_tax(), compute_grade()). They do not speak to the client or manage office logistics; they receive exact raw materials (parameters), execute their craft, and hand back finished components (return).

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

##### Analogy 3: The VIP Security Bouncer (Guard Clauses)
Before guests enter a private venue, a security bouncer stands at the door:
1.  **Check 1:** Do you have an ID? (Type validation: isinstance(x, (int, float)))
2.  **Check 2:** Are you on the ban list? (Value boundary: x <= 0 or divisor == 0)
If any check fails, the bouncer immediately turns the guest away (return None). Only valid guests who pass all checks enter the VIP room (the "happy path" calculation logic).

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

--------------------------------------------------------------------------------

#### 3. Idiomatic Python Implementation & State Tracing
Every code snippet in this section illustrates professional Python coding standards. Step-by-step state changes, variable values, and terminal outputs are annotated directly inline.

##### 3.1 Console I/O, Type Casting, and Input Processing
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

##### 3.2 Single Responsibility Principle (SRP) & Pure Functions
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

##### 3.3 Guard Clauses & Defensive Filtering (The 6 Edge-Case Buckets)
The six primary edge-case buckets that software engineers guard against are:
1.  **Empty:** "" or []
2.  **Zero:** 0 or 0.0
3.  **Negative:** -1 or -99.9
4.  **Extreme / Big:** 10_000_000
5.  **None:** None
6.  **Wrong Type:** "abc" passed to numeric math

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

##### 3.4 Function Pipelines & Composition
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

--------------------------------------------------------------------------------

#### 4. Defensive Programming & Common Traps
This section documents common execution bugs, runtime exceptions, and anti-patterns encountered by developers, paired with idiomatic fixes.

##### Trap 1: The Print vs Return Traversal Bug (TypeError)
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

##### Trap 2: Direct Arithmetic on Raw Strings (TypeError)
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

##### Trap 3: Unprotected Division and Missing Type Checks (ZeroDivisionError)
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

##### Trap 4: Entry Point Double Execution / Unintended Script Execution
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

--------------------------------------------------------------------------------

#### 5. Python Memory Mechanics, References & Scope
Understanding Python's runtime execution model requires peering into how Python manages namespaces, stack frames, and object references in heap memory.

##### Key Memory Principles
1.  **Dynamic Typing & Variable Binding:** In Python, variables are not typed storage containers. A variable name is merely a symbolic reference (a name tag or pointer) bound to a typed object residing in heap memory.
2.  **Assignment (** `=` **) Behavior:** Assignment evaluates the right-hand expression to produce an object in heap memory, then binds the name on the left-hand side to that object's memory address.
3.  **Pass-by-Object-Reference:** When arguments are passed into functions, Python binds local parameter names inside the function's stack frame to the existing objects in heap memory.
4.  **Scope Resolution & Call Stack:** Local variables exist only within their function's stack frame. When a function returns, its frame is popped off the stack, and local bindings are deallocated.

##### Namespace to Heap Memory Layout Diagram
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

--------------------------------------------------------------------------------

#### 6. Practical Integration / Mini Case Study
This case study integrates all core principles into a robust, professional transaction calculator module (`transaction_processor.py`). It enforces guard clauses across all six edge-case buckets, utilizes single-purpose helpers, chains a function pipeline, uses an orchestrator main(), and concludes with the `if __name__ == "__main__":` entry point guard.

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

##### Complete Execution Trace Table for transaction_processor.py
| Line # | Statement Executed | Local Variables & State Changes | Evaluated Result / Output |
| ------ | ------ | ------ | ------ |
| 81 | main() invoked | Scope enters main() frame | Orchestration begins |
| 86 | raw_price_str = "200.0" | raw_price_str: "200.0" | Literal string assignment |
| 92 | base_price = float("200.0") | base_price: 200.0 | String cast to float |
| 93 | tax_rate = float("7.5") | tax_rate: 7.5 | String cast to float |
| 94 | discount_pct = float("15.0") | discount_pct: 15.0 | String cast to float |
| 100 | calculate_tax(200.0, 7.5) | Scope enters calculate_tax() | Guards pass (200.0 >= 0) |
| 18 | 200.0 * (1 + 7.5/100) | tax_multiplier: 1.075 | 200.0 * 1.075 -> 215.0 |
| 100 | price_after_tax = 215.0 | price_after_tax: 215.0 | Assigned return value |
| 106 | apply_discount(215.0, 15.0) | Scope enters apply_discount() | Guards pass (15.0 <= 100) |
| 45 | 215.0 * (1 - 15.0/100) | discount_multiplier: 0.85 | 215.0 * 0.85 -> 182.75 |
| 106 | final_price = 182.75 | final_price: 182.75 | Assigned return value |
| 112 | format_currency(182.75) | Scope enters format_currency() | f"${182.75:.2f}" -> "$182.75" |
| 112 | formatted_total = "$182.75" | formatted_total: "$182.75" | Assigned return string |
| 118 | print(...) statements | Reading scope variables | Console Output printed |

###### Final Terminal Output
```
=== PROFESSIONAL TRANSACTION PROCESSOR ===
Base Price:    $200.00
After Tax:     $215.00
Final Total:   $182.75
==========================================
```

--------------------------------------------------------------------------------

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
This section presents four diagnostic tracing challenges involving order of operations, guard short-circuiting, scope behavior, and pipeline composition.

##### Challenge A: Nested Pipeline Evaluation Order
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

###### Line-by-Line Execution Trace
1. initial_val is initialized to 4.
2. Evaluation of fn_gamma(fn_beta(fn_alpha(4))) begins from the innermost parentheses:
    *   **Step 1 (Innermost):** fn_alpha(4) executes -> 4 + 3 = 7.
    *   **Step 2 (Middle):** fn_beta(7) executes -> 7 * 2 = 14.
    *   **Step 3 (Outermost):** fn_gamma(14) executes -> 14 - 5 = 9.
3. result_a is bound to integer object 9.

###### Final Terminal Output
```
Result A: 9
```

--------------------------------------------------------------------------------

##### Challenge B: Guard Clause Short-Circuit Trapping
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

###### Line-by-Line Execution Trace
1. process_data("50"): Argument "50" is str. Guard 1 triggers (not isinstance("50", (int, float)) is True). Returns "ERROR: INVALID_TYPE" immediately. Guard 2 is skipped.
2. process_data(-10): Argument -10 is int. Guard 1 passes. Guard 2 triggers (-10 <= 0 is True). Returns "ERROR: NON_POSITIVE".
3. process_data(25): Argument 25 is int. Guard 1 passes (True). Guard 2 passes (25 <= 0 is False). Reaches Happy Path -> evaluates f"VALID: {25 * 2}" -> returns "VALID: 50".

###### Final Terminal Output
```
1: ERROR: INVALID_TYPE | 2: ERROR: NON_POSITIVE | 3: VALID: 50
```

--------------------------------------------------------------------------------

##### Challenge C: Variable Reassignment & Scope Isolation
```python
def increment_counter(count: int) -> int:
    count = count + 1
    return count


main_count: int = 10
returned_count: int = increment_counter(main_count)

print(f"main_count: {main_count} | returned_count: {returned_count}")
```

###### Line-by-Line Execution Trace
1. main_count is assigned 10 in module scope.
2. increment_counter(main_count) is called, passing reference to 10. Local parameter count inside function frame is bound to 10.
3. Inside function frame: count + 1 evaluates to 11. Local name count is rebound to new integer object 11. Module-level main_count remains untouched at 10.
4. Function returns 11, which is assigned to returned_count in module scope.
5. main_count evaluates to 10; returned_count evaluates to 11.

###### Final Terminal Output
```
main_count: 10 | returned_count: 11
```

--------------------------------------------------------------------------------

##### Challenge D: Pipeline Non-Commutative Operations
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

###### Line-by-Line Execution Trace
1. start_price initialized to 100.0.
2.  **Pipeline 1 (** `p1_result` **):**
    *   Inner call: add_flat_fee(100.0) -> 100.0 + 15.0 = 115.0.
    *   Outer call: apply_percent_discount(115.0) -> 115.0 * 0.80 = 92.0.
    *   p1_result = 92.0.
3.  **Pipeline 2 (** `p2_result` **):**
    *   Inner call: apply_percent_discount(100.0) -> 100.0 * 0.80 = 80.0.
    *   Outer call: add_flat_fee(80.0) -> 80.0 + 15.0 = 95.0.
    *   p2_result = 95.0.

###### Final Terminal Output
```
Pipeline 1: 92.00 | Pipeline 2: 95.00
```

--------------------------------------------------------------------------------

*CS101 / PY104 Week 1 Master Reference Guide. All code examples verified for syntax and runtime validity.*

---
## PART II: WEEK 2 - Dictionaries, Data Retrieval, and Loop Integration

### PY104 - Week 2 Master Reference: Dictionaries, Data Retrieval, and Loop Integration
*Welcome to the PY104 Week 2 Master Reference Document. This authoritative, publication-grade guide synthesizes all core programming concepts, mental models, memory mechanics, defensive coding strategies, and step-by-step code execution traces covered in this module. It is designed as a self-contained, technical reference for mastering Python dictionaries, key-based retrieval, state tracking, loop control, and modular function integration.*

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

--------------------------------------------------------------------------------

#### 1. Abstract Foundations & Core Theory
Data structures dictate both the algorithmic complexity and readability of software systems. This module contrasts **position-based retrieval** (inherent to sequence types like lists) with **key-based retrieval** (inherent to mapping types like dictionaries), alongside the flow-control primitives that orchestrate data processing.

##### Primary Data Types, Operations, and Keywords
*   **List (** `list` **):** A mutable, ordered sequence of elements. Elements are indexed sequentially starting at integer position 0 through N - 1. Searching a list for a value without knowing its index requires linear scanning ($O(N)$ time complexity).
*   **Dictionary (** `dict` **):** A mutable, associative mapping structure composed of unique **keys** mapped to arbitrary **values** (key: value). Lookup, insertion, and deletion operate via hashing, offering average $O(1)$ constant time complexity.
*   **Key (** `key` **):** A unique, immutable identifier within a dictionary (e.g., str, int, tuple). Serves as the direct address for value retrieval.
*   **Value (** `value` **):** The data payload associated with a key. Values can be of any Python data type, mutable or immutable, and do not need to be unique.
*   **Safe Lookup (** `.get(key, default)` **):** A dictionary method that evaluates a key and returns its associated value if present; otherwise, it returns a specified default value (or None), suppressing runtime KeyError exceptions.
*   **Dictionary Views (** `.keys()`, `.values()`, `.items()` **):** Dynamic view objects providing iterable references to the dictionary's keys, values, or key-value tuples respectively without duplicating underlying memory.
*   **Boolean Flag:** A bool state variable (initialized to True or False) used inside iterative blocks to signal whether a specific condition has been encountered across loop execution cycles.
*   **Loop Control (** `break` **):** A flow control keyword that immediately terminates the innermost enclosing loop execution, transferring program control to the statement immediately following the loop block.
*   **Helper Function:** A modular sub-routine defined using def that encapsulates a specific unit of logic, called repeatedly within a loop to delegate per-item transformations.

--------------------------------------------------------------------------------

##### Side-by-Side Comparison Matrix
| Feature / Spec | List (Position-Based Retrieval) | Parallel Lists (Index Juggling) | Dictionary (Key-Based Retrieval) |
| ------ | ------ | ------ | ------ |
| **Primary Structure** | Single ordered sequence of items | Two or more synchronized sequence lists | Unordered/insertion-ordered mapping of key-value pairs |
| **Syntax / Delimiters** | Bracket notation: [item1, item2] | Multiple lists: keys = [...], vals = [...] | Curly braces / colons: {key1: val1, key2: val2} |
| **Retrieval Mechanism** | Integer index access: lst[0] | Multi-step dance: idx = keys.index(k); val = vals[idx] | Direct key mapping: d[key] or d.get(key) |
| **Lookup Time Complexity** | $O(1)$ by index; $O(N)$ by value search | $O(N)$ linear search through key list | $O(1)$ average constant time hash-lookup |
| **Data Integrity Risk** | Minimal for single items | High: Lists easily get out of sync if modified | Zero sync risk: Keys and values are bound in one object |
| **Permitted Key Types** | Integers only (0 to len - 1) | Integers for indexing | Any hashable/immutable type (str, int, tuple) |
| **Mutability Behavior** | Mutable in-place via index assignment | Mutable in-place per list independently | Mutable in-place via key assignment d[k] = v |
| **Common Runtime Error** | IndexError: list index out of range | ValueError (missing item) or desynchronized lookup | KeyError (missing key during direct [] access) |

--------------------------------------------------------------------------------

#### 2. Real-World Mental Models & Conceptual Mapping
To build strong architectural intuition, abstract programming concepts can be mapped to physical systems and visual models.

##### Analogy 1: The Labeled Drawer Array vs. Unmarked Storage Cubbies
Imagine a physical storage unit containing 100 drawers.
*   **List (Unmarked Cubbies):** The drawers have no labels on the front—only position numbers ($0, 1, 2, \dots, 99$). To locate "Carol's document", an assistant must start at drawer $0$ and open every drawer sequentially until they stumble upon Carol's file. This represents the **manual scan requirement**.
*   **Dictionary (Labeled Drawers):** Every drawer has a clear nameplate (e.g., "Carol"). The assistant walks directly to the drawer marked "Carol", opens it once, and retrieves the payload. This is **direct key-based lookup**.

```
POSITION-BASED SCAN (List):
[0: Alice] --> [1: Bob] --> [2: Carol] --> [3: Dave]  (Linear O(N) Scan)

KEY-BASED DIRECT LOOKUP (Dictionary):
Key: "Carol"  === Hash Table Lookup ===> [ Drawer "Carol": Grade 78 ]  (Direct O(1) Access)
```

##### Analogy 2: Parallel List Index Juggling vs. Single Bound File Folders
Consider maintaining student grades.
*   **Parallel Lists:** You keep a roster list in your left hand and a grade sheet in your right hand. To find Carol's grade, you scan down the left paper to line 12, remember the number 12, and then locate line 12 on the right paper. If someone inserts a new student at line 5 on the roster but forgets the grade sheet, every subsequent lookup returns corrupt, mismatched data.
*   **Dictionary:** Each student has a single folder where their name is printed on the tab and their grade is inside. The label and value are intrinsically bound.

##### Analogy 3: The Assembly Line and the Station Specialist
Processing items in a loop with helper functions mirrors an industrial assembly line.
*   **The Loop:** A conveyor belt carrying raw items sequentially.
*   **The Helper Function:** A specialized robotic station along the belt. As each item arrives, the belt stops briefly, hands the single item to the robot, receives the transformed item back, and places it into an output crate.

```
+-------------------------------------------------------------------+
|                        LOOP CONVEYOR BELT                         |
|  Raw Item [ "Ron" ] ---> [ Helper Station: add_title(name) ]      |
|                                    |                              |
|                                    v (Executes: "Dr. " + "Ron")   |
|  Output Item [ "Dr. Ron" ] <-------+                              |
|         |                                                         |
|         v                                                         |
|  [ Append to Result List: ["Dr. Ron"] ]                           |
+-------------------------------------------------------------------+
```

--------------------------------------------------------------------------------

#### 3. Idiomatic Python Implementation & State Tracing
This section details idiomatic patterns across five core operational domains. Every snippet includes step-by-step state tracing annotations and console output previews.

##### Domain A: Dictionary Creation, Direct Access, and Safe Lookup
```python
# --- 1. Literal Creation ---
contacts = {
    "Alice": "555-0101",
    "Bob": "555-0102"
}
# State: contacts = {'Alice': '555-0101', 'Bob': '555-0102'}

# --- 2. Step-by-Step Assignment & In-Place Mutation ---
contacts["Carol"] = "555-0103"  # Add new key-value pair
# State: contacts = {'Alice': '555-0101', 'Bob': '555-0102', 'Carol': '555-0103'}

contacts["Alice"] = "555-9999"  # Update existing key
# State: contacts = {'Alice': '555-9999', 'Bob': '555-0102', 'Carol': '555-0103'}

# --- 3. Direct Lookup vs. Safe .get() Access ---
alice_phone = contacts["Alice"]  # Direct lookup (Key exists)
# Evaluation: alice_phone = "555-9999"

dave_safe = contacts.get("Dave")  # Safe lookup (Missing key, defaults to None)
# Evaluation: dave_safe = None

dave_custom = contacts.get("Dave", "Unlisted")  # Custom default fallback
# Evaluation: dave_custom = "Unlisted"

print(f"Alice: {alice_phone}")
print(f"Dave Status: {dave_custom}")
# Console Output:
# Alice: 555-9999
# Dave Status: Unlisted
```

--------------------------------------------------------------------------------

##### Domain B: Dictionary Iteration Views (.keys(), .values(), .items())
```python
inventory = {
    "Laptop": 1200.00,
    "Mouse": 25.50,
    "Keyboard": 75.00
}

# --- 1. Iterating Over Keys Only (.keys()) ---
# Use Case: Operating strictly on labels (e.g., generating product menus)
print("Product Roster:")
for product_name in inventory.keys():
    # Loop 1: product_name = "Laptop"
    # Loop 2: product_name = "Mouse"
    # Loop 3: product_name = "Keyboard"
    print(f"- {product_name}")

# --- 2. Iterating Over Values Only (.values()) ---
# Use Case: Aggregating numerical payload data without key reference
total_valuation = 0.0
for unit_price in inventory.values():
    # Loop 1: unit_price = 1200.00 -> total_valuation = 1200.00
    # Loop 2: unit_price = 25.50   -> total_valuation = 1225.50
    # Loop 3: unit_price = 75.00   -> total_valuation = 1300.50
    total_valuation += unit_price
print(f"Total Valuation: ${total_valuation:.2f}")

# --- 3. Iterating Over Key-Value Pairs (.items()) ---
# Use Case: Full record formatted output or dual-component checks
print("Price Audit:")
for item, price in inventory.items():
    # Loop 1: item = "Laptop",   price = 1200.00
    # Loop 2: item = "Mouse",    price = 25.50
    # Loop 3: item = "Keyboard", price = 75.00
    status = "Premium" if price > 100.00 else "Standard"
    print(f"{item} (${price:.2f}): {status}")

# Console Output:
# Product Roster:
# - Laptop
# - Mouse
# - Keyboard
# Total Valuation: $1300.50
# Price Audit:
# Laptop ($1200.00): Premium
# Mouse ($25.50): Standard
# Keyboard ($75.00): Standard
```

--------------------------------------------------------------------------------

##### Domain C: Advanced Dictionary Patterns (Counting, Accumulation, Grouping)
```python
# --- Pattern 1: Frequency Counting ---
# Skeleton: counts[key] = counts.get(key, 0) + 1
events = ["click", "view", "click", "purchase", "click", "view"]
event_counts = {}

for event in events:
    # Cycle 1: event = "click"    -> counts.get("click", 0) + 1 = 1 -> event_counts["click"] = 1
    # Cycle 2: event = "view"     -> counts.get("view", 0) + 1 = 1  -> event_counts["view"] = 1
    # Cycle 3: event = "click"    -> counts.get("click", 1) + 1 = 2 -> event_counts["click"] = 2
    # Cycle 4: event = "purchase" -> counts.get("purchase", 0) + 1 = 1 -> event_counts["purchase"] = 1
    # Cycle 5: event = "click"    -> counts.get("click", 2) + 1 = 3 -> event_counts["click"] = 3
    # Cycle 6: event = "view"     -> counts.get("view", 1) + 1 = 2  -> event_counts["view"] = 2
    event_counts[event] = event_counts.get(event, 0) + 1

print(f"Event Frequency: {event_counts}")


# --- Pattern 2: Numerical Accumulation ---
# Skeleton: totals[key] = totals.get(key, 0.0) + magnitude
transactions = [
    ("Alice", 50.00),
    ("Bob", 20.00),
    ("Alice", 35.50),
    ("Bob", 10.00)
]
customer_totals = {}

for customer, amount in transactions:
    # Cycle 1: customer="Alice", amount=50.00 -> totals["Alice"] = 0.0 + 50.00 = 50.00
    # Cycle 2: customer="Bob",   amount=20.00 -> totals["Bob"]   = 0.0 + 20.00 = 20.00
    # Cycle 3: customer="Alice", amount=35.50 -> totals["Alice"] = 50.00 + 35.50 = 85.50
    # Cycle 4: customer="Bob",   amount=10.00 -> totals["Bob"]   = 20.00 + 10.00 = 30.00
    customer_totals[customer] = customer_totals.get(customer, 0.0) + amount

print(f"Customer Totals: {customer_totals}")


# --- Pattern 3: Categorical Grouping ---
# Skeleton: if key not in groups: groups[key] = []; groups[key].append(payload)
students = [
    ("Math", "Alice"),
    ("Physics", "Bob"),
    ("Math", "Charlie"),
    ("Physics", "David")
]
class_roster = {}

for course, student in students:
    # Cycle 1: course="Math", student="Alice" -> "Math" not in roster -> roster["Math"] = []; append("Alice")
    # Cycle 2: course="Physics", student="Bob" -> "Physics" not in roster -> roster["Physics"] = []; append("Bob")
    # Cycle 3: course="Math", student="Charlie" -> "Math" in roster -> append("Charlie")
    # Cycle 4: course="Physics", student="David" -> "Physics" in roster -> append("David")
    if course not in class_roster:
        class_roster[course] = []
    class_roster[course].append(student)

print(f"Class Roster: {class_roster}")

# Console Output:
# Event Frequency: {'click': 3, 'view': 2, 'purchase': 1}
# Customer Totals: {'Alice': 85.5, 'Bob': 30.0}
# Class Roster: {'Math': ['Alice', 'Charlie'], 'Physics': ['Bob', 'David']}
```

--------------------------------------------------------------------------------

##### Domain D: Loop Control, State Tracking, and Short-Circuiting
```python
data_stream = [12, 45, 8, -3, 99, 104]

has_negative = False  # Boolean Flag State Tracker
running_sum = 0       # Accumulator

for entry in data_stream:
    # Cycle 1: entry = 12 -> entry < 0 False -> running_sum = 12
    # Cycle 2: entry = 45 -> entry < 0 False -> running_sum = 57
    # Cycle 3: entry = 8  -> entry < 0 False -> running_sum = 65
    # Cycle 4: entry = -3 -> entry < 0 TRUE  -> has_negative = True -> BREAK TRIGGERED
    if entry < 0:
        has_negative = True
        break
    running_sum += entry

# Unprocessed elements (99, 104) are skipped due to immediate loop termination.
print(f"Processed Sum: {running_sum}")
print(f"Anomaly Detected: {has_negative}")

# Console Output:
# Processed Sum: 65
# Anomaly Detected: True
```

--------------------------------------------------------------------------------

##### Domain E: Modular Loop Processing via Helper Functions
```python
# Helper Function: Isolated single-item transformer
def format_user_title(name: str, degree: str) -> str:
    # Transforms a single name and degree into a standardized title.
    return f"Dr. {name}, {degree}"

raw_candidates = [
    ("Smith", "Ph.D."),
    ("Patel", "MD"),
    ("Jones", "Sc.D.")
]

processed_directory = []  # Collector list

for name, degree in raw_candidates:
    # Cycle 1: name="Smith", degree="Ph.D." -> format_user_title("Smith", "Ph.D.") -> returns "Dr. Smith, Ph.D."
    # Cycle 2: name="Patel", degree="MD"     -> format_user_title("Patel", "MD")     -> returns "Dr. Patel, MD"
    # Cycle 3: name="Jones", degree="Sc.D."  -> format_user_title("Jones", "Sc.D.")  -> returns "Dr. Jones, Sc.D."
    formatted_title = format_user_title(name, degree)
    processed_directory.append(formatted_title)

print(f"Directory: {processed_directory}")

# Console Output:
# Directory: ['Dr. Smith, Ph.D.', 'Dr. Patel, MD', 'Dr. Jones, Sc.D.']
```

--------------------------------------------------------------------------------

#### 4. Defensive Programming & Common Traps
When transitioning from sequential lists to mapping types and loop modularity, software engineers encounter predictable runtime errors.

##### Trap 1: Missing Key Direct Access (KeyError)
Direct bracket access on a non-existent key raises an unhandled KeyError exception, abruptly halting execution.
```python
contacts = {"Alice": "555-0101"}

# INCORRECT: Direct bracket lookup on missing key
# number = contacts["Bob"]  # Raises KeyError: 'Bob'

# CORRECT: Option A - Defensive membership check
if "Bob" in contacts:
    number = contacts["Bob"]
else:
    number = "Not Found"

# CORRECT: Option B - Idiomatic safe lookup using .get()
number = contacts.get("Bob", "Not Found")
```

--------------------------------------------------------------------------------

##### Trap 2: Attempting Value Assignment to Method Call
A common syntax error arises from confusing the **read-only retrieval method** .get() with bracket assignment syntax [].
```python
contacts = {"Alice": "555-0101"}

# INCORRECT: Attempting to assign a value to a function return value
# contacts.get("Alice") = "555-9999"
# SyntaxError: cannot assign to function call here / cannot assign to expression

# CORRECT: Use bracket indexing for mutation and assignment
contacts["Alice"] = "555-9999"  # Updates existing key
contacts["Bob"] = "555-0102"    # Inserts new key
```

--------------------------------------------------------------------------------

##### Trap 3: Tuple Iteration Bug vs. Full Index Range Scanning
When scanning lists by index, iterating over a fixed tuple (0, len(lst)-1) checks only the boundary indices (first and last elements), silently skipping all internal elements.
```python
products = ["apple", "banana", "orange", "grape"]
prices = [0.99, 0.59, 0.79, 2.49]
target = "orange"

# INCORRECT: Tuple literal checks ONLY index 0 ("apple") and index 3 ("grape")
# for i in (0, len(products) - 1):
#     if products[i] == target:
#         print(prices[i])  # Fails to find "orange" at index 2!

# CORRECT: Use range(len(...)) to scan every integer index sequentially
for i in range(len(products)):
    if products[i] == target:
        print(f"Price: {prices[i]}")  # Correctly identifies index 2 (0.79)
```

--------------------------------------------------------------------------------

##### Trap 4: Set Literal Instantiation Mismatch in Data Structures
Defining collection literals with curly braces {} without key-value colons creates an unordered set, which strips duplicate entries and lacks list ordering/indexing.
```python
# INCORRECT: Using curly braces creates a set of tuples, dropping duplicates and losing order
raw_sales = {
    ("Alice", 10.0),
    ("Bob", 5.0),
    ("Alice", 10.0)  # SILENTLY DROPPED as a duplicate set element!
}

# CORRECT: Use square brackets to define a sequence list of tuples
raw_sales = [
    ("Alice", 10.0),
    ("Bob", 5.0),
    ("Alice", 10.0)  # Retained accurately in sequence
]
```

--------------------------------------------------------------------------------

##### Trap 5: Omitting Return Statements in Modular Helper Functions
Failing to include an explicit return statement in a helper function causes Python to implicitly return None, corrupting downstream collection building.
```python
# INCORRECT: Missing return statement
def boost_score_broken(score):
    result = score + 5
    # Forgot return! Returns None implicitly.

scores = [80, 90]
boosted = []
for s in scores:
    boosted.append(boost_score_broken(s))
# Result: boosted = [None, None]  <-- Silent Logic Bug!

# CORRECT: Explicit return of transformed payload
def boost_score_correct(score):
    return score + 5

boosted = []
for s in scores:
    boosted.append(boost_score_correct(s))
# Result: boosted = [85, 95]
```

--------------------------------------------------------------------------------

#### 5. Python Memory Mechanics, References & Scope
Understanding how Python manages object references in memory is critical for predicting variable bindings, mutability behavior, and function execution frames.

##### Variable Bindings and the Object Heap
In Python:
1.  **Namespaces:** Names (variables) are symbolic labels stored inside a namespace dictionary mapping variable names to memory addresses.
2.  **Heap Memory:** All actual objects (integers, strings, lists, dictionaries) reside on the memory heap.
3.  **Binding vs. Assignment:** Assigning a variable (x = ...) binds the symbol x to an object's memory address in the current frame. Assigning to a dictionary key (d[k] = v) alters the internal pointer table of the existing dictionary object on the heap without changing the memory address of d itself.

##### Dictionary Hash Tables & Mutability Invariants
*   **Dictionaries are Mutable Heap Objects:** Modifying a dictionary (e.g., adding a key) alters its memory contents in-place. All variables referencing that same memory address reflect the modification.
*   **Keys Must Be Hashable (Immutable):** A dictionary key must have a hash value that remains fixed during its lifetime. Immutables (str, int, float, tuple) are hashable. Mutables (list, dict, set) are unhashable and cause a TypeError if used as keys.

```
GLOBAL NAMESPACE FRAME                      HEAP MEMORY OBJECTS
+-------------------+                       +---------------------------------------+
|  contacts --------+---------------------> | Dict Object (id: 0x7f8a)              |
+-------------------+                       | {                                     |
|  scores ----------+-----------+           |   "Alice": Pointer to "555-9999" (0x101) |
+-------------------+           |           |   "Bob":   Pointer to "555-0102" (0x102) |
                                |           | }                                     |
                                |           +---------------------------------------+
                                |
                                |           +---------------------------------------+
                                +---------> | List Object (id: 0x9b2c)              |
                                            | [ 85 (0x301), 92 (0x302), 78 (0x303) ]|
                                            +---------------------------------------+
```

--------------------------------------------------------------------------------

#### 6. Practical Integration / Mini Case Study
This case study integrates all core module concepts—dictionary creation, safe .get() access, frequency counting, numerical accumulation, categorical grouping, loop state flags with short-circuiting, and helper function delegation—into a single production-ready telemetry parser script.

##### Case Study: E-Commerce Audit & Telemetry Processor
```python
# --- STEP 1: Modular Helper Functions ---
def sanitize_transaction(raw_user: str, raw_amount: float) -> tuple:
    # Helper function: Normalizes username casing and enforces float precision.
    clean_user = raw_user.strip().capitalize()
    clean_amount = round(float(raw_amount), 2)
    return clean_user, clean_amount

def calculate_tax(amount: float, rate: float = 0.08) -> float:
    # Helper function: Computes regional tax contribution.
    return round(amount * rate, 2)


# --- STEP 2: Raw Telemetry Stream Input ---
raw_logs = [
    ("  alice ", 120.50, "US"),
    ("bob", 45.00, "CA"),
    ("ALICE ", 35.25, "US"),
    (" charlie", -10.00, "US"),  # INVALID TRANSACTION (Negative Amount)
    ("BOB", 150.00, "CA"),
    ("alice", 89.99, "US")
]


# --- STEP 3: State Initialization ---
user_totals = {}       # Accumulation Pattern
user_activity = {}     # Frequency Counting Pattern
regional_groups = {}   # Grouping Pattern

fraud_flag = False     # Boolean Flag
processed_count = 0    # Loop State Accumulator


# --- STEP 4: Processing Loop Execution ---
print("--- STARTING TELEMETRY PROCESSING ---")

for user_raw, amount_raw, region in raw_logs:
    # 1. Defensive Validation & Loop Short-Circuiting
    if amount_raw < 0:
        fraud_flag = True
        print(f"CRITICAL ANOMALY: Negative transaction detected for '{user_raw.strip()}'. Halting processing.")
        break  # Terminate loop immediately
    
    # 2. Delegate Per-Item Transformations to Helper Functions
    user, amount = sanitize_transaction(user_raw, amount_raw)
    tax_contribution = calculate_tax(amount)
    total_with_tax = amount + tax_contribution
    
    # 3. Apply Accumulation Pattern
    user_totals[user] = user_totals.get(user, 0.0) + total_with_tax
    
    # 4. Apply Frequency Counting Pattern
    user_activity[user] = user_activity.get(user, 0) + 1
    
    # 5. Apply Categorical Grouping Pattern
    if region not in regional_groups:
        regional_groups[region] = []
    regional_groups[region].append(user)
    
    processed_count += 1


# --- STEP 5: Final Analytics Reporting ---
print("
--- EXECUTIVE ANALYTICS REPORT ---")
print(f"Records Processed: {processed_count}")
print(f"Fraud Flag Triggered: {fraud_flag}")

print("
1. Customer Revenue Totals (With Tax):")
for customer, gross_spend in user_totals.items():
    print(f"   - {customer}: ${gross_spend:.2f}")

print("
2. Customer Order Activity Frequency:")
for customer, count in user_activity.items():
    print(f"   - {customer}: {count} order(s)")

print("
3. Regional Customer Distribution:")
for reg, customer_list in regional_groups.items():
    print(f"   - Region [{reg}]: {customer_list}")

# Console Output:
# --- STARTING TELEMETRY PROCESSING ---
# CRITICAL ANOMALY: Negative transaction detected for 'charlie'. Halting processing.
# 
# --- EXECUTIVE ANALYTICS REPORT ---
# Records Processed: 3
# Fraud Flag Triggered: True
# 
# 1. Customer Revenue Totals (With Tax):
#    - Alice: $168.21
#    - Bob: $48.60
# 
# 2. Customer Order Activity Frequency:
#    - Alice: 2 order(s)
#    - Bob: 1 order(s)
# 
# 3. Regional Customer Distribution:
#    - Region [US]: ['Alice', 'Alice']
#    - Region [CA]: ['Bob']
```

--------------------------------------------------------------------------------

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
Test your understanding of execution mechanics, state tracking, and dictionary patterns with these four diagnostic tracing challenges.

##### Challenge A: Safe Lookup & State Mutation Order
```python
profile = {"name": "Ron", "age": 59}

# Line 1: In-place bracket assignment
profile["city"] = "Seattle"

# Line 2: Safe lookup on missing key with custom default fallback
nickname = profile.get("nickname", "No Nickname Set")

# Line 3: In-place update of existing key
profile["age"] = 60

# Line 4: Safe lookup on recently updated existing key
current_age = profile.get("age", 0)

print(f"Nickname: {nickname}")
print(f"Age: {current_age}")
print(f"Keys Count: {len(profile.keys())}")
```

###### Line-by-Line Execution Trace:
1.  **Line 1:** Key "city" does not exist in profile. Inserts "city": "Seattle". State: profile = {'name': 'Ron', 'age': 59, 'city': 'Seattle'}.
2.  **Line 2:** Key "nickname" is evaluated in profile. Not found. Default fallback "No Nickname Set" is evaluated and assigned to nickname. Dictionary remains unchanged.
3.  **Line 3:** Key "age" exists in profile. Value 59 is overwritten with 60. State: profile = {'name': 'Ron', 'age': 60, 'city': 'Seattle'}.
4.  **Line 4:** Key "age" is evaluated in profile. Found. Returns value 60. current_age is assigned 60.
5.  **Line 5-7:** Terminal formatting output. len(profile.keys()) evaluates to 3.

```
TERMINAL OUTPUT:
Nickname: No Nickname Set
Age: 60
Keys Count: 3
```

--------------------------------------------------------------------------------

##### Challenge B: Short-Circuit Loop with Accumulator & Flag State
```python
numbers = [10, 20, -5, 40]
flag = False
accumulator = 0

for n in numbers:
    if n < 0:
        flag = True
        break
    accumulator += n

print(f"Final Accumulator: {accumulator}")
print(f"Flag State: {flag}")
```

###### Step-by-Step Execution Trace Table:
| Iteration | Current n | Condition (n < 0) | flag State | accumulator State | Loop Action |
| ------ | ------ | ------ | ------ | ------ | ------ |
| **Start** | N/A | N/A | False | 0 | Initialize |
| **Cycle 1** | 10 | 10 < 0 (False) | False | 0 + 10 = 10 | Continue |
| **Cycle 2** | 20 | 20 < 0 (False) | False | 10 + 20 = 30 | Continue |
| **Cycle 3** | -5 | -5 < 0 ( **TRUE** ) | True | 30 (Unchanged) | **BREAK EXECUTED** |
| **Cycle 4** | 40 | *Unreached* | True | 30 | *Skipped* |

```
TERMINAL OUTPUT:
Final Accumulator: 30
Flag State: True
```

--------------------------------------------------------------------------------

##### Challenge C: Multi-Pattern Counting & Grouping Diagnostic
```python
raw_items = ["apple", "banana", "apple", "cherry"]
inventory_groups = {}

for item in raw_items:
    first_char = item[0].upper()
    inventory_groups[first_char] = inventory_groups.get(first_char, [])
    inventory_groups[first_char].append(item)

print(f"Group Keys: {list(inventory_groups.keys())}")
print(f"Group 'A': {inventory_groups['A']}")
```

###### Line-by-Line Execution Trace:
1.  **Cycle 1 (** `item = "apple"` **):** first_char = 'A'. inventory_groups.get('A', []) returns []. inventory_groups['A'] assigned []. Appends "apple". State: {'A': ['apple']}.
2.  **Cycle 2 (** `item = "banana"` **):** first_char = 'B'. inventory_groups.get('B', []) returns []. inventory_groups['B'] assigned []. Appends "banana". State: {'A': ['apple'], 'B': ['banana']}.
3.  **Cycle 3 (** `item = "apple"` **):** first_char = 'A'. inventory_groups.get('A', ['apple']) returns existing list ['apple']. Appends "apple". State: {'A': ['apple', 'apple'], 'B': ['banana']}.
4.  **Cycle 4 (** `item = "cherry"` **):** first_char = 'C'. inventory_groups.get('C', []) returns []. inventory_groups['C'] assigned []. Appends "cherry". State: {'A': ['apple', 'apple'], 'B': ['banana'], 'C': ['cherry']}.

```
TERMINAL OUTPUT:
Group Keys: ['A', 'B', 'C']
Group 'A': ['apple', 'apple']
```

--------------------------------------------------------------------------------

##### Challenge D: Helper Function Delegation & List Transformation
```python
def transform_score(score: int) -> int:
    if score >= 90:
        return score + 10
    elif score >= 70:
        return score + 5
    return score

scores = [65, 75, 95]
adjusted_scores = []

for s in scores:
    adjusted_scores.append(transform_score(s))

print(f"Original: {scores}")
print(f"Adjusted: {adjusted_scores}")
```

###### Step-by-Step Execution Trace:
1.  **Cycle 1 (** `s = 65` **):** transform_score(65) evaluated. 65 >= 90 (False) -> 65 >= 70 (False) -> returns 65. adjusted_scores.append(65).
2.  **Cycle 2 (** `s = 75` **):** transform_score(75) evaluated. 75 >= 90 (False) -> 75 >= 70 ( **True** ) -> returns 75 + 5 = 80. adjusted_scores.append(80).
3.  **Cycle 3 (** `s = 95` **):** transform_score(95) evaluated. 95 >= 90 ( **True** ) -> returns 95 + 10 = 105. adjusted_scores.append(105).

```
TERMINAL OUTPUT:
Original: [65, 75, 95]
Adjusted: [65, 80, 105]
```

--------------------------------------------------------------------------------

*End of PY104 Master Reference Document.*

---
## PART III: WEEK 3 - Advanced Data Structures, Filtering, Grouping & Functional Pipelines

### CS101 - Week 3 Master Reference: Advanced Data Structures, Filtering, Grouping & Functional Pipelines
*Welcome to the CS101 Week 3 Master Reference Guide. This publication-grade reference document synthesizes all core concepts, mental models, memory mechanics, data structure designs, and step-by-step code execution traces from this module into an authoritative, self-contained textbook reference.*

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

--------------------------------------------------------------------------------

#### 1. Abstract Foundations & Core Theory
##### Primary Data Structures and Operations
Python provides flexible composite data types that allow developers to model complex real-world systems. Managing collections of structured records relies on combining primitive types into nested data architectures.
*   **List of Dictionaries (** `List[Dict[str, Any]]` **):** An ordered, mutable sequence of dictionary objects where each dictionary represents a discrete record ("row") and dictionary keys represent consistent attributes ("columns").
*   **Dictionary of Lists (** `Dict[str, List[Any]]` **):** A mutable mapping where each key represents a category or grouping ("bucket") and each value is an ordered list containing elements belonging to that category.
*   **Dictionary Index (** `Dict[Key, Dict[str, Any]]` **):** A hash map keyed by a unique primary key (e.g., id, sku, student_id) pointing directly to a complete record dictionary, enabling $O(1)$ constant-time lookups.
*   **Filter Pattern (Scan-Test-Store):** An algorithmic pattern that iterates over a dataset, evaluates a boolean conditional rule for each item, and collects matching records into a new result collection.
*   **Grouping Pattern:** An incremental categorization algorithm that iterates over records, checks for category key existence in a destination dictionary, initializes empty list buckets when necessary, and appends records to their respective buckets.
*   **Functional Pipeline (Chaining):** A modular software architecture where small, single-responsibility functions are linked sequentially such that the return value of one function becomes the direct input parameter of the next.
*   **Loop Skeleton vs. Per-Item Helper:** An architectural design principle separating iteration control (for loop over a collection) from single-item transformation logic (a helper function operating on a single record).
*   **Dictionary Views (** `.keys()`, `.values()`, `.items()` **):** Dynamic view objects reflecting the keys, values, or key-value tuples of a dictionary without making memory-intensive copies.

--------------------------------------------------------------------------------

##### Side-by-Side Comparison Matrix
| Feature / Spec | List of Dictionaries (Table Model) | Dictionary of Lists (Bucket Model) | Dictionary Index (Lookup Model) |
| ------ | ------ | ------ | ------ |
| **Primary Definition** | Ordered collection of record dictionaries representing table rows | Hash map mapping category labels to lists of grouped values | Hash map mapping unique keys directly to complete record objects |
| **Literal Syntax / Delimiters** | [ {"key": val}, {"key": val} ] | { "category": [val1, val2] } | { id_key: {"id": id_key, ...} } |
| **Permitted Operations** | for row in list:, list.append(dict), row["field"] | dict[key].append(val), for k, v in dict.items() | dict[id_key], if id in dict:, dict.get(id) |
| **Type Invariant / Mutability** | Outer list mutable; inner dictionaries mutable | Outer dictionary mutable; inner lists mutable | Outer dictionary mutable; inner record dictionaries mutable |
| **Primary Access Pattern** | Sequential scan ($O(N)$ linear search across all rows) | Category jump ($O(1)$ key access) followed by list access | Instant retrieval ($O(1)$ hash lookup by primary key) |
| **Best Architectural Fit** | Searching across all records by arbitrary fields | Displaying grouped categories or dropdown options | High-frequency single-record lookups by primary ID |
| **Common Runtime Exception** | KeyError (missing field), IndexError (bad index) | KeyError (uninitialized category key) | KeyError (missing ID without in guard check) |

--------------------------------------------------------------------------------

#### 2. Real-World Mental Models & Conceptual Mapping
To select the correct data architecture and logic flow, developers rely on visual and physical mental models.

##### 1. The Spreadsheet Table vs. The Labeled Storage Bins
*   **List of Dictionaries (The Spreadsheet Table):** Imagine a paper binder where each page is a table. Each line on the page is a single row (one dictionary) representing a specific entity (e.g., a pet or game character). The column headers (e.g., "name", "species", "age") are identical keys across every row. To find all dragons, you must start at the top line and read down the page line by line.
*   **Dictionary of Lists (The Labeled Bins):** Imagine a physical wall of storage bins. Each bin has a label on the front (e.g., "dragon", "unicorn", "griffin"). Inside the "dragon" bin is a folder containing a list of names (["Flamey", "Storm"]). If you need all dragons, you do not scan the room; you walk directly to the bin labeled "dragon" and lift out the list.

##### 2. The Linear Grid Search vs. The Phonebook Index
*   **Nested Loop Search ($O(N \times M)$ Grid):** Imagine a stack of 100 customer order sheets and a separate ledger of 100 customer profiles. To match each order to a customer, you take Order 1 and read through the customer ledger line by line until you find match #101. Then you take Order 2 and read through the entire customer ledger again from top to bottom. For $N$ orders and $M$ customers, you perform $N \times M$ manual line comparisons.
*   **Dictionary Index ($O(1)$ Direct Jump):** Before processing orders, you rearrange the customer ledger into an alphabetical Rolodex indexed by Customer ID. Now, when you pick up Order 1 (Customer #101), you flip directly to tab #101 in one motion. Total comparisons drop from $N \times M$ down to $N$.

##### 3. The Conveyor Belt Assembly Line (Functional Pipelines & Helpers)
*   **Loop Skeleton (The Conveyor Motor):** The for loop acts as a factory conveyor belt. Its sole job is advancing the next raw component to the workstation. It handles bookkeeping, iteration count, and transport.
*   **Per-Item Helper (The Robotic Workstation):** A dedicated station positioned along the belt. It accepts a single raw item, performs precise mathematical or structural transformations (e.g., adding 8% tax and 5% discount), and returns the finished item back to the belt.
*   **Pipeline Chaining:** Station 1 (add_tax) processes the raw item and hands the result directly to Station 2 (add_shipping), which hands its result directly to Station 3 (apply_discount).

```
========================================================================================
                                CONCEPT VISUALIZATIONS
========================================================================================

1. LIST OF DICTIONARIES (Spreadsheet Rows):
+--------------------------------------------------------------------------------------+
| Outer List [                                                                         |
|   Row 1: { "name": "Flamey",  "species": "dragon",  "age": 120 },                      |
|   Row 2: { "name": "Nibbles", "species": "hamster", "age": 2   },                      |
|   Row 3: { "name": "Storm",   "species": "dragon",  "age": 300 }                       |
| ]                                                                                    |
+--------------------------------------------------------------------------------------+

2. DICTIONARY OF LISTS (Category Buckets):
+--------------------------------------------------------------------------------------+
| Outer Dictionary {                                                                   |
|   "dragon"  : [ "Flamey", "Storm" ],  <-- Key "dragon" maps to List of Names         |
|   "hamster" : [ "Nibbles" ]           <-- Key "hamster" maps to List of Names        |
| }                                                                                    |
+--------------------------------------------------------------------------------------+

3. DICTIONARY INDEX (O(1) Hash Map Lookup):
+--------------------------------------------------------------------------------------+
| customer_by_id = {                                                                   |
|   101 : { "id": 101, "name": "Alice", "role": "Admin" },                             |
|   102 : { "id": 102, "name": "Bob",   "role": "User"  }                              |
| }                                                                                    |
| Lookup: customer_by_id[101] ----> Jumps directly to Alice's dictionary in O(1) time  |
+--------------------------------------------------------------------------------------+

4. FUNCTIONAL PIPELINE CHAINING:
   base_price (100)
         |
         v
   +-----------+
   | add_tax() |  ---> returns 108.0
   +-----------+
         |
         v
   +----------------+
   | add_shipping() | ---> returns 113.0
   +----------------+
         |
         v
   +------------------+
   | apply_discount() | ---> returns 101.7
   +------------------+
         |
         v
    final_total (101.7)
========================================================================================
```

--------------------------------------------------------------------------------

#### 3. Idiomatic Python Implementation & State Tracing

##### Topic 1: The Scan-Test-Store Filter Pattern
Extracting records based on evaluation rules requires initializing a result list, scanning with a for loop, testing with boolean expressions, and storing matches with `.append()`.

```python
# Raw dataset: List of Dictionaries representing pet records
pets = [
    {"name": "Flamey", "species": "dragon", "age": 120},
    {"name": "Nibbles", "species": "hamster", "age": 2},
    {"name": "Storm", "species": "dragon", "age": 300}
]

# Helper Function: Encapsulates single-record matching rule
def is_elder_dragon(pet):
    # Evaluates boolean expression: species must be 'dragon' AND age >= 200
    # Iteration 1 (Flamey): 'dragon' == 'dragon' (True) and 120 >= 200 (False) -> Returns False
    # Iteration 2 (Nibbles): 'hamster' == 'dragon' (False) -> Short-circuits -> Returns False
    # Iteration 3 (Storm): 'dragon' == 'dragon' (True) and 300 >= 200 (True) -> Returns True
    return pet["species"] == "dragon" and pet["age"] >= 200

# Filter Pattern Execution
elder_dragons = []  # Step 1: Initialize empty accumulator list

for pet in pets:  # Step 2: Scan each dictionary record in list
    if is_elder_dragon(pet):  # Step 3: Test condition via helper call
        elder_dragons.append(pet)  # Step 4: Store matching record dictionary

# Final State Inspection
print(elder_dragons)
# Terminal Output:
# [{'name': 'Storm', 'species': 'dragon', 'age': 300}]
```

--------------------------------------------------------------------------------

##### Topic 2: Incremental Grouping (Building a Dictionary of Lists)
Converting flat records into category buckets requires checking key presence with `if key not in dict:`, instantiating an empty list `[]` on first encounter, and appending items.

```python
# Raw dataset: List of student records
students = [
    {"name": "Alice", "grade": "A"},
    {"name": "Bob", "grade": "B"},
    {"name": "Charlie", "grade": "A"},
    {"name": "Diana", "grade": "C"}
]

by_grade = {}  # Initialize empty dictionary for bucket storage

for student in students:
    grade = student["grade"]  # Extract category key
    name = student["name"]    # Extract target value

    # Guard Condition: Initialize bucket list if key does not yet exist
    if grade not in by_grade:
        by_grade[grade] = []  # State: Creates new empty list for unseen grade

    # Append value to appropriate category list
    by_grade[grade].append(name)

    # State Trace per iteration:
    # Iteration 1 (Alice): grade="A" not in by_grade -> by_grade["A"] = [] -> by_grade["A"].append("Alice")
    # Iteration 2 (Bob):   grade="B" not in by_grade -> by_grade["B"] = [] -> by_grade["B"].append("Bob")
    # Iteration 3 (Charlie): grade="A" IS in by_grade -> skips init -> by_grade["A"].append("Charlie")
    # Iteration 4 (Diana): grade="C" not in by_grade -> by_grade["C"] = [] -> by_grade["C"].append("Diana")

print(by_grade)
# Terminal Output:
# {'A': ['Alice', 'Charlie'], 'B': ['Bob'], 'C': ['Diana']}
```

--------------------------------------------------------------------------------

##### Topic 3: Building a Dictionary Index to Replace Nested Loops
Replacing $O(N \times M)$ nested loop scans with an $O(1)$ dictionary hash lookup dramatically reduces total comparison operations.

```python
orders = [
    {"id": 1, "customer_id": 101},
    {"id": 2, "customer_id": 102}
]

customers = [
    {"id": 101, "name": "Alice"},
    {"id": 102, "name": "Bob"}
]

# STEP 1: Build a Dictionary Index keyed by Customer ID
customer_by_id = {}
for customer in customers:
    cust_id = customer["id"]              # Extract unique primary key
    customer_by_id[cust_id] = customer    # Map key 101 -> whole customer dict

# State of customer_by_id index:
# { 101: {"id": 101, "name": "Alice"}, 102: {"id": 102, "name": "Bob"} }

# STEP 2: Perform Single-Loop Matching via Direct Hash Lookups
comparisons = 0

for order in orders:
    cid = order["customer_id"]          # Extract foreign key (e.g., 101)
    matched_customer = customer_by_id[cid]  # O(1) Direct Jump to customer dictionary
    comparisons += 1                    # Increment operation counter
    
    # State Trace:
    # Order 1: cid=101 -> matched_customer={"id": 101, "name": "Alice"} -> Output: 1 Alice
    # Order 2: cid=102 -> matched_customer={"id": 102, "name": "Bob"}   -> Output: 2 Bob
    print(f"Order ID: {order['id']}, Customer: {matched_customer['name']}")

print("Total comparisons:", comparisons)
# Terminal Output:
# Order ID: 1, Customer: Alice
# Order ID: 2, Customer: Bob
# Total comparisons: 2
```

--------------------------------------------------------------------------------

##### Topic 4: Functional Pipelines & Call Chaining
Single-purpose helpers can be composed in a nested functional pipeline where inner return values serve directly as outer parameters.

```python
def add_tax(price):
    # Takes price, multiplies by 1.08 (8% tax addition)
    return price * 1.08

def add_shipping(price):
    # Takes price, adds flat $5 shipping fee
    return price + 5.00

def apply_discount(price):
    # Takes price, multiplies by 0.90 (10% discount -> keeps 90%)
    return price * 0.90

# Execution Pipeline
base_price = 100.00

# Nested Call Evaluation Order (Inside-Out):
# Step 1: add_tax(100.00)                        -> Evaluates to 108.00
# Step 2: add_shipping(108.00)                    -> Evaluates to 113.00
# Step 3: apply_discount(113.00)                  -> Evaluates to 101.70
final_total = apply_discount(add_shipping(add_tax(base_price)))

print(f"Final Total: ${final_total:.2f}")
# Terminal Output:
# Final Total: $101.70
```

--------------------------------------------------------------------------------

##### Topic 5: Loop Skeleton vs. Per-Item Helper Interaction
Demonstrating clean separation between iteration bookkeeping (main loop) and per-item transformation logic (helper).

```python
# Per-Item Helper: Handles transformation logic for exactly ONE item
def process_price(price):
    price_with_tax = price * 1.10      # Step 1: Add 10% tax
    discounted_price = price_with_tax * 0.95  # Step 2: Apply 5% discount
    return discounted_price            # Returns transformed float for single item

# Main Execution Context (Loop Skeleton & Accumulators)
prices = [10.00, 20.00, 30.00]
total_revenue = 0.00
item_count = 0

for price in prices:  # Loop Skeleton: Controls iteration over collection
    processed = process_price(price)  # Delegates per-item math to helper
    total_revenue += processed        # Main loop manages running total accumulator
    item_count += 1                   # Main loop manages item count accumulator

# State Trace:
# Iteration 1: price=10.00 -> process_price(10.00)=10.45 -> total_revenue=10.45, item_count=1
# Iteration 2: price=20.00 -> process_price(20.00)=20.90 -> total_revenue=31.35, item_count=2
# Iteration 3: price=30.00 -> process_price(30.00)=31.35 -> total_revenue=62.70, item_count=3

print(f"Processed {item_count} items. Total Revenue: ${total_revenue:.2f}")
# Terminal Output:
# Processed 3 items. Total Revenue: $62.70
```

--------------------------------------------------------------------------------

#### 4. Defensive Programming & Common Traps
When working with composite structures, nested loops, and functional pipelines, developers encounter specific runtime exceptions and logic errors.

##### Trap 1: KeyError from Accessing Uninitialized Dictionary Buckets
*   **Bug Description:** Attempting to invoke `.append()` on a dictionary key that has not yet been assigned a list object. Python raises a KeyError because the key does not exist.

```python
# INCORRECT: Assumes category key already exists in dictionary
by_species = {}
pets = [{"name": "Flame", "species": "dragon"}]

for pet in pets:
    # Raises KeyError: 'dragon' because by_species['dragon'] is undefined!
    by_species[pet["species"]].append(pet["name"])
```

```python
# CORRECT: Uses guard check to initialize empty list before appending
by_species = {}
pets = [{"name": "Flame", "species": "dragon"}]

for pet in pets:
    species = pet["species"]
    if species not in by_species:  # Guard check
        by_species[species] = []   # Initialize bucket
    by_species[species].append(pet["name"])  # Safe append
```

--------------------------------------------------------------------------------

##### Trap 2: KeyError and Shape Mismatch in Dictionary Lookups
*   **Bug Description:** Mismatching key data types (e.g., comparing string "101" to integer 101) or building a dictionary with an improper structural shape (e.g., storing a list under key "id" rather than indexing records by ID).

```python
# INCORRECT: Converts integer ID to string, causing lookup failure against integer keys
customer_by_id = {101: {"name": "Alice"}}
order = {"customer_id": 101}

cid = str(order["customer_id"])  # String "101"
# Raises KeyError: '101' because dictionary contains integer key 101, not string "101"
customer = customer_by_id[cid]
```

```python
# CORRECT: Preserves original key data type for exact hash lookup
customer_by_id = {101: {"name": "Alice"}}
order = {"customer_id": 101}

cid = order["customer_id"]  # Integer 101 maintained
customer = customer_by_id[cid]  # Successfully retrieves {"name": "Alice"}
```

--------------------------------------------------------------------------------

##### Trap 3: Mathematical Multiplier Errors (Percentage vs. Decimal)
*   **Bug Description:** Using whole integer percentages directly in multiplication (e.g., multiplying by 8 for an 8% tax or 10 for a 10% discount) rather than proper decimal multipliers.

```python
# INCORRECT: Multiplies price by whole integer percent
def add_tax(price):
    return price * 8  # Converts $100 price to $800! Huge logic error.

def apply_discount(price):
    return price * 10  # Converts $100 price to $1000!
```

```python
# CORRECT: Converts percentages to decimal ratios
def add_tax(price):
    return price * 1.08  # 8% tax addition -> 1 + 0.08 = 1.08

def apply_discount(price):
    return price * 0.90  # 10% discount -> keeps 90% (1 - 0.10 = 0.90)
```

--------------------------------------------------------------------------------

##### Trap 4: Variable Shadowing Built-in Functions
*   **Bug Description:** Naming loop variables or dictionary fields after Python built-in functions (e.g., type, list, dict), which overrides the built-in function in the local namespace.

```python
# INCORRECT: Loop variable shadows built-in function type()
pets = [{"name": "Flame", "species": "dragon"}]

for type in pets:  # Overwrites global built-in function 'type'
    if type["species"] == "dragon":
        print(type["name"])
```

```python
# CORRECT: Uses descriptive, non-reserved identifier names
pets = [{"name": "Flame", "species": "dragon"}]

for pet in pets:  # Clear variable name representing one record
    if pet["species"] == "dragon":
        print(pet["name"])
```

--------------------------------------------------------------------------------

##### Trap 5: Moving Iteration Control into a Per-Item Helper
*   **Bug Description:** Placing a for loop inside a helper function that is supposed to process only a single record. This creates confusion over loop ownership and causes redundant iterations.

```python
# INCORRECT: Helper contains an internal loop but caller also loops over items
def process_single_item(items):
    for item in items:  # Internal loop violates single-item responsibility!
        return item * 2

numbers = [1, 2, 3]
for n in numbers:
    result = process_single_item(numbers)  # Repeatedly processes list, returning 2 each time!
```

```python
# CORRECT: Helper handles one item; main loop controls iteration over collection
def double_item(item):
    return item * 2  # Processes exactly one item

numbers = [1, 2, 3]
for n in numbers:
    result = double_item(n)  # Main loop passes one item per iteration
```

--------------------------------------------------------------------------------

#### 5. Python Memory Mechanics, References & Scope
Understanding how Python handles object references, heap memory, and namespaces is essential when working with nested data structures.

##### Dynamic Typing and Variable Binding
In Python, variables are not typed memory storage boxes. Instead, **variables are names (pointers) bound to objects residing in heap memory**.
*   Assignment (`x = {"name": "Aria"}`) creates a dictionary object in heap memory and binds the name x in the namespace to that object's memory address.
*   Reassignment (`x = [1, 2, 3]`) binds x to a new object; it does not overwrite the old dictionary object if other references point to it.

##### Composite Structures as Reference Containers
Lists and dictionaries do not contain physical data values directly; they store **memory addresses (references)** pointing to heap objects.
*   In `characters = [{"name": "Aria"}, {"name": "Bron"}]`, the list object stores references to two distinct dictionary objects in heap memory.
*   Each dictionary object stores key strings that map to references pointing to string or integer objects (e.g., "Aria", 5).

##### Function Scope and Object Mutability
*   When a mutable object (like a list or dictionary record) is passed as an argument to a function, Python uses **pass-by-assignment** (passing object references).
*   Modifying a dictionary inside a helper function (e.g., `record["status"] = "Active"`) mutates the original object on the heap, making the change visible across all variables referencing that object.

```
========================================================================================
                                PYTHON HEAP MEMORY & NAMESPACES
========================================================================================

NAMESPACE (Stack / Local Scope)                 HEAP MEMORY (Objects & References)
-------------------------------                 ----------------------------------

                                                +--------------------------------+
  pets  ------------------------------------->  | List Object at 0x7f90          |
                                                | Index 0: ref 0x101 ------------|----+
                                                | Index 1: ref 0x102 ------------|--+ |
                                                +--------------------------------+  | |
                                                                                    | |
  by_species ----------------+                                                      | |
                             |                  +--------------------------------+  | |
                             |               -> | Dict Object at 0x101          | <+ |
                             |               |  | "name"    : ref 0xABC --------|---|----+
                             |               |  | "species" : ref 0xDEF --------|---|--|-+
                             |               |  +--------------------------------+  |  | |
                             v               |                                      |  | |
                +-------------------------+  |  +--------------------------------+  |  | |
                | Dict Object at 0x8A00   |  |  | Dict Object at 0x102          | <-+  | |
                | "dragon" : ref 0x9B00 --|--|->| "name"    : ref 0xACC          |      | |
                +-------------------------+  |  | "species" : ref 0xDEF ---------|------|-+
                                             |  +--------------------------------+      | |
                                             |                                          | |
                                             |  +--------------------------------+      | |
                                             +--| List Object at 0x9B00          |      | |
                                                | Index 0: ref "Flamey"          |      | |
                                                +--------------------------------+      | |
                                                                                        | |
                                                +--------------------------------+      | |
                                                | String Object: "Flamey" (0xABC)| <----+ |
                                                +--------------------------------+        |
                                                                                          |
                                                +--------------------------------+        |
                                                | String Object: "dragon" (0xDEF)| <------+
                                                +--------------------------------+
========================================================================================
```

--------------------------------------------------------------------------------

#### 6. Practical Integration / Mini Case Study
##### Integrated Retail Order & Inventory State Manager
This script combines all Week 3 concepts into a single execution workflow:
1.  **Filtering:** Extracting active valid orders.
2.  **Dictionary Indexing:** Building an $O(1)$ lookup index for inventory items.
3.  **Grouping:** Categorizing orders into customer tier buckets ("VIP", "Standard").
4.  **Functional Pipeline:** Processing unit prices through tax, discount, and shipping functions.
5.  **Loop Skeleton & Helpers:** Using single-purpose helper functions inside a clean main loop.

```python
# Raw Dataset 1: List of Dictionaries representing orders
raw_orders = [
    {"order_id": 1001, "customer": "Alice", "sku": "A1", "qty": 2, "status": "COMPLETED", "tier": "VIP"},
    {"order_id": 1002, "customer": "Bob", "sku": "B2", "qty": 1, "status": "CANCELLED", "tier": "Standard"},
    {"order_id": 1003, "customer": "Charlie", "sku": "A1", "qty": 1, "status": "COMPLETED", "tier": "Standard"},
    {"order_id": 1004, "customer": "Diana", "sku": "C3", "qty": 3, "status": "COMPLETED", "tier": "VIP"}
]

# Raw Dataset 2: List of Dictionaries representing inventory catalog
inventory_catalog = [
    {"sku": "A1", "name": "Mechanical Keyboard", "unit_price": 100.00},
    {"sku": "B2", "name": "Ergonomic Mouse", "unit_price": 50.00},
    {"sku": "C3", "name": "UltraWide Monitor", "unit_price": 300.00}
]

# --------------------------------------------------------------------------------------
# PIPELINE FUNCTIONS & HELPERS
# --------------------------------------------------------------------------------------

def is_valid_order(order):
    # Filter Helper: Checks if order status is COMPLETED
    return order["status"] == "COMPLETED"

def add_tax(amount):
    # Pipeline Stage 1: Applies 8% sales tax
    return amount * 1.08

def apply_tier_discount(amount, tier):
    # Pipeline Stage 2: Applies 15% discount for VIPs, 5% for Standard
    if tier == "VIP":
        return amount * 0.85
    return amount * 0.95

def add_flat_shipping(amount):
    # Pipeline Stage 3: Adds flat $10 shipping charge
    return amount + 10.00

def calculate_order_total(unit_price, qty, tier):
    # Per-Item Helper: Chains pricing pipeline for a single order
    base_cost = unit_price * qty
    taxed = add_tax(base_cost)
    discounted = apply_tier_discount(taxed, tier)
    final_cost = add_flat_shipping(discounted)
    return final_cost

# --------------------------------------------------------------------------------------
# MAIN EXECUTION WORKFLOW
# --------------------------------------------------------------------------------------

def main():
    print("=== STARTING ORDER PROCESSING SYSTEM ===")

    # STEP 1: Build Dictionary Index for O(1) Catalog Lookups
    inventory_by_sku = {}
    for item in inventory_catalog:
        sku = item["sku"]
        inventory_by_sku[sku] = item
    
    # STEP 2: Filter Valid Orders
    valid_orders = []
    for order in raw_orders:
        if is_valid_order(order):
            valid_orders.append(order)

    # STEP 3: Group Orders by Customer Tier & Process Totals
    orders_by_tier = {}
    grand_total_revenue = 0.00

    for order in valid_orders:
        tier = order["tier"]
        sku = order["sku"]
        
        # Direct lookup into Inventory Index
        item_data = inventory_by_sku[sku]
        unit_price = item_data["unit_price"]
        
        # Calculate final pricing via pipeline helper
        total_price = calculate_order_total(unit_price, order["qty"], tier)
        grand_total_revenue += total_price
        
        # Store processed summary dictionary in order record
        summary = {
            "order_id": order["order_id"],
            "customer": order["customer"],
            "item_name": item_data["name"],
            "final_price": round(total_price, 2)
        }

        # Incremental Grouping Pattern
        if tier not in orders_by_tier:
            orders_by_tier[tier] = []
        orders_by_tier[tier].append(summary)

    # STEP 4: Output Processed Tier Groups
    for tier_label, order_list in orders_by_tier.items():
        print(f"\n--- Tier Bucket: {tier_label} ---")
        for summary_record in order_list:
            print(f"  Order #{summary_record['order_id']} ({summary_record['customer']}): "
                  f"{summary_record['item_name']} -> Total: ${summary_record['final_price']:.2f}")

    print(f"\nSystem Total Revenue: ${grand_total_revenue:.2f}")

if __name__ == "__main__":
    main()

# ======================================================================================
# COMPLETE TERMINAL OUTPUT EXECUTION TRACE
# ======================================================================================
# === STARTING ORDER PROCESSING SYSTEM ===
#
# --- Tier Bucket: VIP ---
#   Order #1001 (Alice): Mechanical Keyboard -> Total: $207.20
#   Order #1004 (Diana): UltraWide Monitor -> Total: $836.20
#
# --- Tier Bucket: Standard ---
#   Order #1003 (Charlie): Mechanical Keyboard -> Total: $112.60
#
# System Total Revenue: $1156.00
# ======================================================================================
```

--------------------------------------------------------------------------------

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
Analyze each code challenge line-by-line to trace variable reassignments, mathematical evaluations, and intermediate terminal outputs.

##### Challenge A: Nested Pipeline with State Mutability & Decimals
```python
def calc_step1(val):
    return val * 1.05  # Adds 5%

def calc_step2(val, bonus):
    return val + bonus

def calc_step3(val):
    return val * 0.80  # 20% discount

raw_val = 200
bonus_amount = 10

# Nested functional call
result = calc_step3(calc_step2(calc_step1(raw_val), bonus_amount))
print(f"Result: {result:.2f}")
```

###### Step-by-Step State Evaluation Table:
| Step / Line | Expression Evaluated | Intermediate State / Value | Notes |
| ------ | ------ | ------ | ------ |
| **Line 11** | calc_step1(200) | 200 * 1.05 = 210.0 | 5% added to base value |
| **Line 11** | calc_step2(210.0, 10) | 210.0 + 10 = 220.0 | $10 flat bonus added |
| **Line 11** | calc_step3(220.0) | 220.0 * 0.80 = 176.0 | 20% discount applied (keeps 80%) |
| **Line 12** | f"Result: {176.0:.2f}" | "Result: 176.00" | Formatted float output |

**Final Terminal Output:**
```text
Result: 176.00
```

--------------------------------------------------------------------------------

##### Challenge B: Incremental Grouping with Key Initializations
```python
data = [
    {"type": "fruit", "item": "apple"},
    {"type": "veg", "item": "carrot"},
    {"type": "fruit", "item": "banana"}
]

bucket = {}

for entry in data:
    t = entry["type"]
    i = entry["item"]
    if t not in bucket:
        bucket[t] = []
    bucket[t].append(i)

print("Keys:", list(bucket.keys()))
print("Fruit count:", len(bucket["fruit"]))
```

###### Step-by-Step State Evaluation Table:
| Iteration | Variable State (t, i) | t not in bucket Check | bucket Memory State After Append |
| ------ | ------ | ------ | ------ |
| **Start** | bucket = {} | N/A | {} |
| **Iter 1** | t="fruit", i="apple" | True -> bucket["fruit"] = [] | {"fruit": ["apple"]} |
| **Iter 2** | t="veg", i="carrot" | True -> bucket["veg"] = [] | {"fruit": ["apple"], "veg": ["carrot"]} |
| **Iter 3** | t="fruit", i="banana" | False (skips initialization) | {"fruit": ["apple", "banana"], "veg": ["carrot"]} |

**Final Terminal Output:**
```text
Keys: ['fruit', 'veg']
Fruit count: 2
```

--------------------------------------------------------------------------------

##### Challenge C: Dictionary Index vs. Nested Loop Comparison Counter
```python
orders = [{"id": 1}, {"id": 2}, {"id": 3}]
catalog = {1: "Item A", 2: "Item B", 3: "Item C"}

loop_count = 0
for order in orders:
    item_id = order["id"]
    if item_id in catalog:
        loop_count += 1
        item_name = catalog[item_id]

print(f"Processed {len(orders)} orders in {loop_count} comparisons.")
```

###### Step-by-Step State Evaluation Table:
| Order Iteration | item_id | item_id in catalog Check | loop_count State | item_name Retrieved |
| ------ | ------ | ------ | ------ | ------ |
| **Iter 1** | 1 | 1 in catalog (True) | 1 | "Item A" |
| **Iter 2** | 2 | 2 in catalog (True) | 2 | "Item B" |
| **Iter 3** | 3 | 3 in catalog (True) | 3 | "Item C" |

**Final Terminal Output:**
```text
Processed 3 orders in 3 comparisons.
```

--------------------------------------------------------------------------------

##### Challenge D: Dual Accumulators in Loop Skeleton with Per-Item Helper
```python
def process_score(raw_score):
    return raw_score + 5  # Add 5 point curve

scores = [75, 82, 90]
passing_count = 0
total_score = 0

for s in scores:
    curved = process_score(s)
    total_score += curved
    if curved >= 85:
        passing_count += 1

avg_score = total_score / len(scores)
print(f"Avg: {avg_score:.1f}, Passing: {passing_count}")
```

###### Step-by-Step State Evaluation Table:
| Iteration | s | curved (s + 5) | total_score (+ curved) | curved >= 85 | passing_count State |
| ------ | ------ | ------ | ------ | ------ | ------ |
| **Iter 1** | 75 | 80 | 0 + 80 = 80 | 80 >= 85 (False) | 0 |
| **Iter 2** | 82 | 87 | 80 + 87 = 167 | 87 >= 85 (True) | 1 |
| **Iter 3** | 90 | 95 | 167 + 95 = 262 | 95 >= 85 (True) | 2 |
| **Post-Loop** | N/A | N/A | avg_score = 262 / 3 = 87.3333... | N/A | passing_count = 2 |

**Final Terminal Output:**
```text
Avg: 87.3, Passing: 2
```

--------------------------------------------------------------------------------

*End of Master Reference Document.*

---
## PART IV: WEEK 4 - Foundations of Software Engineering & The Full Development Pipeline

### CS101 - Week 4 Master Reference: Foundations of Software Engineering & The Full Development Pipeline
*This document synthesizes all core concepts, mental models, memory mechanics, state traces, and defensive programming patterns from Module 4 into an authoritative, self-contained reference guide. It covers the complete transition from conceptual specification to verified, modular Python implementation.*

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

--------------------------------------------------------------------------------

#### 1. Abstract Foundations & Core Theory
Software engineering is distinguished from ad-hoc programming by a disciplined, multi-stage pipeline that converts ambiguous requests into verified, modular software systems. This section formalizes the theoretical foundations of the software development lifecycle.

##### Formal Definitions of Primary Concepts

###### 1. Specification & The Four Pillars ("Thinking Before Typing")
A specification (or "spec") is a language-neutral contract defining software requirements before code is written. Rushing into implementation without a spec causes logic gaps, unnecessary rework, and incorrect assumptions. A complete specification relies on four foundational pillars:
*   **Inputs:** The exact data elements the program receives from external sources (e.g., data types, structures, parameters).
*   **Outputs:** The specific data return values or visual displays produced after execution.
*   **Constraints:** The operational rules and invariants the solution must strictly obey (e.g., non-negative pricing, integer-only restrictions).
*   **Edge Cases:** Exceptional, unusual, or boundary conditions the program must gracefully handle without collapsing (e.g., empty lists, zero quantities, non-numeric strings).

###### 2. Acceptance Criteria & Definition of "Done"
An acceptance criterion is an unambiguous, testable pass/fail statement structured as a deterministic state promise: *Given a specific input, when the function executes, then it must yield an exact output.*
*   **Boundary Conditions:** Valid input values residing precisely on the threshold of a decision rule (e.g., testing temp = 10 for a rule temp < 10 -> "cold" vs temp >= 10 -> "warm"). Boundary values are the primary source of off-by-one errors.
*   **Invalid Inputs:** Inputs that violate the function contract (e.g., passing None or string "100" to a numeric calculator). They must trigger controlled error messaging or exceptions.
*   **Definition of "Done":** A feature is strictly considered complete ("done-done") only when all predefined acceptance criteria—covering normal cases, boundaries, and invalid inputs—pass successfully.

###### 3. Pseudocode: The Plain-Language Recipe
Pseudocode is a language-neutral, step-by-step design blueprint that mirrors formal algorithmic flow using structured plain language.
*   **Core Syntax Rules:**
    1. Action-First Verbs: Each line begins with an imperative action (e.g., ASK, CHECK, CALCULATE, RETURN).
    2. Atomic Steps: Exactly one distinct operation per line.
    3. Structural Indentation: Indentation strictly represents hierarchical control blocks (IF, ELSE, FOR EACH).

###### 4. Incremental Implementation & Micro-Verification Loops
Incremental implementation is the practice of constructing software through small, verified iterations rather than monolithic coding.
*   **Smallest Testable Unit (STU):** The minimal single input/output assertion pair that isolates one specific program behavior (e.g., calculate_shipping_fee(30) -> 10).
*   **Micro-Verification Loop:** The continuous cycle: *Define STU -> Write Minimal Code -> Execute Assert Test -> Refine -> Repeat*.
*   **Assertion Hard-Checking:** The execution of Python assert statements to programmatically enforce promises, stopping execution instantly upon contract failure.

###### 5. Pipeline Integration & Helper Function Orchestration
A pipeline integrates independent units into a modular execution flow.
*   **Helper Functions:** Pure, single-responsibility functions that execute specific tasks (e.g., validate_item, calculate_shipping).
*   **Main Loop Orchestrator:** A primary function (e.g., calculate_cart) that iterates over collections, delegates validation and calculations to helpers, accumulates intermediate subtotals and error state, and constructs a clean summary data structure.

--------------------------------------------------------------------------------

##### Side-by-Side Architectural Comparison Matrix
| Feature / Spec | Specification (4 Pillars) | Acceptance Criteria | Pseudocode Recipe | Incremental Implementation | Pipeline Main Loop |
| ------ | ------ | ------ | ------ | ------ | ------ |
| **Primary Objective** | Eliminate ambiguity before coding | Define deterministic "Definition of Done" | Design language-agnostic logic flow | Verify micro-behaviors step-by-step | Integrate helpers into end-to-end execution |
| **Input / Artifact** | Problem statement / Feature request | Specific input values and edge scenarios | Structured plain-text algorithm | Smallest Testable Unit (STU) | Data collections (e.g., list of item dicts) |
| **Output / Artifact** | 4-Pillar Spec Table | Pass/Fail binary test statements | Indented step-by-step instructions | Python code + pass/fail assert statement | Summary output dictionary |
| **Core Delimiters / Keywords** | Inputs, Outputs, Constraints, Edge Cases | Given, When, Then, Must Return | CHECK, IF, ELSE, FOR, RETURN | def, return, assert == | for item in cart:, status = helper() |
| **Primary Quality Metric** | Exhaustiveness & complete scope coverage | Unambiguous pass/fail binary status | Concrete action verbs & line alignment | High assertion density & instant feedback | High modularity & error isolation |
| **Common Failure Mode** | Unstated requirements causing rework | Vague promises (e.g., "should work well") | High-level hand-waving (e.g., "do login stuff") | Writing full features before testing | Hardcoded errors & global scope pollution |

--------------------------------------------------------------------------------

#### 2. Real-World Mental Models & Conceptual Mapping
To master software engineering habits, abstract programming mechanics must be mapped to physical and structural analogies.

##### Conceptual Analogy 1: The Subway Sandwich Recipe
*   **Vague Request:** "Make me a good sandwich." (Leads to incorrect ingredients, wrong bread, and complete customer dissatisfaction).
*   **Pseudocode Blueprint:**
```text
GET 6-inch Italian bread
ADD turkey and bacon
TOAST sandwich
IF customer wants veggies:
    ADD lettuce, tomato, mayo
CUT in half AND SERVE
```
*   **Python Execution:** The line-by-line physical execution in the kitchen following exact syntax and rules.

##### Conceptual Analogy 2: Quality Assurance & Customs Border Control
*   **Valid Normal Input:** Standard passport holder -> Fast lane through customs.
*   **Boundary Condition:** Passport expiring on the exact day of travel -> Valid, but sitting directly on the rule boundary. Requires precise verification.
*   **Invalid Edge Case:** Carrying an invalid paper scrap or foreign item -> Fails the fundamental contract, immediately stopped at border checkpoint with a clear rejection code.

##### Conceptual Analogy 3: Factory Assembly Line & Helper Relay
*   **Raw Materials:** Unprocessed list of cart items entering the facility.
*   **Station 1 (Validation Helper):** Inspects each item against the master inventory catalog. If defective, flags an error tag; if valid, approves line item cost.
*   **Station 2 (Shipping Calculator Helper):** Evaluates total approved weight/cost and applies shipping fee logic.
*   **Final Packing (Main Pipeline):** Packages subtotals, shipping, final totals, and error manifests into a sealed export box (Dictionary).

--------------------------------------------------------------------------------

##### ASCII Structural Diagrams

###### Figure 2.1: The Full Development Pipeline Architecture
```text
+---------------------------------------------------------------------------------+
|                                 DEVELOPMENT PIPELINE                            |
|                                                                                 |
|  [ Feature Request ]                                                            |
|          |                                                                      |
|          v                                                                      |
|  +---------------------------------------------------------------------------+  |
|  | STEP 1: SPECIFICATION (4 Pillars)                                         |  |
|  | - Inputs       - Outputs       - Constraints       - Edge Cases           |  |
|  +---------------------------------------------------------------------------+  |
|          |                                                                      |
|          v                                                                      |
|  +---------------------------------------------------------------------------+  |
|  | STEP 2: ACCEPTANCE CRITERIA (Definition of Done)                          |  |
|  | - Boundary Conditions (Valid edges)  - Invalid Inputs (Contract breaks)   |  |
|  +---------------------------------------------------------------------------+  |
|          |                                                                      |
|          v                                                                      |
|  +---------------------------------------------------------------------------+  |
|  | STEP 3: PSEUDOCODE RECIPE                                                 |  |
|  | - Imperative Verbs  - 1 Action / Line  - Indented Control Flow            |  |
|  +---------------------------------------------------------------------------+  |
|          |                                                                      |
|          v                                                                      |
|  +---------------------------------------------------------------------------+  |
|  | STEP 4: INCREMENTAL IMPLEMENTATION (Micro-Verification Loop)              |  |
|  |   [ Smallest Testable Unit ] ---> [ Code Stub ] ---> [ Assert Check ]     |  |
|  |            ^                                                |                |  |
|  |            +----------------- Refine Logic <----------------+                |  |
|  +---------------------------------------------------------------------------+  |
|          |                                                                      |
|          v                                                                      |
|  +---------------------------------------------------------------------------+  |
|  | STEP 5: PIPELINE ORCHESTRATION & INTEGRATION                              |  |
|  | - Pure Helper Functions (validate_item, calculate_shipping)              |  |
|  | - Main Loop Integration (calculate_cart) -> Final Summary Dictionary     |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
```

###### Figure 2.2: The Micro-Verification Loop (code a bit -> assert a bit)
```text
                  +--------------------------+
                  |  Pick Smallest Testable  |
                  |     Unit (Input/Output)  |
                  +--------------------------+
                               |
                               v
                  +--------------------------+
                  |  Write / Update Code     |
                  +--------------------------+
                               |
                               v
                  +--------------------------+
                  | Run Assert Statement     |
                  +--------------------------+
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
         [ ASSERTION FAILS ]        [ ASSERTION PASSES ]
                 |                           |
                 | (Fix Bug)                 v
                 +---------------> [ Add Next Behavior / STU ]
```

--------------------------------------------------------------------------------

#### 3. Idiomatic Python Implementation & State Tracing
This section demonstrates the line-by-line implementation of Week 4 engineering concepts. Inline comments trace exact variable bindings, evaluation states, and stdout results.

##### Topic A: Translating Pseudocode to Python Flow
```python
# PSEUDOCODE PLAN:
# CHECK if cart has any items
# IF cart is empty
#     SHOW "Your cart is empty"
# ELSE
#     SHOW "You have X items in your cart"

# INITIALIZATION
cart_items = ["apple", "banana"]  # State: cart_items bound to list of length 2

# LINE-BY-LINE TRANSLATION & STATE TRACE
if len(cart_items) == 0:          # Evaluates: len(["apple", "banana"]) == 0 -> 2 == 0 -> False
    print("Your cart is empty")    # Skipped due to False condition
else:
    # f-string evaluates len(cart_items) -> 2
    print(f"You have {len(cart_items)} items in your cart")
    # CONSOLE OUTPUT: You have 2 items in your cart
```

##### Topic B: Boundary Verification & Acceptance Criteria Enforcement
```python
def temperature_to_label(temp):
    """
    Acceptance Criteria:
    - temp < 10            -> "cold"
    - 10 <= temp < 25      -> "warm"
    - temp >= 25           -> "hot"
    - non-numeric input    -> "invalid input"
    """
    if not isinstance(temp, (int, float)): # Guard clause for invalid types
        return "invalid input"
    
    if temp < 10:                          # Lower boundary check
        return "cold"
    elif temp < 25:                        # Mid-range boundary check
        return "warm"
    else:                                  # Upper boundary check
        return "hot"

# EXECUTING BOUNDARY TEST SUITE WITH ASSERTS
# Test 1: Below lower boundary
res1 = temperature_to_label(9)
# State: temp=9 -> 9 < 10 -> True -> Returns "cold"
assert res1 == "cold"                      # Evaluation: "cold" == "cold" -> True

# Test 2: Exactly on lower boundary cutoff
res2 = temperature_to_label(10)
# State: temp=10 -> 10 < 10 -> False -> 10 < 25 -> True -> Returns "warm"
assert res2 == "warm"                      # Evaluation: "warm" == "warm" -> True

# Test 3: Upper boundary cutoff
res3 = temperature_to_label(25)
# State: temp=25 -> 25 < 10 -> False -> 25 < 25 -> False -> Else -> Returns "hot"
assert res3 == "hot"                       # Evaluation: "hot" == "hot" -> True

# Test 4: Invalid Edge Case
res4 = temperature_to_label("hot")
# State: temp="hot" -> isinstance("hot", (int, float)) -> False -> Returns "invalid input"
assert res4 == "invalid input"             # Evaluation: "invalid input" == "invalid input" -> True

print("All Temperature Boundary Asserts Passed Successfully!")
# CONSOLE OUTPUT: All Temperature Boundary Asserts Passed Successfully!
```

##### Topic C: Incremental Implementation with Assert Stubs
```python
def apply_discount(price, discount_percent):
    """
    STU 1: (100, 10) -> 90
    STU 2: (50, 0)   -> 50
    """
    # Step 1: Calculate raw discount value
    discount_amount = price * discount_percent / 100
    # State (for 100, 10): 100 * 10 / 100 -> 10.0
    
    # Step 2: Compute net price
    final_price = price - discount_amount
    # State (for 100, 10): 100 - 10.0 -> 90.0
    
    return final_price

# Micro-Test 1 Execution
test1_res = apply_discount(100, 10)
# State: test1_res = 90.0
assert test1_res == 90                     # Evaluates: 90.0 == 90 -> True

# Micro-Test 2 Execution (Zero Discount Boundary)
test2_res = apply_discount(50, 0)
# State: discount_amount = 50 * 0 / 100 -> 0.0; final_price = 50 - 0.0 -> 50.0
assert test2_res == 50                     # Evaluates: 50.0 == 50 -> True

print("Incremental Discount Unit Tests Passed!")
# CONSOLE OUTPUT: Incremental Discount Unit Tests Passed!
```

--------------------------------------------------------------------------------

#### 4. Defensive Programming & Common Traps
When transitioning from plain-English specifications to code, engineers frequently encounter specific categories of runtime exceptions and logical defects.

##### Trap 1: F-String Quote Reuse Syntax Error
*   **Root Cause:** Nesting double quotes inside an f-string dictionary lookup terminates the string literal prematurely, raising a SyntaxError.

```python
# INCORRECT: Re-using double quotes inside f-string expression
cart = {"sku": "A1", "price": 19.99}
# RUNTIME ERROR: SyntaxError: f-string: matched '(' expecting ')' or invalid syntax
# err_msg = f"Price mismatch for sku {cart["sku"]}"

# CORRECT: Mix single quotes inside double-quoted f-string
cart = {"sku": "A1", "price": 19.99}
err_msg = f"Price mismatch for sku {cart['sku']}"
# Evaluation: f"Price mismatch for sku {'A1'}" -> "Price mismatch for sku A1"
assert err_msg == "Price mismatch for sku A1"
```

##### Trap 2: Dictionary Accumulator Reset Bug
*   **Root Cause:** Assigning `= 1` inside an `if key in dict:` branch resets existing counts back to 1 instead of incrementing them with `+= 1`.

```python
# INCORRECT: Overwriting accumulated count
errors = ["404", "500", "404", "403"]
counts = {}
for code in errors:
    if code in counts:
        counts[code] = 1   # BUG: Resets count to 1 on subsequent encounters!
    else:
        counts[code] = 1
# Resulting counts state: {"404": 1, "500": 1, "403": 1} -- INCORRECT!

# CORRECT: Increment existing keys with += 1
errors = ["404", "500", "404", "403"]
counts = {}
for code in errors:
    if code in counts:
        counts[code] += 1  # CORRECT: Mutates stored integer value by +1
    else:
        counts[code] = 1   # Initializes key on first encounter
# Resulting counts state: {"404": 2, "500": 1, "403": 1} -- CORRECT!
assert counts["404"] == 2
```

##### Trap 3: Global Parameter Shadowing in Helper Functions
*   **Root Cause:** Referencing a global variable identifier (e.g., `inventory_dict`) inside a function scope rather than referencing the function's parameter argument (e.g., `inventory`). This creates brittle code that breaks when passed alternative test dictionaries.

```python
# INCORRECT: Helper function ignores parameter and reads global scope
global_inventory = {"A1": 20.00}

def validate_item_buggy(item, inventory):
    # BUG: Reading global_inventory directly instead of using parameter 'inventory'
    if item["sku"] not in global_inventory: 
        return -1
    return 1

# CORRECT: Pure function referencing local parameter namespace
def validate_item_correct(item, inventory):
    # CORRECT: Binds strictly to whatever object is passed to 'inventory'
    if item["sku"] not in inventory:
        return -1
    return 1
```

##### Trap 4: Work Inside the Iteration Loop (Loop Misplacement)
*   **Root Cause:** Placing final calculations (`shipping = calculate_shipping(subtotal)`) or result packaging inside the for loop body, causing repetitive recalculations and premature return states.

```python
# INCORRECT: Packaging result inside loop body
def calculate_cart_buggy(carts, inventory):
    subtotal = 0
    for item in carts:
        subtotal += item["price"] * item["quantity"]
        # BUG: Shipping and return executed on FIRST item iteration!
        shipping = 10 if subtotal < 150 else 0
        return {"subtotal": subtotal, "shipping": shipping} 

# CORRECT: Accumulate in loop, finalize AFTER loop completion
def calculate_cart_correct(carts, inventory):
    subtotal = 0
    errors = []
    # STEP 1: Loop accumulates state
    for item in carts:
        subtotal += item["price"] * item["quantity"]
    
    # STEP 2: Finalize AFTER loop terminates (out-dented)
    shipping = 10 if subtotal < 150 else 0
    total = subtotal + shipping
    return {"subtotal": subtotal, "shipping": shipping, "total": total}
```

--------------------------------------------------------------------------------

#### 5. Python Memory Mechanics, References & Scope
Understanding Python's memory management model is essential for tracing state across modular helper functions and pipeline orchestrators.

##### Dynamic Typing, Variable Binding, and Namespace Mapping
1.  **Variables as Pointers:** In Python, variables do not store raw data bytes directly. A variable name is a symbol residing in a **Namespace** (a dictionary-like mapping of names to memory addresses) that points to an **Object in Heap Memory**.
2.  **Assignment (** `=` **):** Performing `x = 10` binds the name x in the current frame namespace to the integer object 10 residing on the heap. Reassigning `x = 20` does not overwrite the memory of 10; it updates x to point to a different heap object 20.
3.  **Mutability vs. Immutability:**
    *   **Immutable Objects:** int, float, str, bool, tuple. Their underlying heap values cannot be changed in-place.
    *   **Mutable Objects:** list, dict, set. Modifying a list via `.append()` or a dict via `d[k] = v` mutates the object directly in heap memory. All variable names pointing to that same object reflect the change immediately.
4.  **Call-by-Object-Reference Scope Mechanics:**
    *   When `calculate_cart(carts, inventory_dict)` is called, a new local execution frame is created on the call stack.
    *   Parameters carts and inventory inside the function frame are bound to the *exact same heap memory addresses* as the arguments carts and inventory_dict in the global scope.

--------------------------------------------------------------------------------

##### Memory Visualization Diagram
```text
GLOBAL NAMESPACE FRAME                         HEAP MEMORY (Objects)
+-----------------------+                      +---------------------------------------+
|  PRICE_ERROR          |--------------------->| PyIntObject: -2                       |
|  OUT_OF_STOCK         |--------------------->| PyIntObject: -1                       |
|  ITEM_VALIDATED       |--------------------->| PyIntObject: 1                        |
|                       |                      |                                       |
|  inventory_dict       |--------------------->| PyDictObject (Address: 0x7F01)        |
|                       |                      |   "A1": 20.00                         |
|                       |                      |   "B2": 5.00                          |
|  carts                |------------+         +---------------------------------------+
+-----------------------+            |
                                     |         +---------------------------------------+
CALCULATE_CART FRAME                 +-------->| PyListObject (Address: 0x8A02)        |
+-----------------------+                      |   [0]: Dict -> {"sku":"A1", ...}      |
|  carts (parameter)    |--------------------->|   [1]: Dict -> {"sku":"B2", ...}      |
|  inventory (parameter)|-------+              +---------------------------------------+
|                       |       |
|  subtotal             |---|   +-------------> PyDictObject (Address: 0x7F01)
|  errors_list          |--+|                  
+-----------------------+  ||                  +---------------------------------------+
                           ||                  | PyFloatObject: 15.00 (Rebound value)  |
                           ||                  +---------------------------------------+
                           ||
                           |+----------------->+---------------------------------------+
                           |                   | PyListObject: ["SKU C2 not in inventory"]|
                           |                   +---------------------------------------+
                           |
                           +------------------>+---------------------------------------+
                                               | PyFloatObject: 0.0 -> 15.0 (Rebound)  |
                                               +---------------------------------------+
```

--------------------------------------------------------------------------------

#### 6. Practical Integration / Mini Case Study
This section presents a complete, fully functional, multi-file-style shopping cart and shipping pipeline. It synthesizes all module concepts: domain constants, item validation helpers, shipping calculators, and main loop orchestration with comprehensive state tracing.

```python
# ==============================================================================
# CS101 MODULE 4: AUTOMATED SHOPPING CART & SHIPPING PIPELINE SYSTEM
# ==============================================================================

# ------------------------------------------------------------------------------
# SECTION 1: DOMAIN CONSTANTS (Status Codes)
# ------------------------------------------------------------------------------
PRICE_ERROR = -2
OUT_OF_STOCK = -1
ITEM_VALIDATED = 1

# ------------------------------------------------------------------------------
# SECTION 2: HELPER FUNCTIONS (Pure, Single-Responsibility Units)
# ------------------------------------------------------------------------------
def calculate_shipping(subtotal):
    """
    Calculates shipping cost based on subtotal.
    Rule: Free shipping if subtotal >= 150.00, otherwise $10.00 flat fee.
    """
    if subtotal >= 150.00:
        return 0.0
    else:
        return 10.0


def validate_item(item_dict, inventory_dict):
    """
    Validates a single cart item dictionary against master inventory.
    Returns:
        ITEM_VALIDATED (1)  if SKU exists and price matches inventory.
        PRICE_ERROR (-2)    if SKU exists but price mismatches.
        OUT_OF_STOCK (-1)   if SKU does not exist in inventory.
    """
    sku = item_dict["sku"]
    price = item_dict["price"]
    
    if sku not in inventory_dict:
        return OUT_OF_STOCK
    
    expected_price = inventory_dict[sku]
    if price != expected_price:
        return PRICE_ERROR
        
    return ITEM_VALIDATED

# ------------------------------------------------------------------------------
# SECTION 3: MAIN PIPELINE ORCHESTRATOR
# ------------------------------------------------------------------------------
def calculate_cart(carts, inventory):
    """
    Orchestrates cart validation, subtotal aggregation, error reporting,
    and shipping calculations.
    Returns a structured summary dictionary.
    """
    subtotal = 0.0
    errors_list = []
    
    # ITERATION LOOP: Process each cart item line
    for item in carts:
        status = validate_item(item, inventory)
        
        if status == ITEM_VALIDATED:
            # Line item total calculation
            subtotal += item["price"] * item["quantity"]
        else:
            # Construct dynamic error message based on failure status
            if status == OUT_OF_STOCK:
                err_msg = f"SKU {item['sku']} not in inventory"
            elif status == PRICE_ERROR:
                err_msg = f"Price mismatch for sku {item['sku']}"
            else:
                err_msg = f"Unknown validation error for sku {item['sku']}"
            errors_list.append(err_msg)
            
    # POST-LOOP ORCHESTRATION: Final calculations
    shipping_cost = calculate_shipping(subtotal)
    grand_total = subtotal + shipping_cost
    
    # PACKAGING SUMMARY DICTIONARY
    result_manifest = {
        "subtotal": round(subtotal, 2),
        "shipping": round(shipping_cost, 2),
        "total": round(grand_total, 2),
        "errors": errors_list
    }
    return result_manifest

# ------------------------------------------------------------------------------
# SECTION 4: SYSTEM EXECUTION & STATE TRACE DEMONSTRATION
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Master Inventory Database Setup
    inventory_database = {
        "A1": 20.00,
        "B2": 5.00,
        "C3": 9.00
    }
    
    # Customer Cart Input Scenario
    customer_cart = [
        {"sku": "A1", "price": 19.99, "quantity": 2},  # Item 1: Price Mismatch (19.99 vs 20.00)
        {"sku": "B2", "price": 5.00,  "quantity": 3},  # Item 2: Valid (5.00 * 3 = 15.00)
        {"sku": "X9", "price": 9.00,  "quantity": 1}   # Item 3: Out of Stock (X9 missing)
    ]
    
    # Execute Pipeline
    pipeline_output = calculate_cart(customer_cart, inventory_database)
    
    # Output Verification Traces
    print("=== PIPELINE EXECUTION OUTPUT ===")
    print(f"Subtotal: ${pipeline_output['subtotal']}")
    print(f"Shipping: ${pipeline_output['shipping']}")
    print(f"Total:    ${pipeline_output['total']}")
    print(f"Errors:   {pipeline_output['errors']}")
    
    # System Unit Tests (Verification Criteria)
    assert pipeline_output["subtotal"] == 15.00
    assert pipeline_output["shipping"] == 10.00
    assert pipeline_output["total"] == 25.00
    assert len(pipeline_output["errors"]) == 2
    assert "Price mismatch for sku A1" in pipeline_output["errors"]
    assert "SKU X9 not in inventory" in pipeline_output["errors"]
    print("\n[SYSTEM VERIFICATION]: All end-to-end integration assertions passed!")
```

--------------------------------------------------------------------------------

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
This section provides four diagnostic code tracing challenges designed to test line-by-line mental execution, boundary evaluation, and state mutation tracking.

##### Challenge A: Boundary Evaluation in Multi-Branch Logic
###### Source Code:
```python
def classify_shipping_tier(subtotal, is_vip):
    if is_vip or subtotal >= 150.0:
        return 0.0
    elif subtotal >= 50.0:
        return 5.0
    else:
        return 10.0

# Diagnostic Line-by-Line Execution Trace:
val1 = classify_shipping_tier(150.0, False)
# Line 2: Evaluation: (is_vip=False) or (subtotal=150.0 >= 150.0 -> True) -> False or True -> True
# Line 3: Executes 'return 0.0'
# Bound Result: val1 = 0.0

val2 = classify_shipping_tier(49.99, False)
# Line 2: Evaluation: False or (49.99 >= 150.0 -> False) -> False
# Line 4: Evaluation: 49.99 >= 50.0 -> False
# Line 6: Executes 'else: return 10.0'
# Bound Result: val2 = 10.0

val3 = classify_shipping_tier(20.0, True)
# Line 2: Evaluation: (is_vip=True) or ... -> Short-circuit True!
# Line 3: Executes 'return 0.0'
# Bound Result: val3 = 0.0

print(f"Results: {val1}, {val2}, {val3}")
# TERMINAL OUTPUT: Results: 0.0, 10.0, 0.0
```

--------------------------------------------------------------------------------

##### Challenge B: Dictionary Frequency Counter State Mutation
###### Source Code:
```python
raw_log = ["500", "404", "500", "200", "404", "500"]
error_counts = {}

for entry in raw_log:
    if entry in error_counts:
        error_counts[entry] += 1
    else:
        error_counts[entry] = 1

# Diagnostic Iteration Step Trace:
# Iteration 1: entry = "500" -> "500" in {} -> False -> error_counts["500"] = 1
# Iteration 2: entry = "404" -> "404" in {"500":1} -> False -> error_counts["404"] = 1
# Iteration 3: entry = "500" -> "500" in {"500":1,"404":1} -> True -> error_counts["500"] += 1 (becomes 2)
# Iteration 4: entry = "200" -> "200" in dict -> False -> error_counts["200"] = 1
# Iteration 5: entry = "404" -> "404" in dict -> True -> error_counts["404"] += 1 (becomes 2)
# Iteration 6: entry = "500" -> "500" in dict -> True -> error_counts["500"] += 1 (becomes 3)

print(f"Final Count Dict: {error_counts}")
# TERMINAL OUTPUT: Final Count Dict: {'500': 3, '404': 2, '200': 1}
```

--------------------------------------------------------------------------------

##### Challenge C: Conditional Filtering and Accumulation Trace
###### Source Code:
```python
def total_positive_prices(prices):
    running_total = 0.0
    processed_count = 0
    
    for p in prices:
        if p <= 0:
            continue  # Skip zero or negative values
        running_total += p
        processed_count += 1
        
    return running_total, processed_count

# Diagnostic Execution Trace with Input [-10.0, 25.0, 0.0, 15.5]:
# Initial State: running_total = 0.0, processed_count = 0
# Item 1: p = -10.0 -> -10.0 <= 0 -> True -> continue (Skipped)
# Item 2: p = 25.0  -> 25.0 <= 0  -> False -> running_total = 0.0 + 25.0 = 25.0; processed_count = 1
# Item 3: p = 0.0   -> 0.0 <= 0   -> True -> continue (Skipped)
# Item 4: p = 15.5  -> 15.5 <= 0  -> False -> running_total = 25.0 + 15.5 = 40.5; processed_count = 2

tot, cnt = total_positive_prices([-10.0, 25.0, 0.0, 15.5])
print(f"Total: {tot}, Count: {cnt}")
# TERMINAL OUTPUT: Total: 40.5, Count: 2
```

--------------------------------------------------------------------------------

##### Challenge D: Nested Helper Dispatch & Summary Aggregation
###### Source Code:
```python
def format_user_greeting(username, age):
    # Step 1: Input validation helper
    if not username or age < 0:
        return "Invalid User"
    
    # Step 2: Conditional status label
    status = "Adult" if age >= 18 else "Minor"
    return f"Welcome, {username} ({status})"

# Trace Case 1: Empty Username
t1 = format_user_greeting("", 25)
# Evaluation: not "" -> True -> Returns "Invalid User"
assert t1 == "Invalid User"

# Trace Case 2: Boundary Age 18
t2 = format_user_greeting("Ron", 18)
# Evaluation: username="Ron" (valid), age=18 >= 0 (valid)
# Status: 18 >= 18 -> "Adult"
# Format: f"Welcome, Ron (Adult)"
assert t2 == "Welcome, Ron (Adult)"

# Trace Case 3: Minor Age 17
t3 = format_user_greeting("Alice", 17)
# Evaluation: age=17 >= 18 -> False -> Status: "Minor"
# Format: f"Welcome, Alice (Minor)"
assert t3 == "Welcome, Alice (Minor)"

print("Diagnostic Suite D Complete!")
# TERMINAL OUTPUT: Diagnostic Suite D Complete!
```

--------------------------------------------------------------------------------

*Reference Document saved as an .md file in my studio ready to be downloaded and exported.*

---
End of Course Master Compendium. Complete syllabus mastery verified.
