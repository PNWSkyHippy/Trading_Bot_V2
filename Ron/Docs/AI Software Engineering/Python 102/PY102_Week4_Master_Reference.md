# PY102 - Week 4 Master Reference: Searching and Sorting Algorithms in Python

*This document synthesizes all core concepts, mental models, memory mechanics, algorithmic bounds, and code traces from Week 4 into an authoritative, publication-grade reference guide.* [1, 19]

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

Computer science organizes operations on data collections into fundamental paradigms [2]. A **search task** is defined as locating a specific **target** element within a broader **collection** based on a matching criteria [2, 13]. Conversely, a **sorting task** rearranges all elements within a collection according to a specified total ordering [13, 108].

### Primary Terminology & Keywords

*   **Collection:** The underlying data structure (such as a Python list or database table) containing the target items [2].
*   **Target:** The specific value, key, or property condition sought during a search operation [2, 61].
*   **Linear Search (Full Scan):** Sequential inspection of elements from index $0$ to $n-1$, running in worst-case $O(n)$ time [6, 61, 66].
*   **Binary Search:** A divide-and-conquer strategy that repeatedly halves a sorted search space, running in logarithmic $O(\log n)$ time [74, 82].
*   **Logarithmic Complexity ($O(\log n)$):** Algorithmic efficiency wherein each operational step eliminates approximately half of the remaining problem domain [86].
*   **In-Place Mutation:** Direct modification of an existing object's memory without allocating a new primary data structure [20, 21].
*   **Algorithm Stability:** A property of sorting algorithms that preserves the relative input order of records with equal keys [38].
*   **Timsort:** Python's default hybrid sorting algorithm, exhibiting $O(n \log n)$ time complexity [24, 25].

---

### Side-by-Side Comparison Matrix

