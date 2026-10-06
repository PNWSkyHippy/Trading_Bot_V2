class OpOverloaded:
    value = 0

    def __init__(self, input):
        self.value = input

    def get_value(self):
        return self.value

    def set_value(self, input):
        self.value = input

    def lt(self, a, b):
        # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  < b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() < b

        # Case 3: We don't know how to handle this type
        return NotImplemented


    def le(self, a, b):
     # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  <=  b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() <= b

        # Case 3: We don't know how to handle this type
        return NotImplemented


    def eq(self, a, b):
     # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  == b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() == b

        # Case 3: We don't know how to handle this type
        return NotImplemented


    def ne(self, a, b):
     # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  != b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() != b

        # Case 3: We don't know how to handle this type
        return NotImplemented


    def ge(self, a, b):
     # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  >= b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() >= b

        # Case 3: We don't know how to handle this type
        return NotImplemented

   

    def gt(self, a, b):
     # Case 1: 'other' is another MyClass object
        if isinstance(b, OpOverloaded):
            return a.get_value()  >b.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(b, (int), float):
            return a.get_value() <> b

        # Case 3: We don't know how to handle this type
        return NotImplemented

        """gt(a, b) is equivalent to a > b,"""
        return a.value > b

    def __lt__(self, other):
        """__lt__(self, other) is equivalent to self < other,"""
        return self.lt(self, other)

    def __le__(self, other):
        """__le__(self, other) is equivalent to self <= other,"""
        return self.le(self, other)

    def __eq__(self, other):
        """__eq__(self, other) is equivalent to self == other,"""
        return self.eq(self, other)

    def __ne__(self, other):
        """__ne__(self, other) is equivalent to self != other,"""
        return self.ne(self, other)

    def __ge__(self, other):
        """__ge__(self, other) is equivalent to self >= other,"""
        return self.ge(self, other)

    def __gt__(self, other):
        """__gt__(self, other) is equivalent to self > other,"""
        return self.gt(self, other)

    def not_(self, other):
     # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return  not self.eq(self.get_value(), other.get_value())
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return not self.eq(self.get_value() < other)

        # Case 3: We don't know how to handle this type
        return NotImplemented



    def __not__(self, other):
        """__not__(self, other) is equivalent to not self == other,"""
        return self.not_(other)

    def truth(self):
     # Case 1: 'other' is another MyClass object
        """truth(self) is equivalent to self == self,"""
        return self.eq(self, self)

    def is_(self, other):
     # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return self is other
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return self.get_value() is other

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def is_not(self, other):
     # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return not self.eq(self, other)
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return not self.eq(self.get_value(), other)

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def is_none(self):
        """is_none(self) is equivalent to self is None,"""
        return self.eq(self, None)

    def is_not_none(self):
        """is_not_none(self) is equivalent to self is not None,"""
        return not self.eq(self, None)

    def abs(self):
        """abs(self) is equivalent to self if self >= 0 else -self,"""
        return self if self.ge(self, 0) else -self

    def add(self, other):  # is equivalent to self + other
     # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return self.get_value()  + other.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return self.get_value() + other

        # Case 3: We don't know how to handle this type
        return NotImplemented


    def __add__(self, other):
        """__add__(self, other) is equivalent to self + other,"""
        return self.add(other)

    def and_(self, other):
     # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return self.get_value() and  other.get_value()
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return self.get_value() and other

        # Case 3: We don't know how to handle this type
        return NotImplemented


  
    def __and__(self, other):
        """__and__(self, other) is equivalent to self and other,"""
        return self.and_(other)

    def floordiv(self, other):
     # Case 1: 'other' is another MyClass object
        rep = 0
        if isinstance(other, OpOverloaded):
            try:
                rep = self.get_value() // other.get_value()
            except ZeroDivisionError:
                rep = 0
            return re
      
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            try:
                rep = self.get_value() // other
            except ZeroDivisionError:
                rep = 0
            return rep

        # Case 3: We don't know how to handle this type
        return NotImplemented

    

    def __floordiv__(self, other):
        """__floordiv__(self, other) is equivalent to self // other,"""
        return self.floordiv(other)

    def index(self, other):
        """index(self, other) is equivalent to self[other],"""
     # Case 1: 'other' is another MyClass object
        if isinstance(self, List) and isinstance(other, OpOverloaded):
            return self[other.getvalue()]
        
        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int), float):
            return self[other]

        # Case 3: We don't know how to handle this type
        return NotImplemented

        def __index__(self, other):
            """__index__(self, other) is equivalent to self[other],"""
            return self.index(self, other)

    def inv(self):
        """inv(self) is equivalent to not self,"""
        return not self.truth()

    def __inv__(self):
        """__inv__(self) is equivalent to not self,"""
        return self.inv()

    def invert(self):
        """invert(self) is equivalent to not self,"""
        return not self.truth()

    def __invert__(self):
        """__invert__(self) is equivalent to not self,"""
        return self.invert()

    def lfshift(self, other):
        """lfshift(self, other) is equivalent to self << other,"""
        return self.value << other.value

    def __lfshift__(self, other):
        """__lfshift__(self, other) is equivalent to self << other,"""
        return self.lfshift(other)

    def mod(self, other):
        """mod(self, other) is equivalent to self % other,"""
        res = 0
        try:
            res = self.value % other.value
        except ZeroDivisionError:
            res = 0
        return res

    def __mod__(self, other):
        """__mod__(self, other) is equivalent to self % other,"""
        return self.mod(other)

    def mul(self, other):
        """mul(self, other) is equivalent to self * other,"""
        return self.value * other.value

    def __mul__(self, other):
        """__mul__(self, other) is equivalent to self * other,"""
        return self.mul(other)

    def matmul(self, other):
        """matmul(self, other) is equivalent to self @ other,"""
        return self.value @ other.value

    def __matmul__(self, other):
        """__matmul__(self, other) is equivalent to self @ other,"""
        return self.matmul(other)

    def neg(self):
        """neg(self) is equivalent to -self,"""
        return -self.value

    def __neg__(self):
        """__neg__(self) is equivalent to -self,"""
        return self.neg()

    def or_(self, other):
        """or_(self, other) is equivalent to self or other,"""
        return self.value or other.value

    def __or__(self, other):
        """__or__(self, other) is equivalent to self or other,"""
        return self.or_(other)

    def pos(self):
        """pos(self) is equivalent to +self,"""
        return +self.value

    def __pos__(self):
        """__pos__(self) is equivalent to +self,"""
        return self.pos()

    def pow(self, other):

        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            return self.value**other.value

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            return self.value**other

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __pow__(self, other):
        """__pow__(self, other) is equivalent to self ** other,"""
        return self.pow(other)

    def rshift(self, other):
        """rshift(self, other) is equivalent to self >> other,"""
        return self.value >> other.value

    def __rshift__(self, other):
        """__rshift__(self, other) is equivalent to self >> other,"""
        return self.rshift(other)

    def sub(self, other):
        """sub(self, other) is equivalent to self - other,"""
        return self.value - other.value

    def __sub__(self, other):
        """__sub__(self, other) is equivalent to self - other,"""
        return self.sub(other)

    def truediv(self, other):
        """truediv(self, other) is equivalent to self / other,"""
        return self.value / other.value

    def __truediv__(self, other):
        """__truediv__(self, other) is equivalent to self / other,"""
        return self.truediv(other)

    def xor(self, other):
        """xor(self, other) is equivalent to self ^ other,"""
        return self.value ^ other.value

    def __xor__(self, other):
        """__xor__(self, other) is equivalent to self ^ other,"""
        return self.xor(other)

    def comcat(self, other):
        """comcat(self, other) is equivalent to str(self) + str(other),"""
        return str(self.value) + str(other.value)

    def __comcat__(self, other):
        """__concat__(self, other) is equivalent to str(self) + str(other),"""
        return self.comcat(other)

    def contains(self, other):
        """contains(self, other) is equivalent to other in self,"""
        return other.value in self.value

    def __contains__(self, other):
        """__contains__(self, other) is equivalent to other in self,"""
        return self.contains(other)

    def countOf(self, other):
        """countOf(self, other) is equivalent to self.count(other),"""
        return self.countOf(other / value)

    def __countOf__(self, other):
        """__countOf__(self, other) is equivalent to self.count(other),"""
        return self.countOf(other)

    def delitem(self, other):
        """delitem(self, other) is equivalent to del self[other],"""
        del self[other / value]

    def __delitem__(self, other):
        """__delitem__(self, other) is equivalent to del self[other],"""
        return self.delitem(other)

    def getitem(self, other):
        """getitem(self, other) is equivalent to self[other],"""
        return self[other / value]

    def __getitem__(self, other):
        """__getitem__(self, other) is equivalent to self[other],"""
        return self.getitem(other)

    def indexOf(self, other):
        """indexOf(self, other) is equivalent to self.index(other),"""
        return self.indexOf(other.value)

    def __indexOf__(self, other):
        """__indexOf__(self, other) is equivalent to self.index(other),"""
        return self.indexOf(other)

    def setitem(self, other, value):
        """setitem(self, other, value) is equivalent to self[other] = value,"""
        self[other.value] = value.value

    def __setitem__(self, other, value):
        """__setitem__(self, other, value) is equivalent to self[other] = value,"""
        return self.setitem(other, value)

    #   def length_hint(self):
    #       """length_hint(self) is equivalent to len(self),"""
    #       return self.__length_hint__()

    #   def __length_hint__(self):
    #       """__length_hint__(self) is equivalent to len(self),"""
    #       return self.length_hint()

    def call(self, *args, **kwargs):
        """call(self, *args, **kwargs) is equivalent to self(*args, **kwargs),"""
        return self(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """__call__(self, *args, **kwargs) is equivalent to self(*args, **kwargs),"""
        return self.call(self, *args, **kwargs)

    def attrgetter(self, attr):
        """attrgetter(self, attr) is equivalent to getattr(self, attr),"""
        return getattr(self, attr)

    def __attrgetter__(self, attr):
        """__attrgetter__(self, attr) is equivalent to getattr(self, attr),"""
        return self.attrgetter(attr)

    def itemgetter(self, item):
        """itemgetter(self, item) is equivalent to self[item],"""
        return self[item]

    def __itemgetter__(self, item):
        """__itemgetter__(self, item) is equivalent to self[item],"""
        return self.itemgetter(item)

    def methodcaller(self, method, *args, **kwargs):
        """methodcaller(self, method, *args, **kwargs) is equivalent to getattr(self, method)(*args, **kwargs),"""
        return getattr(self, method)(*args, **kwargs)

    def __methodcaller__(self, method, *args, **kwargs):
        """__methodcaller__(self, method, *args, **kwargs) is equivalent to getattr(self, method)(*args, **kwargs),"""
        return self.methodcaller(self, method, *args, **kwargs)

    def iadd(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value += other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value += other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __iadd__(self, other):
        return self.iadd(other)

    def __repr__(self):
        return f"{self.value}"

    def isub(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value -= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value -= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __isub__(self, other):
        return self.isub(other)

    def iand(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value &= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value &= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __iand__(self, other):
        return self.iand(other)

    def ifloordiv(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value //= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value //= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __ifloordiv__(self, other):
        return self.ifloordiv(other)

    def ilshift(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value <<= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value <<= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __ilshift__(self, other):
        return self.ilshift(other)

    def imod(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value %= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value %= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __imod__(self, other):
        return self.imod(other)

    def imul(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value *= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value *= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __imul__(self, other):
        return self.imul(other)

    def imatmul(self, other):
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value @= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value @= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __imatmul__(self, other):
        return self.imatmul(other)

    def ior(self, other):
        """ior(self, other) is equivalent to self |= other,"""
        self.value |= other.value
        return self

    def __ior__(self, other):
        """__ior__(self, other) is equivalent to self |= other,"""
        return self.ior(other)

    def ipow(self, other):
        """ipow(self, other) is equivalent to self **= other,"""
        # Case 1: 'other' is another MyClass object
        if isinstance(other, OpOverloaded):
            self.value **= other.value
            return self

        # Case 2: 'other' is an int or float (e.g., a += 5)
        elif isinstance(other, (int)):
            self.value **= other
            return self

        # Case 3: We don't know how to handle this type
        return NotImplemented

    def __ipow__(self, other):
        """__ipow__(self, other) is equivalent to self **= other,"""
        return self.ipow(other)

    def irshift(self, other):
        """irshift(self, other) is equivalent to self >>= other,"""
        self.value >>= other.value
        return self

    def __irshift__(self, other):
        """__irshift__(self, other) is equivalent to self >>= other,"""
        return self.irshift(other)

    def itruediv(self, other):
        """itruediv(self, other) is equivalent to self /= other,"""
        self.value /= other.value
        return self

    def __itruediv__(self, other):
        """__itruediv__(self, other) is equivalent to self /= other,"""
        return self.itruediv(other)

    def ixor(self, other):
        """ixor(self, other) is equivalent to self ^= other,"""
        self.value ^= other.value
        return self

    def __ixor__(self, other):
        """__ixor__(self, other) is equivalent to self ^= other,"""
        return self.ixor(other)


class TestOpOverload(OpOverloaded):
    def __init__(self, value):
        self.value = value


def main():
    a = OpOverloaded(13)
    b = OpOverloaded(13)
    c = a
    print("a = 13, b = 13")
    print(f"a < b) = {a < b}")  # True
    print(f"a <= b) = {a <= b}")  # True
    print(f"a == b) = {a == b}")  # False
    print(f"a != b = {a != b}")  # True
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
    print(f"a > b = {a > b}")  # False
    print(f"a >= b = {a >= b}")  # False
    print(f"b + a = {b + a}")  # 5
    print(f"b - a = {b - a}")
    print(f"a // b = {a // b}")  # 0
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
    print(f"b -= a {b}")


if __name__ == "__main__":
    main()
