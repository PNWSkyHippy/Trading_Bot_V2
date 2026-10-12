import math
import numpy as np
from overloaded_inc import OpOverloaded

MAXRAD = 6.28318530717958
MINRAD = 0.01745329251994329
def degtorad(deg):
    if deg >= 1:
        deg = min(max(deg, 1),360)
    elif deg <= -1:
        deg = max(min(deg, -1), -360)
    else:
        return 0
    return deg * math.pi / 180

def radtodeg(rad):
    if rad >= MINRAD:
        rad = min(max(rad, MINRAD),MAXRAD)
    elif rad <= -MINRAD:
        rad = max(min(rad, -MINRAD), -MAXRAD)
    else:
        return 0
    return rad * 180 / math.pi

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


class Point3d(OpOverloaded):
    """Store and manipulate a 3d X,Y,Z coordinate
    methods: get_x, get_y, get_z return x,y,or z
    move(newx,newy,newz) translates x+newx,y+newy,z+newz

    """

    # intitialie and store x,y, z
    def __init__(self, x, y, z, color=None,name="Point3d"):
        self._x = x
        self._y = y
        self._z = z
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def deepcopy(self):
        return Point3d(self.get_x(), self.get_y(), self.get_z())
    
    def copy(self):
        return Point3d(self.get_x(), self.get_y(), self.get_z())

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
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def descr(self):
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def __repr__(self):
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

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



class ColoredPixel(Point3d, OpOverloaded):
    """Store and manipulate a 3d colored pixel
    adds color to a Point3d object it contains
    methods:
    set_color and get_color as well as al Point3d methods
    """

    # Initialize, store x,y,z in Point3d and color locally
    def __init__(self, x, y, z, color,name="ColoredPixel"):
        super().__init__(x, y, z)  # initialize parent Point3d
        self._color = color
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

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
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    # Return state of ColoredPixel object
    def descr(self):
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    def __repr__(self):
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"


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

    def get_perpendicular_vectors(self,v):

        # Make sure the input vector is normalized
        lv = v.get_end()
        v = np.array((lv.get_x(), lv.get_y(), lv.get_z()))
        v = v / np.linalg.norm(v)
    
        # Pick the axis with the smallest absolute value to project onto cleanly
        if abs(v[0]) < abs(v[1]):
            # Swap Y and Z, negate one, zero out X
            p = np.array([0, -v[2], v[1]])
        else:
            # Swap X and Z, negate one, zero out Y
            p = np.array([-v[2], 0, v[0]])
        
        # Normalize our newly found perpendicular vector
        p = p / np.linalg.norm(p)

        # Now use the cross product of your 1st vector and the new perpendicular
        # vector to get the third orthogonal normal axis!
        normal = np.cross(v, p)
    
        return p, normal

class Line3d(_Geometry3d, OpOverloaded):
    """Store and manipulate a 3d line segment methods: get_start, get_end return start or end Point3d
    move(newx,newy,newz) translates start and end points
    """

    # Initialize and store start and end Point3d objects
    def __init__(self, start, end, color=None, name="Line3d"):
        if isinstance(start, Point3d):
            self._start_pt = Point3d(start.get_x(), start.get_y(), start.get_z())
            self._end_pt = Point3d(end.get_x(), end.get_y(), end.get_z())
            self._color = color
            self._name = name
        elif isinstance(start, (list, tuple)):
            self._start_pt = Point3d(start[0], start[1], start[2])
            self._end_pt = Point3d(end[0], end[1], end[2])
            self._color = color
            self._name = name
        else:
            raise ValueError("Error Line3d arguments mut be Pomt3d or x,y,z,")
 
    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

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
    
    def deepcopy(self):
        return Line3d(self.get_start(), self.get_end(), self.get_color())
    
    def copy(self):
        return Line3d(self.get_start(), self.get_end(), self.get_color())

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
        return f"{self.get_name()}:Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def descr(self):
        return f"{self.get_name()}:Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def __repr__(self):
        return f"{self.get_name()}:Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