| Feature / Spec | Linear Search | Binary Search | Bubble Sort | Insertion Sort | Timsort (`sorted()` / `.sort()`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Definition** | Sequential element-by-element scan from start to end | Divide-and-conquer index halving on sorted data | Repeated adjacent neighbor comparison and swapping | Building a sorted left sub-list by shifting larger items right | Hybrid merge/insertion sort built into Python C-extension |
| **Syntax / Delimiters** | `for index, item in enumerate(lst):` | `while low <= high:` with `mid = (low + high) // 2` | Nested `for` loops comparing `arr[j]` and `arr[j+1]` | Outer `for` loop with inner `while pos >= 0 and arr[pos] > key:` | `sorted(iterable, key=..., reverse=...)` or `lst.sort(...)` |
| **Best-Case Complexity** | $O(1)$ (target is at index 0) | $O(1)$ (target is at initial midpoint) | $O(n)$ (with optimized early-exit flag on sorted array) | $O(n)$ (nearly or fully sorted array requiring zero shifts) | $O(n)$ (already sorted or nearly sorted array) |
| **Worst-Case Complexity** | $O(n)$ (target at end or missing) | $O(\log n)$ (target missing or at extreme boundaries) | $O(n^2)$ (reverse-sorted array requiring maximum swaps) | $O(n^2)$ (reverse-sorted array requiring maximum shifts) | $O(n \log n)$ (randomized or adversarial distribution) |
| **Space Complexity** | $O(1)$ auxiliary space | $O(1)$ auxiliary space (iterative version) | $O(1)$ auxiliary space (in-place) | $O(1)$ auxiliary space (in-place) | $O(n)$ auxiliary space |
| **Data Invariants** | Unsorted or sorted collections | **Strictly required:** Collection MUST be pre-sorted | Operates on unsorted collections | Operates on unsorted collections | Operates on unsorted collections |
| **Mutability Behavior** | Read-only (non-mutating) | Read-only (non-mutating) | Mutates list in-place | Mutates list in-place (or operate on copy) | `sorted()` returns new list; `.sort()` mutates list in-place |
| **Common Trap** | Unnecessary $O(n)$ scans when direct dict lookups exist | Executing on unsorted data leading to incorrect exclusions | Extreme performance penalty ($O(n^2)$) on large datasets | Confusing key extraction with element substitution | Assigning `.sort()` return value (`None`) to variable |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: The Phone Book Search (Linear vs. Binary Search)
Searching through an unsorted binder of 1,000 documents requires inspecting each sheet sequentially from page 1 to 1,000 [1]. If the phone book is sorted alphabetically (A to Z), locating a target like "Miller" does not start on page 1 [73]. Instead, you open to the midpoint [73]. Observing "Smith" immediately informs you that "Miller" precedes "Smith", allowing you to discard the entire second half [73]. Repeating this halving operation reduces 1,000 pages to roughly 10 inspections [87].

### Analogy 2: Playing Card Arrangement (Insertion Sort)
When holding a hand of playing cards, you keep a sorted subset in your left hand [116]. As you draw a new card with your right hand, you compare it against the sorted left hand from right to left [116]. You shift larger cards one position right to create a slot ("hole") and insert the new card in its proper position [116, 118].

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

### Analogy 3: Bubble Sort Neighbor Exchange
Imagine physical weights lined up on a beam. You step through from left to right, comparing adjacent pairs [108]. If a heavier weight is to the left of a lighter one, you swap their physical positions [108]. Over a full pass from left to right, the heaviest remaining weight "bubbles" up to its final destination at the rightmost available index [108, 120].

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

---

## 3. Idiomatic Python Implementation & State Tracing

### Topic 1: Sequential Linear Search

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

---

### Topic 2: Binary Search (Divide and Conquer)

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

---

### Topic 3: Bubble Sort Algorithm

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

---

### Topic 4: Insertion Sort Algorithm

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

---

### Topic 5: Python Built-in Sorting Tools (`sorted()` and `.sort()`)

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
# Console Output: Sorted Players (Descending): [{'name': 'Bob', 'score': 50}, {'name': 'Cara', 'score': 40}, {'name': 'Alice', 'score': 30}]

# 2. In-Place Method Mutation via .sort()
words = ["pear", "apple", "banana", "kiwi"]
words.sort(key=len)
# In-place modification sorts by length: 4, 5, 6, 4 -> "pear" (4), "kiwi" (4), "apple" (5), "banana" (6)
# Note: "pear" precedes "kiwi" because Timsort is stable and preserves original relative order
print("In-Place Sorted Words by Length:", words)
# Console Output: In-Place Sorted Words by Length: ['pear', 'kiwi', 'apple', 'banana']
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Expecting `.sort()` to Return a New List
The `.sort()` method mutates lists in-place and returns `None` [20, 21]. Assigning its return value to a variable destroys reference access to the sorted data [21].

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

---

### Trap 2: Running Binary Search on Unsorted Data
Binary search logic assumes sorted input to discard left or right sub-arrays [79, 81]. Running it on unsorted data yields incorrect results [79, 81].

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

---

### Trap 3: Off-By-One Index Initialization in Binary Search
Initializing `high = len(lst)` instead of `len(lst) - 1` leads to `IndexError` when evaluating `lst[mid]` [76].

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

---

### Trap 4: Mutating a List While Iterating Over It
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

---

## 5. Python Memory Mechanics, References & Scope

Python manages variables as name bindings pointing to heap-allocated objects.

### Dynamic Binding & Memory Allocation
1.  **Object Creation:** Executing `scores = [50, 10, 75, 30]` allocates a `list` object on the heap containing pointers to integer objects `50`, `10`, `75`, and `30` [20].
2.  **`sorted(scores)` Execution:** `sorted()` creates an entirely **new** `list` object on the heap, populating it with pointers to the same element objects in ascending order [20]. The reference variable `scores` remains pointing to the original unordered list [20].
3.  **`scores.sort()` Execution:** `.sort()` modifies the existing heap list object in-place by re-ordering internal element references [20]. No new primary list object is created [20].

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

### Reference Identity Verification
Object memory identity can be verified using Python's built-in `id()` function and `is` identity comparison operator:

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

---

## 6. Practical Integration / Mini Case Study

### High-Frequency Trade Management System

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

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Single Pass Bubble Sort State Trace
**Code:**
```python
scores = [5, 2, 4, 1]
for j in range(len(scores) - 1):
    if scores[j] > scores[j + 1]:
        scores[j], scores[j + 1] = scores[j + 1], scores[j]
```
**Step-by-Step Line Trace:**
1.  `j = 0`: Compare `scores[0]` (5) and `scores[1]` (2). 5 > 2 -> Swap! `scores` becomes `[2, 5, 4, 1]` [35].
2.  `j = 1`: Compare `scores[1]` (5) and `scores[2]` (4). 5 > 4 -> Swap! `scores` becomes `[2, 4, 5, 1]` [35].
3.  `j = 2`: Compare `scores[2]` (5) and `scores[3]` (1). 5 > 1 -> Swap! `scores` becomes `[2, 4, 1, 5]` [35, 154].
**Final Terminal Output:** `[2, 4, 1, 5]` [43, 154].

---

### Challenge B: First Step Insertion Sort State Trace
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
1.  Initialize `key = 3`, `pos = 0` (`nums[0]` is 7) [58].
2.  `while pos (0) >= 0 and nums[0] (7) > key (3)` evaluates to `True` [121].
3.  Shift element: `nums[1] = nums[0]` -> `nums` becomes `[7, 7, 5, 4]` [121].
4.  `pos` decrements to `-1`. Loop terminates [121].
5.  `nums[pos + 1]` (`nums[0]`) assigned `key` (3) -> `nums` becomes `[3, 7, 5, 4]` [121].
**Final Terminal Output:** `[3, 7, 5, 4]` [158].

---

### Challenge C: Binary Search Low/Mid/High Pointer Trace
**Code:**
```python
arr = [2, 9, 14, 26, 30, 41, 50]
target = 30
low, high = 0, 6
```
**Step-by-Step Line Trace:**
1.  **Iteration 1:** `low = 0`, `high = 6` -> `mid = (0 + 6) // 2 = 3` [209].
    *   `arr[3]` is 26. 26 < 30 -> `low` becomes `mid + 1 = 4` [209, 215].
2.  **Iteration 2:** `low = 4`, `high = 6` -> `mid = (4 + 6) // 2 = 5` [209, 218].
    *   `arr[5]` is 41. 41 > 30 -> `high` becomes `mid - 1 = 4` [219].
3.  **Iteration 3:** `low = 4`, `high = 4` -> `mid = (4 + 4) // 2 = 4` [220].
    *   `arr[4]` is 30. 30 == 30 -> Target found at index 4 [220]!
**Final Terminal Output:** Found target 30 at index `4` [220].

---

### Challenge D: Custom Sorting with `key=len` and Stability
**Code:**
```python
words = ["pear", "apple", "banana", "kiwi"]
words.sort(key=len)
```
**Step-by-Step Line Trace:**
1.  Evaluate lengths via `key=len`:
    *   `"pear"` -> length 4 [166]
    *   `"apple"` -> length 5 [166]
    *   `"banana"` -> length 6 [166]
    *   `"kiwi"` -> length 4 [166]
2.  Group by length: Length 4 (`"pear"`, `"kiwi"`), Length 5 (`"apple"`), Length 6 (`"banana"`).
3.  Timsort stability invariant: `"pear"` originally appeared at index 0 and `"kiwi"` at index 3 [220, 221]. Because their key lengths tie (4 == 4), their original relative order is preserved (`"pear"` before `"kiwi"`) [220, 221].
**Final Terminal Output:** `['pear', 'kiwi', 'apple', 'banana']` [212, 221].
