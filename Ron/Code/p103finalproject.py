import math
import numpy as np

MAXRAD = 6.2832
MINRAD = 0.17
def degtorad(deg):
    if deg >= 1:
        deg = min(max(deg, 1),360)
    elif deg <= -1:
        deg = max(min(deg, -1), -360)
    else:
        return 0
    return round((deg * math.pi / 180),2)

def radtodeg(rad):
    if rad >= MINRAD:
        rad = min(max(rad, MINRAD),MAXRAD)
    elif rad <= -MINRAD:
        rad = max(min(rad, -MINRAD), -MAXRAD)
    else:
        return 0
    return round((rad * 180 / math.pi), 2)

def _vector_components(value):
    """Read a point's coordinates or a line/vector's end-minus-start direction."""
    if isinstance(value, Point3d):
        components = value.get_xyz()
    elif isinstance(value, Line3d):
        components = tuple(b - a for a, b in zip(value.get_start().get_xyz(),
                                               value.get_end().get_xyz()))
    else:
        raise TypeError("Expected a Point3d, Line3d, or Vector3d.")
    if not all(math.isfinite(component) for component in components):
        raise ValueError("Vector components must be finite.")
    return components


def dot(u, v):
    """Return the scalar dot product without changing inputs or rounding."""
    return sum(a * b for a, b in zip(_vector_components(u), _vector_components(v)))

def cross(u, v):
    """Return a new origin-anchored Vector3d using the right-hand rule.

    Inputs are unchanged. Parallel inputs produce zero; no normalization.
    """
    ux, uy, uz = _vector_components(u)
    vx, vy, vz = _vector_components(v)
    return Vector3d(Point3d(0, 0, 0), Point3d(
        uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx))

def unit_vector(v):
    """Return a new origin-anchored unit Vector3d; reject a zero direction."""
    components = _vector_components(v)
    scale = max(abs(component) for component in components)
    if scale == 0:
        raise ValueError("Cannot normalize a zero vector.")
    scaled = tuple(component / scale for component in components)
    length = math.hypot(*scaled)
    return Vector3d(Point3d(0, 0, 0),
                    Point3d(*(component / length for component in scaled)))

def _rotation_pivot(pivot, owner, default=(0, 0, 0)):
    """Snapshot a pivot before any points move; reject malformed coordinates."""
    if pivot is None:
        pivot = default
    elif isinstance(pivot, str):
        if pivot != "center":
            raise ValueError('The only named pivot is "center".')
        pivot = owner if isinstance(owner, Point3d) else owner.get_center()
    if isinstance(pivot, Point3d):
        pivot = pivot.get_xyz()
    coordinates = np.asarray(pivot, dtype=float)
    if coordinates.shape != (3,) or not np.all(np.isfinite(coordinates)):
        raise ValueError('Pivot must be a Point3d, three finite coordinates, or "center".')
    return tuple(coordinates)


