# CS101 - Week 3 Master Reference: Advanced Data Structures, Filtering, Grouping & Functional Pipelines

*Welcome to the CS101 Week 3 Master Reference Guide. This publication-grade reference document synthesizes all core concepts, mental models, memory mechanics, data structure designs, and step-by-step code execution traces from this module into an authoritative, self-contained textbook reference.*

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

### Primary Data Structures and Operations

Python provides flexible composite data types that allow developers to model complex real-world systems. Managing collections of structured records relies on combining primitive types into nested data architectures.

- **List of Dictionaries (`List[Dict[str, Any]]`)**: An ordered, mutable sequence of dictionary objects where each dictionary represents a discrete record ("row") and dictionary keys represent consistent attributes ("columns").
- **Dictionary of Lists (`Dict[str, List[Any]]`)**: A mutable mapping where each key represents a category or grouping ("bucket") and each value is an ordered list containing elements belonging to that category.
- **Dictionary Index (`Dict[Key, Dict[str, Any]]`)**: A hash map keyed by a unique primary key (e.g., `id`, `sku`, `student_id`) pointing directly to a complete record dictionary, enabling $O(1)$ constant-time lookups.
- **Filter Pattern (Scan-Test-Store)**: An algorithmic pattern that iterates over a dataset, evaluates a boolean conditional rule for each item, and collects matching records into a new result collection.
- **Grouping Pattern**: An incremental categorization algorithm that iterates over records, checks for category key existence in a destination dictionary, initializes empty list buckets when necessary, and appends records to their respective buckets.
- **Functional Pipeline (Chaining)**: A modular software architecture where small, single-responsibility functions are linked sequentially such that the return value of one function becomes the direct input parameter of the next.
- **Loop Skeleton vs. Per-Item Helper**: An architectural design principle separating iteration control (`for` loop over a collection) from single-item transformation logic (a helper function operating on a single record).
- **Dictionary Views (`.keys()`, `.values()`, `.items()`)**: Dynamic view objects reflecting the keys, values, or key-value tuples of a dictionary without making memory-intensive copies.

---

### Side-by-Side Comparison Matrix

| Feature / Spec | List of Dictionaries (Table Model) | Dictionary of Lists (Bucket Model) | Dictionary Index (Lookup Model) |
| :--- | :--- | :--- | :--- |
| **Primary Definition** | Ordered collection of record dictionaries representing table rows | Hash map mapping category labels to lists of grouped values | Hash map mapping unique keys directly to complete record objects |
| **Literal Syntax / Delimiters** | `[ {"key": val}, {"key": val} ]` | `{ "category": [val1, val2] }` | `{ id_key: {"id": id_key, ...} }` |
| **Permitted Operations** | `for row in list:`, `list.append(dict)`, `row["field"]` | `dict[key].append(val)`, `for k, v in dict.items()` | `dict[id_key]`, `if id in dict:`, `dict.get(id)` |
| **Type Invariant / Mutability** | Outer list mutable; inner dictionaries mutable | Outer dictionary mutable; inner lists mutable | Outer dictionary mutable; inner record dictionaries mutable |
| **Primary Access Pattern** | Sequential scan ($O(N)$ linear search across all rows) | Category jump ($O(1)$ key access) followed by list access | Instant retrieval ($O(1)$ hash lookup by primary key) |
| **Best Architectural Fit** | Searching across all records by arbitrary fields | Displaying grouped categories or dropdown options | High-frequency single-record lookups by primary ID |
| **Common Runtime Exception** | `KeyError` (missing field), `IndexError` (bad index) | `KeyError` (uninitialized category key) | `KeyError` (missing ID without `in` guard check) |

---

## 2. Real-World Mental Models & Conceptual Mapping

To select the correct data architecture and logic flow, developers rely on visual and physical mental models.

### 1. The Spreadsheet Table vs. The Labeled Storage Bins
- **List of Dictionaries (The Spreadsheet Table)**: Imagine a paper binder where each page is a table. Each line on the page is a single row (one dictionary) representing a specific entity (e.g., a pet or game character). The column headers (e.g., `"name"`, `"species"`, `"age"`) are identical keys across every row. To find all dragons, you must start at the top line and read down the page line by line.
- **Dictionary of Lists (The Labeled Bins)**: Imagine a physical wall of storage bins. Each bin has a label on the front (e.g., `"dragon"`, `"unicorn"`, `"griffin"`). Inside the `"dragon"` bin is a folder containing a list of names (`["Flamey", "Storm"]`). If you need all dragons, you do not scan the room; you walk directly to the bin labeled `"dragon"` and lift out the list.

