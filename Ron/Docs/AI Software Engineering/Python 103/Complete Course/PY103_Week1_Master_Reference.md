# PY104 - Week 1 Master Reference: Object-Oriented Programming Fundamentals

This master reference document synthesizes all core concepts, mental models, memory mechanics, and code traces from PY104 Week 1 into an authoritative, self-contained reference guide for Object-Oriented Programming (OOP) in Python.

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

- **Programming Paradigm**: A foundational style, architecture, and theoretical approach to structuring and executing software programs. Object-Oriented Programming (OOP) is a paradigm that organizes software around autonomous entities (objects) containing both data and behavior, contrasting with procedural scripting which organizes code around sequential lists of instructions.
- **Module**: A pre-packaged file or collection of related Python code (functions, classes, constants) that acts as an independent namespace or "toolbox" (e.g., `random`, `math`). Modules are imported into scripts using the `import` keyword to enable code reuse and prevent naming collisions.
- **Class**: A user-defined template, category definition, or blueprint that establishes the shared structural attributes (data fields) and behavioral routines (methods) for a category of entities (e.g., `class Pet:`). A class defines a type but does not allocate memory for specific individual entities.
- **Instance / Object**: A concrete runtime entity allocated in heap memory created from a class blueprint (e.g., `luna = Pet()`). An instance encapsulates its own specific state values alongside access to the methods declared by its class.
- **Attribute / State**: The named facts, properties, or variables bound to a specific object instance (e.g., `luna.name = "Luna"`). State represents what an object is like at a specific point during program execution.
- **Method / Behavior**: Callable functions defined within or bound to an object/class that execute actions or state transformations (e.g., `rng.randint(1, 10)` or `coin_flipper.choice(...)`). Behavior represents what an object can do.
- **`type()` Function**: A built-in Python inspection function that returns the exact class/type of any given object or variable reference (e.g., `type(luna)` returns `<class '__main__.Pet'>`).
- **`pass` Keyword**: A Python null statement used as a syntactic placeholder inside empty class definitions or function bodies where code is syntactically required but no action is needed (e.g., `class Pet: pass`).

### Side-by-Side Concept Comparison Matrix

| Feature / Spec | Module | Class | Instance / Object |
| :--- | :--- | :--- | :--- |
| **Definition** | A collection of related Python functions, classes, and code assets stored in a single namespace. | An abstract blueprint or structural specification defining state attributes and methods for a category. | A concrete runtime entity constructed in memory from a class blueprint holding distinct state values. |
| **Syntax / Delimiters** | `import module_name` or `from module import item` | `class ClassName:` using `CapitalCase` naming convention. | `instance_name = ClassName()` using `snake_case` naming convention. |
| **Permitted Operators** | Dot operator for namespace qualification (`module.tool()`). | Instantiation call operator `()`, class attribute access. | Dot operator for instance attribute assignment (`obj.attr = val`) and method invocation (`obj.method()`). |
| **Type Invariant / Mutability** | Singleton module object residing in `sys.modules`; mutable namespace dict. | Class object of built-in type `type`; defines shared structure for all instances. | Mutable state container of type `ClassName`; allocated at a unique heap memory address. |
| **Common Runtime Error** | `ModuleNotFoundError` (invalid name) / `AttributeError` (missing function/class). | `SyntaxError` (missing colon or `pass`) / `TypeError` (incorrect initialization arguments). | `AttributeError` (accessing an uninitialized attribute or non-existent method). |

---

## 2. Real-World Mental Models & Conceptual Mapping

### Analogy 1: The Specialized Toolbox (Modules)
In physical work, a craftsman does not forge a new hammer or tape measure for every project; they reach for a pre-assembled toolbox on the shelf. In Python, built-in libraries like `math` or `random` serve as specialized toolboxes. Writing `import random` pulls the entire randomness toolbox into the script. Calling `random.randint(1, 10)` fetches a specific tool (`randint`) from inside that toolbox to produce a result without requiring the developer to implement mathematical pseudo-random generation algorithms from scratch.

### Analogy 2: Architectural Blueprint vs. Physical Construction (Classes vs. Instances)
An architectural blueprint for a residential home specifies room dimensions, electrical wiring layouts, and plumbing routes. However, one cannot live inside a blueprint. The blueprint represents the **Class** (`Pet` or `House`). Construction workers use that single blueprint to build three actual physical houses on a street (`luna`, `max`, `pepper`). These houses represent **Instances / Objects**. Painting the front door of House 1 blue (`luna.color = "blue"`) changes the state of House 1 only; it leaves House 2 (`max`) untouched.

