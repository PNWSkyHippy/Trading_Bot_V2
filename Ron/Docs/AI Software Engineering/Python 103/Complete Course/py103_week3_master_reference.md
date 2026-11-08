# PY103 - Week 3 Master Reference: Object-Oriented Programming (State, Relationships, Encapsulation & Invariants)

> **Welcome Blurb:** This Master Reference Document synthesizes all core concepts, mental models, memory mechanics, object relationships, and code traces from PY103 Week 3 into an authoritative, publication-grade, self-contained technical guide. It is designed for software engineering students, computer science educators, and Python developers seeking a rigorous, low-level understanding of object-oriented design in Python.

---

## Table of Contents

1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
   - 1.1 Formal Technical Definitions
   - 1.2 Side-by-Side Concept Comparison Matrix
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
   - 2.1 Visual Analogies
   - 2.2 ASCII System Architecture Diagrams
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
   - 3.1 Topic A: Class Definitions & Instance Instantiation
   - 3.2 Topic B: Method Invocation & Independent State Mutation
   - 3.3 Topic C: Object Relationships (1-to-1 & 1-to-Many)
   - 3.4 Topic D: Iterating Collections of Custom Objects & Summary Aggregations
   - 3.5 Topic E: Class Variables vs. Instance Variables
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
   - 4.1 Trap 1: AttributeError (Accessing Uninitialized Attributes)
   - 4.2 Trap 2: Direct State Mutation (Encapsulation Violation)
   - 4.3 Trap 3: Invariant Violation / Boundary Bleed
   - 4.4 Trap 4: Shared Mutable Default Parameters
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
   - 5.1 Object References, Binding, and Heap Memory
   - 5.2 Instance `__dict__` vs Class Namespace Resolution
   - 5.3 ASCII Memory Layout Diagram
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
   - 6.1 Complete Integrated Script: Municipal Shelter & Care System
   - 6.2 Step-by-Step Execution Trace & State Snapshot
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)
   - 7.1 Challenge A: Independent State & Divergent Method Execution
   - 7.2 Challenge B: One-to-Many Relationship Navigation & State Mutation
   - 7.3 Challenge C: Class Namespace Mutation vs Instance Overriding
   - 7.4 Challenge D: Cascading Invariants & Delegated Method Chains

---

## 1. Abstract Foundations & Core Theory

### 1.1 Formal Technical Definitions

- **Class (`class`)**: A user-defined composite data type that acts as a blueprint or template for creating objects. It encapsulates data (attributes) and behaviors (methods) into a single cohesive unit.
- **Instance / Object**: A concrete instantiation of a class allocated in heap memory. Each instance maintains its own distinct identity (`id()`) and unique state dictionary (`__dict__`).
- **Constructor (`__init__`)**: A special dunder (double underscore) initializer method in Python automatically invoked upon instance creation. Its primary function is to bind initial instance attributes to the newly allocated instance reference (`self`).
- **Instance Reference (`self`)**: The explicit first parameter in instance methods representing the specific instance object upon which the method was invoked. It allows Python to dynamically locate and mutate instance-specific attributes in memory.
- **Instance Attribute / Object State**: A variable bound directly to a specific object instance (via `self.attribute_name`). The collective values of an object's instance attributes at a specific execution timestamp define its **object state**.
- **Instance Method**: A function defined within a class body that accepts `self` as its first parameter, granting it full read and write access to the calling instance's attribute state.
- **Relationship Attribute**: An instance attribute that holds a reference to another custom class instance (1-to-1) or a data structure containing multiple instances (1-to-many, such as a Python `list`).
- **Encapsulation & Object Responsibility**: The object-oriented design paradigm dictating that the object owning the data must also own the behavior that mutates that data. External actor objects must send requests (call methods) rather than directly altering internal attributes.
- **Class Variable**: A variable declared directly within the class body (outside methods). It belongs to the class namespace and is shared among all instances of that class unless explicitly overridden in an instance namespace.
- **Simple Invariant**: An immutable system rule governing an object's state that must remain strictly true throughout the object's entire lifecycle (before, during, and after any method invocation).
- **Clamping / Boundary Check**: Defensive programming logic within a method that intercepts out-of-bounds inputs or state changes and normalizes them to upper or lower boundary limits to preserve state invariants.

### 1.2 Side-by-Side Concept Comparison Matrix

