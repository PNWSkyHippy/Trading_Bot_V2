# PY101 - Master Reference: Python Programming Foundations & Advanced Concepts

Welcome to the **PY101 Master Reference Document**. This authoritative reference synthesizes all core concepts, mental models, memory mechanics, syntax patterns, defensive programming idioms, and code execution traces from across the Python Practice & Fundamentals modules into a single, publication-grade reference guide.

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

### Formal Definitions

#### Primary Data Types
*   **Integer (`int`)**: An immutable, arbitrary-precision scalar data type representing whole signed numbers (e.g., `-5`, `0`, `42`).
*   **Floating-Point (`float`)**: An immutable, double-precision (64-bit IEEE 754) scalar data type representing real numbers with decimal fractions (e.g., `3.14159`, `-0.001`).
*   **String (`str`)**: An immutable, ordered sequence of Unicode characters encapsulated by matching single (`'`), double (`"`), or triple (`"""`) quotes.
*   **Boolean (`bool`)**: An immutable logical data type evaluated as either `True` or `False`. In Python, `bool` is a structural subclass of `int` where `True == 1` and `False == 0`.
*   **List (`list`)**: A mutable, ordered, dynamic array structure capable of storing heterogeneous object references.
*   **Tuple (`tuple`)**: An immutable, ordered sequence structure capable of storing heterogeneous object references.

