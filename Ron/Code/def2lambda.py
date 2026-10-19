"""def2lambda.py - show the lambda version of simple functions.

    python def2lambda.py myfile.py      every def in a file
    python def2lambda.py                paste defs, then a blank line twice (or Ctrl+Z / Ctrl+D)

A def can become a lambda only when its whole body is one  return <expression>.
"""
import ast
import sys


def why_not(fn):
    """Reason fn can't be a lambda, or None when it can."""
    body = [s for s in fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str))]          # a docstring doesn't count
    if fn.decorator_list:
        return "it has a decorator (@...)"
    if isinstance(fn, ast.AsyncFunctionDef):
        return "it is async"
    if len(body) != 1:
        kinds = ", ".join(type(s).__name__.lower() for s in body)
        return f"its body has {len(body)} statements ({kinds}) - a lambda is one expression"
    stmt = body[0]
    if isinstance(stmt, ast.Return):
        if any(isinstance(n, (ast.Yield, ast.YieldFrom, ast.Await)) for n in ast.walk(stmt)):
            return "it uses yield/await"
        return None
    if isinstance(stmt, ast.Expr):
        return None                          # e.g. print(x): lambda returns its result (None)
    return f"its one statement is '{type(stmt).__name__.lower()}', not 'return <expression>'"


def to_lambda(fn):
    for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
        if a.annotation:                     # lambdas can't have type hints
            a.annotation = None
    for a in (fn.args.vararg, fn.args.kwarg):
        if a is not None:
            a.annotation = None
    args = ast.unparse(fn.args)
    stmt = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                                       and isinstance(s.value.value, str))][0]
    expr = ast.unparse(stmt.value) if stmt.value is not None else "None"
    return f"lambda {args}: {expr}" if args else f"lambda: {expr}"


def convert(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"Can't read that code: {exc}")
        return
    fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not fns:
        print("No def found.")
    for fn in fns:
        print(f"def {fn.name}(...):")
        reason = why_not(fn)
        if reason:
            print(f"    no lambda: {reason}\n")
            continue
        lam = to_lambda(fn)
        print(f"    {lam}")
        print(f"    as a name:  {fn.name} = {lam}")
        if len(fn.args.args) == 1:           # one input: fits sort/sorted/min/max key=
            print(f"    as a key:   found_files.sort(key={lam})")
        print()


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            convert(f.read())
        return
    print("Paste your def(s). Two blank lines in a row (or Ctrl+Z then Enter) to convert.")
    lines, blanks = [], 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        blanks = blanks + 1 if not line.strip() else 0
        if blanks >= 2:
            break
        lines.append(line)
    convert("\n".join(lines))


if __name__ == "__main__":
    main()
