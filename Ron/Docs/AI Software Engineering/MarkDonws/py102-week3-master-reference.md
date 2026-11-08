# PY102 - Week 3 Master Reference: Algorithmic Complexity, Data Structures & Optimization

*This Master Reference Document synthesizes all core concepts, mental models, memory mechanics, algorithmic complexities, and code execution traces from PY102 Week 3 into an authoritative, self-contained reference guide. Designed for software engineering students and technical practitioners, it bridges abstract computational theory with Python's internal memory management and production refactoring patterns.*

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

### Formal Terminology & Definitions

- **Algorithm Correctness**: The mandatory baseline property ensuring an algorithm produces accurate, mathematically sound outputs across all valid input domain instances. Correctness is an absolute prerequisite; speed without correctness is useless.
- **Algorithmic Efficiency**: The quantitative measure of computational resource consumption (CPU step operations and RAM memory allocation) required by an algorithm as a function of the input size ($n$).
- **Code Readability**: The structural clarity, naming intent, and self-documenting maintainability of source code. Highly readable code minimizes cognitive load for engineering teams during debugging and maintenance.
- **Big O Notation**: A formal asymptotic framework that categorizes the upper bound (worst-case scenario) of an algorithm's growth rate as input size $n$ approaches infinity. Big O ignores constant multipliers, coefficient offsets, and lower-order terms.
- **Time Complexity**: The mathematical function describing how an algorithm's execution step count grows relative to input size $n$.
- **Space Complexity**: The mathematical function describing how an algorithm's auxiliary memory footprint scales relative to input size $n$.
- **Constant Time ($O(1)$)**: Workload remains entirely fixed regardless of input scale $n$. Examples include direct list index access (`lst[i]`) and dictionary key lookups (`dct[key]`).
- **Linear Time ($O(n)$)**: Workload grows in direct 1:1 proportion with input size $n$. Examples include single-pass iteration over a list or searching for an unindexed item.
- **Quadratic Time ($O(n^2)$)**: Workload grows proportionally to the square of input size $n$. Examples include nested loops iterating over the same $n$-element collection.
- **Amortized $O(1)$**: The guaranteed average time per operation over a sequence of operations, accounting for rare, high-cost maintenance events (such as dynamic array resizing during list appends).
- **Invariant**: An expression or logical condition that remains strictly unchanged throughout the execution of a loop or algorithmic phase.
- **Hash Table**: The underlying probabilistic data structure powering Python dictionaries and sets, mapping keys to memory array indices via a hash function to enable $O(1)$ average-time retrieval.

---

### Core Data Structure & Complexity Comparison Matrix

