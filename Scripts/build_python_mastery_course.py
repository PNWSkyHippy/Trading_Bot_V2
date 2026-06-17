from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path

SRC = Path(r"C:\Users\Linda\OneDrive\Documents\python_study_plan-1.html")
OUT = Path(r"C:\Users\Linda\OneDrive\Documents\python_mastery_interactive_course.html")


class OutlineParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.weeks = []
        self.week = None
        self.in_week = False
        self.in_h2 = False
        self.in_topic_tag = False
        self.in_td = False
        self.skip_span = False
        self.row = []
        self.cell = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "")
        if tag == "div" and "week-card" in cls:
            self.in_week = True
            self.week = {"title": "", "tagline": "", "days": []}
        elif self.in_week and tag == "h2":
            self.in_h2 = True
        elif self.in_week and tag == "div" and "topic-tag" in cls:
            self.in_topic_tag = True
        elif self.in_week and tag == "tr":
            self.row = []
        elif self.in_week and tag == "td":
            self.in_td = True
            self.cell = []
        elif self.in_td and tag == "span" and "exercise-tag" in cls:
            self.skip_span = True
        elif self.in_td and tag == "code":
            self.cell.append("`")
        elif self.in_td and tag == "br":
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_h2 = False
        elif tag == "div" and self.in_topic_tag:
            self.in_topic_tag = False
        elif tag == "span" and self.skip_span:
            self.skip_span = False
        elif tag == "code" and self.in_td:
            self.cell.append("`")
        elif tag == "td" and self.in_td:
            text = re.sub(r"\s+", " ", "".join(self.cell)).strip()
            self.row.append(text)
            self.in_td = False
        elif tag == "tr" and self.in_week and len(self.row) == 4 and self.row[0] != "Day":
            day, topic, exercise, time = self.row
            self.week["days"].append(
                {"day": day, "topic": topic, "exercise": exercise, "time": time}
            )
        elif tag == "div" and self.in_week and self.week and len(self.week["days"]) == 5:
            self.weeks.append(self.week)
            self.week = None
            self.in_week = False

    def handle_data(self, data):
        if self.in_h2 and self.week is not None:
            self.week["title"] += data.strip()
        elif self.in_topic_tag and self.week is not None:
            self.week["tagline"] += data.strip()
        elif self.in_td and not self.skip_span:
            self.cell.append(data)


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


REFERENCE_LINKS = [
    ("Python Tutorial", "https://docs.python.org/3/tutorial/index.html"),
    ("Python Library Reference", "https://docs.python.org/3/library/index.html"),
    ("Built-in Functions", "https://docs.python.org/3/library/functions.html"),
    ("VS Code Python", "https://code.visualstudio.com/docs/languages/python"),
    ("VS Code Python Debugging", "https://code.visualstudio.com/docs/python/debugging"),
    ("pytest", "https://docs.pytest.org/en/stable/"),
    ("pytest Fixtures", "https://docs.pytest.org/en/stable/explanation/fixtures.html"),
    ("pytest Parametrize", "https://docs.pytest.org/en/stable/how-to/parametrize.html"),
    ("Requests Quickstart", "https://requests.readthedocs.io/en/latest/user/quickstart/"),
    ("Rich", "https://rich.readthedocs.io/en/stable/"),
]


