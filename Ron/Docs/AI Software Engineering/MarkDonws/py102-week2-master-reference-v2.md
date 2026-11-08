# PY102 - Week 2 Master Reference: Linear Data Structures (Stacks & Queues)

Welcome to the **PY102 Week 2 Master Reference Document**. This publication-grade technical guide synthesizes all core concepts, mental models, memory mechanics, defensive programming practices, and step-by-step code traces from across the module into an authoritative, self-contained reference text. It is fully formatted in GitHub Flavored Markdown and engineered for direct export and integration into your master class notebook.

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

Linear data structures organize data sequentially, where elements are arranged in a contiguous logical sequence. The two foundational abstract linear data structures introduced in this module are **Stacks** and **Queues**. Though both maintain ordered collections, they enforce opposite access policies regarding where items enter and exit.

### Core Vocabulary & Operations

* **Stack**: A linear collection governed by the **LIFO** rule, where all additions and removals occur exclusively at a single access point termed the **Top**.
* **Queue**: A linear collection governed by the **FIFO** rule, where new items enter at one end (**Rear**) and processing occurs at the opposite end (**Front**).
* **LIFO (Last-In, First-Out)**: The structural policy where the most recently added item is the first element to be extracted.
* **FIFO (First-In, First-Out)**: The structural policy where elements are processed strictly according to their arrival sequence (oldest item first).
* **Push**: The operation of inserting a new element onto the top of a stack. In standard Python lists, this is executed via `append()`.
* **Pop**: The operation of extracting and returning the top element from a stack (via `pop()`) or front element from a queue (via `pop(0)` or `popleft()`).
* **Enqueue**: The operation of adding a new element to the rear of a queue. In Python, this is executed via `append()`.
* **Dequeue**: The operation of removing and returning the front element of a queue.
* **Peek**: Observing the element at the top of a stack or front of a queue without removing it (e.g., using index `[-1]` for stacks or `[0]` for queues).
* **Underflow Guard**: A protective conditional logic check that verifies a structure is non-empty before attempting a removal or peek operation, preventing runtime exceptions.
* **`collections.deque`**: A specialized Python class from the standard library providing a double-ended queue implementation optimized for $O(1)$ insertions and removals at both ends.

---

### Side-by-Side Structural Comparison Matrix

| Feature / Spec | Stack (`list`) | Queue (`list`) | Optimized Queue (`collections.deque`) |
| :--- | :--- | :--- | :--- |
| **Ordering Rule** | **LIFO** (Last-In, First-Out) | **FIFO** (First-In, First-Out) | **FIFO** (First-In, First-Out) |
| **Access Point(s)** | Single access point: **Top** (Right end / index `-1`) | Dual access points: **Rear** (index `-1`) & **Front** (index `0`) | Dual access points: **Right** (index `-1`) & **Left** (index `0`) |
| **Primary Operations** | Push (`append`), Pop (`pop`), Peek (`[-1]`) | Enqueue (`append`), Dequeue (`pop(0)`), Peek (`[0]`) | Enqueue (`append`), Dequeue (`popleft`), Peek (`[0]`) |
| **Initialization Syntax** | `stack = []` | `queue = []` | `from collections import deque; q = deque()` |
| **Insertion Syntax & Speed** | `stack.append(item)` — $O(1)$ amortized | `queue.append(item)` — $O(1)$ amortized | `q.append(item)` — $O(1)$ constant time |
| **Removal Syntax & Speed** | `stack.pop()` — $O(1)$ constant time | `queue.pop(0)` — $O(n)$ linear time | `q.popleft()` — $O(1)$ constant time |
| **Underflow Guard Check** | `if len(stack) > 0:` or `if stack:` | `if len(queue) > 0:` or `if queue:` | `if len(q) > 0:` or `if q:` |
| **Primary Memory Layout** | Contiguous array (dynamic vector) | Contiguous array (dynamic vector) | Doubly linked list of fixed-size blocks |
| **Common Runtime Exception** | `IndexError` on empty pop/peek | `IndexError` on empty `pop(0)` | `IndexError` on empty `popleft()` |

---

## 2. Real-World Mental Models & Conceptual Mapping

To reliably predict data structure behavior, developers rely on visual physical analogies that map access restrictions directly to physical constraints.