| Feature / Spec | Instance Attribute (State) | Class Variable (Shared State) | Relationship Attribute (Reference) |
| :--- | :--- | :--- | :--- |
| **Definition** | Variables bound to a single instance via `self` inside methods. | Variables defined at class scope shared across all instances. | Attributes holding references to other class instances or lists of instances. |
| **Syntax / Delimiters** | `self.attr = value` within `__init__` or methods. | `class_var = value` directly under `class ClassName:`. | `self.target = target_obj` or `self.targets = []`. |
| **Permitted Operators** | Attribute access `.`, assignment `=`, augmented assignment `+=`, `-=`. | Class access `ClassName.var` or instance lookup `inst.var`. | Dot notation chaining `self.target.method()`, `list.append()`. |
| **Type Invariant / Mutability** | Mutable per-instance; bound to `self.__dict__`. | Mutable at class level; rebinds across all instances unless overridden. | References heap addresses; underlying target objects maintain own mutability. |
| **Common Runtime Error** | `AttributeError` if accessed before assignment in `__init__`. | Unexpected instance shadowing if modified via `self.class_var = val`. | `AttributeError` if attribute is set to `None` or wrong object type. |

---

## 2. Real-World Mental Models & Conceptual Mapping

### 2.1 Visual Analogies

1. **The Architectural Blueprint vs. Concrete Houses**
   - **Class**: The architectural blueprint drawn on paper. It defines room layouts, door dimensions, and wiring diagrams, but nobody can live inside a blueprint.
   - **Instance**: An actual physical house constructed on a specific plot of land (heap memory address).
   - **State Isolation**: Painting the living room wall blue in House A (`luna.happiness = 6`) does not alter the wall color in House B (`max_pet.happiness = 5`), even though both houses were built from the exact same blueprint.

2. **The Data Owner vs. External Actor (The "Polite Request" Model)**
   - **Direct Mutation (Bad Design)**: Reaching into a library book's cover with a black marker and writing "BORROWED" yourself (`book.is_checked_out = True`).
   - **Delegated Encapsulation (Good Design)**: Requesting the librarian at the desk to execute the official checkout procedure (`member.borrow_book(book)` -> `book.borrow()`). The book object manages its own status stamp and check-out counters internally.

3. **The Boundary Gatekeeper (Invariant Protection)**
   - **Invariant**: A rule stating that a water tank can never hold less than 0 gallons or more than 100 gallons.
   - **Clamping / Gatekeeper**: A float valve in the tank (`set_health` / `take_damage`). If a pipe attempts to force 150 gallons into a 100-gallon tank, the float valve intercepts the overflow and caps the water level strictly at 100 gallons.

### 2.2 ASCII System Architecture Diagrams

#### Diagram A: One-to-Many Relationship Mapping & Action Delegation

```
[ Owner Instance: Sam ]
  │  name: "Sam"
  │  pets: [ Ref_0x01, Ref_0x02 ]
  │
  ├───► feeds all pets ───► owner.feed_all_pets()
  │                               │
  │     ┌─────────────────────────┴────────────────────────┐
  │     │ Loop Iteration over self.pets                     │
  │     ▼                                                  ▼
[ Pet Instance 1: Misty @ 0x01 ]           [ Pet Instance 2: Rex @ 0x02 ]
  │  name: "Misty"                           │  name: "Rex"
  │  is_hungry: True ──► (feed()) ──► False  │  is_hungry: True ──► (feed()) ──► False
```

#### Diagram B: Direct Encapsulated Request Flow vs Illegal Reaching

```
CORRECT DELEGATED FLOW (Encapsulated):
[ Member Object ] ─────────────── .borrow_book(book) ─────────────► [ Book Object ]
                                                                           │
                                                                 Executes self.borrow()
                                                                           │
                                                                           ▼
                                                                 self.is_checked_out = True

INCORRECT REACOGNING FLOW (Violation):
[ Member Object ] ─────── Reaches inside and directly sets ───────► [ Book.is_checked_out = True ]
                          (Bypasses Book methods & invariants!)
```

---

## 3. Idiomatic Python Implementation & State Tracing

### 3.1 Topic A: Class Definitions & Instance Instantiation

