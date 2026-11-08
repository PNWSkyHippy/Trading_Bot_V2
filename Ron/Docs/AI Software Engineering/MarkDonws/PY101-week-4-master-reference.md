# CS101 - Week 4 Master Reference: Sequence Data Structures, Slicing & Mutation Mechanics

*Welcome blurb: This authoritative, self-contained reference guide synthesizes all core concepts, mental models, memory mechanics, execution traces, and defensive programming strategies from CS101 Week 4. It covers string and list indexing/slicing, list mutation methods, iteration paradigms, sorting mechanics, memory reference behaviors, and runtime error diagnostics into a single publication-grade technical reference.*

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

### 1.1 Fundamental Definitions & Language Primitives

Python sequence data structures represent ordered collections of items where each element is accessible by its position (index). The CS101 curriculum categorizes data structures based on their **mutability** (whether the underlying memory object can be altered in place) and their **homogeneity** (whether elements must share the same data type).

*   **String (`str`)**: An immutable, ordered sequence of Unicode characters enclosed in single (`'`), double (`"`), or triple (`'''`/`"""`) quotes. Once created, individual characters cannot be modified or replaced in place.
*   **List (`list`)**: A mutable, ordered collection of arbitrary Python objects enclosed in square brackets (`[]`). Lists allow dynamic size expansion, in-place item replacement, element removal, and reordering.
*   **Range (`range`)**: An immutable, memory-efficient sequence of integers generated on demand via `range(start, stop, step)`. The `stop` value is strictly non-inclusive.
*   **Zero-Based Indexing**: A positional mapping convention where the first element of a sequence is located at index `0`, and the final element is located at index `len(sequence) - 1`.
*   **Negative Indexing**: Backward positional mapping where index `-1` addresses the last element, `-2` addresses the second to last, down to `-len(sequence)` for the first element.
*   **Slicing**: The extraction of a sub-sequence using the bracket notation `[start:stop:step]`. The extraction begins at `start` (inclusive), terminates immediately before `stop` (exclusive), and advances by `step`.
*   **In-Place Mutation**: Modifying the internal memory heap state of a mutable object (such as a `list`) without changing its memory address identity.
*   **Sort Stability**: A property of sorting algorithms (such as Python's Timsort) guaranteeing that two elements with equal sort keys preserve their original relative ordering in the sorted result.

---

### 1.2 Side-by-Side Comparison Matrices

#### Matrix A: Sequence Type Specification (`str` vs. `list` vs. `range`)

| Feature / Spec | String (`str`) | List (`list`) | Range (`range`) |
| :--- | :--- | :--- | :--- |
| **Definition** | Ordered immutable sequence of characters | Ordered mutable collection of arbitrary objects | Immutable sequence of integers generated on demand |
| **Syntax / Delimiters** | Single `' '` or double `" "` quotes | Square brackets `[item1, item2]` | Function call `range(start, stop, step)` |
| **Permitted Operators** | `+`, `*`, `in`, `not in`, `==`, `!=`, `[]` | `+`, `*`, `in`, `not in`, `==`, `!=`, `[]` | `in`, `not in`, `==`, `!=`, `[]` |
| **Mutability / Invariant** | Immutable (reassignment creates new `str`) | Mutable (in-place modification allowed) | Immutable (sequence cannot be altered) |
| **Memory Allocation** | Contiguous text block | Dynamic array of object references | Range iterator object (calculates items on demand) |
| **Common Runtime Error** | `TypeError` on item assignment | `IndexError` on out-of-bounds access | `TypeError` if float passed as argument |

#### Matrix B: Sorting Mechanics (`list.sort()` vs. `sorted()`)

| Feature / Spec | `list.sort()` Method | `sorted()` Built-In Function |
| :--- | :--- | :--- |
| **Target Object** | List instances strictly (`list`) | Any iterable sequence (`list`, `str`, `tuple`, etc.) |
| **Return Value** | `None` (returns nothing) | A **new** sorted `list` object |
| **Memory Impact** | Modifies memory in place (zero extra memory) | Allocates new memory heap space for copy |
| **Original Data** | Overwritten / modified in place | Unchanged / preserved completely |
| **Keyword Arguments** | `key=function`, `reverse=bool` | `key=function`, `reverse=bool` |
| **Common Student Trap** | Assigning result to variable (`x = my_list.sort()`) | Forgetting to capture returned list (`sorted(my_list)`) |

#### Matrix C: List Removal Methods (`pop()` vs. `remove()` vs. `del`)

| Feature / Spec | `list.pop([index])` | `list.remove(value)` | `del list[index]` |
| :--- | :--- | :--- | :--- |
| **Target Parameter** | Index position (defaults to `-1`) | Search value | Index position or slice |
| **Return Value** | Returns the removed item | Returns `None` | Statement (no return value) |
| **Search Mechanism** | Direct index lookup ($O(1)$ at end) | Linear scan for first match ($O(N)$) | Direct index/slice removal |
| **Error Trigger** | `IndexError` if index out of bounds | `ValueError` if value not in list | `IndexError` if index out of bounds |

---

## 2. Real-World Mental Models & Conceptual Mapping

### 2.1 Visual Analogies for Sequence Mechanics

#### Analogy 1: "Fence Posts vs. Wooden Rails" (Indexing vs. Slicing Bounds)
To understand why slicing `sequence[start:stop]` includes the start index but excludes the stop index, visualize a wooden split-rail fence:
*   **Fence Posts (Indices)**: Positional markers placed at the boundaries between wood panels, numbered `0, 1, 2, 3, 4`.
*   **Wooden Rails (Data Elements)**: The actual characters or list elements spanning the space between two fence posts.
*   When requesting a slice `[1:4]`, you are placing hands on **Fence Post 1** and **Fence Post 4** and picking up the wooden rails suspended between them (Rails 1, 2, and 3). Rail 4 lies beyond Post 4 and is excluded.

```
Fence Post Indices:   0       1       2       3       4       5
                     |       |       |       |       |       |
Data Rail Items:     |  'P'  |  'Y'  |  'T'  |  'H'  |  'O'  |  'N'  |
                     |       |       |       |       |       |
Slice [1:4] Extract:         [====== Rail 1 ====== Rail 2 ====== Rail 3 ======]
Extracted Result:    'Y', 'T', 'H' (Length = 4 - 1 = 3)
```

#### Analogy 2: "Stone Carving vs. Modular Train Cars" (Immutability vs. Mutability)
*   **Immutable Strings (`str`)**: A sentence carved into a marble tablet. To change a single letter, you cannot edit the marble; you must carve an entirely new tablet from scratch (`new_str = old_str.replace(...)`).
*   **Mutable Lists (`list`)**: A modular toy train where each car holds cargo. You can decouple a car (`pop()`), insert a container car in the middle (`insert()`), swap cargo in car #2 (`list[2] = new_val`), or paint all cars a new color in place without destroying the engine.

#### Analogy 3: "Labeled Name Tags vs. Physical Storage Boxes" (Variables & Heap Memory)
*   Variables in Python are **not** physical boxes containing values. They are **sticky name tags** attached by string to physical objects sitting on a warehouse heap floor.
*   Executing `a = [10, 20]` places a physical list on the floor and ties name tag `a` to it.
*   Executing `b = a` does **not** duplicate the box; it simply ties a second name tag `b` to the exact same physical box (aliasing).
*   Executing `c = a[:]` creates a brand-new physical box containing duplicate cargo and ties name tag `c` to the new box.

---

### 2.2 Structural Execution Diagrams

```
-----------------------------------------------------------------------------------
DIAGRAM A: In-Place Mutation vs. New Object Creation
-----------------------------------------------------------------------------------

1. Aliasing & In-Place Mutation:
   my_list = [3, 1, 2]
   ref = my_list
   my_list.sort()

   Namespace             Heap Memory Object
   +---------+           +------------------+
   | my_list |---------->| List Object      |
   +---------+           | ID: 0x7f9a       |
   | ref     |---------->| State: [1, 2, 3] | (Mutated directly in place!)
   +---------+           +------------------+

2. Copying & Returning New Copy:
   original = [3, 1, 2]
   copied = sorted(original)

   Namespace             Heap Memory Objects
   +----------+          +-------------------+
   | original |--------->| Original List     |
   +----------+          | ID: 0x10a1        |
                         | State: [3, 1, 2]  | (Unchanged)
                         +-------------------+
   +----------+          +-------------------+
   | copied   |--------->| New Sorted List   |
   +----------+          | ID: 0x20b2        |
                         | State: [1, 2, 3]  | (Allocated separately)
                         +-------------------+
-----------------------------------------------------------------------------------
```

---

## 3. Idiomatic Python Implementation & State Tracing

### 3.1 Console I/O, Keyword Formatting & Type Casting

```python
# --- STEP 1: Basic Console Output and Formatting ---
# Default print separates arguments with space ' ' and ends with newline '\n'
print("Python", "101", "Core")
# Console Output: Python 101 Core

# Custom separator 'sep' and custom line ending 'end'
print("2026", "06", "10", sep="-", end=" | ")
print("Status: OK")
# Console Output: 2026-06-10 | Status: OK

# --- STEP 2: Input Handling and Type Conversion ---
# Simulated string input from user via console
raw_input_age = "25"  # input() always yields str type
processed_age = int(raw_input_age)  # Convert '25' to integer 25
next_year_age = processed_age + 1  # Integer arithmetic: 25 + 1 = 26

# --- STEP 3: Safe Output Formatting with F-Strings ---
# F-strings automatically interpolate expressions and prevent TypeError
user_name = "Ron"
print(f"User: {user_name} | Age: {processed_age} | Next Year: {next_year_age}")
# Console Output: User: Ron | Age: 25 | Next Year: 26
```

---

### 3.2 String Indexing, Slicing & Method Manipulation

```python
# --- STEP 1: Positive and Negative Indexing ---
text = "PYTHON101"
# Index Map:   P(0) Y(1) T(2) H(3) O(4) N(5) 1(6) 0(7) 1(8)
# Neg Map:    -9   -8   -7   -6   -5   -4   -3   -2   -1

char_first = text[0]    # State: char_first = 'P'
char_last = text[-1]   # State: char_last = '1'
char_mid = text[3]     # State: char_mid = 'H'

# --- STEP 2: Slicing [Start Included : Stop Excluded : Step] ---
slice_prefix = text[0:6]     # Extract indices 0..5 -> 'PYTHON'
slice_numbers = text[6:9]    # Extract indices 6..8 -> '101'
slice_default = text[:6]     # Omitted start defaults to 0 -> 'PYTHON'
slice_suffix = text[6:]      # Omitted stop defaults to len -> '101'
slice_stepped = text[0:6:2]   # Step of 2 -> 'P', 'T', 'O' -> 'PTO'
slice_reversed = text[::-1]  # Negative step reverses string -> '101NOHTYP'

# --- STEP 3: String Cleaning & Transformation Methods ---
raw_data = "  btc_usd,100,BUY  \n"
cleaned_data = raw_data.strip()  # State: "btc_usd,100,BUY"
upper_data = cleaned_data.upper() # State: "BTC_USD,100,BUY"

# Splitting string into a list of substrings
tokens = upper_data.split(",")
# State: tokens = ['BTC_USD', '100', 'BUY']

# Rejoining list back into formatted string
rejoined_str = " -> ".join(tokens)
# State: rejoined_str = 'BTC_USD -> 100 -> BUY'
print(rejoined_str)
# Console Output: BTC_USD -> 100 -> BUY
```

---

### 3.3 List Creation, Slice Replacement & In-Place Replacement

```python
# --- STEP 1: List Initialization and Direct Index Mutation ---
scores = [85, 90, 78, 92, 88]
# State: scores = [85, 90, 78, 92, 88], len = 5

# Direct element replacement by positive index
scores[2] = 82  
# State: scores = [85, 90, 82, 92, 88] (78 replaced by 82)

# Direct element replacement by negative index
scores[-1] = 95 
# State: scores = [85, 90, 82, 92, 95] (88 replaced by 95)

# --- STEP 2: Sub-List Slicing and Shallow Copying ---
top_three = scores[0:3] 
# State: top_three = [85, 90, 82] (New list created)

# Explicit shallow copy using [:]
scores_backup = scores[:] 
# State: scores_backup = [85, 90, 82, 92, 95] (Separate memory object)

# --- STEP 3: Slice Replacement (Replacing multiple items at once) ---
scores[1:4] = [100, 100]
# Replaces indices 1, 2, 3 ([90, 82, 92]) with [100, 100]
# State: scores = [85, 100, 100, 95], len = 4 (List resized in place)
```

---

### 3.4 List Mutation Methods (`append`, `insert`, `extend`, `pop`, `remove`)

```python
# Initialize empty list
tasks = []

# --- 1. append(item): Add single item to end ---
tasks.append("Task_A")  # State: ['Task_A']
tasks.append("Task_C")  # State: ['Task_A', 'Task_C']

# --- 2. insert(index, item): Insert item at specific position ---
tasks.insert(1, "Task_B") 
# Shifts 'Task_C' to right -> State: ['Task_A', 'Task_B', 'Task_C']

# --- 3. extend(iterable): Append all items from an iterable ---
new_batch = ["Task_D", "Task_E"]
tasks.extend(new_batch) 
# State: ['Task_A', 'Task_B', 'Task_C', 'Task_D', 'Task_E']

# --- 4. pop(index): Remove and RETURN item at index ---
completed_last = tasks.pop() 
# Removes index -1 -> State: completed_last = 'Task_E'
# State: tasks = ['Task_A', 'Task_B', 'Task_C', 'Task_D']

completed_first = tasks.pop(0) 
# Removes index 0 -> State: completed_first = 'Task_A'
# State: tasks = ['Task_B', 'Task_C', 'Task_D']

# --- 5. remove(value): Remove FIRST occurrence of value ---
tasks.remove("Task_C") 
# Scans for 'Task_C' and deletes it -> State: tasks = ['Task_B', 'Task_D']
print(f"Final Tasks: {tasks} | Removed: {completed_last}, {completed_first}")
# Console Output: Final Tasks: ['Task_B', 'Task_D'] | Removed: Task_E, Task_A
```

---

### 3.5 Iteration Patterns: Index-Based vs. Value-Based Loops

```python
items = ["apple", "banana", "cherry"]
prices = [1.20, 0.50, 2.50]

# --- PATTERN A: Value-Based Iteration (Clean, readable when index unnecessary) ---
print("--- Value-Based Loop ---")
for item in items:
    # item directly binds to each string element in succession
    print(f"Item: {item}")
# Console Output:
# Item: apple
# Item: banana
# Item: cherry

# --- PATTERN B: Index-Based Iteration (Necessary for parallel list access/mutation) ---
print("--- Index-Based Loop ---")
for i in range(len(items)):
    # i sequence: 0, 1, 2
    item_name = items[i]
    item_price = prices[i]
    print(f"Index {i}: {item_name} costs ${item_price:.2f}")
# Console Output:
# Index 0: apple costs $1.20
# Index 1: banana costs $0.50
# Index 2: cherry costs $2.50
```

---

### 3.6 Sorting Mechanics: Custom Keys, Reversal & Stability

```python
# --- STEP 1: In-Place Mutation with list.sort() vs Built-in sorted() ---
numbers = [42, 11, 88, 23, 55]

# Using sorted() to preserve original list
sorted_copy = sorted(numbers)
# State: numbers = [42, 11, 88, 23, 55] (Unchanged)
# State: sorted_copy = [11, 23, 42, 55, 88] (New object)

# Using list.sort() to mutate in place
numbers.sort(reverse=True)
# State: numbers = [88, 55, 42, 23, 11] (Mutated to descending order)

# --- STEP 2: Custom Key Sorting ---
words = ["elephant", "fig", "banana", "apple"]

# Sort words by string length using len function as key
words_by_len = sorted(words, key=len)
# Lengths: 'fig'(3), 'apple'(5), 'banana'(6), 'elephant'(8)
# State: words_by_len = ['fig', 'apple', 'banana', 'elephant']

# --- STEP 3: Demonstrating Sort Stability (Ties preserve relative order) ---
# List of tuples representing (Player, Score)
leaderboard = [("Alice", 50), ("Bob", 80), ("Charlie", 50), ("Diana", 80)]

# Sort exclusively by Score (index 1 of tuple)
def get_score(entry):
    return entry[1]

stable_result = sorted(leaderboard, key=get_score)
# Output Trace:
# Score 50 ties: ("Alice", 50) appeared before ("Charlie", 50) -> order preserved!
# Score 80 ties: ("Bob", 80) appeared before ("Diana", 80) -> order preserved!
# State: [('Alice', 50), ('Charlie', 50), ('Bob', 80), ('Diana', 80)]
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Accidental `NoneType` Assignment from Mutation Methods
*   **Root Cause**: Calling `.sort()`, `.append()`, `.extend()`, or `.insert()` on a list performs in-place mutation and explicitly returns `None`. Assigning the function call to a variable overwrites the variable with `None`.

```python
# INCORRECT: Assigning in-place mutation return value to variable
data = [3, 1, 4, 2]
data = data.sort()  
# Bug: data.sort() returns None. 'data' is now None!
# Executing len(data) now raises: TypeError: object of type 'NoneType' has no len()

# CORRECT: Perform in-place mutation, OR assign using sorted()
data = [3, 1, 4, 2]
data.sort()  # Option A: Mutate in place (data remains a list: [1, 2, 3, 4])

# OR
data = [3, 1, 4, 2]
data = sorted(data)  # Option B: sorted() returns a new list object
```

---

### Trap 2: Direct String/Numeric Concatenation Triggering `TypeError`
*   **Root Cause**: The `+` operator requires identical data types on both sides. Joining a `str` and an `int` or `float` via `+` causes a runtime type conflict.

```python
# INCORRECT: Combining string and integer via + operator
age = 21
msg = "User age is: " + age
# Bug raises: TypeError: can only concatenate str (not "int") to str

# CORRECT: Use explicit str() casting or an F-String
age = 21
msg = "User age is: " + str(age)  # Option A: Explicit type cast
# OR
msg = f"User age is: {age}"        # Option B: F-String interpolation (Idiomatic)
```

---

### Trap 3: Off-by-One and Out-of-Bounds Sequence `IndexError`
*   **Root Cause**: Attempting to access `sequence[len(sequence)]`. Because indexing starts at `0`, the maximum valid positive index is `len(sequence) - 1`.

```python
# INCORRECT: Accessing length value as an index
items = ["A", "B", "C"]  # len = 3. Valid indices: 0, 1, 2
last_item = items[3]
# Bug raises: IndexError: list index out of range

# CORRECT: Access maximum index or use negative indexing
items = ["A", "B", "C"]
last_item = items[len(items) - 1]  # Option A: len - 1
# OR
last_item = items[-1]               # Option B: Negative index -1 (Idiomatic)
```

---

### Trap 4: Non-Numeric String Input to `int()` / `float()` Casting
*   **Root Cause**: Passing text containing alphabetic characters, spaces, or decimals to `int()` raises a data formatting exception.

```python
# INCORRECT: Direct cast without input validation
raw_val = "12.5"  # Contains decimal point
number = int(raw_val)
# Bug raises: ValueError: invalid literal for int() with base 10: '12.5'

# CORRECT: Parse appropriately or handle floats first
raw_val = "12.5"
number = int(float(raw_val))  # Cast str -> float (12.5) -> int (12)
```

---

### Trap 5: Calling Non-Existent Value Removal on Lists (`ValueError`)
*   **Root Cause**: Invoking `list.remove(x)` when `x` is not present in the list.

```python
# INCORRECT: Removing item without checking membership
inventory = ["sword", "shield"]
inventory.remove("potion")
# Bug raises: ValueError: list.remove(x): x not in list

# CORRECT: Guard clause membership check using 'in'
inventory = ["sword", "shield"]
if "potion" in inventory:
    inventory.remove("potion")
else:
    print("Item 'potion' not present in inventory.")
```

---

## 5. Python Memory Mechanics, References & Scope

### 5.1 Object Binding, Identity and Namespaces

In Python, variables do not hold data directly; they act as **name references (pointers)** bound to objects instantiated in **heap memory**.

1.  **Dynamic Typing**: Variable names have no fixed type. A name `x` can be bound to an `int` object, then rebound to a `list` object. The type resides with the **object in heap memory**, not the variable name.
2.  **Object Identity (`id()`)**: Every object in memory possesses a unique integer address ID.
    *   The `==` operator compares **value equality** (whether contents match).
    *   The `is` keyword compares **object identity** (`id(a) == id(b)`).
3.  **Assignment (`=`)**: Assigning `b = a` binds variable `b` to the **exact same memory address** as `a`. No object duplication occurs.
4.  **Local vs. Global Scope**: Variables defined inside a function body (`def`) exist exclusively in the function's local namespace. They are instantiated upon function call and destroyed upon function return (`return`).

```python
# --- Memory Binding Demonstration ---
list_a = [10, 20, 30]
list_b = list_a          # Aliasing: list_b references list_a's heap memory
list_c = list_a[:]       # Shallow Copy: list_c references a NEW list object

print(list_a == list_b)  # Output: True (Content matches)
print(list_a is list_b)  # Output: True (Identical memory address!)

print(list_a == list_c)  # Output: True (Content matches)
print(list_a is list_c)  # Output: False (Different memory addresses!)
```

---

### 5.2 Memory Heap & Namespace ASCII Diagram

```
===================================================================================
MEMORY NAMESPACE AND HEAP OBJECT BINDING DIAGRAM
===================================================================================

STACK / NAMESPACE                              HEAP MEMORY
(Variable Pointers)                            (Data Objects)

+------------------+                           +-------------------------------+
| list_a           |-------------------------->| List Object 1                 |
+------------------+                           | Memory ID: 0x88F1             |
                                               | Type: list                    |
+------------------+                           | Elements: [10, 20, 30]        |
| list_b           |-------------------------->|                               |
+------------------+ (Aliased to same object)  +-------------------------------+

+------------------+                           +-------------------------------+
| list_c           |-------------------------->| List Object 2                 |
+------------------+ (Shallow Copy)            | Memory ID: 0x99Z2             |
                                               | Type: list                    |
                                               | Elements: [10, 20, 30]        |
                                               +-------------------------------+

-----------------------------------------------------------------------------------
EXECUTION TRACE OF MUTATION:
Executing: list_a.append(99)

Result on Memory Heap:
- List Object 1 (0x88F1) is updated to [10, 20, 30, 99].
- Both list_a AND list_b reflect [10, 20, 30, 99] because they point to 0x88F1.
- List Object 2 (0x99Z2) remains [10, 20, 30] (completely isolated).
===================================================================================
```

---

## 6. Practical Integration / Mini Case Study

### Comprehensive Program: Autonomous Trade Ledger & Portfolio Analyzer

This self-contained script integrates string parsing, list mutation, index/value iteration, guard clauses, error handling, custom sorting with tuple keys, f-string output formatting, and custom console delimiters.

```python
# ===============================================================================
# AUTONOMOUS TRADE LEDGER & PORTFOLIO ANALYZER
# ===============================================================================

def process_raw_trades(raw_stream):
    """
    Parses raw comma-separated trade logs, sanitizes inputs, 
    calculates metrics, and sorts transactions.
    """
    # Guard Clause: Check for empty input
    if not raw_stream:
        print("Error: Empty input stream provided.", file=sys.stderr)
        return None

    # Step 1: Clean raw string input and split into record lines
    cleaned_stream = raw_stream.strip()
    lines = cleaned_stream.split("\n")
    
    parsed_ledger = []
    
    # Step 2: Index-based iteration over record lines
    for idx in range(len(lines)):
        raw_line = lines[idx]
        
        # Skip empty lines or comments
        if not raw_line or raw_line.startswith("#"):
            continue
            
        parts = raw_line.split(",")
        
        # Guard Clause: Validate fields
        if len(parts) != 3:
            print(f"Skipping malformed line at index {idx}: {raw_line}")
            continue
            
        ticker = parts[0].strip().upper()
        
        try:
            shares = int(parts[1].strip())
            price = float(parts[2].strip())
        except ValueError as err:
            print(f"Type conversion error on line {idx}: {err}")
            continue
            
        total_cost = round(shares * price, 2)
        
        # Store sanitized trade tuple: (Ticker, Shares, Price, TotalCost)
        parsed_ledger.append((ticker, shares, price, total_cost))
        
    return parsed_ledger


def analyze_and_display(ledger):
    """
    Calculates summary statistics and prints sorted output.
    """
    if not ledger:
        print("No valid trades to analyze.")
        return

    # Calculate portfolio total spent using value-based loop
    grand_total = 0.0
    for trade in ledger:
        # Tuple unpacking: (ticker, shares, price, total_cost)
        grand_total += trade[3]
        
    # Sort trades by Total Cost DESCENDING using custom tuple key
    def get_total_cost(trade_tuple):
        return trade_tuple[3]
        
    sorted_ledger = sorted(ledger, key=get_total_cost, reverse=True)
    
    # Display Formatted Header
    print("=" * 45)
    print("PORTFOLIO EXECUTION REPORT", end="\n")
    print("=" * 45)
    
    # Display Trades using custom separators
    for trade in sorted_ledger:
        t_name, t_shares, t_price, t_total = trade
        print(f"TICKER: {t_name:<5}", f"QTY: {t_shares:<4}", f"PRICE: ${t_price:<6.2f}", f"TOTAL: ${t_total:<8.2f}", sep=" | ")
        
    print("-" * 45)
    print(f"TOTAL PORTFOLIO EXPOSURE: ${grand_total:,.2f}")
    print("=" * 45)


# --- EXECUTION DEMONSTRATION ---
raw_data_input = """
# Raw Trade Log Stream
btc_usd , 2 , 45000.50
eth_usd , 10 , 3000.00
sol_usd , 50 , 110.25
invalid_row , X , 99.00
  
nvda , 15 , 120.00
"""

# Step 1: Execute Processing
ledger_data = process_raw_trades(raw_data_input)

# Step 2: Display Summary
analyze_and_display(ledger_data)
```

---

### Step-by-Step Execution Trace & Console Output

```
===================================================================================
EXECUTION STATE TRACE:
1. process_raw_trades receives raw_data_input.
2. raw_data_input.strip().split("\n") creates 7 raw lines.
3. Iteration loop parses valid lines:
   - Line 2: 'btc_usd , 2 , 45000.50' -> ('BTC_USD', 2, 45000.50, 90001.0)
   - Line 3: 'eth_usd , 10 , 3000.00' -> ('ETH_USD', 10, 3000.00, 30000.0)
   - Line 4: 'sol_usd , 50 , 110.25' -> ('SOL_USD', 50, 110.25, 5512.5)
   - Line 5: 'invalid_row , X , 99.00' -> Fails int("X"), catches ValueError -> Skipped!
   - Line 7: 'nvda , 15 , 120.00' -> ('NVDA', 15, 120.00, 1800.0)
4. analyze_and_display sorts ledger by TotalCost descending:
   Order: BTC_USD ($90,001.00) -> ETH_USD ($30,000.00) -> SOL_USD ($5,512.50) -> NVDA ($1,800.00)

-----------------------------------------------------------------------------------
TERMINAL CONSOLE OUTPUT:
-----------------------------------------------------------------------------------
Type conversion error on line 5: invalid literal for int() with base 10: 'X'
=============================================
PORTFOLIO EXECUTION REPORT
=============================================
TICKER: BTC_USD | QTY: 2    | PRICE: $45000.50 | TOTAL: $90001.00
TICKER: ETH_USD | QTY: 10   | PRICE: $3000.00  | TOTAL: $30000.00
TICKER: SOL_USD | QTY: 50   | PRICE: $110.25   | TOTAL: $5512.50 
TICKER: NVDA    | QTY: 15   | PRICE: $120.00   | TOTAL: $1800.00 
---------------------------------------------
TOTAL PORTFOLIO EXPOSURE: $127,313.50
=============================================
===================================================================================
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Complex Slicing & Negative Step Evaluation

```python
# --- CODE SNIPPET ---
data = "PYTHON_101_CORE"

slice_1 = data[2:8:2]
slice_2 = data[-4:-10:-2]
slice_3 = data[::-3]
```

#### Step-by-Step Diagnostic Trace

*   **String Length**: `len("PYTHON_101_CORE")` = 15.
*   **Index Map**:
    `P(0), Y(1), T(2), H(3), O(4), N(5), _(6), 1(7), 0(8), 1(9), _(10), C(11), O(12), R(13), E(14)`
*   **Neg Map**:
    `-15, -14, -13, -12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1`

1.  **`slice_1 = data[2:8:2]`**:
    *   Start = `2` (`'T'`), Stop = `8` (`'0'`, exclusive), Step = `+2`.
    *   Extracted Indices: `2` (`'T'`), `4` (`'O'`), `6` (`'_'`).
    *   **Result**: `slice_1 = "TO_"`
2.  **`slice_2 = data[-4:-10:-2]`**:
    *   Start = `-4` (`'C'`), Stop = `-10` (`'N'`, exclusive), Step = `-2` (moving backward).
    *   Extracted Neg Indices: `-4` (`'C'`), `-6` (`'1'`), `-8` (`'1'`).
    *   **Result**: `slice_2 = "C11"`
3.  **`slice_3 = data[::-3]`**:
    *   Start = End (`14`, `'E'`), Stop = Beginning, Step = `-3`.
    *   Extracted Indices: `14` (`'E'`), `11` (`'C'`), `8` (`'0'`), `5` (`'N'`), `2` (`'T'`).
    *   **Result**: `slice_3 = "EC0NT"`

```
FINAL TERMINAL OUTPUT:
slice_1 = "TO_"
slice_2 = "C11"
slice_3 = "EC0NT"
```

---

### Challenge B: Nested List Mutation, Aliasing, and Slice Replacement

```python
# --- CODE SNIPPET ---
nums = [10, 20, 30, 40, 50]
ref_a = nums
ref_b = nums[:]

nums[1:4] = [99]
ref_a.append(100)
ref_b.insert(0, 5)
```

#### Step-by-Step Diagnostic Trace

1.  `nums = [10, 20, 30, 40, 50]` initialized in memory.
2.  `ref_a = nums`: `ref_a` aliases the original list memory address (`0x01`).
3.  `ref_b = nums[:]`: `ref_b` receives a **shallow copy** in a new memory address (`0x02`), containing `[10, 20, 30, 40, 50]`.
4.  `nums[1:4] = [99]`: Slice replacement on `0x01`.
    *   Target slice `1:4` includes indices 1, 2, 3 (`[20, 30, 40]`).
    *   `[20, 30, 40]` is replaced by `[99]`.
    *   State of `0x01` (`nums` & `ref_a`): `[10, 99, 50]`.
5.  `ref_a.append(100)`: In-place append on `0x01`.
    *   State of `0x01` (`nums` & `ref_a`): `[10, 99, 50, 100]`.
6.  `ref_b.insert(0, 5)`: In-place insert at index 0 on isolated copy `0x02`.
    *   State of `0x02` (`ref_b`): `[5, 10, 20, 30, 40, 50]`.

```
FINAL TERMINAL OUTPUT:
nums  = [10, 99, 50, 100]
ref_a = [10, 99, 50, 100]
ref_b = [5, 10, 20, 30, 40, 50]
```

---

### Challenge C: Stable Sort with Multi-Criteria Tuple Keys & Reverse Flag

```python
# --- CODE SNIPPET ---
students = [
    ("Bob", 85, "A"),
    ("Alice", 90, "B"),
    ("Charlie", 85, "C"),
    ("Diana", 90, "A")
]

# Sort step 1: Sort by Name alphabetical (Ascending)
step1 = sorted(students, key=lambda s: s[0])

# Sort step 2: Sort by Grade numerical (Descending) using reverse=True
step2 = sorted(step1, key=lambda s: s[1], reverse=True)
```

#### Step-by-Step Diagnostic Trace

1.  `step1 = sorted(students, key=lambda s: s[0])`:
    *   Sorts alphabetically by index 0 (Name).
    *   Order: `"Alice"`, `"Bob"`, `"Charlie"`, `"Diana"`.
    *   `step1` = `[("Alice", 90, "B"), ("Bob", 85, "A"), ("Charlie", 85, "C"), ("Diana", 90, "A")]`.
2.  `step2 = sorted(step1, key=lambda s: s[1], reverse=True)`:
    *   Sorts numerically by index 1 (Grade) in **Descending** order (`reverse=True`).
    *   Sort algorithm is **STABLE**; tied grades maintain their relative order from `step1`.
    *   Grade 90 items in `step1`: `("Alice", 90, "B")` comes before `("Diana", 90, "A")`.
    *   Grade 85 items in `step1`: `("Bob", 85, "A")` comes before `("Charlie", 85, "C")`.
    *   Final Order: Grade 90s first (Alice, then Diana), followed by Grade 85s (Bob, then Charlie).

```
FINAL TERMINAL OUTPUT:
step2 = [
    ("Alice", 90, "B"),
    ("Diana", 90, "A"),
    ("Bob", 85, "A"),
    ("Charlie", 85, "C")
]
```

---

### Challenge D: Loop Accumulator, Index Shifting, and Guard Clause Exits

```python
# --- CODE SNIPPET ---
vals = [4, 7, 2, 9, 12, 15, 6]
running_sum = 0
processed_count = 0

for idx in range(len(vals)):
    current = vals[idx]
    
    # Guard clause 1: Skip odd numbers
    if current % 2 != 0:
        continue
        
    # Guard clause 2: Terminate loop if number > 10
    if current > 10:
        break
        
    running_sum += current
    processed_count += 1
```

#### Step-by-Step Diagnostic Trace

*   `vals` = `[4, 7, 2, 9, 12, 15, 6]`, `len` = 7. Indices: 0..6.
*   **Iteration 0** (`idx=0, current=4`):
    *   `4 % 2 != 0` is False.
    *   `4 > 10` is False.
    *   `running_sum` = `0 + 4` = `4`. `processed_count` = `1`.
*   **Iteration 1** (`idx=1, current=7`):
    *   `7 % 2 != 0` is True -> `continue` triggers! Skips remainder of loop body.
*   **Iteration 2** (`idx=2, current=2`):
    *   `2 % 2 != 0` is False.
    *   `2 > 10` is False.
    *   `running_sum` = `4 + 2` = `6`. `processed_count` = `2`.
*   **Iteration 3** (`idx=3, current=9`):
    *   `9 % 2 != 0` is True -> `continue` triggers!
*   **Iteration 4** (`idx=4, current=12`):
    *   `12 % 2 != 0` is False.
    *   `12 > 10` is True -> `break` triggers! Immediately exits loop.

```
FINAL TERMINAL OUTPUT:
running_sum = 6
processed_count = 2
last_visited_index = 4
```

---

*End of CS101 Week 4 Master Reference Document.*