### Analogy 3: The Digital Dice Machine (Objects, Methods, and Data)
Consider a physical electronic dice-rolling tabletop gadget:
1. **The Object (`rng = random.Random()`)**: The physical plastic dice machine sitting on the table. It possesses physical existence and internal electrical state.
2. **The Method (`rng.randint(1, 6)`)**: Pushing the red button on the machine. Pushing the button is the action or behavior performed by the machine.
3. **The Data (`roll_result = 4`)**: The numeric value displayed on the LED screen after the button is pressed. The integer `4` is the data produced by the method; it is distinct from the machine itself.

### Conceptual ASCII Architecture Diagrams

```
+-----------------------------------------------------------------------+
| MODULE: random (The Toolbox Namespace)                               |
|                                                                       |
|   +---------------------------------------------------------------+   |
|   | CLASS: Random (The Blueprint / Machine Specification)         |   |
|   |   - Internal State: Seed vector, generator status             |   |
|   |   - Behaviors / Methods: randint(), choice(), random()        |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
                                  |
                   Instantiation: rng = random.Random()
                                  v
+-----------------------------------------------------------------------+
| HEAP MEMORY OBJECT: rng (Instance #1)                                 |
|   - Memory Address: 0x7f8a1234                                        |
|   - Type: <class 'random.Random'>                                     |
|   - Method Invocation: rng.randint(1, 6)                              |
|   - Evaluation Result: Data Integer value 4                           |
+-----------------------------------------------------------------------+
```

```
+-----------------------------------------------------------------------+
| OBJECT STATE vs. BEHAVIOR MAPPING (Instance: luna)                    |
+------------------------------------+----------------------------------+
| STATE (Attributes / What it is like)| BEHAVIOR (Methods / What it does)|
+------------------------------------+----------------------------------+
| luna.name = "Luna"                 | luna.bark()                      |
| luna.species = "Dog"               | luna.fetch()                     |
| luna.age = 3                       | luna.sleep()                     |
| luna.is_hungry = True              | luna.eat()                       |
+------------------------------------+----------------------------------+
```

---

## 3. Idiomatic Python Implementation & State Tracing

### Topic A: Module Imports & Built-In Tool Invocations

```python
import math
import random

# Step 1: Assign integer literal to variable 'number'
number = 16  # State: number = 16 (type: int)

# Step 2: Call sqrt function from math module toolbox
root = math.sqrt(number)  # Intermediate: math.sqrt(16) -> 4.0 | State: root = 4.0 (type: float)

# Step 3: Print result to terminal
print("Square root:", root)  # Console Output: Square root: 4.0

# Step 4: Call randint function directly from random module
secret = random.randint(1, 10)  # Intermediate: random.randint(1, 10) -> e.g., 7 | State: secret = 7 (type: int)

# Step 5: Output generated secret number
print("Secret number:", secret)  # Console Output: Secret number: 7
```

### Topic B: Minimal Class Definitions & Type Inspection

```python
# Step 1: Define minimal class blueprint shell using pass keyword
class Pet:
    pass  # Class 'Pet' registered in current module namespace

# Step 2: Instantiate Pet class to create an object instance
luna = Pet()  # Heap Allocation: New Pet object created | Reference: luna points to object at 0x...

# Step 3: Inspect object type using built-in type() function
obj_type = type(luna)  # Intermediate: type(luna) -> <class '__main__.Pet'> | State: obj_type = <class '__main__.Pet'>

# Step 4: Output type information to console
print(obj_type)  # Console Output: <class '__main__.Pet'>
```

### Topic C: Dynamic Attribute Binding & Instance State Isolation

```python
class Pet:
    pass

# Step 1: Instantiate two distinct objects from the same Pet blueprint
luna = Pet()  # Heap Allocation: Pet instance #1 created at 0x01
max_pet = Pet()  # Heap Allocation: Pet instance #2 created at 0x02

# Step 2: Bind state attributes to instance #1 (luna)
luna.name = "Luna"  # State: luna.name = "Luna" (str)
luna.age = 3  # State: luna.age = 3 (int)
luna.species = "Dog"  # State: luna.species = "Dog" (str)

# Step 3: Bind state attributes to instance #2 (max_pet)
max_pet.name = "Max"  # State: max_pet.name = "Max" (str)
max_pet.age = 5  # State: max_pet.age = 5 (int)
max_pet.species = "Cat"  # State: max_pet.species = "Cat" (str)

# Step 4: Verify state isolation across distinct instance objects
print(luna.name, "is a", luna.species, "aged", luna.age)  # Console Output: Luna is a Dog aged 3
print(max_pet.name, "is a", max_pet.species, "aged", max_pet.age)  # Console Output: Max is a Cat aged 5
```