| Feature / Spec | Python List (`list`) | Python Dictionary (`dict`) | Double-Ended Queue (`deque`) |
| :--- | :--- | :--- | :--- |
| **Definition** | Ordered, index-based mutable sequence stored internally as a contiguous dynamic array of object pointers. | Unordered (insertion-ordered) key-value mapping backed by a sparse hash table with hash-bucket indexing. | Doubly linked list structure optimized for fast sequential access and mutations at both endpoints. |
| **Syntax / Delimiters** | Square brackets `[val1, val2]` or `list()` | Curly braces `{key: val}` or `dict()` | `collections.deque([val1, val2])` |
| **Access by Index / Key** | `lst[i]`: $O(1)$ constant time direct index calculation. | `dct[key]`: $O(1)$ average time hash lookup. | Endpoints `dq[0]`, `dq[-1]`: $O(1)$. Random index `dq[i]`: $O(n)$ pointer traversal. |
| **Search by Value** | `val in lst`: $O(n)$ linear scan through contiguous array pointers. | `val in dct.values()`: $O(n)$ linear scan over dictionary values. | `val in dq`: $O(n)$ linear traversal across doubly linked nodes. |
| **Insertion / Addition** | `lst.append(x)`: Amortized $O(1)$. `lst.insert(i, x)`: $O(n)$ due to element shifting. | `dct[key] = val`: $O(1)$ average time hash assignment and collision resolution. | `dq.append(x)` (right) or `dq.appendleft(x)` (left): Both $O(1)$ constant time. |
| **Deletion / Removal** | `lst.pop()` (end): $O(1)$. `lst.pop(i)` / `lst.pop(0)`: $O(n)$ due to element shifting. | `del dct[key]` / `dct.pop(key)`: $O(1)$ average time hash slot clearing. | `dq.pop()` (right) or `dq.popleft()` (left): Both $O(1)$ constant time. |
| **Type Invariants** | Mutable. Elements can be any data type. Indices must be integers. | Mutable container. Keys must be immutable/hashable; values can be any type. | Mutable. Elements can be any data type; endpoint pointers maintained. |
| **Common Runtime Exception** | `IndexError`: Out-of-bounds index access or popping from an empty list. | `KeyError`: Accessing missing key directly without `.get()` or `in` check. | `IndexError`: Popping from an empty deque or invalid index offset. |
| **Primary Performance Bottleneck** | Scanning for values ($O(n)$) or mutating front/middle elements ($O(n)$ shifting). | High memory footprint; hash collisions causing theoretical $O(n)$ worst-case lookup. | Random middle indexing is $O(n)$ requiring traversal from closest endpoint node. |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: The Cafeteria Tray Stack vs. The Ticket Booth Line
- **Stack (LIFO - Last-In, First-Out)**: Picture a spring-loaded cafeteria tray dispenser. Clean trays are pushed onto the top of the stack (`append()`). Customers always take the top tray off the stack (`pop()`). The last tray added is the first tray removed. Operations at the top take constant time $O(1)$ because no other trays need to move.
- **Queue (FIFO - First-In, First-Out)**: Picture a single-file line at a theater ticket booth. The first person to enter the line (`append()`) is the first person served (`popleft()`). 
  - *Inefficient Queue (Standard List)*: If you use a Python list for a queue, removing the front person via `list.pop(0)` forces *every single person behind them* to take one step forward to fill the empty space. For $n$ people, this requires $n-1$ shifts ($O(n)$ linear time).
  - *Efficient Queue (`collections.deque`)*: Using `deque.popleft()` opens the front gate without requiring anyone behind to move. The booth operator simply shifts their focus to the next linked node ($O(1)$ constant time).

```
STRICT LIFO STACK (Python List)
   [Push / Pop Endpoint]  <--->  [ TRAY C (Top) ]
                                 [ TRAY B       ]
                                 [ TRAY A (Base)]

EFFICIENT FIFO QUEUE (collections.deque)
   [Left Endpoint]                                 [Right Endpoint]
   (Popleft O(1))  <--- [Node 1] <-> [Node 2] <-> [Node 3] <--- (Append O(1))
```

---

### Analogy 2: The Street Address Index vs. The Phone Book Hash
- **List Indexing ($O(1)$)**: Imagine a suburban street where houses are numbered strictly from 0 to 99 on a uniform grid. To visit House #42, you drive directly to block 42 without checking Houses 0 through 41.
- **List Value Search ($O(n)$)**: If you do not know the house number and are looking for "John Smith", you must knock on every door starting at House #0 until you find him ($O(n)$ worst-case scan).
- **Dictionary Hash Table ($O(1)$ Average)**: Imagine a phone book with an instant index tab. When you search for key `"John Smith"`, a hash algorithm immediately converts `"John Smith"` into a page number (bucket index). You flip straight to that page and read his phone number ($O(1)$ key lookup).

```
LIST LINEAR SEARCH vs DICTIONARY HASH LOOKUP

List Scan (Searching for "Target"):
Index 0         Index 1         Index 2         Index n-1
[ "Alpha" ] ->  [ "Beta" ]  ->  [ "Target" ] -> [ ... ]     (Scans 1-by-1: O(n))

Dictionary Hash Lookup:
Key: "Target" ---> Hash Function: hash("Target") % size ---> Bucket 2 ---> Value: 99  (Direct jump: O(1))
```

---

### Analogy 3: Assembly Line Blueprint vs. Redundant Inspection (Invariant Extraction)
- **Unoptimized Loop ($O(n^2)$)**: An assembly line inspector picks up a part, measures the room temperature, recalculates the factory tax rate formula, and then inspects the part. Repeating environmental calculations for every single item wastes massive energy.
- **Optimized Loop with Invariant Extraction ($O(n)$)**: The inspector calculates the factory tax rate once before the conveyer belt starts running (storing it in a local variable), then uses that fixed result for every item on the line.

---

## 3. Idiomatic Python Implementation & State Tracing

### 3.1 Step Counting and Big O Complexity Classes