class Point3d:
    """Store and manipulate a 3d X,Y,Z coordinate
    methods: get_x, get_y, get_z return x,y,or z
    move(newx,newy,newz) translates x+newx,y+newy,z+newz

    """

    # intitialie and store x,y, z
    def __init__(self, x, y, z, color=None):
        self._x = x
        self._y = y
        self._z = z

    def set_x(self, val):
        self._x  = val

    # Report x
    def get_x(self):
        return self._x

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        self._x = val

    def set_y(self, val):
        self._y = val

    # Report y
    def get_y(self):
        return self._y

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        self._y = val

    def set_z(self, val):
        self._z = val

    def get_z(self):
        return self._z

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, val):
        self._z = val

    def get_xyz(self):
        return (self._x, self._y, self._z)

    def set_xyz(self, newx, newy, newz):
        self._x = newx
        self._y = newy
        self._z = newz
        return self

    # translate x,y,z to new x,y,z
    def move(self, dx, dy, dz):
        self._x = self._x + dx
        self._y = self._y + dy
        self._z = self._z + dz
        return self

    # Return state of point object
    def __str__(self):
        return f"Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def descr(self):
        return f"Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def __repr__(self):
        return f"Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def __neg__(self):
        return -self._x, -self._y, -self._z

    def __iadd__(self, v):
        if isinstance(v, (int, float)):
            self._x += v
            self._y += v
            self._z += v
        else:
            self._x += v.get_x()
            self._y += v.get_y()
            self._z += v.get_z()
        return self

    def __imul__(self, t):

        if isinstance(t, (int, float)):
            self._x *= t
            self._y *= t
            self._z *= t
        else:
            self._x *= t.get_x()
            self._y *= t.get_y()
            self._z *= t.get_z()
        return self

    def __itruediv__(self, t):
        return self.__imul__(1 / t)

    def __add__(self, v):
        if isinstance(v, (int, float)):
            return Point3d(self._x + v, self._y + v, self._z + v)
        else:
            return Point3d(self._x + v.get_x(), self._y + v.get_y(), self._z + v.get_z())

    def __sub__(self, v):
        if isinstance(v, (int, float)):
            return Point3d(self._x - v, self._y - v, self._z - v)
        else:
            return Point3d(self._x - v.get_x(), self._y - v.get_y(), self._z - v.get_z())

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Point3d(
                round((self._x * other),2), round((self._y * other),2), round((self._z * other),2)
            )
        else:
            return Point3d(round((self._x * other.get_x()),2), round((self._y * other.get_y()),2), round((self._z * other.get_z()),2))

    def __rmul__(self, t):
        if isinstance(t, (int, float)):
            return Point3d(round((t * self._x),2), round((t * self._y),2), round((t * self._z),2))
        else:
            return Point3d(round((t.get_x() * self._x),2), round((t.get_y() * self._y),2), round((t.get_z() * self._z),2))

    def __truediv__(self, t):
        if isinstance(t, (int, float)):
            return Point3d(round(((1 / t) * self._x),2), round(((1 / t) * self._y),2), round(((1 / t) * self._z),2))
        else:
            return Point3d(round(((1 / t.get_x()) * self._x),2), round(((1 / t.get_y()) * self._y),2), round(((1 / t.get_z()) * self._z),2))


    def xrot(self, angle_rad, pivot=None):
        """Rotate in place about X through pivot (default: world origin).

        pivot accepts Point3d, an (x, y, z) sequence, or "center".
        Angles are radians; returns self. A point's own center is itself.
        """
        px, py, pz = _rotation_pivot(pivot, self)
        # Subtract the pivot, rotate relative coordinates, then add it back.
        y, z = self._y - py, self._z - pz
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(self._x, py + y * cos_a - z * sin_a,
                     pz + y * sin_a + z * cos_a)
        return self

    def yrot(self, angle_rad, pivot=None):
        """Rotate in place about Y through pivot; see xrot for pivot options."""
        px, py, pz = _rotation_pivot(pivot, self)
        x, z = self._x - px, self._z - pz
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(px + x * cos_a + z * sin_a, self._y,
                     pz - x * sin_a + z * cos_a)
        return self

    def zrot(self, angle_rad, pivot=None):
        """Rotate in place about Z through pivot; see xrot for pivot options."""
        px, py, pz = _rotation_pivot(pivot, self)
        x, y = self._x - px, self._y - py
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(px + x * cos_a - y * sin_a,
                     py + x * sin_a + y * cos_a, self._z)
        return self

    def vecrot(self, vecaxis, angle_rad, pivot=None):
        """
        Rotate in place using Rodrigues' formula; angle_rad is in radians.

        By default, rotate about the supplied line. An explicit pivot moves
        that axis parallel to itself through the chosen point. "center" uses
        this point's position, so the point remains fixed. Returns self.
        """
        # The axis is the infinite line through its start and end points.
        start = np.array(vecaxis.get_start().get_xyz(), dtype=float)
        axis = np.array(vecaxis.get_end().get_xyz(), dtype=float) - start
        origin = np.array(_rotation_pivot(pivot, self, default=start))
        norm = np.linalg.norm(axis)
        if norm == 0:
            raise ValueError("Rotation axis cannot be a zero vector.")
        k = axis / norm
        v = np.array(self.get_xyz(), dtype=float) - origin
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        rotated = (v * cos_a + np.cross(k, v) * sin_a
                   + k * np.dot(k, v) * (1 - cos_a)) + origin
        self.set_xyz(*rotated)
        return self



