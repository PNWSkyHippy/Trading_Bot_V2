# PY103 - Week 2 Master Reference: Methods, Object State, and Class Dynamics

> **Welcome**: This Master Reference Document synthesizes all core concepts, mental models, memory mechanics, and code traces from Week 2 of PY103 into an authoritative, self-contained reference guide for Python Object-Oriented Programming (OOP).

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

### Primary Keywords, Functions, and Concepts

* **`class`**: A user-defined compound type and factory blueprint that specifies the attributes (state variables) and methods (behaviors) common to all objects instantiated from it.
* **`object` / Instance**: A concrete entity instantiated in heap memory based on a class blueprint. Each instance possesses its own identity and namespace.
* **`__init__` (Constructor)**: A special dunder (double-underscore) method automatically invoked by Python immediately after a new object is created in memory. Its primary role is to initialize instance attributes and set up a valid starting state.
* **`self`**: The explicit first parameter in instance methods. When a method is called on an object, Python automatically passes the calling instance as the `self` argument, allowing the method to access and modify that specific object's namespace.
* **Instance Attributes**: Variables bound to a specific instance via `self.attribute_name` inside methods or `instance.attribute_name` externally. They store unique per-object data.
* **Class Attributes**: Variables defined directly inside the class block (outside any method). They are bound to the class object itself and shared across all instances that do not override them.
* **Attribute Shadowing (Overriding)**: The mechanism where assigning a value to `instance.attribute` creates a new key in the instance's private dictionary (`__dict__`), hiding ("shadowing") a class attribute of the same name for that specific instance.
* **Read-Only Methods**: Instance methods that access stored state through `self` to compute or display information without performing any attribute assignments (`self.attr = ...`).
* **State-Changing Methods**: Instance methods that mutate an object's internal attributes via `self`, permanently transitioning the object to a new state that persists across future interactions.
* **`is` Operator**: The identity operator. Evaluates to `True` if and only if two variables reference the exact same object in heap memory (`id(a) == id(b)`).
* **`==` Operator**: The equality operator. Evaluates to `True` if the underlying data values stored in two objects match, regardless of whether they reside at the same memory location.
* **`ValueError`**: A built-in exception raised when a function or operation receives an argument with the correct data type but an inappropriate value (e.g., `int("abc")`).
* **`TypeError`**: A built-in exception raised when an operation or function is applied to an object of an inappropriate type, or when a function call is missing required arguments.

---

### Side-by-Side Comparison Matrix

| Feature / Spec | Instance Attributes | Class Attributes | Aliased Variables / Identity References |
| :--- | :--- | :--- | :--- |
| **Definition** | Unique data stored inside individual instance namespaces. | Shared data stored once on the parent class namespace. | Multiple variable names pointing to the exact same heap memory object. |
| **Syntax / Delimiters** | Defined inside `__init__` via `self.attr_name = value`. | Defined inside `class` body via `attr_name = value`. | Assignment statement `var2 = var1`. |
| **Permitted Operators** | Attribute access (`obj.attr`), assignment (`obj.attr = val`). | Class access (`Class.attr`), instance read (`obj.attr`). | Identity check (`var1 is var2`), Equality check (`var1 == var2`). |
| **Type Invariant / Mutability** | Mutable per object; changes affect only that instance. | Shared across instances unless shadowed on an instance. | Changes made via one name immediately reflect on all aliases. |
| **Common Runtime Error** | `AttributeError` if accessed before assignment on `self`. | Unintended instance shadowing when assigning via `obj.attr`. | Unexpected side effects caused by mutating shared state via alias. |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: Shelter Dogs and Name Tags (Aliasing vs. Distinct Instances)
Imagine a pet shelter with a physical dog in a room.
* **Aliasing (`is` = True)**: If the dog wears two name tags—one reading `"Luna"` and another reading `"Favorite"`—there is still only **one physical dog**. If you update `"Favorite"`'s collar color, `"Luna"`'s collar color changes simultaneously because both tags refer to the exact same physical animal in memory.
* **Distinct Instances (`is` = False, `==` = True)**: If two separate dogs sit in adjacent cages, and both happen to be named `"Luna"` and are `3` years old, they are **two distinct entities**. Changing the age of Dog 1 leaves Dog 2 entirely unaffected.