```python
def analyze_complexity_classes(data_list):
    # --- O(1) CONSTANT TIME DEMONSTRATION ---
    # Step 1: Access element by direct index calculation
    first_element = data_list[0]  # State: Instant memory jump. Step count = 1
    # Console Output: First element retrieved instantly regardless of len(data_list)
    print("O(1) Step Output:", first_element)

    # --- O(n) LINEAR TIME DEMONSTRATION ---
    linear_step_count = 0
    # Step 2: Iterate over every element once
    for item in data_list:
        linear_step_count += 1  # State: Increments exactly once per element
        # Intermediate State: linear_step_count tracks index + 1
    # Console Output: Total steps equal len(data_list)
    print("O(n) Total Step Count:", linear_step_count)

    # --- O(n^2) QUADRATIC TIME DEMONSTRATION ---
    quadratic_step_count = 0
    # Step 3: Nested iteration over the collection
    for i in data_list:
        for j in data_list:
            quadratic_step_count += 1  # State: Increments n times for each of the n outer iterations
            # Intermediate State: quadratic_step_count reaches n * n
    # Console Output: Total steps equal len(data_list) squared
    print("O(n^2) Total Step Count:", quadratic_step_count)

# Execution Trace with n = 4 elements:
sample_data = [10, 20, 30, 40]
analyze_complexity_classes(sample_data)
# Output:
# O(1) Step Output: 10
# O(n) Total Step Count: 4
# O(n^2) Total Step Count: 16
```

---

### 3.2 List vs. Dictionary Search Refactoring

```python
def compare_search_performance(user_ids, target_id):
    # --- INEFFICIENT: List Search O(n) ---
    list_steps = 0
    found_in_list = False
    for uid in user_ids:
        list_steps += 1  # Step counter tracking linear evaluation
        if uid == target_id:
            found_in_list = True
            break  # Early exit stops linear scan early if found
    # State: list_steps = 5 if target is at index 4 or worst-case len(user_ids) if missing
    print(f"List Search: Found={found_in_list}, Steps Taken={list_steps}")

    # --- EFFICIENT: Dictionary Search O(1) Average ---
    # Step 1: Convert list to dict map once (or maintain dict natively)
    user_dict = {uid: True for uid in user_ids}  # Pre-processing cost O(n)
    dict_steps = 1  # Hash lookup takes 1 step operation
    found_in_dict = target_id in user_dict  # Hash key lookup O(1)
    # State: Instant boolean result via hash key verification
    print(f"Dict Search: Found={found_in_dict}, Steps Taken={dict_steps}")

# Execution Trace with 5 elements:
ids = [101, 102, 103, 104, 105]
compare_search_performance(ids, 105)
# Output:
# List Search: Found=True, Steps Taken=5
# Dict Search: Found=True, Steps Taken=1
```

---

### 3.3 Sequential Collections: Stacks (`list`) vs. Queues (`collections.deque`)

```python
from collections import deque

def demonstrate_stacks_and_queues():
    # --- STACK IMPLEMENTATION (LIFO via Python list) ---
    undo_stack = []
    
    # State Step 1: Push actions onto stack O(1)
    undo_stack.append("Action_1")  # State: ["Action_1"]
    undo_stack.append("Action_2")  # State: ["Action_1", "Action_2"]
    undo_stack.append("Action_3")  # State: ["Action_1", "Action_2", "Action_3"]
    
    # State Step 2: Pop last action from top of stack O(1)
    last_action = undo_stack.pop()  # State: last_action = "Action_3", undo_stack = ["Action_1", "Action_2"]
    print("Stack Pop (LIFO):", last_action)

    # --- QUEUE IMPLEMENTATION (FIFO via collections.deque) ---
    task_queue = deque()

    # State Step 1: Enqueue tasks to back of queue O(1)
    task_queue.append("Task_A")  # State: deque(["Task_A"])
    task_queue.append("Task_B")  # State: deque(["Task_A", "Task_B"])
    task_queue.append("Task_C")  # State: deque(["Task_A", "Task_B", "Task_C"])

    # State Step 2: Dequeue task from front of queue O(1)
    first_task = task_queue.popleft()  # State: first_task = "Task_A", task_queue = deque(["Task_B", "Task_C"])
    print("Queue Popleft (FIFO):", first_task)

demonstrate_stacks_and_queues()
# Output:
# Stack Pop (LIFO): Action_3
# Queue Popleft (FIFO): Task_A
```

