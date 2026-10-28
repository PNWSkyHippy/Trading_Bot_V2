"""turtle3d.py - a 3D LOGO for the viewer.  Pure numpy, no Tk.

A turtle walks in 3D leaving tubes, stamps solids, fills flat polygons, and whole
sub-assemblies (PART) can be placed again and again - mirrored, scaled - nested into
torso / head / arm hierarchies.  Output is triangle meshes grouped by instance path, so
it rides the viewer's colour / transform / Taichi / POV-Ray / STL rails unchanged.

A program is plain text, so a Python script can write one (fractals, equations ...):
    import turtle3d
    turtle3d.run_file("mickey.logo", session)          # -> scene entries (Session or App)
    facets = turtle3d.facets(open("x.logo").read())    # -> [(a,b,c,normal)] for STL/OBJ

Language (case-insensitive; ';' or '#' starts a comment; free-form whitespace)
  Frame     turtle starts at 0,0,0 facing +X, left = +Y, up = +Z
  Move      fd n | bk n | goto x y z | home | pu | pd              (pd = pen draws a tube)
  Turn      rt a | lt a   (yaw)    up a | down a   (pitch)    roll a   (bank, + = right)
  Pen       pensize r | color name | joints on|off | detail n (sides, default 12)
  Stamps    cube s | box dx dy dz | sphere r | cylinder r h | cone r h
            (cube/sphere centred on the turtle; box/cylinder/cone run FORWARD from it,
             centred sideways and up - so a limb is "cylinder 2 20")
  Flat      beginfill  fd/rt ... endfill      (polygon of the path; fillthick t = solid slab)
  State     push | pop   (save / restore turtle position, heading, pen, colour)
  Control   repeat n [ ... ] | if expr [ ... ] else [ ... ] | for i a b [ ... ] (step s)
            make name expr | to name :a :b ... end   (then:  name 3 4)
  Parts     part name :a :b ... endpart            (a reusable assembly, own local frame)
            place name [args] [as inst] [mirror l|f|u ...] [scale s]
            group name ... endgroup                 (just a folder in the scene tree)
            use file                                (splice in turtle_lib/file.logo or ./file.logo)
  Maths     + - * / % ^ ( ) comparisons == != < > <= >= ; sin cos tan asin acos atan (degrees),
            sqrt abs min max int round pow exp log rand pi ; variables as :x or x

  `place` puts a copy of the part at the turtle's position and orientation.  Local axes of
  a part are f (forward = its x), l (left = its y), u (up = its z).  `mirror l` flips the
  copy left<->right, so a left arm built at +l becomes the right arm.  Instances become
  groups: "mickey/torso/head/ear_l" and each (instance, colour) becomes one mesh3d entry.
"""
import math
import os
import random
import re
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(HERE, "turtle_lib")


class TurtleError(Exception):
    pass


MAX_STEPS = 2_000_000
MAX_DEPTH = 400


# ---------------------------------------------------------------- tokenizer
_TOK = re.compile(r"""\s*(?:
    (?P<num>\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+)
  | (?P<word>[:"]?[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|==|!=|[-+*/%^(),<>=\[\]])
)""", re.X)


def tokenize(text):
    toks = []
    for ln, raw in enumerate(text.splitlines(), 1):
        line = re.split(r"[;#]", raw, 1)[0]
        pos = 0
        while pos < len(line):
            if not line[pos:].strip():
                break
            m = _TOK.match(line, pos)
            if not m:
                raise TurtleError(f"line {ln}: can't read '{line[pos:].strip()[:20]}'")
            start, pos = m.start(m.lastgroup), m.end()
            glued = (start > 0 and line[start - 1] in " 	" and pos < len(line)
                     and line[pos] not in " 	")      # " -3": a new (negative) argument
            if m.group("num") is not None:
                toks.append(("num", float(m.group("num")), ln, False))
            elif m.group("word") is not None:
                w = m.group("word")
                toks.append(("word", w.lower().lstrip(':"'), ln, False))
            else:
                toks.append(("op", m.group("op"), ln, glued))
    return toks


def _splice_uses(toks, base_dir, seen=()):
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t[0] == "word" and t[1] == "use" and i + 1 < len(toks):
            name = str(toks[i + 1][1])
            path = _find_lib(name, base_dir)
            if path in seen:
                raise TurtleError(f"line {t[2]}: circular use '{name}'")
            with open(path, "r", encoding="utf-8") as fh:
                sub = tokenize(fh.read())
            out += _splice_uses(sub, os.path.dirname(path), seen + (path,))
            i += 2
            continue
        out.append(t)
        i += 1
    return out