### Analogy 2: Car Factory Blueprints vs. Vehicle Serial Numbers
* **Class Attribute (`Car.wheels = 4`)**: The master engineering blueprint specifies that all standard cars produced by this factory have 4 wheels. This fact exists once at the factory level.
* **Instance Attribute (`self.color`, `self.vin`)**: When an individual car rolls off the line, it gets its own custom color and unique vehicle identification number stored on its chassis. Modifying the paint on Car #101 does not repaint Car #102.

### Analogy 3: Library Card Catalog System (Inter-Object Communication)
In a library system, a `Reader` object and a `Book` object are distinct entities that communicate via method calls:
* A `Reader` possesses a `name` attribute and a `borrow(book)` method.
* A `Book` possesses `title` and `available` attributes, alongside a `check_out()` method.
* When `reader.borrow(book)` executes, the `Reader` object delegates the availability check to `book.check_out()`. The `Book` object updates its own internal state (`available = False`) and returns a boolean status, allowing the `Reader` object to react and display the result.

---

### Conceptual Memory & Execution Diagrams

```
+-----------------------------------------------------------------------+
|                           HEAP MEMORY                                 |
|                                                                       |
|  [ Class: Pet ]                                                       |
|  +-----------------------------------+                                |
|  | kind = "pet"                     |  <--- Shared Class Namespace    |
|  | describe(self)                   |                                 |
|  +-----------------------------------+                                |
|                   ^                                                   |
|                   | (instance-of)                                     |
|         +---------+---------+                                         |
|         |                   |                                         |
|  [ Object: luna ]    [ Object: max_pet ]                              |
|  +---------------+   +-------------------+                            |
|  | name = "Luna" |   | name = "Max"      | <--- Instance Namespaces   |
|  | age  = 3      |   | age  = 5          |                            |
|  +---------------+   +-------------------+                            |
|         ^                   ^                                         |
+---------|-------------------|-----------------------------------------+
          |                   |
   STACK: luna             max_pet
```

```
+-----------------------------------------------------------------------+
|                      METHOD CALL EXECUTION FLOW                       |
|                                                                       |
|   luna.describe()                                                     |
|        |                                                              |
|        v                                                              |
|   Pet.describe(luna)   <--- Python automatically binds caller to self |
|        |                                                              |
|        v                                                              |
|   def describe(self):                                                 |
|       print(self.name) ---> evaluates self.name as luna.name ("Luna") |
+-----------------------------------------------------------------------+
```

---

## 3. Idiomatic Python Implementation & State Tracing

### Topic A: Object Instantiation & Constructor Validation

```python
class Pet:
    # Class attribute shared across all standard instances
    species = "Domestic Pet"

    def __init__(self, name="Unknown", age=0):
        # Validate name input: fallback to 'Unknown' if empty or invalid string
        if isinstance(name, str) and len(name.strip()) > 0:
            self.name = name.strip()  # State: self.name assigned validated string
        else:
            self.name = "Unknown"    # State: fallback value applied

        # Validate age input: fallback to 0 if negative
        if isinstance(age, (int, float)) and age >= 0:
            self.age = age            # State: self.age assigned validated numeric
        else:
            self.age = 0              # State: fallback value applied for bad/negative age

# Trace 1: Valid instantiation
pet1 = Pet("Luna", 3)
# State: pet1.name = "Luna", pet1.age = 3
print(f"{pet1.name} is {pet1.age} years old.")
# Console Output: Luna is 3 years old.

# Trace 2: Invalid inputs handled via fallback
pet2 = Pet("", -5)
# State: pet2.name = "Unknown", pet2.age = 0
print(f"{pet2.name} is {pet2.age} years old.")
# Console Output: Unknown is 0 years old.
```

---

### Topic B: Read-Only vs. State-Changing Methods

```python
class PetAccount:
    def __init__(self, name, happiness=5):
        self.name = name            # Initial State
        self.happiness = happiness  # Initial State: 5

    def get_status(self):
        # Read-Only Method: Reads attributes without modifying state
        # Returns formatted string derived from self.happiness
        return f"{self.name} happiness level is {self.happiness}"

    def play(self, bonus=1):
        # State-Changing Method: Mutates internal attribute self.happiness
        self.happiness = self.happiness + bonus  # State transition
        return self.happiness

# Instantiate object
pet = PetAccount("Fido", 5)

# Call Read-Only Method
status1 = pet.get_status()
# Intermediate Value: status1 = "Fido happiness level is 5"
print(status1)
# Console Output: Fido happiness level is 5

# Call State-Changing Method
new_happy = pet.play(2)
# Step: self.happiness transitions from 5 to 7 (5 + 2)
# Intermediate Value: new_happy = 7
print(f"New happiness: {new_happy}")
# Console Output: New happiness: 7

# Verify persistent state change via Read-Only Method
status2 = pet.get_status()
# Intermediate Value: status2 = "Fido happiness level is 7"
print(status2)
# Console Output: Fido happiness level is 7
```