### Topic D: Explicit Object Instantiation & Method Calls (`random.Random`)

```python
import random

# Step 1: Instantiate explicit Random class object (the digital dice machine)
rng = random.Random()  # Heap Allocation: Random object created | Reference: rng points to object at 0x...

# Step 2: Invoke randint method on the rng object instance
die_roll = rng.randint(1, 6)  # Intermediate: rng.randint(1, 6) -> e.g., 4 | State: die_roll = 4 (int)

# Step 3: Invoke choice method on rng instance with a list argument
outcomes = ["heads", "tails"]  # State: outcomes = ["heads", "tails"] (list)
coin_flip = rng.choice(outcomes)  # Intermediate: rng.choice(["heads", "tails"]) -> e.g., "heads" | State: coin_flip = "heads"

# Step 4: Print outputs to verify object behavior results
print("Die roll output:", die_roll)  # Console Output: Die roll output: 4
print("Coin flip output:", coin_flip)  # Console Output: Coin flip output: heads
```

---

## 4. Defensive Programming & Common Traps

### Trap 1: Omitting Parentheses During Instantiation
- **Root Cause**: Writing `luna = Pet` binds the variable `luna` to the **class object itself** rather than invoking the constructor to instantiate a new object in memory.

```python
# INCORRECT: Missing instantiation parentheses
class Pet:
    pass

luna = Pet  # Bug: luna holds a reference to the class Pet, NOT an instance!
print(type(luna))  # Console Output: <class 'type'>
```

```python
# CORRECT: Proper instantiation with call operator ()
class Pet:
    pass

luna = Pet()  # Fixed: Creates a new instance of class Pet
print(type(luna))  # Console Output: <class '__main__.Pet'>
```

### Trap 2: Accessing Uninitialized Instance Attributes
- **Root Cause**: Attempting to read an attribute from an instance before that attribute has been assigned causes Python to raise an `AttributeError`.

```python
# INCORRECT: Accessing unassigned attribute
class Pet:
    pass

luna = Pet()
print(luna.age)  # Error: AttributeError: 'Pet' object has no attribute 'age'
```

```python
# CORRECT: Bind attribute prior to read access
class Pet:
    pass

luna = Pet()
luna.age = 3  # Fixed: Bind attribute 'age' to instance luna
print(luna.age)  # Console Output: 3
```

### Trap 3: Confusing Module Names with Class Names
- **Root Cause**: Calling `Random()` directly without module qualification raises a `NameError`, while attempting to call the module `random()` as a function raises a `TypeError`.

```python
# INCORRECT: Improper module/class invocation
import random

rng = Random()  # Error: NameError: name 'Random' is not defined
# OR
rng = random()  # Error: TypeError: 'module' object is not callable
```

```python
# CORRECT: Qualify class name with module prefix
import random

rng = random.Random()  # Fixed: Accesses class Random from module random
```

### Trap 4: Confusing Method Return Data with the Generating Object
- **Root Cause**: Attempting to invoke object methods on returned integer or string data values rather than on the generator object.

```python
# INCORRECT: Invoking object method on data return value
import random

rng = random.Random()
roll = rng.randint(1, 6)  # roll stores an integer (e.g., 4)
next_roll = roll.randint(1, 6)  # Error: AttributeError: 'int' object has no attribute 'randint'
```

```python
# CORRECT: Invoke methods on the persistent generator object
import random

rng = random.Random()  # Object instance
roll = rng.randint(1, 6)  # Data value (int)
next_roll = rng.randint(1, 6)  # Fixed: Call method on generator object 'rng'
```

### Trap 5: Namespace Pollution via Wildcard Imports
- **Root Cause**: Executing `from module import *` dumps all module identifiers into the global namespace, creating name collision hazards and obscuring code provenance.

```python
# INCORRECT: Wildcard import creates namespace ambiguity
from math import *
from random import *

val = pow(2, 3)  # Bug: Ambiguous whether pow comes from math, built-ins, or random
```

```python
# CORRECT: Explicit module qualification
import math
import random

val = math.pow(2, 3)  # Fixed: Explicit namespace qualification
```

---

## 5. Python Memory Mechanics, References & Scope

### How Python Manages Variables Under the Hood