def _find_lib(name, base_dir):
    cands = []
    for d in (base_dir, LIB_DIR):
        if d:
            cands += [os.path.join(d, name), os.path.join(d, name + ".logo")]
    for c in cands:
        if os.path.isfile(c):
            return c
    raise TurtleError(f"use: no library '{name}' (looked in {base_dir or '.'} and turtle_lib/)")


# ---------------------------------------------------------------- parser
ARITY = {"fd": 1, "forward": 1, "bk": 1, "back": 1, "rt": 1, "right": 1, "lt": 1, "left": 1,
         "up": 1, "down": 1, "roll": 1, "pu": 0, "pd": 0, "penup": 0, "pendown": 0, "home": 0,
         "goto": 3, "pensize": 1, "detail": 1, "cube": 1, "box": 3, "sphere": 1,
         "cylinder": 2, "cone": 2, "beginfill": 0, "endfill": 0, "fillthick": 1,
         "push": 0, "pop": 0}
WORD_ARG = {"color": 1, "joints": 1}
FUNCS = {
    "sin": lambda a: math.sin(math.radians(a)), "cos": lambda a: math.cos(math.radians(a)),
    "tan": lambda a: math.tan(math.radians(a)), "asin": lambda a: math.degrees(math.asin(a)),
    "acos": lambda a: math.degrees(math.acos(a)), "atan": lambda a: math.degrees(math.atan(a)),
    "sqrt": math.sqrt, "abs": abs, "min": min, "max": max, "int": lambda a: float(int(a)),
    "round": lambda a: float(round(a)), "pow": pow, "exp": math.exp, "log": math.log,
    "rand": lambda a=1.0, b=None: random.uniform(a, b) if b is not None else random.uniform(0, a),
}
CONSTS = {"pi": math.pi, "true": 1.0, "false": 0.0}
PLACE_KW = ("as", "mirror", "scale")


