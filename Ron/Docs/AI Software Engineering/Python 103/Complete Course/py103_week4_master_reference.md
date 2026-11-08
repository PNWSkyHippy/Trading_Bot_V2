# PY103 - Week 4 Master Reference: Object-Oriented Programming Principles & Architecture
> **Welcome Blurb**: This publication-grade Master Reference Document synthesizes all core concepts, mental models, memory mechanics, object-oriented design patterns, and code traces from Week 4 of PY103 into an authoritative, self-contained reference guide. Grounded directly in the curriculum, this document covers Encapsulation, Internal Attributes, State Validation and Clamping, Inheritance, Method Overriding, Composition ("has-a" vs. "is-a"), Polymorphism, Class vs. Instance Attributes, and Object String Representation (`__str__` vs. `__repr__`).

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

### Formal Definitions

- **Class**: A user-defined logical blueprint and data type that encapsulates data structures (attributes) and behavior routines (methods) into a unified entity.
- **Instance / Object**: A concrete, instantiated realization of a class allocated in memory, maintaining its own distinct state space via an internal instance dictionary (`__dict__`).
- **Encapsulation**: The object-oriented architectural principle asserting that an object owns and manages its own state. Direct external access to raw state is restricted in favor of controlled interface operations.
- **Internal Attribute Convention (`_attribute`)**: Python's standard naming convention where an attribute name begins with a single leading underscore. It signifies to external developers that the variable is managed internally by the object ("a gentle coder's agreement").
- **Accessor Methods (Getters & Setters)**:
  - **Getter**: An inspector method whose sole function is to read and return an object's internal attribute value without mutating state.
  - **Setter / State Guardian**: A mutator method that accepts a proposed new value, validates or clamps it against system invariants (such as range boundaries), and updates internal state safely.
- **Inheritance (`is-a` Relationship)**: A foundational mechanism enabling a specialized subclass to acquire attributes and behaviors from a general parent (base) class without redundant code duplication.
- **Method Overriding**: The process by which a subclass redefines a method with the exact same identifier as one in its parent class to provide specialized behavior tailored to the subclass.
- **Composition (`has-a` Relationship)**: A software design pattern where a complex object contains one or more instances of other classes as internal components, delegating specialized tasks to them.
- **Polymorphism**: The object-oriented principle where a single, unified interface (a shared method identifier like `.speak()` or `.move()`) produces distinct class-specific behaviors depending on the target object's class.
- **Class Attributes vs. Instance Attributes**:
  - **Class Attribute**: A variable declared directly inside the class body, shared across all instances of that class.
  - **Instance Attribute**: A variable bound to `self` inside instance methods (typically `__init__`), unique to each individual object instance.
- **String Representation (`__str__` vs. `__repr__`)**:
  - **`__str__`**: A special dunder method returning a clean, human-readable string representation of an object, automatically invoked by `print()` and `str()`.
  - **`__repr__`**: A special dunder method returning an unambiguous, developer-focused string representation suitable for inspection and debugging.

---

### Side-by-Side Comparison Matrices

#### Matrix 1: Architectural Paradigm Comparison

| Feature / Spec | Encapsulation (Accessors) | Inheritance (Subclassing) | Composition (Has-a Delegation) |
| :--- | :--- | :--- | :--- |
| **Primary Purpose** | Protects internal state integrity and enforces domain boundaries | Promotes code reusability by establishing specialized sub-types | Combines modular components into complex composite systems |
| **Linguistic Design Rule** | "An object owns and guards its data" | "Class A **is a** specialized type of Class B" | "Class A **has a** or uses an instance of Class B" |
| **Syntax / Delimiters** | `self._attribute` + `get_x()` / `set_x()` | `class Subclass(Parent):` | `self.component = Component()` |
| **Permitted Operations** | State reading, validation checking, and boundary clamping | Method execution, attribute acquisition, and method overriding | Delegation of sub-tasks to internal component instances |
| **Type Invariant / Mutability** | Preserves object invariants (e.g., clamping health between 0 and 100) | Subclass maintains parent type invariant while adding specialized state | Composite object manages life cycle and state of contained objects |
| **Common Runtime Error** | `AttributeError` via typo or direct variable assignment bypass | Incorrect MRO resolution or missing parent constructor execution | `AttributeError` when delegating to an uninitialized component |