---

### 3.4 Invariant Extraction & Single-Pass Refactoring Patterns

```python
def optimize_ratio_calculation(scores):
    # --- UNOPTIMIZED: Recalculating invariant inside loop O(n^2) ---
    # The total sum is an invariant (does not change during loop execution)
    unoptimized_ratios = []
    unoptimized_ops = 0
    for score in scores:
        # BUG: sum(scores) is executed repeatedly inside loop! sum() takes O(n)
        current_sum = sum(scores)  # Step count per iteration = len(scores)
        unoptimized_ratios.append(score / current_sum)
        unoptimized_ops += len(scores) + 1
    print(f"Unoptimized Loop Steps: {unoptimized_ops}")

    # --- OPTIMIZED: Invariant Extraction O(n) ---
    optimized_ratios = []
    optimized_ops = 0
    # Step 1: Extract invariant outside loop
    total_sum = sum(scores)  # Executed ONCE: len(scores) operations
    optimized_ops += len(scores)
    
    # Step 2: Single pass ratio calculation
    for score in scores:
        optimized_ratios.append(score / total_sum)  # O(1) operation inside loop
        optimized_ops += 1
    print(f"Optimized Loop Steps: {optimized_ops}")

data = [10, 20, 30, 40, 50]  # n = 5
optimize_ratio_calculation(data)
# Output:
# Unoptimized Loop Steps: 30
# Optimized Loop Steps: 10
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: `IndexError` on Out-of-Bounds Indexing or Empty Sequence Removal

```python
# INCORRECT: Direct access without bounds check causes crash
items = [10, 20]
# Exception Raised: IndexError: list index out of range
third_item = items[2]

# CORRECT: Defensive check or try-except handling
items = [10, 20]
if len(items) > 2:
    third_item = items[2]
else:
    third_item = None  # Safe fallback value
print("Safely Handled Missing Index:", third_item)
```

---

### Trap 2: `KeyError` on Direct Dictionary Key Access

```python
# INCORRECT: Accessing a missing key directly causes fatal error
user_profile = {"username": "alex99", "role": "admin"}
# Exception Raised: KeyError: 'email'
user_email = user_profile["email"]

# CORRECT: Defensive access using .get() method or membership check
user_profile = {"username": "alex99", "role": "admin"}
# Option A: .get() with default fallback value
user_email = user_profile.get("email", "no_email_provided@domain.com")
print("Safe Profile Email:", user_email)

# Option B: Membership verification
if "email" in user_profile:
    email_val = user_profile["email"]
else:
    email_val = "unregistered"
print("Verified Email State:", email_val)
```

---

### Trap 3: The Hidden $O(n^2)$ Loop Trap (`val in list` or `list.pop(0)` inside a loop)

```python
# INCORRECT: Nested linear search creates hidden O(n^2) runtime bottleneck
list_a = list(range(1000))
list_b = list(range(500, 1500))
common_elements = []

# 'item in list_b' scans list_b linearly (O(n)) inside a linear loop (O(n)) = O(n^2)
for item in list_a:
    if item in list_b:  # HIDDEN BOTTLENECK: O(n) operation repeated n times!
        common_elements.append(item)

# CORRECT: Refactor list_b to a set/dict for O(1) membership lookups -> Total O(n)
set_b = set(list_b)  # One-time conversion O(n)
fast_common_elements = []

for item in list_a:
    if item in set_b:  # O(1) average lookup inside linear loop = O(n) overall
        fast_common_elements.append(item)
print("Optimized Overlap Count:", len(fast_common_elements))
```

---

### Trap 4: Mutability and Unhashable Key Traps (`TypeError: unhashable type: 'list'`)

```python
# INCORRECT: Using a mutable list as a dictionary key raises TypeError
coordinates_map = {}
location_point = [37.7749, -122.4194]
# Exception Raised: TypeError: unhashable type: 'list'
coordinates_map[location_point] = "San Francisco"

