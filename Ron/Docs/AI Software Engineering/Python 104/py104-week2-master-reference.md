# PY104 - Week 2 Master Reference: Dictionaries, Data Retrieval, and Loop Integration

*Welcome to the PY104 Week 2 Master Reference Document. This authoritative, publication-grade guide synthesizes all core programming concepts, mental models, memory mechanics, defensive coding strategies, and step-by-step code execution traces covered in this module. It is designed as a self-contained, technical reference for mastering Python dictionaries, key-based retrieval, state tracking, loop control, and modular function integration.*

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

Data structures dictate both the algorithmic complexity and readability of software systems. This module contrasts **position-based retrieval** (inherent to sequence types like lists) with **key-based retrieval** (inherent to mapping types like dictionaries), alongside the flow-control primitives that orchestrate data processing.

### Primary Data Types, Operations, and Keywords

*   **List (`list`):** A mutable, ordered sequence of elements. Elements are indexed sequentially starting at integer position `0` through `N - 1`. Searching a list for a value without knowing its index requires linear scanning ($O(N)$ time complexity).
*   **Dictionary (`dict`):** A mutable, associative mapping structure composed of unique **keys** mapped to arbitrary **values** (`key: value`). Lookup, insertion, and deletion operate via hashing, offering average $O(1)$ constant time complexity.
*   **Key (`key`):** A unique, immutable identifier within a dictionary (e.g., `str`, `int`, `tuple`). Serves as the direct address for value retrieval.
*   **Value (`value`):** The data payload associated with a key. Values can be of any Python data type, mutable or immutable, and do not need to be unique.
*   **Safe Lookup (`.get(key, default)`):** A dictionary method that evaluates a key and returns its associated value if present; otherwise, it returns a specified default value (or `None`), suppressing runtime `KeyError` exceptions.
*   **Dictionary Views (`.keys()`, `.values()`, `.items()`):** Dynamic view objects providing iterable references to the dictionary's keys, values, or key-value tuples respectively without duplicating underlying memory.
*   **Boolean Flag:** A `bool` state variable (initialized to `True` or `False`) used inside iterative blocks to signal whether a specific condition has been encountered across loop execution cycles.
*   **Loop Control (`break`):** A flow control keyword that immediately terminates the innermost enclosing loop execution, transferring program control to the statement immediately following the loop block.
*   **Helper Function:** A modular sub-routine defined using `def` that encapsulates a specific unit of logic, called repeatedly within a loop to delegate per-item transformations.

---

### Side-by-Side Comparison Matrix

| Feature / Spec | List (Position-Based Retrieval) | Parallel Lists (Index Juggling) | Dictionary (Key-Based Retrieval) |
| :--- | :--- | :--- | :--- |
| **Primary Structure** | Single ordered sequence of items | Two or more synchronized sequence lists | Unordered/insertion-ordered mapping of key-value pairs |
| **Syntax / Delimiters** | Bracket notation: `[item1, item2]` | Multiple lists: `keys = [...]`, `vals = [...]` | Curly braces / colons: `{key1: val1, key2: val2}` |
| **Retrieval Mechanism** | Integer index access: `lst[0]` | Multi-step dance: `idx = keys.index(k); val = vals[idx]` | Direct key mapping: `d[key]` or `d.get(key)` |
| **Lookup Time Complexity** | $O(1)$ by index; $O(N)$ by value search | $O(N)$ linear search through key list | $O(1)$ average constant time hash-lookup |
| **Data Integrity Risk** | Minimal for single items | High: Lists easily get out of sync if modified | Zero sync risk: Keys and values are bound in one object |
| **Permitted Key Types** | Integers only (`0` to `len - 1`) | Integers for indexing | Any hashable/immutable type (`str`, `int`, `tuple`) |
| **Mutability Behavior** | Mutable in-place via index assignment | Mutable in-place per list independently | Mutable in-place via key assignment `d[k] = v` |
| **Common Runtime Error** | `IndexError: list index out of range` | `ValueError` (missing item) or desynchronized lookup | `KeyError` (missing key during direct `[]` access) |

---

## 2. Real-World Mental Models & Conceptual Mapping

To build strong architectural intuition, abstract programming concepts can be mapped to physical systems and visual models.

### Analogy 1: The Labeled Drawer Array vs. Unmarked Storage Cubbies
Imagine a physical storage unit containing 100 drawers.
*   **List (Unmarked Cubbies):** The drawers have no labels on the front—only position numbers ($0, 1, 2, \dots, 99$). To locate "Carol's document", an assistant must start at drawer $0$ and open every drawer sequentially until they stumble upon Carol's file. This represents the **manual scan requirement**.
*   **Dictionary (Labeled Drawers):** Every drawer has a clear nameplate (e.g., `"Carol"`). The assistant walks directly to the drawer marked `"Carol"`, opens it once, and retrieves the payload. This is **direct key-based lookup**.

