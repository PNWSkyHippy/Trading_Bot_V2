# FE101 - Week 2 Master Reference: Modern Data Structures, Iteration Mechanics, Destructuring, Memory References, and First-Class Functions

**Welcome Blurb**: This document synthesizes all core programming theory, data structure mechanics, memory models, destructuring paradigms, iteration control flows, and first-class functional abstractions from this module into an authoritative, publication-grade reference manual. Designed for rigorous technical mastery, it maps high-level language concepts to lower-level memory dynamics and concrete execution traces.

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

### Formal Definitions of Primary Data Types & Constructs

1. **Associative Mappings (Objects / Dictionaries)**: Unordered collections of key-value pairs where keys map to distinct memory locations storing associated data values. Property lookup occurs via string identifier resolution or dynamic expression evaluation.
2. **Bounded vs. Unbounded Iteration**:
   - *Conditional Repetition (`while` loops)*: Continues execution as long as a boolean predicate evaluates to `True`. Requires explicit state initialization, evaluation, and mutation steps to prevent infinite loop execution.
   - *Positional Index Control (`for` loops with range/index)*: Iterates through sequences using explicit numerical counter variables, enabling precise index-based access, strides, and position-sensitive logic.
   - *Sequence Element Traversal (`for...of` / Direct Element Iteration)*: Abstracts positional tracking to yield sequential values directly from an iterable object.
3. **Pattern Extraction (Destructuring / Unpacking)**: Structural assignment syntax that extracts elements from sequences (by relative position) or mappings (by property key name) into individual variable bindings in a single declaration.
4. **Value vs. Reference Semantics & Mutability**:
   - *Primitive Immutability*: Scalar data types (integers, floats, booleans, strings) whose in-memory state cannot be altered after creation. Reassignment creates a new value binding.
   - *Reference Mutability*: Compound structures (lists, dictionaries, custom objects) where variables store heap memory pointers. Reassignment or property alteration mutates the existing structure in-place across all referenced aliases.
5. **First-Class Functions & Functional Callbacks**: Higher-order execution primitives where function definitions are treated as first-class values stored in variables, passed into other functions as arguments (callbacks), and executed dynamically on demand.

### Side-by-Side Comparison Matrix

| Feature / Spec | Primitive Data Types | Associative Mappings (Dicts/Objects) | Ordered Sequences (Lists/Arrays) |
| :--- | :--- | :--- | :--- |
| **Definition** | Scalar immutables representing single atomic values. | Key-value pairs mapping unique hashable keys to arbitrary values. | Index-ordered collection of contiguous item references. |
| **Syntax / Delimiters** | `10`, `"text"`, `True`, `3.14` | `{ key: value }` or `dict(key=value)` | `[item1, item2, item3]` or `list()` |
| **Permitted Operators** | Arithmetic (`+`, `-`, `*`), Logical (`and`, `or`), Comparison (`==`, `<`) | Key Lookup (`obj[key]`), Member Test (`in`), Update (`obj[key] = val`) | Indexing (`arr[i]`), Unpacking (`a, b = arr`), Concatenation (`+`) |
| **Type Invariant / Mutability** | Strictly Immutable (cannot modify internal state in-place). | Strictly Mutable (keys and values can be added, updated, or deleted). | Strictly Mutable (elements can be reassigned, inserted, or removed). |
| **Common Runtime Error** | `TypeError` (operating across incompatible scalar types). | `KeyError` (querying a non-existent dictionary key). | `IndexError` (accessing an index beyond sequence boundaries). |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogies for Core Mechanics

1. **Analogy 1: "The Labeled Storage Cabinet vs. The Numbered Conveyor Belt"**
   - *Associative Mappings (Dicts/Objects)* function like a storage cabinet where every drawer has a custom text label ("age", "city"). Access requires reading the label regardless of drawer location.
   - *Ordered Sequences (Lists/Arrays)* function like a numbered conveyor belt where boxes pass by in strict numerical sequence (`0`, `1`, `2`). Access requires stopping at the specific sequence position.

2. **Analogy 2: "The Co-Signed Bank Account vs. The Duplicated Photo"**
   - *Reference Aliasing (`alias = original`)* is like giving two people debit cards to the exact same bank account. Withdrawing money via one card changes the balance visible to the other person.
   - *Shallow Copying (`copy = [...original]` or `dict.copy()`)* is like printing a duplicate photo. Writing on the second print does not alter the original print. However, if the photo depicts a locker key, both prints still point to the same physical locker (nested reference sharing).

