# PY101: Complete Course Master Reference & Technical Manual

*Welcome blurb: The complete, unabridged compilation of all 4 weeks of Python Foundations, covering console I/O, primitives, memory mechanics, control structures, and collections.*

---

## Master Course-Wide Index

- [Unified Course Cross-Reference Matrix](#unified-course-cross-reference-matrix)
- [PART I: WEEK 1 - FOUNDATIONS, CONSOLE I/O & MEMORY BINDING](#part-i-week-1---foundations-console-io--memory-binding)
  - [1. Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
    - [1.1 Primitive Data Types and Formal Language Semantics](#11-primitive-data-types-and-formal-language-semantics)
    - [1.2 Core Operators, Function Keywords, and Evaluative Rules](#12-core-operators-function-keywords-and-evaluative-rules)
    - [1.3 Side-by-Side Type & Operator Comparison Matrix](#13-side-by-side-type--operator-comparison-matrix)
  - [2. Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
    - [2.1 The "Labeled Storage Box" Namespace Model](#21-the-labeled-storage-box-namespace-model)
    - [2.2 The "Text Glue vs. Value Separator" Stream Model](#22-the-text-glue-vs-value-separator-stream-model)
    - [2.3 The "Sequential Chronology" Story-to-Math Translation Model](#23-the-sequential-chronology-story-to-math-translation-model)
  - [3. Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
    - [3.1 Console I/O and Standard Output Streams](#31-console-io-and-standard-output-streams)
    - [3.2 String Operators: Concatenation and Repetition](#32-string-operators-concatenation-and-repetition)
    - [3.3 Identifier Declaration, Naming Style, and f-Strings](#33-identifier-declaration-naming-style-and-f-strings)
    - [3.4 Numeric Calculations and Operator Precedence](#34-numeric-calculations-and-operator-precedence)
  - [4. Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
    - [4.1 Case-Sensitivity Mismatches and NameError Traps](#41-case-sensitivity-mismatches-and-nameerror-traps)
    - [4.2 Assignment Operator (=) vs. Minus Operator (-) Visual Confusion](#42-assignment-operator--vs-minus-operator---visual-confusion)
    - [4.3 Type Boundaries and TypeError Exceptions](#43-type-boundaries-and-typeerror-exceptions)
    - [4.4 Console Order of Operations vs. Outer Function Evaluation Traps](#44-console-order-of-operations-vs-outer-function-evaluation-traps)
  - [5. Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
    - [5.1 Dynamic Type Inference vs. Static Type Declarations](#51-dynamic-type-inference-vs-static-type-declarations)
    - [5.2 Object Binding, Pointer Reassignment, and Accumulator Logic](#52-object-binding-pointer-reassignment-and-accumulator-logic)
    - [5.3 Namespace to Heap Memory Reference Diagram](#53-namespace-to-heap-memory-reference-diagram)
  - [6. Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
    - [6.1 Multi-Step Transaction Calculator Script](#61-multi-step-transaction-calculator-script)
    - [6.2 Step-by-Step State and Execution Trace](#62-step-by-step-state-and-execution-trace)
  - [7. Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)
    - [7.1 Challenge A: Precedence and String Repetition](#71-challenge-a-precedence-and-string-repetition)
    - [7.2 Challenge B: Sequential Variable Reassignment](#72-challenge-b-sequential-variable-reassignment)
    - [7.3 Challenge C: Argument Separation vs. Explicit Concatenation](#73-challenge-c-argument-separation-vs-explicit-concatenation)
    - [7.4 Challenge D: Nested Parenthetical Expressions in Console Output](#74-challenge-d-nested-parenthetical-expressions-in-console-output)
- [PART II: WEEK 2 - CORE FOUNDATIONS, ARITHMETIC & DIAGNOSTICS](#part-ii-week-2---core-foundations-arithmetic--diagnostics)
  - [1. Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory-1)
    - [Primary Data Types & Type System](#primary-data-types--type-system)
    - [Division & Modulo Operator Ecosystem](#division--modulo-operator-ecosystem)
    - [Modulo Applications: Parity and Cyclic Position Mapping](#modulo-applications-parity-and-cyclic-position-mapping)
    - [Function Architecture, Parameters, and Execution Control](#function-architecture-parameters-and-execution-control)
    - [Side-by-Side Comparison Matrices](#side-by-side-comparison-matrices)
  - [2. Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping-1)
    - [Analogy 1: The Cookie Factory (Floor Division and Modulo as a Team)](#analogy-1-the-cookie-factory-floor-division-and-modulo-as-a-team)
    - [Analogy 2: The Factory Conveyor vs. The Public Billboard (return vs print)](#analogy-2-the-factory-conveyor-vs-the-public-billboard-return-vs-print)
    - [Analogy 3: The Private Workspace vs. The Corporate Bulletin Board (Scope & Shadowing)](#analogy-3-the-private-workspace-vs-the-corporate-bulletin-board-scope--shadowing)
  - [3. Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing-1)
    - [Module 3.1: Console Input, Dynamic Type Casting, and Inspection](#module-31-console-input-dynamic-type-casting-and-inspection)
    - [Module 3.2: Division Operators, Parity Check, and Cyclic Mapping](#module-32-division-operators-parity-check-and-cyclic-mapping)
    - [Module 3.3: Currency Display vs. Value Rounding](#module-33-currency-display-vs-value-rounding)
    - [Module 3.4: Function Definition, Multi-Parameters, and Guard Clauses](#module-34-function-definition-multi-parameters-and-guard-clauses)
  - [4. Defensive Programming & Common Traps](#4-defensive-programming--common-traps-1)
    - [Trap 1: Implicit String-to-Numeric Concatenation (TypeError)](#trap-1-implicit-string-to-numeric-concatenation-typeerror)
    - [Trap 2: Uncasted User Input Arithmetic (TypeError)](#trap-2-uncasted-user-input-arithmetic-typeerror)
    - [Trap 3: Division by Zero (ZeroDivisionError)](#trap-3-division-by-zero-zerodivisionerror)
    - [Trap 4: Void Function Assignment Trap (TypeError / Value Error)](#trap-4-void-function-assignment-trap-typeerror--value-error)
    - [Trap 5: Unbound Local / Scope Confusion (UnboundLocalError / NameError)](#trap-5-unbound-local--scope-confusion-unboundlocalerror--nameerror)
  - [5. Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope-1)
    - [Dynamic Binding & Variable References](#dynamic-binding--variable-references)
    - [Memory & Namespace Architecture Diagram](#memory--namespace-architecture-diagram)
    - [Namespace Resolution Rules (LEGB Rule)](#namespace-resolution-rules-legb-rule)
    - [Variable Shadowing Mechanics](#variable-shadowing-mechanics)
  - [6. Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study-1)
    - [Comprehensive Program: Event Catering & Budget Allocation System](#comprehensive-program-event-catering--budget-allocation-system)
    - [Execution State Trace & Terminal Output Simulation](#execution-state-trace--terminal-output-simulation)
  - [7. Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics-1)
    - [Challenge A: Mixed Division Modes & Order of Operations](#challenge-a-mixed-division-modes--order-of-operations)
    - [Challenge B: Modulo Cycles, Parity & State Mutations](#challenge-b-modulo-cycles-parity--state-mutations)
    - [Challenge C: Function Return vs. Print & Early Return Guard Clauses](#challenge-c-function-return-vs-print--early-return-guard-clauses)
    - [Challenge D: Scope, Shadowing & Variable Re-binding](#challenge-d-scope-shadowing--variable-re-binding)
- [PART III: WEEK 3 - DECISIONS, CONDITIONAL FLOW & LOOPS](#part-iii-week-3---decisions-conditional-flow--loops)
  - [1. Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory-2)
    - [Formal Definitions & Theoretical Mechanics](#formal-definitions--theoretical-mechanics)
    - [Side-by-Side Comparison Matrix](#side-by-side-comparison-matrix)
  - [2. Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping-2)
    - [Analogy 1: The Railroad Switch Track (Decision Chains & "First True Wins")](#analogy-1-the-railroad-switch-track-decision-chains--first-true-wins)
    - [Analogy 2: The Cashier Scanning Belt (Counters vs. Accumulators)](#analogy-2-the-cashier-scanning-belt-counters-vs-accumulators)
    - [Analogy 3: Physical Tickets vs. Seat Numbers (Value == vs. Identity is)](#analogy-3-physical-tickets-vs-seat-numbers-value--vs-identity-is)
  - [3. Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing-2)
    - [Snippet 1: Decision Logic, Chained Comparisons, and Refactoring](#snippet-1-decision-logic-chained-comparisons-and-refactoring)
    - [Snippet 2: String Membership and Short-Circuit Diagnostics](#snippet-2-string-membership-and-short-circuit-diagnostics)
    - [Snippet 3: Bounded Loops (for), Step Variations, and Accumulation](#snippet-3-bounded-loops-for-step-variations-and-accumulation)
    - [Snippet 4: Unbounded Iteration (while), Loop Control, and Gatekeeper Pattern](#snippet-4-unbounded-iteration-while-loop-control-and-gatekeeper-pattern)
  - [4. Defensive Programming & Common Traps](#4-defensive-programming--common-traps-2)
    - [Trap 1: Accidental Assignment Operator in Conditions](#trap-1-accidental-assignment-operator-in-conditions)
    - [Trap 2: Incorrect Condition Ordering Leading to Unreachable Code](#trap-2-incorrect-condition-ordering-leading-to-unreachable-code)
    - [Trap 3: Missing State Update in while Loop (Infinite Loop)](#trap-3-missing-state-update-in-while-loop-infinite-loop)
    - [Trap 4: Misplacing break vs. continue ("Only Done Printed" Bug)](#trap-4-misplacing-break-vs-continue-only-done-printed-bug)
    - [Trap 5: range() Boundary Off-By-One Error](#trap-5-range-boundary-off-by-one-error)
  - [5. Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope-2)
    - [Dynamic Binding, Heap Memory, and Identity](#dynamic-binding-heap-memory-and-identity)
    - [ASCII Memory Architecture Diagram](#ascii-memory-architecture-diagram)
  - [6. Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study-2)
    - [Comprehensive Multi-Step Script: Automated E-Commerce Order Processor](#comprehensive-multi-step-script-automated-e-commerce-order-processor)
    - [Execution Step Trace Table](#execution-step-trace-table)
  - [7. Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics-2)
    - [Challenge A: Complex Logical Short-Circuit & Side Effects](#challenge-a-complex-logical-short-circuit--side-effects)
    - [Challenge B: Nested Loops and Range Boundaries](#challenge-b-nested-loops-and-range-boundaries)
    - [Challenge C: while Loop with Modulo, continue, and break Interaction](#challenge-c-while-loop-with-modulo-continue-and-break-interaction)
    - [Challenge D: Variable Identity and Memory Rebinding State](#challenge-d-variable-identity-and-memory-rebinding-state)
- [PART IV: WEEK 4 - COLLECTIONS, LISTS & INTEGRATED SYSTEMS](#part-iv-week-4---collections-lists--integrated-systems)
  - [1. Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory-3)
    - [1.1 Fundamental Definitions & Language Primitives](#11-fundamental-definitions--language-primitives)
    - [1.2 Side-by-Side Comparison Matrices](#12-side-by-side-comparison-matrices)
  - [2. Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping-3)
    - [2.1 Visual Analogies for Sequence Mechanics](#21-visual-analogies-for-sequence-mechanics)
    - [2.2 Structural Execution Diagrams](#22-structural-execution-diagrams)
  - [3. Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing-3)
    - [3.1 Console I/O, Keyword Formatting & Type Casting](#31-console-io-keyword-formatting--type-casting)
    - [3.2 String Indexing, Slicing & Method Manipulation](#32-string-indexing-slicing--method-manipulation)
    - [3.3 List Creation, Slice Replacement & In-Place Replacement](#33-list-creation-slice-replacement--in-place-replacement)
    - [3.4 List Mutation Methods (append, insert, extend, pop, remove)](#34-list-mutation-methods-append-insert-extend-pop-remove)
    - [3.5 Iteration Patterns: Index-Based vs. Value-Based Loops](#35-iteration-patterns-index-based-vs-value-based-loops)
    - [3.6 Sorting Mechanics: Custom Keys, Reversal & Stability](#36-sorting-mechanics-custom-keys-reversal--stability)
  - [4. Defensive Programming & Common Traps](#4-defensive-programming--common-traps-3)
    - [Trap 1: Accidental NoneType Assignment from Mutation Methods](#trap-1-accidental-nonetype-assignment-from-mutation-methods)
    - [Trap 2: Direct String/Numeric Concatenation Triggering TypeError](#trap-2-direct-stringnumeric-concatenation-triggering-typeerror)
    - [Trap 3: Off-by-One and Out-of-Bounds Sequence IndexError](#trap-3-off-by-one-and-out-of-bounds-sequence-indexerror)
    - [Trap 4: Non-Numeric String Input to int() / float() Casting](#trap-4-non-numeric-string-input-to-int--float-casting)
    - [Trap 5: Calling Non-Existent Value Removal on Lists (ValueError)](#trap-5-calling-non-existent-value-removal-on-lists-valueerror)
  - [5. Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope-3)
    - [5.1 Object Binding, Identity and Namespaces](#51-object-binding-identity-and-namespaces)
    - [5.2 Memory Heap & Namespace ASCII Diagram](#52-memory-heap--namespace-ascii-diagram)
  - [6. Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study-3)
    - [Comprehensive Program: Autonomous Trade Ledger & Portfolio Analyzer](#comprehensive-program-autonomous-trade-ledger--portfolio-analyzer)
    - [Step-by-Step Execution Trace & Console Output](#step-by-step-execution-trace--console-output)
  - [7. Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics-3)
    - [Challenge A: Complex Slicing & Negative Step Evaluation](#challenge-a-complex-slicing--negative-step-evaluation)
    - [Challenge B: Nested List Mutation, Aliasing, and Slice Replacement](#challenge-b-nested-list-mutation-aliasing-and-slice-replacement)
    - [Challenge C: Stable Sort with Multi-Criteria Tuple Keys & Reverse Flag](#challenge-c-stable-sort-with-multi-criteria-tuple-keys--reverse-flag)
    - [Challenge D: Loop Accumulator, Index Shifting, and Guard Clause Exits](#challenge-d-loop-accumulator-index-shifting-and-guard-clause-exits)
- [PART V: PRACTICE SESSIONS](#part-v-practice-sessions)
  - [1. Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory-4)
    - [Formal Definitions](#formal-definitions)
    - [Core Operations & Keywords](#core-operations--keywords)
    - [Core Foundations Comparison Matrix](#core-foundations-comparison-matrix)
  - [2. Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping-4)
    - [Model 1: The Labeled Storage Box & Address Tag (Variable References)](#model-1-the-labeled-storage-box--address-tag-variable-references)
    - [Model 2: The Trapeze Safety Net Architecture (try / except / else / finally)](#model-2-the-trapeze-safety-net-architecture-try--except--else--finally)
    - [Model 3: The Assembly Line Conveyor Belt & Pipe (stdin -> Filter -> stdout)](#model-3-the-assembly-line-conveyor-belt--pipe-stdin---filter---stdout)
  - [3. Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing-4)
    - [Module A: Console Input/Output & Explicit Type Conversion](#module-a-console-inputoutput--explicit-type-conversion)
    - [Module B: Precision Arithmetic, Floor Division, and Modulo](#module-b-precision-arithmetic-floor-division-and-modulo)
    - [Module C: Sequence Slicing & List Mutation Mechanics](#module-c-sequence-slicing--list-mutation-mechanics)
    - [Module D: Modular Function with Input Validation Trap](#module-d-modular-function-with-input-validation-trap)
  - [4. Defensive Programming & Common Traps](#4-defensive-programming--common-traps-4)
    - [Trap 1: Implied String-Integer Concatenation (TypeError)](#trap-1-implied-string-integer-concatenation-typeerror)
    - [Trap 2: Unsafe Input Conversion (ValueError)](#trap-2-unsafe-input-conversion-valueerror)
    - [Trap 3: The Uninitialized Variable Trap (NameError)](#trap-3-the-uninitialized-variable-trap-nameerror)
    - [Trap 4: Index Out of Bounds (IndexError)](#trap-4-index-out-of-bounds-indexerror)
  - [5. Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope-4)
    - [Memory Architecture & Dynamic Typing](#memory-architecture--dynamic-typing)
    - [LEGB Scope Resolution Rule](#legb-scope-resolution-rule)
  - [6. Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study-4)
    - [Interactive Batch Processing Script](#interactive-batch-processing-script)
    - [Complete Console Output Trace](#complete-console-output-trace)
  - [7. Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics-4)
    - [Diagnostic Challenge A: Complex Arithmetic & Modulo Logic](#diagnostic-challenge-a-complex-arithmetic--modulo-logic)
    - [Diagnostic Challenge B: String Slicing & Replication Mechanics](#diagnostic-challenge-b-string-slicing--replication-mechanics)
    - [Diagnostic Challenge C: List Mutation & In-Place Operations](#diagnostic-challenge-c-list-mutation--in-place-operations)
    - [Diagnostic Challenge D: Exception Flow with Uninitialized State Fallback](#diagnostic-challenge-d-exception-flow-with-uninitialized-state-fallback)

---

## Unified Course Cross-Reference Matrix

| Technical Axis | Week 1: Foundations & Console I/O | Week 2: Arithmetic & Functions | Week 3: Decisions & Loops | Week 4: Collections & Sequences | Part V: Integrated Systems & Practice |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core Primitives & Structures** | `int`, `float`, `str` | `int`, `float`, `str`, function parameters | Booleans (`bool`), `NoneSingleton`, range objects | `str`, `list`, `range`, sequence indexing | Heterogeneous collections, exception blocks (`try/except`) |
| **Memory Mechanics & Binding** | Dynamic type inference, variable pointers to heap objects | Function stack frames, variable shadowing, LEGB resolution | Identity (`is`) vs. Value (`==`), small integer caching | Mutability, aliasing (`ref = list`), shallow copies (`list[:]`) | Reference counts, garbage collection, dynamic object rebinding |
| **Primary Operators & Control** | Concatenation (`+`), Repetition (`*`), `print()`, `,` separator | True `/`, Floor `//`, Modulo `%`, `def`, `return` | Branching (`if/elif/else`), Loops (`for`, `while`), `break/continue` | Slicing `[start:stop:step]`, mutation methods (`append`, `pop`) | Exception handling (`try/except/else/finally`), stream filters |
| **Common Runtime Traps** | `TypeError` (string+number), `NameError` (case sensitivity) | `ZeroDivisionError`, `UnboundLocalError`, returning `None` | Infinite `while` loops, unreachable `elif` blocks, `SyntaxError` (`=`) | `IndexError` (out-of-bounds), `ValueError` (`remove()`), `None` assignment | `NameError` (uninitialized variables in `try`), `ValueError` (unvalidated cast) |
| **Defensive Programming Idioms** | Explicit type casting (`str()`), f-string interpolation | Guard clauses for parameters, non-zero divisor checks | Exhaustive mutually exclusive logic, loop termination guards | Membership testing (`in`), safe slice boundaries, stability checks | Multi-stage exception trapping, fallback defaults, stream safety |
| **Real-World Mental Model** | Labeled Storage Boxes & Address Tags | Cookie Factory & Factory Conveyor Belt | Railroad Switch Tracks & Cashier Scanning Belts | Wooden Rail Fence Posts & Train Cars | Trapeze Safety Nets & Assembly Line Pipelines |

---

## PART I: WEEK 1 - FOUNDATIONS, CONSOLE I/O & MEMORY BINDING

### PY101 - Week 1 Master Reference: Python Foundations & Console I/O
This document synthesizes all core concepts, mental models, memory mechanics, defensive programming traps, and code execution traces from Week 1 into an authoritative, publication-grade reference guide. It is designed to be completely self-contained, mathematically rigorous, and formatted for direct import into a master notebook.

---

#### Table of Contents
1. **Abstract Foundations & Core Theory**
    * 1.1 Primitive Data Types and Formal Language Semantics
    * 1.2 Core Operators, Function Keywords, and Evaluative Rules
    * 1.3 Side-by-Side Type & Operator Comparison Matrix
2. **Real-World Mental Models & Conceptual Mapping**
    * 2.1 The "Labeled Storage Box" Namespace Model
    * 2.2 The "Text Glue vs. Value Separator" Stream Model
    * 2.3 The "Sequential Chronology" Story-to-Math Translation Model
3. **Idiomatic Python Implementation & State Tracing**
    * 3.1 Console I/O and Standard Output Streams
    * 3.2 String Operators: Concatenation and Repetition
    * 3.3 Identifier Declaration, Naming Style, and f-Strings
    * 3.4 Numeric Calculations and Operator Precedence
4. **Defensive Programming & Common Traps**
    * 4.1 Case-Sensitivity Mismatches and NameError Traps
    * 4.2 Assignment Operator (=) vs. Minus Operator (-) Visual Confusion
    * 4.3 Type Boundaries and TypeError Exceptions
    * 4.4 Console Order of Operations vs. Outer Function Evaluation Traps
5. **Python Memory Mechanics, References & Scope**
    * 5.1 Dynamic Type Inference vs. Static Type Declarations
    * 5.2 Object Binding, Pointer Reassignment, and Accumulator Logic
    * 5.3 Namespace to Heap Memory Reference Diagram
6. **Practical Integration / Mini Case Study**
    * 6.1 Multi-Step Transaction Calculator Script
    * 6.2 Step-by-Step State and Execution Trace
7. **Step-by-Step Code Tracing Challenges & Diagnostics**
    * 7.1 Challenge A: Precedence and String Repetition
    * 7.2 Challenge B: Sequential Variable Reassignment
    * 7.3 Challenge C: Argument Separation vs. Explicit Concatenation
    * 7.4 Challenge D: Nested Parenthetical Expressions in Console Output

---

#### 1. Abstract Foundations & Core Theory
##### 1.1 Primitive Data Types and Formal Language Semantics
A **data type** defines a formal category of data that governs the permissible operations, memory storage patterns, and behavioral rules applied to its values. Python enforces strict semantics on its primitive data categories:
* **String (`str`):** Sequences of textual characters delimited by single quotes (`'...'`) or double quotes (`"..."`). Quotes designate raw text literals; enclosing numeric characters within quotes (e.g., `"5"`) creates a string object rather than a mathematical quantity.
* **Integer (`int`):** Discrete, non-fractional whole numbers extending infinitely in positive and negative domains (e.g., `-3`, `0`, `7`, `42`).
* **Floating-Point Number (`float`):** Real numbers represented with a fractional component indicated by a decimal point (e.g., `0.5`, `3.14`, `49.99`). Python distinguishes integers from floats based on the presence of a decimal point; for example, `7` is stored as an `int`, whereas `7.0` is instantiated as a `float`.

```
Primitive Data Taxonomy:
├── String (str)   --> Textual literals delimited by quotes (e.g., 'Hello', "5")
└── Numeric Types
    ├── Integer (int) --> Discrete whole quantities (e.g., 3, 42, -100)
    └── Float (float) --> Fractional decimal quantities (e.g., 3.0, 49.99)
```

---

##### 1.2 Core Operators, Function Keywords, and Evaluative Rules
Python relies on built-in keywords and operator symbols to manipulate primitive objects:
* **`print()` Function:** The standard output mechanism that converts arguments into text streams and writes them to the console. Each `print()` invocation terminates by emitting a newline character (`
`), forcing subsequent output calls to begin on a new line.
* **Comma Separator (`,`):** Evaluates multiple arguments within a function call, printing each value sequentially separated by an automatic single space.
* **Assignment Operator (`=`):** Binds an identifier label on the left-hand side to an object evaluated on the right-hand side.
* **String Concatenation Operator (`+`):** Combines two string operands into a single continuous string object without inserting spaces.
* **String Repetition Operator (`*`):** Multiplies a string operand by an integer quantity $N$, duplicating the character sequence $N$ times.
* **Numeric Arithmetic Operators (`+`, `-`, `*`, `/`):** Execute standard arithmetic operations. Division (`/`) always produces a `float` object, even when the quotient is a whole number.
* **Parentheses `()`:** Overrides default operator precedence and groups calculations into explicit evaluation blocks.

---

##### 1.3 Side-by-Side Type & Operator Comparison Matrix
| Feature / Spec | String (str) | Integer (int) | Float (float) |
| ------ | ------ | ------ | ------ |
| **Definition** | Sequence of text characters. | Discrete whole quantity without decimals. | Fractional real quantity with decimals. |
| **Syntax / Delimiters** | `'text'` or `"text"` | Raw digits (e.g., `42`) | Digits with decimal (e.g., `42.0`) |
| **Permitted Operators** | `+` (Concatenation), `*` (Repetition) | `+`, `-`, `*`, `/` (Arithmetic) | `+`, `-`, `*`, `/` (Arithmetic) |
| **Division Result** | N/A | Always yields float (e.g., `10 / 2` $ightarrow$ `5.0`) | Always yields float |
| **Type Invariant / Mutability** | Immutable text sequence | Immutable numeric scalar | Immutable numeric scalar |
| **Common Runtime Error** | TypeError on string + number | TypeError on number + string | TypeError on float + string |

---

#### 2. Real-World Mental Models & Conceptual Mapping
##### 2.1 The "Labeled Storage Box" Namespace Model
Variables do not store raw binary data in place. Instead, a variable acts as a **labeled storage box** placed in computer memory.
* **Box Label:** Represents the variable identifier (e.g., `seat_number`).
* **Box Contents:** Represents the bound object (e.g., `"A12"`).
* **Retrieval Mechanics:** Invoking a label instructs the interpreter to look up the box, open it, and evaluate the stored value without destroying the contents.

```
+------------------------------------------+
| Variable Identifier: seat_number         |
| +--------------------------------------+ |
| | Object Value: "A12" (Data Type: str) | |
| +--------------------------------------+ |
+------------------------------------------+
```

---

##### 2.2 The "Text Glue vs. Value Separator" Stream Model
Console output rendering depends on the mechanism used inside the `print()` function:
1. **Comma Separator (`,`):** Acts as a **Value Separator**. Passing arguments separated by commas instructs Python to emit each item individually while injecting an automatic space delimiter between them.
2. **Concatenation Operator (`+`):** Acts as **Text Glue**. The `+` operator evaluates two strings in memory first, welding them together into a single unified string object before passing it to the standard output stream.

```
Commas:        print("Band:", "The PyTones") ---> ["Band:"] + " " + ["The PyTones"] ---> "Band: The PyTones"
Concatenation: print("Band: " + "The PyTones") ---> ["Band: " + "The PyTones"]      ---> "Band: The PyTones"
```

---

##### 2.3 The "Sequential Chronology" Story-to-Math Translation Model
Translating real-world word problems into functional Python expressions requires mapping logical chronology directly to operator order of operations:
1. **Primary Grouping (Base Multiples):** Calculate core item totals first using multiplication inside inner parentheses: `(unit_price * quantity)`.
2. **Secondary Adjustment (Fees or Discounts):** Apply flat adjustments chronologically to the calculated total: `+ fee` or `- discount`.
3. **Encapsulation:** Wrap the entire expression inside the outer `print(...)` function so arithmetic evaluation completes prior to console output.

```
Story: "Buy 3 tickets at $35 each, plus a $10 processing fee."
Chronological Mapping:
Step 1: (35 * 2)   --> Base ticket cost ($70)
Step 2: + 10       --> Apply processing fee ($80)
Step 3: print(...) --> Emit computed scalar to terminal
Python Expression: print((35 * 2) + 10)
```

---

#### 3. Idiomatic Python Implementation & State Tracing
##### 3.1 Console I/O and Standard Output Streams
The `print()` function manages console output streams. Each call automatically appends a newline character unless configured otherwise.

```python
# Initial State: Execution starts
print("Band:", "The PyTones")
# State: Evaluates two arguments separated by comma
# Console Output: Band: The PyTones
# Intermediate: Trailing newline generated (
)

print("Date:", "2026-06-01")
# State: Evaluates date arguments on line 2
# Console Output: Date: 2026-06-01
# Intermediate: Trailing newline generated (
)

print("Seat:", "A12")
# State: Evaluates seat arguments on line 3
# Console Output: Seat: A12
# Execution complete
```

---

##### 3.2 String Operators: Concatenation and Repetition
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

##### 3.3 Identifier Declaration, Naming Style, and f-Strings
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

##### 3.4 Numeric Calculations and Operator Precedence
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

#### 4. Defensive Programming & Common Traps
##### 4.1 Case-Sensitivity Mismatches and NameError Traps
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

##### 4.2 Assignment Operator (=) vs. Minus Operator (-) Visual Confusion
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

##### 4.3 Type Boundaries and TypeError Exceptions
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

##### 4.4 Console Order of Operations vs. Outer Function Evaluation Traps
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

#### 5. Python Memory Mechanics, References & Scope
##### 5.1 Dynamic Type Inference vs. Static Type Declarations
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

##### 5.2 Object Binding, Pointer Reassignment, and Accumulator Logic
Variables in Python do not act as static memory slots that overwrite binary data in place. Instead, they function as pointers bound to immutable objects in heap memory.
When executing an accumulator statement like `x = x + 5`:
1. **Evaluate Right-Hand Side:** Python resolves the value currently bound to `x` (`10`), adds `5`, and computes the scalar result (`15`).
2. **Instantiate New Object:** A new integer object representing `15` is created in heap memory.
3. **Rebind Pointer:** The identifier `x` is unbound from `10` and rebound to `15`.

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

##### 5.3 Namespace to Heap Memory Reference Diagram
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

#### 6. Practical Integration / Mini Case Study
##### 6.1 Multi-Step Transaction Calculator Script
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

##### 6.2 Step-by-Step State and Execution Trace
1. **Line 8–9:** Instantiates string objects `"PyTones World Tour"` and `"Main Hall - Tier 1"` and binds them to `event_name` and `venue_section`.
2. **Line 12–14:** Evaluates `"=" * 35`, generating a line of 35 equals signs. Outputs event headers using string concatenation (`+`).
3. **Line 17–22:** Instantiates numeric objects (`ticket_count=3`, `ticket_price=45.0`, `service_fee=12.50`, `popcorn_count=2`, `popcorn_price=6.0`, `discount_coupon=5.0`).
4. **Line 26:** Computes `(45.0 * 3) + 12.50` $ightarrow$ `135.0 + 12.50 = 147.5` (float). Binds result to `ticket_subtotal` and displays: `Ticket Subtotal (incl. fee): 147.5`.
5. **Line 30:** Computes `(6.0 * 2) - 5.0` $ightarrow$ `12.0 - 5.0 = 7.0` (float). Binds result to `concession_subtotal` and displays: `Concession Subtotal (after coupon): 7.0`.
6. **Line 34:** Accumulates `147.5 + 7.0` $ightarrow$ `154.5` (float), binding it to `grand_total`.
7. **Line 36–38:** Emits formatted delimiter and f-string output to standard output: `Grand Total Bill: $154.5`.

```text
Terminal Output Stream:
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

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### 7.1 Challenge A: Precedence and String Repetition
```python
print("Boom" + "Boom" * 2)
```
###### Step-by-Step Diagnostic Trace:
1. **Identify Operands:** Operand 1 is `"Boom"` (str), Operand 2 is `"Boom"` (str), Operand 3 is `2` (int).
2. **Evaluate Multiplication First:** Due to operator precedence, string repetition (`*`) evaluates before concatenation (`+`).
    * Sub-expression: `"Boom" * 2`
    * Intermediate Result: `"BoomBoom"`
3. **Evaluate Concatenation Second:** Concatenate primary operand with intermediate result.
    * Sub-expression: `"Boom" + "BoomBoom"`
    * Intermediate Result: `"BoomBoomBoom"`
4. **Emit to Output Stream:** Pass final string literal to `print()`.

```text
Terminal Output:
BoomBoomBoom
```

---

##### 7.2 Challenge B: Sequential Variable Reassignment
```python
x = 5
y = 2
x = x + 3
y = y * x
print(x, y)
```
###### Step-by-Step Diagnostic Trace:
1. **Line 1:** Instantiates integer 5; binds `x` $ightarrow$ `5`.
2. **Line 2:** Instantiates integer 2; binds `y` $ightarrow$ `2`.
3. **Line 3 (Reassignment of `x`):**
    * Read current `x` (`5`)
    * Evaluate expression: `5 + 3` $ightarrow$ `8`
    * Rebind `x` $ightarrow$ `8`
4. **Line 4 (Reassignment of `y`):**
    * Read current `y` (`2`) and current `x` (`8`)
    * Evaluate expression: `2 * 8` $ightarrow$ `16`
    * Rebind `y` $ightarrow$ `16`
5. **Line 5 (Console Output):** Pass `x` (`8`) and `y` (`16`) separated by comma.

```text
Terminal Output:
8 16
```

---

##### 7.3 Challenge C: Argument Separation vs. Explicit Concatenation
```python
val1 = "5"
val2 = 3
print(val1 * val2)
print(val1, val2)
```
###### Step-by-Step Diagnostic Trace:
1. **Line 1–2:** Instantiates string `"5"` bound to `val1`, and integer `3` bound to `val2`.
2. **Line 3 (`val1 * val2`):**
    * Evaluates string repetition: `"5"` (str) multiplied by `3` (int).
    * Intermediate Result: `"555"` (str).
    * Console Output: `555`.
3. **Line 4 (`val1, val2`):**
    * Evaluates `print()` with comma separator across multi-type arguments.
    * Inserts space delimiter between `"5"` and `3`.
    * Console Output: `5 3`.

```text
Terminal Output:
555
5 3
```

---

##### 7.4 Challenge D: Nested Parenthetical Expressions in Console Output
```python
print((10 + 2 * 3) / 4)
```
###### Step-by-Step Diagnostic Trace:
1. **Inner Parentheses - Precedence Step 1:** Evaluate multiplication before addition inside `(10 + 2 * 3)`.
    * Sub-expression: `2 * 3` $ightarrow$ `6`
2. **Inner Parentheses - Precedence Step 2:** Complete addition inside parentheses.
    * Sub-expression: `10 + 6` $ightarrow$ `16`
3. **Outer Division:** Divide parenthetical result (`16`) by denominator (`4`).
    * Sub-expression: `16 / 4`
    * Behavior Rule: Division (`/`) always returns a floating-point number (`float`).
    * Intermediate Result: `4.0`
4. **Emit to Output Stream:** Pass scalar float `4.0` to `print()`.

```text
Terminal Output:
4.0
```


---

## PART II: WEEK 2 - CORE FOUNDATIONS, ARITHMETIC & DIAGNOSTICS

### CS101 - Week 2 Master Reference: Python Fundamentals: Division Modes, Functions, Scope, and Data Types
*Welcome blurb: This document synthesizes all core concepts, mental models, memory mechanics, state tracing, and defensive programming patterns from Module/Week 2 into an authoritative, publication-grade reference guide.*

---

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

---

#### 1. Abstract Foundations & Core Theory
##### Primary Data Types & Type System
Python is a dynamically typed language where variables act as references to strongly typed objects in memory. The three primary scalar data types introduced in this module are:
* **Integer (`int`):** Represents unbounded positive or negative whole numbers (e.g., `-5`, `0`, `42`). Integer arithmetic produces exact discrete values except when using true division.
* **Floating-Point (`float`):** Represents double-precision 64-bit IEEE 754 decimal numbers (e.g., `3.14159`, `0.0`, `-2.5`). Floating-point arithmetic is subject to standard binary representation limits.
* **String (`str`):** An immutable sequence of Unicode characters enclosed in single (`'...'`) or double (`"..."`) quotes. Used for textual data and user prompts.

---

##### Division & Modulo Operator Ecosystem
Python provides three specialized operators for division-based arithmetic:
1. **True Division (`/`):** Computes the exact mathematical quotient of two numbers. It **always** evaluates to a float, even if the numerator is evenly divisible by the denominator (e.g., `10 / 2` evaluates to `5.0`).
2. **Floor Division (`//`):** Computes the mathematical quotient and applies the floor function ($\lfloor x \rfloor$), truncating the fractional part towards negative infinity. When both operands are integers, it returns an `int` representing the total number of complete groups.
3. **Modulo Operator (`%`):** Computes the remainder after integer floor division, satisfying the fundamental identity:
$$\text{dividend} = (\text{divisor} \times (\text{dividend} // \text{divisor})) + (\text{dividend} \% \text{divisor})$$
The result of `a % b` represents the "leftover" quantity after extracting all complete groups of size `b`.

---

##### Modulo Applications: Parity and Cyclic Position Mapping
* **Parity Determination (`x % 2`):** Evaluating a whole number modulo 2 yields `0` for even numbers and `1` for odd numbers. This is the canonical test for numerical parity.
* **Cyclic Position Mapping (`x % N`):** For any positive integer $N$, evaluating `x % N` maps any non-negative integer $x$ into a bounded range $[0, N - 1]$. As $x$ increases linearly, the expression output cycles continuously: $0, 1, 2, \dots, N-1, 0, 1, \dots$.

##### Function Architecture, Parameters, and Execution Control
* **Function Definition (`def`):** Binds a function name to a block of executable code.
* **Parameters vs. Arguments:** Parameters are variable names declared in the function header that serve as local placeholders. Arguments are the concrete values or object references passed into the function upon invocation.
* **`print()` vs. `return`:** `print()` is an I/O side effect that writes textual representation to standard output (returning `None`). `return` explicitly exits the function, passing an evaluated object back to the caller's evaluation context.
* **Guard Clauses (Early Returns):** Conditional checks placed at the beginning of a function body that evaluate edge cases and immediately return control, avoiding nested logic blocks.

---

##### Side-by-Side Comparison Matrices
###### Matrix 1: Python Division Operators Comparison
| Feature / Spec | True Division (/) | Floor Division (//) | Modulo Operator (%) |
| ------ | ------ | ------ | ------ |
| **Mathematical Definition** | Exact ratio $\frac{a}{b}$ | Floor quotient $\lfloor \frac{a}{b} \rfloor$ | Remainder $a - b \lfloor \frac{a}{b} \rfloor$ |
| **Syntax / Symbol** | `/` | `//` | `%` |
| **Primary Return Type** | Always float | int (if both operands are int) | int (if both operands are int) |
| **Semantic Meaning** | Continuous proportion | Count of full/complete groups | Quantity remaining after grouping |
| **Common Runtime Error** | ZeroDivisionError (if divisor is 0) | ZeroDivisionError (if divisor is 0) | ZeroDivisionError (if divisor is 0) |

###### Matrix 2: Function Output Mechanics (return vs. print)
| Feature / Spec | return Statement | print() Function |
| ------ | ------ | ------ |
| **Primary Purpose** | Pass evaluated data back to caller | Write text to stdout console |
| **Program Flow Effect** | Immediately terminates function execution | Execution continues to next statement |
| **Evaluated Result** | Specified expression (or None if bare) | Always returns None |
| **Data Reusability** | Fully reusable in expressions/variables | Non-reusable (side-effect only) |
| **Typical Context** | Computation, transformations, logic | Debugging, user messaging, logs |

###### Matrix 3: Scalar Data Types & Type Conversion
| Feature / Spec | Integer (int) | Floating-Point (float) | String (str) |
| ------ | ------ | ------ | ------ |
| **Delimiters / Form** | Digits without decimal (e.g. `42`) | Digits with decimal (e.g. `42.0`) | Quotes (e.g. `'42'`, `"42"`) |
| **Mutability** | Immutable | Immutable | Immutable |
| **Casting Function** | `int()` | `float()` | `str()` |
| **Primary Error Type** | ValueError (invalid string conversion) | ValueError (invalid string conversion) | TypeError (implicit concatenation) |

---

#### 2. Real-World Mental Models & Conceptual Mapping
##### Analogy 1: The Cookie Factory (Floor Division and Modulo as a Team)
Imagine a cookie packaging facility. You have a batch of baked cookies (the Dividend) and standard shipping boxes that hold a fixed capacity (the Divisor).
* **Floor Division (`//`):** Represents the packing machine counting **how many full boxes** can be sealed and shipped.
* **Modulo (`%`):** Represents the inspector counting the **loose cookies left on the tray** that cannot fill a complete box.
* **True Division (`/`):** Represents a theoretical blender that purees all cookies and boxes into a fractional float quantity.

```
+-----------------------------------------------------------------------+
| COOKIE FACTORY DIVISION MODEL: 36 Cookies, Box Capacity = 8          |
+-----------------------------------------------------------------------+
|                                                                       |
|  [ Box 1: 8 ]   [ Box 2: 8 ]   [ Box 3: 8 ]   [ Box 4: 8 ]   [Tray]  |
|  ( 8 cookies)   ( 8 cookies)   ( 8 cookies)   ( 8 cookies)  (4 left) |
|                                                                       |
|  36 // 8  ==>  4 FULL BOXES (Floor Quotient)                          |
|  36 % 8   ==>  4 LOOSE COOKIES (Modulo Remainder)                     |
|  36 / 8   ==>  4.5 THEORETICAL BOXES (True Float Division)            |
+-----------------------------------------------------------------------+
```

---

##### Analogy 2: The Factory Conveyor vs. The Public Billboard (return vs print)
To understand function execution:
* **`return` (The Conveyor Belt):** An assembly worker places a finished component onto a conveyor belt. The component is sent directly inside the machine for the next worker (a variable or calling expression) to build upon.
* **`print()` (The Public Billboard):** The worker flashes a sign on the factory wall announcing *"Component Completed!"*. People looking through the window see the text, but no physical part is fed back into the machinery.

```
+-----------------------------------------------------------------------+
| FUNCTION DATA FLOW: return vs print()                                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  FUNCTION CALL: compute_cost(10, 2)                                   |
|       |                                                               |
|       +---> print("Cost is 20") --------> [ Console Display ]         |
|       |                                   (Data lost to program)      |
|       |                                                               |
|       +---> return 20 -------------------> [ Calling Context ]        |
|                                           total_price = 20            |
|                                           (Data stored in memory)     |
+-----------------------------------------------------------------------+
```

---

##### Analogy 3: The Private Workspace vs. The Corporate Bulletin Board (Scope & Shadowing)
Variable namespaces resemble organizational information access:
* **Global Scope (Corporate Bulletin Board):** Information posted in the hallway. Anyone inside any room can read it.
* **Local Scope (Private Conference Room):** Notes written on a whiteboard inside a specific conference room. When the room is unlocked (function call), workers enter, write on the board, and read local notes. When the meeting ends, the room is wiped completely clean.
* **Variable Shadowing:** If a local whiteboard has the label `tax_rate = 0.05` written on it, workers inside the room will use `0.05` instead of the global `tax_rate = 0.10` posted out in the hallway. The hallway board remains entirely untouched.

---

#### 3. Idiomatic Python Implementation & State Tracing
##### Module 3.1: Console Input, Dynamic Type Casting, and Inspection
```python
# Step 1: Prompt user for raw textual input (input always returns str)
raw_quantity = input("Enter number of items: ")  # State: raw_quantity = "5" (type: str)

# Step 2: Inspect raw type before transformation
raw_type = type(raw_quantity)  # State: raw_type = <class 'str'>

# Step 3: Explicitly cast string to integer for mathematical operations
item_count = int(raw_quantity)  # State: item_count = 5 (type: int)

# Step 4: Prompt and cast float input for unit price
unit_price = float(input("Enter unit price: "))  # Input: "12.50" -> State: unit_price = 12.5 (type: float)

# Step 5: Compute raw total cost
subtotal = item_count * unit_price  # State: subtotal = 5 * 12.5 = 62.5 (type: float)

# Step 6: Console Output via f-string formatting
print(f"Subtotal for {item_count} items: ${subtotal:.2f}")
# Output: Subtotal for 5 items: $62.50
```

---

##### Module 3.2: Division Operators, Parity Check, and Cyclic Mapping
```python
# --- Division Ecosystem ---
total_students = 29  # State: total_students = 29
group_size = 4       # State: group_size = 4

# True Division
exact_groups = total_students / group_size  # State: exact_groups = 7.25 (type: float)

# Floor Division (Full Groups)
full_groups = total_students // group_size  # State: full_groups = 7 (type: int)

# Modulo (Leftover Students)
leftover_students = total_students % group_size  # State: leftover_students = 1 (type: int)

# --- Parity Evaluation ---
number_to_check = 11  # State: number_to_check = 11
parity_remainder = number_to_check % 2  # State: parity_remainder = 1
is_even = (parity_remainder == 0)  # State: is_even = False

# --- Cyclic Mapping (7-Day Week Cycle: 0=Sun, 1=Mon, ..., 6=Sat) ---
current_day = 0  # Sunday
days_elapsed = 15  # Advance 15 days
future_day = (current_day + days_elapsed) % 7  # State: 15 % 7 = 1 (Monday)

print(f"Full rows: {full_groups}, Remaining: {leftover_students}")
# Output: Full rows: 7, Remaining: 1
print(f"Is {number_to_check} even? {is_even}")
# Output: Is 11 even? False
print(f"Day in 15 days: {future_day}")
# Output: Day in 15 days: 1
```

---

##### Module 3.3: Currency Display vs. Value Rounding
```python
raw_price = 7.5  # State: raw_price = 7.5

# Approach A: f-string formatting (Modifies visual output only)
formatted_display = f"${raw_price:.2f}"  # State: formatted_display = "$7.50" (type: str)
# raw_price remains float 7.5 in memory

# Approach B: round() function (Modifies numerical value in memory)
calculated_value = 5.55555  # State: calculated_value = 5.55555
rounded_memory_value = round(calculated_value, 2)  # State: rounded_memory_value = 5.56 (type: float)

print(f"Display: {formatted_display}, Rounded Value: {rounded_memory_value}")
# Output: Display: $7.50, Rounded Value: 5.56
```

---

##### Module 3.4: Function Definition, Multi-Parameters, and Guard Clauses
```python
def calculate_box_allocation(total_items, box_capacity):
    # Guard Clause 1: Validate positive integer inputs
    if box_capacity <= 0:
        print("Error: Box capacity must be greater than zero.")
        return None  # Early termination on invalid input
    
    # Guard Clause 2: Check for empty inventory
    if total_items <= 0:
        return 0, 0  # Early return of zero boxes, zero remainder
    
    # Core Logic
    boxes_needed = total_items // box_capacity  # State calculation
    items_leftover = total_items % box_capacity # State calculation
    
    return boxes_needed, items_leftover  # Return tuple of evaluated results

# Execution Call 1: Normal Execution
boxes, leftovers = calculate_box_allocation(50, 9)
# State: boxes = 5, leftovers = 5
print(f"Boxes: {boxes}, Leftovers: {leftovers}")
# Output: Boxes: 5, Leftovers: 5

# Execution Call 2: Triggering Guard Clause
result = calculate_box_allocation(50, 0)
# Output: Error: Box capacity must be greater than zero.
# State: result = None
```

---

#### 4. Defensive Programming & Common Traps
##### Trap 1: Implicit String-to-Numeric Concatenation (TypeError)
Occurs when attempting to combine strings and numeric values using the `+` operator.

```python
# INCORRECT: Implicit concatenation of str and float
item_price = 19.99
# Raises TypeError: can only concatenate str (not "float") to str
# print("Total price is: " + item_price)

# CORRECT 1: Explicit type conversion using str()
print("Total price is: " + str(item_price))
# Console Output: Total price is: 19.99

# CORRECT 2: Idiomatic String Formatting via f-string
print(f"Total price is: ${item_price:.2f}")
# Console Output: Total price is: $19.99
```

---

##### Trap 2: Uncasted User Input Arithmetic (TypeError)
Occurs when attempting mathematical operations directly on the return value of `input()`.

```python
# INCORRECT: input() returns str, cannot add int
# user_age = input("Enter age: ") # User inputs "25"
# next_year = user_age + 1
# Raises TypeError: can only concatenate str (not "int") to str

# CORRECT: Cast input to int before arithmetic
user_age = int(input("Enter age: "))  # User inputs "25" -> State: user_age = 25
next_year = user_age + 1              # State: next_year = 26
print(f"Next year age: {next_year}")
```

---

##### Trap 3: Division by Zero (ZeroDivisionError)
Occurs when `/`, `//`, or `%` is evaluated with a denominator equal to zero.

```python
# INCORRECT: Unchecked division by zero
# divisor = 0
# result = 100 / divisor
# Raises ZeroDivisionError: division by zero

# CORRECT: Defensive check / Guard Clause
divisor = 0
if divisor != 0:
    result = 100 / divisor
else:
    result = 0.0
    print("Warning: Division by zero avoided.")
```

---

##### Trap 4: Void Function Assignment Trap (TypeError / Value Error)
Occurs when assigning the output of a function that uses `print()` instead of `return`.

```python
# INCORRECT: Function prints value but does not return it
def compute_tax_bad(amount):
    print(amount * 0.05) # Returns None implicitly!

tax = compute_tax_bad(100) # Console Output: 5.0 | State: tax = None
# total = 100 + tax        # Raises TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'

# CORRECT: Function returns calculated value
def compute_tax_good(amount):
    return amount * 0.05

tax = compute_tax_good(100) # State: tax = 5.0
total = 100 + tax           # State: total = 105.0
print(f"Total: ${total:.2f}")
```

---

##### Trap 5: Unbound Local / Scope Confusion (UnboundLocalError / NameError)
Occurs when attempting to access a local variable outside its function scope.

```python
# INCORRECT: Accessing local variable in global scope
def process_data():
    local_result = 42
    return local_result

process_data()
# print(local_result)
# Raises NameError: name 'local_result' is not defined

# CORRECT: Capture return value in a global variable
def process_data_fixed():
    local_result = 42
    return local_result

global_result = process_data_fixed()
print(f"Result: {global_result}")
```

---

#### 5. Python Memory Mechanics, References & Scope
##### Dynamic Binding & Variable References
In Python, variables do **not** hold direct values or reserve memory locations of fixed types. Instead, variables are **named references (pointers)** stored in a namespace, pointing to strongly typed objects allocated in heap memory.
When you execute:
```python
x = 25      # 'x' references an int object with value 25
x = "25"    # 'x' is re-bound to point to a str object with value "25"
```
The variable name `x` is dynamically rebound from an integer object to a string object. The original `int` object `25` is unreferenced and becomes eligible for garbage collection.

---

##### Memory & Namespace Architecture Diagram
```
+-----------------------------------------------------------------------+
| NAMESPACES (Stack / Frame)           HEAP MEMORY (Objects)            |
+-----------------------------------------------------------------------+
|                                                                       |
|  GLOBAL NAMESPACE                                                     |
|  +-----------------------+           +-----------------------------+  |
|  | base_price -----------|---------->| float object: 100.0         |  |
|  | tax_rate -------------|----+      +-----------------------------+  |
|  +-----------------------+    |                                       |
|                               |      +-----------------------------+  |
|                               +----->| float object: 0.10          |  |
|                                      +-----------------------------+  |
|  FUNCTION LOCAL FRAME (during call)                 ^                 |
|  +-----------------------+                          |                 |
|  | rate (shadows global) |--------------------------+                 |
|  | item_count -----------|---------->+-----------------------------+  |
|  | subtotal -------------|---------->| int object: 5               |  |
|  +-----------------------+           +-----------------------------+  |
|                                                                       |
+-----------------------------------------------------------------------+
```

---

##### Namespace Resolution Rules (LEGB Rule)
When Python encounters a variable name, it searches namespaces in a strict hierarchy:
1. **L (Local):** Names defined inside the currently executing function.
2. **E (Enclosing):** Names in enclosing/nested functions (if any).
3. **G (Global):** Names declared at the top level of the module file.
4. **B (Built-in):** Pre-loaded Python names (e.g., `len`, `int`, `print`).

##### Variable Shadowing Mechanics
When a local variable inside a function shares the exact same identifier as a global variable, the local name **shadows** the global name inside that function frame. All reads and writes to that variable name inside the function resolve strictly to the local object. The global variable remains completely unaffected in global space.

---

#### 6. Practical Integration / Mini Case Study
##### Comprehensive Program: Event Catering & Budget Allocation System
This script integrates all core concepts from Week 2: console input parsing, type casting, floor division, modulo cyclic mapping, financial formatting, functions with guard clauses, and variable scope isolation.

```python
# Global Configurations
TAX_RATE = 0.07  # Global constant for sales tax (7%)

def calculate_event_logistics(attendees, table_capacity):
    # Guard Clause: Invalid table capacity
    if table_capacity <= 0:
        print("[LOGISTICS ERROR] Table capacity must be greater than zero.")
        return None, None
    
    # Guard Clause: Zero attendees
    if attendees <= 0:
        return 0, 0
    
    # Compute full tables and overflow attendees using teamwork of // and %
    full_tables = attendees // table_capacity
    overflow_seats = attendees % table_capacity
    
    return full_tables, overflow_seats


def calculate_catering_budget(num_meals, meal_price):
    # Guard Clause: Invalid meal count or price
    if num_meals < 0 or meal_price < 0.0:
        return 0.0
    
    # Local computations
    subtotal = num_meals * meal_price
    tax_amount = subtotal * TAX_RATE  # Accesses global TAX_RATE
    total_cost = subtotal + tax_amount
    
    return total_cost


def determine_setup_day(days_from_today):
    # 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    today_index = 2  # Assume today is Tuesday (Index 2)
    target_day_index = (today_index + days_from_today) % 7
    return target_day_index


def main():
    print("=== EVENT CATERING & LOGISTICS PLANNING SYSTEM ===")
    
    # 1. User Input and Dynamic Casting
    raw_attendees = input("Enter total expected attendees: ")
    attendee_count = int(raw_attendees)
    
    table_size = int(input("Enter seats per table: "))
    meal_cost = float(input("Enter price per catering meal: "))
    days_until_event = int(input("Enter days until event setup: "))
    
    # 2. Execute Logistics Computation
    tables, leftovers = calculate_event_logistics(attendee_count, table_size)
    
    # 3. Execute Financial Computation
    total_budget = calculate_catering_budget(attendee_count, meal_cost)
    
    # 4. Execute Cyclic Mapping Computation
    setup_day_code = determine_setup_day(days_until_event)
    
    # 5. Formatted Execution Report Output
    print("
--------------------------------------------------")
    print("             EVENT EXECUTION SUMMARY              ")
    print("--------------------------------------------------")
    print(f"Total Attendees      : {attendee_count}")
    print(f"Full Tables Required : {tables} tables")
    print(f"Overflow Attendees   : {leftovers} person(s)")
    print(f"Setup Day Code (0-6) : {setup_day_code} (0=Sun, 1=Mon, ..., 6=Sat)")
    print(f"Total Budget (w/ Tax): ${total_budget:.2f}")
    print("--------------------------------------------------")

# Execute Main Program Workflow
if __name__ == "__main__":
    main()
```

---

##### Execution State Trace & Terminal Output Simulation
###### Input Data Provided:
* `raw_attendees` = `"38"` -> `attendee_count` = 38
* `table_size` = `"8"`
* `meal_cost` = `"15.50"`
* `days_until_event` = `"10"`

###### Step-by-Step Execution Trace:
1. `calculate_event_logistics(38, 8)`:
    * `38 // 8` evaluates to 4 (Full Tables).
    * `38 % 8` evaluates to 6 (Overflow Attendees).
    * Returns tuple `(4, 6)`.
2. `calculate_catering_budget(38, 15.50)`:
    * `subtotal` = `38 * 15.50` = `589.0`.
    * `tax_amount` = `589.0 * 0.07` = `41.23`.
    * `total_cost` = `589.0 + 41.23` = `630.23`.
    * Returns float `630.23`.
3. `determine_setup_day(10)`:
    * Today = 2 (Tuesday).
    * `(2 + 10) % 7` = `12 % 7` = 5 (Friday).
    * Returns int 5.

```text
Simulated Terminal Output:
=== EVENT CATERING & LOGISTICS PLANNING SYSTEM ===
Enter total expected attendees: 38
Enter seats per table: 8
Enter price per catering meal: 15.50
Enter days until event setup: 10

--------------------------------------------------
             EVENT EXECUTION SUMMARY              
--------------------------------------------------
Total Attendees      : 38
Full Tables Required : 4 tables
Overflow Attendees   : 6 person(s)
Setup Day Code (0-6) : 5 (0=Sun, 1=Mon, ..., 6=Sat)
Total Budget (w/ Tax): $630.23
--------------------------------------------------
```

---

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Mixed Division Modes & Order of Operations
```python
a = 17
b = 4
c = 2

res1 = a / b + a // b
res2 = a % b * c + a // (b + c)
```
###### Line-by-Line Execution Trace:
1. `a = 17`, `b = 4`, `c = 2`
2. `res1 = 17 / 4 + 17 // 4`:
    * `17 / 4` evaluates to float `4.25`.
    * `17 // 4` evaluates to int `4`.
    * `4.25 + 4` evaluates to float `8.25`.
    * State: `res1 = 8.25`
3. `res2 = 17 % 4 * 2 + 17 // (4 + 2)`:
    * `17 % 4` evaluates to int `1`.
    * `1 * 2` evaluates to int `2`.
    * `4 + 2` evaluates to int `6`.
    * `17 // 6` evaluates to int `2`.
    * `2 + 2` evaluates to int `4`.
    * State: `res2 = 4`

```text
Terminal Output:
res1 = 8.25
res2 = 4
```

---

##### Challenge B: Modulo Cycles, Parity & State Mutations
```python
counter = 14
step = 5

parity_check = counter % 2
cycle_pos1 = counter % step

counter = counter + 3
cycle_pos2 = counter % step
```
###### Line-by-Line Execution Trace:
1. `counter = 14`, `step = 5`
2. `parity_check = 14 % 2` -> 14 is even, so `parity_check = 0`.
3. `cycle_pos1 = 14 % 5` -> 14 = (5 * 2) + 4, so `cycle_pos1 = 4`.
4. `counter = 14 + 3` -> `counter` mutated to 17.
5. `cycle_pos2 = 17 % 5` -> 17 = (5 * 3) + 2, so `cycle_pos2 = 2`.

| Variable Name | Intermediate Value | Final Type |
| ------ | ------ | ------ |
| counter | 17 | int |
| step | 5 | int |
| parity_check | 0 | int |
| cycle_pos1 | 4 | int |
| cycle_pos2 | 2 | int |

```text
Terminal Output:
parity_check = 0
cycle_pos1 = 4
cycle_pos2 = 2
```

---

##### Challenge C: Function Return vs. Print & Early Return Guard Clauses
```python
def process_val(x):
    if x < 0:
        print("Negative detected")
        return 0
    if x % 2 == 0:
        return x // 2
    print("Odd positive processed")
    return x * 3

val1 = process_val(-5)
val2 = process_val(8)
val3 = process_val(7)
```
###### Line-by-Line Execution Trace:
1. `val1 = process_val(-5)`:
    * Condition `x < 0` (`-5 < 0`) is True.
    * Executes `print("Negative detected")`.
    * Executes `return 0`.
    * State: `val1 = 0`.
2. `val2 = process_val(8)`:
    * Condition `x < 0` (`8 < 0`) is False.
    * Condition `x % 2 == 0` (`8 % 2 == 0`) is True.
    * Executes `return 8 // 2` -> `return 4`.
    * `print("Odd positive processed")` is skipped!
    * State: `val2 = 4`.
3. `val3 = process_val(7)`:
    * Condition `x < 0` (`7 < 0`) is False.
    * Condition `x % 2 == 0` (`7 % 2 == 0`) is False.
    * Executes `print("Odd positive processed")`.
    * Executes `return 7 * 3` -> `return 21`.
    * State: `val3 = 21`.

```text
Terminal Console Output During Execution:
Negative detected
Odd positive processed

Final Variable Values:
val1 = 0
val2 = 4
val3 = 21
```

---

##### Challenge D: Scope, Shadowing & Variable Re-binding
```python
rate = 10  # Global variable

def calculate(val):
    rate = 2  # Local shadowing variable
    result = val * rate
    return result

output1 = calculate(5)
output2 = rate * 5
```
###### Line-by-Line Execution Trace:
1. Global scope initializes `rate = 10`.
2. Call `calculate(5)`:
    * Local frame created. Parameter `val = 5`.
    * Local variable `rate = 2` is assigned (shadows global `rate = 10`).
    * `result = 5 * 2 = 10`.
    * Returns 10. Local frame destroyed.
    * State: `output1 = 10`.
3. Evaluate `output2 = rate * 5`:
    * In global scope, `rate` resolves to global 10.
    * `10 * 5 = 50`.
    * State: `output2 = 50`.

```text
Terminal Output:
output1 = 10
output2 = 50
```


---

## PART III: WEEK 3 - DECISIONS, CONDITIONAL FLOW & LOOPS

### CS101 - Week 3 Master Reference: Decisions and Loops in Python
*This document synthesizes all core concepts, mental models, memory mechanics, and code traces from Week 3 into an authoritative, publication-grade reference guide. It covers conditional logic, logical operators, short-circuit evaluation, value equality vs. object identity, decision tables, iteration structures (`for` and `while` loops), loop control (`break` and `continue`), and data aggregation patterns (counters and accumulators).*

---

#### Table of Contents
1. [Abstract Foundations & Core Theory](#1-abstract-foundations--core-theory)
2. [Real-World Mental Models & Conceptual Mapping](#2-real-world-mental-models--conceptual-mapping)
3. [Idiomatic Python Implementation & State Tracing](#3-idiomatic-python-implementation--state-tracing)
4. [Defensive Programming & Common Traps](#4-defensive-programming--common-traps)
5. [Python Memory Mechanics, References & Scope](#5-python-memory-mechanics-references--scope)
6. [Practical Integration / Mini Case Study](#6-practical-integration--mini-case-study)
7. [Step-by-Step Code Tracing Challenges & Diagnostics](#7-step-by-step-code-tracing-challenges--diagnostics)

---

#### 1. Abstract Foundations & Core Theory
##### Formal Definitions & Theoretical Mechanics
###### 1. Conditional Branching (`if`, `elif`, `else`)
* **`if` Statement:** The primary entry point for conditional execution. Evaluates a boolean expression; if `True`, executes the indented code block directly beneath it.
* **`elif` Statement:** Abbreviation for "else if". Evaluates a subsequent condition only if all preceding `if` and `elif` statements in the chain evaluated to `False`.
* **`else` Statement:** The fallback branch. Executes if and only if every preceding condition in the `if`/`elif` chain evaluated to `False`.
* **Indentation Block Structure:** Python uses whitespace (standardized as 4 spaces per nesting level) rather than curly braces (`{}`) or keywords (`begin`/`end`) to denote block scope. Every conditional header line must terminate with a colon (`:`).

---

###### 2. Operators & Boolean Logic
* **Comparison Operators:** Evaluate expressions to boolean literals (`True` or `False`).
    * `==` (Equality): Evaluates whether two operands hold equivalent values.
    * `!=` (Inequality): Evaluates whether two operands hold distinct values.
    * `<`, `>`, `<=`, `>=` (Relational): Compare ordinal or numeric values.
    * **Chained Comparisons:** Python supports compound bounds such as `a <= x < b`, which evaluates as `(a <= x) and (x < b)` without re-evaluating `x`.
* **Logical Operators & Truth Evaluation:**
    * `and` (Conjunction): Returns `True` if and only if both left and right operands evaluate to truthy values.
    * `or` (Disjunction): Returns `True` if at least one operand evaluates to a truthy value.
    * `not` (Boolean Negation): Inverts the boolean truth value of its operand.
* **Short-Circuit Evaluation:** Python evaluates compound logical expressions strictly from left to right and halts evaluation as soon as the final result is guaranteed:
    * In `A and B`: If `A` is `False`, `B` is never evaluated because the conjunction is guaranteed `False`.
    * In `A or B`: If `A` is `True`, `B` is never evaluated because the disjunction is guaranteed `True`.
* **Membership Operators (`in`, `not in`):**
    * `"sub" in "string"`: Traverses a sequence (e.g., string) to check for contiguous substring existence, returning `True` or `False`. Case-sensitive.

---

###### 3. Equality vs. Identity (`==` vs. `is`)
* **Value Equality (`==`):** Inspects whether two object references hold equivalent internal state/data.
* **Object Identity (`is`):** Inspects whether two memory references point to the exact same memory address (heap reference).
* **The `None` Singleton:** `None` represents the intentional absence of a value. The idiomatic Python check for `None` is `x is None` or `x is not None`.

###### 4. Decision Tables: Exclusivity and Completeness
* **Mutual Exclusivity:** A set of conditions is mutually exclusive if no input value can satisfy more than one condition simultaneously (no range overlaps).
* **Completeness:** A set of conditions is complete if every possible input value within the domain satisfies at least one condition (no logic gaps).
* **First True Branch Wins:** In an `if`/`elif`/`else` chain, execution stops at the first condition that evaluates to `True`. General conditions placed before specific conditions create **unreachable code**.

---

###### 5. Iteration Structures (`for` & `while`)
* **Bounded Iteration (`for` + `range`):** Executes a loop body for a predetermined sequence of values generated by `range()`.
    * `range(stop)`: Generates integers `0` through `stop - 1`.
    * `range(start, stop)`: Generates integers `start` through `stop - 1`.
    * `range(start, stop, step)`: Generates integers from `start` up to (excluding) `stop`, incrementing by `step`. A negative step counts backward.
* **Unbounded Iteration (`while`):** Repeats execution as long as a state condition evaluates to `True`. Requires the **Three-Part Pattern**:
    1. **Initialize:** Set control variable(s) prior to loop entry.
    2. **Test:** Evaluate condition in the `while` header.
    3. **Update:** Modify control variable(s) inside the loop body to guarantee termination.
* **Loop Flow Control (`break` & `continue`):**
    * `break`: Terminates loop execution immediately, transferring control to the first statement following the loop block.
    * `continue`: Aborts the remainder of the current iteration body, transferring control back to the loop header check (or next sequence element).

---

##### Side-by-Side Comparison Matrix
| Feature / Spec | Conditional Control (if / elif / else) | Bounded Iteration (for + range) | Unbounded Iteration (while) | Identity & Null Check (is / None) |
| ------ | ------ | ------ | ------ | ------ |
| **Primary Definition** | Branching structure that executes code based on boolean evaluation. | Iterative structure that runs a fixed number of times over a sequence. | Iterative structure that repeats while a state condition remains True. | Operator/literal pair checking object reference identity in memory. |
| **Syntax / Delimiters** | `if cond:` / `elif cond:` / `else:` with 4-space indented blocks. | `for var in range(start, stop, step):` with 4-space indented body. | `while condition:` with 4-space indented loop body. | `var is None` or `var is not None`. |
| **Permitted Operators / Keywords** | `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`. | Loop variable assignment, `break`, `continue`, accumulators. | Comparison expression, boolean variables, `break`, `continue`. | `is`, `is not`. |
| **Type Invariant / Scope** | Does not alter variable types; depends on existing state. | Creates/rebinds target variable on each turn across the generated range. | Relies on external variable initialization and in-body mutation. | Evaluates memory address equality (`id(a) == id(b)`). |
| **Common Runtime Error** | IndentationError, SyntaxError (missing colon or using `=` instead of `==`). | TypeError (passing non-integers to range), off-by-one boundary bugs. | **Infinite Loop** (omitting condition update step, locking runtime). | Using `is` for value comparison on numbers/strings (unreliable optimization). |

---

#### 2. Real-World Mental Models & Conceptual Mapping
##### Analogy 1: The Railroad Switch Track (Decision Chains & "First True Wins")
Imagine a train traveling along a single track toward a series of automated switches. Each switch represents an `if` or `elif` condition.
* The train checks Switch 1 (`if age < 13`). If `True`, the track shifts, sending the train down the "Child Ticket" siding.
* Once on that siding, the train bypasses all subsequent switches (`elif age < 65`, `else`). It cannot re-enter the main line to flip later switches.
* If Switch 1 is `False`, the train continues straight to Switch 2 (`elif age < 65`).
* The `else` block is the terminal buffer at the very end of the line, catching any train that failed to flip every preceding switch.

```
Main Track ---> [ Switch 1: age < 13? ] ===(True)===> [ Branch A: Child Ticket ] (EXIT)
                     |
                  (False)
                     v
                [ Switch 2: age < 65? ] ===(True)===> [ Branch B: Adult Ticket ] (EXIT)
                     |
                  (False)
                     v
                [ Default Buffer: else ] ===========> [ Branch C: Senior Ticket ] (EXIT)
```

---

##### Analogy 2: The Cashier Scanning Belt (Counters vs. Accumulators)
Imagine a grocery checkout counter where items move down a conveyor belt inside a loop (`for item in groceries`). The cashier maintains two distinct tally instruments on the register desk:
1. **The Clicker Counter (`item_count`):** A physical tally counter initialized to `0`. Every time an item costs over $20, the cashier presses the button once (`count = count + 1`). It tracks **frequency** (how many items).
2. **The Register Cash Drawer (`total_val`):** A monetary accumulator initialized to `$0.00`. Every time an item costs over $20, the cashier adds that specific item's dollar value into the drawer (`total = total + price`). It tracks **summed quantity** (how much total value).

```
[ Incoming Stream: $12.00, $25.00, $5.00, $30.00 ]
                     |
                     v
          Is Price > $20.00?
             /        \
         (YES)        (NO) ---> Skip to next item
           /            \
          v              v
 +1 to Clicker     +$Price to Drawer
 (item_count += 1)  (total_val += price)
```

---

##### Analogy 3: Physical Tickets vs. Seat Numbers (Value == vs. Identity is)
Imagine two identical physical paper concert tickets placed on a table.
* **Ticket Box A:** Printed with "Section 101, Row A, Seat 5".
* **Ticket Box B:** Printed with "Section 101, Row A, Seat 5".
* **Value Equality (`A == B`):** Evaluates to `True` because the text written inside both boxes is identical.
* **Object Identity (`A is B`):** Evaluates to `False` because they are two distinct slips of paper sitting at different physical coordinates on the table.
* **Assigning `C = A`:** Does not print a new ticket; it attaches a second labeled sticker (C) to Ticket Box A. Now, `C is A` evaluates to `True`.

```
Name Space (Variables)        Heap Memory (Object Storage)
+-------+                     +---------------------------------------+
|   A   | ------------------> | [Memory Address 0x101]                |
+-------+                     | Value: "Section 101, Row A, Seat 5"   |
                              +---------------------------------------+
+-------+                     +---------------------------------------+
|   B   | ------------------> | [Memory Address 0x202]                |
+-------+                     | Value: "Section 101, Row A, Seat 5"   |
                              +---------------------------------------+
+-------+                     |
|   C   | --------------------+ (Points to same Address 0x101)
+-------+
```

---

#### 3. Idiomatic Python Implementation & State Tracing
##### Snippet 1: Decision Logic, Chained Comparisons, and Refactoring
```python
# Topic: Refactored Decision Chain with Chained Range Checks
temp = 18

if temp >= 30:
    # State: temp=18 >= 30 (False) -> Skip block
    status = "Hot"
elif 15 <= temp < 30:
    # State: 15 <= 18 < 30 evaluates as (15 <= 18) and (18 < 30) -> True and True -> True
    # Executing block: status set to "Mild"
    status = "Mild"
elif 0 <= temp < 15:
    # Skipped because preceding branch succeeded
    status = "Cold"
else:
    # Skipped
    status = "Freezing"

print(f"Temperature: {temp}C | Status: {status}")
# Console Output: Temperature: 18C | Status: Mild
```

---

##### Snippet 2: String Membership and Short-Circuit Diagnostics
```python
# Topic: Substring Searching and Logical Short-Circuiting Mechanics
log_entry = "WARN: Disk space low on /dev/sda1"

# Short-circuit test 1: 'and' operator
# Left operand ("CRITICAL" in log_entry) -> False
# Right operand (print(...)) is SKIPPED due to short-circuiting
if "CRITICAL" in log_entry and print("DIAGNOSTIC: Evaluating right side of AND"):
    action = "Escalate"
else:
    # Executes because condition evaluated to False
    action = "Log Only"

# Short-circuit test 2: 'or' operator
# Left operand ("WARN" in log_entry) -> True
# Right operand (print(...)) is SKIPPED because True OR anything is True
if "WARN" in log_entry or print("DIAGNOSTIC: Evaluating right side of OR"):
    severity = "Medium"

print(f"Action: {action} | Severity: {severity}")
# Console Output: Action: Log Only | Severity: Medium
```

---

##### Snippet 3: Bounded Loops (`for`), Step Variations, and Accumulation
```python
# Topic: Accumulator Pattern and Step Iteration
sum_even = 0
count_even = 0

# range(start=2, stop=11, step=2) -> Sequence: 2, 4, 6, 8, 10
for num in range(2, 11, 2):
    # Turn 1: num=2  | sum_even = 0 + 2 = 2   | count_even = 0 + 1 = 1
    # Turn 2: num=4  | sum_even = 2 + 4 = 6   | count_even = 1 + 1 = 2
    # Turn 3: num=6  | sum_even = 6 + 6 = 12  | count_even = 2 + 1 = 3
    # Turn 4: num=8  | sum_even = 12 + 8 = 20 | count_even = 3 + 1 = 4
    # Turn 5: num=10 | sum_even = 20+10 = 30 | count_even = 4 + 1 = 5
    sum_even += num
    count_even += 1

print(f"Count: {count_even} | Sum: {sum_even}")
# Console Output: Count: 5 | Sum: 30
```

---

##### Snippet 4: Unbounded Iteration (`while`), Loop Control, and Gatekeeper Pattern
```python
# Topic: while Loop Gate with break and continue Filtering
attempts = 0
max_attempts = 3
access_granted = False

# Sequence simulation: inputs = ["wrong1", "skip_me", "admin123"]
simulated_inputs = ["wrong1", "skip_me", "admin123"]

while attempts < max_attempts:
    curr_input = simulated_inputs[attempts]
    attempts += 1  # State Update: Ensures loop progresses
    
    if curr_input == "skip_me":
        # Aborts current iteration without checking password
        continue
        
    if curr_input == "admin123":
        access_granted = True
        # Terminates loop immediately
        break

print(f"Attempts: {attempts} | Access Granted: {access_granted}")
# Console Output: Attempts: 3 | Access Granted: True
```

---

#### 4. Defensive Programming & Common Traps
##### Trap 1: Accidental Assignment Operator in Conditions
Students often confuse the assignment operator (`=`) with the equality comparison operator (`==`).

```python
# INCORRECT: Causes SyntaxError in Python 3
score = 85
if score = 100:
    print("Perfect score!")
# Error Output: SyntaxError: invalid syntax. Maybe you meant '==' or ':='?
```

```python
# CORRECT: Uses comparison operator ==
score = 85
if score == 100:
    print("Perfect score!")
else:
    print("Standard score.")
```

---

##### Trap 2: Incorrect Condition Ordering Leading to Unreachable Code
Placing a general condition before a specific condition in an `if`/`elif` chain renders the specific condition dead code.

```python
# INCORRECT: Logical Bug - Senior branch is unreachable
age = 72
if age >= 18:
    # 72 >= 18 is True -> Executes immediately for all adults AND seniors!
    tier = "Adult"
elif age >= 65:
    # UNREACHABLE CODE: Any age >= 65 already satisfied age >= 18 above.
    tier = "Senior"
# Result: tier = "Adult" (Incorrect classification for 72-year-old)
```

```python
# CORRECT: Orders conditions from most specific (highest constraint) to general
age = 72
if age >= 65:
    tier = "Senior"
elif age >= 18:
    tier = "Adult"
else:
    tier = "Child"
# Result: tier = "Senior"
```

---

##### Trap 3: Missing State Update in `while` Loop (Infinite Loop)
Omitting the control variable update causes the condition to remain `True` indefinitely, freezing the runtime.

```python
# INCORRECT: Infinite Loop Trap
count = 5
while count > 0:
    print(f"T-minus {count}")
    # BUG: Forgot count = count - 1
    # Loop repeats printing "T-minus 5" forever.
```

```python
# CORRECT: Follows Initialize -> Test -> Update pattern
count = 5
while count > 0:
    print(f"T-minus {count}")
    count -= 1  # Guaranteed progress toward termination (count > 0 becomes False)
print("Liftoff!")
```

---

##### Trap 4: Misplacing `break` vs. `continue` ("Only Done Printed" Bug)
Using `break` when filtering data prematurely terminates processing on the very first unmatched item.

```python
# INCORRECT: Uses break instead of continue when filtering odd numbers
numbers = [1, 2, 3, 4]
for n in numbers:
    if n % 2 != 0:
        break  # BUG: Immediately kills the loop on 1! 2, 3, 4 are never inspected.
    print(f"Even: {n}")
# Result Output: (Nothing printed except code after loop)
```

```python
# CORRECT: Uses continue to skip odd numbers while maintaining loop execution
numbers = [1, 2, 3, 4]
for n in numbers:
    if n % 2 != 0:
        continue  # Skips current odd number, proceeds to next iteration
    print(f"Even: {n}")
# Console Output:
# Even: 2
# Even: 4
```

---

##### Trap 5: `range()` Boundary Off-By-One Error
Assuming `range(1, 5)` includes `5`. The stop value in Python's `range` function is strictly exclusive.

```python
# INCORRECT: Expecting 5 iterations from range(1, 5)
total = 0
for i in range(1, 5):
    total += i
# Only adds 1 + 2 + 3 + 4 = 10 (Missed 5!)
```

```python
# CORRECT: Adds +1 to the intended boundary
total = 0
for i in range(1, 6):  # Generates 1, 2, 3, 4, 5
    total += i
# Result: total = 15
```

---

#### 5. Python Memory Mechanics, References & Scope
##### Dynamic Binding, Heap Memory, and Identity
Python manages memory using an object-centric model:
1. **Objects in Heap Memory:** All data values (integers, strings, booleans) exist as instantiated objects in heap memory. Each object contains a type header, reference count, and raw value.
2. **Variables as Reference Names:** Variable names in Python are not typed storage "boxes." They are untyped pointers (names) in a namespace symbol table bound to memory objects in heap memory.
3. **Small Integer Caching Optimization:** During startup, Python pre-allocates and caches integer objects in the range `-5` through `257`.
    * Assigning `a = 10` and `b = 10` binds both names to the **exact same pre-cached heap object**. Thus, `a is b` evaluates to `True`.
    * Assigning `x = 1000` and `y = 1000` instantiates **two distinct integer objects** in heap memory. Thus, `x == y` evaluates to `True` (same value), but `x is y` evaluates to `False` (different memory addresses).
4. **Rebinding vs. Mutation:** When you execute `y = x`, `y` is bound to the exact object `x` currently points to (`x is y` is `True`). When you subsequently execute `y = y + 5`, Python evaluates `1000 + 5 = 1005`, creates a *new* object `1005` in heap memory, and rebinds `y` to this new address. `x` remains bound to `1000`.

---

##### ASCII Memory Architecture Diagram
```
[ Namespace / Symbol Table ]                   [ Heap Memory Area ]

  Variable Name:                              Object References:
  
  +-----------+                               +----------------------------------+
  |     a     | ----------------------------> | PyObject (int)                   |
  +-----------+                               | Memory Address: 0x7FFF0001 (Cached)|
  |     b     | ----------------------------> | Value: 10                        |
  +-----------+                               +----------------------------------+
                                                (a is b -> True)

  +-----------+                               +----------------------------------+
  |     x     | ----------------------------> | PyObject (int)                   |
  +-----------+                               | Memory Address: 0x00A1B2C3        |
                                              | Value: 1000                       |
                                              +----------------------------------+
                                                (x == y -> True, x is y -> False)

  +-----------+                               +----------------------------------+
  |     y     | ----------------------------> | PyObject (int)                   |
  +-----------+                               | Memory Address: 0x00D4E5F6        |
                                              | Value: 1000                       |
                                              +----------------------------------+

  Rebinding Execution: y = y + 5

  +-----------+                               +----------------------------------+
  |  y (rebound) ---------------------------> | PyObject (int)                   |
  +-----------+                               | Memory Address: 0x00F98765        |
                                              | Value: 1005                       |
                                              +----------------------------------+
```

---

#### 6. Practical Integration / Mini Case Study
##### Comprehensive Multi-Step Script: Automated E-Commerce Order Processor
This single functional script integrates all Week 3 concepts: `while` gate loop, function definitions (`def`), branching logic (`if`/`elif`/`else`), membership testing (`in`), `for` loop with `range`, accumulators, counters, and f-string reporting.

```python
def classify_shipping(order_total, is_vip):
    # Categorizes shipping charges using decision table rules
    if is_vip or order_total >= 50.0:
        return 0.0
    elif 25.0 <= order_total < 50.0:
        return 5.0
    else:
        return 10.0


def process_batch_transactions():
    print("=== STARTING E-COMMERCE BATCH PROCESSOR ===")
    
    # Aggregator Variables
    total_revenue = 0.0
    flagged_orders_count = 0
    valid_orders_count = 0
    
    # Simulated Input Queue: List of tuples (order_id, user_msg, item_prices, is_vip)
    transaction_queue = [
        ("ORD101", "URGENT: Expedite order", [12.50, 15.00, 8.00], False),   # Total $35.50 -> Ship $5.0
        ("ORD102", "Standard delivery", [60.00], False),                     # Total $60.00 -> Ship $0.0
        ("ORD103", "CANCEL ORDER immediately", [100.00], False),             # Flagged -> Skipped
        ("ORD104", "FYI: Gift wrap requested", [15.00], True),              # VIP -> Total $15.00 -> Ship $0.0
        ("END", "TERMINATE QUEUE", [], False)                               # Sentinel value
    ]
    
    queue_index = 0
    
    # Unbounded while loop controlling queue processing
    while queue_index < len(transaction_queue):
        order_id, memo, prices, is_vip = transaction_queue[queue_index]
        queue_index += 1  # State update
        
        # Termination check
        if order_id == "END":
            print("Sentinel 'END' encountered. Halting batch loop.")
            break
            
        # String membership check for flagged orders
        if "CANCEL" in memo or "INVALID" in memo:
            print(f"[{order_id}] FLAGGED: Cancel keyword detected in memo. Skipping.")
            flagged_orders_count += 1
            continue  # Skip processing rest of loop turn
            
        # Bounded iteration to accumulate item prices
        subtotal = 0.0
        for p in prices:
            subtotal += p
            
        # Function call incorporating logic & short-circuit evaluation
        shipping = classify_shipping(subtotal, is_vip)
        final_order_cost = subtotal + shipping
        
        # Update aggregators
        total_revenue += final_order_cost
        valid_orders_count += 1
        
        # Formatted output
        priority_flag = "HIGH" if "URGENT" in memo else "NORMAL"
        print(f"[{order_id}] Priority: {priority_flag} | Subtotal: ${subtotal:.2f} | "
              f"Shipping: ${shipping:.2f} | Total: ${final_order_cost:.2f}")

    print("\n=== BATCH PROCESSING SUMMARY REPORT ===")
    print(f"Valid Orders Processed: {valid_orders_count}")
    print(f"Flagged Orders Skipped : {flagged_orders_count}")
    print(f"Total Revenue Generated : ${total_revenue:.2f}")

# Execute case study
process_batch_transactions()
```

---

##### Execution Step Trace Table
| Step | Order ID | Memo / Flag Check | Subtotal Calc | Shipping Calc | Order Total | Running Total Revenue | Valid Count | Flagged Count |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| **1** | ORD101 | "URGENT" present -> Priority HIGH | 12.5+15.0+8.0 = $35.50 | 25 <= 35.5 < 50 -> $5.00 | $40.50 | $40.50 | 1 | 0 |
| **2** | ORD102 | Standard -> Priority NORMAL | 60.00 = $60.00 | 60.0 >= 50.0 -> $0.00 | $60.00 | $100.50 | 2 | 0 |
| **3** | ORD103 | "CANCEL" in memo -> continue | Skipped | Skipped | Skipped | $100.50 | 2 | 1 |
| **4** | ORD104 | "FYI" present | 15.00 = $15.00 | is_vip=True -> $0.00 | $15.00 | $115.50 | 3 | 1 |
| **5** | END | order_id == "END" -> break | Terminated | Terminated | Terminated | $115.50 | 3 | 1 |

```text
=== CONSOLE OUTPUT RESULT ===
=== STARTING E-COMMERCE BATCH PROCESSOR ===
[ORD101] Priority: HIGH | Subtotal: $35.50 | Shipping: $5.00 | Total: $40.50
[ORD102] Priority: NORMAL | Subtotal: $60.00 | Shipping: $0.00 | Total: $60.00
[ORD103] FLAGGED: Cancel keyword detected in memo. Skipping.
[ORD104] Priority: NORMAL | Subtotal: $15.00 | Shipping: $0.00 | Total: $15.00
Sentinel 'END' encountered. Halting batch loop.

=== BATCH PROCESSING SUMMARY REPORT ===
Valid Orders Processed: 3
Flagged Orders Skipped : 1
Total Revenue Generated : $115.50
```

---

#### 7. Step-by-Step Code Tracing Challenges & Diagnostics
##### Challenge A: Complex Logical Short-Circuit & Side Effects
Trace the exact execution, evaluate all short-circuit paths, and provide final terminal output.

```python
# Code Code Snippet:
a = False
b = True
c = 0

if a and print("Step A"):
    c += 1
elif b or print("Step B"):
    c += 10
    if not a:
        c += 100

print(f"Final c: {c}")
```

###### Line-by-Line Execution Trace:
1. `a = False`, `b = True`, `c = 0`.
2. `if a and print("Step A"):`
    * `a` is `False`.
    * Because operator is `and` and left operand is `False`, short-circuiting triggers! `print("Step A")` is **never executed**.
    * Expression evaluates to `False`. Move to `elif`.
3. `elif b or print("Step B"):`
    * `b` is `True`.
    * Because operator is `or` and left operand is `True`, short-circuiting triggers! `print("Step B")` is **never executed**.
    * Expression evaluates to `True`. Enter `elif` block.
4. `c += 10` -> `c` becomes `0 + 10 = 10`.
5. `if not a:` -> `not False` evaluates to `True`.
6. `c += 100` -> `c` becomes `10 + 100 = 110`.
7. `print(f"Final c: {c}")` executes.

```text
Final Terminal Output:
Final c: 110
```

---

##### Challenge B: Nested Loops and Range Boundaries
Trace the accumulator and boundary limits.

```python
# Code Snippet:
total = 0
for outer in range(1, 4):         # outer sequence: 1, 2, 3
    for inner in range(outer, 4): # inner sequence depends on outer
        if (outer + inner) % 2 == 0:
            total += (outer * inner)

print(f"Total: {total}")
```

###### Line-by-Line Execution Trace:
1. `outer = 1`: `range(1, 4)` -> inner sequence: `1, 2, 3`.
    * `inner = 1`: `1 + 1 = 2` (Even) -> `total += 1 * 1` -> `total = 1`.
    * `inner = 2`: `1 + 2 = 3` (Odd) -> Skipped.
    * `inner = 3`: `1 + 3 = 4` (Even) -> `total += 1 * 3` -> `total = 1 + 3 = 4`.
2. `outer = 2`: `range(2, 4)` -> inner sequence: `2, 3`.
    * `inner = 2`: `2 + 2 = 4` (Even) -> `total += 2 * 2` -> `total = 4 + 4 = 8`.
    * `inner = 3`: `2 + 3 = 5` (Odd) -> Skipped.
3. `outer = 3`: `range(3, 4)` -> inner sequence: `3`.
    * `inner = 3`: `3 + 3 = 6` (Even) -> `total += 3 * 3` -> `total = 8 + 9 = 17`.

```text
Final Terminal Output:
Total: 17
```

---

##### Challenge C: `while` Loop with Modulo, `continue`, and `break` Interaction
Trace loop variable state updates across skips.

```python
# Code Snippet:
val = 0
output = ""

while val < 10:
    val += 1
    if val % 3 == 0:
        continue
    if val > 7:
        break
    output += f"{val}-"

print(f"Output: {output}")
```

###### Line-by-Line Execution Trace:
* `val = 0`
* Turn 1: `val=1`. `1 % 3 != 0`, `1 <= 7` -> `output = "1-"`.
* Turn 2: `val=2`. `2 % 3 != 0`, `2 <= 7` -> `output = "1-2-"`.
* Turn 3: `val=3`. `3 % 3 == 0` -> `continue` triggers! Skip rest of block.
* Turn 4: `val=4`. `4 % 3 != 0`, `4 <= 7` -> `output = "1-2-4-"`.
* Turn 5: `val=5`. `5 % 3 != 0`, `5 <= 7` -> `output = "1-2-4-5-"`.
* Turn 6: `val=6`. `6 % 3 == 0` -> `continue` triggers! Skip rest of block.
* Turn 7: `val=7`. `7 % 3 != 0`, `7 <= 7` -> `output = "1-2-4-5-7-"`.
* Turn 8: `val=8`. `8 % 3 != 0`. `val > 7` (`8 > 7`) is `True` -> `break` triggers! Loop exits immediately.

```text
Final Terminal Output:
Output: 1-2-4-5-7-
```

---

##### Challenge D: Variable Identity and Memory Rebinding State
Trace value equality vs. identity across operations.

```python
# Code Snippet:
x = [1, 2]
y = [1, 2]
z = x

eq_1 = (x == y)
id_1 = (x is y)
id_2 = (x is z)

x.append(3)
eq_2 = (x == z)

print(f"eq_1: {eq_1} | id_1: {id_1} | id_2: {id_2} | eq_2: {eq_2}")
```

###### Line-by-Line Execution Trace:
1. `x = [1, 2]`: Instantiates list object `[1, 2]` at Heap Address `0xA1`.
2. `y = [1, 2]`: Instantiates distinct list object `[1, 2]` at Heap Address `0xB2`.
3. `z = x`: Binds `z` to same Heap Address `0xA1`.
4. `eq_1 = (x == y)` -> Both hold `[1, 2]` -> `True`.
5. `id_1 = (x is y)` -> `0xA1` is `0xB2` -> `False`.
6. `id_2 = (x is z)` -> `0xA1` is `0xA1` -> `True`.
7. `x.append(3)` -> Mutates list at Address `0xA1` to `[1, 2, 3]`. Because `z` points to `0xA1`, `z` now sees `[1, 2, 3]`.
8. `eq_2 = (x == z)` -> Both inspect `0xA1` (`[1, 2, 3]`) -> `True`.

```text
Final Terminal Output:
eq_1: True | id_1: False | id_2: True | eq_2: True
```