EXAMPLES = {
    "enumerate": """names = ["Ada", "Grace", "Guido"]\nfor index, name in enumerate(names, start=1):\n    print(f"{index}. {name}")""",
    "input": """width = float(input("Width: "))\nheight = float(input("Height: "))\nprint(f"Area = {width * height:.2f}")""",
    "string": """full = input("First and last name: ").strip()\nfirst, last = full.split()[0], full.split()[-1]\nprint(f"{last.title()}, {first.title()}")""",
    "conditional": """score = float(input("Score: "))\nif score < 0 or score > 100:\n    print("Invalid")\nelif score >= 90:\n    print("A")\nelif score >= 80:\n    print("B")\nelse:\n    print("Keep practicing")""",
    "list": """items = []\nitems.append("coffee")\nitems.append("notebook")\nfor i, item in enumerate(items, 1):\n    print(i, item)""",
    "dict": """sentence = "the bot saw the bot trade"\ncounts = {}\nfor word in sentence.split():\n    counts[word] = counts.get(word, 0) + 1\nprint(counts)""",
    "function": """def is_palindrome(text):\n    cleaned = text.lower().replace(" ", "")\n    return cleaned == cleaned[::-1]\n\nassert is_palindrome("race car")""",
    "args": """def make_coffee(size="medium", *extras, **options):\n    print(size, extras, options)\n\nmake_coffee("large", "cream", iced=True, shots=2)""",
    "lambda": """people = [{"name": "Ada", "age": 36}, {"name": "Grace", "age": 85}]\nprint(sorted(people, key=lambda p: p["age"]))""",
    "scope": """def stats(numbers):\n    low = min(numbers)\n    high = max(numbers)\n    average = sum(numbers) / len(numbers)\n    return low, high, average\n\nlow, high, avg = stats([4, 8, 15, 16, 23, 42])\nprint(low, high, avg)""",
    "tuple": """point = (10, 20)\nx, y = point\nscores = [95, 82, 77, 61]\nsummary = (min(scores), max(scores), sum(scores) / len(scores))\nprint(point, summary)""",
    "file": """from pathlib import Path\ntext = Path("sample.txt").read_text(encoding="utf-8")\nsummary = f"Words: {len(text.split())}\\nChars: {len(text)}\\n"\nPath("summary.txt").write_text(summary, encoding="utf-8")""",
    "exception": """try:\n    value = int(input("Number: "))\n    print(100 / value)\nexcept ValueError:\n    print("Enter a whole number")\nexcept ZeroDivisionError:\n    print("Cannot divide by zero")""",
    "json": """import json\nfrom pathlib import Path\nrows = [{"name": "Ada", "role": "Engineer"}]\nPath("people.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")\nprint(json.loads(Path("people.json").read_text(encoding="utf-8")))""",
    "module": """# calc.py\ndef add(a, b):\n    return a + b\n\n# main.py\nfrom calc import add\n\nif __name__ == "__main__":\n    print(add(2, 3))""",
    "pathlib": """from pathlib import Path\n\nroot = Path.cwd()\nfor py_file in root.rglob("*.py"):\n    print(py_file.name, py_file.stat().st_size)\n\ntemp = root / "temp_demo"\ntemp.mkdir(exist_ok=True)""",
    "class": """class BankAccount:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n\n    def deposit(self, amount):\n        self.balance += amount""",
    "inheritance": """class BankAccount:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n\n    def deposit(self, amount):\n        self.balance += amount\n\n\nclass SavingsAccount(BankAccount):\n    def __init__(self, owner, balance=0, interest_rate=0.02):\n        super().__init__(owner, balance)\n        self.interest_rate = interest_rate\n\n    def apply_interest(self):\n        self.balance += self.balance * self.interest_rate\n\n\nacct = SavingsAccount("Ron", 100)\nacct.deposit(50)\nacct.apply_interest()\nprint(acct.owner, acct.balance)""",
    "dunder": """class Vector2D:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n    def __add__(self, other):\n        return Vector2D(self.x + other.x, self.y + other.y)\n    def __repr__(self):\n        return f"Vector2D({self.x}, {self.y})" """,
    "property": """class Money:\n    def __init__(self, cents):\n        self.cents = cents\n    @property\n    def dollars(self):\n        return self.cents / 100""",
    "comprehension": """numbers = [1, 2, 3, 4, 5]\nsquares = [n*n for n in numbers]\nlengths = {word: len(word) for word in ["debug", "test"]}\nprint(squares, lengths)""",
    "generator": """def fibonacci(limit):\n    a, b = 0, 1\n    while a <= limit:\n        yield a\n        a, b = b, a + b\n\nprint(list(fibonacci(100)))""",
    "itertools": """from itertools import product, chain\nfrom functools import lru_cache\n\nprint(list(product(["S", "M"], ["red", "blue"])))\nprint(list(chain([1, 2], [3, 4])))\n\n@lru_cache\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)""",
    "decorator": """from functools import wraps\nfrom time import perf_counter\n\ndef timer(fn):\n    @wraps(fn)\n    def wrapper(*args, **kwargs):\n        start = perf_counter()\n        result = fn(*args, **kwargs)\n        print(fn.__name__, perf_counter() - start)\n        return result\n    return wrapper""",
    "venv": """python -m venv .venv\n.venv\\Scripts\\activate\npython -m pip install requests rich\npython -m pip freeze > requirements.txt""",
    "unittest": """import unittest\n\nclass TestMath(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(2 + 3, 5)\n\nif __name__ == "__main__":\n    unittest.main()""",
    "pytest": """import pytest\n\n@pytest.mark.parametrize("score,grade", [(95, "A"), (82, "B")])\ndef test_grade(score, grade):\n    assert classify_grade(score) == grade""",
    "debug": """import logging\nlogging.basicConfig(level=logging.DEBUG)\n\ndef search(items, term):\n    logging.debug("searching for %r", term)\n    breakpoint()\n    return [x for x in items if term.lower() in x.lower()]""",
    "profile": """import cProfile\n\ndef slow_fib(n):\n    if n < 2:\n        return n\n    return slow_fib(n-1) + slow_fib(n-2)\n\ncProfile.run("slow_fib(30)")\n\n# Then run in PowerShell:\n# black .\n# flake8 .""",
    "api": """import requests\nresp = requests.get("https://jsonplaceholder.typicode.com/todos/1", timeout=10)\nresp.raise_for_status()\nprint(resp.json())""",
    "argparse": """import argparse\nparser = argparse.ArgumentParser(description="Analyze a CSV file")\nparser.add_argument("--input", required=True)\nparser.add_argument("--top", type=int, default=5)\nargs = parser.parse_args()\nprint(args)""",
    "pipeline": """import csv, json, statistics\nfrom pathlib import Path\n\nwith open("data.csv", newline="", encoding="utf-8") as f:\n    values = [float(row["amount"]) for row in csv.DictReader(f)]\n\nreport = {"count": len(values), "mean": statistics.mean(values), "median": statistics.median(values)}\nPath("report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")""",
    "capstone": """class DataLoader:\n    def load(self):\n        raise NotImplementedError\n\nclass Analyzer:\n    def summarize(self, rows):\n        raise NotImplementedError\n\nclass Reporter:\n    def write(self, report):\n        raise NotImplementedError""",
    "polish": """# Final polish checklist\npython -m pytest\nblack .\nflake8 .\n\n# README sections:\n# Install, Usage, Examples, Tests, Known Limits, Next Steps""",
}