class Vector3d(Line3d, OpOverloaded):
    """Store and manipulate a 3d vector
    methods: get_direction returns direction of vector
    get_origin returns origin of vector
    get_color returns color of vector
    Inherits Line3d transformations; direction is the end point, as in Line3d.
    """

    # intitialie and store x,y, z
    def __init__(self, origin, direction, name="Vector3d"):
        super().__init__(origin, direction)
        # Use the same points as Line3d so inherited transforms stay visible.
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

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
        return f"{self.get_name()}:origin={self._start_pt}\n\tdirection={self._end_pt}\n"

    def descr(self):
        return f"{self.get_name()}:origin={self._start_pt}\n\tdirection={self._end_pt}\n"

    def __repr__(self):
        return f"{self.get_name()}:origin={self._start_pt}\n\tdirection={self._end_pt}\n"


class Square3d(_Geometry3d, OpOverloaded):
    """Store and manipulate a 3d Square
    methods: get_area returns area of square
    move(newx,newy,newz) translates all four lines
    """ 
    # Store four boundary edges; centers and dimensions use their current points.
    def __init__(self, line1, line2, line3, line4, bc=None,fc=None, name="Square3d"):
        self._line1 = line1.deepcopy()
        self._line2 = line2.deepcopy()
        self._line3 = line3.deepcopy()
        self._line4 = line4.deepcopy()
        self._border_col = bc
        self._fill_col = fc
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

    def _points(self):
        return [point for line in (self._line1, self._line2, self._line3, self._line4)
                for point in line._points()]

    def deepcopy(self):
        return Square3d(self._line1, self._line2, self._line3, self._line4,  self._border_col, self._fill_col)

    def copy(self):
        return Square3d(self._line1, self._line2, self._line3, self._line4,  self._border_col, self._fill_col)

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

    @_area.setter
    def _area(self, val):
          raise ValueError("_ar cannot be set mannually. Adjust length or width instead.")
    
    @_length.setter
    def _length(self, val):
          self._length = val

    @_width.setter
    def _width(self, val):
          self._with = val

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
        return f"{self.get_name()}:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def descr(self):
        return f"{self.get_name()}:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def __repr__(self):
        return f"{self.get_name()}:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