```python
class Pet:
    # Blueprint defining a Pet entity with default initial state

    def __init__(self, name: str):
        # Bind parameter name to instance dictionary
        self.name = name  # State: self.name = "Luna" (for luna instance)
        self.happiness = 5  # State: default happiness initialized to 5


# Instantiating two distinct instances from the same class blueprint
luna = Pet("Luna")  # Memory: Pet instance created at 0x101. luna.name = "Luna", luna.happiness = 5
max_pet = Pet(
    "Max"
)  # Memory: Pet instance created at 0x102. max_pet.name = "Max", max_pet.happiness = 5

# Step-by-Step Terminal Output Verification:
print(
    f"{luna.name} initial happiness:", luna.happiness
)  # Terminal Output: Luna initial happiness: 5
print(
    f"{max_pet.name} initial happiness:", max_pet.happiness
)  # Terminal Output: Max initial happiness: 5
```

### 3.2 Topic B: Method Invocation & Independent State Mutation

```python
class Account:
    # Bank account class demonstrating method-driven independent state changes

    def __init__(self, owner: str, balance: float):
        self.owner = owner  # Bind owner name
        self.balance = balance  # Bind balance integer/float

    def deposit(self, amount: float):
        # Mutate balance attribute of self specifically
        self.balance += (
            amount  # Step: self.balance = current self.balance + amount
        )


# Instantiate two separate accounts
acc1 = Account("Ron", 100)  # State snapshot: acc1.balance = 100
acc2 = Account("Alex", 100)  # State snapshot: acc2.balance = 100

# Execute deposit method ONLY on acc1
acc1.deposit(50)  # Internal trace: inside deposit, self refers to acc1. acc1.balance becomes 150

# Verify isolated instance state:
print(
    "acc1 balance:", acc1.balance
)  # Terminal Output: acc1 balance: 150 (Changed: 100 -> 150)
print(
    "acc2 balance:", acc2.balance
)  # Terminal Output: acc2 balance: 100 (Unchanged: 100)
```

### 3.3 Topic C: Object Relationships (1-to-1 & 1-to-Many)

```python
class Item:
    # Target object owning equipment state

    def __init__(self, name: str):
        self.name = name  # Item name
        self.equipped = False  # State: initial equipped status is False

    def equip(self):
        # Target object mutates its own state upon request
        self.equipped = True  # Step: self.equipped changes from False to True
        print(f"{self.name} is now equipped.")


class Player:
    # Actor object managing inventory and relationship attributes

    def __init__(self, name: str):
        self.name = name  # Player name
        self.weapon = None  # 1-to-1 Relationship attribute (initially unassigned)

    def equip_weapon(self, item: Item):
        # Establish 1-to-1 relationship reference
        self.weapon = item  # State: self.weapon now points to Item instance
        # Delegate action to target object
        self.weapon.equip()  # Step: Invokes Item.equip() using relationship reference


# Execution & State Trace:
sword = Item("Excalibur")  # sword.equipped = False
hero = Player("Arthur")  # hero.weapon = None

print("Before:", sword.equipped)  # Terminal Output: Before: False
hero.equip_weapon(sword)  # Terminal Output: Excalibur is now equipped.
# Internal trace: hero.weapon set to sword; sword.equip() called; sword.equipped set to True
print("After:", sword.equipped)  # Terminal Output: After: True
```

### 3.4 Topic D: Iterating Collections of Custom Objects & Summary Aggregations

```python
class Book:
    # Represents a library book that manages its checkout state

    def __init__(self, title: str):
        self.title = title  # Book title
        self.is_checked_out = False  # Initial state: available

    def borrow(self):
        self.is_checked_out = True  # State mutation: mark checked out


# Create collection of custom objects
library = [
    Book("1984"),
    Book("Brave New World"),
    Book("Fahrenheit 451"),
]  # List containing 3 distinct Book references

# State Mutation Loop: Borrow specific books matching criteria
titles_to_borrow = ["1984", "Fahrenheit 451"]
for book in library:  # Step 1: book = Book("1984"); Step 2: book = Book("Brave New World"); Step 3: book = Book("Fahrenheit 451")
    if book.title in titles_to_borrow:
        book.borrow()  # Invokes borrow() on matching instances

# Summary Aggregation Loop: Calculate total checked-out books
total_checked_out = 0  # Initialize accumulator
for book in library:
    if book.is_checked_out:
        total_checked_out += 1  # Increment accumulator for true states

print("Total Books Borrowed:", total_checked_out)  # Terminal Output: Total Books Borrowed: 2
```

