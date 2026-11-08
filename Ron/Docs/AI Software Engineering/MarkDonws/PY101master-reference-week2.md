# CS101 - Week 2 Master Reference: Python Fundamentals: Division Modes, Functions, Scope, and Data Types

*Welcome blurb: This document synthesizes all core concepts, mental models, memory mechanics, state tracing, and defensive programming patterns from Module/Week 2 into an authoritative, publication-grade reference guide.*

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

### Primary Data Types & Type System
Python is a dynamically typed language where variables act as references to strongly typed objects in memory. The three primary scalar data types introduced in this module are:

*   **Integer (`int`):** Represents unbounded positive or negative whole numbers (e.g., `-5`, `0`, `42`). Integer arithmetic produces exact discrete values except when using true division.
*   **Floating-Point (`float`):** Represents double-precision 64-bit IEEE 754 decimal numbers (e.g., `3.14159`, `0.0`, `-2.5`). Floating-point arithmetic is subject to standard binary representation limits.
*   **String (`str`):** An immutable sequence of Unicode characters enclosed in single (`'...'`) or double (`"..."`) quotes. Used for textual data and user prompts.

### Division & Modulo Operator Ecosystem
Python provides three specialized operators for division-based arithmetic:

1.  **True Division (`/`):** Computes the exact mathematical quotient of two numbers. It **always** evaluates to a `float`, even if the numerator is evenly divisible by the denominator (e.g., `10 / 2` evaluates to `5.0`).
2.  **Floor Division (`//`):** Computes the mathematical quotient and applies the floor function ($\lfloor x \rfloor$), truncating the fractional part towards negative infinity. When both operands are integers, it returns an `int` representing the total number of complete groups.
3.  **Modulo Operator (`%`):** Computes the remainder after integer floor division, satisfying the fundamental identity:
    $$\text{dividend} = (\text{divisor} \times (\text{dividend} // \text{divisor})) + (\text{dividend} \% \text{divisor})$$
    The result of `a % b` represents the "leftover" quantity after extracting all complete groups of size `b`.

### Modulo Applications: Parity and Cyclic Position Mapping
*   **Parity Determination (`x % 2`):** Evaluating a whole number modulo 2 yields `0` for even numbers and `1` for odd numbers. This is the canonical test for numerical parity.
*   **Cyclic Position Mapping (`x % N`):** For any positive integer $N$, evaluating `x % N` maps any non-negative integer $x$ into a bounded range $[0, N - 1]$. As $x$ increases linearly, the expression output cycles continuously: $0, 1, 2, \dots, N-1, 0, 1, \dots$.

### Function Architecture, Parameters, and Execution Control
*   **Function Definition (`def`):** Binds a function name to a block of executable code.
*   **Parameters vs. Arguments:** Parameters are variable names declared in the function header that serve as local placeholders. Arguments are the concrete values or object references passed into the function upon invocation.
*   **`print()` vs. `return`:** `print()` is an I/O side effect that writes textual representation to standard output (returning `None`). `return` explicitly exits the function, passing an evaluated object back to the caller's evaluation context.
*   **Guard Clauses (Early Returns):** Conditional checks placed at the beginning of a function body that evaluate edge cases and immediately return control, avoiding nested logic blocks.

---

### Side-by-Side Comparison Matrices

#### Matrix 1: Python Division Operators Comparison
| Feature / Spec | True Division (`/`) | Floor Division (`//`) | Modulo Operator (`%`) |
| :--- | :--- | :--- | :--- |
| **Mathematical Definition** | Exact ratio $\frac{a}{b}$ | Floor quotient $\lfloor \frac{a}{b} \rfloor$ | Remainder $a - b \lfloor \frac{a}{b} \rfloor$ |
| **Syntax / Symbol** | `/` | `//` | `%` |
| **Primary Return Type** | Always `float` | `int` (if both operands are `int`) | `int` (if both operands are `int`) |
| **Semantic Meaning** | Continuous proportion | Count of full/complete groups | Quantity remaining after grouping |
| **Common Runtime Error** | `ZeroDivisionError` (if divisor is `0`) | `ZeroDivisionError` (if divisor is `0`) | `ZeroDivisionError` (if divisor is `0`) |

#### Matrix 2: Function Output Mechanics (`return` vs. `print`)
| Feature / Spec | `return` Statement | `print()` Function |
| :--- | :--- | :--- |
| **Primary Purpose** | Pass evaluated data back to caller | Write text to stdout console |
| **Program Flow Effect** | Immediately terminates function execution | Execution continues to next statement |
| **Evaluated Result** | Specified expression (or `None` if bare) | Always returns `None` |
| **Data Reusability** | Fully reusable in expressions/variables | Non-reusable (side-effect only) |
| **Typical Context** | Computation, transformations, logic | Debugging, user messaging, logs |

#### Matrix 3: Scalar Data Types & Type Conversion
| Feature / Spec | Integer (`int`) | Floating-Point (`float`) | String (`str`) |
| :--- | :--- | :--- | :--- |
| **Delimiters / Form** | Digits without decimal (e.g. `42`) | Digits with decimal (e.g. `42.0`) | Quotes (e.g. `'42'`, `"42"`) |
| **Mutability** | Immutable | Immutable | Immutable |
| **Casting Function** | `int()` | `float()` | `str()` |
| **Primary Error Type** | `ValueError` (invalid string conversion) | `ValueError` (invalid string conversion) | `TypeError` (implicit concatenation) |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: The Cookie Factory (Floor Division and Modulo as a Team)
Imagine a cookie packaging facility. You have a batch of baked cookies (the Dividend) and standard shipping boxes that hold a fixed capacity (the Divisor).

*   **Floor Division (`//`):** Represents the packing machine counting **how many full boxes** can be sealed and shipped.
*   **Modulo (`%`):** Represents the inspector counting the **loose cookies left on the tray** that cannot fill a complete box.
*   **True Division (`/`):** Represents a theoretical blender that purees all cookies and boxes into a fractional float quantity.

```
+-----------------------------------------------------------------------+
| COOKIE FACTORY DIVISION MODEL: 36 Cookies, Box Capacity = 8          |
+-----------------------------------------------------------------------+
|                                                                       |
|  [ Box 1: 8 ]   [ Box 2: 8 ]   [ Box 3: 8 ]   [ Box 4: 8 ]   [Tray]  |
|  ( 8 cookies)   ( 8 cookies)   ( 8 cookies)   ( 8 cookies)  (4 left) |
|                                                                       |
|  36 // 8  ==>  4 FULL BOXES (Floor Quotient)                          |
|  36 % 8   ==>  4 LOOSE COOKIES (Modulo Remainder)                     |
|  36 / 8   ==>  4.5 THEORETICAL BOXES (True Float Division)            |
+-----------------------------------------------------------------------+
```

### Analogy 2: The Factory Conveyor vs. The Public Billboard (`return` vs `print`)
To understand function execution:

*   **`return` (The Conveyor Belt):** An assembly worker places a finished component onto a conveyor belt. The component is sent directly inside the machine for the next worker (a variable or calling expression) to build upon.
*   **`print()` (The Public Billboard):** The worker flashes a sign on the factory wall announcing *"Component Completed!"*. People looking through the window see the text, but no physical part is fed back into the machinery.

```
+-----------------------------------------------------------------------+
| FUNCTION DATA FLOW: return vs print()                                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  FUNCTION CALL: compute_cost(10, 2)                                   |
|       |                                                               |
|       +---> print("Cost is 20") --------> [ Console Display ]         |
|       |                                   (Data lost to program)      |
|       |                                                               |
|       +---> return 20 -------------------> [ Calling Context ]        |
|                                           total_price = 20            |
|                                           (Data stored in memory)     |
+-----------------------------------------------------------------------+
```

### Analogy 3: The Private Workspace vs. The Corporate Bulletin Board (Scope & Shadowing)
Variable namespaces resemble organizational information access:

*   **Global Scope (Corporate Bulletin Board):** Information posted in the hallway. Anyone inside any room can read it.
*   **Local Scope (Private Conference Room):** Notes written on a whiteboard inside a specific conference room. When the room is unlocked (function call), workers enter, write on the board, and read local notes. When the meeting ends, the room is wiped completely clean.
*   **Variable Shadowing:** If a local whiteboard has the label `tax_rate = 0.05` written on it, workers inside the room will use `0.05` instead of the global `tax_rate = 0.10` posted out in the hallway. The hallway board remains entirely untouched.

---

## 3. Idiomatic Python Implementation & State Tracing

### Module 3.1: Console Input, Dynamic Type Casting, and Inspection

```python
# Step 1: Prompt user for raw textual input (input always returns str)
raw_quantity = input("Enter number of items: ")  # State: raw_quantity = "5" (type: str)

# Step 2: Inspect raw type before transformation
raw_type = type(raw_quantity)  # State: raw_type = <class 'str'>

# Step 3: Explicitly cast string to integer for mathematical operations
item_count = int(raw_quantity)  # State: item_count = 5 (type: int)

# Step 4: Prompt and cast float input for unit price
unit_price = float(input("Enter unit price: "))  # Input: "12.50" -> State: unit_price = 12.5 (type: float)

# Step 5: Compute raw total cost
subtotal = item_count * unit_price  # State: subtotal = 5 * 12.5 = 62.5 (type: float)

# Step 6: Console Output via f-string formatting
print(f"Subtotal for {item_count} items: ${subtotal:.2f}")
# Output: Subtotal for 5 items: $62.50
```

### Module 3.2: Division Operators, Parity Check, and Cyclic Mapping

```python
# --- Division Ecosystem ---
total_students = 29  # State: total_students = 29
group_size = 4       # State: group_size = 4

# True Division
exact_groups = total_students / group_size  # State: exact_groups = 7.25 (type: float)

# Floor Division (Full Groups)
full_groups = total_students // group_size  # State: full_groups = 7 (type: int)

# Modulo (Leftover Students)
leftover_students = total_students % group_size  # State: leftover_students = 1 (type: int)

# --- Parity Evaluation ---
number_to_check = 11  # State: number_to_check = 11
parity_remainder = number_to_check % 2  # State: parity_remainder = 1
is_even = (parity_remainder == 0)  # State: is_even = False

# --- Cyclic Mapping (7-Day Week Cycle: 0=Sun, 1=Mon, ..., 6=Sat) ---
current_day = 0  # Sunday
days_elapsed = 15  # Advance 15 days
future_day = (current_day + days_elapsed) % 7  # State: 15 % 7 = 1 (Monday)

print(f"Full rows: {full_groups}, Remaining: {leftover_students}")
# Output: Full rows: 7, Remaining: 1
print(f"Is {number_to_check} even? {is_even}")
# Output: Is 11 even? False
print(f"Day in 15 days: {future_day}")
# Output: Day in 15 days: 1
```

### Module 3.3: Currency Display vs. Value Rounding

```python
raw_price = 7.5  # State: raw_price = 7.5

# Approach A: f-string formatting (Modifies visual output only)
formatted_display = f"${raw_price:.2f}"  # State: formatted_display = "$7.50" (type: str)
# raw_price remains float 7.5 in memory

# Approach B: round() function (Modifies numerical value in memory)
calculated_value = 5.55555  # State: calculated_value = 5.55555
rounded_memory_value = round(calculated_value, 2)  # State: rounded_memory_value = 5.56 (type: float)

print(f"Display: {formatted_display}, Rounded Value: {rounded_memory_value}")
# Output: Display: $7.50, Rounded Value: 5.56
```

### Module 3.4: Function Definition, Multi-Parameters, and Guard Clauses

```python
def calculate_box_allocation(total_items, box_capacity):
    # Guard Clause 1: Validate positive integer inputs
    if box_capacity <= 0:
        print("Error: Box capacity must be greater than zero.")
        return None  # Early termination on invalid input
    
    # Guard Clause 2: Check for empty inventory
    if total_items <= 0:
        return 0, 0  # Early return of zero boxes, zero remainder
    
    # Core Logic
    boxes_needed = total_items // box_capacity  # State calculation
    items_leftover = total_items % box_capacity # State calculation
    
    return boxes_needed, items_leftover  # Return tuple of evaluated results

# Execution Call 1: Normal Execution
boxes, leftovers = calculate_box_allocation(50, 9)
# State: boxes = 5, leftovers = 5
print(f"Boxes: {boxes}, Leftovers: {leftovers}")
# Output: Boxes: 5, Leftovers: 5

# Execution Call 2: Triggering Guard Clause
result = calculate_box_allocation(50, 0)
# Output: Error: Box capacity must be greater than zero.
# State: result = None
```

---

## 4. Defensive Programming & Common Traps

This section lists common runtime exceptions, detailing the underlying bug and the idiomatically correct fix.

### Trap 1: Implicit String-to-Numeric Concatenation (`TypeError`)
Occurs when attempting to combine strings and numeric values using the `+` operator.

```python
# INCORRECT: Implicit concatenation of str and float
item_price = 19.99
# Raises TypeError: can only concatenate str (not "float") to str
# print("Total price is: " + item_price)

# CORRECT 1: Explicit type conversion using str()
print("Total price is: " + str(item_price))
# Console Output: Total price is: 19.99

# CORRECT 2: Idiomatic String Formatting via f-string
print(f"Total price is: ${item_price:.2f}")
# Console Output: Total price is: $19.99
```

### Trap 2: Uncasted User Input Arithmetic (`TypeError`)
Occurs when attempting mathematical operations directly on the return value of `input()`.

```python
# INCORRECT: input() returns str, cannot add int
# user_age = input("Enter age: ") # User inputs "25"
# next_year = user_age + 1
# Raises TypeError: can only concatenate str (not "int") to str

# CORRECT: Cast input to int before arithmetic
user_age = int(input("Enter age: "))  # User inputs "25" -> State: user_age = 25
next_year = user_age + 1              # State: next_year = 26
print(f"Next year age: {next_year}")
```

### Trap 3: Division by Zero (`ZeroDivisionError`)
Occurs when `/`, `//`, or `%` is evaluated with a denominator equal to zero.

```python
# INCORRECT: Unchecked division by zero
# divisor = 0
# result = 100 / divisor
# Raises ZeroDivisionError: division by zero

# CORRECT: Defensive check / Guard Clause
divisor = 0
if divisor != 0:
    result = 100 / divisor
else:
    result = 0.0
    print("Warning: Division by zero avoided.")
```

### Trap 4: Void Function Assignment Trap (`TypeError` / Value Error)
Occurs when assigning the output of a function that uses `print()` instead of `return`.

```python
# INCORRECT: Function prints value but does not return it
def compute_tax_bad(amount):
    print(amount * 0.05) # Returns None implicitly!

tax = compute_tax_bad(100) # Console Output: 5.0 | State: tax = None
# total = 100 + tax        # Raises TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'

# CORRECT: Function returns calculated value
def compute_tax_good(amount):
    return amount * 0.05

tax = compute_tax_good(100) # State: tax = 5.0
total = 100 + tax           # State: total = 105.0
print(f"Total: ${total:.2f}")
```

### Trap 5: Unbound Local / Scope Confusion (`UnboundLocalError` / `NameError`)
Occurs when attempting to access a local variable outside its function scope.

```python
# INCORRECT: Accessing local variable in global scope
def process_data():
    local_result = 42
    return local_result

process_data()
# print(local_result)
# Raises NameError: name 'local_result' is not defined

# CORRECT: Capture return value in a global variable
def process_data_fixed():
    local_result = 42
    return local_result

global_result = process_data_fixed()
print(f"Result: {global_result}")
```

---

## 5. Python Memory Mechanics, References & Scope

### Dynamic Binding & Variable References
In Python, variables do **not** hold direct values or reserve memory locations of fixed types. Instead, variables are **named references (pointers)** stored in a namespace, pointing to strongly typed objects allocated in heap memory.

When you execute:
```python
x = 25      # 'x' references an int object with value 25
x = "25"    # 'x' is re-bound to point to a str object with value "25"
```
The variable name `x` is dynamically rebound from an integer object to a string object. The original `int` object `25` is unreferenced and becomes eligible for garbage collection.

### Memory & Namespace Architecture Diagram

```
+-----------------------------------------------------------------------+
| NAMESPACES (Stack / Frame)           HEAP MEMORY (Objects)            |
+-----------------------------------------------------------------------+
|                                                                       |
|  GLOBAL NAMESPACE                                                     |
|  +-----------------------+           +-----------------------------+  |
|  | base_price -----------|---------->| float object: 100.0         |  |
|  | tax_rate -------------|----+      +-----------------------------+  |
|  +-----------------------+    |                                       |
|                               |      +-----------------------------+  |
|                               +----->| float object: 0.10          |  |
|                                      +-----------------------------+  |
|  FUNCTION LOCAL FRAME (during call)                 ^                 |
|  +-----------------------+                          |                 |
|  | rate (shadows global) |--------------------------+                 |
|  | item_count -----------|---------->+-----------------------------+  |
|  | subtotal -------------|---------->| int object: 5               |  |
|  +-----------------------+           +-----------------------------+  |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Namespace Resolution Rules (LEGB Rule)
When Python encounters a variable name, it searches namespaces in a strict hierarchy:
1.  **L (Local):** Names defined inside the currently executing function.
2.  **E (Enclosing):** Names in enclosing/nested functions (if any).
3.  **G (Global):** Names declared at the top level of the module file.
4.  **B (Built-in):** Pre-loaded Python names (e.g., `len`, `int`, `print`).

### Variable Shadowing Mechanics
When a local variable inside a function shares the exact same identifier as a global variable, the local name **shadows** the global name inside that function frame. All reads and writes to that variable name inside the function resolve strictly to the local object. The global variable remains completely unaffected in global space.

---

## 6. Practical Integration / Mini Case Study

### Comprehensive Program: Event Catering & Budget Allocation System
This script integrates all core concepts from Week 2: console input parsing, type casting, floor division, modulo cyclic mapping, financial formatting, functions with guard clauses, and variable scope isolation.

```python
# Global Configurations
TAX_RATE = 0.07  # Global constant for sales tax (7%)

def calculate_event_logistics(attendees, table_capacity):
    # Guard Clause: Invalid table capacity
    if table_capacity <= 0:
        print("[LOGISTICS ERROR] Table capacity must be greater than zero.")
        return None, None
    
    # Guard Clause: Zero attendees
    if attendees <= 0:
        return 0, 0
    
    # Compute full tables and overflow attendees using teamwork of // and %
    full_tables = attendees // table_capacity
    overflow_seats = attendees % table_capacity
    
    return full_tables, overflow_seats


def calculate_catering_budget(num_meals, meal_price):
    # Guard Clause: Invalid meal count or price
    if num_meals < 0 or meal_price < 0.0:
        return 0.0
    
    # Local computations
    subtotal = num_meals * meal_price
    tax_amount = subtotal * TAX_RATE  # Accesses global TAX_RATE
    total_cost = subtotal + tax_amount
    
    return total_cost


def determine_setup_day(days_from_today):
    # 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    today_index = 2  # Assume today is Tuesday (Index 2)
    target_day_index = (today_index + days_from_today) % 7
    return target_day_index


def main():
    print("=== EVENT CATERING & LOGISTICS PLANNING SYSTEM ===")
    
    # 1. User Input and Dynamic Casting
    raw_attendees = input("Enter total expected attendees: ")
    attendee_count = int(raw_attendees)
    
    table_size = int(input("Enter seats per table: "))
    meal_cost = float(input("Enter price per catering meal: "))
    days_until_event = int(input("Enter days until event setup: "))
    
    # 2. Execute Logistics Computation
    tables, leftovers = calculate_event_logistics(attendee_count, table_size)
    
    # 3. Execute Financial Computation
    total_budget = calculate_catering_budget(attendee_count, meal_cost)
    
    # 4. Execute Cyclic Mapping Computation
    setup_day_code = determine_setup_day(days_until_event)
    
    # 5. Formatted Execution Report Output
    print("\n--------------------------------------------------")
    print("             EVENT EXECUTION SUMMARY              ")
    print("--------------------------------------------------")
    print(f"Total Attendees      : {attendee_count}")
    print(f"Full Tables Required : {tables} tables")
    print(f"Overflow Attendees   : {leftovers} person(s)")
    print(f"Setup Day Code (0-6) : {setup_day_code} (0=Sun, 1=Mon, ..., 6=Sat)")
    print(f"Total Budget (w/ Tax): ${total_budget:.2f}")
    print("--------------------------------------------------")

# Execute Main Program Workflow
if __name__ == "__main__":
    main()
```

### Execution State Trace & Terminal Output Simulation

#### Input Data Provided:
*   `raw_attendees` = `"38"` -> `attendee_count` = `38`
*   `table_size` = `"8"`
*   `meal_cost` = `"15.50"`
*   `days_until_event` = `"10"`

#### Step-by-Step Execution Trace:
1.  `calculate_event_logistics(38, 8)`:
    *   `38 // 8` evaluates to `4` (Full Tables).
    *   `38 % 8` evaluates to `6` (Overflow Attendees).
    *   Returns tuple `(4, 6)`.
2.  `calculate_catering_budget(38, 15.50)`:
    *   `subtotal` = 38 * 15.50 = 589.0.
    *   `tax_amount` = 589.0 * 0.07 = 41.23.
    *   `total_cost` = 589.0 + 41.23 = 630.23.
    *   Returns float `630.23`.
3.  `determine_setup_day(10)`:
    *   Today = `2` (Tuesday).
    *   `(2 + 10) % 7` = `12 % 7` = `5` (Friday).
    *   Returns int `5`.

#### Simulated Terminal Output:
```text
=== EVENT CATERING & LOGISTICS PLANNING SYSTEM ===
Enter total expected attendees: 38
Enter seats per table: 8
Enter price per catering meal: 15.50
Enter days until event setup: 10

--------------------------------------------------
             EVENT EXECUTION SUMMARY              
--------------------------------------------------
Total Attendees      : 38
Full Tables Required : 4 tables
Overflow Attendees   : 6 person(s)
Setup Day Code (0-6) : 5 (0=Sun, 1=Mon, ..., 6=Sat)
Total Budget (w/ Tax): $630.23
--------------------------------------------------
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Mixed Division Modes & Order of Operations

```python
a = 17
b = 4
c = 2

res1 = a / b + a // b
res2 = a % b * c + a // (b + c)
```

#### Line-by-Line Execution Trace:
1.  `a = 17`, `b = 4`, `c = 2`
2.  `res1 = 17 / 4 + 17 // 4`:
    *   `17 / 4` evaluates to float `4.25`.
    *   `17 // 4` evaluates to int `4`.
    *   `4.25 + 4` evaluates to float `8.25`.
    *   State: `res1 = 8.25`
3.  `res2 = 17 % 4 * 2 + 17 // (4 + 2)`:
    *   `17 % 4` evaluates to int `1`.
    *   `1 * 2` evaluates to int `2`.
    *   `4 + 2` evaluates to int `6`.
    *   `17 // 6` evaluates to int `2`.
    *   `2 + 2` evaluates to int `4`.
    *   State: `res2 = 4`

#### Terminal Output:
```text
res1 = 8.25
res2 = 4
```

---

### Challenge B: Modulo Cycles, Parity & State Mutations

```python
counter = 14
step = 5

parity_check = counter % 2
cycle_pos1 = counter % step

counter = counter + 3
cycle_pos2 = counter % step
```

#### Line-by-Line Execution Trace:
1.  `counter = 14`, `step = 5`
2.  `parity_check = 14 % 2` -> `14` is even, so `parity_check = 0`.
3.  `cycle_pos1 = 14 % 5` -> 14 = (5 * 2) + 4, so `cycle_pos1 = 4`.
4.  `counter = 14 + 3` -> `counter` mutated to `17`.
5.  `cycle_pos2 = 17 % 5` -> 17 = (5 * 3) + 2, so `cycle_pos2 = 2`.

#### State Table:
| Variable Name | Intermediate Value | Final Type |
| :--- | :--- | :--- |
| `counter` | `17` | `int` |
| `step` | `5` | `int` |
| `parity_check` | `0` | `int` |
| `cycle_pos1` | `4` | `int` |
| `cycle_pos2` | `2` | `int` |

#### Terminal Output:
```text
parity_check = 0
cycle_pos1 = 4
cycle_pos2 = 2
```

---

### Challenge C: Function Return vs. Print & Early Return Guard Clauses

```python
def process_val(x):
    if x < 0:
        print("Negative detected")
        return 0
    if x % 2 == 0:
        return x // 2
    print("Odd positive processed")
    return x * 3

val1 = process_val(-5)
val2 = process_val(8)
val3 = process_val(7)
```

#### Line-by-Line Execution Trace:
1.  `val1 = process_val(-5)`:
    *   Condition `x < 0` (`-5 < 0`) is `True`.
    *   Executes `print("Negative detected")`.
    *   Executes `return 0`.
    *   State: `val1 = 0`.
2.  `val2 = process_val(8)`:
    *   Condition `x < 0` (`8 < 0`) is `False`.
    *   Condition `x % 2 == 0` (`8 % 2 == 0`) is `True`.
    *   Executes `return 8 // 2` -> `return 4`.
    *   `print("Odd positive processed")` is skipped!
    *   State: `val2 = 4`.
3.  `val3 = process_val(7)`:
    *   Condition `x < 0` (`7 < 0`) is `False`.
    *   Condition `x % 2 == 0` (`7 % 2 == 0`) is `False`.
    *   Executes `print("Odd positive processed")`.
    *   Executes `return 7 * 3` -> `return 21`.
    *   State: `val3 = 21`.

#### Terminal Console Output During Execution:
```text
Negative detected
Odd positive processed
```

#### Final Variable Values:
```text
val1 = 0
val2 = 4
val3 = 21
```

---

### Challenge D: Scope, Shadowing & Variable Re-binding

```python
rate = 10  # Global variable

def calculate(val):
    rate = 2  # Local shadowing variable
    result = val * rate
    return result

output1 = calculate(5)
output2 = rate * 5
```

#### Line-by-Line Execution Trace:
1.  Global scope initializes `rate = 10`.
2.  Call `calculate(5)`:
    *   Local frame created. Parameter `val = 5`.
    *   Local variable `rate = 2` is assigned (shadows global `rate = 10`).
    *   `result = 5 * 2 = 10`.
    *   Returns `10`. Local frame destroyed.
    *   State: `output1 = 10`.
3.  Evaluate `output2 = rate * 5`:
    *   In global scope, `rate` resolves to global `10`.
    *   `10 * 5 = 50`.
    *   State: `output2 = 50`.

#### Terminal Output:
```text
output1 = 10
output2 = 50
```

---

End of Reference Doc, saved as an .md file in my studio ready to be downloaded and exported