#### Matrix 2: Object String Representation & Attribute Scope

| Feature / Spec | User Display (`__str__`) | Developer Inspection (`__repr__`) | Class Attributes | Instance Attributes |
| :--- | :--- | :--- | :--- | :--- |
| **Target Audience** | End users and general terminal output | Developers, maintainers, and interactive debuggers | All instances sharing common class state | Single distinct object instance |
| **Invocation Context** | `print(obj)` or `str(obj)` | REPL evaluation, `repr(obj)`, or collection printing | `ClassName.attr` or `self.attr` (read-only) | `self.attr` inside instance methods |
| **Return Requirement** | Must return a string (`str`) | Must return a string (`str`), ideally valid Python code | Any valid Python object/data type | Any valid Python object/data type |
| **Default Fallback** | Falls back to `__repr__` if `__str__` is omitted | Defaults to `<ClassName object at 0x...>` | Shared memory address across instances | Dedicated entry in instance `__dict__` |
| **Common Runtime Error** | `TypeError` if non-string is returned | `TypeError` if non-string is returned | Unintended instance shadowing via `self.attr = x` | `AttributeError` if accessed prior to `__init__` binding |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: The Bank Vault & State Guardian (Encapsulation & Setters)

Imagine a high-security bank vault holding monetary gold reserves. If external clients could walk inside and directly adjust the gold balance (`wallet._gold = -500`), the system would collapse into an impossible negative state.

Instead, encapsulation positions a **State Guardian / Teller** (the setter method) at the entrance. When outside code proposes an update (`wallet.spend(amount)`), the guardian evaluates the input against strict validation rules. If a value is out of bounds, the guardian clamps or rejects it before updating internal storage (`_gold`).

```
[ Outside Code ] ---> Proposes value (-10) ---> [ Setter Guardian: set_health() ]
                                                       |
                                                       v
                                            Is value < 0? YES!
                                           Clamp input to 0
                                                       |
                                                       v
                                          [ Internal State: self._health = 0 ]
```

---

### Analogy 2: Lineage Tree vs. Modular Toolbelt ("Is-A" vs. "Has-A")

- **Inheritance ("is-a")**: A `Dog` **is a** `Pet`. Just as a biological child inherits DNA from a parent, a `Dog` subclass automatically inherits attributes (`_name`) and behaviors (`eat()`) from the base `Pet` class without re-writing code.
- **Composition ("has-a")**: A `Player` **has a** `Wallet`, or a `Line3D` **has** two `Point3D` endpoints. A player is not a specialized type of wallet. Instead, the player holds a wallet inside their inventory toolbelt to perform monetary transactions.

```
INHERITANCE ("is-a"):                      COMPOSITION ("has-a"):

   +-------------------+                      +-------------------+
   |   Pet (Parent)    |                      |   Player          |
   +-------------------+                      |  - name           |
             ^                                |  - wallet --------+---> [ Wallet Object ]
             | (inherits)                     +-------------------+      |  - _gold: 100 |
   +-------------------+                                                 +---------------+
   |   Dog (Subclass)  |
   +-------------------+
```

---

### Analogy 3: The Universal Remote Interface (Polymorphism)

Imagine a universal media remote with a single "Play" button. When directed at a DVD Player, pressing "Play" spins an optical disc. When directed at a streaming stick, it fetches a network stream. When directed at an automated synth, it triggers audio output.

The external interface command (`.play()` or `.speak()`) remains identical across all devices. Each individual object class supplies its own specialized internal method implementation.

```
Unified Caller Command: device.speak()
          |
   +------+------+------+
   |             |      |
   v             v      v
[ Pet ]       [ Dog ]  [ Cat ]
   |             |      |
"Generic"     "Woof!"  "Meow!"
```

---

## 3. Idiomatic Python Implementation & State Tracing

### Topic 1: Encapsulation with Internal State & Boundary Clamping