### 1. The Stack Analogy: Heavy Buffet Plate Dispenser & Book Pile
* **Physical Constraint**: Plates are loaded into a spring-loaded vertical cylinder. You can only place a new plate on top of the pile, and you can only lift off the topmost plate.
* **Software Mapping**: Software features like **Text Editor Undo Histories** (`Ctrl+Z`) and **Browser Back Buttons** place each user state on top of a history stack. Undoing an action extracts the most recent state first.

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

---

### 2. The Queue Analogy: Coffee Shop & Ice-Cream Truck Line
* **Physical Constraint**: Customers arrive and join the back of the line (Rear). The barista serves the customer at the front of the line (Front). Jumping ahead or serving out of order breaks fairness.
* **Software Mapping**: Systems like **Printer Spoolers**, **Help Desk Ticketing**, and **Game Server Matchmaking Lobbies** process jobs in the exact order they arrive.

```
       QUEUE (FIFO) STRUCTURAL DIAGRAM
       
   DEQUEUE (popleft / pop(0))                 ENQUEUE (append)
          <-- FRONT                              REAR <--
   +------------+------------+------------+------------+
   | Customer A | Customer B | Customer C | Customer D |
   +------------+------------+------------+------------+
      Index 0      Index 1      Index 2      Index 3
```

---

### 3. The Hybrid Analogy: Adventurers in Line with Item Backpacks
* **Physical Constraint**: Adventurers wait in a single-file FIFO line to enter a dungeon portal. Each adventurer wears a backpack operated as a LIFO stack (items packed last are on top and pulled out first).
* **Software Mapping**: Multi-level software architecture where outer workflows are managed via queue queues, while local sub-task contexts manage state via internal stacks.

---

## 3. Idiomatic Python Implementation & State Tracing

### 3.1 Stack Operations using Python Lists

When mapping a stack to a standard Python list, the **rightmost element (index `-1`) is treated as the Top**.

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

---

### 3.2 List-Based Queue Operations

When implementing a queue with a standard Python list, elements enter at the rear via `append()` and exit from the front (index `0`) via `pop(0)`.

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

---

### 3.3 Module Imports & High-Performance `collections.deque`

Standard lists require $O(n)$ linear time for `pop(0)` because Python must shift every remaining item in memory leftward by one memory slot. The `collections.deque` class provides an $O(1)$ constant time `popleft()` implementation.

#### Importing Syntax Variants
```python
# Variant 1: Full module import (requires prefixing)
import collections
service_queue = collections.deque()

# Variant 2: Specific tool import (direct class usage)
from collections import deque
ticket_queue = deque()
```

#### High-Performance Deque Code Walkthrough
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

---

## 4. Defensive Programming & Common Traps

When building state-driven software, unhandled boundary conditions cause runtime crashes or silent data corruption. Below are the four primary traps and their defensive solutions.

### Trap 1: Underflow Exception (`IndexError`)
Attempting to pop or peek an empty collection causes Python to halt with an `IndexError`.

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

---

### Trap 2: Overwriting Collection Reference with `None` (`AttributeError`)
In Python, standard list methods like `.append()` and `.reverse()` modify the collection **in-place** and return `None`. Assigning the result back to the variable destroys the collection.

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

---

### Trap 3: Calling `popleft()` on Standard Python Lists (`AttributeError`)
`popleft()` is a method exclusive to `collections.deque` objects. Calling it on a list causes a method lookup failure.

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

---

### Trap 4: Module Name Scope & Namespace Ambiguity (`NameError`)
Using the general `import module` statement requires prefixing function calls with the module name. Calling imported functions directly causes a `NameError`.

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

---

## 5. Python Memory Mechanics, References & Scope

Understanding how Python manages variables in memory is critical when passing data structures into functions.

### 1. Variables as Object References (Binding vs Assignment)
In Python, variables are not named memory slots containing values. Instead, variables are **names bound to object memory addresses** residing in heap memory.

* **Immutable Objects** (e.g., integers, strings, tuples): Modifying the value creates a brand-new object at a new memory address.
* **Mutable Objects** (e.g., lists, dictionaries, `deque` objects): Modifying the object alters the underlying data structure in-place at its existing memory address.

### 2. Passing Data Structures to Functions
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

---

### Memory Address & Namespace ASCII Diagram

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

---

## 6. Practical Integration / Mini Case Study

### Comprehensive System: Dungeon Adventurer & Inventory Dispatcher

The following script integrates all concepts from Week 2:
1. `collections.deque` manages an outer **FIFO Queue** of Adventurers waiting to enter a dungeon.
2. Standard Python `list` objects act as inner **LIFO Stacks** representing each adventurer's item backpack.
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

---