3. **Analogy 3: "Passing the Power Tool vs. Pressing the Power Button"**
   - *Passing a First-Class Function Callback (`run_task(shout)`)* is like handing a physical power drill to a craftsman. The drill remains idle until the craftsman chooses to pull the trigger (`task()`).
   - *Passing an Executed Function Result (`run_task(shout())`)* is like pulling the trigger first and handing the craftsman the resulting hole in the wall.

### Conceptual ASCII Memory Reference Diagram

```
STACK NAMESPACE                       HEAP MEMORY
+--------------------+               +-------------------------------+
| original           |-------------->| List Object [10, 20, 30]       |
+--------------------+               | Address: 0x7FA8B1             |
| alias              |-------------->|                               |
+--------------------+               +-------------------------------+
                                                ^
                                                |
+--------------------+               +----------+--------------------+
| shallow_copy       |-------------->| Outer List [[10, 20, 30]]      |
+--------------------+               | Address: 0x7FA8C9             |
                                     | Element [0] Pointer -----------+
                                     +-------------------------------+
```

---

## 3. Idiomatic Python Implementation & State Tracing

### 1. Associative Mappings & Dynamic Property Resolution

```python
# Initialize associative mapping representing a user profile
profile = {"name": "Ron", "age": 30, "city": "London"}

# Direct key lookup and assignment
profile["age"] = 31  # State: profile["age"] updated from 30 to 31
profile["country"] = "UK"  # State: new key "country" added with value "UK"

# Dynamic property access using runtime variables
target_key = "city"
accessed_val = profile[target_key]  # Evaluates profile["city"] -> "London"

# Key deletion and post-deletion inspection
del profile["country"]  # Key "country" removed from dictionary
has_country = "country" in profile  # Evaluates to False

# State Trace Output
print("profile:", profile)  # Out: profile: {'name': 'Ron', 'age': 31, 'city': 'London'}
print("accessed_val:", accessed_val)  # Out: accessed_val: London
print("has_country:", has_country)  # Out: has_country: False
```

### 2. Iteration Protocols & Positional vs Value Control

```python
scores = [85, 92, 78]

# Index-based iteration when positional indices are required
print("--- Index-Based Iteration ---")
for idx in range(len(scores)):
    val = scores[idx]
    # Step 0: idx=0, val=85
    # Step 1: idx=1, val=92
    # Step 2: idx=2, val=78
    print("Index:", idx, "Score:", val)

# Direct value-based iteration when positional indices are omitted
print("--- Value-Based Iteration ---")
for score in scores:
    # Iteration 1: score=85
    # Iteration 2: score=92
    # Iteration 3: score=78
    print("Direct Score:", score)

# Controlled while loop with manual iteration counter and state condition
counter = 1
while counter <= 3:
    # Round 1: counter=1, condition 1 <= 3 is True
    # Round 2: counter=2, condition 2 <= 3 is True
    # Round 3: counter=3, condition 3 <= 3 is True
    print("Counter value:", counter)
    counter += 1  # Increments to 2, then 3, then 4 (terminates loop)
```

### 3. Structural Pattern Destructuring & Unpacking

```python
coordinates = [10, 20, 30]

# Unpacking positional sequence into distinct variable bindings
x_pos, y_pos, z_pos = coordinates  # State: x_pos=10, y_pos=20, z_pos=30

# Skipping unwanted positions using placeholder underscore conventions
first_val, _, third_val = coordinates  # State: first_val=10, third_val=30

# Unpacking mapping structures via keys
user_data = {"username": "r_hensley", "role": "admin"}
user_name = user_data["username"]  # State: user_name="r_hensley"
user_role = user_data.get("role", "user")  # State: user_role="admin"
missing_setting = user_data.get("theme", "default_dark")  # Fallback: "default_dark"

# Output state verification
print("Positions:", x_pos, y_pos, z_pos)  # Out: Positions: 10 20 30
print("Skipped:", first_val, third_val)  # Out: Skipped: 10 30
print("User Config:", user_name, user_role, missing_setting)  # Out: User Config: r_hensley admin default_dark
```

### 4. First-Class Functions & Callback Execution

```python
# First-class function definition
def transform_shout(text):
    return text.upper() + "!"

# Higher-order function accepting a functional callback parameter
def process_message(message, callback_fn):
    # Receives string and function handle reference
    formatted_text = callback_fn(message)  # Executes transform_shout("hello")
    return "Processed: " + formatted_text

# Passing function handle directly without invocation parentheses
result_output = process_message("hello", transform_shout)  # Evaluates to "Processed: HELLO!"

# Passing anonymous inline function (lambda) as callback
quick_result = process_message("world", lambda msg: msg.lower() + "...")

# Output state verification
print(result_output)  # Out: Processed: HELLO!
print(quick_result)  # Out: Processed: world...
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Accessing Non-Existent Mapping Keys (`KeyError`)

```python
# INCORRECT: Direct key access without existence verification causes runtime fatal crash
student_record = {"name": "Ron", "score": 95}
# level_val = student_record["level"]  # Error: KeyError: 'level'