```python
class Pet:
    """Demonstrates state encapsulation and boundary validation clamping."""

    def __init__(self, name, health):
        self._name = name  # Internal attribute (gentleman's agreement)
        self._health = 0  # Pre-initialize internal state
        self.set_health(
            health
        )  # Route through setter guardian for initial validation

    def get_name(self):
        """Getter: Reads internal _name without mutating state."""
        return self._name  # State read: returns str

    def get_health(self):
        """Getter: Reads internal _health without mutating state."""
        return self._health  # State read: returns int

    def set_health(self, new_value):
        """Setter / Guardian: Clamps proposed health values strictly between 0 and 100."""
        if new_value < 0:  # Boundary check: lower limit violation
            self._health = 0  # Clamp negative inputs to 0
        elif new_value > 100:  # Boundary check: upper limit violation
            self._health = 100  # Clamp excess inputs to 100
        else:
            self._health = new_value  # Valid input accepted directly
        return self._health  # Return updated state value


# --- Execution State Trace ---
pet = Pet(
    "Shadow", 80
)  # Instantiation -> _name="Shadow", set_health(80) -> _health=80
print(pet.get_health())  # Output: 80 | _health remains 80

pet.set_health(150)  # Call setter with 150 -> 150 > 100 -> Clamped to 100
print(pet.get_health())  # Output: 100 | _health updated to 100

pet.set_health(-25)  # Call setter with -25 -> -25 < 0 -> Clamped to 0
print(pet.get_health())  # Output: 0 | _health updated to 0
```

---

### Topic 2: Inheritance & Method Overriding

```python
class Vehicle:
    """Base parent class defining core vehicle behavior."""

    def __init__(self, brand):
        self._brand = brand  # Internal attribute initialized in parent

    def get_brand(self):
        """Inherited getter method."""
        return self._brand  # Returns internal _brand string

    def start(self):
        """Generic parent method to be overridden by subclasses."""
        return "Vehicle starting..."  # Generic baseline output


class Car(Vehicle):
    """Subclass overriding parent method with specialized behavior."""

    def start(self):
        """Overridden method: Replaces generic baseline with car engine ignition."""
        return "Car engine starting with a key or button."  # Specialized output


class Bicycle(Vehicle):
    """Subclass inheriting parent behavior without overriding start()."""

    pass  # Retains parent start() implementation directly


# --- Execution State Trace ---
v = Vehicle("GenericCorp")  # Instantiation -> v._brand = "GenericCorp"
c = Car("Tesla")  # Subclass instantiation -> inherits Vehicle.__init__ -> c._brand = "Tesla"
b = Bicycle("Trek")  # Subclass instantiation -> inherits Vehicle.__init__ -> b._brand = "Trek"

print(v.start())  # Output: Vehicle starting... (Uses Vehicle.start)
print(
    c.start()
)  # Output: Car engine starting with a key or button. (Uses Car.start override)
print(
    b.start()
)  # Output: Vehicle starting... (Falls back to inherited Vehicle.start)
print(b.get_brand())  # Output: Trek (Uses inherited get_brand method)
```

---

### Topic 3: Composition Patterns

```python
class Wallet:
    """Component class managing monetary balances and expenditure integrity."""

    def __init__(self, initial_gold=0):
        self._gold = 0  # Initialize internal balance
        self.deposit(initial_gold)  # Route through deposit guardian

    def get_gold(self):
        """Getter for internal gold balance."""
        return self._gold  # Returns current int balance

    def deposit(self, amount):
        """Adds gold if input is positive."""
        if amount > 0:  # Validation rule
            self._gold += amount  # State update
        return self._gold  # Returns new balance

    def spend(self, amount):
        """Guards against negative balance spent."""
        if 0 < amount <= self._gold:  # Solvency check
            self._gold -= amount  # Deduct gold
            return True  # Transaction successful
        return False  # Transaction denied


class Player:
    """Composite class utilizing composition ("has-a") to manage a Wallet."""

    def __init__(self, name, gold_amount):
        self._name = name  # Primitive instance state
        self._wallet = Wallet(
            gold_amount
        )  # Composition: Player HAS A Wallet object

    def get_name(self):
        """Returns player name."""
        return self._name

    def get_balance(self):
        """Delegates balance inspection to internal Wallet component."""
        return self._wallet.get_gold()  # Component delegation

    def buy_item(self, cost):
        """Delegates spending transaction to internal Wallet component."""
        return self._wallet.spend(cost)  # Component delegation


# --- Execution State Trace ---
player = Player("Aragorn", 100)  # Instantiation -> Player contains Wallet(_gold=100)
print(player.get_balance())  # Output: 100 | Delegated to Wallet.get_gold()

success = player.buy_item(40)  # Calls spend(40) -> 40 <= 100 -> _gold becomes 60
print(success)  # Output: True
print(player.get_balance())  # Output: 60 | Wallet state correctly updated

failed = player.buy_item(100)  # Calls spend(100) -> 100 <= 60 is False -> Denied
print(failed)  # Output: False
print(player.get_balance())  # Output: 60 | Balance unchanged
```