class ColoredPixel(Point3d):
    """Store and manipulate a 3d colored pixel
    adds color to a Point3d object it contains
    methods:
    set_color and get_color as well as al Point3d methods
    """

    # Initialize, store x,y,z in Point3d and color locally
    def __init__(self, x, y, z, color):
        super().__init__(x, y, z)  # initialize parent Point3d
        self._color = color

    # Change color of pixel
    def set_color(self, color):
        self._color = color

    # Report current color
    def get_color(self):
        return self._color

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, val):
        self._color = val

    def __str__(self):
        return f"ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    # Return state of ColoredPixel object
    def descr(self):
        return f"ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    def __repr__(self):
        return f"ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"


class _Geometry3d:
    """Common in-place transforms for shapes made from Point3d objects."""

    @property
    def _center(self):
        # Calculate on access so editing a child point cannot leave stale data.
        points = self._points()
        count = len(points)
        return Point3d(*(sum(p.get_xyz()[axis] for p in points) / count
                         for axis in range(3)))

    def get_center(self):
        """Return the current midpoint or geometric center."""
        return self._center

    def _transform(self, method, *args):
        # Faces can share edges. Transform each actual point only once.
        points = {id(point): point for point in self._points()}
        for point in points.values():
            getattr(point, method)(*args)
        return self

    def move(self, dx, dy, dz):
        return self._transform("move", dx, dy, dz)

    def xrot(self, angle, pivot=None):
        """Rotate about world X through pivot; radians, in place, returns self.

        pivot=None uses (0, 0, 0); "center" uses this shape's current center.
        A Point3d or (x, y, z) sequence specifies another fixed pivot.
        """
        return self._transform("xrot", angle, _rotation_pivot(pivot, self))

    def yrot(self, angle, pivot=None):
        """Rotate about world Y through pivot; see xrot for pivot options."""
        return self._transform("yrot", angle, _rotation_pivot(pivot, self))

    def zrot(self, angle, pivot=None):
        """Rotate about world Z through pivot; see xrot for pivot options."""
        return self._transform("zrot", angle, _rotation_pivot(pivot, self))

    def vecrot(self, vecaxis, angle, pivot=None):
        """Rotate about vecaxis, or a parallel axis through pivot, in radians.

        Use pivot="center" to spin around this shape's center. Returns self.
        """
        # Freeze both axis and pivot before changing any shared child points.
        axis = Line3d(vecaxis.get_start(), vecaxis.get_end())
        if axis.len_sqr() == 0:
            raise ValueError("Rotation axis cannot be a zero vector.")
        origin = _rotation_pivot(pivot, self, default=axis.get_start().get_xyz())
        return self._transform("vecrot", axis, angle, origin)

    def scale(self, factor):
        """Scale about the world origin; preserve the existing 0.01..10 limit."""
        if factor <  0.001:
            raise ValueError("Scale factor must be a positive number.")
        return self._transform("__imul__", factor)


class Line3d(_Geometry3d):
    """Store and manipulate a 3d line segment methods: get_start, get_end return start or end Point3d
    move(newx,newy,newz) translates start and end points
    """

    # Initialize and store start and end Point3d objects
    def __init__(self, start, end, color=None):
        if isinstance(start, Point3d):
            self._start_pt = Point3d(start.get_x(), start.get_y(), start.get_z())
            self._end_pt = Point3d(end.get_x(), end.get_y(), end.get_z())
            self._color = color
        elif isinstance(start, (list, tuple)):
            self._start_pt = Point3d(start[0], start[1], start[2])
            self._end_pt = Point3d(end[0], end[1], end[2])
            self._color = color
        else:
            raise ValueError("Error Line3d arguments mut be Pomt3d or x,y,z,")
    def _points(self):
        return [self._start_pt, self._end_pt]

    # Return start point
    def get_start(self):
        return self._start_pt

    # Return end point
    def get_end(self):
        return self._end_pt

    def length(self):
        return math.sqrt(self.len_sqr())

    def len_sqr(self):
        xx = self._end_pt.get_x() - self._start_pt.get_x()
        yy = self._end_pt.get_y() - self._start_pt.get_y()
        zz = self._end_pt.get_z() - self._start_pt.get_z()
        return xx * xx + yy * yy + zz * zz

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, val):
        self._color = val

    def __str__(self):
        return f"Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def descr(self):
        return f"Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def __repr__(self):
        return f"Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