---

### Topic C: Class Attributes vs. Instance Attributes & Shadowing

```python
class Car:
    wheels = 4  # Shared Class Attribute

    def __init__(self, model):
        self.model = model  # Instance Attribute

car1 = Car("Sedan")
car2 = Car("Coupe")

# Initial lookup: Both instances access the shared class attribute
print(car1.wheels, car2.wheels, Car.wheels)
# Console Output: 4 4 4

# Action 1: Mutate Class Attribute directly on the class
Car.wheels = 6
# State: Car.__dict__['wheels'] updated to 6; car1 and car2 read updated value
print(car1.wheels, car2.wheels, Car.wheels)
# Console Output: 6 6 6

# Action 2: Assign wheels on car1 instance (Attribute Shadowing)
car1.wheels = 3
# State: car1.__dict__['wheels'] created with value 3 (Shadowing Class Attribute)
# State: car2 and Car remain unaffected
print(car1.wheels, car2.wheels, Car.wheels)
# Console Output: 3 6 6
```

---

### Topic D: Inter-Object Method Execution

```python
class Book:
    def __init__(self, title):
        self.title = title
        self.available = True  # Initial State: Available for checkout

    def check_out(self):
        if self.available:
            self.available = False  # Mutate state: mark unavailable
            return True             # Transition successful
        return False                # Already checked out

class Reader:
    def __init__(self, name):
        self.name = name

    def borrow(self, book):
        # Inter-object call: Reader invokes Book.check_out()
        success = book.check_out()
        if success:
            print(f"{self.name} successfully borrowed '{book.title}'")
        else:
            print(f"{self.name} failed: '{book.title}' is unavailable")

book = Book("The Hobbit")
reader1 = Reader("Alice")
reader2 = Reader("Bob")

# Execution Trace 1: First checkout attempt
reader1.borrow(book)
# Step 1: reader1.borrow(book) calls book.check_out()
# Step 2: book.available is True -> mutated to False -> returns True
# Console Output: Alice successfully borrowed 'The Hobbit'

# Execution Trace 2: Second checkout attempt on same book object
reader2.borrow(book)
# Step 1: reader2.borrow(book) calls book.check_out()
# Step 2: book.available is False -> returns False
# Console Output: Bob failed: 'The Hobbit' is unavailable
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Missing Required Constructor Arguments
When `__init__` parameters lack default values, instantiating the class without mandatory positional arguments raises a runtime `TypeError`.

```python
# INCORRECT: Missing required positional arguments
class Pet:
    def __init__(self, name, age):
        self.name = name
        self.age = age

# Attempting instantiation without arguments:
# bad_pet = Pet()
# Error: TypeError: __init__() missing 2 required positional arguments: 'name' and 'age'
```

```python
# CORRECT: Provide default parameters to ensure safe instantiation
class Pet:
    def __init__(self, name="Unknown", age=0):
        self.name = name
        self.age = age

# Safe instantiation with or without arguments
safe_pet1 = Pet()             # State: name="Unknown", age=0
safe_pet2 = Pet("Luna", 3)    # State: name="Luna", age=3
print(f"{safe_pet1.name}, {safe_pet2.name}")
# Console Output: Unknown, Luna
```

---

### Trap 2: Double Conversion & "Fake Protection" in Try/Except
Attempting type conversions inside a `try` block, discarding the result, and then re-calling the conversion outside the `try` block creates an unhandled exception vulnerability.

```python
# INCORRECT: Discarded conversion result inside try block
class Position:
    def __init__(self, price):
        try:
            temp = float(price)
        except ValueError:
            price = 0.0
        # CRASH: If price was a non-convertible type like a list or bad object,
        # calling float(price) outside try/except causes uncaught exception!
        self.price = float(price)
```

```python
# CORRECT: Convert once, catch ValueError and TypeError, assign safely
class Position:
    def __init__(self, price):
        try:
            validated_price = float(price)
            if validated_price < 0:
                validated_price = 0.0
        except (ValueError, TypeError):
            validated_price = 0.0

        self.price = validated_price  # Single safe assignment