---

### Topic 4: Polymorphism in Collection Iteration

```python
class Enemy:
    """Base class in polymorphic hierarchy."""

    def __init__(self, name):
        self._name = name  # Store enemy identifier

    def attack_power(self):
        """Baseline attack power."""
        return 5  # Generic base power

    def __str__(self):
        """User string representation."""
        return f"Enemy({self._name})"


class Orc(Enemy):
    """Subclass overriding attack power."""

    def attack_power(self):
        return 10  # Orcs hit harder


class Goblin(Enemy):
    """Subclass overriding attack power."""

    def attack_power(self):
        return 3  # Goblins hit lighter


# --- Execution State Trace ---
army = [Orc("Gruk"), Goblin("Sneak"), Enemy("Generic")]  # Heterogeneous list of objects
total_damage = 0  # Initialize accumulator

for unit in army:  # Polymorphic loop over diverse instances
    damage = unit.attack_power()  # Dynamic dispatch resolves correct class method
    total_damage += damage  # Accumulate damage
    # Iteration 1 (Orc "Gruk"): unit.attack_power() -> 10 | total_damage = 10
    # Iteration 2 (Goblin "Sneak"): unit.attack_power() -> 3  | total_damage = 13
    # Iteration 3 (Enemy "Generic"): unit.attack_power() -> 5 | total_damage = 18

print(total_damage)  # Output: 18
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Direct Internal Attribute Mutation (Bypassing Setters)

- **Root Cause**: Bypassing setter validation rules by directly mutating internal variables (`_attribute`), leading to impossible object states.

```python
# INCORRECT: Direct assignment allows invalid state
pet = Pet("Buddy", 50)
pet._health = 99999  # BUG: Bypasses setter validation! State corrupted to impossible value.

# CORRECT: Use setter guardian to enforce range constraints
pet = Pet("Buddy", 50)
pet.set_health(99999)  # FIXED: Setter clamps input to 100, maintaining invariant.
```

---

### Trap 2: Infinite Recursion Loop in Setter Definition

- **Root Cause**: Naming a setter method identical to the variable being assigned inside its body, causing the setter to infinitely call itself until call stack exhaustion.

```python
# INCORRECT: Infinite recursion bug
class BadPet:

    def set_health(self, health):
        self.set_health(
            health
        )  # BUG: Calls set_health recursively! Raises RecursionError.


# CORRECT: Assign to internal instance variable
class GoodPet:

    def set_health(self, health):
        self._health = health  # FIXED: Mutates internal attribute _health cleanly.
```

---

### Trap 3: Unintended Class Attribute Shadowing via Instance Assignment

- **Root Cause**: Attempting to update a class attribute using an instance reference (`self.attr = value`), which silently creates a new instance attribute that shadows the class attribute for that object only.

```python
class Player:
    max_health = 100  # Class attribute shared by all players


p1 = Player()
p2 = Player()

# INCORRECT: Attempting to update global max health on an instance
p1.max_health = 150  # BUG: Creates instance attribute on p1! Player.max_health remains 100 for p2.

# CORRECT: Mutate class attribute via Class Name
Player.max_health = 150  # FIXED: Updates shared state across all current & future instances.
```

---

### Trap 4: Missing `self` Parameter or Missing Parent Constructor Execution

- **Root Cause**: Omitting `self` in instance method definitions, or forgetting to pass `self` / arguments when calling parent methods manually without `super()`.

```python
# INCORRECT: Missing self parameter and incorrect parent call
class Parent:

    def __init__(self, name):
        self._name = name


class Child(Parent):

    def __init__(self, name, age):
        Parent.__init__(
            name
        )  # BUG: Missing 'self' argument! Raises TypeError.
        self._age = age


# CORRECT: Explicit self binding or super() call
class FixedChild(Parent):

    def __init__(self, name, age):
        Parent.__init__(
            self, name
        )  # FIXED: Explicitly passes self instance to parent
        self._age = age