# CORRECT: Use an immutable tuple as the dictionary key
coordinates_map = {}
location_tuple = (37.7749, -122.4194)  # Tuples are immutable and hashable
coordinates_map[location_tuple] = "San Francisco"
print("Successfully Registered Location:", coordinates_map[location_tuple])
```

---

## 5. Python Memory Mechanics, References & Scope

### Dynamic Typing & Object Binding
In Python, variables are **not typed memory boxes**. Instead, variable names are simply symbolic references (pointers) bound to typed objects residing in **Heap Memory**.
- **Assignment (`x = 10`)**: Binds the variable name `x` in the current **Namespace** to an integer object `10` in Heap Memory.
- **Reassignment (`x = "Hello"`)**: Changes the reference pointer of `x` to point to a string object `"Hello"`. The original integer object `10` is left for garbage collection if no other references exist.

### Contiguous Pointer Arrays vs. Sparse Hash Buckets

1. **Python List (`PyListObject`)**:
   - Consists of a contiguous block of **memory addresses (pointers)** pointing to the actual elements scattered in heap memory.
   - Indexing (`lst[i]`) multiplies the index $i$ by pointer size (8 bytes) and jumps directly to that memory offset ($O(1)$).
   - Modifying middle elements (`lst.insert(0, x)` or `lst.pop(0)`) requires shifting all downstream pointer memory blocks via `memmove()`, resulting in $O(n)$ overhead.

2. **Python Dictionary (`PyDictObject`)**:
   - Consists of a sparse hash table array.
   - Executing `dct[key]` runs `hash(key)`, maps the resulting integer to a table bucket index, and retrieves the stored value pointer.
   - Hash collisions are resolved using open addressing with quadratic probing, preserving $O(1)$ average access.

```
NAMESPACES & HEAP MEMORY ARCHITECTURE

[ Local Namespace ]                 [ Heap Memory Objects ]
+-----------------+                 +-----------------------+
| variable_a      | --------------> | PyLongObject (Val: 42)|
+-----------------+                 +-----------------------+
| variable_b      | ------+
+-----------------+       |         +-----------------------+
| user_list       | ----+ | ------> | PyListObject          |
+-----------------+     | |         | Size: 2, Capacity: 4  |
                        | |         | Pointers: [ p0, p1 ]  |
                        | |         +-------------|---|-----+
                        | |                       |   |
                        | +-----------------------+   |
                        |                             v
                        |           +-----------------------+
                        |           | PyUnicodeObject ("SF")|
                        |           +-----------------------+
                        |
                        v
          +-------------------------------+
          | PyDictObject (Hash Table)     |
          | Buckets: [ None, (k1, v1) ]   |
          +-------------------------------+
```

---

## 6. Practical Integration / Mini Case Study

### High-Throughput E-Commerce Log & Queue Processor

This cohesive script processes incoming e-commerce clickstream events, maintains a FIFO customer service request queue, handles user undo operations via a LIFO stack, and refactors an $O(n^2)$ user aggregation task into a single-pass $O(n)$ hash map lookup.

```python
from collections import deque

class ECommerceAnalyticsEngine:
    def __init__(self):
        # Data Structures Initialization
        self.service_queue = deque()    # FIFO Queue for customer support tickets
        self.navigation_stack = []      # LIFO Stack for user page navigation history
        self.user_database = {}         # Dictionary for O(1) user profile lookups

    def register_users(self, user_records):
        # Populates database map for O(1) user details lookup
        for uid, name, tier in user_records:
            # Hash table insertion: O(1) average time per record
            self.user_database[uid] = {"name": name, "tier": tier, "spent": 0.0}

    def process_navigation_click(self, page_name):
        # Pushes page view to LIFO navigation stack
        self.navigation_stack.append(page_name)  # O(1) push

    def undo_navigation(self):
        # Pops most recent page view from LIFO navigation stack
        if self.navigation_stack:
            return self.navigation_stack.pop()   # O(1) pop
        return None

    def enqueue_support_ticket(self, ticket_id):
        # Enqueues customer ticket into FIFO service queue
        self.service_queue.append(ticket_id)     # O(1) enqueue

    def process_next_support_ticket(self):
        # Dequeues earliest customer ticket from FIFO service queue without shifting
        if self.service_queue:
            return self.service_queue.popleft()  # O(1) dequeue via deque
        return None

    def aggregate_user_purchases_optimized(self, transaction_logs):
        # Refactors quadratic nested search into an O(n) single-pass aggregation
        # transaction_logs: list of tuples (user_id, purchase_amount)
        for uid, amount in transaction_logs:
            # O(1) Dictionary Lookup and Update
            if uid in self.user_database:
                self.user_database[uid]["spent"] += amount
            # State Trace: Direct bucket modification without scanning full list