```
POSITION-BASED SCAN (List):
[0: Alice] --> [1: Bob] --> [2: Carol] --> [3: Dave]  (Linear $O(N)$ Scan)

KEY-BASED DIRECT LOOKUP (Dictionary):
Key: "Carol"  === Hash Table Lookup ===> [ Drawer "Carol": Grade 78 ]  (Direct $O(1)$ Access)
```

### Analogy 2: Parallel List Index Juggling vs. Single Bound File Folders
Consider maintaining student grades.
*   **Parallel Lists:** You keep a roster list in your left hand and a grade sheet in your right hand. To find Carol's grade, you scan down the left paper to line 12, remember the number 12, and then locate line 12 on the right paper. If someone inserts a new student at line 5 on the roster but forgets the grade sheet, every subsequent lookup returns corrupt, mismatched data.
*   **Dictionary:** Each student has a single folder where their name is printed on the tab and their grade is inside. The label and value are intrinsically bound.

### Analogy 3: The Assembly Line and the Station Specialist
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

---

## 3. Idiomatic Python Implementation & State Tracing

This section details idiomatic patterns across five core operational domains. Every snippet includes step-by-step state tracing annotations and console output previews.

### Domain A: Dictionary Creation, Direct Access, and Safe Lookup

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

---

### Domain B: Dictionary Iteration Views (`.keys()`, `.values()`, `.items()`)

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

---

### Domain C: Advanced Dictionary Patterns (Counting, Accumulation, Grouping)

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

---

### Domain D: Loop Control, State Tracking, and Short-Circuiting

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

---

### Domain E: Modular Loop Processing via Helper Functions

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

---

## 4. Defensive Programming & Common Traps

When transitioning from sequential lists to mapping types and loop modularity, software engineers encounter predictable runtime errors.

### Trap 1: Missing Key Direct Access (`KeyError`)
Direct bracket access on a non-existent key raises an unhandled `KeyError` exception, abruptly halting execution.

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

---

### Trap 2: Attempting Value Assignment to Method Call
A common syntax error arises from confusing the **read-only retrieval method** `.get()` with bracket assignment syntax `[]`.

```python
contacts = {"Alice": "555-0101"}

# INCORRECT: Attempting to assign a value to a function return value
# contacts.get("Alice") = "555-9999"
# SyntaxError: cannot assign to function call here / cannot assign to expression

# CORRECT: Use bracket indexing for mutation and assignment
contacts["Alice"] = "555-9999"  # Updates existing key
contacts["Bob"] = "555-0102"    # Inserts new key
```

---

### Trap 3: Tuple Iteration Bug vs. Full Index Range Scanning
When scanning lists by index, iterating over a fixed tuple `(0, len(lst)-1)` checks only the boundary indices (first and last elements), silently skipping all internal elements.

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

---

### Trap 4: Set Literal Instantiation Mismatch in Data Structures
Defining collection literals with curly braces `{}` without key-value colons creates an unordered `set`, which strips duplicate entries and lacks list ordering/indexing.

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

---

### Trap 5: Omitting Return Statements in Modular Helper Functions
Failing to include an explicit `return` statement in a helper function causes Python to implicitly return `None`, corrupting downstream collection building.

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

---

## 5. Python Memory Mechanics, References & Scope

Understanding how Python manages object references in memory is critical for predicting variable bindings, mutability behavior, and function execution frames.

### Variable Bindings and the Object Heap
In Python:
1.  **Namespaces:** Names (variables) are symbolic labels stored inside a namespace dictionary mapping variable names to memory addresses.
2.  **Heap Memory:** All actual objects (integers, strings, lists, dictionaries) reside on the memory heap.
3.  **Binding vs. Assignment:** Assigning a variable (`x = ...`) binds the symbol `x` to an object's memory address in the current frame. Assigning to a dictionary key (`d[k] = v`) alters the internal pointer table of the existing dictionary object on the heap without changing the memory address of `d` itself.

### Dictionary Hash Tables & Mutability Invariants
*   **Dictionaries are Mutable Heap Objects:** Modifying a dictionary (e.g., adding a key) alters its memory contents in-place. All variables referencing that same memory address reflect the modification.
*   **Keys Must Be Hashable (Immutable):** A dictionary key must have a hash value that remains fixed during its lifetime. Immutables (`str`, `int`, `float`, `tuple`) are hashable. Mutables (`list`, `dict`, `set`) are unhashable and cause a `TypeError` if used as keys.

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