```

---

### Trap 5: Returning Non-String Data Types from `__str__` 

- **Root Cause**: Returning integers, tuples, or non-string objects inside `__str__`, violating Python's strict protocol requirement that `__str__` must return a string (`str`).

```python
# INCORRECT: Returning integer from __str__
class BadDisplay:

    def __str__(self):
        return 42  # BUG: Raises TypeError: __str__ returned non-string (type int)


# CORRECT: Return formatted string
class GoodDisplay:

    def __str__(self):
        return "Value: 42"  # FIXED: Returns valid string instance
```

---

## 5. Python Memory Mechanics, References & Scope

### Variable Binding, Heap Allocation & Namespaces

Python manages variables through **dynamic name binding**. Variable names in local namespaces do not hold raw data directly; they hold memory pointers (references) pointing to objects allocated in **heap memory**.

1. **Instantiation**: Executing `p = Pet("Buddy", 80)` allocates a new `Pet` instance object in heap memory.
2. **`self` Binding**: When `__init__` runs, Python automatically passes the newly allocated heap memory address as the first argument (`self`).
3. **Attribute Dictionaries**: Every instance maintains a private dictionary (`p.__dict__`) storing its instance attributes (`_name`, `_health`).
4. **Method & Attribute Lookup Order**:
   - Step 1: Search the instance's own `__dict__` (`instance.__dict__`).
   - Step 2: If absent, search the class's `__dict__` (`Class.__dict__`).
   - Step 3: If absent, search base parent classes in Method Resolution Order (`MRO`).
   - Step 4: If not found, raise `AttributeError`.

```
STACK FRAME / NAMESPACE                             HEAP MEMORY

+-----------------------+                    +------------------------------------+
| Local Scope           |                    | Pet Instance (id: 0x7f9a8b10)      |
|   pet ----------------+------------------->|   __class__ ------> [ Pet Class ]  |
|                       |                    |   __dict__:                        |
+-----------------------+                    |     '_name': "Shadow"              |
| Pet Class Namespace   |                    |     '_health': 100                 |
|   max_capacity: 100 --+---+                +------------------------------------+
+-----------------------+   |                
                            v                +------------------------------------+
                     [ Integer: 100 ] <------+ Integer Object in Heap             |
                                             +------------------------------------+
```

---

## 6. Practical Integration / Mini Case Study

### Multi-Step System Scenario: 3D Spatial Graphics Engine

This cohesive, multi-step scenario combines all Week 4 concepts: **Encapsulation** (`_x`, `_y`, `_z` state guardianship in `Point3D`), **Inheritance** (`ColoredPixel` inheriting from `Point3D`), **Composition** (`Line3D` composing two `Point3D`s; `Plane3D` composing four `Line3D`s), **Polymorphism**, and **String Representation** (`__str__`).

```python
class Point3D:
    """Base 3D coordinate point demonstrating encapsulation and state mutation."""

    def __init__(self, x, y, z):
        self._x = x  # Encapsulated x-coordinate
        self._y = y  # Encapsulated y-coordinate
        self._z = z  # Encapsulated z-coordinate

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y

    def get_z(self):
        return self._z

    def move(self, dx, dy, dz):
        """Translates point position by delta offsets."""
        self._x += dx  # Mutate internal x
        self._y += dy  # Mutate internal y
        self._z += dz  # Mutate internal z

    def __str__(self):
        return f"Point3D(x={self._x}, y={self._y}, z={self._z})"


class ColoredPixel(Point3D):
    """Subclass inheriting spatial coordinates from Point3D and adding color state."""

    def __init__(self, x, y, z, color):
        Point3D.__init__(self, x, y, z)  # Initialize parent spatial state
        self._color = color  # Additional specialized state

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    def __str__(self):
        """Overridden string representation including inherited coordinates and color."""
        return f"ColoredPixel(x={self._x}, y={self._y}, z={self._z}, color='{self._color}')"


class Line3D:
    """Composite class managing a 3D line segment formed by two Point3D instances."""

    def __init__(self, start_point, end_point):
        self._start = start_point  # Composition: HAS A start Point3D
        self._end = end_point  # Composition: HAS A end Point3D

    def get_start(self):
        return self._start

    def get_end(self):
        return self._end

    def move(self, dx, dy, dz):
        """Delegates spatial translation to both internal Point3D instances."""
        self._start.move(dx, dy, dz)  # Component delegation
        self._end.move(dx, dy, dz)  # Component delegation

    def __str__(self):
        return f"Line3D(start={self._start}, end={self._end})"