pos1 = Position("150.50")  # Valid float string -> 150.5
pos2 = Position("abc")     # ValueError caught -> 0.0
pos3 = Position(None)      # TypeError caught  -> 0.0
print(pos1.price, pos2.price, pos3.price)
# Console Output: 150.5 0.0 0.0
```

---

### Trap 3: Unintended Instance Attribute Shadowing
Assigning a value to a class attribute name via an *instance* reference creates an instance attribute that shadows the class attribute, leaving the class attribute and other instances untouched.

```python
# INCORRECT: Attempting to update a class default via an instance reference
class Animal:
    category = "Wildlife"

a1 = Animal()
a2 = Animal()

a1.category = "Domestic"  # BUG: Creates a1.__dict__['category'] = "Domestic"
# Does NOT update Animal.category or a2.category!
print(a1.category, a2.category, Animal.category)
# Console Output: Domestic Wildlife Wildlife
```

```python
# CORRECT: Mutate class attribute via the class name explicitly
class Animal:
    category = "Wildlife"

a1 = Animal()
a2 = Animal()

Animal.category = "Domestic"  # Updates shared class state directly
print(a1.category, a2.category, Animal.category)
# Console Output: Domestic Domestic Domestic
```

---

## 5. Python Memory Mechanics, References & Scope

### Variable Binding and Heap Memory
In Python, variables do not store values directly; they are **name bindings (references)** pointing to objects in heap memory.
1. **Dynamic Binding**: Evaluating `x = Pet()` creates a `Pet` object in heap memory and binds the identifier `x` in the local namespace to that memory address.
2. **Aliasing**: Executing `y = x` copies the memory address reference, not the underlying object. Both `x` and `y` point to the exact same heap memory block.
3. **Namespace Resolution Order**: When evaluating `obj.attr`, Python performs an attribute lookup in the following order:
   * Step 1: Search `obj.__dict__` (Instance Namespace).
   * Step 2: Search `type(obj).__dict__` (Class Namespace).
   * Step 3: Search parent classes in the Method Resolution Order (MRO).
   * Step 4: Raise `AttributeError` if not found in any namespace.

---

### Namespace & Reference Diagram

```
LOCAL NAMESPACE (Stack)              HEAP MEMORY
+--------------------+               +----------------------------------+
|                    |               | Class Object: Pet                |
|  Pet -------------->-------------> | - __name__: "Pet"                |
|                    |               | - species: "Domestic Pet"        |
|                    |               +----------------------------------+
|                    |                                ^
|                    |                                | (class pointer)
|  luna ------------>-------------> +----------------------------------+
|                    |              | Instance Object (0x7f8a)         |
|  favorite_pet ---->-------------> | - name: "Luna"                   |
|                    |              | - age: 3                         |
|                    |              +----------------------------------+
|                    |
|                    |              +----------------------------------+
|  pet1 ------------>-------------> | Instance Object (0x7f8b)         |
|                    |              | - name: "Luna"                   |
|                    |              | - age: 3                         |
+--------------------+              +----------------------------------+

Identity Evaluation Traces:
- (luna is favorite_pet)    ==> True  (Both point to heap address 0x7f8a)
- (luna is pet1)            ==> False (0x7f8a != 0x7f8b)
- (luna.name == pet1.name)  ==> True  ("Luna" == "Luna")
```

---

## 6. Practical Integration / Mini Case Study

### Financial Futures Position Tracker (`MNQPosition`)

This comprehensive script demonstrates:
1. Class attributes (`symbol`, `point_value`) vs Instance attributes (`entry_price`, `current_price`, `quantity`).
2. Robust input validation handling both `ValueError` and `TypeError` using explicit fallbacks.
3. State-changing methods (`update_price`) and read-only/computed methods (`unrealized_pnl`).
4. Inter-object interaction with a position portfolio manager.

```python
class MNQPosition:
    # Shared Class Attributes for Micro E-mini Nasdaq futures
    symbol = "MNQ"
    point_value = 2.0  # $2 per index point multiplier

    def __init__(self, entry_price, current_price, quantity):
        # Validate entry_price
        try:
            p_entry = float(entry_price)
            self.entry_price = p_entry if p_entry > 0 else 0.0
        except (ValueError, TypeError):
            self.entry_price = 0.0

        # Validate current_price
        try:
            p_curr = float(current_price)
            self.current_price = p_curr if p_curr > 0 else self.entry_price
        except (ValueError, TypeError):
            self.current_price = self.entry_price

        # Validate quantity (positive = long, negative = short, 0 = flat)
        try:
            self.quantity = int(quantity)
        except (ValueError, TypeError):
            self.quantity = 0

    def update_price(self, new_price):
        # State-Changing Method: Updates live market price
        try:
            p_new = float(new_price)
            if p_new > 0:
                self.current_price = p_new
                return True
        except (ValueError, TypeError):
            pass
        return False

    def unrealized_pnl(self):
        # Read-Only Derived Method: Calculates current PnL in dollars
        price_diff = self.current_price - self.entry_price
        return price_diff * self.point_value * self.quantity