### 3.5 Topic E: Class Variables vs. Instance Variables

```python
class Counter:
    # Demonstrates shared class namespace vs isolated instance namespace

    total_created = 0  # Class variable: shared across all instances

    def __init__(self):
        self.value = 0  # Instance attribute: unique to each instance
        Counter.total_created += 1  # Explicitly mutate class variable in class namespace


c1 = Counter()  # c1.value = 0; Counter.total_created becomes 1
c2 = Counter()  # c2.value = 0; Counter.total_created becomes 2
c3 = Counter()  # c3.value = 0; Counter.total_created becomes 3

c1.value += 1  # c1.value becomes 1; c2.value & c3.value remain 0
c1.value += 1  # c1.value becomes 2

print(f"c1.value = {c1.value}")  # Terminal Output: c1.value = 2
print(f"c2.value = {c2.value}")  # Terminal Output: c2.value = 0
print(f"c3.value = {c3.value}")  # Terminal Output: c3.value = 0
print(
    f"Counter.total_created = {Counter.total_created}"
)  # Terminal Output: Counter.total_created = 3
```

---

## 4. Defensive Programming & Common Traps

### 4.1 Trap 1: AttributeError (Accessing Uninitialized Attributes)

- **Root Cause**: Attempting to read or mutate an instance attribute that was never assigned inside `__init__` or before method execution.

```python
# INCORRECT: Attribute initialized only inside a conditional method
class Character:

    def __init__(self, name: str):
        self.name = name
        # Bug: self.score is NOT initialized here!

    def gain_score(self):
        self.score += 10  # Raises AttributeError: 'Character' object has no attribute 'score'


hero = Character("Hero")
# hero.gain_score() # CRASHES with AttributeError!
```

```python
# CORRECT: Always bind all instance attributes in __init__
class Character:

    def __init__(self, name: str):
        self.name = name
        self.score = 0  # Fix: Guarantee default state upon instantiation

    def gain_score(self):
        self.score += 10  # Safe: self.score initialized to 0 + 10 = 10


hero = Character("Hero")
hero.gain_score()
print(hero.score)  # Terminal Output: 10
```

### 4.2 Trap 2: Direct State Mutation (Encapsulation Violation)

- **Root Cause**: External objects reaching directly into target object attributes to modify state, bypassing method validation and business logic.

```python
# INCORRECT: Member directly sets book's private state variable
class Book:

    def __init__(self, title: str):
        self.title = title
        self.available = True


class Member:

    def borrow_book(self, book: Book):
        book.available = False  # Bug: Direct attribute mutation bypasses Book rules and tracking!
```

```python
# CORRECT: Delegate state modification to the object owning the data
class Book:

    def __init__(self, title: str):
        self.title = title
        self.available = True

    def borrow(self):
        self.available = False  # Object manages its own data attribute


class Member:

    def borrow_book(self, book: Book):
        book.borrow()  # Fix: Member politely requests Book to execute its own method
```

### 4.3 Trap 3: Invariant Violation / Boundary Bleed

- **Root Cause**: Allowing raw input values to directly overwrite object attributes without boundary checks, breaking state rules (e.g., negative health or over-healing).

```python
# INCORRECT: Direct assignment permits impossible domain states
class Player:

    def __init__(self):
        self.health = 100

    def take_damage(self, amount: int):
        self.health -= (
            amount  # Bug: take_damage(150) results in self.health = -50!
        )
```

```python
# CORRECT: Enforce invariant rules using clamping / gatekeeper logic
class Player:

    def __init__(self):
        self.health = 100  # Invariant rule: 0 <= health <= 100

    def set_health(self, new_health: int):
        # Clamping gatekeeper logic enforcing invariant
        if new_health < 0:
            self.health = 0
        elif new_health > 100:
            self.health = 100
        else:
            self.health = new_health

    def take_damage(self, amount: int):
        self.set_health(
            self.health - amount
        )  # Fix: Delegates update to gatekeeper method


p = Player()
p.take_damage(150)
print(p.health)  # Terminal Output: 0 (Safely clamped to lower boundary!)
```

### 4.4 Trap 4: Shared Mutable Default Parameters

- **Root Cause**: Defining a mutable object (like a list `[]`) as a default parameter in `__init__`, causing all instances that omit the argument to share the exact same list reference in memory.