# CORRECT: Defensive key querying using .get() with explicit default fallback
student_record = {"name": "Ron", "score": 95}
level_val = student_record.get("level", 1)  # Safe evaluation -> returns default integer 1
print("Defensive Level:", level_val)  # Out: Defensive Level: 1
```

### Trap 2: Out-of-Bounds Sequence Indexing (`IndexError`)

```python
# INCORRECT: Using inclusive range boundary matching sequence length
items = ["alpha", "beta", "gamma"]
# final_item = items[3]  # Error: IndexError: list index out of range

# CORRECT: Safe boundary indexing using len() or standard iteration
items = ["alpha", "beta", "gamma"]
if len(items) > 0:
    final_item = items[-1]  # Safe access -> "gamma"
print("Last Item:", final_item)  # Out: Last Item: gamma
```

### Trap 3: Accidental Mutation via Reference Aliasing

```python
# INCORRECT: Variable assignment copies heap reference, mutating original structure
base_scores = [10, 20, 30]
alias_scores = base_scores  # Aliasing reference
alias_scores[0] = 999  # Accidentally mutates base_scores[0] to 999!

# CORRECT: Creating an independent top-level shallow copy
original_scores = [10, 20, 30]
isolated_copy = original_scores.copy()  # Explicit top-level duplication
isolated_copy[0] = 999  # Modifies only isolated_copy

print("Original untouched:", original_scores)  # Out: Original untouched: [10, 20, 30]
print("Isolated copy:", isolated_copy)  # Out: Isolated copy: [999, 20, 30]
```

### Trap 4: Executing Callbacks During Registration Instead of Passing Handles

```python
def compute_data():
    return 42

def execute_later(task_callback):
    # Expects a function handle, not an evaluated return value
    return task_callback()

# INCORRECT: Invoking function during argument passing passes integer 42 instead of callback handle
# result = execute_later(compute_data())  # Error: TypeError: 'int' object is not callable

# CORRECT: Pass uninvoked function reference identifier
result = execute_later(compute_data)  # Correctly evaluates task_callback() -> 42
print("Execution Result:", result)  # Out: Execution Result: 42
```

---

## 5. Python Memory Mechanics, References & Scope

### Namespace Bindings & Memory Architecture

Python manages state through dynamic binding where variable names exist inside isolated **namespaces** (symbol tables) pointing to strongly typed **objects** allocated in the **heap memory**.

1. **Primitive Values**: Immutable scalars (integers, strings) are stored as fixed heap objects. When a primitive variable is modified (e.g., `x += 1`), Python creates a new scalar object on the heap and updates `x` to point to the new memory address.
2. **Reference Types & Aliasing**: Compound structures (lists, dicts) store references to their contained elements. Assigning `a = b` creates a secondary name binding pointing to the exact same heap memory address.
3. **Shallow vs. Deep Copying**:
   - *Shallow Copy (`list.copy()`, `copy.copy()`)*: Allocates a new outer collection container, but populates it with pointers to the same internal elements as the original structure.
   - *Deep Copy (`copy.deepcopy()`)*: Recursively duplicates the outer container AND all nested child structures, establishing total memory independence.

### ASCII Architecture Memory Diagram

```
[ NAMESPACE STACK ]                       [ HEAP MEMORY ALLOCATION ]

  Variable Name                             Object ID / Data Payload
+---------------+                         +---------------------------+
| num_val       |------------------------>| int: 100                  |
+---------------+                         +---------------------------+
| list_orig     |-----+                   | list: [Ref_A, Ref_B]      |
+---------------+     |                   | Address: 0x88F0           |
| list_alias    |-----+------------------>| Ref_A ----> list: [1, 2]  |
+---------------+                         | Ref_B ----> list: [3, 4]  |
| list_shallow  |------------------------>| list: [Ref_A, Ref_B]      |
+---------------+                         | Address: 0x99A1 (New)     |
                                          +---------------------------+
```

---

## 6. Practical Integration / Mini Case Study

### Game Score Analyzer & Player State Manager

This integrated application combines dictionary key-value management, sequence iteration, array unpacking, shallow copy state snapshots, and higher-order callback filter logic.

```python
# Step 1: Define higher-order filter callbacks
def is_high_score(score_entry):
    # Accepts score dict entry, returns True if score exceeds threshold
    return score_entry["points"] >= 80

