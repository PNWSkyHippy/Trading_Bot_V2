# PY101 - Week 1 Master Reference: Python Foundations & Console I/O

This document synthesizes all core concepts, mental models, memory mechanics, defensive programming traps, and code execution traces from Week 1 into an authoritative, publication-grade reference guide. It is designed to be completely self-contained, mathematically rigorous, and formatted for direct import into a master notebook.

---

## Table of Contents
1. **Abstract Foundations & Core Theory**
   - 1.1 Primitive Data Types and Formal Language Semantics
   - 1.2 Core Operators, Function Keywords, and Evaluative Rules
   - 1.3 Side-by-Side Type & Operator Comparison Matrix
2. **Real-World Mental Models & Conceptual Mapping**
   - 2.1 The "Labeled Storage Box" Namespace Model
   - 2.2 The "Text Glue vs. Value Separator" Stream Model
   - 2.3 The "Sequential Chronology" Story-to-Math Translation Model
3. **Idiomatic Python Implementation & State Tracing**
   - 3.1 Console I/O and Standard Output Streams
   - 3.2 String Operators: Concatenation and Repetition
   - 3.3 Identifier Declaration, Naming Style, and f-Strings
   - 3.4 Numeric Calculations and Operator Precedence
4. **Defensive Programming & Common Traps**
   - 4.1 Case-Sensitivity Mismatches and `NameError` Traps
   - 4.2 Assignment Operator (`=`) vs. Minus Operator (`-`) Visual Confusion
   - 4.3 Type Boundaries and `TypeError` Exceptions
   - 4.4 Console Order of Operations vs. Outer Function Evaluation Traps
5. **Python Memory Mechanics, References & Scope**
   - 5.1 Dynamic Type Inference vs. Static Type Declarations
   - 5.2 Object Binding, Pointer Reassignment, and Accumulator Logic
   - 5.3 Namespace to Heap Memory Reference Diagram
6. **Practical Integration / Mini Case Study**
   - 6.1 Multi-Step Transaction Calculator Script
   - 6.2 Step-by-Step State and Execution Trace
7. **Step-by-Step Code Tracing Challenges & Diagnostics**
   - 7.1 Challenge A: Precedence and String Repetition
   - 7.2 Challenge B: Sequential Variable Reassignment
   - 7.3 Challenge C: Argument Separation vs. Explicit Concatenation
   - 7.4 Challenge D: Nested Parenthetical Expressions in Console Output

---

## 1. Abstract Foundations & Core Theory

### 1.1 Primitive Data Types and Formal Language Semantics
A **data type** defines a formal category of data that governs the permissible operations, memory storage patterns, and behavioral rules applied to its values. Python enforces strict semantics on its primitive data categories:

*   **String (`str`):** Sequences of textual characters delimited by single quotes (`'...'`) or double quotes (`"..."`). Quotes designate raw text literals; enclosing numeric characters within quotes (e.g., `"5"`) creates a string object rather than a mathematical quantity.
*   **Integer (`int`):** Discrete, non-fractional whole numbers extending infinitely in positive and negative domains (e.g., `-3`, `0`, `7`, `42`).
*   **Floating-Point Number (`float`):** Real numbers represented with a fractional component indicated by a decimal point (e.g., `0.5`, `3.14`, `49.99`). Python distinguishes integers from floats based on the presence of a decimal point; for example, `7` is stored as an `int`, whereas `7.0` is instantiated as a `float`.

```
Primitive Data Taxonomy:
├── String (str)   --> Textual literals delimited by quotes (e.g., 'Hello', "5")
└── Numeric Types
    ├── Integer (int) --> Discrete whole quantities (e.g., 3, 42, -100)
    └── Float (float) --> Fractional decimal quantities (e.g., 3.0, 49.99)
```

---

### 1.2 Core Operators, Function Keywords, and Evaluative Rules
Python relies on built-in keywords and operator symbols to manipulate primitive objects:

*   **`print()` Function:** The standard output mechanism that converts arguments into text streams and writes them to the console. Each `print()` invocation terminates by emitting a newline character (`\n`), forcing subsequent output calls to begin on a new line.
*   **Comma Separator (`,`):** Evaluates multiple arguments within a function call, printing each value sequentially separated by an automatic single space.
*   **Assignment Operator (`=`):** Binds an identifier label on the left-hand side to an object evaluated on the right-hand side.
*   **String Concatenation Operator (`+`):** Combines two string operands into a single continuous string object without inserting spaces.
*   **String Repetition Operator (`*`):** Multiplies a string operand by an integer quantity $N$, duplicating the character sequence $N$ times.
*   **Numeric Arithmetic Operators (`+`, `-`, `*`, `/`):** Execute standard arithmetic operations. Division (`/`) always produces a `float` object, even when the quotient is a whole number.
*   **Parentheses `()`:** Overrides default operator precedence and groups calculations into explicit evaluation blocks.

---

### 1.3 Side-by-Side Type & Operator Comparison Matrix

| Feature / Spec | String (`str`) | Integer (`int`) | Float (`float`) |
| :--- | :--- | :--- | :--- |
| **Definition** | Sequence of text characters. | Discrete whole quantity without decimals. | Fractional real quantity with decimals. |
| **Syntax / Delimiters** | `'text'` or `"text"` | Raw digits (e.g., `42`) | Digits with decimal (e.g., `42.0`) |
| **Permitted Operators** | `+` (Concatenation), `*` (Repetition) | `+`, `-`, `*`, `/` (Arithmetic) | `+`, `-`, `*`, `/` (Arithmetic) |
| **Division Result** | N/A | Always yields `float` (e.g., `10 / 2` $\rightarrow$ `5.0`) | Always yields `float` |
| **Type Invariant / Mutability** | Immutable text sequence | Immutable numeric scalar | Immutable numeric scalar |
| **Common Runtime Error** | `TypeError` on string + number | `TypeError` on number + string | `TypeError` on float + string |

---

## 2. Real-World Mental Models & Conceptual Mapping

### 2.1 The "Labeled Storage Box" Namespace Model
Variables do not store raw binary data in place. Instead, a variable acts as a **labeled storage box** placed in computer memory.
*   **Box Label:** Represents the variable identifier (e.g., `seat_number`).
*   **Box Contents:** Represents the bound object (e.g., `"A12"`).
*   **Retrieval Mechanics:** Invoking a label instructs the interpreter to look up the box, open it, and evaluate the stored value without destroying the contents.

```
+------------------------------------------+
| Variable Identifier: seat_number         |
| +--------------------------------------+ |
| | Object Value: "A12" (Data Type: str) | |
| +--------------------------------------+ |
+------------------------------------------+
```

---

### 2.2 The "Text Glue vs. Value Separator" Stream Model
Console output rendering depends on the mechanism used inside the `print()` function:

1.  **Comma Separator (`,`):** Acts as a **Value Separator**. Passing arguments separated by commas instructs Python to emit each item individually while injecting an automatic space delimiter between them.
2.  **Concatenation Operator (`+`):** Acts as **Text Glue**. The `+` operator evaluates two strings in memory first, welding them together into a single unified string object before passing it to the standard output stream.

```
Commas:        print("Band:", "The PyTones") ---> ["Band:"] + " " + ["The PyTones"] ---> "Band: The PyTones"
Concatenation: print("Band: " + "The PyTones") ---> ["Band: " + "The PyTones"]      ---> "Band: The PyTones"
```

---

### 2.3 The "Sequential Chronology" Story-to-Math Translation Model
Translating real-world word problems into functional Python expressions requires mapping logical chronology directly to operator order of operations:

1.  **Primary Grouping (Base Multiples):** Calculate core item totals first using multiplication inside inner parentheses: `(unit_price * quantity)`.
2.  **Secondary Adjustment (Fees or Discounts):** Apply flat adjustments chronologically to the calculated total: `+ fee` or `- discount`.
3.  **Encapsulation:** Wrap the entire expression inside the outer `print(...)` function so arithmetic evaluation completes prior to console output.