class TradingAccount:
    def __init__(self, account_id, starting_balance=10000.0):
        self.account_id = account_id
        self.balance = float(starting_balance) if starting_balance > 0 else 10000.0
        self.positions = []  # List storing MNQPosition objects

    def add_position(self, position):
        if isinstance(position, MNQPosition):
            self.positions.append(position)

    def total_unrealized_pnl(self):
        # Calculates total PnL across all active position objects
        total = 0.0
        for pos in self.positions:
            total += pos.unrealized_pnl()  # Inter-object method call
        return total

    def print_portfolio_summary(self):
        print(f"=== Account: {self.account_id} ===")
        print(f"Cash Balance: ${self.balance:,.2f}")
        total_pnl = self.total_unrealized_pnl()
        print(f"Unrealized PnL: ${total_pnl:,.2f}")
        print(f"Net Equity: ${self.balance + total_pnl:,.2f}")


# =====================================================================
# STEP-BY-STEP EXECUTION TRACE
# =====================================================================

# Step 1: Initialize Trading Account
acct = TradingAccount("ACC-9982", 25000.0)
# State: acct.balance = 25000.0, acct.positions = []

# Step 2: Instantiate Valid Long Position (10 contracts MNQ entered at 18,000)
pos1 = MNQPosition(entry_price=18000, current_price=18050, quantity=10)
# State: pos1.entry_price = 18000.0, pos1.current_price = 18050.0, pos1.quantity = 10
# PnL Calc: (18050 - 18000) * 2.0 * 10 = +$1,000.00

# Step 3: Instantiate Short Position with Bad Price String (Handled via Try/Except)
pos2 = MNQPosition(entry_price=18100, current_price="INVALID_MARKET_DATA", quantity=-5)
# Validation Trace: current_price conversion fails -> falls back to entry_price (18100.0)
# State: pos2.entry_price = 18100.0, pos2.current_price = 18100.0, pos2.quantity = -5
# PnL Calc: (18100 - 18100) * 2.0 * -5 = $0.00

# Step 4: Add Positions to Account
acct.add_position(pos1)
acct.add_position(pos2)

# Step 5: Initial Portfolio Output Trace
acct.print_portfolio_summary()
# Console Output:
# === Account: ACC-9982 ===
# Cash Balance: $25,000.00
# Unrealized PnL: $1,000.00
# Net Equity: $26,000.00

# Step 6: Market Price Movement (Update pos2 current price to 18,050 -> Short profit)
pos2.update_price(18050)
# State: pos2.current_price updated to 18050.0
# pos2 PnL Calc: (18050 - 18100) * 2.0 * -5 = (-50) * 2.0 * -5 = +$500.00
# Total Unrealized PnL: $1,000.00 (pos1) + $500.00 (pos2) = $1,500.00