class Vector3d(Line3d):
    """Store and manipulate a 3d vector
    methods: get_direction returns direction of vector
    get_origin returns origin of vector
    get_color returns color of vector
    Inherits Line3d transformations; direction is the end point, as in Line3d.
    """

    # intitialie and store x,y, z
    def __init__(self, origin, direction):
        super().__init__(origin, direction)
        # Use the same points as Line3d so inherited transforms stay visible.

    def at(self, t):
        return self.origin + t * self.direction

    # Return the origin of the vector
    def get_origin(self):
        return self._start_pt

    @property
    def origin(self):
        return self._start_pt

    @property
    def direction(self):
        return self._end_pt

    @direction.setter
    def direction(self, val):
        self._end_pt = val

    @origin.setter
    def origin(self, val):
        self._start_pt = val

    def set_origin(self, origin):
        self._start_pt.set_xyz(*origin.get_xyz())

    def get_direction(self):
        return self._end_pt

    def set_direction(self, direction):
        self._end_pt.set_xyz(*direction.get_xyz())

    def __str__(self):
        return f"Vector3D(origin={self._start_pt}, direction={self._end_pt})\n"

    def descr(self):
        return f"Vector3D(origin={self._start_pt}, direction={self._end_pt})\n"

    def __repr__(self):
        return f"Vector3D(origin={self._start_pt}, direction={self._end_pt})\n"


class Square3d(_Geometry3d):
    """Store and manipulate a 3d Square
    methods: get_area returns area of square
    move(newx,newy,newz) translates all four lines
    """

    # Store four boundary edges; centers and dimensions use their current points.
    def __init__(self, line1, line2, line3, line4, bc=None,fc=None):
        self._line1 = line1
        self._line2 = line2
        self._line3 = line3
        self._line4 = line4
        self._border_col = bc
        self._fill_col = fc

    def _points(self):
        return [point for line in (self._line1, self._line2, self._line3, self._line4)
                for point in line._points()]

    @property
    def _length(self):
        return self._line1.length()

    @property
    def _width(self):
        return self._line2.length()

    @property
    def _area(self):
        # Assumes four boundary edges of a square/rectangle, in order.
        return self._length * self._width

    # Calculate and return the area of the square
    def get_area(self):
        return self._area

    def get_bc(self):
        return self._border_col

    def set_bc(self, bc):
        self._border_col = bc

    def get_fc(self):
        return self._fill_col

    def set_fc(self, fc):
        self._fill_col = fc

    def fc(self):
        return self._fill_col

    def bc(self):
        return self._border_col

    # Return state of Square object
    def __str__(self):
        return f"Square:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def descr(self):
        return f"Square:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def __repr__(self):
        return f"Square:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