```python
# INCORRECT: Mutable default parameter shared across instances
class Owner:

    def __init__(self, name: str, pets=[]):  # Bug: pets=[] evaluated ONCE at class load!
        self.name = name
        self.pets = pets


o1 = Owner("Alice")
o2 = Owner("Bob")
o1.pets.append("Cat")
print(o2.pets)  # Terminal Output: ['Cat'] (Bob unintentionally got Alice's pet!)
```

```python
# CORRECT: Use None sentinel and initialize fresh list per instance
class Owner:

    def __init__(self, name: str, pets=None):
        self.name = name
        if pets is None:
            self.pets = []  # Fix: Allocates a new distinct list instance per object
        else:
            self.pets = pets


o1 = Owner("Alice")
o2 = Owner("Bob")
o1.pets.append("Cat")
print(o2.pets)  # Terminal Output: [] (Bob's pet list remains clean and isolated!)
```

---

## 5. Python Memory Mechanics, References & Scope

### 5.1 Object References, Binding, and Heap Memory

In Python, variables do **not** store raw data directly inside named storage boxes. Instead, variable names are **identifiers in a namespace dictionary** that point to reference memory addresses allocated on the **heap memory**.

1. **Instantiation & Allocation**: Executing `p1 = Player("Ron", 10)` allocates a new `Player` object in heap memory (e.g., address `0x7f01`).
2. **Reference Binding**: The variable identifier `p1` in the current local namespace is bound to reference `0x7f01`.
3. **Attribute Lookup Resolution (`obj.attr`)**: When Python evaluates `p1.score`, it searches:
   - First: The instance's own attribute dictionary (`p1.__dict__`).
   - Second: The class namespace (`Player.__dict__`).
   - Third: Parent classes in the MRO (Method Resolution Order).
   - If unfound: Raises `AttributeError`.

### 5.2 Instance `__dict__` vs Class Namespace Resolution

- Every class instance possesses an isolated dictionary attribute called `__dict__`.
- Executing `self.health = 100` inserts key `'health': 100` into that specific instance's `__dict__`.
- Modifying `Counter.total_created += 1` updates the class dictionary (`Counter.__dict__`), making the value visible across all instances inspecting the class variable.

### 5.3 ASCII Memory Layout Diagram

```
LOCAL NAMESPACE                    HEAP MEMORY
(Variable Binding)                 (Objects & Collections)

  luna  ───────────────►  [ Pet Instance @ 0x101 ]
                            ├── __dict__: { 'name': 'Luna', 'happiness': 6 }
                            └── __class__: Pointer to Pet Class

  max_pet ─────────────►  [ Pet Instance @ 0x102 ]
                            ├── __dict__: { 'name': 'Max', 'happiness': 5 }
                            └── __class__: Pointer to Pet Class

  sam (Owner) ─────────►  [ Owner Instance @ 0x201 ]
                            ├── __dict__: { 'name': 'Sam', 'pets': 0x301 }
                            └── __class__: Pointer to Owner Class
                                                │
                                                ▼
                                    [ List Collection @ 0x301 ]
                                      ├── Index 0: Reference to 0x101 (Luna)
                                      └── Index 1: Reference to 0x102 (Max)
```

---

## 6. Practical Integration / Mini Case Study

### 6.1 Complete Integrated Script: Municipal Shelter & Care System