class Plane3D:
    """Composite class managing a rectangular 3D plane formed by 4 Line3D instances."""

    def __init__(self, top, bottom, left, right, length, width):
        self._top = top  # Line3D component
        self._bottom = bottom  # Line3D component
        self._left = left  # Line3D component
        self._right = right  # Line3D component
        self._length = length  # Dimension scalar
        self._width = width  # Dimension scalar

    def get_area(self):
        """Calculates area of the rectangular plane."""
        return self._length * self._width

    def move(self, dx, dy, dz):
        """Deep delegation: Cascades movement to all 4 constituent Line3D objects."""
        self._top.move(dx, dy, dz)
        self._bottom.move(dx, dy, dz)
        self._left.move(dx, dy, dz)
        self._right.move(dx, dy, dz)

    def __str__(self):
        return f"Plane3D(area={self.get_area()}, top_line={self._top})"


# =====================================================================
# --- Execution & Step-by-Step State Trace ---
# =====================================================================

# 1. Instantiate Point3D and ColoredPixel instances
p1 = Point3D(0, 0, 0)  # p1 state: _x=0, _y=0, _z=0
p2 = Point3D(10, 0, 0)  # p2 state: _x=10, _y=0, _z=0
pixel = ColoredPixel(
    0, 5, 0, "red"
)  # pixel state: _x=0, _y=5, _z=0, _color='red'

print(p1)  # Terminal Output: Point3D(x=0, y=0, z=0)
print(
    pixel
)  # Terminal Output: ColoredPixel(x=0, y=5, z=0, color='red')

# 2. Instantiate Composite Line3D objects using points
line_top = Line3D(
    Point3D(0, 10, 0), Point3D(10, 10, 0)
)  # Constituent points initialized
line_bottom = Line3D(
    Point3D(0, 0, 0), Point3D(10, 0, 0)
)  # Constituent points initialized
line_left = Line3D(
    Point3D(0, 0, 0), Point3D(0, 10, 0)
)  # Constituent points initialized
line_right = Line3D(
    Point3D(10, 0, 0), Point3D(10, 10, 0)
)  # Constituent points initialized

# 3. Instantiate Composite Plane3D object containing the lines
plane = Plane3D(
    line_top, line_bottom, line_left, line_right, length=10, width=10
)
print(plane.get_area())  # Terminal Output: 100
print(
    plane
)  # Terminal Output: Plane3D(area=100, top_line=Line3D(start=Point3D(x=0, y=10, z=0), end=Point3D(x=10, y=10, z=0)))

# 4. Trigger cascaded delegation via plane.move(5, 5, 5)
plane.move(5, 5, 5)
# Trace: plane.move -> calls move on 4 lines -> each line calls move on 2 points -> points mutate _x, _y, _z
# line_top start point mutated from (0, 10, 0) -> (5, 15, 5)
# line_top end point mutated from (10, 10, 0) -> (15, 15, 5)

print(
    plane
)  # Terminal Output: Plane3D(area=100, top_line=Line3D(start=Point3D(x=5, y=15, z=5), end=Point3D(x=15, y=15, z=5)))
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Encapsulation & Setter Boundary Clamping Trace

#### Code Snippet
```python
class HealthTracker:

    def __init__(self, initial):
        self._health = 0
        self.set_health(initial)

    def set_health(self, val):
        if val < 0:
            self._health = 0
        elif val > 100:
            self._health = 100
        else:
            self._health = val

    def take_damage(self, dmg):
        self.set_health(self._health - dmg)


ht = HealthTracker(120)
ht.take_damage(30)
ht.take_damage(150)
print(ht._health)
```

#### Line-by-Line Annotation & Output Diagnostic
1. `ht = HealthTracker(120)` -> `__init__` sets `self._health = 0`, calls `set_health(120)`.
   - Evaluation: `120 > 100` -> Clamped! `self._health` becomes `100`.
2. `ht.take_damage(30)` -> Calls `set_health(100 - 30)` = `set_health(70)`.
   - Evaluation: `0 <= 70 <= 100` -> Accepted! `self._health` becomes `70`.
3. `ht.take_damage(150)` -> Calls `set_health(70 - 150)` = `set_health(-80)`.
   - Evaluation: `-80 < 0` -> Clamped! `self._health` becomes `0`.