#### Core Operations & Keywords
*   **Floating-Point Division (`/`)**: Evaluates numeric division and unconditionally returns a `float` result regardless of operand types (e.g., `10 / 2` yields `5.0`).
*   **Floor Division (`//`)**: Evaluates numeric division and rounds the resulting quotient down to the nearest lower integer (e.g., `10 // 3` yields `3`, `-10 // 3` yields `-4`).
*   **Modulo Operator (`%`)**: Evaluates integer division and returns the remainder $r = a - (b \times (a // b))$ (e.g., `10 % 3` yields `1`).
*   **String Replication (`*`)**: Evaluates a string and an integer operand to yield a newly allocated string repeated $N$ times.
*   **F-String (`f"..."`)**: Literal string interpolation syntax evaluating expressions inside curly braces `{}` at runtime.
*   **Sequence Slicing (`[start:stop:step]`)**: Sub-sequence extraction mechanism where `start` is inclusive, `stop` is exclusive, and `step` determines stride and direction.
*   **Try / Except / Else / Finally**: Exception handling control structure. `try` isolates risky code; `except` catches matching runtime exceptions; `else` executes if no exception occurs; `finally` executes unconditionally for resource cleanup.
*   **Standard Streams (`sys.stdin`, `sys.stdout`)**: Input and output text stream abstractions provided by the operating system interface.

### Core Foundations Comparison Matrix

| Feature / Spec | Numeric Types (`int` / `float`) | Text Sequences (`str`) | Mutable Sequences (`list`) | Exception Blocks (`try/except`) |
| :--- | :--- | :--- | :--- | :--- |
| **Definition** | Scalar quantitative values representing whole numbers or double-precision floating-point values. | Immutable ordered sequences of Unicode characters representing textual data. | Mutable, dynamically-sized ordered collections of arbitrary object references. | Control flow structure used to trap runtime exceptions and prevent fatal script execution crashes. |
| **Syntax / Delimiters** | Unquoted numeric literals (`42`, `3.14159`). | Single (`'`), double (`"`), or triple (`"""`) quotes. | Square brackets (`[item1, item2]`) with comma-separated elements. | `try:` clause followed by indented code, attached to `except ExceptionType:` clauses. |
| **Permitted Operators** | `+`, `-`, `*`, `/`, `//`, `%`, `**`, `==`, `!=`, `<`, `>`, `<=`, `>=` | `+` (concatenation), `*` (replication), `==`, `!=`, `in`, `[i]`, `[a:b:c]` | `+` (concatenation), `*` (replication), `in`, `[i]`, `[a:b:c]`, `.append()`, `.pop()` | Structural control flow keywords (`try`, `except`, `else`, `finally`). |
| **Type Invariant / Mutability** | Immutable (operations yield new numeric instances in memory). | Immutable (modifications allocate a new `str` instance). | Mutable (elements added, updated, or removed in-place without changing object identity). | N/A (Structural control flow construct). |
| **Common Runtime Error** | `ZeroDivisionError` (dividing by zero), `ValueError` (invalid string conversion). | `TypeError` (implicit concatenation with non-str), `IndexError` (index out of bounds). | `IndexError` (accessing non-existent index), `ValueError` (removing missing item). | `NameError` (referencing variables initialized inside failed `try` block). |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Model 1: The Labeled Storage Box & Address Tag (Variable References)
In Python, a variable name is not a physical container holding data. Instead, a variable name is a lightweight **address tag** (reference) bound to a typed object residing in heap memory. Assigning a variable (`x = 42`) attaches the tag `x` to the object `42`. Reassigning `x = "Python"` detaches tag `x` from integer `42` and re-attaches it to string object `"Python"`.

```
[ Namespace / Variable Tags ]                 [ Heap Memory / Typed Objects ]
+---------------------------+                 +-----------------------------+
|  x ---------------------->|---------------->|  int: 42 (id: 0x7f9a10)     |
|                           |                 +-----------------------------+
|  y ---------------------->|---------------->|  str: "Python" (id: 0x7f9a28)|
|                           |                 +-----------------------------+
|  z ---------------------->|---------------->|  list: [1, 2] (id: 0x7f9a40)|
+---------------------------+                 +-----------------------------+
```

### Model 2: The Trapeze Safety Net Architecture (`try / except / else / finally`)
The `try` block represents a high-wire performance containing code that carries a risk of falling (raising an exception). The `except` block acts as a calibrated safety net positioned below to catch specific falls. The `else` block is the performer's bow, executed only if the performance completed with zero falls. The `finally` block represents packing up the circus tent—an operation that MUST occur whether the performer landed smoothly or crashed into the net.

```
+-----------------------------------------------------------+
|                      try: BLOCK                           |
|               (High Wire: Risky Execution)                |
+-----------------------------------------------------------+
          /                                   \
   [ Exception Raised ]                 [ No Exception ]
        /                                       \
+-----------------------+               +-----------------------+
|    except BLOCK:      |               |      else BLOCK:      |
| (Safety Net Deployed) |               | (Victorious Execution)|
+-----------------------+               +-----------------------+
        \                                       /
         \                                     /
+-----------------------------------------------------------+
|                     finally: BLOCK                        |
|         (Mandatory Cleanup - Always Executes)             |
+-----------------------------------------------------------+
```

### Model 3: The Assembly Line Conveyor Belt & Pipe (`stdin` -> Filter -> `stdout`)
Stream processing treats data as a continuous conveyer belt moving through a factory. Standard Input (`sys.stdin`) ingests items line-by-line from upstream sources. The Python script acts as a station on the belt, inspecting and mutating each item. Processed items are placed onto Standard Output (`sys.stdout`) to be consumed by downstream commands or saved to files via shell redirects (`>`).

```
[ Upstream Data Source ] ===(stdout)===> [ Pipe | ] ===(stdin)===> [ Python Filter Script ] ===(stdout)===> [ Terminal / File ]
                                                                          |
                                                                          v
                                                                [ Inspect / Transform ]
```

---

## 3. Idiomatic Python Implementation & State Tracing

### Module A: Console Input/Output & Explicit Type Conversion

```python
# --- STEP 1: Capture Raw Input ---
# Console input prompts user and receives raw string representation
raw_age_str = "28"  # Simulated input: user types 28 -> state: raw_age_str = "28" (str)

# --- STEP 2: Explicit Type Conversion & Validation ---
# Convert string representation to integer for arithmetic processing
age_int = int(raw_age_str)  # State evaluation: int("28") -> age_int = 28 (int)

# --- STEP 3: Arithmetic Computation ---
# Perform integer addition
next_year_age = age_int + 1  # State evaluation: 28 + 1 -> next_year_age = 29 (int)

# --- STEP 4: Interpolated Output via F-String ---
# Format variables into final display string
output_msg = f"Current: {age_int}, Next Year: {next_year_age}"
# State evaluation: f"Current: {28}, Next Year: {29}" -> output_msg = "Current: 28, Next Year: 29"

print(output_msg)
# CONSOLE OUTPUT:
# Current: 28, Next Year: 29
```

### Module B: Precision Arithmetic, Floor Division, and Modulo

```python
total_items = 17  # State: total_items = 17 (int)
batch_size = 5    # State: batch_size = 5 (int)

# --- Floating-point Division ---
exact_ratio = total_items / batch_size
# State evaluation: 17 / 5 -> exact_ratio = 3.4 (float)

# --- Floor Division (Quotient) ---
completed_batches = total_items // batch_size
# State evaluation: 17 // 5 -> completed_batches = 3 (int)

# --- Modulo (Remainder) ---
remaining_items = total_items % batch_size
# State evaluation: 17 % 5 -> remaining_items = 2 (int)

# --- Output Formatting ---
summary = f"Batches: {completed_batches}, Remaining: {remaining_items}, Ratio: {exact_ratio:.2f}"
print(summary)
# CONSOLE OUTPUT:
# Batches: 3, Remaining: 2, Ratio: 3.40
```

### Module C: Sequence Slicing & List Mutation Mechanics

```python
# Initializing mutable list structure
data_series = [10, 20, 30, 40, 50, 60]  # State: data_series len=6

# --- Slicing [start:stop:step] ---
# Extract elements from index 1 up to (but excluding) index 4
sub_series = data_series[1:4:1]
# Intermediate evaluation: indices 1, 2, 3 -> [20, 30, 40]
# State: sub_series = [20, 30, 40]

# --- Reverse Slicing ---
reversed_series = data_series[::-1]
# Intermediate evaluation: step -1 traverses right-to-left
# State: reversed_series = [60, 50, 40, 30, 20, 10]

# --- In-Place List Mutation ---
data_series.append(70)  # Mutates data_series -> [10, 20, 30, 40, 50, 60, 70]
popped_val = data_series.pop(0)  # Removes index 0 -> popped_val = 10, list = [20, 30, 40, 50, 60, 70]

print(f"Sub: {sub_series} | Popped: {popped_val} | Current: {data_series}")
# CONSOLE OUTPUT:
# Sub: [20, 30, 40] | Popped: 10 | Current: [20, 30, 40, 50, 60, 70]
```

### Module D: Modular Function with Input Validation Trap

```python
def calculate_unit_price(total_cost_str: str, quantity_str: str) -> float:
    """Safely converts inputs and calculates unit price with error trapping."""
    try:
        # Attempt conversion of raw inputs
        cost = float(total_cost_str)  # Step 1: float("100.0") -> 100.0
        qty = int(quantity_str)       # Step 2: int("4") -> 4
        
        # Calculate ratio
        unit_price = cost / qty       # Step 3: 100.0 / 4 -> 25.0
    except ValueError:
        # Handles non-numeric string inputs
        print("Error: Non-numeric input encountered.")
        return -1.0
    except ZeroDivisionError:
        # Handles division by zero
        print("Error: Quantity cannot be zero.")
        return -1.0
    else:
        # Executes only if try block succeeded completely
        return unit_price
    finally:
        # Mandatory execution trace
        pass

# Test Execution Path 1: Valid Inputs
result_valid = calculate_unit_price("100.0", "4")
print(f"Valid Test Result: {result_valid:.2f}")
# CONSOLE OUTPUT:
# Valid Test Result: 25.00

# Test Execution Path 2: Invalid Quantity Trap
result_invalid = calculate_unit_price("100.0", "0")
print(f"Invalid Test Result: {result_invalid:.2f}")
# CONSOLE OUTPUT:
# Error: Quantity cannot be zero.
# Invalid Test Result: -1.00
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Implied String-Integer Concatenation (`TypeError`)
Attempting to concatenate a string literal with a numeric variable directly using the `+` operator.

```python
# INCORRECT:
age = 25
# Raises TypeError: can only concatenate str (not "int") to str
# message = "User age is: " + age

# CORRECT:
age = 25
# Idiomatic solution 1: Explicit conversion
message_converted = "User age is: " + str(age)
# Idiomatic solution 2: F-String interpolation (preferred)
message_fstring = f"User age is: {age}"
```

### Trap 2: Unsafe Input Conversion (`ValueError`)
Directly converting raw user input without wrapping the conversion in error validation.

```python
# INCORRECT:
# If user enters "abc", script terminates immediately with ValueError
# user_number = int("abc")

# CORRECT:
raw_input_val = "abc"
try:
    user_number = int(raw_input_val)
except ValueError:
    # Graceful fallback assignment preventing script failure
    user_number = 0
    print(f"Warning: Invalid integer input '{raw_input_val}'. Defaulted to 0.")
```

### Trap 3: The Uninitialized Variable Trap (`NameError`)
Declaring a variable exclusively inside a `try` block and attempting to reference it outside after an exception was caught.

```python
# INCORRECT:
raw_data = "invalid_number"
try:
    parsed_val = int(raw_data)  # Fails with ValueError
except ValueError:
    print("Failed to parse integer.")

# Raises NameError: name 'parsed_val' is not defined because assignment was skipped
# print(f"Parsed Value: {parsed_val}")

# CORRECT:
raw_data = "invalid_number"
parsed_val = None  # Pre-initialize variable in outer scope

try:
    parsed_val = int(raw_data)
except ValueError:
    parsed_val = 0  # Provide safe fallback value in except block

print(f"Parsed Value safely resolved to: {parsed_val}")
```

### Trap 4: Index Out of Bounds (`IndexError`)
Attempting to access a sequence index that exceeds $len - 1$.

```python
# INCORRECT:
items = ["apple", "banana"]
# Raises IndexError: list index out of range
# element = items[2]

# CORRECT:
items = ["apple", "banana"]
target_index = 2

if target_index < len(items):
    element = items[target_index]
else:
    element = "default_value"
    print(f"Index {target_index} out of bounds for list length {len(items)}. Used default.")
```

---

## 5. Python Memory Mechanics, References & Scope

### Memory Architecture & Dynamic Typing
In Python, variables do not possess inherent types; **objects possess types**. A variable is simply a name bound to an object in heap memory. When a variable is reassigned, Python changes the binding of the variable reference, decrementing the reference count of the old object and incrementing that of the new object.

*   **Immutable Objects (`int`, `float`, `str`, `tuple`, `bool`)**: Once allocated in heap memory, their internal values cannot be changed. Any mutating operation allocates a brand new object at a new memory location.
*   **Mutable Objects (`list`, `dict`, `set`)**: Their contents can be altered in-place without altering the memory address (`id()`) of the parent object container.

```
[ Namespace Scope (Local/Global) ]           [ Heap Memory Allocations ]
+--------------------------------+           +----------------------------------+
| name_var --------------------->|---------->| str: "Alice" (id: 0x1004a)       |
| count_var -------------------->|---------->| int: 10      (id: 0x10020)       |
|                                |           |                                  |
| list_ref_a ------------------->|---+------>| list: [1, 2, 3] (id: 0x20080)   |
|                                |   |       | (Shared heap allocation)         |
| list_ref_b ------------------->|---+       +----------------------------------+
+--------------------------------+
```

### LEGB Scope Resolution Rule
When a variable name is referenced in code, Python searches four concentric namespace scopes in exact order until a match is found:

1.  **L (Local)**: Names defined within the current function execution block.
2.  **E (Enclosing)**: Names defined in nested outer function enclosing scopes.
3.  **G (Global)**: Names defined at the top-level of the module/file script.
4.  **B (Built-in)**: Pre-loaded Python module keywords and functions (e.g., `len`, `int`, `print`).

If the name is not found across all four scopes, Python raises a `NameError`.

---

## 6. Practical Integration / Mini Case Study

### Interactive Batch Processing Script
The following complete script integrates input validation, error handling, list manipulation, precision arithmetic, and formatted execution traces into a production-grade utility.

```python
import sys

def process_transaction_batch(raw_entries: list) -> dict:
    """Processes raw transaction string inputs, enforces data validation,
    calculates summary metrics, and handles exceptions cleanly."""
    valid_amounts = []
    error_count = 0
    
    print("--- Starting Transaction Batch Processing ---")
    
    for idx, raw_val in enumerate(raw_entries):
        try:
            # Step 1: Strip whitespaces and parse float
            clean_str = raw_val.strip()
            amount = float(clean_str)
            
            # Step 2: Enforce business domain validation rule
            if amount <= 0:
                raise ValueError(f"Non-positive transaction amount: {amount}")
                
        except ValueError as err:
            # Traps invalid string conversions and non-positive values
            error_count += 1
            print(f"[ENTRY {idx+1} REJECTED] Input: '{raw_val}' | Reason: {err}")
        else:
            # Runs only when entry passes validation
            valid_amounts.append(amount)
            print(f"[ENTRY {idx+1} ACCEPTED] Value: ${amount:.2f}")
        finally:
            # Execution progress log
            pass

    # Metric Calculations
    total_volume = sum(valid_amounts)
    processed_count = len(valid_amounts)
    
    # Calculate average safely to prevent ZeroDivisionError
    if processed_count > 0:
        average_transaction = total_volume / processed_count
    else:
        average_transaction = 0.0

    summary_report = {
        "processed_count": processed_count,
        "error_count": error_count,
        "total_volume": total_volume,
        "average_transaction": average_transaction
    }
    
    return summary_report

# --- SIMULATED EXECUTION RUN ---
if __name__ == "__main__":
    sample_batch = [" 45.50 ", "invalid_number", "-12.00", "100.00", "0.00", "254.25"]
    
    report = process_transaction_batch(sample_batch)
    
    print("\n================ BATCH SUMMARY REPORT ================")
    print(f"Successfully Processed : {report['processed_count']} entries")
    print(f"Rejected / Errors      : {report['error_count']} entries")
    print(f"Total Volume          : ${report['total_volume']:.2f}")
    print(f"Average Transaction   : ${report['average_transaction']:.2f}")
    print("======================================================")
```

### Complete Console Output Trace

```text
--- Starting Transaction Batch Processing ---
[ENTRY 1 ACCEPTED] Value: $45.50
[ENTRY 2 REJECTED] Input: 'invalid_number' | Reason: could not convert string to float: 'invalid_number'
[ENTRY 3 REJECTED] Input: '-12.00' | Reason: Non-positive transaction amount: -12.0
[ENTRY 4 ACCEPTED] Value: $100.00
[ENTRY 5 REJECTED] Input: '0.00' | Reason: Non-positive transaction amount: 0.0
[ENTRY 6 ACCEPTED] Value: $254.25

================ BATCH SUMMARY REPORT ================
Successfully Processed : 3 entries
Rejected / Errors      : 3 entries
Total Volume          : $399.75
Average Transaction   : $133.25
======================================================
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Diagnostic Challenge A: Complex Arithmetic & Modulo Logic

```python
# CODE SNIPPET:
a = 14
b = 4
res_1 = a // b
res_2 = a % b
res_3 = a / b
calc = (res_1 * b) + res_2

print(f"r1: {res_1}, r2: {res_2}, r3: {res_3}, calc: {calc}")

# STEP-BY-STEP TRACE:
# Line 1: a = 14 (int)
# Line 2: b = 4 (int)
# Line 3: res_1 = 14 // 4 -> Floor division quotient -> res_1 = 3 (int)
# Line 4: res_2 = 14 % 4  -> Integer modulo remainder -> res_2 = 2 (int)
# Line 5: res_3 = 14 / 4  -> Floating-point division -> res_3 = 3.5 (float)
# Line 6: calc = (3 * 4) + 2 -> 12 + 2 -> calc = 14 (int)

# FINAL TERMINAL OUTPUT:
# r1: 3, r2: 2, r3: 3.5, calc: 14
```

### Diagnostic Challenge B: String Slicing & Replication Mechanics

```python
# CODE SNIPPET:
raw_text = "Py101Engine"
part_a = raw_text[:5]
part_b = raw_text[-6:]
symbol_str = "!" * 3
combined = (part_a.upper() + "_" + part_b) + symbol_str

print(f"Result: {combined}")

# STEP-BY-STEP TRACE:
# Line 1: raw_text = "Py101Engine" (len=11)
# Line 2: part_a = raw_text[:5] -> Index 0 to 4 -> part_a = "Py101"
# Line 3: part_b = raw_text[-6:] -> Last 6 characters -> part_b = "Engine"
# Line 4: symbol_str = "!" * 3 -> String replication -> symbol_str = "!!!"
# Line 5: part_a.upper() -> "PY101"
# Line 6: "PY101" + "_" + "Engine" -> "PY101_Engine"
# Line 7: "PY101_Engine" + "!!!" -> combined = "PY101_Engine!!!"

# FINAL TERMINAL OUTPUT:
# Result: PY101_Engine!!!
```

### Diagnostic Challenge C: List Mutation & In-Place Operations

```python
# CODE SNIPPET:
stack = [10, 20, 30]
stack.append(40)
popped_first = stack.pop(0)
stack.insert(1, 25)
final_len = len(stack)

print(f"Popped: {popped_first}, Stack: {stack}, Len: {final_len}")

# STEP-BY-STEP TRACE:
# Line 1: stack initialized -> [10, 20, 30]
# Line 2: stack.append(40) -> stack becomes [10, 20, 30, 40]
# Line 3: stack.pop(0) -> Removes item at index 0 (10) -> popped_first = 10
#         stack becomes [20, 30, 40]
# Line 4: stack.insert(1, 25) -> Inserts 25 at index 1
#         stack becomes [20, 25, 30, 40]
# Line 5: final_len = len([20, 25, 30, 40]) -> final_len = 4

# FINAL TERMINAL OUTPUT:
# Popped: 10, Stack: [20, 25, 30, 40], Len: 4
```

### Diagnostic Challenge D: Exception Flow with Uninitialized State Fallback

```python
# CODE SNIPPET:
entries = ["100", "twenty", "300"]
total_sum = 0
converted_count = 0

for item in entries:
    try:
        val = int(item)
    except ValueError:
        val = 0
        print(f"Conversion failed for '{item}'")
    else:
        converted_count += 1
    finally:
        total_sum += val

print(f"Total: {total_sum}, Converted: {converted_count}")

# STEP-BY-STEP TRACE:
# Iteration 1: item = "100"
#   try: val = int("100") -> val = 100
#   except: Skipped
#   else: converted_count increments to 1
#   finally: total_sum += 100 -> total_sum = 100

# Iteration 2: item = "twenty"
#   try: int("twenty") raises ValueError
#   except: Trapped! val set to 0. Prints "Conversion failed for 'twenty'"
#   else: Skipped
#   finally: total_sum += 0 -> total_sum = 100

# Iteration 3: item = "300"
#   try: val = int("300") -> val = 300
#   except: Skipped
#   else: converted_count increments to 2
#   finally: total_sum += 300 -> total_sum = 400

# FINAL TERMINAL OUTPUT:
# Conversion failed for 'twenty'
# Total: 400, Converted: 2
```

---
*PY101 Master Reference Document — Grounded in Python Fundamentals & Practice Session Curricula.*