def choose_key(topic: str, exercise: str) -> str:
    text = f"{topic} {exercise}".lower()
    checks = [
        ("capstone", "capstone"),
        ("next steps", "polish"),
        ("polish", "polish"),
        ("profiling", "profile"),
        ("cprofile", "profile"),
        ("data processing", "pipeline"),
        ("pipeline", "pipeline"),
        ("itertools", "itertools"),
        ("functools", "itertools"),
        ("pathlib", "pathlib"),
        ("scope", "scope"),
        ("legb", "scope"),
        ("tuple", "tuple"),
        ("json", "json"),
        ("csv", "json"),
        ("generator", "generator"),
        ("yield", "generator"),
        ("decorator", "decorator"),
        ("venv", "venv"),
        ("unittest", "unittest"),
        ("pytest", "pytest"),
        ("debug", "debug"),
        ("logging", "debug"),
        ("api", "api"),
        ("requests", "api"),
        ("argparse", "argparse"),
        ("enumerate", "enumerate"),
        ("condition", "conditional"),
        ("string", "string"),
        ("dictionaries", "dict"),
        ("sets", "dict"),
        ("function", "function"),
        ("*args", "args"),
        ("lambda", "lambda"),
        ("file", "file"),
        ("exception", "exception"),
        ("module", "module"),
        ("inheritance", "inheritance"),
        ("subclass", "inheritance"),
        ("super", "inheritance"),
        ("class", "class"),
        ("dunder", "dunder"),
        ("static", "property"),
        ("property", "property"),
        ("comprehension", "comprehension"),
        ("list", "list"),
        ("input", "input"),
    ]
    for needle, key in checks:
        if needle in text:
            return key
    return "default"