### 2. The Linear Grid Search vs. The Phonebook Index
- **Nested Loop Search ($O(N \times M)$ Grid)**: Imagine a stack of 100 customer order sheets and a separate ledger of 100 customer profiles. To match each order to a customer, you take Order 1 and read through the customer ledger line by line until you find match #101. Then you take Order 2 and read through the entire customer ledger again from top to bottom. For $N$ orders and $M$ customers, you perform $N \times M$ manual line comparisons.
- **Dictionary Index ($O(1)$ Direct Jump)**: Before processing orders, you rearrange the customer ledger into an alphabetical Rolodex indexed by Customer ID. Now, when you pick up Order 1 (Customer #101), you flip directly to tab #101 in one motion. Total comparisons drop from $N \times M$ down to $N$.

### 3. The Conveyor Belt Assembly Line (Functional Pipelines & Helpers)
- **Loop Skeleton (The Conveyor Motor)**: The `for` loop acts as a factory conveyor belt. Its sole job is advancing the next raw component to the workstation. It handles bookkeeping, iteration count, and transport.
- **Per-Item Helper (The Robotic Workstation)**: A dedicated station positioned along the belt. It accepts a single raw item, performs precise mathematical or structural transformations (e.g., adding 8% tax and 5% discount), and returns the finished item back to the belt.
- **Pipeline Chaining**: Station 1 (`add_tax`) processes the raw item and hands the result directly to Station 2 (`add_shipping`), which hands its result directly to Station 3 (`apply_discount`).

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

---

## 3. Idiomatic Python Implementation & State Tracing

### Topic 1: The Scan-Test-Store Filter Pattern

Extracting records based on evaluation rules requires initializing a result list, scanning with a `for` loop, testing with boolean expressions, and storing matches with `.append()`.

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

---

### Topic 2: Incremental Grouping (Building a Dictionary of Lists)

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

---

### Topic 3: Building a Dictionary Index to Replace Nested Loops

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

---

### Topic 4: Functional Pipelines & Call Chaining

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

---

### Topic 5: Loop Skeleton vs. Per-Item Helper Interaction

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

---

## 4. Defensive Programming & Common Traps

When working with composite structures, nested loops, and functional pipelines, developers encounter specific runtime exceptions and logic errors.

### Trap 1: `KeyError` from Accessing Uninitialized Dictionary Buckets
- **Bug Description**: Attempting to invoke `.append()` on a dictionary key that has not yet been assigned a list object. Python raises a `KeyError` because the key does not exist.

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

---

### Trap 2: `KeyError` and Shape Mismatch in Dictionary Lookups
- **Bug Description**: Mismatching key data types (e.g., comparing string `"101"` to integer `101`) or building a dictionary with an improper structural shape (e.g., storing a list under key `"id"` rather than indexing records by ID).

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

---

### Trap 3: Mathematical Multiplier Errors (Percentage vs. Decimal)
- **Bug Description**: Using whole integer percentages directly in multiplication (e.g., multiplying by `8` for an 8% tax or `10` for a 10% discount) rather than proper decimal multipliers.

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

---

### Trap 4: Variable Shadowing Built-in Functions
- **Bug Description**: Naming loop variables or dictionary fields after Python built-in functions (e.g., `type`, `list`, `dict`), which overrides the built-in function in the local namespace.

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

---

### Trap 5: Moving Iteration Control into a Per-Item Helper
- **Bug Description**: Placing a `for` loop inside a helper function that is supposed to process only a single record. This creates confusion over loop ownership and causes redundant iterations.

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

---

## 5. Python Memory Mechanics, References & Scope

Understanding how Python handles object references, heap memory, and namespaces is essential when working with nested data structures.

### Dynamic Typing and Variable Binding
In Python, variables are not typed memory storage boxes. Instead, **variables are names (pointers) bound to objects residing in heap memory**. 
- Assignment (`x = {"name": "Aria"}`) creates a dictionary object in heap memory and binds the name `x` in the namespace to that object's memory address.
- Reassignment (`x = [1, 2, 3]`) binds `x` to a new object; it does not overwrite the old dictionary object if other references point to it.

### Composite Structures as Reference Containers
Lists and dictionaries do not contain physical data values directly; they store **memory addresses (references)** pointing to heap objects.
- In `characters = [{"name": "Aria"}, {"name": "Bron"}]`, the list object stores references to two distinct dictionary objects in heap memory.
- Each dictionary object stores key strings that map to references pointing to string or integer objects (e.g., `"Aria"`, `5`).

### Function Scope and Object Mutability
- When a mutable object (like a list or dictionary record) is passed as an argument to a function, Python uses **pass-by-assignment** (passing object references).
- Modifying a dictionary inside a helper function (e.g., `record["status"] = "Active"`) mutates the original object on the heap, making the change visible across all variables referencing that object.

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

---

## 6. Practical Integration / Mini Case Study

### Integrated Retail Order & Inventory State Manager

This script combines all Week 3 concepts into a single execution workflow:
1. **Filtering**: Extracting active valid orders.
2. **Dictionary Indexing**: Building an $O(1)$ lookup index for inventory items.
3. **Grouping**: Categorizing orders into customer tier buckets (`"VIP"`, `"Standard"`).
4. **Functional Pipeline**: Processing unit prices through tax, discount, and shipping functions.
5. **Loop Skeleton & Helpers**: Using single-purpose helper functions inside a clean main loop.

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

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

Analyze each code challenge line-by-line to trace variable reassignments, mathematical evaluations, and intermediate terminal outputs.

### Challenge A: Nested Pipeline with State Mutability & Decimals

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

#### Step-by-Step State Evaluation Table:
| Step / Line | Expression Evaluated | Intermediate State / Value | Notes |
| :--- | :--- | :--- | :--- |
| **Line 11** | `calc_step1(200)` | `200 * 1.05 = 210.0` | 5% added to base value |
| **Line 11** | `calc_step2(210.0, 10)` | `210.0 + 10 = 220.0` | $10 flat bonus added |
| **Line 11** | `calc_step3(220.0)` | `220.0 * 0.80 = 176.0` | 20% discount applied (keeps 80%) |
| **Line 12** | `f"Result: {176.0:.2f}"` | `"Result: 176.00"` | Formatted float output |

**Final Terminal Output:**
```text
Result: 176.00
```

---

### Challenge B: Incremental Grouping with Key Initializations

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

#### Step-by-Step State Evaluation Table:
| Iteration | Variable State (`t`, `i`) | `t not in bucket` Check | `bucket` Memory State After Append |
| :--- | :--- | :--- | :--- |
| **Start** | `bucket = {}` | N/A | `{}` |
| **Iter 1** | `t="fruit"`, `i="apple"` | `True` -> `bucket["fruit"] = []` | `{"fruit": ["apple"]}` |
| **Iter 2** | `t="veg"`, `i="carrot"` | `True` -> `bucket["veg"] = []` | `{"fruit": ["apple"], "veg": ["carrot"]}` |
| **Iter 3** | `t="fruit"`, `i="banana"` | `False` (skips initialization) | `{"fruit": ["apple", "banana"], "veg": ["carrot"]}` |

**Final Terminal Output:**
```text
Keys: ['fruit', 'veg']
Fruit count: 2
```

---

### Challenge C: Dictionary Index vs. Nested Loop Comparison Counter

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

#### Step-by-Step State Evaluation Table:
| Order Iteration | `item_id` | `item_id in catalog` Check | `loop_count` State | `item_name` Retrieved |
| :--- | :--- | :--- | :--- | :--- |
| **Iter 1** | `1` | `1 in catalog` (`True`) | `1` | `"Item A"` |
| **Iter 2** | `2` | `2 in catalog` (`True`) | `2` | `"Item B"` |
| **Iter 3** | `3` | `3 in catalog` (`True`) | `3` | `"Item C"` |

**Final Terminal Output:**
```text
Processed 3 orders in 3 comparisons.
```

---

### Challenge D: Dual Accumulators in Loop Skeleton with Per-Item Helper

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

#### Step-by-Step State Evaluation Table:
| Iteration | `s` | `curved` (`s + 5`) | `total_score` (`+ curved`) | `curved >= 85` | `passing_count` State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Iter 1** | `75` | `80` | `0 + 80 = 80` | `80 >= 85` (`False`) | `0` |
| **Iter 2** | `82` | `87` | `80 + 87 = 167` | `87 >= 85` (`True`) | `1` |
| **Iter 3** | `90` | `95` | `167 + 95 = 262` | `95 >= 85` (`True`) | `2` |
| **Post-Loop**| N/A | N/A | `avg_score = 262 / 3 = 87.3333...` | N/A | `passing_count = 2` |

**Final Terminal Output:**
```text
Avg: 87.3, Passing: 2
```

---

*End of Master Reference Document.*