```
Story: "Buy 3 tickets at $35 each, plus a $10 processing fee."
Chronological Mapping:
Step 1: (35 * 2)   --> Base ticket cost ($70)
Step 2: + 10       --> Apply processing fee ($80)
Step 3: print(...) --> Emit computed scalar to terminal
Python Expression: print((35 * 2) + 10)
```

---

## 3. Idiomatic Python Implementation & State Tracing

### 3.1 Console I/O and Standard Output Streams
The `print()` function manages console output streams. Each call automatically appends a newline character unless configured otherwise.

```python
# Initial State: Execution starts
print("Band:", "The PyTones")
# State: Evaluates two arguments separated by comma
# Console Output: Band: The PyTones
# Intermediate: Trailing newline generated (\n)

print("Date:", "2026-06-01")
# State: Evaluates date arguments on line 2
# Console Output: Date: 2026-06-01
# Intermediate: Trailing newline generated (\n)

print("Seat:", "A12")
# State: Evaluates seat arguments on line 3
# Console Output: Seat: A12
# Execution complete
```

---

### 3.2 String Operators: Concatenation and Repetition
String operators follow formal mathematical precedence rules: repetition (`*`) is evaluated prior to concatenation (`+`).

```python
# Topic: String Concatenation (+)
# State: Evaluates "Hello, " + "Ron"
# Intermediate Value: "Hello, Ron"
print("Hello, " + "Ron")
# Console Output: Hello, Ron

# Topic: String Repetition (*)
# State: Evaluates "ha" * 3
# Intermediate Value: "hahaha"
print("ha" * 3)
# Console Output: hahaha

# Topic: Operator Precedence (* before +)
# Step 1: "Ha" * 2 -> "HaHa" (Repetition takes priority)
# Step 2: "Ha" + "HaHa" -> "HaHaHaHa" (Concatenation applies second)
print("Ha" + "Ha" * 2)
# Console Output: HaHaHaHa
```

---

### 3.3 Identifier Declaration, Naming Style, and f-Strings
Variables must adhere to strict identifier rules: letters, digits, and underscores (`_`) are allowed; starting with digits or using hyphens/spaces causes syntax errors. Pythonic style requires lowercase `snake_case`.

```python
# Variable Initialization
# State: favorite_band bound to str "Pink Floyd"
favorite_band = "Pink Floyd"

# State: seat_number bound to str "B17"
seat_number = "B17"

# Direct Variable Print
# State: Evaluates variable favorite_band -> "Pink Floyd"
print(favorite_band)
# Console Output: Pink Floyd

# Formatted String (f-string) Interpolation
# State: Evaluates {favorite_band} placeholder -> "Pink Floyd"
print(f"The band's name is {favorite_band}")
# Console Output: The band's name is Pink Floyd
```

---

### 3.4 Numeric Calculations and Operator Precedence
Python executes arithmetic expressions following standard algebraic operator precedence (PEMDAS).

```python
# Topic: Integer and Float Declarations
# State: num_items bound to int 10
num_items = 10

# State: item_price bound to float 9.99
item_price = 9.99

# Topic: Mixed-type Arithmetic (int * float -> float)
# State: total = 10 * 9.99 -> float 99.9
total = num_items * item_price
print(total)
# Console Output: 99.9

# Topic: Division Yields Float Always
# State: div_result = 10 / 2 -> float 5.0
div_result = 10 / 2
print(div_result)
# Console Output: 5.0

# Topic: Parenthesized Order of Operations
# Step 1: 9 * 3 -> 27 (Inner multiplication)
# Step 2: 27 + 6 -> 33 (Addition)
# Step 3: print(33) -> Console display
print((9 * 3) + 6)
# Console Output: 33
```

---

## 4. Defensive Programming & Common Traps

### 4.1 Case-Sensitivity Mismatches and `NameError` Traps
Python is strictly case-sensitive. Mismatched capitalization in built-in function names or variable identifiers causes the interpreter to raise a `NameError`.

```python
# INCORRECT: Capitalizing built-in print function
# Causes: NameError: name 'Print' is not defined
Print("Hello World")

# INCORRECT: Typo in variable identifier reference
favorite_band = "Led Zeppelin"
# Causes: NameError: name 'faorite_and' is not defined
print(faorite_and)

# CORRECT: Strict case alignment
favorite_band = "Led Zeppelin"
print(favorite_band)
# Output: Led Zeppelin
```