```python
# PY103 Week 3 Case Study: Animal Shelter & Care Management System
# Integrates: Classes, Instances, 1-to-Many Relationships, Invariants, Encapsulation, and Aggregation Loops.


class Animal:
    # Target entity maintaining health and hunger invariants

    def __init__(self, name: str, species: str, health: int = 50):
        self.name = name  # Instance attribute
        self.species = species  # Instance attribute
        self.is_hungry = True  # Initial state: hungry
        self.health = 0  # Default bound
        self.set_health(health)  # Pass through invariant gatekeeper

    def set_health(self, new_health: int):
        # Invariant Gatekeeper: Health must remain strictly in [0, 100]
        if new_health < 0:
            self.health = 0
        elif new_health > 100:
            self.health = 100
        else:
            self.health = new_health

    def feed(self):
        # Mutates own hunger state and delegates health boost to gatekeeper
        if self.is_hungry:
            self.is_hungry = False
            self.set_health(self.health + 20)  # Delegate invariant update
            print(f"[{self.name} the {self.species}] fed. Health boosted.")
        else:
            print(f"[{self.name}] is already full.")


class ShelterCaretaker:
    # Actor entity managing 1-to-Many relationship with Animals

    def __init__(self, name: str):
        self.name = name  # Caretaker name
        self.animals = []  # 1-to-Many Relationship attribute (list of Animals)

    def adopt_animal(self, animal: Animal):
        # Establishes relationship reference
        self.animals.append(animal)
        print(f"Caretaker {self.name} adopted {animal.name}.")

    def feed_all_animals(self):
        # Iterates over relationship collection and delegates feeding behavior
        print(f"
--- Caretaker {self.name} feeding round initiated ---")
        for animal in self.animals:
            animal.feed()  # Delegated action call

    def calculate_shelter_health_summary(self) -> dict:
        # Summary Aggregation Loop producing program-level metrics
        total_health = 0
        hungry_count = 0
        for animal in self.animals:
            total_health += animal.health
            if animal.is_hungry:
                hungry_count += 1

        total_animals = len(self.animals)
        avg_health = total_health / total_animals if total_animals > 0 else 0.0
        return {
            "total_animals": total_animals,
            "avg_health": avg_health,
            "hungry_count": hungry_count,
        }


# Driver Execution Demonstration
if __name__ == "__main__":
    # 1. Instantiate Caretaker
    caretaker = ShelterCaretaker("Dr. Sarah")

    # 2. Dynamic creation and enrollment of Animals with varying initial states
    a1 = Animal("Misty", "Cat", health=40)
    a2 = Animal("Rex", "Dog", health=90)
    a3 = Animal("Shadow", "Wolf", health=-20)  # Triggers invariant clamping to 0

    # 3. Adopt animals into caretaker's 1-to-Many collection
    caretaker.adopt_animal(a1)
    caretaker.adopt_animal(a2)
    caretaker.adopt_animal(a3)

    # 4. Check Initial Summary Metrics
    summary_before = caretaker.calculate_shelter_health_summary()
    print("
[Summary Before Feeding]:", summary_before)

    # 5. Execute Caretaker Feeding Round (Delegated State Mutation)
    caretaker.feed_all_animals()

    # 6. Check Final Summary Metrics
    summary_after = caretaker.calculate_shelter_health_summary()
    print("
[Summary After Feeding]:", summary_after)
```

### 6.2 Step-by-Step Execution Trace & State Snapshot

1. **Animal Instantiation & Invariant Clamping Trace**:
   - `a1 = Animal("Misty", "Cat", 40)` -> `a1.health` set to `40`, `a1.is_hungry` set to `True`.
   - `a2 = Animal("Rex", "Dog", 90)` -> `a2.health` set to `90`, `a2.is_hungry` set to `True`.
   - `a3 = Animal("Shadow", "Wolf", -20)` -> `set_health(-20)` intercepts `< 0` and clamps `a3.health = 0`.
2. **Relationship Setup**:
   - `caretaker.adopt_animal(...)` appends `a1`, `a2`, and `a3` references to `caretaker.animals` list.
3. **Summary Loop 1 (Before Feeding)**:
   - `total_health = 40 + 90 + 0 = 130`.
   - `avg_health = 130 / 3 = 43.33`.
   - `hungry_count = 3`.
4. **Feeding Loop (`feed_all_animals`)**:
   - Iteration 1 (`a1`): `a1.is_hungry` becomes `False`. `a1.set_health(40 + 20)` -> `a1.health` becomes `60`.
   - Iteration 2 (`a2`): `a2.is_hungry` becomes `False`. `a2.set_health(90 + 20)` -> `90 + 20 = 110` -> clamped by `set_health(110)` to `100`.
   - Iteration 3 (`a3`): `a3.is_hungry` becomes `False`. `a3.set_health(0 + 20)` -> `a3.health` becomes `20`.
5. **Summary Loop 2 (After Feeding Terminal Output)**:
   - `total_health = 60 + 100 + 20 = 180`.
   - `avg_health = 180 / 3 = 60.0`.
   - `hungry_count = 0`.

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### 7.1 Challenge A: Independent State & Divergent Method Execution