class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0
        self.arity = {}                      # user to/part name -> parameter count
        self._prescan()

    def _prescan(self):
        t = self.t
        for i, tk in enumerate(t):
            if tk[0] == "word" and tk[1] in ("to", "part") and i + 1 < len(t):
                n, j = 0, i + 2
                while j < len(t) and t[j][0] == "word" and t[j][1] not in ("end", "endpart") \
                        and t[j][2] == t[i][2]:
                    n += 1
                    j += 1
                self.arity[t[i + 1][1]] = n

    # -- plumbing
    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("eof", None, 0, False)

    def take(self):
        tk = self.peek()
        self.i += 1
        return tk

    def is_op(self, v):
        tk = self.peek()
        return tk[0] == "op" and tk[1] == v

    def expect_op(self, v):
        tk = self.take()
        if tk[0] != "op" or tk[1] != v:
            raise TurtleError(f"line {tk[2]}: expected '{v}'")

    def word(self):
        tk = self.take()
        if tk[0] != "word":
            raise TurtleError(f"line {tk[2]}: expected a name")
        return tk[1]

    # -- expressions (precedence climbing)
    def expr(self):
        return self._cmp()

    def _cmp(self):
        a = self._add()
        while self.peek()[0] == "op" and self.peek()[1] in ("<", ">", "<=", ">=", "==", "!=", "="):
            op = self.take()[1]
            a = ("bin", "==" if op == "=" else op, a, self._add())
        return a

    def _add(self):
        a = self._mul()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-") and not self.peek()[3]:
            a = ("bin", self.take()[1], a, self._mul())
        return a

    def _mul(self):
        a = self._pow()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/", "%"):
            a = ("bin", self.take()[1], a, self._pow())
        return a

    def _pow(self):
        a = self._unary()
        if self.is_op("^"):
            self.take()
            return ("bin", "^", a, self._pow())
        return a

    def _unary(self):
        if self.is_op("-"):
            self.take()
            return ("neg", self._unary())
        if self.is_op("+"):
            self.take()
            return self._unary()
        return self._atom()

    def _atom(self):
        tk = self.take()
        if tk[0] == "num":
            return ("num", tk[1])
        if tk[0] == "op" and tk[1] == "(":
            e = self.expr()
            self.expect_op(")")
            return e
        if tk[0] == "word":
            if self.is_op("(") and tk[1] in FUNCS:
                self.take()
                args = []
                if not self.is_op(")"):
                    args.append(self.expr())
                    while self.is_op(","):
                        self.take()
                        args.append(self.expr())
                self.expect_op(")")
                return ("call", tk[1], args)
            return ("var", tk[1], tk[2])
        raise TurtleError(f"line {tk[2]}: expected a number or variable")

    # -- statements
    def block(self):
        self.expect_op("[")
        out = []
        while not self.is_op("]"):
            if self.peek()[0] == "eof":
                raise TurtleError("missing ']'")
            out.append(self.stmt())
        self.take()
        return out

    def body(self, *enders):
        out = []
        while True:
            tk = self.peek()
            if tk[0] == "eof":
                raise TurtleError(f"missing '{enders[0]}'")
            if tk[0] == "word" and tk[1] in enders:
                self.take()
                return out
            out.append(self.stmt())

    def program(self):
        out = []
        while self.peek()[0] != "eof":
            out.append(self.stmt())
        return out

    def stmt(self):
        tk = self.take()
        if tk[0] != "word":
            raise TurtleError(f"line {tk[2]}: unexpected '{tk[1]}'")
        w, ln = tk[1], tk[2]
        if w in ARITY:
            return ("cmd", w, [self.expr() for _ in range(ARITY[w])], ln)
        if w in WORD_ARG:
            return ("cmd", w, [self.word() if self.peek()[0] == "word" else self.take()[1]], ln)
        if w == "repeat":
            return ("repeat", self.expr(), self.block(), ln)
        if w == "if":
            cond, yes, no = self.expr(), self.block(), []
            if self.peek()[0] == "word" and self.peek()[1] == "else":
                self.take()
                no = self.block()
            return ("if", cond, yes, no, ln)
        if w == "for":
            var = self.word()
            a, b, step = self.expr(), self.expr(), ("num", 1.0)
            if self.peek()[0] == "word" and self.peek()[1] == "step":
                self.take()
                step = self.expr()
            return ("for", var, a, b, step, self.block(), ln)
        if w in ("make", "let"):
            return ("make", self.word(), self.expr(), ln)
        if w in ("to", "part"):
            name = self.word()
            params = []
            while self.peek()[0] == "word" and self.peek()[2] == ln:
                params.append(self.word())
            body = self.body("end" if w == "to" else "endpart")
            return ("def", w, name, params, body, ln)
        if w == "group":
            return ("group", self.word(), self.body("endgroup"), ln)
        if w == "place":
            name = self.word()
            if name not in self.arity:
                raise TurtleError(f"line {ln}: place: no part named '{name}' (define it first)")
            args = [self.expr() for _ in range(self.arity[name])]
            inst, mirror, scale = None, "", 1.0
            while self.peek()[0] == "word" and self.peek()[1] in PLACE_KW:
                kw = self.take()[1]
                if kw == "as":
                    inst = self.word()
                elif kw == "mirror":
                    mirror += self.word()
                    while self.peek()[0] == "word" and self.peek()[1] in ("l", "f", "u"):
                        mirror += self.take()[1]
                else:
                    scale = self.expr()
            return ("place", name, args, inst, mirror, scale, ln)
        if w in self.arity:
            return ("call", w, [self.expr() for _ in range(self.arity[w])], ln)
        raise TurtleError(f"line {ln}: unknown command '{w}'")


# ---------------------------------------------------------------- geometry helpers
def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _box_pts(f0, f1, w, h):
    """12 triangles of a box spanning f0..f1, lateral +-w/2, vertical +-h/2, in (f,l,u)."""
    x0, x1, y, z = f0, f1, w / 2, h / 2
    P = np.array([[x0, -y, -z], [x1, -y, -z], [x1, y, -z], [x0, y, -z],
                  [x0, -y, z], [x1, -y, z], [x1, y, z], [x0, y, z]], float)
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]
    return np.array([P[[a, b, c]] for q in quads for a, b, c in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))])


