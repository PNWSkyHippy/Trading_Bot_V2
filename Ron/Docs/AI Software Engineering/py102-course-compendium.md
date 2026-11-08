# PY102: Complete Course Master Reference & Technical Manual

*Welcome blurb: The complete, unabridged compilation of all 4 weeks of Python Foundations of data structures and arrays.*

---

## Master Course-Wide Index

### PART I: WEEK 1 - Master Reference: Foundations of Data Structures & Array Mechanics
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-1)
   - Primary Technical Definitions
   - Structural Comparison Matrix
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-1)
   - Model 1: The Digital Workshop
   - Model 2: The Movie Theater Line (Index Shifting)
   - Model 3: Cinema Seating Grid (2D Coordinate Mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-1)
   - 3.1 Array Mutation & Reshaping Mechanics
   - 3.2 Multi-Dimensional Grid Operations
   - 3.3 Accumulator Pattern: Filtering vs. Transforming
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-1)
   - Trap 1: IndexError via Direct Index Over-Bounds Access
   - Trap 2: IndexError via Deletion on Empty Lists
   - Trap 3: ValueError on Invalid Item Removal
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-1)
   - Namespace Bindings & Heap Object Memory
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-1)
   - Venue Seating & VIP Reservation Manager
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-1)
   - Challenge A: Playlist Mutation Execution Trace
   - Challenge B: 2D Cinema Grid Mutation & Cell Query
   - Challenge C: Helper-Based Filtering Accumulator Trace
   - Challenge D: Boundary Guards vs. Safe Slicing

### PART II: WEEK 2 - Master Reference: Linear Data Structures (Stacks & Queues)
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-2)
   - Core Vocabulary & Operations
   - Side-by-Side Structural Comparison Matrix
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-2)
   - 1. The Stack Analogy: Heavy Buffet Plate Dispenser & Book Pile
   - 2. The Queue Analogy: Coffee Shop & Ice-Cream Truck Line
   - 3. The Hybrid Analogy: Adventurers in Line with Item Backpacks
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-2)
   - 3.1 Stack Operations using Python Lists
   - 3.2 List-Based Queue Operations
   - 3.3 Module Imports & High-Performance collections.deque
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-2)
   - Trap 1: Underflow Exception (IndexError)
   - Trap 2: Overwriting Collection Reference with None (AttributeError)
   - Trap 3: Calling popleft() on Standard Python Lists (AttributeError)
   - Trap 4: Module Name Scope & Namespace Ambiguity (NameError)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-2)
   - 1. Variables as Object References (Binding vs Assignment)
   - 2. Passing Data Structures to Functions
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-2)
   - Dungeon Adventurer & Inventory Dispatcher
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-2)
   - Challenge A: Stack Undo-Redo & Double-Pop Trace
   - Challenge B: Dual-Ended List Queue Manipulation
   - Challenge C: High-Performance collections.deque Trace
   - Challenge D: Function Scope & Mutable Reference Side-Effect Trace

### PART III: WEEK 3 - Master Reference: Algorithmic Complexity, Data Structures & Optimization
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-3)
   - Formal Terminology & Definitions
   - Core Data Structure & Complexity Comparison Matrix
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-3)
   - Analogy 1: The Cafeteria Tray Stack vs. The Ticket Booth Line
   - Analogy 2: The Street Address Index vs. The Phone Book Hash
   - Analogy 3: Assembly Line Blueprint vs. Redundant Inspection (Invariant Extraction)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-3)
   - 3.1 Step Counting and Big O Complexity Classes
   - 3.2 List vs. Dictionary Search Refactoring
   - 3.3 Sequential Collections: Stacks (list) vs. Queues (collections.deque)
   - 3.4 Invariant Extraction & Single-Pass Refactoring Patterns
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-3)
   - Trap 1: IndexError on Out-of-Bounds Indexing or Empty Sequence Removal
   - Trap 2: KeyError on Direct Dictionary Key Access
   - Trap 3: The Hidden O(n^2) Loop Trap
   - Trap 4: Mutability and Unhashable Key Traps
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-3)
   - Dynamic Typing & Object Binding
   - Contiguous Pointer Arrays vs. Sparse Hash Buckets
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-3)
   - High-Throughput E-Commerce Log & Queue Processor
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-3)
   - Challenge A: Nested Loops with Early Exit (break)
   - Challenge B: Hidden O(n^2) Complexity vs. Linear Refactoring Trace
   - Challenge C: Stack and Queue Pipeline Interleaved State Trace
   - Challenge D: Invariant Extraction and Single-Pass Ratio Trace

### PART IV: WEEK 4 - Master Reference: Searching and Sorting Algorithms in Python
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-4)
   - Primary Terminology & Keywords
   - Side-by-Side Comparison Matrix
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-4)
   - Analogy 1: The Phone Book Search (Linear vs. Binary Search)
   - Analogy 2: Playing Card Arrangement (Insertion Sort)
   - Analogy 3: Bubble Sort Neighbor Exchange
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-4)
   - Topic 1: Sequential Linear Search
   - Topic 2: Binary Search (Divide and Conquer)
   - Topic 3: Bubble Sort Algorithm
   - Topic 4: Insertion Sort Algorithm
   - Topic 5: Python Built-in Sorting Tools (sorted() and .sort())
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-4)
   - Trap 1: Expecting .sort() to Return a New List
   - Trap 2: Running Binary Search on Unsorted Data
   - Trap 3: Off-By-One Index Initialization in Binary Search
   - Trap 4: Mutating a List While Iterating Over It
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-4)
   - Dynamic Binding & Memory Allocation
   - Reference Identity Verification
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-4)
   - High-Frequency Trade Management System
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-4)
   - Challenge A: Single Pass Bubble Sort State Trace
   - Challenge B: First Step Insertion Sort State Trace
   - Challenge C: Binary Search Low/Mid/High Pointer Trace
   - Challenge D: Custom Sorting with key=len and Stability

---

## Unified Course Cross-Reference Matrix

| Data Structure / Construct | Primary Python Syntax | Access / Lookup | Insertion / Enqueue | Deletion / Dequeue / Pop | Best Time Complexity | Worst Time Complexity | Auxiliary Space | Key Memory / Invariant Property | Primary Failure Trap & Defensive Guard |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Python List (1D Array)** | `[item1, item2]` | Direct Index: $O(1)$ <br> Value Search: $O(n)$ | End `append()`: $O(1)$ amortized <br> Middle `insert()`: $O(n)$ | End `pop()`: $O(1)$ <br> Front/Middle `pop(i)`: $O(n)$ | $O(1)$ (index) | $O(n)$ (scan / shift) | $O(n)$ | Contiguous pointer array on heap; index shifts require $O(n)$ `memmove` | `IndexError` on out-of-bounds index or empty pop. <br> **Guard:** `if 0 <= idx < len(lst):` |
| **Python Dictionary (Hash Map)** | `{"key": value}` | Key Lookup `dict[key]`: $O(1)$ avg | Key Assignment `dict[key] = val`: $O(1)$ avg | Key Removal `del dict[key]`: $O(1)$ avg | $O(1)$ avg | $O(n)$ (rare severe hash collisions) | $O(n)$ | Sparse hash table mapping hashable keys to bucket indices | `KeyError` on missing key access. <br> **Guard:** `dict.get(key, default)` or `if key in dict:` |
| **Double-Ended Queue (`collections.deque`)** | `from collections import deque` <br> `dq = deque()` | Endpoints `dq[0]`, `dq[-1]`: $O(1)$ <br> Middle `dq[i]`: $O(n)` | Right `append()`: $O(1)$ <br> Left `appendleft()`: $O(1)` | Right `pop()`: $O(1)$ <br> Left `popleft()`: $O(1)` | $O(1)$ | $O(1)$ (endpoints) <br> $O(n)$ (middle search) | $O(n)$ | Doubly-linked list of fixed-size block nodes; zero memory shifts on endpoint operations | `AttributeError` when calling `popleft()` on list; `IndexError` on empty pop. <br> **Guard:** `if dq:` |
| **2D Nested List (Grid / Matrix)** | `[[r0c0, r0c1], [r1c0, r1c1]]` | Dual Index `grid[r][c]`: $O(1)` | Inner row append: $O(1)$ <br> Row/Col insert: $O(n)` | Cell pop: $O(n)$ inner shift | $O(1)$ | $O(n 	imes m)$ full scan | $O(n 	imes m)$ | Outer list containing inner row list references; row-major memory structure | `IndexError` on row or column boundary breach. <br> **Guard:** `if 0 <= r < len(grid) and 0 <= c < len(grid[r]):` |
| **Stack (LIFO Construct)** | List `stack = []` | Top Peek `stack[-1]`: $O(1)` | Push `stack.append(x)`: $O(1)` | Pop `stack.pop()`: $O(1)` | $O(1)$ | $O(1)$ | $O(n)$ | Last-In, First-Out enforcement at rightmost index (top) | Underflow `IndexError` on empty stack pop/peek. <br> **Guard:** `if stack:` |
| **Queue (FIFO Construct)** | `deque` or List | Front Peek `q[0]`: $O(1)` | Enqueue `q.append(x)`: $O(1)` | Dequeue list `pop(0)`: $O(n)$ <br> Dequeue deque `popleft()`: $O(1)` | $O(1)$ | $O(n)$ (list) <br> $O(1)$ (`deque`) | $O(n)$ | First-In, First-Out enforcement; items enter rear and exit front | $O(n)$ performance trap with `list.pop(0)`. <br> **Refactor:** Use `collections.deque.popleft()` |
| **Linear Search** | `for idx, val in enumerate(lst):` | Sequential Scan: $O(n)` | N/A | N/A | $O(1)$ (target at index 0) | $O(n)$ (target at end or missing) | $O(1)$ | Read-only scan; operates on unsorted or sorted collections | Inefficient $O(n)$ scans when direct hash table lookups exist. <br> **Refactor:** Convert to set/dict |
| **Binary Search** | `while low <= high:` divide-and-conquer | Halving Search Space: $O(\log n)` | N/A | N/A | $O(1)$ (target at initial mid) | $O(\log n)$ | $O(1)$ iterative | **Strict Invariant:** Collection MUST be pre-sorted | Silent failure on unsorted input; off-by-one index crash. <br> **Guard:** `high = len(lst) - 1` |
| **Bubble Sort** | Nested loops adjacent swap | Compare neighbors | N/A | N/A | $O(n)$ (optimized early-exit flag) | $O(n^2)$ | $O(1)$ in-place | Adjacent pair swapping; largest unpositioned element bubbles right | Extreme $O(n^2)$ quadratic slowdown on large datasets |
| **Insertion Sort** | Outer loop, inner shift `while` | Building sorted left subset | N/A | N/A | $O(n)$ (nearly or fully sorted) | $O(n^2)$ | $O(1)$ in-place | Cards analogy; shifts larger elements right to create target insertion hole | Misidentifying shift operations vs element overwrites |
| **Timsort (Python Built-in)** | `sorted(lst)` or `lst.sort()` | Hybrid Merge/Insertion Sort | N/A | N/A | $O(n)$ (already sorted) | $O(n \log n)$ | $O(n)$ | Stable sorting algorithm preserving relative order of equal keys | Assigning `None` return from `lst.sort()`. <br> **Guard:** Use `sorted()` for new list |

---

## PART I: WEEK 1 - Master Reference: Foundations of Data Structures & Array Mechanics

### PY102 - Week 1 Master Reference: Foundations of Data Structures & Array Mechanics
**Welcome to the PY102 Week 1 Master Reference Document.** This authoritative guide synthesizes all core concepts, mental models, memory mechanics, defensive programming habits, and code execution traces from Week 1 into a self-contained reference manual. It is designed to bridge the transition from basic syntax execution to professional software design and algorithmic reasoning.

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-1)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-1)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-1)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-1)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-1)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-1)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-1)

--------------------------------------------------------------------------------

<a id="1-abstract-foundations--core-theory---week-1"></a>
#### 1. Abstract Foundations & Core Theory
Software development fundamentally shifts in PY102 from writing syntax instructions to designing structured data systems. Core engineering design is governed by the foundational directive: **"Structure first. Steps second. Code third."**

##### Primary Technical Definitions
*   **Data Structure:** A specialized format for organizing, storing, and managing data in computer memory so that specific operations (such as searching, updating, or iterating) can be executed efficiently.
*   **Array / Python List:** An ordered, zero-indexed collection of elements stored sequentially in memory. In Python, standard dynamic lists fulfill the architectural role of arrays.
*   **Zero-Based Indexing:** A numbering scheme where the initial element of a sequence is assigned an index of 0. For a collection of length N, valid positive indices span 0 to N - 1.
*   **Negative Indexing:** A reverse positional offset mechanism where index -1 addresses the last item in a sequence, -2 addresses the second-to-last item, down to -N for the first element.
*   **In-Place Update (Mutation):** Replacing a value at an existing index position (list[i] = new_val) without modifying the overall length or shifting surrounding elements.
*   **Structural Reshaping:** Operations that alter the length and memory alignment of a collection (append, insert, pop, remove), forcing subsequent elements to recalculate their positional indices.
*   **Multi-Dimensional Array (2D Grid):** A nested structure wherein an outer array contains child arrays as its elements, representing data in rows and columns accessed via dual indices (grid[row][col]).
*   **Accumulator Pattern:** A programmatic construct that creates an initially empty collection ([]) and incrementally populates it inside an iteration loop based on evaluation criteria.
*   **Filtering vs. Transforming:**
    *   *Filtering:* Selecting a subset of original elements based on a boolean condition (reducing or maintaining list length).
    *   *Transforming:* Applying a modification rule to every element in an array, generating a new list of identical length.
*   **Guard Clause:** A defensive conditional check positioned at the start of a code path to detect invalid inputs or out-of-bound indices, exiting early or taking fallback action before a runtime crash occurs.

--------------------------------------------------------------------------------

##### Structural Comparison Matrix
| Feature / Spec | Python List (1D Array) | Python Dictionary | Multi-Dimensional Array (2D List) |
| ------ | ------ | ------ | ------ |
| **Primary Purpose** | Sequential, ordered data management | Direct key-to-value association | Tabular, grid-based, or spatial data modeling |
| **Delimiters & Syntax** | Square brackets [item1, item2] | Curly braces {"key": value} | Nested square brackets [[r0c0, r0c1], [r1c0, r1c1]] |
| **Lookup Mechanism** | Positional Integer Indexing list[index] | Hash Key Access dict[key] | Dual Integer Indexing grid[row][col] |
| **Order Preservation** | Strictly ordered by insertion and index | Key order preserved (Python 3.7+) | Row-major ordered sequence |
| **Element Modification** | In-place overwrite or list mutation methods | Key assignment or value update | Cell-level targeting grid[r][c] = val |
| **Reshaping Overhead** | Middle insert/pop causes O(N) index shifts | Key insertion/deletion maintains O(1) amortized cost | Row or column operations shift inner/outer lists |
| **Primary Crash Traps** | IndexError (out of valid 0 to N-1 range) | KeyError (querying non-existent key) | IndexError (invalid row or column index) |

--------------------------------------------------------------------------------

<a id="2-real-world-mental-models--conceptual-mapping---week-1"></a>
#### 2. Real-World Mental Models & Conceptual Mapping
To master data structure logic, abstract memory operations must be mapped onto tangible, real-world physical systems.
##### Model 1: The Digital Workshop
A computer program is analogous to an industrial workshop.
*   **The Unstructured Floor:** Throwing tools, fasteners, and raw materials into an unorganized pile on the floor represents raw, unstructured data. Locating a specific bolt requires searching every single item in the pile.
*   **Organized Shelving & Drawers:** Data structures function as labeled drawers, compartmentalized toolboxes, and indexed racks. Selecting a list vs. a dictionary is identical to choosing between a numbered drill-bit organizer (ordered index) versus a labeled key pegboard (key-value lookup).

```
UNSTRUCTURED PILE (Unorganized Memory)
[ Screws ]  [ Hammer ]  [ Nails ]  [ Wrench ]  --> Must search one by one