1. **Dynamic Typing & Memory Allocation**: In Python, variables do not have static types; objects in heap memory do. A variable name in a namespace is merely a named reference (a pointer) to an object stored in heap memory.
2. **Binding vs. Assignment**: Writing `luna = Pet()` allocates memory for a new `Pet` instance on the heap (e.g., at address `0x7f9a88001`) and binds the name `luna` in the local namespace symbol table to that address.
3. **Reference Aliasing**: Executing `alias_pet = luna` does **NOT** duplicate or clone the `Pet` object. Instead, it creates a second variable name in the namespace pointing to the **exact same heap memory address**. Consequently, mutating `alias_pet.age` simultaneously modifies `luna.age`.

### ASCII Memory Allocation & Reference Map

```
+-----------------------------------+           +---------------------------------------+
| NAMESPACE (Symbol Table / Stack)  |           | HEAP MEMORY                           |
+-----------------------------------+           +---------------------------------------+
| Variable Name   | Target Address  |           | Memory Address | Object Content       |
+-----------------+-----------------+           +----------------+----------------------+
| pet1 -----------+---------------->|=========> | 0x7f9a88001    | Pet Object           |
|                 |                 |           |                |   __class__: Pet     |
| pet2 -----------+---------------->|=========> |                |   name: "Luna"       |
| (Alias of pet1) |                 |           |                |   species: "Dog"     |
|                 |                 |           |                |   age: 3             |
|                 |                 |           +----------------+----------------------+
| pet3 -----------+-----------------+=========> | 0x7f9a88002    | Pet Object           |
|                 |                 |           |                |   __class__: Pet     |
|                 |                 |           |                |   name: "Max"        |
|                 |                 |           |                |   species: "Cat"     |
|                 |                 |           |                |   age: 5             |
+-----------------+-----------------+           +----------------+----------------------+
```

---

## 6. Practical Integration / Mini Case Study

### Comprehensive Multi-Step Script: Shelter Animal Activity & Energy System

```python
import math
import random

# Step 1: Define domain classes for shelter entities
class Pet:
    pass

class ShelterReport:
    pass

# Step 2: Instantiate pet instances
dog = Pet()
dog.name = "Luna"
dog.species = "Dog"
dog.energy = 50  # State: initial energy = 50

cat = Pet()
cat.name = "Shadow"
cat.species = "Cat"
cat.energy = 70  # State: initial energy = 70

# Step 3: Instantiate Random object generator
dice = random.Random()

# Step 4: Simulate activity energy changes using method calls
dog_boost = dice.randint(15, 30)  # Intermediate: dog_boost = e.g., 20
dog.energy = dog.energy + dog_boost  # State: dog.energy = 50 + 20 = 70

cat_drain = dice.randint(10, 20)  # Intermediate: cat_drain = e.g., 15
cat.energy = cat.energy - cat_drain  # State: cat.energy = 70 - 15 = 55

# Step 5: Aggregate data into report object using math module
report = ShelterReport()
report.total_pets = 2  # State: total_pets = 2
raw_avg = (dog.energy + cat.energy) / report.total_pets  # Intermediate: (70 + 55) / 2 = 62.5
report.average_energy = math.floor(raw_avg)  # Intermediate: math.floor(62.5) -> 62

# Step 6: Terminal Output Formatting
print("=== SHELTER ACTIVITY REPORT ===")
print("Pet 1 (" + dog.name + " - " + dog.species + "): Energy =", dog.energy)
print("Pet 2 (" + cat.name + " - " + cat.species + "): Energy =", cat.energy)
print("System Average Energy (Floored):", report.average_energy)
```

### Complete Step-by-Step Execution Trace

| Execution Line | Expression / Action | Intermediate Value | Resulting State / Output |
| :--- | :--- | :--- | :--- |
| Line 1-2 | `import math`, `import random` | Standard library modules loaded | Namespaces `math` and `random` available |
| Line 5, 8 | `class Pet: pass`, `class ShelterReport: pass` | Class objects constructed | Classes `Pet` and `ShelterReport` defined |
| Line 12-15 | `dog = Pet()`, attributes assigned | `dog.name="Luna"`, `dog.energy=50` | `dog` object initialized at address `0x01` |
| Line 17-20 | `cat = Pet()`, attributes assigned | `cat.name="Shadow"`, `cat.energy=70` | `cat` object initialized at address `0x02` |
| Line 23 | `dice = random.Random()` | Object created | `dice` points to `Random` instance at `0x03` |
| Line 26-27 | `dog_boost = dice.randint(15, 30)` | `randint` evaluates to `20` | `dog.energy` updated from `50` to `70` |
| Line 29-30 | `cat_drain = dice.randint(10, 20)` | `randint` evaluates to `15` | `cat.energy` updated from `70` to `55` |
| Line 33-35 | `report = ShelterReport()`, `math.floor` | `(70 + 55)/2 = 62.5` -> `62` | `report.average_energy = 62` |
| Line 38-41 | `print(...)` statements | Formatted strings generated | Output printed to terminal console |

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### Challenge A: Reference Aliasing & State Mutation