```python
class Pet:

    def __init__(self, name: str):
        self.name = name
        self.happiness = 5

    def pet_owner(self):
        self.happiness += 1


# Trace Execution:
luna = Pet("Luna")  # line 1: luna.happiness = 5
max_p = Pet("Max")  # line 2: max_p.happiness = 5

luna.pet_owner()  # line 3: luna.happiness evaluated: 5 + 1 = 6
luna.pet_owner()  # line 4: luna.happiness evaluated: 6 + 1 = 7
luna.pet_owner()  # line 5: luna.happiness evaluated: 7 + 1 = 8

max_p.pet_owner()  # line 6: max_p.happiness evaluated: 5 + 1 = 6

print(f"luna.happiness = {luna.happiness}")  # Terminal Output: luna.happiness = 8
print(f"max_p.happiness = {max_p.happiness}")  # Terminal Output: max_p.happiness = 6
```

### 7.2 Challenge B: One-to-Many Relationship Navigation & State Mutation

```python
class Item:

    def __init__(self, name: str, power: int):
        self.name = name
        self.power = power
        self.is_equipped = False

    def equip(self):
        self.is_equipped = True


class Hero:

    def __init__(self, name: str):
        self.name = name
        self.inventory = []

    def add_item(self, item: Item):
        self.inventory.append(item)

    def equip_all(self):
        for item in self.inventory:
            item.equip()


# Trace Execution:
sword = Item("Sword", 10)  # sword.is_equipped = False
shield = Item("Shield", 5)  # shield.is_equipped = False

hero = Hero("Arthur")  # hero.inventory = []
hero.add_item(sword)  # hero.inventory = [sword]
hero.add_item(shield)  # hero.inventory = [sword, shield]

hero.equip_all()  # Iteration 1: sword.equip() -> sword.is_equipped = True
# Iteration 2: shield.equip() -> shield.is_equipped = True

print(f"sword equipped: {sword.is_equipped}")  # Terminal Output: sword equipped: True
print(
    f"shield equipped: {shield.is_equipped}"
)  # Terminal Output: shield equipped: True
```

### 7.3 Challenge C: Class Namespace Mutation vs Instance Overriding

```python
class Robot:
    manufactured_count = 0  # Class variable

    def __init__(self, model: str):
        self.model = model  # Instance variable
        Robot.manufactured_count += 1  # Mutates class namespace directly


# Trace Execution:
r1 = Robot("Alpha")  # Robot.manufactured_count becomes 1
r2 = Robot("Beta")  # Robot.manufactured_count becomes 2

r1.manufactured_count = 99  # WARNING: Creates INSTANCE attribute override in r1.__dict__!
# Does NOT change Robot.manufactured_count class namespace!

r3 = Robot("Gamma")  # Robot.manufactured_count becomes 2 + 1 = 3

print(
    f"r1.manufactured_count = {r1.manufactured_count}"
)  # Terminal Output: r1.manufactured_count = 99 (Instance Shadow)
print(
    f"r2.manufactured_count = {r2.manufactured_count}"
)  # Terminal Output: r2.manufactured_count = 3  (Class Variable Lookup)
print(
    f"Robot.manufactured_count = {Robot.manufactured_count}"
)  # Terminal Output: Robot.manufactured_count = 3 (Class Variable Direct)
```

### 7.4 Challenge D: Cascading Invariants & Delegated Method Chains

```python
class Wallet:

    def __init__(self, initial_balance: float = 0.0):
        self.balance = 0.0
        self.deposit(initial_balance)

    def deposit(self, amount: float):
        if amount > 0:
            self.balance += amount

    def withdraw(self, amount: float) -> bool:
        # Invariant Guard: Balance cannot go negative
        if 0 < amount <= self.balance:
            self.balance -= amount
            return True
        return False


# Trace Execution:
w = Wallet(50.0)  # Initial deposit: w.balance = 50.0
w.deposit(20.0)  # Deposit: 50.0 + 20.0 -> w.balance = 70.0

success1 = w.withdraw(40.0)  # 40 <= 70 is True -> w.balance = 30.0; returns True
success2 = w.withdraw(50.0)  # 50 <= 30 is False -> invariant guard triggers; w.balance remains 30.0; returns False

print(f"success1 = {success1}")  # Terminal Output: success1 = True
print(f"success2 = {success2}")  # Terminal Output: success2 = False
print(f"final balance = {w.balance}")  # Terminal Output: final balance = 30.0
```

---
*Reference Document generated and validated for PY103 Week 3 Master Reference.*