### Executable Console Output Trace

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

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Stack Undo-Redo & Double-Pop Trace

#### Code Snippet
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

#### Line-by-Line State Trace
1. `history = []` $\rightarrow$ `history`: `[]`
2. `history.append("Action 1")` $\rightarrow$ `history`: `["Action 1"]`
3. `history.append("Action 2")` $\rightarrow$ `history`: `["Action 1", "Action 2"]`
4. `history.append("Action 3")` $\rightarrow$ `history`: `["Action 1", "Action 2", "Action 3"]`
5. `act1 = history.pop()` $\rightarrow$ removes `"Action 3"`, `history`: `["Action 1", "Action 2"]`, `act1`: `"Action 3"`
6. `history.append("Action 4")` $\rightarrow$ `history`: `["Action 1", "Action 2", "Action 4"]`
7. `if len(history) >= 2:` $\rightarrow$ `len(history)` is `3` (`3 >= 2` evaluates to `True`)
8. `undo_a = history.pop()` $\rightarrow$ removes `"Action 4"`, `history`: `["Action 1", "Action 2"]`, `undo_a`: `"Action 4"`
9. `undo_b = history.pop()` $\rightarrow$ removes `"Action 2"`, `history`: `["Action 1"]`, `undo_b`: `"Action 2"`

#### Terminal Output
```text
history: ['Action 1']
undo_a: Action 4
undo_b: Action 2
```

---

### Challenge B: Dual-Ended List Queue Manipulation

#### Code Snippet
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

#### Line-by-Line State Trace
1. `q = ["Alpha", "Beta", "Gamma"]` $\rightarrow$ `q`: `["Alpha", "Beta", "Gamma"]`
2. `q.append("Delta")` $\rightarrow$ `q`: `["Alpha", "Beta", "Gamma", "Delta"]`
3. `item_x = q.pop(0)` $\rightarrow$ removes index `0` (`"Alpha"`), `q`: `["Beta", "Gamma", "Delta"]`, `item_x`: `"Alpha"`
4. `q.append(item_x)` $\rightarrow$ appends `"Alpha"`, `q`: `["Beta", "Gamma", "Delta", "Alpha"]`
5. `item_y = q.pop(0)` $\rightarrow$ removes index `0` (`"Beta"`), `q`: `["Gamma", "Delta", "Alpha"]`, `item_y`: `"Beta"`

#### Terminal Output
```text
Final Queue: ['Gamma', 'Delta', 'Alpha']
item_x: Alpha
item_y: Beta
```

---

### Challenge C: High-Performance `collections.deque` Trace

#### Code Snippet
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

#### Line-by-Line State Trace
1. `d = deque(["Task A", "Task B"])` $\rightarrow$ `d`: `deque(['Task A', 'Task B'])`
2. `d.append("Task C")` $\rightarrow$ `d`: `deque(['Task A', 'Task B', 'Task C'])`
3. `d.appendleft("Task Zero")` $\rightarrow$ `d`: `deque(['Task Zero', 'Task A', 'Task B', 'Task C'])`
4. `val_left = d.popleft()` $\rightarrow$ removes left element (`"Task Zero"`), `d`: `deque(['Task A', 'Task B', 'Task C'])`, `val_left`: `"Task Zero"`
5. `val_right = d.pop()` $\rightarrow$ removes right element (`"Task C"`), `d`: `deque(['Task A', 'Task B'])`, `val_right`: `"Task C"`

#### Terminal Output
```text
Deque state: ['Task A', 'Task B']
val_left: Task Zero
val_right: Task C
```

---

### Challenge D: Function Scope & Mutable Reference Side-Effect Trace

#### Code Snippet
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

#### Line-by-Line State Trace
1. `s = [10, 20, 30]`, `q = [100, 200]`
2. First call: `process_data(s, q)`
   - `stack_ref` points to `s`, `queue_ref` points to `q`.
   - `popped = stack_ref.pop()` $\rightarrow$ removes `30` from `s`. `s` is now `[10, 20]`.
   - `queue_ref.append(30)` $\rightarrow$ appends `30` to `q`. `q` is now `[100, 200, 30]`.
3. Second call: `process_data(s, q)`
   - `popped = stack_ref.pop()` $\rightarrow$ removes `20` from `s`. `s` is now `[10]`.
   - `queue_ref.append(20)` $\rightarrow$ appends `20` to `q`. `q` is now `[100, 200, 30, 20]`.

#### Terminal Output
```text
s: [10]
q: [100, 200, 30, 20]
```