```python
class Item:
    pass

a = Item()
a.val = 10
b = a
b.val = 25
a.val = a.val + 5

print("a.val:", a.val)
print("b.val:", b.val)
```

#### Step-by-Step Diagnostic Trace:
1. `a = Item()`: Allocates `Item` object on heap at `0x100`. `a` points to `0x100`.
2. `a.val = 10`: Binds attribute `val = 10` inside object at `0x100`.
3. `b = a`: Binds `b` to the same memory address `0x100` (`b` is an alias of `a`).
4. `b.val = 25`: Replaces `val` in object at `0x100` with `25`.
5. `a.val = a.val + 5`: Evaluates `25 + 5 = 30`. Updates `val` in object at `0x100` to `30`.
6. Both `a` and `b` refer to object at `0x100`.

#### Final Terminal Output:
```text
a.val: 30
b.val: 30
```

---

### Challenge B: Primitive Value Binding vs. Instance Attributes

```python
class Counter:
    pass

c1 = Counter()
c1.count = 100
x = c1.count
x = x + 50
c1.count = c1.count + 10

print("x:", x)
print("c1.count:", c1.count)
```

#### Step-by-Step Diagnostic Trace:
1. `c1 = Counter()`: Allocates `Counter` object on heap at `0x200`.
2. `c1.count = 100`: Binds attribute `count = 100` on object at `0x200`.
3. `x = c1.count`: Copies the primitive integer value `100` into independent variable `x`. `x` is NOT an alias to `c1.count`.
4. `x = x + 50`: Evaluates `100 + 50 = 150`. `x` is now `150`.
5. `c1.count = c1.count + 10`: Evaluates `100 + 10 = 110`. `c1.count` is now `110`.

#### Final Terminal Output:
```text
x: 150
c1.count: 110
```

---

### Challenge C: Module Function Chaining & Mathematical Operations

```python
import math
import random

gen = random.Random()
val1 = 9
val2 = 25

res1 = math.sqrt(val1)
res2 = math.sqrt(val2)
total = res1 + res2

print("res1 type:", type(res1).__name__)
print("Total:", total)
```

#### Step-by-Step Diagnostic Trace:
1. `gen = random.Random()`: Instantiates `Random` generator object.
2. `val1 = 9`, `val2 = 25`: Assigns integer variables.
3. `res1 = math.sqrt(9)`: Evaluates square root to float `3.0`.
4. `res2 = math.sqrt(25)`: Evaluates square root to float `5.0`.
5. `total = 3.0 + 5.0`: Floating-point addition yields float `8.0`.
6. `type(res1).__name__`: Evaluates type of float `3.0` -> `"float"`.

#### Final Terminal Output:
```text
res1 type: float
Total: 8.0
```

---

### Challenge D: Multi-Instance State Mutation & Alias Chains

```python
class Robot:
    pass

r1 = Robot()
r2 = Robot()
r1.battery = 100
r2.battery = 100

r1.battery = r1.battery - 30
r3 = r2
r3.battery = r3.battery - 50

print("r1.battery:", r1.battery)
print("r2.battery:", r2.battery)
print("r3.battery:", r3.battery)
```

#### Step-by-Step Diagnostic Trace:
1. `r1 = Robot()`, `r2 = Robot()`: Creates distinct objects at `0x301` (`r1`) and `0x302` (`r2`).
2. `r1.battery = 100`, `r2.battery = 100`: Both objects initialized with battery = `100`.
3. `r1.battery = 100 - 30 = 70`: Mutates `r1` (`0x301`) battery to `70`. `r2` remains `100`.
4. `r3 = r2`: Binds `r3` as an alias to object `r2` (`0x302`).
5. `r3.battery = 100 - 50 = 50`: Mutates object at `0x302` battery to `50`.
6. Reading `r2.battery` and `r3.battery` accesses object at `0x302` (`50`).

#### Final Terminal Output:
```text
r1.battery: 70
r2.battery: 50
r3.battery: 50
```

---
Reference Document saved as an .md file in studio ready to be downloaded and exported.