# --- COMPLETE EXECUTION TRACE & TEST BENCH ---
engine = ECommerceAnalyticsEngine()

# 1. Register Users
raw_users = [(101, "Alice", "Gold"), (102, "Bob", "Silver"), (103, "Charlie", "Bronze")]
engine.register_users(raw_users)

# 2. Simulate LIFO Navigation Stack
engine.process_navigation_click("Home_Page")
engine.process_navigation_click("Product_Catalog")
engine.process_navigation_click("Checkout_Page")

popped_page = engine.undo_navigation()  # State: Pops "Checkout_Page"
print("Undo Navigation Result (LIFO):", popped_page)  # Output: Checkout_Page

# 3. Simulate FIFO Service Queue
engine.enqueue_support_ticket("Ticket_1001")
engine.enqueue_support_ticket("Ticket_1002")

served_ticket = engine.process_next_support_ticket()  # State: Dequeues "Ticket_1001"
print("Served Ticket Result (FIFO):", served_ticket)    # Output: Ticket_1001

# 4. Aggregate Transactions O(n)
logs = [(101, 150.00), (102, 45.50), (101, 89.99), (103, 12.00)]
engine.aggregate_user_purchases_optimized(logs)

# Final State Trace Output
print("Aggregated User Database State:")
for uid, profile in engine.user_database.items():
    print(f" User {uid} ({profile['name']}): Total Spent = ${profile['spent']:.2f}")

# Output:
# Undo Navigation Result (LIFO): Checkout_Page
# Served Ticket Result (FIFO): Ticket_1001
# Aggregated User Database State:
#  User 101 (Alice): Total Spent = $239.99
#  User 102 (Bob): Total Spent = $45.50
#  User 103 (Charlie): Total Spent = $12.00
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Nested Loops with Early Exit (`break`) and Best-Case vs. Worst-Case Evaluation

```python
def diagnostic_search(matrix, target):
    steps = 0
    found = False
    for row in matrix:
        for val in row:
            steps += 1
            if val == target:
                found = True
                break  # CRITICAL: Breaks out of inner loop ONLY
        if found:
            break      # CRITICAL: Outer break triggered by found flag
    return found, steps

grid = [
    [10, 20, 30],
    [40, 50, 60],
    [70, 80, 90]
]

# CASE 1: Target at beginning (Best-Case execution)
res_1, steps_1 = diagnostic_search(grid, 10)
# Step-by-Step State Trace:
# Outer Row 0 ([10, 20, 30]):
#   Inner Val 0: 10 == 10 -> steps=1, found=True -> break inner
# Outer check: found is True -> break outer
# Final Case 1 Result: found=True, steps=1 (O(1) Best Case)

# CASE 2: Target missing (Worst-Case execution)
res_2, steps_2 = diagnostic_search(grid, 99)
# Step-by-Step State Trace:
# Outer Row 0: 3 inner checks (10, 20, 30) -> steps=3
# Outer Row 1: 3 inner checks (40, 50, 60) -> steps=6
# Outer Row 2: 3 inner checks (70, 80, 90) -> steps=9
# Final Case 2 Result: found=False, steps=9 (O(n*m) Worst Case)

print(f"Case 1 (Best): Found={res_1}, Steps={steps_1}")   # Output: Found=True, Steps=1
print(f"Case 2 (Worst): Found={res_2}, Steps={steps_2}")  # Output: Found=False, Steps=9
```

---

### Challenge B: Hidden $O(n^2)$ Complexity vs. Linear Refactoring Trace

```python
def trace_deduplication(raw_list):
    # APPROACH 1: List-based deduplication
    unique_list = []
    list_steps = 0
    for item in raw_list:
        list_steps += 1  # Outer loop step
        # Hidden inner step: 'item not in unique_list' checks unique_list sequentially
        for existing in unique_list:
            list_steps += 1
        if item not in unique_list:
            unique_list.append(item)
            
    # APPROACH 2: Set-based deduplication
    seen_set = set()
    unique_set_list = []
    set_steps = 0
    for item in raw_list:
        set_steps += 1  # Outer loop step
        # 'item not in seen_set' takes O(1) step via hashing
        if item not in seen_set:
            seen_set.add(item)
            unique_set_list.append(item)
            
    return list_steps, set_steps

data = list(range(100)) + list(range(100))  # 200 elements total
l_steps, s_steps = trace_deduplication(data)

# Step-by-Step Step Count Evaluation:
# List Deduplication Steps: 200 outer checks + ~10000 inner search steps = 10100 steps
# Set Deduplication Steps: 200 outer checks + 200 direct hash lookups = 200 steps

print(f"List Deduplication Total Steps: {l_steps}")  # Output: ~10100 steps
print(f"Set Deduplication Total Steps: {s_steps}")   # Output: 200 steps
```