---

### 4.2 Assignment Operator (`=`) vs. Minus Operator (`-`) Visual Confusion
Using the minus operator (`-`) in place of the single assignment operator (`=`) causes invalid arithmetic syntax and leaves variables undefined.

```python
# INCORRECT: Using minus '-' instead of assignment '='
# Interpreter reads: Subtract "Led Zeppelin" from undefined variable 'band'
# Causes: NameError: name 'band' is not defined
band - "Led Zeppelin"

# CORRECT: Explicit single assignment operator '='
# State: Variable band correctly bound to string object
band = "Led Zeppelin"
print(band)
# Output: Led Zeppelin
```

---

### 4.3 Type Boundaries and `TypeError` Exceptions
Using the `+` operator directly between a `str` and a numeric type (`int` or `float`) raises a `TypeError` because Python cannot automatically convert numeric types during concatenation.

```python
total = 99.9

# INCORRECT: Attempting string + float concatenation
# Causes: TypeError: can only concatenate str (not "float") to str
print("Total is " + total)

# CORRECT FIX 1: Using comma separation inside print()
# State: Evaluates text and float as separate arguments, inserting space
print("Total is", total)
# Output: Total is 99.9

# CORRECT FIX 2: Using f-string formatted interpolation
# State: Automatically converts expression inside placeholder to string
print(f"Total is {total}")
# Output: Total is 99.9
```

---

### 4.4 Console Order of Operations vs. Outer Function Evaluation Traps
Placing arithmetic operations or arguments outside the closing parenthesis of `print(...)` causes a syntax or type error because `print()` evaluates first, returns `None`, and leaves trailing operations orphaned.

```python
# INCORRECT: Placing arithmetic operation outside print() call
# Step 1: print(12 * 4) executes and outputs 48, returning None
# Step 2: Interpreter attempts None + 3 -> Crash!
# Causes: TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
print(12 * 4) + 3

# CORRECT: Fully enclosing arithmetic expression inside print()
# Step 1: Evaluates (12 * 4) + 3 -> 48 + 3 -> 51
# Step 2: Passes 51 to print()
print((12 * 4) + 3)
# Output: 51
```

---

## 5. Python Memory Mechanics, References & Scope

### 5.1 Dynamic Type Inference vs. Static Type Declarations
In statically typed languages like C, variables require explicit data type declarations before allocation. In Python, variable declarations use **dynamic type inference**: the interpreter evaluates the right-hand value and binds the variable name to an object created in heap memory.

```c
/* Statically Typed C Syntax */
float item_price = 9.99;
int item_count = 10;
```

```python
# Dynamically Typed Python Syntax
# Python detects float literal -> instantiates float object in heap memory
item_price = 9.99

# Python detects integer literal -> instantiates int object in heap memory
item_count = 10
```

---

### 5.2 Object Binding, Pointer Reassignment, and Accumulator Logic
Variables in Python do not act as static memory slots that overwrite binary data in place. Instead, they function as pointers bound to immutable objects in heap memory.

When executing an accumulator statement like `x = x + 5`:
1.  **Evaluate Right-Hand Side:** Python resolves the value currently bound to `x` (`10`), adds `5`, and computes the scalar result (`15`).
2.  **Instantiate New Object:** A new integer object representing `15` is created in heap memory.
3.  **Rebind Pointer:** The identifier `x` is unbound from `10` and rebound to `15`.

```python
# Initial Assignment
# State: Pointer 'x' bound to int object 10
x = 10

# Accumulator Reassignment
# Step 1: Read x (10) -> Evaluate 10 + 5 -> 15
# Step 2: Instantiate int object 15
# Step 3: Rebind pointer 'x' to object 15
x = x + 5

print(x)
# Console Output: 15
```

---

### 5.3 Namespace to Heap Memory Reference Diagram