def _sphere_pts(r, n):
    n = max(6, n)
    rings = max(4, n // 2)
    tris = []
    for i in range(rings):
        a0, a1 = math.pi * i / rings, math.pi * (i + 1) / rings
        for j in range(n):
            b0, b1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
            p = lambda a, b: (r * math.sin(a) * math.cos(b), r * math.sin(a) * math.sin(b),  # noqa: E731
                              r * math.cos(a))
            p00, p01, p10, p11 = p(a0, b0), p(a0, b1), p(a1, b0), p(a1, b1)
            if i > 0:
                tris.append((p00, p01, p10))
            if i < rings - 1:
                tris.append((p01, p11, p10))
    # local sphere is built about +z; orientation is irrelevant for a sphere
    return _fix_winding(np.array(tris, float), np.zeros(3))


def _cyl_pts(r0, r1, h, n):
    """Cylinder / cone along +f from 0..h (axis f); cross-section in (l,u). r1=0 -> cone."""
    n = max(3, n)
    tris = []
    ang = [2 * math.pi * k / n for k in range(n + 1)]
    ring = lambda r, f: [(f, r * math.cos(a), r * math.sin(a)) for a in ang]  # noqa: E731
    A, B = ring(r0, 0.0), ring(r1, h)
    for k in range(n):
        if r1 > 1e-12:
            tris.append((A[k], B[k], B[k + 1]))
        tris.append((A[k], B[k + 1], A[k + 1]) if r1 > 1e-12 else (A[k], B[0], A[k + 1]))
        tris.append(((0.0, 0.0, 0.0), A[k + 1], A[k]))
        if r1 > 1e-12:
            tris.append(((h, 0.0, 0.0), B[k], B[k + 1]))
    return np.array(tris, float)


def _fix_winding(tris, centre):
    """Make a closed, roughly convex mesh face outward (used for the primitives)."""
    if not len(tris):
        return tris
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    mid = tris.mean(1) - centre
    flip = np.einsum("ij,ij->i", nrm, mid) < 0
    out = tris.copy()
    out[flip] = out[flip][:, [0, 2, 1]]
    return out


# ---------------------------------------------------------------- interpreter
class Chunk:
    __slots__ = ("path", "color", "tris")

    def __init__(self, path, color, tris):
        self.path, self.color, self.tris = path, color, tris


class Turtle:
    def __init__(self):
        self.p = np.zeros(3)
        self.A = np.eye(3)                 # columns: forward, left, up
        self.pen = True
        self.size = 0.5
        self.color = "white"
        self.joints = True
        self.detail = 12
        self.thick = 0.0

    def copy(self):
        t = Turtle()
        t.p, t.A = self.p.copy(), self.A.copy()
        t.pen, t.size, t.color, t.joints, t.detail, t.thick = (
            self.pen, self.size, self.color, self.joints, self.detail, self.thick)
        return t


class Interp:
    def __init__(self, parser, collect=None):
        self.parser = parser
        self.defs = {}
        self.chunks = []
        self.steps = 0
        self.depth = 0
        self.counter = {}
        self.collect = collect

    # -- expression eval
    def ev(self, n, env):
        k = n[0]
        if k == "num":
            return n[1]
        if k == "var":
            name = n[1]
            for scope in reversed(env):
                if name in scope:
                    return scope[name]
            if name in CONSTS:
                return CONSTS[name]
            raise TurtleError(f"line {n[2]}: '{name}' has no value (use make {name} ...)")
        if k == "neg":
            return -self.ev(n[1], env)
        if k == "call":
            return float(FUNCS[n[1]](*[self.ev(a, env) for a in n[2]]))
        op, a, b = n[1], self.ev(n[2], env), self.ev(n[3], env)
        try:
            if op == "+": return a + b
            if op == "-": return a - b
            if op == "*": return a * b
            if op == "/": return a / b
            if op == "%": return math.fmod(a, b)
            if op == "^": return a ** b
        except (ZeroDivisionError, OverflowError, ValueError) as exc:
            raise TurtleError(f"maths error in '{a} {op} {b}': {exc}")
        return float({"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b,
                      "==": abs(a - b) < 1e-9, "!=": abs(a - b) >= 1e-9}[op])

    # -- definitions
    def predefine(self, stmts):
        for s in stmts:
            if s[0] == "def":
                self.defs[s[2]] = s
            elif s[0] in ("group",):
                self.predefine(s[2])

    # -- execution
    def run(self, stmts, env, tu, base, path):
        for s in stmts:
            self.steps += 1
            if self.steps > MAX_STEPS:
                raise TurtleError("program too long (step limit hit - infinite loop?)")
            self.exec(s, env, tu, base, path)

    def exec(self, s, env, tu, base, path):
        k = s[0]
        if k == "cmd":
            vals = [a if isinstance(a, str) else self.ev(a, env) if isinstance(a, tuple) else a
                    for a in s[2]]
            try:
                self.command(s[1], vals, tu, base, path)
            except TurtleError as exc:
                raise TurtleError(f"line {s[3]}: {exc}")
        elif k == "repeat":
            for _ in range(int(round(self.ev(s[1], env)))):
                self.run(s[2], env, tu, base, path)
        elif k == "if":
            self.run(s[2] if self.ev(s[1], env) else s[3], env, tu, base, path)
        elif k == "for":
            a, b, step = self.ev(s[2], env), self.ev(s[3], env), self.ev(s[4], env)
            if step == 0:
                raise TurtleError(f"line {s[-1]}: for: step is 0")
            v = a
            scope = {}
            env2 = env + [scope]
            while (v <= b + 1e-9) if step > 0 else (v >= b - 1e-9):
                scope[s[1]] = v
                self.run(s[5], env2, tu, base, path)
                v += step
        elif k == "make":
            env[-1][s[1]] = self.ev(s[2], env)
        elif k == "def":
            self.defs[s[2]] = s
        elif k == "group":
            self.run(s[2], env, tu, base, path + (s[1],))
        elif k == "call":
            d = self.defs.get(s[1])
            if not d:
                raise TurtleError(f"line {s[3]}: '{s[1]}' is not defined")
            self.depth += 1
            if self.depth > MAX_DEPTH:
                raise TurtleError("recursion too deep")
            scope = dict(zip(d[3], [self.ev(a, env) for a in s[2]]))
            self.run(d[4], [{}, scope], tu, base, path)      # procedures see only their own args
            self.depth -= 1
        elif k == "place":
            self.place(s, env, tu, base, path)

    def place(self, s, env, tu, base, path):
        _, name, args, inst, mirror, scale, ln = s
        d = self.defs.get(name)
        if not d or d[1] != "part":
            raise TurtleError(f"line {ln}: '{name}' is not a part")
        base_name = inst or name
        n = self.counter.get((path, base_name), 0)
        self.counter[(path, base_name)] = n + 1
        iname = base_name if n == 0 else f"{base_name}_{n + 1}"
        F = np.diag([-1.0 if "f" in mirror else 1.0, -1.0 if "l" in mirror else 1.0,
                     -1.0 if "u" in mirror else 1.0])
        k = float(self.ev(scale, env) if isinstance(scale, tuple) else scale)
        R, t = base
        # a mirror reflects the whole placement (position and orientation) in the current
        # part's own frame, so a part placed at +l with `mirror l` lands at -l.
        child = (R @ F @ tu.A * k, R @ (F @ tu.p) + t)
        scope = dict(zip(d[3], [self.ev(a, env) for a in args]))
        child_tu = Turtle()
        child_tu.color, child_tu.size, child_tu.detail, child_tu.joints = (
            tu.color, tu.size, tu.detail, tu.joints)
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise TurtleError("recursion too deep")
        self.run(d[4], [{}, scope], child_tu, child, path + (iname,))
        self.depth -= 1

    # -- commands
    def emit(self, tu, base, path, local_tris):
        """local_tris: (T,3,3) in the turtle's (f,l,u) frame at tu.p."""
        R, t = base
        P = (local_tris @ tu.A.T + tu.p) @ R.T + t
        if np.linalg.det(R) < 0:
            P = P[:, [0, 2, 1]]
        self.chunks.append(Chunk(path, tu.color, P))

    def emit_world(self, tu, base, path, pts_local):
        R, t = base
        P = pts_local @ R.T + t
        if np.linalg.det(R) < 0:
            P = P[:, [0, 2, 1]]
        self.chunks.append(Chunk(path, tu.color, P))

    def command(self, c, v, tu, base, path):
        A = tu.A
        if c in ("fd", "forward", "bk", "back"):
            d = v[0] if c in ("fd", "forward") else -v[0]
            new = tu.p + A[:, 0] * d
            if tu.pen and abs(d) > 1e-12 and tu.size > 0:
                self._tube(tu, base, path, tu.p, new)
            tu.p = new
            if self.fill is not None:
                self.fill.append(tu.p.copy())
        elif c in ("rt", "right", "lt", "left"):
            a = math.radians(v[0] if c in ("lt", "left") else -v[0])
            ca, sa = math.cos(a), math.sin(a)
            f, l = A[:, 0].copy(), A[:, 1].copy()
            A[:, 0], A[:, 1] = f * ca + l * sa, l * ca - f * sa
        elif c in ("up", "down"):
            a = math.radians(v[0] if c == "up" else -v[0])
            ca, sa = math.cos(a), math.sin(a)
            f, u = A[:, 0].copy(), A[:, 2].copy()
            A[:, 0], A[:, 2] = f * ca + u * sa, u * ca - f * sa
        elif c == "roll":
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            l, u = A[:, 1].copy(), A[:, 2].copy()
            A[:, 1], A[:, 2] = l * ca + u * sa, u * ca - l * sa
        elif c in ("pu", "penup"):
            tu.pen = False
        elif c in ("pd", "pendown"):
            tu.pen = True
        elif c == "home":
            tu.p, tu.A = np.zeros(3), np.eye(3)
        elif c == "goto":
            new = np.array(v[:3], float)
            if tu.pen and tu.size > 0 and np.linalg.norm(new - tu.p) > 1e-12:
                self._tube(tu, base, path, tu.p, new)
            tu.p = new
            if self.fill is not None:
                self.fill.append(tu.p.copy())
        elif c == "pensize":
            tu.size = max(0.0, v[0])
        elif c == "detail":
            tu.detail = int(max(3, v[0]))
        elif c == "color":
            tu.color = str(v[0])
        elif c == "joints":
            tu.joints = str(v[0]) not in ("off", "0", "false", "no")
        elif c == "fillthick":
            tu.thick = max(0.0, v[0])
        elif c == "cube":
            h = v[0]
            self.emit(tu, base, path, _box_pts(-h / 2, h / 2, h, h))
        elif c == "box":
            self.emit(tu, base, path, _box_pts(0.0, v[0], v[1], v[2]))
        elif c == "sphere":
            self.emit(tu, base, path, _sphere_pts(v[0], tu.detail))
        elif c in ("cylinder", "cone"):
            r, h = v
            tris = _cyl_pts(r, r if c == "cylinder" else 0.0, h, tu.detail)
            self.emit(tu, base, path, _fix_winding(tris, np.array([h / 2, 0.0, 0.0])))
        elif c == "beginfill":
            self.fill = [tu.p.copy()]
        elif c == "endfill":
            self._endfill(tu, base, path)
        elif c == "push":
            self.stack.append(tu.copy())
        elif c == "pop":
            if not self.stack:
                raise TurtleError("pop with nothing pushed")
            t2 = self.stack.pop()
            tu.p, tu.A = t2.p, t2.A
            tu.pen, tu.size, tu.color, tu.joints, tu.detail, tu.thick = (
                t2.pen, t2.size, t2.color, t2.joints, t2.detail, t2.thick)

    fill = None
    stack = None

    def _tube(self, tu, base, path, a, b):
        axis = b - a
        h = float(np.linalg.norm(axis))
        z = axis / h
        helper = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
        x = _unit(np.cross(helper, z))
        y = np.cross(z, x)
        M = np.stack([z, x, y], axis=1)                    # local (f,l,u) -> world, f along the tube
        tris = _fix_winding(_cyl_pts(tu.size, tu.size, h, tu.detail), np.array([h / 2, 0.0, 0.0]))
        world = tris @ M.T + a
        if tu.joints:
            sph = _sphere_pts(tu.size, tu.detail)
            world = np.concatenate([world, sph + a, sph + b])
        self.emit_world(tu, base, path, world)

    def _endfill(self, tu, base, path):
        pts = np.array(self.fill or [], float)
        self.fill = None
        if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
            pts = pts[:-1]
        if len(pts) < 3:
            raise TurtleError("endfill: need at least 3 points")
        # Newell normal
        N = np.zeros(3)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            N += np.cross(a, b)
        if np.linalg.norm(N) < 1e-12:
            raise TurtleError("endfill: points are in a straight line")
        n = _unit(N)
        if np.dot(n, tu.A[:, 2]) < 0:
            n = -n
            pts = pts[::-1]
        c = pts.mean(0)
        t = tu.thick
        tris = []
        top = pts + n * t
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            tris.append((c + n * t, top[i], top[j]))            # top face (CCW about n)
            if t > 0:
                tris.append((c, pts[j], pts[i]))                # bottom face
                tris.append((pts[i], pts[j], top[j]))           # side
                tris.append((pts[i], top[j], top[i]))
            else:
                tris.append((c, pts[j], pts[i]))                # flat: back face too
        self.emit_world(tu, base, path, np.array(tris, float))


# ---------------------------------------------------------------- public API
def interpret(source, base_dir=None):
    """Run a program; returns the list of Chunk (path tuple, colour name, (T,3,3) triangles)."""
    toks = _splice_uses(tokenize(source), base_dir)
    prog = Parser(toks)
    stmts = prog.program()
    it = Interp(prog)
    it.stack = []
    it.predefine(stmts)
    it.run(stmts, [{}], Turtle(), (np.eye(3), np.zeros(3)), ())
    return it.chunks


def merged(chunks):
    """Merge chunks by (instance path, colour) -> [(path, colour, tris)] in first-seen order."""
    order, acc = [], {}
    for c in chunks:
        k = (c.path, c.color)
        if k not in acc:
            acc[k] = []
            order.append(k)
        acc[k].append(c.tris)
    return [(p, col, np.concatenate(acc[(p, col)])) for p, col in order]


def facets(source, base_dir=None):
    """[(a,b,c,normal)] for the whole program - ready for mesh_io.write_stl / write_obj."""
    out = []
    for _p, _c, tris in merged(interpret(source, base_dir)):
        out += _tri_facets(tris)
    return out


def _tri_facets(tris):
    out = []
    for a, b, c in tris:
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln > 1e-14:
            out.append((a, b, c, n / ln))
    return out


def _entry_name(path, color, multi, taken):
    base = (path[-1] if path else "turtle")
    if multi:
        base += "_" + color
    name, i = base, 2
    while name in taken:
        name, i = f"{base}_{i}", i + 1
    return name


def run(source, session, base_dir=None, name_prefix=""):
    """Interpret `source` and add its meshes to `session` as mesh3d entries.

    `session` is a commands3d.Session (or anything with .entries, .mesh_dir, ._unique, ._rebuild).
    Returns a one-line summary."""
    import mesh_io
    Entry = getattr(session, 'Entry', None)
    if Entry is None:
        import viewer3d as V
        Entry = V.Entry
    parts = merged(interpret(source, base_dir))
    if not parts:
        return "turtle drew nothing"
    os.makedirs(session.mesh_dir, exist_ok=True)
    by_path = {}
    for p, col, _t in parts:
        by_path.setdefault(p, set()).add(col)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    taken = {e.name for e in session.entries}
    made, tris_n = 0, 0
    for idx, (path, col, tris) in enumerate(parts):
        fac = _tri_facets(tris)
        if not fac:
            continue
        name = name_prefix + _entry_name(path, col, len(by_path[path]) > 1, taken)
        taken.add(name)
        fn = f"turtle_{name}_{stamp}_{idx}.stl"
        mesh_io.write_stl(os.path.join(session.mesh_dir, fn), [(name, fac)], binary=True, name=name)
        e = Entry("mesh3d", name, col if col != "white" else "white", "teal", [])
        e.mesh_src = fn
        e.group = "/".join(path)
        session._rebuild(e)
        session.entries.append(e)
        made += 1
        tris_n += len(fac)
    return f"turtle built {made} mesh object(s), {tris_n} triangles"


def run_file(path, session):
    with open(path, "r", encoding="utf-8") as fh:
        return run(fh.read(), session, base_dir=os.path.dirname(os.path.abspath(path)))


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print("usage: turtle3d.py program.logo out.stl|out.obj|out.csv")
        return 2
    src, out = argv[0], argv[1]
    ext = os.path.splitext(out)[1].lower()
    if ext == ".csv":
        from commands3d import Session
        s = Session()
        print(run_file(src, s))
        print(s.save(out))
        return 0
    import mesh_io
    with open(src, "r", encoding="utf-8") as fh:
        fac = facets(fh.read(), os.path.dirname(os.path.abspath(src)))
    groups = [("turtle", fac)]
    n = mesh_io.write_obj(out, groups) if ext == ".obj" else mesh_io.write_stl(out, groups)
    print(f"wrote {n} facets -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
