class Point3d:
    """Store and manipulate a 3d X,Y,Z coordinate
    methods: get_x, get_y, get_z return x,y,or z
    move(newx,newy,newz) translates x+newx,y+newy,z+newz

    """

    # intitialie and store x,y, z
    def __init__(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z

    # return x
    def get_x(self):
        return self._x

    # return y
    def get_y(self):
        return self._y

    # return z
    def get_z(self):
        return self._z

    # translate x,y,z to new x,y,z
    def move(self, dx, dy, dz):
        self._x = self._x + dx
        self._y = self._y + dy
        self._z = self._z + dz

    # Return state of point object
    def __str__(self):
        return f"Point3D(x={self._x},y={self._y},z={self._z})\n"


class ColoredPixel(Point3d):
    """Store and manipulate a 3d colored pixel
    adds color to a Point3d object it contains
    methods:
    set_color and get_color as well as al Point3d methods
    """

    # Initialize, store x,y,z in Point3d and color locally
    def __init__(self, x, y, z, color):
        self._x = x
        self._y = y
        self._z = z
        self._color = color

    # Change color ofpixel
    def set_color(self, color):
        self._color = color

    # Report current color
    def get_color(self):
        return self._color

    # Return state of ColoredPixel object
    def __str__(self):
        return f"ColoredPixel(x={self._x}, y={self._y}, z={self._z}, color={self._color})\n"


class Line3d:
    """Store and manipulate a 3d line segment5 methods: get_start, get_end return start or end Point3d
    move(newx,newy,newz) translates start and end points
    """

    # Initialize and store start and end Point3d objects
    def __init__(self, start, end):
        self._start_point = Point3d(start.get_x(), start.get_y(), start.get_z())
        self._end_point = Point3d(end.get_x(), end.get_y(), end.get_z())

    # Return start point
    def get_start(self):
        return self._start_point

    # Return end point
    def get_end(self):
        return self._end_point

    # Translate both start and end points by dx,dy,dz
    def move(self, dx, dy, dz):
        self._start_point.move(dx, dy, dz)
        self._end_point.move(dx, dy, dz)

    # Return state of Line3d object
    def __str__(self):
        return f"Line3D(start=Point3d(x={self._start_point.get_x()}, y={self._start_point.get_y()}, z={self._start_point.get_z()}), end=Point3d(x={self._end_point.get_x()}, y={self._end_point.get_y()}, z={self._end_point.get_z()}))\n"


class Plane3d:
    """Store and manipulate a 3d plane
    methods: get_area returns area of plane
    move(newx,newy,newz) translates all four lines
    """

    # Initialize and store four Line3d objects and length andwidth of plane as local variables
    def __init__(self, line1, line2, line3, line4, length, width):
        self._line1 = Line3d(line1.get_start(), line1.get_end())
        self._line2 = Line3d(line2.get_start(), line2.get_end())
        self._line3 = Line3d(line3.get_start(), line3.get_end())
        self._line4 = Line3d(line4.get_start(), line4.get_end())
        self._length = length
        self._width = width

    # Calculate and return the area of the plane
    def get_area(self):
        return self._length * self._width

    # Translate all four lines by dx,dy,dz
    def move(self, dx, dy, dz):
        self._line1.move(dx, dy, dz)
        self._line2.move(dx, dy, dz)
        self._line3.move(dx, dy, dz)
        self._line4.move(dx, dy, dz)

    # Return state of Plane3d object
    def __str__(self):
        return f"Plane3d:\n\tArea: {self.get_area()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"


point1 = Point3d(1, 1, 1)
point2 = Point3d(1, 6, 1)
point3 = Point3d(1, 6, 1)
point4 = Point3d(6, 6, 1)
point5 = Point3d(6, 6, 1)
point6 = Point3d(6, 1, 1)
point7 = Point3d(6, 1, 1)
point8 = Point3d(1, 1, 1)
red_pixel = ColoredPixel(1, 1, 0, "red")
line1 = Line3d(point1, point2)
line2 = Line3d(point3, point4)
line3 = Line3d(point5, point6)
line4 = Line3d(point7, point8)
plane = Plane3d(line1, line2, line3, line4, 5, 5)

print(point1)
print(red_pixel)
print(line1)
print(plane)
plane.move(1, 1, 1)
print(plane)
"""   #    def add(self, other):
    #        return self.value + other.value

    #    def __add__(self, other):
    #        return self.add(other)

    #    def sub(self, other):
    #        return self.value - other

    #    def __sub__(self, other):
    #        return self.sub(other)

    def floordiv(self, other):
        return self.value // other.value

    def __floordiv__(self, other):
        return self.floordiv(other)

    def mod(self, other):
        return self.value % other.value

    def __mod__(self, other):
        return self.mod(other)

    def pow(self, other):
        return self.value**other.value

    def __pow__(self, other):
        return self.pow(other)

    def rshift(self, other):
        return self.value >> other.value

    def __rshift__(self, other):
        return self.rshift(other)

    def truediv(self, other):
        return self.value / other.value

    def __truediv__(self, other):
        return self.truediv(other)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"({self.value})"

#    def __eq__(self, other):
#        if isinstance(other, TestOpOverload):
#           return self.value == other.value
#        return False

#    def __lt__(self, other):
#        if isinstance(other, TestOpOverload):
#            return self.value < other.value
#        return NotImplemented

#    def __le__(self, other):
#        if isinstance(other, TestOpOverload):
#            return self.value <= other.value
#        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value >= other.value
        return NotImplemented

#    def __ne__(self, other):
#        if isinstance(other, TestOpOverload):
#            return self.value != other.value
#        return NotImplemented

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __bool__(self):
        return bool(self.value)

    def __index__(self):
        return int(self.value)

    def __abs__(self):
        return abs(self.value)

    def __pos__(self):
        return +self.value

    def __invert__(self):
        return ~self.value

    def __and__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value & other.value
        return NotImplemented

    def __or__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value | other.value
        return NotImplemented

    def __xor__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value ^ other.value
        return NotImplemented

    def __lshift__(self, other):
        if isinstance(other, TestOpOverload):
            return self.value << other.value
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value + self.value
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value - self.value
        return NotImplemented

    def __rfloordiv__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value // self.value
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value / self.value
        return NotImplemented

    def __rmod__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value % self.value
        return NotImplemented

    def __rpow__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value**self.value
        return NotImplemented

    def __rrshift__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value >> self.value
        return NotImplemented

    def __rand__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value & self.value
        return NotImplemented

    def __ror__(self, other):
        if isinstance(other, TestOpOverload):
            return other.value | self.value
        return NotImplemente"""