```
[ Namespace / Scope ]                          [ Heap Memory ]

  favorite_band  --------------------------->  +-----------------------+
                                                | String: "Pink Floyd"  |
                                                +-----------------------+

  num_items      --------------------------->  +-----------------------+
                                                | Integer: 10           |
                                                +-----------------------+

  item_price     --------------------------->  +-----------------------+
                                                | Float: 9.99           |
                                                +-----------------------+

  x (Original)   -----[Unbound Pointer]----->  +-----------------------+
                                                | Integer: 10           |
                                                +-----------------------+

  x (Reassigned) --------------------------->  +-----------------------+
                                                | Integer: 15           |
                                                +-----------------------+
```

---

## 6. Practical Integration / Mini Case Study

### 6.1 Multi-Step Transaction Calculator Script
The following practical script synthesizes all core concepts from Week 1: variable declarations, data types, string operators, formatted f-strings, arithmetic precedence, and parenthetical story translation.

```python
# =====================================================================
# PY101 Week 1 Case Study: Concert & Concession Transaction Calculator
# =====================================================================

# Phase 1: String Declarations & Header Formatting
event_name = "PyTones World Tour"
venue_section = "Main Hall - Tier 1"

# Print Event Header using String Repetition and Concatenation
print("=" * 35)
print("EVENT: " + event_name)
print("VENUE: " + venue_section)
print("=" * 35)

# Phase 2: Primitive Variable Declarations
ticket_count = 3             # Integer (int)
ticket_price = 45.0          # Float (float)
service_fee = 12.50          # Float (float)
popcorn_count = 2            # Integer (int)
popcorn_price = 6.0          # Float (float)
discount_coupon = 5.0        # Float (float)

# Phase 3: Synchronous Expression Evaluation inside print()
# Ticket Total Calculation: (45.0 * 3) + 12.50 -> 135.0 + 12.50 -> 147.5
ticket_subtotal = (ticket_price * ticket_count) + service_fee
print("Ticket Subtotal (incl. fee):", ticket_subtotal)

# Concession Calculation: (6.0 * 2) - 5.0 -> 12.0 - 5.0 -> 7.0
concession_subtotal = (popcorn_price * popcorn_count) - discount_coupon
print("Concession Subtotal (after coupon):", concession_subtotal)

# Phase 4: Final Accumulator & Output Generation
# Grand Total Accumulation: 147.5 + 7.0 -> 154.5
grand_total = ticket_subtotal + concession_subtotal

print("-" * 35)
print(f"Grand Total Bill: ${grand_total}")
print("-" * 35)
```

---

### 6.2 Step-by-Step State and Execution Trace

1.  **Line 8–9:** Instantiates string objects `"PyTones World Tour"` and `"Main Hall - Tier 1"` and binds them to `event_name` and `venue_section`.
2.  **Line 12–14:** Evaluates `"=" * 35`, generating a line of 35 equals signs. Outputs event headers using string concatenation (`+`).
3.  **Line 17–22:** Instantiates numeric objects (`ticket_count=3`, `ticket_price=45.0`, `service_fee=12.50`, `popcorn_count=2`, `popcorn_price=6.0`, `discount_coupon=5.0`).
4.  **Line 26:** Computes `(45.0 * 3) + 12.50` $\rightarrow$ `135.0 + 12.50 = 147.5` (`float`). Binds result to `ticket_subtotal` and displays: `Ticket Subtotal (incl. fee): 147.5`.
5.  **Line 30:** Computes `(6.0 * 2) - 5.0` $\rightarrow$ `12.0 - 5.0 = 7.0` (`float`). Binds result to `concession_subtotal` and displays: `Concession Subtotal (after coupon): 7.0`.
6.  **Line 34:** Accumulates `147.5 + 7.0` $\rightarrow$ `154.5` (`float`), binding it to `grand_total`.
7.  **Line 36–38:** Emits formatted delimiter and f-string output to standard output: `Grand Total Bill: $154.5`.

#### Terminal Output Stream:
```text
===================================
EVENT: PyTones World Tour
VENUE: Main Hall - Tier 1
===================================
Ticket Subtotal (incl. fee): 147.5
Concession Subtotal (after coupon): 7.0
-----------------------------------
Grand Total Bill: $154.5
-----------------------------------
```