class Circle3d(_Geometry3d, OpOverloaded):
    """Circle stored as real Point3d objects so inherited move/rot/scale work.

    _cent, _rad_edge and _norm_tip (center + unit normal) are the only stored
    geometry; radius, normal, vectors and border are derived on every call.
    """
    def __init__(self, center, rad_edge, bc= None, fc=None, name="Circle3d", normal=None):
        """normal: optional facing direction (3 numbers); None picks one perpendicular to the radius."""
        self._cent = center.copy()
        self._rad_edge = rad_edge.copy()
        radial = self._xyz(self._rad_edge) - self._xyz(self._cent)
        if np.linalg.norm(radial) == 0:
            raise ValueError("Circle3d center and edge point cannot be the same point.")
        if normal is not None:
            norm = np.array(normal, dtype=float)
            if np.linalg.norm(norm) == 0:
                raise ValueError("Circle3d normal cannot be a zero vector.")
            norm = norm / np.linalg.norm(norm)
        else:
            # Direction-only vector (from origin) so get_perpendicular_vectors sees end - start.
            _, norm = self.get_perpendicular_vectors(Vector3d((0, 0, 0), tuple(radial)))
        self._norm_tip = Point3d(*(self._xyz(self._cent) + norm))
        self._border_color = bc
        self._fill_color = fc
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

    @staticmethod
    def _xyz(point):
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        return [self._cent, self._rad_edge, self._norm_tip]

    def get_norm(self):
        n = self._xyz(self._norm_tip) - self._xyz(self._cent)
        return n / np.linalg.norm(n)

    def get_vec1(self):
        return Vector3d(self._cent, self._rad_edge)

    def get_vec2(self):
        # In-plane unit vector perpendicular to vec1 (normal x vec1).
        v1 = self._xyz(self._rad_edge) - self._xyz(self._cent)
        v2 = np.cross(self.get_norm(), v1)
        return v2 / np.linalg.norm(v2)

    def get_center(self):
        return self._cent

    def set_center(self, new_c):
        # Move the whole shape so its center lands on new_c.
        d = self._xyz(new_c) - self._xyz(self._cent)
        self.move(*d)

    def get_radius(self):
        return self.get_vec1().length()

    def set_radius(self, new_r):
        v1 = self._xyz(self._rad_edge) - self._xyz(self._cent)
        self._rad_edge.set_xyz(*(self._xyz(self._cent) + v1 / np.linalg.norm(v1) * new_r))

    def get_border(self):
        return 2 * math.pi * self.get_radius()

    def get_bc(self):
        return self._border_color

    def set_bc(self, new_bc):
        self._border_color = new_bc

    def get_fc(self):
        return self._fill_color

    def set_fc(self, nwe_fc):
        self._fill_color = nwe_fc

    def __str__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\n\tnormal={self.get_norm()}\n\t fc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def __repr__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\n\tnormal={self.get_norm()}\n\t fc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def descr(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\n\tnormal={self.get_norm()}\n\t fc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

class Cylinder3d(Circle3d):
    """Circle base plus a stored _top point (center + normal * height)."""
    def __init__(self, center, rad_edge, height, bc=None, fc=None, name="Cylinder3d", normal=None):
        super().__init__(center, rad_edge, bc, fc, name, normal)
        self._top = Point3d(*(self._xyz(self._cent) + self.get_norm() * height))
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

    def _points(self):
        return super()._points() + [self._top]

    def get_top(self):
        return self._top

    def get_area(self):
        r = self.get_radius()
        return 2 * math.pi * r * self.get_height() + 2 * (math.pi * (r * r))

    def get_height(self):
        return float(np.linalg.norm(self._xyz(self._top) - self._xyz(self._cent)))

    def get_volume(self):
        r = self.get_radius()
        return math.pi * (r * r) * self.get_height()

    def set_height(self, new_h):
        self._top.set_xyz(*(self._xyz(self._cent) + self.get_norm() * new_h))

    def __str__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def __repr__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def __descr__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

import numpy as np

class Torus3d(_Geometry3d, OpOverloaded):
    def __init__(self, center, tor_rad, tube_rad, bc=None, fc=None, name=None):
        """
        :param center_point: Point3d representing the center of the torus hole
        :param normal_vector: Vector3d defining the orientation of the torus ring
        :param major_radius: Distance from hole center to tube center (R)
        :param minor_radius: Thickness radius of the tube itself (r)
        """
        self._cent = center.copy()
        self._rad_edge = tor_rad.copy()
        self._tube_rad = tube_rad.copy()
        self._fill_color = fc
        self._border_color = bc
        self._name = name

        radial = self._xyz(self._rad_edge) - self._xyz(self._cent)
        tube_radial = self._xyz(self._tube_rad) - self._xyz(self._rad_edge)
        if np.linalg.norm(radial) == 0:
            raise ValueError("Circle3d center and edge point cannot be the same point.")
        # Direction-only vector (from origin) so get_perpendicular_vectors sees end - start.
        _, normal = self.get_perpendicular_vectors(Vector3d((0, 0, 0), tuple(radial)))
        self._norm_tip = Point3d(*(self._xyz(self._cent) + normal))
        self._cyl_list = self.get_segments()

    def _points(self):
        # Torus's own defining points plus every segment's points, so inherited
        # move/rot/scale turn the whole ring about one shared pivot.
        pts = [self._cent, self._rad_edge, self._tube_rad, self._norm_tip]
        for cyl in self.get_cyllist():
            pts += cyl._points()
        return pts

    def get_center(self):
        return self._cent

    def get_norm(self):
        n = self._xyz(self._norm_tip) - self._xyz(self._cent)
        return n / np.linalg.norm(n)

    def get_major_radius(self):
        return self.length(self._cent, self._rad_edge)

    def get_minor_radius(self):
        return self.length(self._rad_edge, self._tube_rad)

    def length(self, start, end):
        return math.sqrt(self.len_sqr(start, end))
    
    def len_sqr(self, start, end):
        xx = end.get_x() - start.get_x()
        yy = end.get_y() - start.get_y()
        zz = end.get_z() - start.get_z()
        return xx * xx + yy * yy + zz * zz

    @staticmethod
    def _xyz(point):
        return np.array(point.get_xyz(), dtype=float)

    def get_cyllist(self):
        return self._cyl_list

    def set_cyllist(self):
        self._cyl_list = self.get_segments()
    
    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_fc(self):
        return self._fill_color
    
    def set_fc(self, color):
        self._fill_color = color

    def get_bc(self):
        return self._border_color

    def set_bc(self, color):
        self._border_color = color

    def __str__(self):
        ret_str =  f'{self.get_name()}:\n'
        for cyl in self.get_cyllist():
            ret_str += f'\t{cyl}\n\n'
        return ret_str

    def __repr__(self):
        ret_str =  f'{self.get_name()}:\n'
        for cyl in self.get_cyllist():
            ret_str += f'\t{cyl}\n\n'
        return ret_str
 
    def desc(self):
        ret_str =  f'{self.get_name()}:\n'
        for cyl in self.get_cyllist():
            ret_str += f'\t{cyl}\n\n'
        return ret_str

    def get_segments(self, num_segments=24):
        """
        Generates a chained list of pre-initialized Cylinder3d objects 
        approximating the torus ring.
        """
        segment_list = []
        
        # 1. Map the 2D local plane of the major torus ring from its normal
        n = self.get_norm()
        R, r = self.get_major_radius(), self.get_minor_radius()
        helper = np.array([1, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1, 0])
        u = np.cross(n, helper)
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        
        cx, cy, cz = self._cent.get_x(), self._cent.get_y(), self._cent.get_z()
        
        # Generate the centerline ring path positions
        theta_vals = np.linspace(0, 2 * np.pi, num_segments + 1)
        centerline_points = []
        
        for theta in theta_vals:
            dir_vec = u * np.cos(theta) + v * np.sin(theta)
            px = cx + R * dir_vec[0]
            py = cy + R * dir_vec[1]
            pz = cz + R * dir_vec[2]
            centerline_points.append(Point3d(px, py, pz))
        fill = self.get_fc()
        # 2. Loop through and chain the segments end-to-end
        for i in range(num_segments):
            base_center = centerline_points[i]
            top_center = centerline_points[i+1]
            
            # Compute segment direction and height
            seg_vector = np.array([
                top_center.get_x() - base_center.get_x(),
                top_center.get_y() - base_center.get_y(),
                top_center.get_z() - base_center.get_z()
            ])
            height = np.linalg.norm(seg_vector)
            
            if height <= 0:
                continue
            seg_normal = seg_vector / height
                
            # 3. Calculate an outward RadialEdgePoint to prevent joints from twisting
            outward_vec = np.array([
                base_center.get_x() - cx,
                base_center.get_y() - cy,
                base_center.get_z() - cz
            ])
            
            # Make the radial vector perfectly perpendicular to the segment spine
            radial_dir = outward_vec - np.dot(outward_vec, seg_normal) * seg_normal
            radial_dir /= np.linalg.norm(radial_dir)
            
            radial_edge = Point3d(
                base_center.get_x() + radial_dir[0] * r,
                base_center.get_y() + radial_dir[1] * r,
                base_center.get_z() + radial_dir[2] * r
            )
            
            # 4. Instantiate and store (points auto-generate inside Cylinder3d)
            nam = f'cylinder{i}'
            segment_list.append(Cylinder3d(base_center, radial_edge, height, bc=self.get_bc(), fc=fill,
                                           name=nam, normal=seg_normal))
            
        return segment_list

 
class CurvedCylinder3d(_Geometry3d, OpOverloaded):
    """A tube bent around a circular arc (a slice of a torus) - the "banana".

    Stored as real Point3d objects so inherited move/rot/scale work:
        _bend_cent  center the tube curves around
        _start      start of the tube's center line (spine); |start - bend_cent| = bend radius R
        _edge       a point on the tube surface at the start, r outward from _start
        _norm_tip   bend_cent + unit normal of the bend plane
    _angle (radians) is a plain number - rotate/move/uniform scale never change it.
    The spine sweeps counter-clockwise about the normal (right-hand rule).
    """
    def __init__(self, bend_center, spine_start, tube_radius, angle, bc=None, fc=None,
                 name="CurvedCylinder3d", normal=None):
        if not 0 < angle <= 2 * math.pi + 1e-9:
            raise ValueError("CurvedCylinder3d angle must be in (0, 2*pi] radians.")
        self._bend_cent = bend_center.copy()
        self._start = spine_start.copy()
        radial = self._xyz(self._start) - self._xyz(self._bend_cent)
        R = np.linalg.norm(radial)
        if R == 0:
            raise ValueError("CurvedCylinder3d bend center and spine start cannot be the same point.")
        if not 0 < tube_radius < R:
            raise ValueError(f"CurvedCylinder3d tube radius ({tube_radius}) must be > 0 and smaller than the "
                             f"bend radius ({R:.4g} = distance from bend center to spine start).")
        e1 = radial / R
        if normal is None:
            _, n = self.get_perpendicular_vectors(Vector3d((0, 0, 0), tuple(radial)))
        else:
            # Keep only the part of the normal that is perpendicular to the radius.
            n = np.array(normal, dtype=float)
            n = n - np.dot(n, e1) * e1
            if np.linalg.norm(n) < 1e-9:
                raise ValueError("CurvedCylinder3d normal cannot be parallel to the radius.")
        n = n / np.linalg.norm(n)
        self._edge = Point3d(*(self._xyz(self._start) + e1 * tube_radius))
        self._norm_tip = Point3d(*(self._xyz(self._bend_cent) + n))
        self._angle = float(angle)
        self._border_color = bc
        self._fill_color = fc
        self._name = name

    @staticmethod
    def _xyz(point):
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        return [self._bend_cent, self._start, self._edge, self._norm_tip]

    # ---- frame: e1 = radial at the start, e2 = sweep direction at the start
    def _frame(self):
        c = self._xyz(self._bend_cent)
        e1 = self._xyz(self._start) - c
        e1 = e1 / np.linalg.norm(e1)
        n = self.get_norm()
        return c, e1, np.cross(n, e1), n

    def get_norm(self):
        n = self._xyz(self._norm_tip) - self._xyz(self._bend_cent)
        return n / np.linalg.norm(n)

    def get_bend_center(self):
        return self._bend_cent

    def get_bend_radius(self):
        return float(np.linalg.norm(self._xyz(self._start) - self._xyz(self._bend_cent)))

    def get_tube_radius(self):
        return float(np.linalg.norm(self._xyz(self._edge) - self._xyz(self._start)))

    def get_angle(self):
        return self._angle

    def set_angle(self, angle):
        if not 0 < angle <= 2 * math.pi + 1e-9:
            raise ValueError("CurvedCylinder3d angle must be in (0, 2*pi] radians.")
        self._angle = float(angle)

    def radial_dir(self, t):
        """Unit vector from the bend center toward the spine at fraction t (0..1)."""
        _c, e1, e2, _n = self._frame()
        th = t * self._angle
        return math.cos(th) * e1 + math.sin(th) * e2

    def tangent(self, t):
        """Unit direction the tube is heading at fraction t (0..1)."""
        _c, e1, e2, _n = self._frame()
        th = t * self._angle
        return -math.sin(th) * e1 + math.cos(th) * e2

    def spine_point(self, t):
        """Point3d on the tube's center line at fraction t (0..1)."""
        return Point3d(*(self._xyz(self._bend_cent) + self.get_bend_radius() * self.radial_dir(t)))

    def surface_point(self, t, phi):
        """Point3d on the tube surface: t along the bend (0..1), phi around the tube (radians)."""
        R, r = self.get_bend_radius(), self.get_tube_radius()
        p = (self._xyz(self._bend_cent) + (R + r * math.cos(phi)) * self.radial_dir(t)
             + r * math.sin(phi) * self.get_norm())
        return Point3d(*p)

    def get_spine_start(self):
        return self._start

    def get_spine_end(self):
        return self.spine_point(1.0)

    def get_center(self):
        # Middle of the bend's center line, so pivot="center" spins the banana about its middle.
        return self.spine_point(0.5)

    def get_arc_length(self):
        return self.get_bend_radius() * self._angle

    def get_volume(self):
        r = self.get_tube_radius()
        return math.pi * (r * r) * self.get_arc_length()

    def get_area(self):
        # Side area (Pappus) plus the two end caps unless the bend closes on itself.
        r = self.get_tube_radius()
        caps = 0 if self._angle >= 2 * math.pi - 1e-9 else 2 * math.pi * (r * r)
        return 2 * math.pi * r * self.get_arc_length() + caps

    def make_next(self, angle, twist=0.0, bend_radius=None, tube_radius=None,
                  bc=None, fc=None, name=None):
        """New CurvedCylinder3d that continues smoothly from this one's end.

        angle   how far the new piece bends (radians)
        twist   rolls the new bend about the tube's direction (radians):
                0 keeps curling the same way, pi curls back the other way (S-bend),
                pi/2 turns it up/down out of this bend's plane
        """
        R2 = self.get_bend_radius() if bend_radius is None else bend_radius
        r2 = self.get_tube_radius() if tube_radius is None else tube_radius
        p = self._xyz(self.get_spine_end())
        T = self.tangent(1.0)
        inward = -self.radial_dir(1.0)                  # from spine end toward this bend's center
        d = inward * math.cos(twist) + np.cross(T, inward) * math.sin(twist)
        center = Point3d(*(p + R2 * d))
        normal = np.cross(-d, T)                        # makes the new sweep start along T
        return CurvedCylinder3d(center, Point3d(*p), r2, angle,
                                bc=self._border_color if bc is None else bc,
                                fc=self._fill_color if fc is None else fc,
                                name=name or f"{self._name}+", normal=normal)

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_bc(self):
        return self._border_color

    def set_bc(self, bc):
        self._border_color = bc

    def get_fc(self):
        return self._fill_color

    def set_fc(self, fc):
        self._fill_color = fc

    def __str__(self):
        return (f'{self.get_name()}:\n\tbend center={self.get_bend_center()}\tbend radius={self.get_bend_radius()},'
                f'  tube radius={self.get_tube_radius()},  angle={math.degrees(self._angle)} deg\n'
                f'\tstart={self.get_spine_start()}\tend={self.get_spine_end()}\tnormal={self.get_norm()}\n'
                f'\tvolume={self.get_volume()},  area={self.get_area()},  fc={self.get_fc()}, bc={self.get_bc()}')

    def __repr__(self):
        return self.__str__()

    def descr(self):
        return self.__str__()


class CurvedTorus3d(_Geometry3d, OpOverloaded):
    """Torus built from `segments` CurvedCylinder3d bends chained end to end (smooth joints)."""
    def __init__(self, center, ring_point, tube_radius, segments=4, bc=None, fc=None,
                 name="CurvedTorus3d", normal=None):
        if segments < 1:
            raise ValueError("CurvedTorus3d needs at least one segment.")
        ring_r = float(np.linalg.norm(np.array(ring_point.get_xyz(), float) - np.array(center.get_xyz(), float)))
        if not 0 < tube_radius < ring_r:
            raise ValueError(f"CurvedTorus3d tube radius ({tube_radius}) must be > 0 and smaller than the "
                             f"ring radius ({ring_r:.4g} = distance from center to ring point).")
        self._segments = int(segments)
        self._tube_r = float(tube_radius)
        self._border_color = bc
        self._fill_color = fc
        self._name = name
        first = CurvedCylinder3d(center, ring_point, tube_radius, 2 * math.pi / self._segments,
                                 bc, fc, f"{name}_bend0", normal)
        self._bends = [first]
        for i in range(1, self._segments):
            self._bends.append(self._bends[-1].make_next(2 * math.pi / self._segments,
                                                         name=f"{name}_bend{i}"))

    def _points(self):
        return [p for bend in self._bends for p in bend._points()]

    def get_bends(self):
        return self._bends

    def get_center(self):
        return self._bends[0].get_bend_center()

    def get_norm(self):
        return self._bends[0].get_norm()

    def get_major_radius(self):
        return self._bends[0].get_bend_radius()

    def get_minor_radius(self):
        return self._bends[0].get_tube_radius()

    def get_volume(self):
        return sum(b.get_volume() for b in self._bends)

    def get_area(self):
        r = self.get_minor_radius()
        return 2 * math.pi * r * 2 * math.pi * self.get_major_radius()

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_bc(self):
        return self._border_color

    def set_bc(self, bc):
        self._border_color = bc
        for b in self._bends:
            b.set_bc(bc)

    def get_fc(self):
        return self._fill_color

    def set_fc(self, fc):
        self._fill_color = fc
        for b in self._bends:
            b.set_fc(fc)

    def __str__(self):
        return (f'{self.get_name()}:\n\tcenter={self.get_center()}\tR={self.get_major_radius()},  '
                f'r={self.get_minor_radius()},  segments={len(self._bends)},  volume={self.get_volume()},  '
                f'area={self.get_area()}\n\tnormal={self.get_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}')

    def __repr__(self):
        return self.__str__()

    def descr(self):
        return self.__str__()


class Cone3d(Circle3d):
    """Circle base plus a stored _top apex point (center + normal * height)."""
    def __init__(self, center, rad_edge, height, bc=None, fc=None, name="Cone3", normal=None):
        super().__init__(center, rad_edge, bc, fc, name, normal)
        self._top = Point3d(*(self._xyz(self._cent) + self.get_norm() * height))
        self._name = name


    def get_name(self):
        return self._name

    def set_name(self,name):
        self._name = name

    def _points(self):
        return super()._points() + [self._top]

    def get_apex(self):
        return self._top

    def get_height(self):
        return float(np.linalg.norm(self._xyz(self._top) - self._xyz(self._cent)))

    def set_height(self, new_h):
        self._top.set_xyz(*(self._xyz(self._cent) + self.get_norm() * new_h))

    def get_slant_height(self):
        r, h = self.get_radius(), self.get_height()
        return math.sqrt((r * r) + (h * h))

    def get_area(self):
        r = self.get_radius()
        return math.pi * r * self.get_slant_height() + math.pi * (r * r)

    def get_volume(self):
        r = self.get_radius()
        return (1/3) * math.pi * (r * r) * self.get_height()

    def __str__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def __repl__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

    def __desc__(self):
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'

class Plane3d(_Geometry3d, OpOverloaded):

    def __init__(self,vec1,color=None, texture=None, name="Plane3d"):
        self._vector1 = Vector3d(vec1.get_start(), vec1.get_end())
        tmp_vec, tmp_norm = self.get_perpendicular_vectors(vec1)
        self._vector2 = Vector3d(self._vector1.get_origin(),Point3d(tmp_vec[0], tmp_vec[1], tmp_vec[2]))
        self._normal = Point3d(tmp_norm[0], tmp_norm[1], tmp_norm[2])
        self._col = color
        self._txt = texture
        self._name = name

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_color(self):
        return self._col

    def set_color(self, color):
        self._color = color

    def get_texture(self):
        return self._txt

    def set_teture(self, teture):
        self._txt = teture

    def get_norm(self):
        return self._normal
    
    def set_norm(self, norm):
        self._normal = norm

    def get_vec1(self):
        return self._vector1

    def set_vec1(elf, vector):
        self._vector1 = vector

    def get_vec2(self):
        return self._vector2
    
    def set_vec2(elf, vector):
        self._vector2 = vector
        
    def __str__(self):
        return f"{self.get_name()}:\nVect1:\t{self.get_vec1()}vector2:{self.get_vec2()}normal: {self.get_norm()}color: {self.get_color()}Texture: {self.get_texture()}\n"

    def descr(self):
        return f"{self.get_name()}:\nVect1:\t{self.get_vec1()}vector2:{self.get_vec2()}normal: {self.get_norm()}color: {self.get_color()}Texture: {self.get_texture()}\n"

    def __repr__(self):
        return f"{self.get_name()}:\nVect1:\t{self.get_vec1()}vector2:{self.get_vec2()}normal: {self.get_norm()}color: {self.get_color()}Texture: {self.get_texture()}\n"

class Cube3d(_Geometry3d, OpOverloaded):
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
        self._square1 = square1.deepcopy()
        self._square2 = square2.deepcopy()
        self._square3 = square3.deepcopy()
        self._square4 = square4.deepcopy()
        self._square5 = square5.deepcopy()
        self._square6 = square6.deepcopy()
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

#Rectangle3d = Cube3d

class Sphere3d(_Geometry3d, OpOverloaded):
    """ Sphere3d represents a shpere in 3 dementions
        as arguments it takes a Point3d center ahd a radius. and optionally a name,
        a matrial and a color
    """
    def __init__(self, center, radius, mat=None, color=None,name="Sphere3d"):
        # Stationary Sphere
        self._static_center= center.deepcopy()
        self._radius = max(0,radius)
        self._mat = mat
        self._color = color
        self._name = name  

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
    main()