def process_scores(player_data, filter_callback):
    # Extracts raw score records from player data structure
    scores_list = player_data["scores"]
    filtered_results = []
    total_points = 0
    highest_points = 0
    
    # Iterate through score entries using sequence traversal
    for entry in scores_list:
        points = entry["points"]
        total_points += points
        
        # Track maximum point value
        if points > highest_points:
            highest_points = points
            
        # Apply passed callback filter
        if filter_callback(entry):
            filtered_results.append(entry["game"])
            
    # Calculate average score
    count = len(scores_list)
    average_points = total_points / count if count > 0 else 0
    
    # Return multiple computed metrics as a summary mapping
    return {
        "total": total_points,
        "highest": highest_points,
        "average": average_points,
        "qualifying_games": filtered_results
    }

# Step 2: Initialize system state mapping
player_profile = {
    "player_id": "P_104",
    "name": "Ron",
    "scores": [
        {"game": "Round 1", "points": 75},
        {"game": "Round 2", "points": 92},
        {"game": "Round 3", "points": 88}
    ]
}

# Step 3: Create shallow copy snapshot before processing state updates
profile_snapshot = player_profile.copy()

# Step 4: Execute processing with high-score callback
analysis_results = process_scores(player_profile, is_high_score)

# Step 5: Unpack calculated metrics from summary dictionary
total_score = analysis_results["total"]
top_score = analysis_results["highest"]
avg_score = analysis_results["average"]
top_games = analysis_results["qualifying_games"]

# Output state verification and diagnostics trace
print("--- Player Score Analysis ---")
print("Player Name:", profile_snapshot["name"])
print("Total Points:", total_score)  # 75 + 92 + 88 = 255
print("Highest Point:", top_score)   # max(75, 92, 88) = 92
print("Average Point:", avg_score)   # 255 / 3 = 85.0
print("Qualifying Games:", top_games)  # ['Round 2', 'Round 3']
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Dynamic Property Resolution & Mutation Trace

```python
state = {"a": 10, "b": 20}
key_var = "a"

# Line 1: Read via dynamic key variable
val_1 = state[key_var]  # state["a"] -> 10

# Line 2: Mutate value at key "a"
state[key_var] = 50  # state becomes {"a": 50, "b": 20}

# Line 3: Add new key named literally "key_var"
state["key_var"] = 99  # state becomes {"a": 50, "b": 20, "key_var": 99}

# Verification trace
print("val_1:", val_1)  # Out: val_1: 10
print("state['a']:", state["a"])  # Out: state['a']: 50
print("state['key_var']:", state["key_var"])  # Out: state['key_var']: 99
```

### Challenge B: Nested List Reference Sharing & Mutation Diagnostics

```python
matrix = [[1, 2], [3, 4]]
matrix_copy = matrix.copy()  # Top-level shallow copy

# Line 1: Mutate outer level of shallow copy
matrix_copy.append([5, 6])  # matrix_copy gets 3rd item; matrix remains length 2

# Line 2: Mutate nested internal list reference
matrix_copy[0][0] = 999  # Shared nested list mutated! Affects matrix[0][0] too!

# Verification trace
print("Original matrix outer len:", len(matrix))  # Out: Original matrix outer len: 2
print("Copy matrix outer len:", len(matrix_copy))  # Out: Copy matrix outer len: 3
print("Original matrix[0][0]:", matrix[0][0])  # Out: Original matrix[0][0]: 999
print("Copy matrix[0][0]:", matrix_copy[0][0])  # Out: Copy matrix[0][0]: 999
```

### Challenge C: Callback Higher-Order Execution Trace

```python
accumulator = 0

def add_five(val):
    return val + 5

def apply_twice(action_fn, initial_val):
    first_pass = action_fn(initial_val)  # Pass 1: add_five(10) -> 15
    second_pass = action_fn(first_pass)  # Pass 2: add_five(15) -> 20
    return second_pass

final_output = apply_twice(add_five, 10)

# Verification trace
print("final_output:", final_output)  # Out: final_output: 20
```

### Challenge D: Unpacking Mismatches & Sequence Defaults

```python
raw_data = [100, 200, 300, 400]

# Line 1: Unpacking explicit positional elements with trailing slice capture
head_item, *middle_items, tail_item = raw_data
# head_item = 100
# middle_items = [200, 300]
# tail_item = 400

# Verification trace
print("head_item:", head_item)  # Out: head_item: 100
print("middle_items:", middle_items)  # Out: middle_items: [200, 300]
print("tail_item:", tail_item)  # Out: tail_item: 400
```