def choose_example(topic: str, exercise: str) -> str:
    key = choose_key(topic, exercise)
    return EXAMPLES.get(
        key,
        'print("Type the smallest possible version first, then add one feature.")',
    )


CONCEPTS = {
    "enumerate": (
        "Use enumerate when you need the item and its position. It gives you "
        "pairs like index, value without manually maintaining a counter."
    ),
    "input": (
        "input always returns a string. Convert it with int or float before math, "
        "and expect bad input while you are learning."
    ),
    "string": (
        "Strings are immutable sequences. Methods such as strip, split, lower, "
        "replace, and title return a new string instead of changing the old one."
    ),
    "conditional": (
        "Python checks if, then each elif in order, then else only if none matched. "
        "Put impossible or invalid cases near the top so they cannot fall through."
    ),
    "list": (
        "Lists keep ordered, changeable data. append adds, pop removes and returns, "
        "remove deletes by value, and indexing starts at zero."
    ),
    "dict": (
        "Dictionaries map keys to values. They are perfect for counts, lookups, "
        "settings, and records where names matter more than numeric positions."
    ),
    "function": (
        "A function packages a repeatable action. Parameters bring values in; "
        "return sends a value back to the caller."
    ),
    "scope": (
        "Scope answers where a name can be seen. Values made inside a function are "
        "local unless returned or deliberately stored somewhere wider."
    ),
    "file": (
        "File code usually has four steps: choose a path, read or write text, parse "
        "or format the content, then handle missing files or bad data."
    ),
    "exception": (
        "Exceptions let you handle expected failures without crashing. Catch specific "
        "errors first, and keep the try block as small as practical."
    ),
    "module": (
        "A module is a .py file you can import. The if __name__ guard lets a file "
        "act as both reusable module and command-line script."
    ),
    "class": (
        "A class is a blueprint for objects. __init__ stores object state on self; "
        "methods are functions that operate on that state."
    ),
    "inheritance": (
        "Inheritance makes a new class from an existing class. Put the parent class "
        "name in parentheses, then use super().__init__(...) to let the parent set "
        "up its part of the object before the child adds more."
    ),
    "dunder": (
        "Dunder methods are hooks Python calls for built-in behavior. __repr__ "
        "controls display; __add__ controls plus; __len__ controls len()."
    ),
    "property": (
        "@property makes a method look like a read-only attribute. Use it for values "
        "computed from other stored data."
    ),
    "comprehension": (
        "A comprehension builds a collection from another iterable in one expression. "
        "Use it when the transformation is short and readable."
    ),
    "generator": (
        "A generator yields one value at a time and pauses between values. It is ideal "
        "when you do not want to build the whole list in memory."
    ),
    "decorator": (
        "A decorator wraps a function with extra behavior. The wrapper receives *args "
        "and **kwargs, calls the original function, then can log, time, cache, or validate."
    ),
    "pytest": (
        "pytest discovers functions named test_*. A good test arranges input, acts by "
        "calling your function, then asserts the exact expected result."
    ),
    "unittest": (
        "unittest groups tests inside classes. Each test method calls assert helpers "
        "such as assertEqual or assertRaises."
    ),
    "debug": (
        "Debugging is controlled observation. Use logs for history, breakpoint for live "
        "inspection, and a small reproducible input so you are not guessing."
    ),
    "api": (
        "HTTP API code sends a request, checks the status, parses JSON, then converts "
        "the response into the shape your program needs."
    ),
    "argparse": (
        "argparse turns command-line flags into typed Python values. Define arguments, "
        "parse them, then pass args into normal functions."
    ),
}