STRUCTURED WORKSHOP (Data Structures)
List (Ordered Racks):        [0: Drill] -> [1: Wrench] -> [2: Hammer]
Dictionary (Labeled Pegs):  "Screws" => 120, "Nails" => 500
```

--------------------------------------------------------------------------------

##### Model 2: The Movie Theater Line (Index Shifting)
The behavior of elements during array mutation mirrors people standing in a ticket line.
*   **In-Place Update (`line[2] = "Ben"`):** Person #2 changes their shirt. The total number of people remains identical, and nobody behind them moves.
*   **Insertion (`line.insert(1, "Eve")`):** "Eve" steps into the line at position 1. Everyone previously standing at position 1 and behind must physically take one step back, increasing their index number by +1.
*   **Deletion (`line.pop(0)`):** The person at the front leaves. Every single remaining person in line must take one step forward, decreasing their index number by -1.

```
Initial Line:  [0: Alice]  [1: Bob]    [2: Cara]    [3: Dan]
pop(0):         (Leaves)   <-- Step Left -- Step Left -- Step Left
Resulting:     [0: Bob]    [1: Cara]   [2: Dan]
```

--------------------------------------------------------------------------------

##### Model 3: Cinema Seating Grid (2D Coordinate Mapping)
Multi-dimensional lists function as cinema seating grids where coordinates specify vertical level first, then horizontal position.
*   **Outer Index (`grid[row]`):** Selects the specific horizontal row array.
*   **Inner Index (`grid[row][col]`):** Pinpoints the individual seat cell within that selected row array.

```
               Col 0     Col 1     Col 2
            +---------+---------+---------+
Row 0  -->  |  [0][0] |  [0][1] |  [0][2] |
            +---------+---------+---------+
Row 1  -->  |  [1][0] |  [1][1] |  [1][2] |
            +---------+---------+---------+
Row 2  -->  |  [2][0] |  [2][1] |  [2][2] |
            +---------+---------+---------+
```

--------------------------------------------------------------------------------

<a id="3-idiomatic-python-implementation--state-tracing---week-1"></a>
#### 3. Idiomatic Python Implementation & State Tracing
##### 3.1 Array Mutation & Reshaping Mechanics
```python
# Initializing baseline list
playlist = ["Intro", "Song A", "Song B", "Song C"]
# State: ["Intro", "Song A", "Song B", "Song C"] | len = 4

# 1. Append: Add to terminal end
playlist.append("Song D")
# State: ["Intro", "Song A", "Song B", "Song C", "Song D"] | len = 5
# Trace: "Song D" placed at new index 4 (len - 1)

# 2. In-Place Update: Modify without shifting
playlist[1] = "Remix A"
# State: ["Intro", "Remix A", "Song B", "Song C", "Song D"] | len = 5
# Trace: Value at index 1 overwritten; length unchanged

# 3. Insertion: Insert at specific index
playlist.insert(1, "Ad")
# State: ["Intro", "Ad", "Remix A", "Song B", "Song C", "Song D"] | len = 6
# Trace: "Ad" inserted at idx 1; "Remix A", "Song B", "Song C", "Song D" shift right (+1 idx)

# 4. Positional Deletion: Remove by index
popped_item = playlist.pop(3)
# State: ["Intro", "Ad", "Remix A", "Song C", "Song D"] | len = 5
# Trace: Element "Song B" at idx 3 removed and returned; "Song C" & "Song D" shift left (-1 idx)
# Value of popped_item: "Song B"

# 5. Value Deletion: Remove by literal matching value
playlist.remove("Ad")
# State: ["Intro", "Remix A", "Song C", "Song D"] | len = 4
# Trace: First occurrence of "Ad" searched and removed; remaining elements shift left

print("Final Playlist:", playlist)
# Terminal Output: Final Playlist: ['Intro', 'Remix A', 'Song C', 'Song D']
```

--------------------------------------------------------------------------------

##### 3.2 Multi-Dimensional Grid Operations
```python
# Initialize a 3x3 Cinema Seating Chart
seats = [
    ["A1", "A2", "A3"],  # Row index 0
    ["B1", "B2", "B3"],  # Row index 1
    ["C1", "C2", "C3"]   # Row index 2
]
# Initial State:
# Row 0: ["A1", "A2", "A3"]
# Row 1: ["B1", "B2", "B3"]
# Row 2: ["C1", "C2", "C3"]

# Cell Update: Reserve seat B3 (Row 1, Col 2)
seats[1][2] = "B3_RESERVED"
# State Row 1: ["B1", "B2", "B3_RESERVED"]

# Inner List Reshaping: Remove first seat from Row 2
removed_seat = seats[2].pop(0)
# State Row 2: ["C2", "C3"] | "C1" popped out

# Inner List Insertion: Insert extra VIP seat in Row 0 at Col 1
seats[0].insert(1, "A1_VIP")
# State Row 0: ["A1", "A1_VIP", "A2", "A3"]

# Target Inspection
target_cell = seats[0][2]
# State Query: seats[0] is now ["A1", "A1_VIP", "A2", "A3"]. Index 2 holds "A2".
print("Target Cell seats[0][2]:", target_cell)
# Terminal Output: Target Cell seats[0][2]: A2
```

--------------------------------------------------------------------------------

##### 3.3 Accumulator Pattern: Filtering vs. Transforming
```python
# Dataset: Raw product records with prices
raw_prices = [45.0, 120.0, 85.5, 30.0, 200.0]

# --- PATTERN A: FILTERING WITH HELPER FUNCTION ---
def is_premium(price):
    """Single-purpose boolean helper to evaluate filter threshold."""
    return price >= 80.0

premium_prices = []  # Step 1: Initialize accumulator list
for price in raw_prices:  # Step 2: Iterate through source
    if is_premium(price):  # Step 3: Evaluate helper condition
        premium_prices.append(price)  # Step 4: Accumulate passing items

# Trace premium_prices: [120.0, 85.5, 200.0]

# --- PATTERN B: TRANSFORMING ---
TAX_RATE = 1.10
taxed_prices = []  # Step 1: Initialize accumulator list
for price in raw_prices:  # Step 2: Iterate through source
    calculated = round(price * TAX_RATE, 2)  # Step 3: Apply transformation logic
    taxed_prices.append(calculated)  # Step 4: Accumulate transformed value

# Trace taxed_prices: [49.5, 132.0, 94.05, 33.0, 220.0]

print("Filtered (Premium):", premium_prices)
print("Transformed (Taxed):", taxed_prices)
# Terminal Output:
# Filtered (Premium): [120.0, 85.5, 200.0]
# Transformed (Taxed): [49.5, 132.0, 94.05, 33.0, 220.0]
```

--------------------------------------------------------------------------------

<a id="4-defensive-programming--common-traps---week-1"></a>
#### 4. Defensive Programming & Common Traps
Building robust software requires handling edge cases defensively to prevent runtime crashes.
##### Trap 1: IndexError via Direct Index Over-Bounds Access
Attempting to access an index equal to or greater than len(collection) causes Python to raise an IndexError.
```python
# INCORRECT: Direct access without boundary check
scores = [95, 88]
# len(scores) is 2. Valid positive indices are 0 and 1.
third_score = scores[2]
# RUNTIME ERROR: IndexError: list index out of range

# CORRECT: Guard Clause implementation
scores = [95, 88]
if len(scores) >= 3:
    third_score = scores[2]
else:
    third_score = None
    print("Guard Warning: Insufficient elements in list.")

# CORRECT: Safe Slicing technique (never raises IndexError)
safe_subset = scores[:3]  # Returns [95, 88] gracefully
```

--------------------------------------------------------------------------------

##### Trap 2: IndexError via Deletion on Empty Lists
Calling .pop() on a list that contains zero elements triggers an execution fatal crash.
```python
# INCORRECT: Popping from an unverified empty list
task_queue = []
active_task = task_queue.pop()
# RUNTIME ERROR: IndexError: pop from empty list

# CORRECT: Defensive validation guard clause
task_queue = []
if len(task_queue) > 0:  # Or simply: if task_queue:
    active_task = task_queue.pop()
else:
    active_task = None
    print("Queue Status: No pending tasks available.")