4. `print(ht._health)` -> Reads final state `0`.
   - **Terminal Output**: `0`  

---

### Challenge B: Class Attribute Mutation vs. Instance Shadowing

#### Code Snippet
```python
class Inventory:
    capacity = 3

    def __init__(self):
        self.items = []

    def add(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)


inv1 = Inventory()
inv2 = Inventory()

inv1.capacity = 1  # Instance attribute shadow
Inventory.capacity = 5  # Class attribute update

inv1.add("sword")
inv1.add("shield")

inv2.add("potion")
inv2.add("bow")
inv2.add("arrow")

print(len(inv1.items))
print(len(inv2.items))
```

#### Line-by-Line Annotation & Output Diagnostic
1. `inv1.capacity = 1`: Dynamically creates an **instance attribute** on `inv1` shadowing `Inventory.capacity`. `inv1.capacity` is now `1`.
2. `Inventory.capacity = 5`: Mutates the **class attribute** shared by instances without shadows. `Inventory.capacity` is now `5`.
3. `inv1.add("sword")` -> `len([]) < 1` (uses shadowed `1`) -> `items` becomes `["sword"]`.
4. `inv1.add("shield")` -> `len(["sword"]) < 1` (1 < 1 is False) -> Rejected! `inv1.items` remains `["sword"]`.
5. `inv2.add("potion")`, `add("bow")`, `add("arrow")` -> `inv2` has no instance shadow, so it reads `Inventory.capacity` (`5`). All 3 items added! `inv2.items` becomes `["potion", "bow", "arrow"]`.
6. `print(len(inv1.items))` -> Length is 1.
7. `print(len(inv2.items))` -> Length is 3.
   - **Terminal Output**:  
     `1`  
     `3`  

---

### Challenge C: Inheritance & Polymorphic Method Resolution Trace

#### Code Snippet
```python
class BaseWriter:

    def write(self):
        return "Base Text"


class MarkdownWriter(BaseWriter):

    def write(self):
        return "# Markdown Text"


class PlainWriter(BaseWriter):

    pass


writers = [BaseWriter(), MarkdownWriter(), PlainWriter()]
results = [w.write() for w in writers]
print(" | ".join(results))
```

#### Line-by-Line Annotation & Output Diagnostic
1. `writers[0]` (`BaseWriter`): Executes `BaseWriter.write()` -> Returns `"Base Text"`.
2. `writers[1]` (`MarkdownWriter`): Overrides `write()`, executes `MarkdownWriter.write()` -> Returns `"# Markdown Text"`.
3. `writers[2]` (`PlainWriter`): No override, falls back to parent `BaseWriter.write()` -> Returns `"Base Text"`.
4. `" | ".join(...)` concatenates the list items with a pipe separator.
   - **Terminal Output**: `Base Text | # Markdown Text | Base Text`  

---

### Challenge D: Deep Composition Chain State Propagation

#### Code Snippet
```python
class Counter:

    def __init__(self):
        self.val = 0

    def inc(self):
        self.val += 1


class Node:

    def __init__(self):
        self.counter = Counter()

    def Step(self):
        self.counter.inc()


class Cluster:

    def __init__(self):
        self.nodes = [Node(), Node()]

    def Step_all(self):
        for n in self.nodes:
            n.Step()


c = Cluster()
c.Step_all()
c.nodes[0].Step()
print(c.nodes[0].counter.val)
print(c.nodes[1].counter.val)
```

#### Line-by-Line Annotation & Output Diagnostic
1. `c = Cluster()` initializes `c.nodes` containing two distinct `Node` instances (`nodes[0]` and `nodes[1]`), each with its own `Counter` instance initialized to `val = 0`.
2. `c.Step_all()` loops over both nodes and calls `Step()` on each.
   - `nodes[0].counter.val` becomes `1`.
   - `nodes[1].counter.val` becomes `1`.
3. `c.nodes[0].Step()` calls `Step()` on `nodes[0]` only.
   - `nodes[0].counter.val` increments from `1` to `2`.
4. `print(c.nodes[0].counter.val)` -> Prints `2`.
5. `print(c.nodes[1].counter.val)` -> Prints `1`.
   - **Terminal Output**:  
     `2`  
     `3` is not printed; `1` is printed.

---

*Reference Document saved as `py103_week4_master_reference.md` in Studio ready for export.*