QUIZZES = {
    "inheritance": (
        "How do you make SavingsAccount inherit from BankAccount and still run the parent setup?",
        [
            "class SavingsAccount(BankAccount): then call super().__init__(...) inside the child __init__.",
            "Copy all BankAccount code into SavingsAccount and change the class name.",
            "Create a BankAccount variable inside SavingsAccount but do not subclass it.",
        ],
        0,
        "Parentheses after the class name choose the parent class; super().__init__ runs the parent initializer.",
    ),
    "class": (
        "What does self mean inside a method?",
        [
            "The current object whose data and methods are being used.",
            "A global variable shared by every class.",
            "The file name Python imported.",
        ],
        0,
        "self is the instance. self.balance means this particular account's balance.",
    ),
    "function": (
        "What is the difference between print and return?",
        [
            "print shows text to the screen; return gives a value back to the caller.",
            "return only works in loops.",
            "print stores a value for later use.",
        ],
        0,
        "A caller can reuse a returned value. Printed text is just output.",
    ),
    "list": (
        "Which list method removes and returns the last item by default?",
        ["pop", "append", "sort"],
        0,
        "pop removes an item and gives it back; append adds; sort changes order in place.",
    ),
    "dict": (
        "Why is dict.get(key, 0) useful in a word counter?",
        [
            "It supplies 0 when the key is not there yet.",
            "It sorts the dictionary by key.",
            "It deletes missing keys.",
        ],
        0,
        "counts[word] = counts.get(word, 0) + 1 starts unseen words at zero.",
    ),
    "exception": (
        "Why catch ValueError separately from ZeroDivisionError?",
        [
            "They represent different failures and usually need different messages.",
            "Python requires every except to be alphabetical.",
            "ZeroDivisionError is not an exception.",
        ],
        0,
        "Specific except blocks make the program's response match the actual failure.",
    ),
    "module": (
        "What does if __name__ == '__main__' protect?",
        [
            "Code that should run only when the file is executed directly.",
            "Code that should run every time the file is imported.",
            "The import statement itself.",
        ],
        0,
        "Imported modules define functions/classes but skip the guarded command-line block.",
    ),
    "pytest": (
        "What should an assert in a test compare?",
        [
            "The actual result from your code against the expected result.",
            "Two random values that are probably close.",
            "Only whether the program printed something.",
        ],
        0,
        "Tests are useful when the expected result is specific and checkable.",
    ),
}


def concept_text(topic: str, exercise: str) -> str:
    key = choose_key(topic, exercise)
    return CONCEPTS.get(key, lesson_text(topic))


def walkthrough(topic: str, exercise: str) -> list[str]:
    key = choose_key(topic, exercise)
    common = [
        "Type the example by hand instead of copying it.",
        "Run it once exactly as written.",
        "Change one input or value and predict the new output before running again.",
    ]
    extra = {
        "inheritance": [
            "Find the parent class name inside the child class parentheses.",
            "Find the child __init__ method and the super().__init__ call.",
            "Notice which attributes come from the parent and which are added by the child.",
        ],
        "class": [
            "Find __init__ and identify every attribute assigned to self.",
            "Create two objects and verify their self attributes do not overwrite each other.",
            "Add one small method that changes object state.",
        ],
        "function": [
            "Circle the parameters, then circle the return value.",
            "Call the function with two different inputs.",
            "Store the return value in a variable and print that variable.",
        ],
        "exception": [
            "Run one valid input, one wrong-type input, and one boundary input.",
            "Keep the try block small enough that you know exactly what can fail.",
            "Add a final print after the try/except to prove the program continues.",
        ],
    }.get(key, [])
    return extra + common