class Cube3d(_Geometry3d):
    """Six rectangular boundary faces of a cube or rectangular box."""
    def __init__(self, square1, square2=None, square3=None, square4=None,
                 square5=None, square6=None, name="Cube3d",bc=None, fc=None, *, height=None):
        """Accept six faces, one square, or one rectangular face plus height.

        Cube3d(base) uses the square's side as height. Cube3d(base, 10) and
        Cube3d(base, height=10) extrude toward the positive normal; negative
        height reverses it. The positive normal has its largest-magnitude
        component positive (X, then Y, then Z breaks exact ties). For an XY
        base this means +Z, regardless of corner order.
        """
        self._name = name
        remaining = (square3, square4, square5, square6)
        if square2 is not None and not isinstance(square2, Square3d):
            if height is not None or any(face is not None for face in remaining):
                raise TypeError("Provide one base and height, or all six faces.")
            height, square2 = square2, None
        if square2 is None:
            if any(face is not None for face in remaining):
                raise TypeError("Provide one base or all six faces.")
            square1, square2, square3, square4, square5, square6 = self._from_base(square1, height)
        elif height is not None or not all(isinstance(face, Square3d)
                                           for face in (square1, square2, *remaining)):
            raise TypeError("The six-face form requires six squares and no height.")
        self._square1 = square1
        self._square2 = square2
        self._square3 = square3
        self._square4 = square4
        self._square5 = square5
        self._square6 = square6
        self._border_col = bc
        self._fill_col = fc

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    @staticmethod
    def _from_base(base, height):
        """Extrude a closed rectangular face with four ordered boundary edges."""
        if not isinstance(base, Square3d):
            raise TypeError("Base must be a Square3d.")
        lines = (base._line1, base._line2, base._line3, base._line4)
        corners = [line.get_start() for line in lines]
        coords = np.array([point.get_xyz() for point in corners], dtype=float)
        ends = np.array([line.get_end().get_xyz() for line in lines], dtype=float)
        if not np.all(np.isfinite(coords)) or not np.all(np.isfinite(ends)):
            raise ValueError("Base coordinates must be finite.")
        if not np.allclose(ends, np.roll(coords, -1, axis=0), rtol=0, atol=1e-9):
            raise ValueError("Base edges must form a closed boundary in order.")
        u, v = coords[1] - coords[0], coords[3] - coords[0]
        length, width = math.hypot(*u), math.hypot(*v)
        if length == 0 or width == 0:
            raise ValueError("Base sides must have positive lengths.")
        if (not math.isclose(float(np.dot(u / length, v / width)), 0, abs_tol=1e-9)
                or not np.allclose(coords[2] - coords[0], u + v, rtol=1e-9, atol=1e-9)):
            raise ValueError("Base must be a rectangle.")
        if height is None:
            if not math.isclose(length, width, rel_tol=1e-9):
                raise ValueError("Provide height for a rectangular, non-square base.")
            height = length
        height = float(height)
        if not math.isfinite(height) or height == 0:
            raise ValueError("Height must be nonzero and finite.")
        normal = np.cross(u / length, v / width)
        normal /= np.linalg.norm(normal)
        # Corner order must not decide which side a positive height builds on.
        if normal[np.argmax(np.abs(normal))] < 0:
            normal = -normal
        offset = normal * height
        top = [Point3d(*(coordinate + offset)) for coordinate in coords]

        def edge(start, end):
            line = Line3d(start, end)
            line._start_pt, line._end_pt = start, end
            return line

        def face(points):
            return Square3d(*(edge(points[i], points[(i + 1) % 4]) for i in range(4)),
                            bc=base.get_bc(), fc=base.get_fc())

        top_face = face(top)
        sides = [face([corners[i], corners[(i + 1) % 4],
                       top[(i + 1) % 4], top[i]]) for i in range(4)]
        # Join coincident base endpoints only after validation succeeds.
        for i, line in enumerate(lines):
            line._end_pt = corners[(i + 1) % 4]
        return (base, top_face, *sides)

    def get_fc(self):
        return self._fill_col

    def get_bc(self):
        return self._border_col

    def set_fc(self, color):
        self._fill_col= color

    def set_bc(self, color):
        self._border_col = color

    def _points(self):
        return [point for square in (self._square1, self._square2, self._square3,
                                    self._square4, self._square5, self._square6)
                for point in square._points()]

    @property
    def _volume(self):
        # Base area times perpendicular height works after any rotation.
        base = self._square1._points()
        origin = np.array(base[0].get_xyz(), dtype=float)
        offsets = [np.array(point.get_xyz(), dtype=float) - origin for point in base]
        normal = max((np.cross(u, v) for u in offsets for v in offsets),
                     key=lambda vector: np.linalg.norm(vector))
        norm = np.linalg.norm(normal)
        if norm == 0:
            return 0.0
        normal = normal / norm
        height = max(abs(np.dot(np.array(point.get_xyz()) - origin, normal))
                     for point in self._points())
        return float(self._square1.get_area() * height)

    def get_volume(self):
        return self._volume

    def __str__(self):
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4},\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}\tvolume: {self.get_volume()}, fill color: {self.get_fc()}, tborder color: {self.get_bc()}\n")

    def __repr__(self):
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4}\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}\tvolume: {self.get_volume()}, fill color: {self.get_fc()}, border color: {self.get_bc()}\n")


    def descr(self):
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4}\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}, volume: {self.get_volume()}, fill color: {self.get_fc()}, border color: {self.get_bc()}\n")

class Sphere3d(_Geometry3d):
    """ Sphere3d represents a shpere in 3 dementions
        as arguments it takes a Point3d center ahd a radius. and optionally a name,
        a matrial and a color
    """
    def __init__(self, center, radius, name=None,mat=None, color=None):
        # Stationary Sphere
        self._static_center= center
        self._radius = radius
        self._mat = mat
        self._color = color
        self._name = name   
        self._radius = max(0, radius)

    @property
    def center(self):
        return self._center

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name
        
    def get_static_radius_center(self):
        return self._static_center

    def get_static_radius(self):
        return self._radius

    def set_static_center(self, center):
        self._static_center = center
        self._center = Vector3d(self._static_center, Point3d(0, 0, 0))

    def set_static_radius(self, radius):
        self._radius = max(0, radius)
    
    def get_color(self):
        return self._color
    
    def set_color(self, color):
        self._color = color
    
    def get_radius(self):
        return self.get_static_radius()
        
    def get_center(self):
        return self.get_static_radius_center()

    def __str__(self):
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")

    def __repr__(self):
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")

    def descr(self):
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")

