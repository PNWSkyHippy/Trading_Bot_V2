# FE11 Pre-Study: Modern JavaScript & TypeScript for a Python Dev

Written for Ron — maps JS/TS onto what you already know from Python 101–104 (and C/C++ where the analogy is sharper). FE11 is "Intro to **Modern** JavaScript and TypeScript," so everything here is ES6+ style — the way JS is actually written today.

---

## 1. The one mental-model shift

Python is **one runtime, one way to do blocking work**. JavaScript has an **event loop**: there is one main thread, and I/O (network, timers, files) never blocks it — it completes *later* via callbacks/promises (Section 8). If you take one thing from this sheet: **in JS, "later" is a first-class concept.**

C/C++ analogy: think of the event loop like a `select()`/`epoll()` reactor loop. Your code registers interest ("call me back when…") and the loop dispatches. Python's `asyncio` is the closest thing you've used — JS just made that the *default* posture of the language.

---

## 2. Variables, scope, and the death of `var`

| Python | Modern JS | Notes |
|---|---|---|
| `x = 5` | `let x = 5;` | Reassignable binding |
| `X = 5` (convention) | `const X = 5;` | **True** constant binding (can't rebind; like C++ `T* const`) |
| `global x` | n/a — use module scope | Modules each have their own scope; no global soup |
| — | `var x = 5;` (legacy) | Function-scoped, hoisted. **Don't use it.** Know it exists so old Stack Overflow answers make sense |

```js
// Block scope works like C++ braces — let/const are scoped to the block
if (true) {
  let a = 1;
  const b = 2;
}
// console.log(a); // ReferenceError: a is not defined — like a C++ local
```

**`const` gotcha:** `const` freezes the *binding*, not the object — exactly like C++ `int* const p` (pointer fixed, pointee mutable). `const arr = [1,2]; arr.push(3);` is fine. Python has no equivalent; your "constants by convention" become real `const`s.

### Types are dynamic (until TypeScript, Section 9)

```js
let x = 5;        // number
x = "hello";      // now a string — legal in plain JS, a compile error in TS
```

The seven primitives: `number` (all floats — **there is no int/float split**, like C's `double` for everything), `string`, `boolean`, `null`, `undefined`, `bigint`, `symbol`. Plus `object` (which includes arrays and functions).

**`null` vs `undefined`:** `undefined` = "declared but never assigned" (like an uninitialized concept, but defined); `null` = "deliberately empty" (like Python's `None`). Use `===` to tell them apart.

**Equality — the trap every Python dev hits:**

```js
0 == "0"    // true  — loose equality coerces types. NEVER use this.
0 === "0"   // false — strict equality, no coercion. ALWAYS use this.
null == undefined  // true (the one idiomatic exception; some linters allow it)
```

Rule of thumb: `==` doesn't exist. Use `===` and `!==` exclusively.

---

## 3. Functions — first-class citizens

In C, function pointers are awkward. In JS, functions are values, like Python's first-class functions but used *far* more aggressively.

```js
// Declaration (hoisted — callable before its line, like a C prototype + definition)
function add(a, b) {
  return a + b;
}

// Expression assigned to a const — the modern default
const add2 = function (a, b) {
  return a + b;
};

// Arrow function — the one you'll write 90% of the time
const add3 = (a, b) => a + b;          // implicit return, no braces
const square = (x) => {                // braces = explicit return needed
  return x * x;
};
const greet = name => `Hello, ${name}`; // one param: parens optional
```

**Default parameters and rest** will feel familiar:

```js
function connect(host, port = 8181, ...options) {  // like *args with a default
  console.log(host, port, options);
}
connect("localhost");              // localhost 8181 []
connect("localhost", 7496, "a");   // localhost 7496 ['a']
```

**Template literals** — Python f-strings with backticks:

```js
const symbol = "ES";
const msg = `Scanning ${symbol} at ${new Date().toLocaleTimeString()}`;
```

---

## 4. Objects and classes — Python OOP with different clothes

```js
// Object literal — like a Python dict, but keys are identifiers and it has methods
const config = {
  host: "localhost",
  port: 8181,
  describe() {
    return `${this.host}:${this.port}`;  // `this` ≈ self, but DYNAMIC (see below)
  },
};
config.describe(); // "localhost:8181"
```

**Destructuring** — unpacking on steroids:

```js
const { host, port } = config;        // like host, port = config["host"], config["port"]
const [first, second, ...rest] = [1, 2, 3, 4];  // like a, b, *rest = [...]
```

**Spread** — the `*`/`**` unpacking operator, generalized:

```js
const base = { a: 1, b: 2 };
const extended = { ...base, c: 3 };   // like {**base, "c": 3}
const nums = [1, 2, 3];
const more = [...nums, 4];            // like [*nums, 4]
```

### Classes

```js
class Signal {
  // Class fields — declared like C++ member init, no constructor boilerplate needed
  active = true;

  constructor(symbol, strength) {   // __init__
    this.symbol = symbol;           // self.symbol
    this.strength = strength;
  }

  isStrong() {                      // method — no `self` param; `this` is implicit
    return this.strength > 60;
  }

  static describe() {               // @staticmethod
    return "A trading signal";
  }
}

const s = new Signal("PHA/USD", 72);
console.log(s.isStrong());  // true
```

**The `this` warning (the #1 JS OOP gotcha):** in Python, `self` is explicit and always the instance. In JS, `this` depends on *how the function was called*. If you pass `s.isStrong` as a callback, `this` is lost. Arrow functions capture `this` lexically (like a C++ lambda `[this]` capture) — that's why callbacks are almost always arrows:

```js
setTimeout(() => console.log(s.isStrong()), 1000); // `this` still s — safe
```

### Prototype chain (know it exists)

JS classes are sugar over prototypes: every object has a hidden link to a "parent" object it inherits from. It's like single inheritance resolved at runtime by delegation instead of vtables. You rarely touch it directly in modern code — just know *why* `arr.map(...)` exists on every array.

---

## 5. Arrays — your lists, with superpowers

```js
const prices = [93.8, 94.1, 93.2];

// map / filter / reduce — list comprehensions as method chains
const doubled   = prices.map(p => p * 2);                    // [p*2 for p in prices]
const high      = prices.filter(p => p > 93.5);              // [p for p in prices if p > 93.5]
const total     = prices.reduce((sum, p) => sum + p, 0);      // functools.reduce
const anyHigh   = prices.some(p => p > 94);                  // any(...)
const allHigh   = prices.every(p => p > 93);                 // all(...)
const firstHigh = prices.find(p => p > 94);                  // next((p for p in ...), None-ish)
```

**Iteration:**

```js
for (const p of prices) { /* like `for p in prices` */ }
for (const [i, p] of prices.entries()) { /* like enumerate(prices) */ }
prices.forEach(p => console.log(p));  // method form; can't `break` out of it
```

Note: `for...of` iterates **values** (Python-style). `for...in` iterates **keys** — a classic trap; don't use it on arrays.

---

## 6. Modules — `import`/`export` instead of plain `import`

Each file is a module with its own scope (no more `if __name__ == "__main__"` hacks; use `node file.js` to run).

```js
// signals.js
export const VERSION = "2.0";
export function strength(s) { return s > 60 ? "strong" : "weak"; }
export default class Scanner { /* ... */ }   // one default export per module
```

```js
// bot.js
import Scanner, { VERSION, strength } from "./signals.js";  // like `from signals import ...`
import * as sig from "./signals.js";                        // like `import signals as sig`
```

---

## 7. Truthiness, short-circuit, and the modern operators

Falsy values: `false`, `0`, `""`, `null`, `undefined`, `NaN`. Everything else is truthy — note `"0"` and `[]` are **truthy** (unlike Python's empty list!).

```js
const name = user.name || "anonymous";   // like `user.name or "anonymous"`
const port = config.port ?? 8181;        // ?? = nullish coalescing: only null/undefined fall through
                                         // (|| would also fall through on 0 and "" — often a bug)
config.timeout ??= 5000;                 // assign only if null/undefined
user?.profile?.email;                    // ?. = optional chaining: no AttributeError-style crash
```

`?.` and `??` are the two operators you'll wish Python had. They eliminate oceans of `if x is not None` guards.

---

## 8. Async — promises and async/await

This is the section that matters most for "modern" JS. Your bot already lives in this world (FastAPI signal receiver, APScheduler) — JS just makes it the native idiom.

```js
// A Promise is a value that will resolve LATER — like a concurrent.futures.Future
function fetchPrice(symbol) {
  return new Promise((resolve, reject) => {
    setTimeout(() => resolve({ symbol, price: 94.2 }), 500); // resolves after 500ms
  });
}

// await pauses THIS function (not the thread) until the promise resolves.
// The event loop keeps serving everything else meanwhile — like asyncio, but built-in.
async function scan() {
  console.log("requesting…");
  const quote = await fetchPrice("KO");   // function suspends here; thread does not block
  console.log("got", quote.price);        // runs 500ms later
  return quote;
}

scan().then(q => console.log("done:", q.symbol)); // .then = "call me back when done"
console.log("scan started");  // prints BEFORE "got" — ordering is the whole lesson
```

Output order: `requesting…` → `scan started` → (500ms) → `got 94.2` → `done: KO`.

**Parallel work** — `Promise.all` is `asyncio.gather`:

```js
const [a, b] = await Promise.all([fetchPrice("KO"), fetchPrice("ES")]);
```

**Error handling** is `try/catch` (like Python, spelled differently):

```js
try {
  const q = await fetchPrice("BOGUS");
} catch (err) {
  console.error("failed:", err.message);
}
```

C/C++ analogy: `async/await` is compiler-generated state-machine code — conceptually what you'd hand-write with callbacks and a state enum, except the compiler does it. Unhandled promise rejections crash Node processes the way uncaught exceptions crash C++ — always `catch`.

---

## 9. TypeScript — JavaScript with a compile-time type checker

TypeScript = JS + static types that are **erased at compile time** (no runtime overhead, no runtime checking — like C++ templates vanishing after compilation, or Python type hints that are actually enforced by a compiler).

```ts
// Primitives and inference — annotate the boundary, let inference do the rest
let symbol: string = "ES";
let price = 94.2;                 // inferred number — annotation optional

function pctChange(open: number, close: number): number {
  return ((close - open) / open) * 100;
}
// pctChange("a", "b");  // COMPILE ERROR — caught before it ever runs
```

```ts
// Interfaces — like Python dataclasses / C++ structs, but for shape-checking
interface Trade {
  symbol: string;
  side: "long" | "short";   // union of string literals — an enum without the boilerplate
  qty: number;
  stopLoss?: number;         // ? = optional field
}

const t: Trade = { symbol: "KO", side: "long", qty: 10 };  // OK, stopLoss omitted
```

```ts
// Generics — C++ templates, civilized
function first<T>(arr: T[]): T | undefined {
  return arr[0];
}
const n = first([1, 2, 3]);      // T inferred as number, n: number | undefined
```

**What TS gives you that Python hints don't:** the compiler *refuses* to emit code on type errors (in strict mode), and your editor gets C++-IDE-level autocomplete and refactoring. **What it doesn't do:** any runtime validation — `JSON.parse` results are `any` until you check them, same discipline as validating webhook payloads in your FastAPI receiver.

---

## 10. Python-dev gotcha table

| Python habit | JS reality |
|---|---|
| `==` compares values | Use `===`; `==` coerces (`0 == "0"` is `true`) |
| `[]` / `{}` are falsy | `[]` and `{}` are **truthy** — check `.length` / `Object.keys()` |
| `self` is explicit | `this` is implicit and call-site dependent; use arrows in callbacks |
| `import` runs top-level code | Modules are scoped; side effects on import are a smell |
| `None` | Two of them: `null` (deliberate) vs `undefined` (never assigned) |
| Integers vs floats | Only `number` (float64); use `bigint` past 2^53 |
| `for k in dict` gives keys | `for...in` on objects gives keys; on arrays use `for...of` for values |
| `and` / `or` / `not` | `&&` / `\|\|` / `!` — plus `??` and `?.` which Python lacks |
| List comprehensions | `.map()` / `.filter()` chains |
| `*args`, `**kwargs` | `...args` (rest/spread) — one operator for both |
| Type hints are advisory | TS types are compiler-enforced (but erased at runtime) |
| `datetime` everywhere | `Date` is famously bad; modern code uses `Temporal` (new) or libs like `date-fns` |
| Threads for concurrency | One thread + event loop; `async/await` for I/O, workers for CPU |

---

## 11. Try it — five exercises (est. 30–45 min total)

Paste each into a file and run with `node file.js` (install Node 20+ LTS if needed).

**E1 — Destructuring + template literals.** Given `const t = { symbol: "PHA/USD", price: 0.0615, change: 10.5 };`, one line to pull out all three fields, then log `` `${symbol} @ ${price} (${change}%)` ``.

**E2 — map/filter chain.** From `[93.8, 94.1, 93.2, 95.0]`, produce an array of strings like `"94.10 ▲"` for prices above 93.5 only (use `toFixed(2)`).

**E3 — `this` trap.** Write a class `Counter` with a `count` field and an `inc()` method; call `setTimeout(c.inc, 100)` and observe the crash; fix it with an arrow wrapper. *This* is the lesson FE11 will test.

**E4 — async ordering.** Write two `fetchPrice`-style promises (300ms and 100ms), `await` them sequentially, then with `Promise.all`; log timestamps to feel the difference.

**E5 — TS interface.** Define `interface Signal { symbol: string; strength: number; side?: "long"|"short" }`, write `isStrong(s: Signal): boolean`, and intentionally pass a bad object to watch the compiler complain. (Run with `npx tsc --strict file.ts` or the TS playground.)

---

### Suggested next steps when FE11 starts
- Keep this sheet as the "translate my Python brain" reference; the course will add DOM, events, and frontend build tooling on top.
- Your ray-tracer OOP maps directly onto TS classes + interfaces — a small TS port of one scene module would be a great FE11 project crossover.

*Prepared 2026-10-19 for FE11 pre-study. Sources: your degree plan and pre-study note in memory (MEMORY.md#L16), your Python/C++ background and study-format preferences (MEMORY.md#L15, #L62).*