def quiz_for(topic: str, exercise: str):
    key = choose_key(topic, exercise)
    if key in QUIZZES:
        return QUIZZES[key]
    return (
        f"What should you be able to explain after this lesson on {topic}?",
        [
            "What each line of the example does and one edge case it should handle.",
            "Only the name of the topic.",
            "How to skip testing until the final week.",
        ],
        0,
        "A lesson is not finished until you can explain the example and test one edge case.",
    )


def lesson_text(topic: str) -> str:
    lower = topic.lower()
    if "class" in lower or "object" in lower:
        return "This lesson is about binding related data and behavior together. Name the objects in the problem, decide what each object owns, then write methods for the actions that belong to that object."
    if "debug" in lower or "test" in lower:
        return "This lesson is about making code trustworthy. Write a small failing case, observe the failure, then use tests, logs, or a debugger to prove the fix instead of guessing."
    if "file" in lower or "json" in lower or "csv" in lower:
        return "This lesson is about moving data between your program and the outside world. Keep parsing, validation, transformation, and output as separate steps so each part can be tested."
    if "loop" in lower or "list" in lower or "dict" in lower or "set" in lower:
        return "This lesson is about collections and repetition. Practice predicting what the collection contains after each loop pass; that mental model is the heart of Python fluency."
    if "function" in lower or "scope" in lower or "lambda" in lower:
        return "This lesson is about reusable logic. Prefer small functions with clear inputs and return values. If a function is hard to name, it is probably trying to do too much."
    if "api" in lower or "cli" in lower or "capstone" in lower:
        return "This lesson is about turning Python into a practical tool. Separate user interface, data loading, core logic, and reporting so the program can grow without becoming tangled."
    return "Read the concept, type the example, run it, then change one input and one edge case. The goal is not memorization; it is building a reliable mental model."


def refs_for(topic: str) -> list[tuple[str, str]]:
    lower = topic.lower()
    refs = [REFERENCE_LINKS[0], REFERENCE_LINKS[1]]
    if "debug" in lower or "vs code" in lower:
        refs.append(REFERENCE_LINKS[4])
    if "test" in lower or "pytest" in lower:
        refs.extend([REFERENCE_LINKS[5], REFERENCE_LINKS[6], REFERENCE_LINKS[7]])
    if "api" in lower or "requests" in lower:
        refs.append(REFERENCE_LINKS[8])
    if "cli" in lower or "argparse" in lower:
        refs.append(("argparse", "https://docs.python.org/3/library/argparse.html"))
    return refs


def code_block(code: str) -> str:
    return f"<pre><code>{esc(code.strip())}</code></pre>"


parser = OutlineParser()
parser.feed(SRC.read_text(encoding="utf-8"))
weeks = parser.weeks
if len(weeks) != 8:
    raise RuntimeError(f"Expected 8 weeks, got {len(weeks)}")

rubric = [
    "Runs from PowerShell without crashing on normal inputs.",
    "Handles empty input, wrong type input, or a boundary case.",
    "Uses clear variable/function/class names.",
    "Has at least three manual tests, asserts, or pytest/unittest tests.",
    "Includes a two-sentence note about what you learned.",
]

