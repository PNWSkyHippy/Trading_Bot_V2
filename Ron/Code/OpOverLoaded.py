"""
OpOverloaded - A Universal, Inheritable Python Base Class for Operator Overloading.

Any subclass inheriting from `OpOverloaded` instantly has every Python operator
overload defined and equipped with comprehensive edge checking and multi-type resilience.

Supports:
- Primitive scalars (int, float, complex, bool)
- Sequences (list, tuple, str)
- Sets (set, frozenset)
- Mappings (dict)
- Custom classes with get_value() / .value or custom __add__, __sub__, etc.
- Seamless inheritance with optional wrapped result via `wrap=True`
"""
from class3d import Point3d, Line3d, Square3d, Cube3d
import math
import operator
from typing import Any
import numpy as np

class OpOverloaded:
    """Universal operator overloaded base class."""

    value: Any = 0

    def __init__(self, value: Any = 0):
        self.value = value

    def get_value(self) -> Any:
        return self.value

    def set_value(self, input: Any) -> None:
        self.value = input

    # -------------------------------------------------------------------------
    # Core Extraction & Wrapping Helpers
    # -------------------------------------------------------------------------
    def _extract_value(self, obj: Any) -> Any:
        """
        Extract the underlying payload value from `obj` if it wraps one,
        supporting any subclass, duck-typed wrapper, or raw value.
        """
        if hasattr(obj, "get_value") and callable(obj.get_value):
            return obj.get_value()
        if hasattr(obj, "get_xyz") and callable(obj, get_xyz):
            return obj,get_xyz()
        if hasattr(obj, "value"):
            return obj.value
        return obj

    def _wrap(self, res: Any, wrap: bool = False) -> Any:
        """Return either the raw computed value or wrapped in the caller's class."""
        if res is NotImplemented:
            return NotImplemented
        return self.__class__(res) if wrap else res

    # -------------------------------------------------------------------------
    # Rich Comparisons (<, <=, ==, !=, >=, >)
    # -------------------------------------------------------------------------
    def eq(self, other: Any) -> bool:
        """eq(self, other) is equivalent to self == other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return a == b
        except Exception:
            return False

    def __eq__(self, other: Any) -> bool:
        return self.eq(other)

    def ne(self, other: Any) -> bool:
        """ne(self, other) is equivalent to self != other"""
        return not self.eq(other)

    def __ne__(self, other: Any) -> bool:
        return self.ne(other)

    def lt(self, other: Any) -> bool:
        """lt(self, other) is equivalent to self < other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return (a.get_x() < b.get_x()) and (a.get_y() < b.get_y()) and (a.get_z() < b.get_z())
        else:
            try:
                return a < b
            except TypeError:
                return NotImplemented

    def __lt__(self, other: Any) -> bool:
        return self.lt(other)

    def le(self, other: Any) -> bool:
        """le(self, other) is equivalent to self <= other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return (a.get_x() <= b.get_x()) and (a.get_y() <= b.get_y()) and (a.get_z() <= b.get_z())
        else:
            try:
                return a <= b
            except TypeError:
                return NotImplemented

    def __le__(self, other: Any) -> bool:
        return self.le(other)

    def gt(self, other: Any) -> bool:
        """gt(self, other) is equivalent to self > other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return (a.get_x() > b.get_x()) and (a.get_y() > b.get_y()) and (a.get_z() > b.get_z())
        else:
            try:
                return a > b
            except TypeError:
                return NotImplemented
 

    def __gt__(self, other: Any) -> bool:
        return self.gt(other)

    def ge(self, other: Any) -> bool:
        """ge(self, other) is equivalent to self >= other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return (a.get_x() >= b.get_x()) and (a.get_y() >= b.get_y()) and (a.get_z() >= b.get_z())
        else:
            try:
                return a >= b
            except TypeError:
                return NotImplemented

    def __ge__(self, other: Any) -> bool:
        return self.ge(other)

    # -------------------------------------------------------------------------
    # Identity & Truth
    # -------------------------------------------------------------------------
    def is_(self, other: Any) -> bool:
        """is_(self, other) is equivalent to self is other"""
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return (self.get_x() is other.get_x()) and (self.get_y() is other.get_y()) and (self.get_z() is  other.get_z())
        else:
            return self._extract_value(self) is self._extract_value(other)

    def is_not(self, other: Any) -> bool:
        """is_not(self, other) is equivalent to self is not other"""
        return not self.is_(other)

    def is_none(self) -> bool:
        """is_none(self) is equivalent to self is None"""
        return self._extract_value(self) is None

    def is_not_none(self) -> bool:
        """is_not_none(self) is equivalent to self is not None"""
        return self._extract_value(self) is not None

    def truth(self) -> bool:
        """truth(self) is equivalent to bool(self)"""
        return bool(self._extract_value(self))

    def __bool__(self) -> bool:
        return self.truth()

    def not_(self, other: Any = None) -> bool:
        """not_(self, other) checks truth if other is None, else not (self == other)"""
        if other is None:
            return not self.truth()
        return not self.eq(other)

    def __not__(self, other: Any = None) -> bool:
        return self.not_(other)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Addition (+)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_add(cls, a: Any, b: Any) -> Any:
        if a is None:
            return b
        if b is None:
            return a
        # 1. Direct Python addition
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            return ((a.get_x() + b.get_x()) ,(a.get_y() + b.get_y()) , (a.get_z() + b.get_z()))
        else:
            try:
                return a + b
            except TypeError:
                pass

        # 2. Dict + Dict (recursive merge for dict of lists/numbers)
        if isinstance(a, dict) and isinstance(b, dict):
            merged = dict(a)
            for k, v in b.items():
                merged[k] = cls._combine_add(merged[k], v) if k in merged else v
            return merged

        # 3. List combinations
        if isinstance(a, list):
            if isinstance(b, (tuple, set, frozenset)):
                return a + list(b)
            return a + [b]
        if isinstance(b, list):
            if isinstance(a, (tuple, set, frozenset)):
                return list(a) + b
            return [a] + b

        # 4. Set combinations
        if isinstance(a, (set, frozenset)):
            if isinstance(b, (set, frozenset)):
                return a | b
            if isinstance(b, (list, tuple)):
                return a | set(b)
            try:
                return a | {b}
            except TypeError:
                return a | {tuple(b) if isinstance(b, (list, set)) else id(b)}

        # 5. Tuple combinations
        if isinstance(a, tuple):
            if isinstance(b, (list, set, frozenset)):
                return a + tuple(b)
            return a + (b,)

        return NotImplemented

    def add(self, other: Any, wrap: bool = False) -> Any:
        """add(self, other) is equivalent to self + other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_add(a, b)
        if res is NotImplemented:
            res = self._combine_add(b, a)
        return self._wrap(res, wrap)

    def __add__(self, other: Any) -> Any:
        return self.add(other)

    def __radd__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_add(b, a)
        if res is NotImplemented:
            res = self._combine_add(a, b)
        return res

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Subtraction (-)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_sub(cls, a: Any, b: Any) -> Any:
        try:
            return a - b
        except TypeError:
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() - b.get_x()), (a.get_y() - b.get_y()) ,(a.get_z() - b.get_z()))
        if isinstance(a, (set, frozenset)):
            return a - set(b) if isinstance(b, (list, tuple)) else a - {b}
        if isinstance(a, list):
            if isinstance(b, (list, tuple, set)):
                return [x for x in a if x not in b]
            return [x for x in a if x != b]
        if isinstance(a, dict):
            keys = set(b.keys()) if isinstance(b, dict) else (set(b) if isinstance(b, (list, tuple, set)) else {b})
            return {k: v for k, v in a.items() if k not in keys}
        if isinstance(a, str):
            return a.replace(str(b), "")
        return NotImplemented

    def sub(self, other: Any, wrap: bool = False) -> Any:
        """sub(self, other) is equivalent to self - other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_sub(a, b)
        return self._wrap(res, wrap)

    def __sub__(self, other: Any) -> Any:
        return self.sub(other)

    def __rsub__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_sub(b, a)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Multiplication (*)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_mul(cls, a: Any, b: Any) -> Any:
        try:
            return a * b
        except TypeError:
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() * b.get_x()), (a.get_y() * b.get_y()) ,(a.get_z() * b.get_z()))
        if isinstance(a, dict):
            if isinstance(b, dict):
                return {k: cls._combine_mul(a[k], b[k]) for k in a.keys() & b.keys()}
            return {k: cls._combine_mul(v, b) for k, v in a.items()}
        if isinstance(b, dict):
            return {k: cls._combine_mul(a, v) for k, v in b.items()}
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) == len(b):
                return type(a)(cls._combine_mul(x, y) for x, y in zip(a, b))
        return NotImplemented

    def mul(self, other: Any, wrap: bool = False) -> Any:
        """mul(self, other) is equivalent to self * other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_mul(a, b)
        return self._wrap(res, wrap)

    def __mul__(self, other: Any) -> Any:
        return self.mul(other)

    def __rmul__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_mul(b, a)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Matrix Multiplication (@)
    # -------------------------------------------------------------------------
    def matmul(self, other: Any, wrap: bool = False) -> Any:
        """matmul(self, other) is equivalent to self @ other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a @ b, wrap)
        except (TypeError, ValueError):
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() @ b.get_x()), (a.get_y() @ b.get_y()) ,(a.get_z() @ b.get_z()))
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            try:
                return self._wrap(sum(x * y for x, y in zip(a, b)), wrap)
            except Exception:
                pass
        return NotImplemented

    def __matmul__(self, other: Any) -> Any:
        return self.matmul(other)

    def __rmatmul__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self.matmul(a, wrap=False)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: True Division (/)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_truediv(cls, a: Any, b: Any) -> Any:
        if b == 0:
            return 0.0
        try:
            return a / b
        except (TypeError, ZeroDivisionError):
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() / b.get_x()), (a.get_y() / b.get_y()) ,(a.get_z() / b.get_z()))
        if isinstance(a, dict):
            if isinstance(b, dict):
                return {k: cls._combine_truediv(a[k], b[k]) for k in a.keys() & b.keys()}
            return {k: cls._combine_truediv(v, b) for k, v in a.items()}
        if isinstance(a, (list, tuple)):
            if isinstance(b, (list, tuple)) and len(a) == len(b):
                return type(a)(cls._combine_truediv(x, y) for x, y in zip(a, b))
            return type(a)(cls._combine_truediv(x, b) for x in a)
        return NotImplemented

    def truediv(self, other: Any, wrap: bool = False) -> Any:
        """truediv(self, other) is equivalent to self / other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_truediv(a, b)
        return self._wrap(res, wrap)

    def __truediv__(self, other: Any) -> Any:
        return self.truediv(other)

    def __rtruediv__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_truediv(b, a)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Floor Division (//)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_floordiv(cls, a: Any, b: Any) -> Any:
        if b == 0:
            return 0
        try:
            return a // b
        except (TypeError, ZeroDivisionError):
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() // b.get_x()), (a.get_y() // b.get_y()) ,(a.get_z() // b.get_z()))

        if isinstance(a, dict):
            if isinstance(b, dict):
                return {k: cls._combine_floordiv(a[k], b[k]) for k in a.keys() & b.keys()}
            return {k: cls._combine_floordiv(v, b) for k, v in a.items()}
        if isinstance(a, (list, tuple)):
            return type(a)(cls._combine_floordiv(x, b) for x in a)
        return NotImplemented

    def floordiv(self, other: Any, wrap: bool = False) -> Any:
        """floordiv(self, other) is equivalent to self // other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_floordiv(a, b)
        return self._wrap(res, wrap)

    def __floordiv__(self, other: Any) -> Any:
        return self.floordiv(other)

    def __rfloordiv__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_floordiv(b, a)

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Modulo (%) & divmod
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_mod(cls, a: Any, b: Any) -> Any:
        if b == 0:
            return 0
        try:
            return a % b
        except (TypeError, ZeroDivisionError):
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type((a.get_x() % b.get_x()), (a.get_y() % b.get_y()) ,(a.get_z() % b.get_z()))
        if isinstance(a, (list, tuple)):
            return type(a)(cls._combine_mod(x, b) for x in a)
        if isinstance(a, dict):
            return {k: cls._combine_mod(v, b) for k, v in a.items()}
        return NotImplemented

    def mod(self, other: Any, wrap: bool = False) -> Any:
        """mod(self, other) is equivalent to self % other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        res = self._combine_mod(a, b)
        return self._wrap(res, wrap)

    def __mod__(self, other: Any) -> Any:
        return self.mod(other)

    def __rmod__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_mod(b, a)

    def divmod(self, other: Any) -> tuple:
        """divmod(self, other) is equivalent to (self // other, self % other)"""
        return (self.floordiv(other), self.mod(other))

    def __divmod__(self, other: Any) -> tuple:
        return self.divmod(other)

    def __rdivmod__(self, other: Any) -> tuple:
        b = self._extract_value(other)
        a = self._extract_value(self)
        return (self._combine_floordiv(b, a), self._combine_mod(b, a))

    # -------------------------------------------------------------------------
    # Binary Arithmetic: Power (**)
    # -------------------------------------------------------------------------
    @classmethod
    def _combine_pow(cls, a: Any, b: Any, mod: Any = None) -> Any:
        try:
            return pow(a, b, mod) if mod is not None else a ** b
        except (TypeError, ValueError):
            pass
        if hasattr(a, "get_xyz") and callable(a, get_xyz):
            ret_type = tpye(a)
            return ret_type(pow(a.get_x(), b.get_x(),mod), pow(a.get_y(),b.get_y(),mod) ,pow(a.get_z() , b.get_z(),mod))

        if isinstance(a, (list, tuple)):
            return type(a)(cls._combine_pow(x, b) for x in a)
        if isinstance(a, dict):
            return {k: cls._combine_pow(v, b) for k, v in a.items()}
        return NotImplemented

    def pow(self, other: Any, modulo: Any = None, wrap: bool = False) -> Any:
        """pow(self, other, modulo=None) is equivalent to self ** other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        m = self._extract_value(modulo) if modulo is not None else None
        res = self._combine_pow(a, b, m)
        return self._wrap(res, wrap)

    def __pow__(self, other: Any, modulo: Any = None) -> Any:
        return self.pow(other, modulo)

    def __rpow__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        return self._combine_pow(b, a)

    # -------------------------------------------------------------------------
    # Bitwise & Shifts (<<, >>, &, ^, |)
    # -------------------------------------------------------------------------
    def lshift(self, other: Any, wrap: bool = False) -> Any:
        """lshift(self, other) is equivalent to self << other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a << b, wrap)
        except TypeError:
            pass
        if isinstance(a, (list, tuple, str)):
            shift = int(b) % len(a) if len(a) else 0
            return self._wrap(a[shift:] + a[:shift], wrap)
        return NotImplemented

    def lfshift(self, other: Any, wrap: bool = False) -> Any:
        return self.lshift(other, wrap)

    def __lshift__(self, other: Any) -> Any:
        return self.lshift(other)

    def __lfshift__(self, other: Any) -> Any:
        return self.lshift(other)

    def __rlshift__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return b << a
        except TypeError:
            return NotImplemented

    def rshift(self, other: Any, wrap: bool = False) -> Any:
        """rshift(self, other) is equivalent to self >> other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a >> b, wrap)
        except TypeError:
            pass
        if isinstance(a, (list, tuple, str)):
            shift = int(b) % len(a) if len(a) else 0
            return self._wrap(a[-shift:] + a[:-shift], wrap)
        return NotImplemented

    def __rshift__(self, other: Any) -> Any:
        return self.rshift(other)

    def __rrshift__(self, other: Any) -> Any:
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return b >> a
        except TypeError:
            return NotImplemented

    def and_(self, other: Any, wrap: bool = False) -> Any:
        """and_(self, other) is equivalent to self & other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a & b, wrap)
        except TypeError:
            pass
        if isinstance(a, (set, frozenset)) or isinstance(b, (set, frozenset)):
            return self._wrap(set(a) & set(b), wrap)
        if isinstance(a, dict) and isinstance(b, dict):
            return self._wrap({k: a[k] for k in a.keys() & b.keys()}, wrap)
        return self._wrap(a and b, wrap)

    def __and__(self, other: Any) -> Any:
        return self.and_(other)

    def __rand__(self, other: Any) -> Any:
        return self.and_(other)

    def xor(self, other: Any, wrap: bool = False) -> Any:
        """xor(self, other) is equivalent to self ^ other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a ^ b, wrap)
        except TypeError:
            pass
        if isinstance(a, (set, frozenset)) or isinstance(b, (set, frozenset)):
            return self._wrap(set(a) ^ set(b), wrap)
        if isinstance(a, dict) and isinstance(b, dict):
            sym_keys = a.keys() ^ b.keys()
            return self._wrap({k: a[k] if k in a else b[k] for k in sym_keys}, wrap)
        return self._wrap(bool(a) ^ bool(b), wrap)

    def __xor__(self, other: Any) -> Any:
        return self.xor(other)

    def __rxor__(self, other: Any) -> Any:
        return self.xor(other)

    def or_(self, other: Any, wrap: bool = False) -> Any:
        """or_(self, other) is equivalent to self | other"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        try:
            return self._wrap(a | b, wrap)
        except TypeError:
            pass
        if isinstance(a, (set, frozenset)) or isinstance(b, (set, frozenset)):
            return self._wrap(set(a) | set(b), wrap)
        if isinstance(a, dict) and isinstance(b, dict):
            return self._wrap({**a, **b}, wrap)
        return self._wrap(a or b, wrap)

    def __or__(self, other: Any) -> Any:
        return self.or_(other)

    def __ror__(self, other: Any) -> Any:
        return self.or_(other)

    # -------------------------------------------------------------------------
    # In-Place Operators (+=, -=, *=, /=, etc.)
    # -------------------------------------------------------------------------
    def _inplace_op(self, method_name: str, other: Any) -> Any:
        func = getattr(self, method_name)
        res = func(other, wrap=False)
        if res is NotImplemented:
            return NotImplemented
        self.set_value(self._extract_value(res))
        return self

    def iadd(self, other: Any) -> Any:
        return self._inplace_op("add", other)

    def __iadd__(self, other: Any) -> Any:
        return self.iadd(other)

    def isub(self, other: Any) -> Any:
        return self._inplace_op("sub", other)

    def __isub__(self, other: Any) -> Any:
        return self.isub(other)

    def imul(self, other: Any) -> Any:
        return self._inplace_op("mul", other)

    def __imul__(self, other: Any) -> Any:
        return self.imul(other)

    def imatmul(self, other: Any) -> Any:
        return self._inplace_op("matmul", other)

    def __imatmul__(self, other: Any) -> Any:
        return self.imatmul(other)

    def itruediv(self, other: Any) -> Any:
        return self._inplace_op("truediv", other)

    def __itruediv__(self, other: Any) -> Any:
        return self.itruediv(other)

    def ifloordiv(self, other: Any) -> Any:
        return self._inplace_op("floordiv", other)

    def __ifloordiv__(self, other: Any) -> Any:
        return self.ifloordiv(other)

    def imod(self, other: Any) -> Any:
        return self._inplace_op("mod", other)

    def __imod__(self, other: Any) -> Any:
        return self.imod(other)

    def ipow(self, other: Any, modulo: Any = None) -> Any:
        res = self.pow(other, modulo, wrap=False)
        if res is NotImplemented:
            return NotImplemented
        self.set_value(self._extract_value(res))
        return self

    def __ipow__(self, other: Any) -> Any:
        return self.ipow(other)

    def ilshift(self, other: Any) -> Any:
        return self._inplace_op("lshift", other)

    def __ilshift__(self, other: Any) -> Any:
        return self.ilshift(other)

    def irshift(self, other: Any) -> Any:
        return self._inplace_op("rshift", other)

    def __irshift__(self, other: Any) -> Any:
        return self.irshift(other)

    def iand(self, other: Any) -> Any:
        return self._inplace_op("and_", other)

    def __iand__(self, other: Any) -> Any:
        return self.iand(other)

    def ixor(self, other: Any) -> Any:
        return self._inplace_op("xor", other)

    def __ixor__(self, other: Any) -> Any:
        return self.ixor(other)

    def ior(self, other: Any) -> Any:
        return self._inplace_op("or_", other)

    def __ior__(self, other: Any) -> Any:
        return self.ior(other)

    # -------------------------------------------------------------------------
    # Unary Operators (+, -, abs, ~, math functions)
    # -------------------------------------------------------------------------
    def neg(self) -> Any:
        """neg(self) is equivalent to -self"""
        a = self._extract_value(self)
        try:
            return -a
        except TypeError:
            if hasattr(self, "get_xyz") and callable(self, get_xyz):
                ret_type = tpye(self)
                return ret_type(-a.get_x(), -a.get_y() ,a.get_z() )
            if isinstance(a, (list, tuple)):
                return type(a)(-x for x in a)
            if isinstance(a, dict):
                return {k: -v for k, v in a.items()}
            return NotImplemented

    def __neg__(self) -> Any:
        return self.neg()

    def pos(self) -> Any:
        """pos(self) is equivalent to +self"""
        a = self._extract_value(self)
        try:
            return +a
        except TypeError:
            return a

    def __pos__(self) -> Any:
        return self.pos()

    def abs(self) -> Any:
        """abs(self) is equivalent to abs(self)"""
        a = self._extract_value(self)
        try:
            return abs(a)
        except TypeError:
            if hasattr(self, "get_xyz") and callable(self, get_xyz):
                ret_type = tpye(self)
                return ret_type(abs(a.get_x()) , abs(a.get_y()), abs(a.get_z()))

            if isinstance(a, (list, tuple)):
                if all(isinstance(x, (int, float)) for x in a):
                    return math.hypot(*a)
                return type(a)(abs(x) for x in a)
            if isinstance(a, dict):
                return {k: abs(v) for k, v in a.items()}
            return NotImplemented

    def __abs__(self) -> Any:
        return self.abs()

    def invert(self) -> Any:
        """invert(self) is equivalent to ~self"""
        a = self._extract_value(self)
        try:
            return ~a
        except TypeError:
            if hasattr(self, "get_xyz") and callable(self, get_xyz):
                ret_type = tpye(self)
                return ret_type(~a.get_x(), ~a.get_y() ,~a.get_z())

            if isinstance(a, bool):
                return not a
            if isinstance(a, (list, tuple, str)):
                return a[::-1]
            return NotImplemented

    def inv(self) -> Any:
        return self.invert()

    def __invert__(self) -> Any:
        return self.invert()

    def __inv__(self) -> Any:
        return self.invert()

    def __round__(self, n: int = 0) -> Any:
        return round(self._extract_value(self), n)

    def __trunc__(self) -> Any:
        return math.trunc(self._extract_value(self))

    def __floor__(self) -> Any:
        return math.floor(self._extract_value(self))

    def __ceil__(self) -> Any:
        return math.ceil(self._extract_value(self))

    # -------------------------------------------------------------------------
    # Conversions & Formatting
    # -------------------------------------------------------------------------
    def __int__(self) -> int:
        return int(self._extract_value(self))

    def __float__(self) -> float:
        return float(self._extract_value(self))

    def __complex__(self) -> complex:
        return complex(self._extract_value(self))

    def __str__(self) -> str:
        return str(self._extract_value(self))

    def __repr__(self) -> str:
        return f"{self._extract_value(self)}"

    def __format__(self, spec: str) -> str:
        return format(self._extract_value(self), spec)

    def __hash__(self) -> int:
        try:
            return hash(self._extract_value(self))
        except TypeError:
            return id(self)

    # -------------------------------------------------------------------------
    # Container & Sequence Operations
    # -------------------------------------------------------------------------
    def __len__(self) -> int:
        a = self._extract_value(self)
        try:
            return len(a)
        except TypeError:
            return 1

    def getitem(self, key: Any) -> Any:
        """getitem(self, key) is equivalent to self[key]"""
        return self._extract_value(self)[self._extract_value(key)]

    def __getitem__(self, key: Any) -> Any:
        return self.getitem(key)

    def setitem(self, key: Any, value: Any) -> None:
        """setitem(self, key, value) is equivalent to self[key] = value"""
        self._extract_value(self)[self._extract_value(key)] = self._extract_value(value)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.setitem(key, value)

    def delitem(self, key: Any) -> None:
        """delitem(self, key) is equivalent to del self[key]"""
        del self._extract_value(self)[self._extract_value(key)]

    def __delitem__(self, key: Any) -> None:
        self.delitem(key)

    def contains(self, other: Any) -> bool:
        """contains(self, other) is equivalent to other in self"""
        return self._extract_value(other) in self._extract_value(self)

    def __contains__(self, other: Any) -> bool:
        return self.contains(other)

    def __iter__(self) -> Any:
        a = self._extract_value(self)
        try:
            return iter(a)
        except TypeError:
            return iter([a])

    def __reversed__(self) -> Any:
        return reversed(self._extract_value(self))

    def index(self, other: Any) -> Any:
        """index(self, other) is equivalent to self[other] or self.index(other)"""
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "index"):
            return a.index(b)
        return operator.index(a)

    def __index__(self) -> int:
        return operator.index(self._extract_value(self))

    def concat(self, other: Any) -> Any:
        return self.add(other)

    def comcat(self, other: Any) -> Any:
        return self.add(other)

    def __concat__(self, other: Any) -> Any:
        return self.add(other)

    def __comcat__(self, other: Any) -> Any:
        return self.add(other)

    def countOf(self, other: Any) -> int:
        a = self._extract_value(self)
        b = self._extract_value(other)
        if hasattr(a, "count"):
            return a.count(b)
        try:
            return sum(1 for x in a if x == b)
        except TypeError:
            return 1 if a == b else 0

    def __countOf__(self, other: Any) -> int:
        return self.countOf(other)

    def indexOf(self, other: Any) -> Any:
        return self.index(other)

    def __indexOf__(self, other: Any) -> Any:
        return self.indexOf(other)

    # -------------------------------------------------------------------------
    # Callable & Functional Operations
    # -------------------------------------------------------------------------
    def call(self, *args: Any, **kwargs: Any) -> Any:
        """call(self, *args, **kwargs) is equivalent to self(*args, **kwargs)"""
        a = self._extract_value(self)
        if callable(a):
            return a(*args, **kwargs)
        return a

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.call(*args, **kwargs)

    def attrgetter(self, attr: str) -> Any:
        return getattr(self._extract_value(self), attr)

    def __attrgetter__(self, attr: str) -> Any:
        return self.attrgetter(attr)

    def itemgetter(self, item: Any) -> Any:
        return self.getitem(item)

    def __itemgetter__(self, item: Any) -> Any:
        return self.itemgetter(item)

    def methodcaller(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return getattr(self._extract_value(self), method)(*args, **kwargs)

    def __methodcaller__(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return self.methodcaller(method, *args, **kwargs)




def main():
    print("=== Running Base OpOverloaded Tests ===")
    a = OpOverloaded(13)
    b = OpOverloaded(13)
    c = a
    print("a = 13, b = 13")
    print(f"a < b) = {a < b}")
    print(f"a <= b) = {a <= b}")
    print(f"a == b) = {a == b}")
    print(f"a != b = {a != b}")
    print(f"a is b = {a is b}")
    print(f"after c = a, c is a = {c is a}")
    a ^= b
    print(f"a ^= b = {a}")
    a.set_value(13)
    b **= 4
    print(f"b **= 4 = {b}")
    b.set_value(13)
    b **= a
    print(f"b **= a = {b}")
    b.set_value(13)
    print(f"a > b = {a > b}")
    print(f"a >= b = {a >= b}")
    c = b + 5.02
    d = a + b
    print(f"c = b + 5 = {c}")
    print(f"d = a + b = {d}")
    print(f"b + a = {b + a}")
    print(f"b - a = {b - a}")
    print(f"a // b = {a // b}")
    print(f"b // a = {b // a}")
    print(f"b % a = {b % a}")
    print(f"a % b = {a % b}")
    print(f"a ** b = {a**b}")
    print(f"a ** 3 = {a**3}")
    print(f"a / b = {a / b}")
    print(f"b / a = {b / a}")

    print(f"b * a = {b * a}")
    print(f"a * b = {a * b}")
    a += b
    print(f"a += b = {a}")
    b -= a
    print(f"b -= a = {b}")

    print("\n=== Multi-Type & Complex Data Structure Tests ===")
    # 1. List of custom classes + another class instance
    class CustomItem:
        def __init__(self, tag):
            self.tag = tag

        def __repr__(self):
            return f"Item({self.tag})"

    items = OpOverloaded([CustomItem("A"), CustomItem("B")])
    combined_items = items + CustomItem("C")
    print(f"List of classes + Item: {combined_items}")

    # 2. Sets and element insertion
    s = OpOverloaded({1, 2, 3})
    print(f"Set + Set: {s + {4, 5}}")
    print(f"Set + scalar: {s + 6}")

    # 3. Dict of lists recursive merge
    d1 = OpOverloaded({"tags": ["python", "oop"], "score": 90})
    d2 = {"tags": ["beginner", "advanced"], "score": 10, "author": "Ron"}
    print(f"Dict of lists merge: {d1 + d2}")

  


if __name__ == "__main__":
    main()