if __name__ == "__main__":
    point1 = Point3d(1, 1, 1)
    point2 = Point3d(1, 6, 1)
    point3 = Point3d(1, 6, 1)
    point4 = Point3d(6, 6, 1)
    point5 = Point3d(6, 6, 1)
    point6 = Point3d(6, 1, 1)
    point7 = Point3d(6, 1, 1)
    point8 = Point3d(1, 1, 1)
    print(f'degtorad 360 {degtorad(360)}, radtodeg 7 {radtodeg(7)}')
    vec1 = Vector3d(point2, point6)
    print(f'vec1: {vec1}')
    vec1.yrot(.35)
    print(f'vec1 after rotation: {vec1}')

    red_pixel = ColoredPixel(1, 1, 0, "red")
    print(f'Orig redpixel= {red_pixel}')
    red_pixel.set_color("blue")
    red_pixel.move(1, 1, 1)
    red_pixel.set_x(5)
    print(f'redpixel after set_color blue, move 1 1 1 setx 5 = {red_pixel}')
    line1 = Line3d(point1, point2)
    line2 = Line3d(point3, point4)
    line3 = Line3d(point5, point6)
    line4 = Line3d(point7, point8)
    line5 = Line3d((4,4,4), (4,4,-4))
    line6 = Line3d((4,4,-4),(4,-4,-4))
    line7 = Line3d((4,-4,-4), (4,-4,4))
    line8 = Line3d((4,-4,4),(4,4,4))
    
    cube_sqr = Square3d(line5, line6, line7, line8)
    cube2 = Cube3d(cube_sqr)
    print(f'Frseh Made cube2: \n{cube2}')
    cube2.yrot(degtorad(90), pivot="center")
    print(f'cube2 rotated 90 aroud y of center:\n{cube2}')
    square1 = Square3d(line1, line2, line3, line4)
    cube1 = Cube3d(square1)
    rectangle1 = Cube3d(square1, 50, name="Rectangle3d")
    sphere1 = Sphere3d(Point3d(10,10,10), 50,name="sphere1", color="blue")
    print(point1)
    print(red_pixel)
    print(line1)
    print(f'square1:\n{square1}')
    square1.zrot(.70)
    print(f'square1 rotated around z by .70 radians = {square1}')
    print(f'cuba1 before rotate\n{cube1}')
    cube1.zrot(degtorad(90), Point3d(-10,-10,-10))
    print(f'cube1 rotated 90 deg arund z of its oqn center\n {cube1}')
    print(rectangle1)
    print(sphere1)
 
    print(f'Current center: {square1.get_center()}')

    # --- Example Usage ---
    angle = 0.45  # Angle in radians

    # 1. Representing a 3D Line: Line = Point + t * Vector
    line_point = line2
    line_vector =  line4

    print(f'line2: {line2}  line3 {line3}')
    # Save text only when a before/after comparison is wanted.
    before_line2 = str(line2)
    before_line3 = str(line3)
    line2.xrot(angle)
    line3.vecrot(line1, angle)

    print(f'line2: {line2} line3 {line3}')
    # --- Example Usage ---
    angle = 0.45
    arbitrary_axis = line3 # Diagonal axis
    sample_point = point7

    print("Original Point      :", point2)
    print("Rotated around Y    :", point2.yrot(angle))
    print("Rotated around Z    :", point3.zrot(angle))
    print("Rotated around Vector:", point4.vecrot(arbitrary_axis, angle))


    # --- Output Verification ---
    print("--- ROTATED LINE ---")
    print(f"Original Line : {before_line2}  -> Rotated: {line2}")
    print(f"Original Line: {before_line3}  -> Rotated: {line3}\n")

    #print("--- ROTATED PLANE ---")
    #print(f"Original Point : {plane_point}  -> Rotated: {plane_point_rot}")
    #print(f"Original Vector 1: {plane_v1}  -> Rotated: {plane_v1_rot}")
    #p#rint(f"Original Vector 2: {plane_v2}  -> Rotated: {plane_v2_rot}")