---

## 7. Step-by-Step Code Tracing Challenges & Diagnostics

### 7.1 Challenge A: Precedence and String Repetition

#### Code Block:
```python
print("Boom" + "Boom" * 2)
```

#### Step-by-Step Diagnostic Trace:
1.  **Identify Operands:** Operand 1 is `"Boom"` (`str`), Operand 2 is `"Boom"` (`str`), Operand 3 is `2` (`int`).
2.  **Evaluate Multiplication First:** Due to operator precedence, string repetition (`*`) evaluates before concatenation (`+`).
    *   Sub-expression: `"Boom" * 2`
    *   Intermediate Result: `"BoomBoom"`
3.  **Evaluate Concatenation Second:** Concatenate primary operand with intermediate result.
    *   Sub-expression: `"Boom" + "BoomBoom"`
    *   Intermediate Result: `"BoomBoomBoom"`
4.  **Emit to Output Stream:** Pass final string literal to `print()`.

#### Terminal Output:
```text
BoomBoomBoom
```

---

### 7.2 Challenge B: Sequential Variable Reassignment

#### Code Block:
```python
x = 5
y = 2
x = x + 3
y = y * x
print(x, y)
```

#### Step-by-Step Diagnostic Trace:
1.  **Line 1:** Instantiates integer `5`; binds `x` $\rightarrow$ `5`.
2.  **Line 2:** Instantiates integer `2`; binds `y` $\rightarrow$ `2`.
3.  **Line 3 (Reassignment of `x`):**
    *   Read current `x` (`5`)
    *   Evaluate expression: `5 + 3` $\rightarrow$ `8`
    *   Rebind `x` $\rightarrow$ `8`
4.  **Line 4 (Reassignment of `y`):**
    *   Read current `y` (`2`) and current `x` (`8`)
    *   Evaluate expression: `2 * 8` $\rightarrow$ `16`
    *   Rebind `y` $\rightarrow$ `16`
5.  **Line 5 (Console Output):** Pass `x` (`8`) and `y` (`16`) separated by comma.

#### Terminal Output:
```text
8 16
```

---

### 7.3 Challenge C: Argument Separation vs. Explicit Concatenation

#### Code Block:
```python
val1 = "5"
val2 = 3
print(val1 * val2)
print(val1, val2)
```

#### Step-by-Step Diagnostic Trace:
1.  **Line 1–2:** Instantiates string `"5"` bound to `val1`, and integer `3` bound to `val2`.
2.  **Line 3 (`val1 * val2`):**
    *   Evaluates string repetition: `"5"` (`str`) multiplied by `3` (`int`).
    *   Intermediate Result: `"555"` (`str`).
    *   Console Output: `555`.
3.  **Line 4 (`val1, val2`):**
    *   Evaluates `print()` with comma separator across multi-type arguments.
    *   Inserts space delimiter between `"5"` and `3`.
    *   Console Output: `5 3`.

#### Terminal Output:
```text
555
5 3
```

---

### 7.4 Challenge D: Nested Parenthetical Expressions in Console Output

#### Code Block:
```python
print((10 + 2 * 3) / 4)
```

#### Step-by-Step Diagnostic Trace:
1.  **Inner Parentheses - Precedence Step 1:** Evaluate multiplication before addition inside `(10 + 2 * 3)`.
    *   Sub-expression: `2 * 3` $\rightarrow$ `6`
2.  **Inner Parentheses - Precedence Step 2:** Complete addition inside parentheses.
    *   Sub-expression: `10 + 6` $\rightarrow$ `16`
3.  **Outer Division:** Divide parenthetical result (`16`) by denominator (`4`).
    *   Sub-expression: `16 / 4`
    *   Behavior Rule: Division (`/`) always returns a floating-point number (`float`).
    *   Intermediate Result: `4.0`
4.  **Emit to Output Stream:** Pass scalar float `4.0` to `print()`.

#### Terminal Output:
```text
4.0
```

---

End of Reference Document. Ready to be imported directly into your Notebook.