---

## 6. Practical Integration / Mini Case Study

This case study integrates all core module concepts—dictionary creation, safe `.get()` access, frequency counting, numerical accumulation, categorical grouping, loop state flags with short-circuiting, and helper function delegation—into a single production-ready telemetry parser script.

### Case Study: E-Commerce Audit & Telemetry Processor

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

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

Test your understanding of execution mechanics, state tracking, and dictionary patterns with these four diagnostic tracing challenges.

### Challenge A: Safe Lookup & State Mutation Order

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

#### Line-by-Line Execution Trace:
1.  **Line 1:** Key `"city"` does not exist in `profile`. Inserts `"city": "Seattle"`. State: `profile = {'name': 'Ron', 'age': 59, 'city': 'Seattle'}`.
2.  **Line 2:** Key `"nickname"` is evaluated in `profile`. Not found. Default fallback `"No Nickname Set"` is evaluated and assigned to `nickname`. Dictionary remains unchanged.
3.  **Line 3:** Key `"age"` exists in `profile`. Value `59` is overwritten with `60`. State: `profile = {'name': 'Ron', 'age': 60, 'city': 'Seattle'}`.
4.  **Line 4:** Key `"age"` is evaluated in `profile`. Found. Returns value `60`. `current_age` is assigned `60`.
5.  **Line 5-7:** Terminal formatting output. `len(profile.keys())` evaluates to `3`.

```
TERMINAL OUTPUT:
Nickname: No Nickname Set
Age: 60
Keys Count: 3
```

---

### Challenge B: Short-Circuit Loop with Accumulator & Flag State

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

#### Step-by-Step Execution Trace Table:

| Iteration | Current `n` | Condition (`n < 0`) | `flag` State | `accumulator` State | Loop Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | N/A | N/A | `False` | `0` | Initialize |
| **Cycle 1** | `10` | `10 < 0` (False) | `False` | `0 + 10 = 10` | Continue |
| **Cycle 2** | `20` | `20 < 0` (False) | `False` | `10 + 20 = 30` | Continue |
| **Cycle 3** | `-5` | `-5 < 0` (**TRUE**) | `True` | `30` (Unchanged) | **BREAK EXECUTED** |
| **Cycle 4** | `40` | *Unreached* | `True` | `30` | *Skipped* |

```
TERMINAL OUTPUT:
Final Accumulator: 30
Flag State: True
```

---

### Challenge C: Multi-Pattern Counting & Grouping Diagnostic

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

#### Line-by-Line Execution Trace:
1.  **Cycle 1 (`item = "apple"`):** `first_char = 'A'`. `inventory_groups.get('A', [])` returns `[]`. `inventory_groups['A']` assigned `[]`. Appends `"apple"`. State: `{'A': ['apple']}`.
2.  **Cycle 2 (`item = "banana"`):** `first_char = 'B'`. `inventory_groups.get('B', [])` returns `[]`. `inventory_groups['B']` assigned `[]`. Appends `"banana"`. State: `{'A': ['apple'], 'B': ['banana']}`.
3.  **Cycle 3 (`item = "apple"`):** `first_char = 'A'`. `inventory_groups.get('A', ['apple'])` returns existing list `['apple']`. Appends `"apple"`. State: `{'A': ['apple', 'apple'], 'B': ['banana']}`.
4.  **Cycle 4 (`item = "cherry"`):** `first_char = 'C'`. `inventory_groups.get('C', [])` returns `[]`. `inventory_groups['C']` assigned `[]`. Appends `"cherry"`. State: `{'A': ['apple', 'apple'], 'B': ['banana'], 'C': ['cherry']}`.

```
TERMINAL OUTPUT:
Group Keys: ['A', 'B', 'C']
Group 'A': ['apple', 'apple']
```

---

### Challenge D: Helper Function Delegation & List Transformation

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

#### Step-by-Step Execution Trace:
1.  **Cycle 1 (`s = 65`):** `transform_score(65)` evaluated. `65 >= 90` (False) -> `65 >= 70` (False) -> returns `65`. `adjusted_scores.append(65)`.
2.  **Cycle 2 (`s = 75`):** `transform_score(75)` evaluated. `75 >= 90` (False) -> `75 >= 70` (**True**) -> returns `75 + 5 = 80`. `adjusted_scores.append(80)`.
3.  **Cycle 3 (`s = 95`):** `transform_score(95)` evaluated. `95 >= 90` (**True**) -> returns `95 + 10 = 105`. `adjusted_scores.append(105)`.

```
TERMINAL OUTPUT:
Original: [65, 75, 95]
Adjusted: [65, 80, 105]
```

---
*End of PY104 Master Reference Document.*