---

### Challenge C: Stack and Queue Pipeline Interleaved State Trace

```python
from collections import deque

def pipeline_trace():
    stack = []
    queue = deque()
    trace_log = []

    # Step 1: Process initial inputs
    inputs = [1, 2, 3, 4]
    for x in inputs:
        stack.append(x * 10)     # stack: [10], [10, 20], [10, 20, 30], [10, 20, 30, 40]
        queue.append(x + 100)    # queue: deque([101, 102, 103, 104])

    # Intermediate State Check:
    # stack contents = [10, 20, 30, 40]
    # queue contents = deque([101, 102, 103, 104])

    # Step 2: Interleaved extraction
    # Operation A: Pop from stack (LIFO) -> 40
    val_a = stack.pop()          # stack: [10, 20, 30]
    trace_log.append(val_a)

    # Operation B: Popleft from queue (FIFO) -> 101
    val_b = queue.popleft()      # queue: deque([102, 103, 104])
    trace_log.append(val_b)

    # Operation C: Push result back to queue
    queue.append(val_a + val_b)  # queue: deque([102, 103, 104, 141])

    # Operation D: Pop remaining stack elements into log
    while stack:
        trace_log.append(stack.pop())  # Pops 30, then 20, then 10

    # Final State Evaluation:
    # trace_log sequence = [40, 101, 30, 20, 10]
    # remaining queue = deque([102, 103, 104, 141])
    return trace_log, list(queue)

final_log, final_q = pipeline_trace()
print("Execution Log Sequence:", final_log)  # Output: [40, 101, 30, 20, 10]
print("Final Queue Contents:", final_q)      # Output: [102, 103, 104, 141]
```

---

### Challenge D: Invariant Extraction and Single-Pass Ratio Trace

```python
def trace_invariant_refactoring(prices, tax_rate):
    # Problem: Calculate final taxed price ratio relative to total taxed inventory value
    
    # --- UNOPTIMIZED APPROACH ---
    # Invariant bug: Re-calculating total taxed sum inside every loop iteration
    unopt_results = []
    unopt_eval_count = 0
    for p in prices:
        # Repetitive calculation of total taxed sum:
        taxed_sum = 0
        for item in prices:
            taxed_sum += item * (1 + tax_rate)  # Nested loop execution
            unopt_eval_count += 1
        
        current_taxed_price = p * (1 + tax_rate)
        unopt_results.append(current_taxed_price / taxed_sum)

    # --- OPTIMIZED APPROACH ---
    # Extract invariant outside loop
    opt_results = []
    opt_eval_count = 0
    
    # Step 1: Pre-calculate invariant once
    single_tax_multiplier = 1 + tax_rate            # Constant calculation
    total_raw_sum = sum(prices)                    # O(n) sum
    total_taxed_sum = total_raw_sum * single_tax_multiplier # Single math operation
    opt_eval_count += len(prices) + 2

    # Step 2: Single pass evaluation
    for p in prices:
        current_taxed = p * single_tax_multiplier
        opt_results.append(current_taxed / total_taxed_sum)
        opt_eval_count += 1

    return unopt_eval_count, opt_eval_count, opt_results

test_prices = [10.0, 20.0, 30.0, 40.0]  # n = 4
tax = 0.08

unopt_steps, opt_steps, results = trace_invariant_refactoring(test_prices, tax)

# Execution Diagnostic Output:
print(f"Unoptimized Evaluation Steps (n=4): {unopt_steps}") # Output: 16 steps (n^2)
print(f"Optimized Evaluation Steps (n=4): {opt_steps}")     # Output: 10 steps (linear)
print("Calculated Ratios:", [round(r, 4) for r in results]) # Output: [0.1, 0.2, 0.3, 0.4]
```