```

--------------------------------------------------------------------------------

##### Trap 3: ValueError on Invalid Item Removal
Calling .remove(val) when val is absent from the target list raises a fatal ValueError.
```python
# INCORRECT: Unvalidated element removal
inventory = ["milk", "bread", "eggs"]
inventory.remove("cheese")
# RUNTIME ERROR: ValueError: list.remove(x): x not in list

# CORRECT: Membership check prior to removal
inventory = ["milk", "bread", "eggs"]
target_item = "cheese"
if target_item in inventory:
    inventory.remove(target_item)
else:
    print(f"Inventory Warning: '{target_item}' not found for removal.")
```

--------------------------------------------------------------------------------

<a id="5-python-memory-mechanics-references--scope---week-1"></a>
#### 5. Python Memory Mechanics, References & Scope
##### Namespace Bindings & Heap Object Memory
In Python, variables are not named memory boxes that hold raw data directly. Instead, variables are **name bindings in a namespace** that contain memory pointers referencing **objects stored in heap memory**.
1.  **Dynamic Reference Allocation:** Executing x = [10, 20] creates a list object in heap memory and binds the label x to that object's address.
2.  **Pointer Arrays in Lists:** A Python list object does not store primitive data inline. It holds a contiguous array of **memory pointers** referencing other discrete objects in heap memory.
3.  **Shifting Cost Mechanics:** When an element is inserted or popped from index 0, Python must physically shift all internal memory pointers in the list's pointer buffer. This structural reorganization requires O(N) operations.

```
NAMESPACE (Local Scope)             HEAP MEMORY (Object Storage)

+---------------+                  +----------------------------------+
| Variable: x   | -------------->  | Python List Object (Header)      |
+---------------+                  | Size: 3, Allocated Capacity: 4   |
                                   | Pointers Buffer:                 |
                                   | [0] ------> Integer Object: 10   |
                                   | [1] ------> Integer Object: 20   |
                                   | [2] ------> Integer Object: 30   |
                                   +----------------------------------+

2D NESTED LIST REFERENCES:

+---------------+                  +----------------------------------+
| Variable: grid| -------------->  | Outer List Object                |
+---------------+                  | [0] ----> Row 0 List: ["A1","A2"]|
                                   | [1] ----> Row 1 List: ["B1","B2"]|
                                   +----------------------------------+
```

--------------------------------------------------------------------------------

<a id="6-practical-integration--mini-case-study---week-1"></a>
#### 6. Practical Integration / Mini Case Study
The following cohesive Python script integrates array updates, structural reshaping, 2D grid cell mapping, helper-based accumulator filtering, and defensive guard checks into a unified venue seating manager.
```python
"""
VENUE SEATING & VIP RESERVATION MANAGER
Integrates lists, 2D grids, helper filters, and guard clauses.
"""

def is_vip_ticket(price):
    """Helper function to filter VIP price thresholds."""
    return price >= 150.0