cards = []
nav = []
lesson_count = 0
for wi, week in enumerate(weeks, 1):
    nav.append(f'<a href="#week-{wi}">Week {wi}: {esc(week["title"])}</a>')
    lessons = []
    for di, day in enumerate(week["days"], 1):
        lesson_count += 1
        topic = day["topic"]
        lid = f"w{wi}d{di}-{slug(topic)}"
        q, options, answer_idx, answer_note = quiz_for(topic, day["exercise"])
        steps = "".join(f"<li>{esc(step)}</li>" for step in walkthrough(topic, day["exercise"]))
        refs = "".join(
            f'<li><a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a></li>'
            for label, url in refs_for(topic)
        )
        lessons.append(
            f"""
<article class="lesson" id="{lid}">
  <div class="lesson-head">
    <span>Week {wi} · {esc(day['day'])} · {esc(day['time'])}</span>
    <h3>{esc(topic)}</h3>
    <p><strong>Assignment:</strong> {esc(day['exercise'])}</p>
  </div>
  <section><h4>Concept Explained</h4><p>{esc(concept_text(topic, day['exercise']))}</p>
    <details open><summary>How to read this lesson's example</summary><ul>{steps}</ul></details>
  </section>
  <section><h4>Type This Example</h4>{code_block(choose_example(topic, day['exercise']))}</section>
  <section><h4>Practice Project</h4><p>{esc(day['exercise'])}</p>
    <details><summary>Project rubric</summary><ul>{''.join(f'<li>{esc(r)}</li>' for r in rubric)}</ul></details>
    <details><summary>Self-check commands</summary>{code_block('python your_file.py\\npython -m unittest\\npython -m pytest\\nblack .\\nflake8 .')}</details>
  </section>
  <section class="quiz" data-answer="{answer_idx}" data-name="q-{lid}">
    <h4>Quick Quiz</h4><p>{esc(q)}</p>
    {''.join(f'<label><input type="radio" name="q-{lid}" value="{i}"> {esc(opt)}</label>' for i, opt in enumerate(options))}
    <button type="button" onclick="checkQuiz(this)">Check answer</button><span class="quiz-result"></span>
    <details><summary>Answer key</summary><p><strong>{esc(options[answer_idx])}</strong></p><p>{esc(answer_note)}</p></details>
  </section>
  <section><h4>References</h4><ul>{refs}</ul></section>
</article>"""
        )
    cards.append(
        f"""
<section class="week" id="week-{wi}">
  <button class="week-toggle" onclick="toggleWeek(this)" type="button"><span>Week {wi}</span><strong>{esc(week['title'])}</strong><em>{esc(week['tagline'])}</em></button>
  <div class="week-lessons">{''.join(lessons)}</div>
</section>"""
    )

review_prompt = """You are reviewing my Python practice project. Check correctness, edge cases, readability, and whether it satisfies the assignment. Do not rewrite everything unless necessary. Give me: bugs, missing requirements, style improvements, tests I should add, and one small next challenge. Here is the assignment and my code:

[PASTE ASSIGNMENT]
[PASTE CODE]"""

doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Python Mastery Interactive Course</title>
<style>
:root {{ --bg:#101820; --paper:#fbf4e8; --card:#fffdf8; --ink:#17110c; --muted:#686158; --line:#dacdb8; --accent:#2d6a4f; --accent2:#c84b31; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font-family:Segoe UI, Arial, sans-serif; line-height:1.6; }}
header {{ background:#111827; color:white; padding:32px 28px; }}
header h1 {{ margin:0; font-size:clamp(2rem,5vw,4rem); }}
header p {{ color:#d1d5db; max-width:900px; }}
.layout {{ display:grid; grid-template-columns:280px 1fr; min-height:100vh; }}
nav {{ position:sticky; top:0; height:100vh; overflow:auto; background:#0f172a; padding:18px; }}
nav h2 {{ color:#94a3b8; font-size:13px; text-transform:uppercase; letter-spacing:.08em; }}
nav a {{ display:block; color:#e5e7eb; text-decoration:none; padding:8px; border-radius:6px; font-size:14px; }}
nav a:hover {{ background:#1e293b; }}
main {{ padding:24px; max-width:1120px; }}
.intro,.tools,.review,.week {{ background:white; border:1px solid var(--line); border-radius:12px; margin-bottom:18px; }}
.intro,.tools,.review {{ padding:18px; }}
.tools button,.quiz button {{ border:1px solid #111827; background:#111827; color:white; border-radius:6px; padding:7px 10px; cursor:pointer; }}
.week {{ overflow:hidden; }}
.week-toggle {{ width:100%; border:0; border-bottom:1px solid var(--line); padding:16px; background:#fff; cursor:pointer; display:grid; grid-template-columns:80px 1fr; text-align:left; gap:6px; }}
.week-toggle span {{ color:var(--accent2); font-weight:800; text-transform:uppercase; font-size:12px; }}
.week-toggle strong {{ font-size:22px; }}
.week-toggle em {{ grid-column:2; color:var(--muted); font-style:normal; }}
.week.closed .week-lessons {{ display:none; }}
.week-lessons {{ padding:16px; }}
.lesson {{ background:var(--card); border:1px solid #eadfcd; border-radius:10px; padding:16px; margin-bottom:16px; }}
.lesson-head span {{ color:var(--accent2); font-family:Consolas, monospace; font-size:12px; text-transform:uppercase; }}
.lesson h3 {{ margin:.2rem 0; font-size:24px; }}
h4 {{ margin:18px 0 6px; color:#173b2d; }}
pre {{ background:#101820; color:#d1fae5; padding:14px; border-radius:8px; overflow:auto; }}
code {{ font-family:Consolas, Monaco, monospace; }}
details {{ margin:8px 0; padding:8px 10px; border-left:3px solid var(--accent); background:#f7f0e4; }}
.quiz label {{ display:block; margin:6px 0; padding:6px; background:white; border:1px solid #eadfcd; border-radius:6px; }}
.quiz-result {{ margin-left:10px; font-weight:700; }}
.review pre {{ white-space:pre-wrap; }}
@media(max-width:850px) {{ .layout {{ grid-template-columns:1fr; }} nav {{ position:relative; height:auto; }} .week-toggle {{ grid-template-columns:1fr; }} .week-toggle em {{ grid-column:auto; }} }}
</style>
</head>
<body>
<header><h1>Python Mastery Interactive Course</h1><p>Expanded from your 8-week outline into a workbook with teaching notes, examples, projects, rubrics, quizzes, hidden answer keys, and reference links.</p></header>
<div class="layout">
<nav><h2>Course Map</h2>{''.join(nav)}<h2>Core References</h2>{''.join(f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>' for label, url in REFERENCE_LINKS)}</nav>
<main>
<section class="intro"><h2>How To Work The Course</h2><ol><li>Read one lesson.</li><li>Type the example manually.</li><li>Run it from PowerShell.</li><li>Break one thing on purpose and read the error.</li><li>Complete the project and quiz before opening the answer key.</li></ol></section>
<section class="tools"><button onclick="setAllWeeks(true)">Open all weeks</button> <button onclick="setAllWeeks(false)">Collapse all weeks</button> <button onclick="window.print()">Print / Save PDF</button></section>
{''.join(cards)}
<section class="review"><h2>AI Review Prompt</h2><p>Use this after you have a real attempt and want feedback without having the AI do the assignment for you.</p>{code_block(review_prompt)}</section>
</main>
</div>
<script>
function toggleWeek(btn) {{ btn.closest('.week').classList.toggle('closed'); }}
function setAllWeeks(open) {{ document.querySelectorAll('.week').forEach(w => w.classList.toggle('closed', !open)); }}
function checkQuiz(btn) {{
  const box = btn.closest('.quiz');
  const selected = box.querySelector('input[type="radio"]:checked');
  const result = box.querySelector('.quiz-result');
  if (!selected) {{ result.textContent = 'Choose one first.'; result.style.color = '#92400e'; return; }}
  if (selected.value === box.dataset.answer) {{ result.textContent = 'Correct.'; result.style.color = '#15803d'; }}
  else {{ result.textContent = 'Not quite. Try again, then check the answer key.'; result.style.color = '#b91c1c'; }}
}}
setAllWeeks(false);
document.querySelector('#week-1')?.classList.remove('closed');
</script>
</body>
</html>
"""

OUT.write_text(doc, encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Weeks: {len(weeks)}")
print(f"Lessons: {lesson_count}")
print(f"Bytes: {OUT.stat().st_size}")