# Step 7: Updated Portfolio Output Trace
print("
--- After Market Update ---")
acct.print_portfolio_summary()
# Console Output:
# --- After Market Update ---
# === Account: ACC-9982 ===
# Cash Balance: $25,000.00
# Unrealized PnL: $1,500.00
# Net Equity: $26,500.00
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Identity vs. Equality with Object Aliasing

```python
class Token:
    def __init__(self, symbol, amount):
        self.symbol = symbol
        self.amount = amount

t1 = Token("BTC", 2)
t2 = Token("BTC", 2)
t3 = t1

t3.amount = 5

print(t1 is t2)           # Line 1
print(t1 is t3)           # Line 2
print(t1.amount == t2.amount) # Line 3
print(t1.amount == t3.amount) # Line 4
```

**Diagnostic Line-by-Line Trace**:
* `t1` and `t2` are created via separate `Token(...)` calls -> two distinct memory addresses.
* `t3 = t1` creates an alias (`t3` points to the exact same object as `t1`).
* `t3.amount = 5` mutates the single shared object in memory referenced by both `t3` and `t1`.
* **Line 1 Evaluation**: `t1 is t2` -> `False` (different heap addresses).
* **Line 2 Evaluation**: `t1 is t3` -> `True` (same heap address).
* **Line 3 Evaluation**: `t1.amount == t2.amount` -> `5 == 2` -> `False`.
* **Line 4 Evaluation**: `t1.amount == t3.amount` -> `5 == 5` -> `True`.

**Terminal Output**:
```text
False
True
False
True
```

---

### Challenge B: Class Attribute Mutation vs. Instance Shadowing

```python
class Widget:
    catalog_code = "W-100"

    def __init__(self, name):
        self.name = name

w1 = Widget("Alpha")
w2 = Widget("Beta")

w1.catalog_code = "W-MAX"
Widget.catalog_code = "W-200"

print(w1.catalog_code)  # Line 1
print(w2.catalog_code)  # Line 2
print(Widget.catalog_code) # Line 3
```

**Diagnostic Line-by-Line Trace**:
* `w1.catalog_code = "W-MAX"` creates an instance attribute in `w1.__dict__`, shadowing `Widget.catalog_code` for `w1` only.
* `Widget.catalog_code = "W-200"` updates the class attribute in `Widget.__dict__` from `"W-100"` to `"W-200"`.
* **Line 1 Evaluation**: `w1.catalog_code` reads `w1.__dict__['catalog_code']` -> `"W-MAX"`.
* **Line 2 Evaluation**: `w2.catalog_code` finds no instance attribute, falls back to `Widget.catalog_code` -> `"W-200"`.
* **Line 3 Evaluation**: `Widget.catalog_code` reads class attribute -> `"W-200"`.

**Terminal Output**:
```text
W-MAX
W-200
W-200
```

---

### Challenge C: Constructor Validation with Mixed Error Fallbacks

```python
class TemperatureSensor:
    def __init__(self, reading):
        try:
            val = float(reading)
            if val < -273.15:
                val = -273.15
        except (ValueError, TypeError):
            val = 0.0

        self.reading = val

s1 = TemperatureSensor(25.5)
s2 = TemperatureSensor("-300.0")
s3 = TemperatureSensor("FAULT_CODE")
s4 = TemperatureSensor(None)

print(s1.reading)  # Line 1
print(s2.reading)  # Line 2
print(s3.reading)  # Line 3
print(s4.reading)  # Line 4
```

**Diagnostic Line-by-Line Trace**:
* `s1`: `float(25.5)` succeeds (25.5 >= -273.15) -> `25.5`.
* `s2`: `float("-300.0")` succeeds (-300.0 < -273.15) -> clamped to fallback `-273.15`.
* `s3`: `float("FAULT_CODE")` raises `ValueError` -> caught by except -> set to `0.0`.
* `s4`: `float(None)` raises `TypeError` -> caught by except -> set to `0.0`.

**Terminal Output**:
```text
25.5
-273.15
0.0
0.0
```

---

### Challenge D: Inter-Object State Mutation Flow

```python
class Account:
    def __init__(self, balance):
        self.balance = balance

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

class ATM:
    def process_transaction(self, account, amount):
        if account.withdraw(amount):
            return f"Dispensed ${amount}"
        return "Insufficient Funds"

acc = Account(100)
atm = ATM()

res1 = atm.process_transaction(acc, 60)
res2 = atm.process_transaction(acc, 60)

print(res1)         # Line 1
print(res2)         # Line 2
print(acc.balance)  # Line 3
```

**Diagnostic Line-by-Line Trace**:
* Initial State: `acc.balance = 100`.
* First Call: `atm.process_transaction(acc, 60)` -> calls `acc.withdraw(60)`.
  * `acc.balance >= 60` (100 >= 60) is `True`.
  * `acc.balance` becomes `40` (100 - 60).
  * `withdraw` returns `True` -> `res1 = "Dispensed $60"`.
* Second Call: `atm.process_transaction(acc, 60)` -> calls `acc.withdraw(60)`.
  * `acc.balance >= 60` (40 >= 60) is `False`.
  * `withdraw` returns `False` -> `res2 = "Insufficient Funds"`.
* **Line 1 Evaluation**: `res1` -> `"Dispensed $60"`.
* **Line 2 Evaluation**: `res2` -> `"Insufficient Funds"`.
* **Line 3 Evaluation**: `acc.balance` -> `40`.

**Terminal Output**:
```text
Dispensed $60
Insufficient Funds
40
```