def safe_get_cell(grid, row, col):
    """Defensive lookup returning cell data or out-of-bounds warning."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        return grid[row][col]
    return "INVALID_CELL"

def main():
    print("=== 1. INITIALIZING VENUE DATA STRUCTURES ===")
    # 2D Grid representing 3 rows of seating
    seating_grid = [
        ["Seat_A1", "Seat_A2", "Seat_A3"],
        ["Seat_B1", "Seat_B2", "Seat_B3"],
        ["Seat_C1", "Seat_C2", "Seat_C3"]
    ]
    ticket_prices = [50.0, 175.0, 220.0, 80.0, 160.0]

    print("\n=== 2. PERFORMING GRID RESERVATIONS & RESHAPING ===")
    # Reserve center seat (Row 1, Col 1)
    seating_grid[1][1] = "RESERVED_B2"
    
    # Add a VIP Seat to Row 0 at Index 1
    seating_grid[0].insert(1, "Seat_A1_VIP")
    
    # Remove last seat from Row 2 defensively
    if len(seating_grid[2]) > 0:
        cancelled = seating_grid[2].pop()
        print(f"Cancelled Terminal Seat: {cancelled}")

    print("\n=== 3. ACCUMULATOR PATTERN (VIP TICKET FILTERING) ===")
    vip_tickets = []
    for price in ticket_prices:
        if is_vip_ticket(price):
            vip_tickets.append(price)
    print(f"Processed VIP Ticket Sales: {vip_tickets}")

    print("\n=== 4. DEFENSIVE BOUNDARY INSPECTIONS ===")
    test_queries = [(0, 1), (1, 1), (2, 5)]
    for r, c in test_queries:
        status = safe_get_cell(seating_grid, r, c)
        print(f"Query Cell ({r}, {c}) -> Status: {status}")

    print("\n=== FINAL SEATING GRID STATE ===")
    for idx, row in enumerate(seating_grid):
        print(f"Row {idx}: {row}")

if __name__ == "__main__":
    main()
```

##### Execution Output Trace
```
=== 1. INITIALIZING VENUE DATA STRUCTURES ===

=== 2. PERFORMING GRID RESERVATIONS & RESHAPING ===
Cancelled Terminal Seat: Seat_C3

=== 3. ACCUMULATOR PATTERN (VIP TICKET FILTERING) ===
Processed VIP Ticket Sales: [175.0, 220.0, 160.0]

=== 4. DEFENSIVE BOUNDARY INSPECTIONS ===
Query Cell (0, 1) -> Status: Seat_A1_VIP
Query Cell (1, 1) -> Status: RESERVED_B2
Query Cell (2, 5) -> Status: INVALID_CELL

=== FINAL SEATING GRID STATE ===
Row 0: ['Seat_A1', 'Seat_A1_VIP', 'Seat_A2', 'Seat_A3']
Row 1: ['Seat_B1', 'RESERVED_B2', 'Seat_B3']
Row 2: ['Seat_C1', 'Seat_C2']
```

--------------------------------------------------------------------------------

<a id="7-step-by-step-code-tracing-challenges--diagnostics---week-1"></a>
#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Playlist Mutation Execution Trace
###### Diagnostic Code
```python
playlist = ["Intro", "Song A", "Song B", "Song C"]
playlist.append("Song D")
playlist.insert(1, "Ad")
playlist.pop(3)
```
###### Step-by-Step State Evaluation
1. playlist = ["Intro", "Song A", "Song B", "Song C"]
    *  State: ["Intro", "Song A", "Song B", "Song C"] (Indices 0..3)
2. playlist.append("Song D")
    *  State: ["Intro", "Song A", "Song B", "Song C", "Song D"] (Indices 0..4)
3. playlist.insert(1, "Ad")
    *  Inserts "Ad" at index 1. Indices 1 to 4 shift right by +1.
    *  State: ["Intro", "Ad", "Song A", "Song B", "Song C", "Song D"]
    *  Index Alignment: 0: "Intro", 1: "Ad", 2: "Song A", 3: "Song B", 4: "Song C", 5: "Song D"
4. playlist.pop(3)
    *  Removes element at current index 3, which is "Song B". Indices 4 to 5 shift left by -1.
    *  Final State: ["Intro", "Ad", "Song A", "Song C", "Song D"]

###### Terminal Output
```
['Intro', 'Ad', 'Song A', 'Song C', 'Song D']
```

--------------------------------------------------------------------------------

##### Challenge B: 2D Cinema Grid Mutation & Cell Query
###### Diagnostic Code
```python
seats = [
    ["A1", "A2", "A3"],
    ["B1", "B2", "B3"],
    ["C1", "C2", "C3"]
]
seats[1][2] = "B3_taken"
seats[2].pop(0)
seats[0].insert(1, "A1_extra")
result = seats[0][2]
```
###### Step-by-Step State Evaluation
1. Initial Grid State:
    *  Row 0: ["A1", "A2", "A3"]
    *  Row 1: ["B1", "B2", "B3"]
    *  Row 2: ["C1", "C2", "C3"]
2. seats[1][2] = "B3_taken"
    *  Overwrites Row 1, Col 2.
    *  Row 1 becomes: ["B1", "B2", "B3_taken"]
3. seats[2].pop(0)
    *  Pops index 0 from Row 2 ("C1"). Row 2 elements shift left.
    *  Row 2 becomes: ["C2", "C3"]
4. seats[0].insert(1, "A1_extra")
    *  Inserts "A1_extra" at index 1 of Row 0. Existing Row 0 items shift right.
    *  Row 0 becomes: ["A1", "A1_extra", "A2", "A3"]
    *  Index Alignment for Row 0: [0]: "A1", [1]: "A1_extra", [2]: "A2", [3]: "A3"
5. result = seats[0][2]
    *  Inspects Row 0, Index 2. Value is "A2".

###### Terminal Output
```
Value of seats[0][2]: 'A2'
```

--------------------------------------------------------------------------------

##### Challenge C: Helper-Based Filtering Accumulator Trace
###### Diagnostic Code
```python
names = ["Anna", "Bob", "Christopher", "Eve", "Jonathan", "Li"]

def is_short(name):
    return len(name) <= 3

short_names = []
for name in names:
    if is_short(name):
        short_names.append(name)
```
###### Step-by-Step State Evaluation
1. Iteration 1 ("Anna"): len("Anna") = 4 <= 3 -> False. Skipped.
2. Iteration 2 ("Bob"): len("Bob") = 3 <= 3 -> True. Appended. short_names = ["Bob"]
3. Iteration 3 ("Christopher"): len("Christopher") = 11 <= 3 -> False. Skipped.
4. Iteration 4 ("Eve"): len("Eve") = 3 <= 3 -> True. Appended. short_names = ["Bob", "Eve"]
5. Iteration 5 ("Jonathan"): len("Jonathan") = 8 <= 3 -> False. Skipped.
6. Iteration 6 ("Li"): len("Li") = 2 <= 3 -> True. Appended. short_names = ["Bob", "Eve", "Li"]

###### Terminal Output
```
['Bob', 'Eve', 'Li']
```

--------------------------------------------------------------------------------

##### Challenge D: Boundary Guards vs. Safe Slicing
###### Diagnostic Code
```python
def process_scores(scores):
    # Safe Slicing Path
    top_three = scores[:3]
    
    # Guard Clause Path
    if len(scores) >= 3:
        third = scores[2]
    else:
        third = "N/A"
        
    return top_three, third

res1 = process_scores([100, 90, 80, 70])
res2 = process_scores([95])
```
###### Step-by-Step State Evaluation
1. Execution process_scores([100, 90, 80, 70]):
    *  top_three = [100, 90, 80, 70][:3] -> [100, 90, 80]
    *  len(scores) is 4 -> len(scores) >= 3 is True.
    *  third = scores[2] -> 80
    *  Returns: ([100, 90, 80], 80)
2. Execution process_scores([95]):
    *  top_three = [95][:3] -> [95] (Slicing safely returns available elements without crashing)
    *  len(scores) is 1 -> len(scores) >= 3 is False.
    *  Guard branch executes: third = "N/A"
    *  Returns: ([95], 'N/A')

###### Terminal Output
```
res1: ([100, 90, 80], 80) res2: ([95], 'N/A')
```

---

## PART II: WEEK 2 - Master Reference: Linear Data Structures (Stacks & Queues)

### PY102 - Week 2 Master Reference: Linear Data Structures (Stacks & Queues)
Welcome to the **PY102 Week 2 Master Reference Document**. This publication-grade technical guide synthesizes all core concepts, mental models, memory mechanics, defensive programming practices, and step-by-step code traces from across the module into an authoritative, self-contained reference text. It is fully formatted in GitHub Flavored Markdown and engineered for direct export and integration into your master class notebook.

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-2)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-2)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-2)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-2)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-2)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-2)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-2)

--------------------------------------------------------------------------------

<a id="1-abstract-foundations--core-theory---week-2"></a>
#### 1. Abstract Foundations & Core Theory
Linear data structures organize data sequentially, where elements are arranged in a contiguous logical sequence. The two foundational abstract linear data structures introduced in this module are **Stacks** and **Queues**. Though both maintain ordered collections, they enforce opposite access policies regarding where items enter and exit.

##### Core Vocabulary & Operations
*   **Stack**: A linear collection governed by the **LIFO** rule, where all additions and removals occur exclusively at a single access point termed the **Top**.
*   **Queue**: A linear collection governed by the **FIFO** rule, where new items enter at one end (**Rear**) and processing occurs at the opposite end (**Front**).
*   **LIFO (Last-In, First-Out)**: The structural policy where the most recently added item is the first element to be extracted.
*   **FIFO (First-In, First-Out)**: The structural policy where elements are processed strictly according to their arrival sequence (oldest item first).
*   **Push**: The operation of inserting a new element onto the top of a stack. In standard Python lists, this is executed via append().
*   **Pop**: The operation of extracting and returning the top element from a stack (via pop()) or front element from a queue (via pop(0) or popleft()).
*   **Enqueue**: The operation of adding a new element to the rear of a queue. In Python, this is executed via append().
*   **Dequeue**: The operation of removing and returning the front element of a queue.
*   **Peek**: Observing the element at the top of a stack or front of a queue without removing it (e.g., using index [-1] for stacks or [0] for queues).
*   **Underflow Guard**: A protective conditional logic check that verifies a structure is non-empty before attempting a removal or peek operation, preventing runtime exceptions.
*   **collections.deque**: A specialized Python class from the standard library providing a double-ended queue implementation optimized for $O(1)$ insertions and removals at both ends.

--------------------------------------------------------------------------------

##### Side-by-Side Structural Comparison Matrix
| Feature / Spec | Stack (list) | Queue (list) | Optimized Queue (collections.deque) |
| ------ | ------ | ------ | ------ |
| **Ordering Rule** | **LIFO** (Last-In, First-Out) | **FIFO** (First-In, First-Out) | **FIFO** (First-In, First-Out) |
| **Access Point(s)** | Single access point: **Top** (Right end / index -1) | Dual access points: **Rear** (index -1) & **Front** (index 0) | Dual access points: **Right** (index -1) & **Left** (index 0) |
| **Primary Operations** | Push (append), Pop (pop), Peek ([-1]) | Enqueue (append), Dequeue (pop(0)), Peek ([0]) | Enqueue (append), Dequeue (popleft), Peek ([0]) |
| **Initialization Syntax** | stack = [] | queue = [] | from collections import deque; q = deque() |
| **Insertion Syntax & Speed** | stack.append(item) — $O(1)$ amortized | queue.append(item) — $O(1)$ amortized | q.append(item) — $O(1)$ constant time |
| **Removal Syntax & Speed** | stack.pop() — $O(1)$ constant time | queue.pop(0) — $O(n)$ linear time | q.popleft() — $O(1)$ constant time |
| **Underflow Guard Check** | if len(stack) > 0: or if stack: | if len(queue) > 0: or if queue: | if len(q) > 0: or if q: |
| **Primary Memory Layout** | Contiguous array (dynamic vector) | Contiguous array (dynamic vector) | Doubly linked list of fixed-size blocks |
| **Common Runtime Exception** | IndexError on empty pop/peek | IndexError on empty pop(0) | IndexError on empty popleft() |

--------------------------------------------------------------------------------

<a id="2-real-world-mental-models--conceptual-mapping---week-2"></a>
#### 2. Real-World Mental Models & Conceptual Mapping
To reliably predict data structure behavior, developers rely on visual physical analogies that map access restrictions directly to physical constraints.
##### 1. The Stack Analogy: Heavy Buffet Plate Dispenser & Book Pile
*   **Physical Constraint**: Plates are loaded into a spring-loaded vertical cylinder. You can only place a new plate on top of the pile, and you can only lift off the topmost plate.
*   **Software Mapping**: Software features like **Text Editor Undo Histories** (Ctrl+Z) and **Browser Back Buttons** place each user state on top of a history stack. Undoing an action extracts the most recent state first.

```
       STACK (LIFO) STRUCTURAL DIAGRAM
       
          PUSH (append)     POP (pop)
                \              ^
                 v             |
             +--------------------+
             |   Item C (Top)     |  <-- Index -1 (Most Recent)
             +--------------------+
             |   Item B           |  <-- Index 1
             +--------------------+
             |   Item A (Bottom)  |  <-- Index 0 (Oldest)
             +--------------------+
             [ Closed Bottom Base ]
```

--------------------------------------------------------------------------------

##### 2. The Queue Analogy: Coffee Shop & Ice-Cream Truck Line
*   **Physical Constraint**: Customers arrive and join the back of the line (Rear). The barista serves the customer at the front of the line (Front). Jumping ahead or serving out of order breaks fairness.
*   **Software Mapping**: Systems like **Printer Spoolers**, **Help Desk Ticketing**, and **Game Server Matchmaking Lobbies** process jobs in the exact order they arrive.

```
       QUEUE (FIFO) STRUCTURAL DIAGRAM
       
   DEQUEUE (popleft / pop(0))                 ENQUEUE (append)
          <-- FRONT                              REAR <--
   +------------+------------+------------+------------+
   | Customer A | Customer B | Customer C | Customer D |
   +------------+------------+------------+------------+
      Index 0      Index 1      Index 2      Index 3
```

--------------------------------------------------------------------------------

##### 3. The Hybrid Analogy: Adventurers in Line with Item Backpacks
*   **Physical Constraint**: Adventurers wait in a single-file FIFO line to enter a dungeon portal. Each adventurer wears a backpack operated as a LIFO stack (items packed last are on top and pulled out first).
*   **Software Mapping**: Multi-level software architecture where outer workflows are managed via queue queues, while local sub-task contexts manage state via internal stacks.

--------------------------------------------------------------------------------

<a id="3-idiomatic-python-implementation--state-tracing---week-2"></a>
#### 3. Idiomatic Python Implementation & State Tracing
##### 3.1 Stack Operations using Python Lists
When mapping a stack to a standard Python list, the **rightmost element (index -1) is treated as the Top**.
```python
# Initialize an empty stack list
undo_stack = []  # State: [], len: 0

# --- PUSH OPERATIONS ---
# append() adds elements to the right end (Top) of the list
undo_stack.append("Type 'H'")     # State: ["Type 'H'"], Top: "Type 'H'"
undo_stack.append("Type 'Hi'")    # State: ["Type 'H'", "Type 'Hi'"], Top: "Type 'Hi'"
undo_stack.append("Type 'Hello'") # State: ["Type 'H'", "Type 'Hi'", "Type 'Hello'"]

# --- PEEK OPERATION ---
# Access index -1 under an underflow guard check
if undo_stack:
    current_top = undo_stack[-1]
    print(f"Current Top State: {current_top}")
    # Terminal Output: Current Top State: Type 'Hello'
    # State remains unchanged: ["Type 'H'", "Type 'Hi'", "Type 'Hello'"]

# --- POP OPERATIONS ---
# pop() removes and returns the rightmost element (Top)
if undo_stack:
    last_action = undo_stack.pop()
    print(f"Undone Action: {last_action}")
    # Terminal Output: Undone Action: Type 'Hello'
    # State after pop: ["Type 'H'", "Type 'Hi'"], len: 2

if undo_stack:
    last_action = undo_stack.pop()
    print(f"Undone Action: {last_action}")
    # Terminal Output: Undone Action: Type 'Hi'
    # State after pop: ["Type 'H'"], len: 1
```

--------------------------------------------------------------------------------

##### 3.2 List-Based Queue Operations
When implementing a queue with a standard Python list, elements enter at the rear via append() and exit from the front (index 0) via pop(0).
```python
# Initialize an empty queue list
print_queue = []  # State: [], len: 0

# --- ENQUEUE OPERATIONS ---
print_queue.append("Doc1.pdf")  # State: ["Doc1.pdf"]
print_queue.append("Doc2.pdf")  # State: ["Doc1.pdf", "Doc2.pdf"]
print_queue.append("Doc3.pdf")  # State: ["Doc1.pdf", "Doc2.pdf", "Doc3.pdf"]

# --- PEEK FRONT ---
if len(print_queue) > 0:
    next_job = print_queue[0]
    print(f"Next job to print: {next_job}")
    # Terminal Output: Next job to print: Doc1.pdf
    # State remains unchanged: ["Doc1.pdf", "Doc2.pdf", "Doc3.pdf"]

# --- DEQUEUE OPERATIONS ---
# pop(0) extracts index 0 and shifts all remaining elements left by 1 index
if print_queue:
    processed_job = print_queue.pop(0)
    print(f"Printed: {processed_job}")
    # Terminal Output: Printed: Doc1.pdf
    # State after dequeue: ["Doc2.pdf", "Doc3.pdf"], len: 2

if print_queue:
    processed_job = print_queue.pop(0)
    print(f"Printed: {processed_job}")
    # Terminal Output: Printed: Doc2.pdf
    # State after dequeue: ["Doc3.pdf"], len: 1
```

--------------------------------------------------------------------------------

##### 3.3 Module Imports & High-Performance collections.deque
Standard lists require $O(n)$ linear time for pop(0) because Python must shift every remaining item in memory leftward by one memory slot. The collections.deque class provides an $O(1)$ constant time popleft() implementation.
###### Importing Syntax Variants
```python
# Variant 1: Full module import (requires prefixing)
import collections
service_queue = collections.deque()

# Variant 2: Specific tool import (direct class usage)
from collections import deque
ticket_queue = deque()
```

###### High-Performance Deque Code Walkthrough
```python
from collections import deque

# Initialize double-ended queue
help_desk = deque()  # State: deque([]), len: 0

# Enqueue customers at rear (right end)
help_desk.append("Ticket #101")  # State: deque(['Ticket #101'])
help_desk.append("Ticket #102")  # State: deque(['Ticket #101', 'Ticket #102'])
help_desk.append("Ticket #103")  # State: deque(['Ticket #101', 'Ticket #102', 'Ticket #103'])

# High-speed Dequeue from front (left end) via popleft()
if help_desk:
    active_ticket = help_desk.popleft()  # O(1) time removal
    print(f"Serving: {active_ticket}")
    # Terminal Output: Serving: Ticket #101
    # State after popleft: deque(['Ticket #102', 'Ticket #103'])

# Deque also supports stack operations on the left side
help_desk.appendleft("VIP Ticket #999")  # Priority insertion at front
# State after appendleft: deque(['VIP Ticket #999', 'Ticket #102', 'Ticket #103'])

served_vip = help_desk.popleft()
print(f"Served Priority: {served_vip}")
# Terminal Output: Served Priority: VIP Ticket #999
# State after popleft: deque(['Ticket #102', 'Ticket #103'])
```

--------------------------------------------------------------------------------

<a id="4-defensive-programming--common-traps---week-2"></a>
#### 4. Defensive Programming & Common Traps
When building state-driven software, unhandled boundary conditions cause runtime crashes or silent data corruption. Below are the four primary traps and their defensive solutions.
##### Trap 1: Underflow Exception (IndexError)
Attempting to pop or peek an empty collection causes Python to halt with an IndexError.
```python
# INCORRECT: Popping or peeking without checking collection length
empty_stack = []
item = empty_stack.pop()
# RUNTIME ERROR: IndexError: pop from empty list

# CORRECT: Implementing an explicit underflow guard
empty_stack = []

# Option A: Length check guard
if len(empty_stack) > 0:
    item = empty_stack.pop()
else:
    print("Underflow prevented: Stack is empty.")

# Option B: Implicit boolean evaluation guard (Pythonic)
if empty_stack:
    item = empty_stack.pop()
else:
    print("Underflow prevented: Stack is empty.")
```

--------------------------------------------------------------------------------

##### Trap 2: Overwriting Collection Reference with None (AttributeError)
In Python, standard list methods like .append() and .reverse() modify the collection **in-place** and return None. Assigning the result back to the variable destroys the collection.
```python
# INCORRECT: Assigning the return value of an in-place method
data_stack = [1, 2, 3]
data_stack = data_stack.append(4)  # append() returns None!
# data_stack is now None

data_stack.append(5)
# RUNTIME ERROR: AttributeError: 'NoneType' object has no attribute 'append'

# CORRECT: Call in-place methods without re-assigning
data_stack = [1, 2, 3]
data_stack.append(4)  # Modifies data_stack directly
# data_stack is now [1, 2, 3, 4]
```

--------------------------------------------------------------------------------

##### Trap 3: Calling popleft() on Standard Python Lists (AttributeError)
popleft() is a method exclusive to collections.deque objects. Calling it on a list causes a method lookup failure.
```python
# INCORRECT: Invoking deque-specific methods on standard lists
standard_list = ["A", "B", "C"]
first_item = standard_list.popleft()
# RUNTIME ERROR: AttributeError: 'list' object has no attribute 'popleft'

# CORRECT: Convert list to deque or use pop(0)
from collections import deque

# Solution A: Convert to deque
deque_obj = deque(["A", "B", "C"])
first_item = deque_obj.popleft()  # Returns "A"

# Solution B: Use list method pop(0)
standard_list = ["A", "B", "C"]
first_item = standard_list.pop(0)  # Returns "A"
```

--------------------------------------------------------------------------------

##### Trap 4: Module Name Scope & Namespace Ambiguity (NameError)
Using the general import module statement requires prefixing function calls with the module name. Calling imported functions directly causes a NameError.
```python
# INCORRECT: Calling function directly after general module import
import math
value = sqrt(16)
# RUNTIME ERROR: NameError: name 'sqrt' is not defined

# CORRECT: Use module prefix OR specific tool import
# Solution A: Prefix with module name
import math
value = math.sqrt(16)  # Evaluates to 4.0

# Solution B: Specific function import
from math import sqrt
value = sqrt(16)       # Evaluates to 4.0
```

--------------------------------------------------------------------------------

<a id="5-python-memory-mechanics-references--scope---week-2"></a>
#### 5. Python Memory Mechanics, References & Scope
Understanding how Python manages variables in memory is critical when passing data structures into functions.
##### 1. Variables as Object References (Binding vs Assignment)
In Python, variables are not named memory slots containing values. Instead, variables are **names bound to object memory addresses** residing in heap memory.
*   **Immutable Objects** (e.g., integers, strings, tuples): Modifying the value creates a brand-new object at a new memory address.
*   **Mutable Objects** (e.g., lists, dictionaries, deque objects): Modifying the object alters the underlying data structure in-place at its existing memory address.

##### 2. Passing Data Structures to Functions
When a list or deque is passed as an argument to a function, Python passes the **object reference by value**. Both the caller variable and the function parameter point to the **exact same memory address**.
```python
def process_queue(q):
    # q receives a reference pointing to the caller's list object
    if q:
        removed = q.pop(0)  # Modifies the caller's object directly in heap memory
        print(f"Function removed: {removed}")
    # No return statement required!

# Caller scope
my_list = ["Task 1", "Task 2"]
process_queue(my_list)
print(f"Caller list after function call: {my_list}")
# Terminal Output:
# Function removed: Task 1
# Caller list after function call: ['Task 2']
```

--------------------------------------------------------------------------------

##### Memory Address & Namespace ASCII Diagram
```
   CALLER NAMESPACE (Global Scope)               HEAP MEMORY
   +--------------------+                       +----------------------------------+
   | Variable: my_list  | --------------------> | Address ID: 0x7f8a3c00           |
   +--------------------+                       | Type: list                       |
                                                | Value: ["Task 1", "Task 2"]      |
   FUNCTION FRAME (process_queue Scope)         +----------------------------------+
   +--------------------+                                 ^
   | Parameter: q       | --------------------------------+
   +--------------------+
   
   * Notice: Both `my_list` and `q` point to the exact same Heap Memory Address ID.
   * Calling q.pop(0) mutates the list object at ID 0x7f8a3c00 directly.
```

--------------------------------------------------------------------------------

<a id="6-practical-integration--mini-case-study---week-2"></a>
#### 6. Practical Integration / Mini Case Study
##### Comprehensive System: Dungeon Adventurer & Inventory Dispatcher
The following script integrates all concepts from Week 2:
1. collections.deque manages an outer **FIFO Queue** of Adventurers waiting to enter a dungeon.
2. Standard Python list objects act as inner **LIFO Stacks** representing each adventurer's item backpack.
3. In-place functional operations process characters and items sequentially while applying underflow guards.

```python
"""
Dungeon Adventurer & Inventory Dispatch Simulation
Demonstrating FIFO Queue dispatch combined with LIFO Stack inventory logic.
"""

from collections import deque


def create_adventurer(name, equipment_list):
    """
    Creates an adventurer representation with an inventory stack.
    """
    return {
        "name": name,
        "backpack": equipment_list  # List acting as LIFO stack
    }


def dispatch_dungeon_party():
    # 1. Initialize FIFO Adventurer Queue using deque
    dungeon_queue = deque()
    
    # Enqueue adventurers into waiting queue (FIFO)
    dungeon_queue.append(create_adventurer("Thorin", ["Torch", "Rope", "Iron Shield"]))
    dungeon_queue.append(create_adventurer("Lyra", ["Health Potion", "Spellbook"]))
    
    print("=== DUNGEON PARTY DISPATCH STARTED ===")
    print(f"Total adventurers queued: {len(dungeon_queue)}\n")
    
    # 2. Process Adventurer Queue (FIFO Order)
    while dungeon_queue:
        # Extract next adventurer from front of queue
        current_hero = dungeon_queue.popleft()
        hero_name = current_hero["name"]
        backpack_stack = current_hero["backpack"]
        
        print(f"--> Adventurer {hero_name} steps through the portal!")
        
        # 3. Process Backpack Inventory (LIFO Order)
        print(f"    {hero_name}'s inventory stack state: {backpack_stack}")
        
        # Hero pulls top item from backpack stack to handle trap
        if backpack_stack:
            top_item = backpack_stack.pop()  # LIFO removal (rightmost element)
            print(f"    {hero_name} equips top item from backpack: '{top_item}'")
            print(f"    Remaining backpack items: {backpack_stack}")
        else:
            print(f"    {hero_name}'s backpack is empty!")
            
        print("-" * 50)

    print("\n=== ALL ADVENTURERS DISPATCHED SAFELY ===")


# Run the integration simulation
if __name__ == "__main__":
    dispatch_dungeon_party()
```

--------------------------------------------------------------------------------

##### Executable Console Output Trace
```text
=== DUNGEON PARTY DISPATCH STARTED ===
Total adventurers queued: 2

--> Adventurer Thorin steps through the portal!
    Thorin's inventory stack state: ['Torch', 'Rope', 'Iron Shield']
    Thorin equips top item from backpack: 'Iron Shield'
    Remaining backpack items: ['Torch', 'Rope']
--------------------------------------------------
--> Adventurer Lyra steps through the portal!
    Lyra's inventory stack state: ['Health Potion', 'Spellbook']
    Lyra equips top item from backpack: 'Spellbook'
    Remaining backpack items: ['Health Potion']
--------------------------------------------------

=== ALL ADVENTURERS DISPATCHED SAFELY ===
```

--------------------------------------------------------------------------------

<a id="7-step-by-step-code-tracing-challenges--diagnostics---week-2"></a>
#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Stack Undo-Redo & Double-Pop Trace
###### Code Snippet
```python
history = []
history.append("Action 1")
history.append("Action 2")
history.append("Action 3")

# First Undo
act1 = history.pop()

# New Action Action 4
history.append("Action 4")

# Double Undo Check
if len(history) >= 2:
    undo_a = history.pop()
    undo_b = history.pop()

print(f"history: {history}")
print(f"undo_a: {undo_a}")
print(f"undo_b: {undo_b}")
```

###### Line-by-Line State Trace
1. history = [] $ightarrow$ history: []
2. history.append("Action 1") $ightarrow$ history: ["Action 1"]
3. history.append("Action 2") $ightarrow$ history: ["Action 1", "Action 2"]
4. history.append("Action 3") $ightarrow$ history: ["Action 1", "Action 2", "Action 3"]
5. act1 = history.pop() $ightarrow$ removes "Action 3", history: ["Action 1", "Action 2"], act1: "Action 3"
6. history.append("Action 4") $ightarrow$ history: ["Action 1", "Action 2", "Action 4"]
7. if len(history) >= 2: $ightarrow$ len(history) is 3 (3 >= 2 evaluates to True)
8. undo_a = history.pop() $ightarrow$ removes "Action 4", history: ["Action 1", "Action 2"], undo_a: "Action 4"
9. undo_b = history.pop() $ightarrow$ removes "Action 2", history: ["Action 1"], undo_b: "Action 2"

###### Terminal Output
```text
history: ['Action 1']
undo_a: Action 4
undo_b: Action 2
```

--------------------------------------------------------------------------------

##### Challenge B: Dual-Ended List Queue Manipulation
###### Code Snippet
```python
q = ["Alpha", "Beta", "Gamma"]
q.append("Delta")
item_x = q.pop(0)
q.append(item_x)
item_y = q.pop(0)

print(f"Final Queue: {q}")
print(f"item_x: {item_x}")
print(f"item_y: {item_y}")
```
###### Line-by-Line State Trace
1. q = ["Alpha", "Beta", "Gamma"] $ightarrow$ q: ["Alpha", "Beta", "Gamma"]
2. q.append("Delta") $ightarrow$ q: ["Alpha", "Beta", "Gamma", "Delta"]
3. item_x = q.pop(0) $ightarrow$ removes index 0 ("Alpha"), q: ["Beta", "Gamma", "Delta"], item_x: "Alpha"
4. q.append(item_x) $ightarrow$ appends "Alpha", q: ["Beta", "Gamma", "Delta", "Alpha"]
5. item_y = q.pop(0) $ightarrow$ removes index 0 ("Beta"), q: ["Gamma", "Delta", "Alpha"], item_y: "Beta"

###### Terminal Output
```text
Final Queue: ['Gamma', 'Delta', 'Alpha']
item_x: Alpha
item_y: Beta
```

--------------------------------------------------------------------------------

##### Challenge C: High-Performance collections.deque Trace
###### Code Snippet
```python
from collections import deque

d = deque(["Task A", "Task B"])
d.append("Task C")
d.appendleft("Task Zero")

val_left = d.popleft()
val_right = d.pop()

print(f"Deque state: {list(d)}")
print(f"val_left: {val_left}")
print(f"val_right: {val_right}")
```
###### Line-by-Line State Trace
1. d = deque(["Task A", "Task B"]) $ightarrow$ d: deque(['Task A', 'Task B'])
2. d.append("Task C") $ightarrow$ d: deque(['Task A', 'Task B', 'Task C'])
3. d.appendleft("Task Zero") $ightarrow$ d: deque(['Task Zero', 'Task A', 'Task B', 'Task C'])
4. val_left = d.popleft() $ightarrow$ removes left element ("Task Zero"), d: deque(['Task A', 'Task B', 'Task C']), val_left: "Task Zero"
5. val_right = d.pop() $ightarrow$ removes right element ("Task C"), d: deque(['Task A', 'Task B']), val_right: "Task C"

###### Terminal Output
```text
Deque state: ['Task A', 'Task B']
val_left: Task Zero
val_right: Task C
```

--------------------------------------------------------------------------------

##### Challenge D: Function Scope & Mutable Reference Side-Effect Trace
###### Code Snippet
```python
def process_data(stack_ref, queue_ref):
    if stack_ref:
        popped = stack_ref.pop()
        queue_ref.append(popped)

s = [10, 20, 30]
q = [100, 200]

process_data(s, q)
process_data(s, q)

print(f"s: {s}")
print(f"q: {q}")
```
###### Line-by-Line State Trace
1. s = [10, 20, 30], q = [100, 200]
2. First call: process_data(s, q)
    *  stack_ref points to s, queue_ref points to q.
    *  popped = stack_ref.pop() $ightarrow$ removes 30 from s. s is now [10, 20].
    *  queue_ref.append(30) $ightarrow$ appends 30 to q. q is now [100, 200, 30].
3. Second call: process_data(s, q)
    *  popped = stack_ref.pop() $ightarrow$ removes 20 from s. s is now [10].
    *  queue_ref.append(20) $ightarrow$ appends 20 to q. q is now [100, 200, 30, 20].
###### Terminal Output
```text
s: [10]
q: [100, 200, 30, 20]
```

---

## PART III: WEEK 3 - Master Reference: Algorithmic Complexity, Data Structures & Optimization

### PY102 - Week 3 Master Reference: Algorithmic Complexity, Data Structures & Optimization
*This Master Reference Document synthesizes all core concepts, mental models, memory mechanics, algorithmic complexities, and code execution traces from PY102 Week 3 into an authoritative, self-contained reference guide. Designed for software engineering students and technical practitioners, it bridges abstract computational theory with Python's internal memory management and production refactoring patterns.*

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-3)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-3)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-3)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-3)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-3)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-3)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-3)

--------------------------------------------------------------------------------

<a id="1-abstract-foundations--core-theory---week-3"></a>
#### 1. Abstract Foundations & Core Theory
##### Formal Terminology & Definitions
*   **Algorithm Correctness**: The mandatory baseline property ensuring an algorithm produces accurate, mathematically sound outputs across all valid input domain instances. Correctness is an absolute prerequisite; speed without correctness is useless.
*   **Algorithmic Efficiency**: The quantitative measure of computational resource consumption (CPU step operations and RAM memory allocation) required by an algorithm as a function of the input size ($n$).
*   **Code Readability**: The structural clarity, naming intent, and self-documenting maintainability of source code. Highly readable code minimizes cognitive load for engineering teams during debugging and maintenance.
*   **Big O Notation**: A formal asymptotic framework that categorizes the upper bound (worst-case scenario) of an algorithm's growth rate as input size $n$ approaches infinity. Big O ignores constant multipliers, coefficient offsets, and lower-order terms.
*   **Time Complexity**: The mathematical function describing how an algorithm's execution step count grows relative to input size $n$.
*   **Space Complexity**: The mathematical function describing how an algorithm's auxiliary memory footprint scales relative to input size $n$.
*   **Constant Time ($O(1)$)**: Workload remains entirely fixed regardless of input scale $n$. Examples include direct list index access (lst[i]) and dictionary key lookups (dct[key]).
*   **Linear Time ($O(n)$)**: Workload grows in direct 1:1 proportion with input size $n$. Examples include single-pass iteration over a list or searching for an unindexed item.
*   **Quadratic Time ($O(n^2)$)**: Workload grows proportionally to the square of input size $n$. Examples include nested loops iterating over the same $n$-element collection.
*   **Amortized $O(1)$**: The guaranteed average time per operation over a sequence of operations, accounting for rare, high-cost maintenance events (such as dynamic array resizing during list appends).
*   **Invariant**: An expression or logical condition that remains strictly unchanged throughout the execution of a loop or algorithmic phase.
*   **Hash Table**: The underlying probabilistic data structure powering Python dictionaries and sets, mapping keys to memory array indices via a hash function to enable $O(1)$ average-time retrieval.

--------------------------------------------------------------------------------

##### Core Data Structure & Complexity Comparison Matrix
| Feature / Spec | Python List (list) | Python Dictionary (dict) | Double-Ended Queue (deque) |
| ------ | ------ | ------ | ------ |
| **Definition** | Ordered, index-based mutable sequence stored internally as a contiguous dynamic array of object pointers. | Unordered (insertion-ordered) key-value mapping backed by a sparse hash table with hash-bucket indexing. | Doubly linked list structure optimized for fast sequential access and mutations at both endpoints. |
| **Syntax / Delimiters** | Square brackets [val1, val2] or list() | Curly braces {key: val} or dict() | collections.deque([val1, val2]) |
| **Access by Index / Key** | lst[i]: $O(1)$ constant time direct index calculation. | dct[key]: $O(1)$ average time hash lookup. | Endpoints dq[0], dq[-1]: $O(1)$. Random index dq[i]: $O(n)$ pointer traversal. |
| **Search by Value** | val in lst: $O(n)$ linear scan through contiguous array pointers. | val in dct.values(): $O(n)$ linear scan over dictionary values. | val in dq: $O(n)$ linear traversal across doubly linked nodes. |
| **Insertion / Addition** | lst.append(x): Amortized $O(1)$. lst.insert(i, x): $O(n)$ due to element shifting. | dct[key] = val: $O(1)$ average time hash assignment and collision resolution. | dq.append(x) (right) or dq.appendleft(x) (left): Both $O(1)$ constant time. |
| **Deletion / Removal** | lst.pop() (end): $O(1)$. lst.pop(i) / lst.pop(0): $O(n)$ due to element shifting. | del dct[key] / dct.pop(key): $O(1)$ average time hash slot clearing. | dq.pop() (right) or dq.popleft() (left): Both $O(1)$ constant time. |
| **Type Invariants** | Mutable. Elements can be any data type. Indices must be integers. | Mutable container. Keys must be immutable/hashable; values can be any type. | Mutable. Elements can be any data type; endpoint pointers maintained. |
| **Common Runtime Exception** | IndexError: Out-of-bounds index access or popping from an empty list. | KeyError: Accessing missing key directly without .get() or in check. | IndexError: Popping from an empty deque or invalid index offset. |
| **Primary Performance Bottleneck** | Scanning for values ($O(n)$) or mutating front/middle elements ($O(n)$ shifting). | High memory footprint; hash collisions causing theoretical $O(n)$ worst-case lookup. | Random middle indexing is $O(n)$ requiring traversal from closest endpoint node. |

--------------------------------------------------------------------------------

<a id="2-real-world-mental-models--conceptual-mapping---week-3"></a>
#### 2. Real-World Mental Models & Conceptual Mapping
##### Analogy 1: The Cafeteria Tray Stack vs. The Ticket Booth Line
*   **Stack (LIFO - Last-In, First-Out)**: Picture a spring-loaded cafeteria tray dispenser. Clean trays are pushed onto the top of the stack (append()). Customers always take the top tray off the stack (pop()). The last tray added is the first tray removed. Operations at the top take constant time $O(1)$ because no other trays need to move.
*   **Queue (FIFO - First-In, First-Out)**: Picture a single-file line at a theater ticket booth. The first person to enter the line (append()) is the first person served (popleft()).
    *   *Inefficient Queue (Standard List)*: If you use a Python list for a queue, removing the front person via list.pop(0) forces *every single person behind them* to take one step forward to fill the empty space. For $n$ people, this requires $n-1$ shifts ($O(n)$ linear time).
    *   *Efficient Queue (`collections.deque`)*: Using deque.popleft() opens the front gate without requiring anyone behind to move. The booth operator simply shifts their focus to the next linked node ($O(1)$ constant time).

```
STRICT LIFO STACK (Python List)
   [Push / Pop Endpoint]  <--->  [ TRAY C (Top) ]
                                 [ TRAY B       ]
                                 [ TRAY A (Base)]

EFFICIENT FIFO QUEUE (collections.deque)
   [Left Endpoint]                                 [Right Endpoint]
   (Popleft O(1))  <--- [Node 1] <-> [Node 2] <-> [Node 3] <--- (Append O(1))
```

--------------------------------------------------------------------------------

##### Analogy 2: The Street Address Index vs. The Phone Book Hash
*   **List Indexing ($O(1)$)**: Imagine a suburban street where houses are numbered strictly from 0 to 99 on a uniform grid. To visit House #42, you drive directly to block 42 without checking Houses 0 through 41.
*   **List Value Search ($O(n)$)**: If you do not know the house number and are looking for "John Smith", you must knock on every door starting at House #0 until you find him ($O(n)$ worst-case scan).
*   **Dictionary Hash Table ($O(1)$ Average)**: Imagine a phone book with an instant index tab. When you search for key "John Smith", a hash algorithm immediately converts "John Smith" into a page number (bucket index). You flip straight to that page and read his phone number ($O(1)$ key lookup).

```
LIST LINEAR SEARCH vs DICTIONARY HASH LOOKUP

List Scan (Searching for "Target"):
Index 0         Index 1         Index 2         Index n-1
[ "Alpha" ] ->  [ "Beta" ]  ->  [ "Target" ] -> [ ... ]     (Scans 1-by-1: O(n))

Dictionary Hash Lookup:
Key: "Target" ---> Hash Function: hash("Target") % size ---> Bucket 2 ---> Value: 99  (Direct jump: O(1))
```

--------------------------------------------------------------------------------

##### Analogy 3: Assembly Line Blueprint vs. Redundant Inspection (Invariant Extraction)
*   **Unoptimized Loop ($O(n^2)$)**: An assembly line inspector picks up a part, measures the room temperature, recalculates the factory tax rate formula, and then inspects the part. Repeating environmental calculations for every single item wastes massive energy.
*   **Optimized Loop with Invariant Extraction ($O(n)$)**: The inspector calculates the factory tax rate once before the conveyer belt starts running (storing it in a local variable), then uses that fixed result for every item on the line.

--------------------------------------------------------------------------------

<a id="3-idiomatic-python-implementation--state-tracing---week-3"></a>
#### 3. Idiomatic Python Implementation & State Tracing
##### 3.1 Step Counting and Big O Complexity Classes
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

--------------------------------------------------------------------------------

##### 3.2 List vs. Dictionary Search Refactoring
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

--------------------------------------------------------------------------------

##### 3.3 Sequential Collections: Stacks (list) vs. Queues (collections.deque)
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

--------------------------------------------------------------------------------

##### 3.4 Invariant Extraction & Single-Pass Refactoring Patterns
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

--------------------------------------------------------------------------------

<a id="4-defensive-programming--common-traps---week-3"></a>
#### 4. Defensive Programming & Common Traps
##### Trap 1: IndexError on Out-of-Bounds Indexing or Empty Sequence Removal
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

--------------------------------------------------------------------------------

##### Trap 2: KeyError on Direct Dictionary Key Access
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

--------------------------------------------------------------------------------

##### Trap 3: The Hidden $O(n^2)$ Loop Trap (val in list or list.pop(0) inside a loop)
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

--------------------------------------------------------------------------------

##### Trap 4: Mutability and Unhashable Key Traps (TypeError: unhashable type: 'list')
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

--------------------------------------------------------------------------------

<a id="5-python-memory-mechanics-references--scope---week-3"></a>
#### 5. Python Memory Mechanics, References & Scope
##### Dynamic Typing & Object Binding
In Python, variables are **not typed memory boxes**. Instead, variable names are simply symbolic references (pointers) bound to typed objects residing in **Heap Memory**.
*   **Assignment (`x = 10`):** Binds the variable name x in the current **Namespace** to an integer object 10 in Heap Memory.
*   **Reassignment (`x = "Hello"`):** Changes the reference pointer of x to point to a string object "Hello". The original integer object 10 is left for garbage collection if no other references exist.

##### Contiguous Pointer Arrays vs. Sparse Hash Buckets
1.  **Python List (`PyListObject`):**
    *  Consists of a contiguous block of **memory addresses (pointers)** pointing to the actual elements scattered in heap memory.
    *  Indexing (lst[i]) multiplies the index $i$ by pointer size (8 bytes) and jumps directly to that memory offset ($O(1)$).
    *  Modifying middle elements (lst.insert(0, x) or lst.pop(0)) requires shifting all downstream pointer memory blocks via memmove(), resulting in $O(n)$ overhead.
2.  **Python Dictionary (`PyDictObject`):**
    *  Consists of a sparse hash table array.
    *  Executing dct[key] runs hash(key), maps the resulting integer to a table bucket index, and retrieves the stored value pointer.
    *  Hash collisions are resolved using open addressing with quadratic probing, preserving $O(1)$ average access.

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

--------------------------------------------------------------------------------

<a id="6-practical-integration--mini-case-study---week-3"></a>
#### 6. Practical Integration / Mini Case Study
##### High-Throughput E-Commerce Log & Queue Processor
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

--------------------------------------------------------------------------------

<a id="7-step-by-step-code-tracing-challenges--diagnostics---week-3"></a>
#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Nested Loops with Early Exit (break) and Best-Case vs. Worst-Case Evaluation
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

--------------------------------------------------------------------------------

##### Challenge B: Hidden $O(n^2)$ Complexity vs. Linear Refactoring Trace
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

--------------------------------------------------------------------------------

##### Challenge C: Stack and Queue Pipeline Interleaved State Trace
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

--------------------------------------------------------------------------------

##### Challenge D: Invariant Extraction and Single-Pass Ratio Trace
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

---

## PART IV: WEEK 4 - Master Reference: Searching and Sorting Algorithms in Python

### PY102 - Week 4 Master Reference: Searching and Sorting Algorithms in Python
*This document synthesizes all core concepts, mental models, memory mechanics, algorithmic bounds, and code traces from Week 4 into an authoritative, publication-grade reference guide.*

--------------------------------------------------------------------------------

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory---week-4)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping---week-4)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing---week-4)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps---week-4)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope---week-4)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study---week-4)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics---week-4)

--------------------------------------------------------------------------------

<a id="1-abstract-foundations--core-theory---week-4"></a>
#### 1. Abstract Foundations & Core Theory
Computer science organizes operations on data collections into fundamental paradigms. A **search task** is defined as locating a specific **target** element within a broader **collection** based on a matching criteria. Conversely, a **sorting task** rearranges all elements within a collection according to a specified total ordering.

##### Primary Terminology & Keywords
*   **Collection:** The underlying data structure (such as a Python list or database table) containing the target items.
*   **Target:** The specific value, key, or property condition sought during a search operation.
*   **Linear Search (Full Scan):** Sequential inspection of elements from index $0$ to $n-1$, running in worst-case $O(n)$ time.
*   **Binary Search:** A divide-and-conquer strategy that repeatedly halves a sorted search space, running in logarithmic $O(\log n)$ time.
*   **Logarithmic Complexity ($O(\log n)$):** Algorithmic efficiency wherein each operational step eliminates approximately half of the remaining problem domain.
*   **In-Place Mutation:** Direct modification of an existing object's memory without allocating a new primary data structure.
*   **Algorithm Stability:** A property of sorting algorithms that preserves the relative input order of records with equal keys.
*   **Timsort:** Python's default hybrid sorting algorithm, exhibiting $O(n \log n)$ time complexity.

--------------------------------------------------------------------------------

##### Side-by-Side Comparison Matrix
| Feature / Spec | Linear Search | Binary Search | Bubble Sort | Insertion Sort | Timsort (sorted() / .sort()) |
| ------ | ------ | ------ | ------ | ------ | ------ |
| **Primary Definition** | Sequential element-by-element scan from start to end | Divide-and-conquer index halving on sorted data | Repeated adjacent neighbor comparison and swapping | Building a sorted left sub-list by shifting larger items right | Hybrid merge/insertion sort built into Python C-extension |
| **Syntax / Delimiters** | for index, item in enumerate(lst): | while low <= high: with mid = (low + high) // 2 | Nested for loops comparing arr[j] and arr[j+1] | Outer for loop with inner while pos >= 0 and arr[pos] > key: | sorted(iterable, key=..., reverse=...) or lst.sort(...) |
| **Best-Case Complexity** | $O(1)$ (target is at index 0) | $O(1)$ (target is at initial midpoint) | $O(n)$ (with optimized early-exit flag on sorted array) | $O(n)$ (nearly or fully sorted array requiring zero shifts) | $O(n)$ (already sorted or nearly sorted array) |
| **Worst-Case Complexity** | $O(n)$ (target at end or missing) | $O(\log n)$ (target missing or at extreme boundaries) | $O(n^2)$ (reverse-sorted array requiring maximum swaps) | $O(n^2)$ (reverse-sorted array requiring maximum shifts) | $O(n \log n)$ (randomized or adversarial distribution) |
| **Space Complexity** | $O(1)$ auxiliary space | $O(1)$ auxiliary space (iterative version) | $O(1)$ auxiliary space (in-place) | $O(1)$ auxiliary space (in-place) | $O(n)$ auxiliary space |
| **Data Invariants** | Unsorted or sorted collections | **Strictly required:** Collection MUST be pre-sorted | Operates on unsorted collections | Operates on unsorted collections | Operates on unsorted collections |
| **Mutability Behavior** | Read-only (non-mutating) | Read-only (non-mutating) | Mutates list in-place | Mutates list in-place (or operate on copy) | sorted() returns new list; .sort() mutates list in-place |
| **Common Trap** | Unnecessary $O(n)$ scans when direct dict lookups exist | Executing on unsorted data leading to incorrect exclusions | Extreme performance penalty ($O(n^2)$) on large datasets | Confusing key extraction with element substitution | Assigning .sort() return value (None) to variable |

--------------------------------------------------------------------------------

<a id="2-real-world-mental-models--conceptual-mapping---week-4"></a>
#### 2. Real-World Mental Models & Conceptual Mapping
##### Analogy 1: The Phone Book Search (Linear vs. Binary Search)
Searching through an unsorted binder of 1,000 documents requires inspecting each sheet sequentially from page 1 to 1,000. If the phone book is sorted alphabetically (A to Z), locating a target like "Miller" does not start on page 1. Instead, you open to the midpoint. Observing "Smith" immediately informs you that "Miller" precedes "Smith", allowing you to discard the entire second half. Repeating this halving operation reduces 1,000 pages to roughly 10 inspections.

--------------------------------------------------------------------------------

##### Analogy 2: Playing Card Arrangement (Insertion Sort)
When holding a hand of playing cards, you keep a sorted subset in your left hand. As you draw a new card with your right hand, you compare it against the sorted left hand from right to left. You shift larger cards one position right to create a slot ("hole") and insert the new card in its proper position.

```
Insertion Sort Index Mechanics (Card Sliding Analogy):

Initial Unsorted Array: [ 5 | 2 | 4 | 6 | 1 | 3 ]
                         ^   ^
                    Sorted   Key to Insert (2)

Pass 1 (Key = 2):
  Compare 2 with 5 -> 5 is greater.
  Shift 5 right:       [ 5 | 5 | 4 | 6 | 1 | 3 ]
  Insert Key into slot:[ 2 | 5 | 4 | 6 | 1 | 3 ]
                        <----->
                        Sorted Sub-list

Pass 2 (Key = 4):
  Compare 4 with 5 -> 5 is greater.
  Shift 5 right:       [ 2 | 5 | 5 | 6 | 1 | 3 ]
  Compare 4 with 2 -> 2 is smaller (stop shift).
  Insert Key into slot:[ 2 | 4 | 5 | 6 | 1 | 3 ]
                        <--------->
                        Sorted Sub-list
```

--------------------------------------------------------------------------------

##### Analogy 3: Bubble Sort Neighbor Exchange
Imagine physical weights lined up on a beam. You step through from left to right, comparing adjacent pairs. If a heavier weight is to the left of a lighter one, you swap their physical positions. Over a full pass from left to right, the heaviest remaining weight "bubbles" up to its final destination at the rightmost available index.

```
Binary Search Low/Mid/High Halving State Diagram:

Target = 30 | Input Array: [ 2, 9, 14, 26, 30, 41, 50 ]
Index:                       0  1   2   3   4   5   6

Step 1:
  low = 0, high = 6 -> mid = (0 + 6) // 2 = 3
  arr[mid] = 26 < 30 (Target is to the RIGHT)
  New Search Space -> low = mid + 1 = 4, high = 6

  [ 2, 9, 14, 26 | 30, 41, 50 ]
    x  x   x   x   low mid high
                    4   5   6

Step 2:
  low = 4, high = 6 -> mid = (4 + 6) // 2 = 5
  arr[mid] = 41 > 30 (Target is to the LEFT)
  New Search Space -> low = 4, high = mid - 1 = 4

  [ 2, 9, 14, 26 | 30 | 41, 50 ]
    x  x   x   x   L/M/H  x   x
                    (4)

Step 3:
  low = 4, high = 4 -> mid = 4
  arr[mid] = 30 == Target -> Match found at Index 4!
```

--------------------------------------------------------------------------------

<a id="3-idiomatic-python-implementation--state-tracing---week-4"></a>
#### 3. Idiomatic Python Implementation & State Tracing
##### Topic 1: Sequential Linear Search
```python
def linear_search(lst, target):
    # Iterate through list elements tracking both index position and value
    for index, item in enumerate(lst):
        # Step state trace: index 0, item is initial element
        # Step state trace: index 1, item is second element
        if item == target:
            # Console state: Match found, returning index integer
            return index
    # Console state: Target absent after full scan, returning -1
    return -1

# Execution Trace Example:
sample_data = ["ShadowFox", "NoScopeNate", "RonTheMage", "PixelPanda"]
result = linear_search(sample_data, "RonTheMage")
# Step 0: index=0, item="ShadowFox" != "RonTheMage"
# Step 1: index=1, item="NoScopeNate" != "RonTheMage"
# Step 2: index=2, item="RonTheMage" == "RonTheMage" -> returns 2
print("Linear Search Index Result:", result)
# Console Output: Linear Search Index Result: 2
```

--------------------------------------------------------------------------------

##### Topic 2: Binary Search (Divide and Conquer)
```python
def binary_search(lst, target):
    # Initialize pointer boundaries to span entire list
    low = 0
    high = len(lst) - 1

    while low <= high:
        # Calculate integral midpoint index
        mid = (low + high) // 2
        mid_val = lst[mid]
        # Trace pointers: low, mid, high, mid_val

        if mid_val == target:
            # Match confirmed at index mid
            return mid
        elif mid_val < target:
            # Target lies in upper right sub-array
            low = mid + 1
        else:
            # Target lies in lower left sub-array
            high = mid - 1

    # Search space exhausted without match
    return -1

# Execution Trace Example:
sorted_numbers = [1, 3, 7, 9, 10, 15, 22]
result_idx = binary_search(sorted_numbers, 9)
# Iteration 1: low=0, high=6 -> mid=3, mid_val=9 == target(9) -> returns 3
print("Binary Search Index Result:", result_idx)
# Console Output: Binary Search Index Result: 3
```

--------------------------------------------------------------------------------

##### Topic 3: Bubble Sort Algorithm
```python
def bubble_sort(arr):
    # Make shallow copy to preserve original list
    tmp_list = arr.copy()
    n = len(tmp_list)
    
    for i in range(n):
        # Track whether any swap occurred during pass
        swapped = False
        for j in range(0, n - i - 1):
            # Compare adjacent elements
            if tmp_list[j] > tmp_list[j + 1]:
                # Swap adjacent elements
                tmp_list[j], tmp_list[j + 1] = tmp_list[j + 1], tmp_list[j]
                swapped = True
        # If no swaps occurred, array is already sorted
        if not swapped:
            break
            
    return tmp_list

# Execution Trace Example:
initial_list = [5, 2, 4, 1]
sorted_res = bubble_sort(initial_list)
# Pass 1: [2, 4, 1, 5] (5 swapped to end)
# Pass 2: [2, 1, 4, 5] (4 swapped to position)
# Pass 3: [1, 2, 4, 5] (1 swapped to position)
print("Bubble Sorted Output:", sorted_res)
# Console Output: Bubble Sorted Output: [1, 2, 4, 5]
```

--------------------------------------------------------------------------------

##### Topic 4: Insertion Sort Algorithm
```python
def insertion_sort(arr):
    # Duplicate input list defensively
    tmp_list = arr.copy()
    shift_count = 0

    # Start loop at second element (index 1)
    for pass_cnt in range(1, len(tmp_list)):
        key = tmp_list[pass_cnt]
        pos = pass_cnt - 1

        # Shift elements greater than key to the right
        while pos >= 0 and tmp_list[pos] > key:
            tmp_list[pos + 1] = tmp_list[pos]
            pos -= 1
            shift_count += 1

        # Drop key into target hole
        tmp_list[pos + 1] = key

    # State log: total shifts executed
    return tmp_list, shift_count

# Execution Trace Example:
test_arr = [5, 2, 4, 6, 1, 3]
sorted_arr, total_shifts = insertion_sort(test_arr)
# Output array: [1, 2, 3, 4, 5, 6], shifts = 9
print("Insertion Sorted Array:", sorted_arr)
print("Total Shift Operations:", total_shifts)
# Console Output: Insertion Sorted Array: [1, 2, 3, 4, 5, 6]
# Console Output: Total Shift Operations: 9
```

--------------------------------------------------------------------------------

##### Topic 5: Python Built-in Sorting Tools (sorted() and .sort())
```python
players = [
    {"name": "Alice", "score": 30},
    {"name": "Bob", "score": 50},
    {"name": "Cara", "score": 40}
]

# 1. Functional Non-Mutating Sort via sorted() with Lambda Key
sorted_by_score_desc = sorted(players, key=lambda p: p["score"], reverse=True)
# Original 'players' remains unmodified
# Result: Bob (50), Cara (40), Alice (30)
print("Sorted Players (Descending):", sorted_by_score_desc)
# Console Output: Sorted Players (Descending): [{'name': 'Bob', 'score': 50}, {'name': 'Cara': 40}, {'name': 'Alice': 30}]

# 2. In-Place Method Mutation via .sort()
words = ["pear", "apple", "banana", "kiwi"]
words.sort(key=len)
# In-place modification sorts by length: 4, 5, 6, 4 -> "pear" (4), "kiwi" (4), "apple" (5), "banana" (6)
# Note: "pear" precedes "kiwi" because Timsort is stable and preserves original relative order
print("In-Place Sorted Words by Length:", words)
# Console Output: In-Place Sorted Words by Length: ['pear', 'kiwi', 'apple', 'banana']
```

--------------------------------------------------------------------------------

<a id="4-defensive-programming--common-traps---week-4"></a>
#### 4. Defensive Programming & Common Traps
##### Trap 1: Expecting .sort() to Return a New List
The .sort() method mutates lists in-place and returns None. Assigning its return value to a variable destroys reference access to the sorted data.
```python
# INCORRECT: Assigning return value of in-place .sort() method
nums = [5, 1, 4, 2]
sorted_nums = nums.sort() # Bug: sorted_nums is assigned None
# TypeError / AttributeError on subsequent operations expecting a list:
# len(sorted_nums) -> TypeError: object of type 'NoneType' has no len()

# CORRECT: Using sorted() function or accessing mutated list directly
nums_a = [5, 1, 4, 2]
sorted_nums_a = sorted(nums_a) # Creates new sorted list

nums_b = [5, 1, 4, 2]
nums_b.sort() # Mutates nums_b in-place; nums_b is now [1, 2, 4, 5]
```

--------------------------------------------------------------------------------

##### Trap 2: Running Binary Search on Unsorted Data
Binary search logic assumes sorted input to discard left or right sub-arrays. Running it on unsorted data yields incorrect results.
```python
# INCORRECT: Calling binary search on unsorted array
unsorted_list = [30, 2, 50, 9, 41]
target = 30
# Mid element is 50. 30 < 50, so high becomes mid - 1, discarding [30, 2]
# Target 30 is falsely declared absent! (-1 returned)

# CORRECT: Sort input prior to binary search or use linear search for unsorted lists
data = [30, 2, 50, 9, 41]
# Option A: One-off scan using linear search
res_linear = linear_search(data, target)

# Option B: Pre-sort if executing multiple binary searches
data.sort() # Data becomes [2, 9, 30, 41, 50]
res_binary = binary_search(data, target)
```

--------------------------------------------------------------------------------

##### Trap 3: Off-By-One Index Initialization in Binary Search
Initializing high = len(lst) instead of len(lst) - 1 leads to IndexError when evaluating lst[mid].
```python
# INCORRECT: Boundary setup using len(lst)
def bad_binary_search(lst, target):
    low = 0
    high = len(lst) # Bug: Should be len(lst) - 1
    while low <= high:
        mid = (low + high) // 2
        if lst[mid] == target: # IndexError: list index out of range when mid == len(lst)
            return mid

# CORRECT: Proper index pointer boundary setup
def clean_binary_search(lst, target):
    low = 0
    high = len(lst) - 1 # Correct upper bound index
    while low <= high:
        mid = (low + high) // 2
        if lst[mid] == target:
            return mid
        elif lst[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
```

--------------------------------------------------------------------------------

##### Trap 4: Mutating a List While Iterating Over It
Removing items from a list while iterating over it causes the iterator index to skip adjacent items due to index shift.
```python
# INCORRECT: Removing elements directly during for-in loop iteration
numbers = [1, 2, 3, 4, 5, 6]
for num in numbers:
    if num % 2 == 0:
        numbers.remove(num) # Bug: Index shifts left, skipping inspection of 3 and 5!
# Resulting list: [1, 3, 5] (Appears correct here by coincidence, but fails on adjacent evens like [2, 4])

# CORRECT: List comprehension or iterating over a shallow copy
numbers_a = [1, 2, 4, 5, 6]
# Solution A: List comprehension
filtered_numbers = [x for x in numbers_a if x % 2 != 0]

# Solution B: Iterate over explicit copy
numbers_b = [1, 2, 4, 5, 6]
for num in numbers_b.copy():
    if num % 2 == 0:
        numbers_b.remove(num)
```

--------------------------------------------------------------------------------

<a id="5-python-memory-mechanics-references--scope---week-4"></a>
#### 5. Python Memory Mechanics, References & Scope
Python manages variables as name bindings pointing to heap-allocated objects.
##### Dynamic Binding & Memory Allocation
1.  **Object Creation:** Executing scores = [50, 10, 75, 30] allocates a list object on the heap containing pointers to integer objects 50, 10, 75, and 30.
2.  **sorted(scores) Execution:** sorted() creates an entirely **new** list object on the heap, populating it with pointers to the same element objects in ascending order. The reference variable scores remains pointing to the original unordered list.
3.  **scores.sort() Execution:** .sort() modifies the existing heap list object in-place by re-ordering internal element references. No new primary list object is created.

```
Namespace & Heap Memory Diagram:

Initial State:
  Namespace                Heap Objects
  [ scores ] ------------> List Object A: [ id_50, id_10, id_75, id_30 ]

After 'result = sorted(scores)':
  Namespace                Heap Objects
  [ scores ] ------------> List Object A: [ id_50, id_10, id_75, id_30 ]
  [ result ] ------------> List Object B: [ id_10, id_30, id_50, id_75 ]  (New Object)

After 'scores.sort()':
  Namespace                Heap Objects
  [ scores ] ------------> List Object A: [ id_10, id_30, id_50, id_75 ]  (Mutated in-place)
```

--------------------------------------------------------------------------------

##### Reference Identity Verification
Object memory identity can be verified using Python's built-in id() function and is identity comparison operator:
```python
scores = [50, 10, 75, 30]
initial_id = id(scores)

# sorted() creates distinct heap object
result = sorted(scores)
print(id(result) == initial_id) # Output: False

# .sort() mutates same heap object
scores.sort()
print(id(scores) == initial_id) # Output: True
```

--------------------------------------------------------------------------------

<a id="6-practical-integration--mini-case-study---week-4"></a>
#### 6. Practical Integration / Mini Case Study
##### High-Frequency Trade Management System
```python
import time

class TradeManager:
    def __init__(self):
        # Initialize primary database storage
        self.trades = []
        self.is_sorted_by_id = False

    def add_trade(self, trade_id, symbol, profit):
        # Append trade record dict to storage
        self.trades.append({
            "trade_id": trade_id,
            "symbol": symbol,
            "profit": profit
        })
        # Appending invalidates sorted state assumption
        self.is_sorted_by_id = False

    def linear_search_symbol(self, symbol):
        # Finds all trades matching a specific ticker symbol (O(n) scan)
        matching_trades = []
        for index, trade in enumerate(self.trades):
            if trade["symbol"] == symbol:
                matching_trades.append((index, trade))
        return matching_trades

    def prepare_index(self):
        # Sorts trades by trade_id in-place using Python Timsort (O(n log n))
        self.trades.sort(key=lambda t: t["trade_id"])
        self.is_sorted_by_id = True

    def binary_search_trade_id(self, target_id):
        # Executes logarithmic O(log n) search for trade_id
        if not self.is_sorted_by_id:
            # Enforce pre-sorting invariant defensively
            self.prepare_index()

        low = 0
        high = len(self.trades) - 1

        while low <= high:
            mid = (low + high) // 2
            mid_id = self.trades[mid]["trade_id"]

            if mid_id == target_id:
                return mid, self.trades[mid]
            elif mid_id < target_id:
                low = mid + 1
            else:
                high = mid - 1

        return -1, None

# --- Complete Integration Execution Trace ---
if __name__ == "__main__":
    bot = TradeManager()
    
    # 1. Populate Unsorted Trade History
    raw_data = [
        (1088, "BTC", 450.50),
        (1002, "ETH", -120.00),
        (1045, "BTC", 890.10),
        (1011, "SOL", 310.00)
    ]
    for tid, sym, pft in raw_data:
        bot.add_trade(tid, sym, pft)

    # 2. Linear Search for Symbol "BTC"
    btc_trades = bot.linear_search_symbol("BTC")
    print("Linear Search Symbol Result ('BTC'):", btc_trades)
    # Trace output: Returns indices 0 and 2 matching BTC

    # 3. Defensive Index Preparation & Binary Search for trade_id 1045
    found_idx, trade_record = bot.binary_search_trade_id(1045)
    print("Binary Search Target 1045 Index:", found_idx)
    print("Trade Record Found:", trade_record)
    # Trace output: Trades sorted to [1002, 1011, 1045, 1088], target 1045 found at Index 2
```

--------------------------------------------------------------------------------

<a id="7-step-by-step-code-tracing-challenges--diagnostics---week-4"></a>
#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Single Pass Bubble Sort State Trace
**Code:**
```python
scores = [5, 2, 4, 1]
for j in range(len(scores) - 1):
    if scores[j] > scores[j + 1]:
        scores[j], scores[j + 1] = scores[j + 1], scores[j]
```
**Step-by-Step Line Trace:**
1. j = 0: Compare scores[0] (5) and scores[1] (2). 5 > 2 -> Swap! scores becomes [2, 5, 4, 1].
2. j = 1: Compare scores[1] (5) and scores[2] (4). 5 > 4 -> Swap! scores becomes [2, 4, 5, 1].
3. j = 2: Compare scores[2] (5) and scores[3] (1). 5 > 1 -> Swap! scores becomes [2, 4, 1, 5]. **Final Terminal Output:** [2, 4, 1, 5].

--------------------------------------------------------------------------------

##### Challenge B: First Step Insertion Sort State Trace
**Code:**
```python
nums = [7, 3, 5, 4]
key = nums[1] # Key extracted is 3
pos = 0       # Initial comparison position is 0
while pos >= 0 and nums[pos] > key:
    nums[pos + 1] = nums[pos]
    pos -= 1
nums[pos + 1] = key
```
**Step-by-Step Line Trace:**
1. Initialize key = 3, pos = 0 (nums[0] is 7).
2. while pos (0) >= 0 and nums[0] (7) > key (3) evaluates to True.
3. Shift element: nums[1] = nums[0] -> nums becomes [7, 7, 5, 4].
4. pos decrements to -1. Loop terminates.
5. nums[pos + 1] (nums[0]) assigned key (3) -> nums becomes [3, 7, 5, 4]. **Final Terminal Output:** [3, 7, 5, 4].

--------------------------------------------------------------------------------

##### Challenge C: Binary Search Low/Mid/High Pointer Trace
**Code:**
```python
arr = [2, 9, 14, 26, 30, 41, 50]
target = 30
low, high = 0, 6
```
**Step-by-Step Line Trace:**
1. **Iteration 1:** low = 0, high = 6 -> mid = (0 + 6) // 2 = 3.
    *  arr[3] is 26. 26 < 30 -> low becomes mid + 1 = 4.
2. **Iteration 2:** low = 4, high = 6 -> mid = (4 + 6) // 2 = 5.
    *  arr[5] is 41. 41 > 30 -> high becomes mid - 1 = 4.
3. **Iteration 3:** low = 4, high = 4 -> mid = (4 + 4) // 2 = 4.
    *  arr[4] is 30. 30 == 30 -> Target found at index 4! **Final Terminal Output:** Found target 30 at index 4.

--------------------------------------------------------------------------------

##### Challenge D: Custom Sorting with key=len and Stability
**Code:**
```python
words = ["pear", "apple", "banana", "kiwi"]
words.sort(key=len)
```
**Step-by-Step Line Trace:**
1. Evaluate lengths via key=len:
    *  "pear" -> length 4
    *  "apple" -> length 5
    *  "banana" -> length 6
    *  "kiwi" -> length 4
2. Group by length: Length 4 ("pear", "kiwi"), Length 5 ("apple"), Length 6 ("banana").
3. Timsort stability invariant: "pear" originally appeared at index 0 and "kiwi" at index 3. Because their key lengths tie (4 == 4), their original relative order is preserved ("pear" before "kiwi"). **Final Terminal Output:** ['pear', 'kiwi', 'apple', 'banana'].

---

End of Course Master Compendium. Complete syllabus mastery verified.
