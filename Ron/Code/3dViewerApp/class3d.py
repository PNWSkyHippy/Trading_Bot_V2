"""Provide 3D geometry classes (points, lines, solids) and a small ray tracer."""

import collections as col
import math
import sys

import numpy as np

from overloaded_inc import OpOverloaded


MAXRAD = 6.28318530717958
MINRAD = 0.01745329251994329

def degtorad(deg):
    """Convert degrees to radians.

    Args:
        deg (float): The angle in degrees.

    Returns:
        float: The angle in radians, or 0 if its magnitude is under 1 degree. Magnitudes are limited to 360 degrees.
    """
    if deg >= 1:
        deg = min(max(deg, 1),360)
    elif deg <= -1:
        deg = max(min(deg, -1), -360)
    else:
        return 0
    return deg * math.pi / 180

def radtodeg(rad):
    """Convert radians to degrees.

    Args:
        rad (float): The angle in radians.

    Returns:
        float: The angle in degrees, or 0 if its magnitude is too small. Magnitudes are limited to 2*pi.
    """
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
    elif isinstance(value, Ray3d):
        components = value.get_direction().get_xyz()
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

def write_color(stdout, pixel_color):
    """Write one pixel color as 0-255 integers to stderr.

    Args:
        stdout (str): Unused; the pixel is written to stderr.
        pixel_color (Point3d): The color, with components in the range 0 to 1.
    """
    r = pixel_color.get_x()
    g = pixel_color.get_y()
    b = pixel_color.get_z()

    # Translate the [0,1] component values to the byte range [0,255].
    rbyte = int(255.999 * r)
    gbyte = int(255.999 * g)
    bbyte = int(255.999 * b)

    #  Write out the pixel color components.
    sys.stderr.write(f'{rbyte} {gbyte} {bbyte}\n')  
    sys.stderr.flush()

def ray_color(r, world):
    """Return the color seen along a ray.

    Args:
        r (Ray3d): The ray being tested.
        world (Hittable): The scene to test the ray against.

    Returns:
        Point3d: A color from the surface normal on a hit, otherwise a sky gradient.
    """
    rec = Hit_Record()
    if world.hit(r, 0, math.inf, rec) and rec.normal is not None:
        N = rec.normal
        return 0.5*Color(N.get_x()+1, N.get_y()+1, N.get_z()+1)

    unit_direction = unit_vector(r.get_direction())
    unit_dir_vec = Point3d(unit_direction.get_direction().get_x(), unit_direction.get_direction().get_y(), unit_direction.get_direction().get_z())
    a = 0.5*(unit_dir_vec.get_y() + 1.0)
    return (1.0-a)*Color(1.0, 1.0, 1.0) + a*Color(0.5, 0.7, 1.0)


def hit_sphere(center, radius,r):

    """Find where a ray meets a sphere.

    Args:
        center (Point3d): The center point.
        radius (float): The radius.
        r (Ray3d): The ray being tested.

    Returns:
        float: The nearest ray parameter, or -1.0 if the ray misses.
    """
    oc = center - r.get_origin()
    a = r.get_direction().len_sqr() #  * r.get_direction()
    h = dot(r.get_direction(), oc)
    c = oc.len_sqr() - radius*radius
    discriminant = h*h - a*c

    if (discriminant < 0):
        return -1.0
    else:
        return (h - math.sqrt(discriminant)) / a
    
class Hit_Record:

    """Hold the details of one ray hit.

    Attributes:
        p (Point3d | None): The hit point.
        normal (Point3d | None): The surface normal facing against the ray.
        t (float): The ray parameter of the hit.
        front_face (bool): Whether the ray hit the outside of the surface.
    """
    def __init__(self, p=None, norm=None, t=0.0, fface=True):
        """Initialize the hit record.

        Args:
            p (Point3d | None): The hit point.
            norm (Point3d | None): The surface normal at the hit.
            t (float): The ray parameter, so the point is origin + t * direction.
            fface (bool): Whether the ray hit the front face.
        """
        self.p = p
        self.normal = norm
        self.t = t
        self.front_face = fface

    def set_face_normal(self, r, outward_normal):
        # Sets the hit record normal vector.
        # NOTE: the parameter `outward_normal` is assumed to have unit length.

        """Set the normal so it always faces against the ray.

        Args:
            r (Ray3d): The ray being tested.
            outward_normal (Point3d): The unit normal pointing out of the surface.
        """
        self.front_face = dot(r.direction, outward_normal) < 0
        self.normal = outward_normal if self.front_face else -1 * outward_normal

    def copy_from(self, other):
        """Copy another record's fields into this one.

        Args:
            other (Hit_Record): The record to copy.
        """
        # Python can't replace the caller's rec, so copy the fields into it
        self.p, self.normal, self.t, self.front_face = other.p, other.normal, other.t, other.front_face


class Hittable:
    """Base class for objects a ray can hit."""
    def __init__(self):
        """Initialize the object."""
        pass

    def hit(self, r, ray_tmin, ray_t_max, rec) -> bool:
        """Test a ray against the object. The base class never hits.

        Args:
            r (Ray3d): The ray being tested.
            ray_tmin (float): The smallest accepted ray parameter.
            ray_t_max (float): The largest accepted ray parameter.
            rec (Hit_Record): Receives the hit details when the ray hits.

        Returns:
            bool: Always False.
        """
        return False

class World3d:

    """Build a camera and viewport and render the default scene."""
    def __init__(self, asp_rat=16.0/9.0,width=400, cam_loc=None,foc_l=1.0, vheight=2.0):
        """Set up the camera and viewport, then render the scene.

        The image is written to stderr as PPM text, and progress is written to stdout.

        Args:
            asp_rat (float): The image aspect ratio (width / height).
            width (int): The image width in pixels.
            cam_loc (Point3d | None): The camera location. Defaults to the origin.
            foc_l (float): The camera focal length.
            vheight (float): The viewport height.
        """
        self._aspect_ratio = (asp_rat)
        self._image_width = width
        self._image_height = int(self._image_width / self._aspect_ratio)
        self._focal_length = foc_l
        self._viewport_height = vheight
        self._viewport_width = self._viewport_height * (float(self._image_width)/self._image_height)
        self._camera_center = cam_loc if cam_loc is not None else Point3d(0,0,0)

        # World
        self._world = Hittable_ObjList()
        self._world.add(Sphere3d(Point3d(0, 0, -1), 0.5))
        self._world.add(Sphere3d(Point3d(0, -100.5, -1), 100))

        # Calculate the vectors across the horizontal and down the vertical viewport edges.
        self._viewport_u = Point3d(self._viewport_width, 0, 0)
        self._viewport_v = Point3d(0, -self._viewport_height, 0)

        #  Calculate the horizontal and vertical delta vectors from pixel to pixel.
        self._pixel_delta_u = self._viewport_u / self._image_width
        self._pixel_delta_v = self._viewport_v / self._image_height

        # Calculate the location of the upper left pixel.
        self._viewport_upper_left = self._camera_center - Point3d(0, 0, self._focal_length) - self._viewport_u/2 - self._viewport_v/2
        self._pixel00_loc = self._viewport_upper_left + 0.5 * (self._pixel_delta_u + self._pixel_delta_v)

        # Render

        sys.stderr.write(f"P3\n{self._image_width} {self._image_height}\n255\n")
        sys.stderr.flush()
        for j  in range(self._image_height):
            sys.stdout.write(f"\rScanlines remaining: ({self._image_height - j})")
            for i  in range(self._image_width):
                self._pixel_center = self._pixel00_loc + (i * self._pixel_delta_u) + (j * self._pixel_delta_v)
                self._ray_direction = self._pixel_center - self._camera_center
                self._r = Ray3d(self._camera_center, self._ray_direction)

                self._pixel_color = ray_color(self._r, self._world)
                write_color("stdout", self._pixel_color);
        
    

        sys.stdout.write("\rDone.                 \n")

class Hittable_ObjList(Hittable): 
  
    """Hold a collection of hittable objects and report the closest hit."""
    def __init__(self):
        """Initialize an empty list."""
        self._objects = col.deque(maxlen=10000)

    def clear(self): 
        """Remove every object."""
        self._objects.clear()

    def add(self, object):
        """Add an object to the list.

        Args:
            object (Hittable): The object to add.
        """
        self._objects.append(object)


    def hit(self, r, ray_tmin, ray_t_max, rec) -> bool:
        """Find the closest hit among all objects.

        Args:
            r (Ray3d): The ray being tested.
            ray_tmin (float): The smallest accepted ray parameter.
            ray_t_max (float): The largest accepted ray parameter.
            rec (Hit_Record): Receives the hit details when the ray hits.

        Returns:
            bool: True if any object is hit. ``rec`` holds the closest hit.
        """
        temp_rec = Hit_Record()
        hit_anything = False
        closest_so_far = ray_t_max

        for obj in self._objects: 
            if (obj.hit(r, ray_tmin, closest_so_far, temp_rec)):
                hit_anything = True
                closest_so_far = temp_rec.t
                rec.copy_from(temp_rec)

        return hit_anything
    

class Ray3d:

    """Represent a ray with an origin and a direction."""
    def __init__(self, origin, direction):
        """Initialize the ray with copies of its origin and direction.

        Args:
            origin (Point3d): The starting point.
            direction (Point3d): The direction.
        """
        self._origin = origin.deepcopy()
        self._direction = direction.deepcopy()

    def get_origin(self):
        """Return the ray's origin.

        Returns:
            Point3d: The origin.
        """
        return self._origin

    def set_origin(self, orig):
        """Set the ray's origin.

        Args:
            orig (Point3d): The new origin.
        """
        self._origin = orig

    @property
    def origin(self):
        """Return the ray's origin.

        Returns:
            Point3d: The origin.
        """
        return self._origin

    @origin.setter
    def origin(self, orig):
        """Set the ray's origin.

        Args:
            orig (Point3d): The new origin.
        """
        self._origin = orig

    def get_direction(self):
        """Return the ray's direction.

        Returns:
            Point3d: The direction.
        """
        return self._direction

    def set_direction(self, dir):
        """Set the ray's direction.

        Args:
            dir (Point3d): The new direction.
        """
        self._direction = dir

    @property
    def direction(self):
        """Return the ray's direction.

        Returns:
            Point3d: The direction.
        """
        return self._direction

    @direction.setter
    def direction(self, dest):
        """Set the ray's direction.

        Args:
            dest (Point3d): The new direction.
        """
        self._direction = dest

    def at(self, t):
        """Return the point at a given distance parameter along the ray.

        Args:
            t (float): The ray parameter, so the point is origin + t * direction.

        Returns:
            Point3d: origin + t * direction.
        """
        return self.get_origin() + ( t * self.get_direction())

class Point3d(OpOverloaded):
    """Store and manipulate a 3d X,Y,Z coordinate
    methods: get_x, get_y, get_z return x,y,or z
    move(newx,newy,newz) translates x+newx,y+newy,z+newz

    """

    # intitialie and store x,y, z
    def __init__(self, x, y, z, color=None,name="Point3d"):
        """Initialize the point.

        Args:
            x (float): The X coordinate.
            y (float): The Y coordinate.
            z (float): The Z coordinate.
            color (object): Accepted but unused.
            name (str): The name.
        """
        self._x = x
        self._y = y
        self._z = z
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def deepcopy(self):
        """Return a new point with the same coordinates.

        Returns:
            Point3d: The copy.
        """
        return Point3d(self.get_x(), self.get_y(), self.get_z())
    
    def copy(self):
        """Return a new point with the same coordinates.

        Returns:
            Point3d: The copy.
        """
        return Point3d(self.get_x(), self.get_y(), self.get_z())

    def set_x(self, val):
        """Set the X coordinate.

        Args:
            val (float): The new value.
        """
        self._x  = val

    # Report x
    def get_x(self):
        """Return the X coordinate.

        Returns:
            float: The X coordinate.
        """
        return self._x

    def len_sqr(self):
        """Return the squared distance from the origin.

        Returns:
            float: x*x + y*y + z*z.
        """
        xx = self.get_x()
        yy = self.get_y()
        zz = self.get_z()
        return xx * xx + yy * yy + zz * zz

    @property
    def x(self):
        """Return the X coordinate.

        Returns:
            float: The X coordinate.
        """
        return self._x

    @x.setter
    def x(self, val):
        """Set the X coordinate.

        Args:
            val (float): The new value.
        """
        self._x = val

    def set_y(self, val):
        """Set the Y coordinate.

        Args:
            val (float): The new value.
        """
        self._y = val

    # Report y
    def get_y(self):
        """Return the Y coordinate.

        Returns:
            float: The Y coordinate.
        """
        return self._y

    @property
    def y(self):
        """Return the Y coordinate.

        Returns:
            float: The Y coordinate.
        """
        return self._y

    @y.setter
    def y(self, val):
        """Set the Y coordinate.

        Args:
            val (float): The new value.
        """
        self._y = val

    def set_z(self, val):
        """Set the Z coordinate.

        Args:
            val (float): The new value.
        """
        self._z = val

    def get_z(self):
        """Return the Z coordinate.

        Returns:
            float: The Z coordinate.
        """
        return self._z

    @property
    def z(self):
        """Return the Z coordinate.

        Returns:
            float: The Z coordinate.
        """
        return self._z

    @z.setter
    def z(self, val):
        """Set the Z coordinate.

        Args:
            val (float): The new value.
        """
        self._z = val

    def get_xyz(self):
        """Return all three coordinates.

        Returns:
            tuple[float, float, float]: The X, Y and Z values.
        """
        return (self._x, self._y, self._z)

    def set_xyz(self, newx, newy, newz):
        """Set all three coordinates.

        Args:
            newx (float): The new X coordinate.
            newy (float): The new Y coordinate.
            newz (float): The new Z coordinate.

        Returns:
            Point3d: This point, to allow chaining.
        """
        self._x = newx
        self._y = newy
        self._z = newz
        return self

    # translate x,y,z to new x,y,z
    def move(self, dx, dy, dz):
        """Translate the point in place.

        Args:
            dx (float): The distance to move along X.
            dy (float): The distance to move along Y.
            dz (float): The distance to move along Z.

        Returns:
            Point3d: This point, to allow chaining.
        """
        self._x = self._x + dx
        self._y = self._y + dy
        self._z = self._z + dz
        return self

    # Return state of point object
    def __str__(self):
        """Return the point's name and coordinates.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def descr(self):
        """Return a text description of the object.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def __repr__(self):
        """Return a text representation of the object.

        Returns:
            str: The representation.
        """
        return f"{self.get_name()}:Point3D(x={self._x:.2f},y={self._y:.2f},z={self._z:.2f})\n"

    def __neg__(self):
        """Return the negated coordinates.

        Returns:
            tuple[float, float, float]: The negated X, Y and Z values.
        """
        return -self._x, -self._y, -self._z

    def __iadd__(self, other):
        """Add a scalar or point to this point in place.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: This point.
        """
        if isinstance(other, (int, float)):
            self._x += other
            self._y += other
            self._z += other
        else:
            self._x += other.get_x()
            self._y += other.get_y()
            self._z += other.get_z()
        return self

    def __imul__(self, other):

        """Multiply this point by a scalar or point in place.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: This point.
        """
        if isinstance(other, (int, float)):
            self._x *= other
            self._y *= other
            self._z *= other
        else:
            self._x *= other.get_x()
            self._y *= other.get_y()
            self._z *= other.get_z()
        return self

    def __itruediv__(self, other):
        """Divide this point by a scalar in place.

        Args:
            other (int | float): The divisor.

        Returns:
            Point3d: This point.
        """
        return self.__imul__(1 / other)

    def __add__(self, other):
        """Return a new point with a scalar or point added.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: The sum.
        """
        if isinstance(other, (int, float)):
            return Point3d(self._x + other, self._y + other, self._z + other)
        else:
            return Point3d(self._x + other.get_x(), self._y + other.get_y(), self._z + other.get_z())

    def __sub__(self, other):
        """Return a new point with a scalar or point subtracted.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: The difference.
        """
        if isinstance(other, (int, float)):
            return Point3d(self._x - other, self._y - other, self._z - other)
        else:
            return Point3d(self._x - other.get_x(), self._y - other.get_y(), self._z - other.get_z())

    def __mul__(self, other):
        """Return a new point multiplied by a scalar or point, rounded to 2 decimals.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: The product.
        """
        if isinstance(other, (int, float)):
            return Point3d(
                round((self._x * other),2), round((self._y * other),2), round((self._z * other),2)
            )
        else:
            return Point3d(round((self._x * other.get_x()),2), round((self._y * other.get_y()),2), round((self._z * other.get_z()),2))

    def __rmul__(self, other):
        """Return a new point multiplied by a scalar or point, rounded to 2 decimals.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: The product.
        """
        if isinstance(other, (int, float)):
            return Point3d(round((other * self._x),2), round((other * self._y),2), round((other * self._z),2))
        else:
            return Point3d(round((other.get_x() * self._x),2), round((other.get_y() * self._y),2), round((other.get_z() * self._z),2))

    def __truediv__(self, other):
        """Return a new point divided by a scalar or point, rounded to 2 decimals.

        Args:
            other (int | float | Point3d): A scalar applied to every coordinate, or a point applied component-wise.

        Returns:
            Point3d: The quotient.
        """
        if isinstance(other, (int, float)):
            return Point3d(round(((1 / other) * self._x),2), round(((1 / other) * self._y),2), round(((1 / other) * self._z),2))
        else:
            return Point3d(round(((1 / other.get_x()) * self._x),2), round(((1 / other.get_y()) * self._y),2), round(((1 / other.get_z()) * self._z),2))


    def xrot(self, angle_rad, pivot=None):
        """Rotate in place about X through pivot (default: world origin).

        pivot accepts Point3d, an (x, y, z) sequence, or "center".
        Angles are radians; returns self. A point's own center is itself.
        """
        _px, py, pz = _rotation_pivot(pivot, self)
        # Subtract the pivot, rotate relative coordinates, then add it back.
        y, z = self._y - py, self._z - pz
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(self._x, py + y * cos_a - z * sin_a,
                     pz + y * sin_a + z * cos_a)
        return self

    def yrot(self, angle_rad, pivot=None):
        """Rotate in place about Y through pivot; see xrot for pivot options."""
        _px, _py, pz = _rotation_pivot(pivot, self)
        x, z = self._x - _px, self._z - pz
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(_px + x * cos_a + z * sin_a, self._y,
                     pz - x * sin_a + z * cos_a)
        return self

    def zrot(self, angle_rad, pivot=None):
        """Rotate in place about Z through pivot; see xrot for pivot options."""
        _px, _py, _pz = _rotation_pivot(pivot, self)
        x, y = self._x - _px, self._y - _py
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        self.set_xyz(_px + x * cos_a - y * sin_a,
                     _py + x * sin_a + y * cos_a, self._z)
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

Color = Point3d

class ColoredPixel(Point3d):
    """Store and manipulate a 3d colored pixel
    adds color to a Point3d object it contains
    methods:
    set_color and get_color as well as al Point3d methods
    """

    # Initialize, store x,y,z in Point3d and color locally
    def __init__(self, x, y, z, color,name="ColoredPixel"):
        """Initialize the colored pixel.

        Args:
            x (float): The X coordinate.
            y (float): The Y coordinate.
            z (float): The Z coordinate.
            color (object): The color.
            name (str): The name.
        """
        super().__init__(x, y, z)  # initialize parent Point3d
        self._color = color
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    # Change color of pixel
    def set_color(self, color):
        """Set the color.

        Args:
            color (object): The color.
        """
        self._color = color

    # Report current color
    def get_color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    @property
    def color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    @color.setter
    def color(self, val):
        """Set the color.

        Args:
            val (object): The new color.
        """
        self._color = val

    def __str__(self):
        """Return the pixel's name, coordinates and color.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    # Return state of ColoredPixel object
    def descr(self):
        """Return the pixel's name, coordinates and color.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"

    def __repr__(self):
        """Return the pixel's name, coordinates and color.

        Returns:
            str: The representation.
        """
        return f"{self.get_name()}:ColoredPixel(x={self._x:.2f}, y={self._y:.2f}, z={self._z:.2f}, color={self._color})\n"


class _Geometry3d:
    """Common in-place transforms for shapes made from Point3d objects."""

    def _points(self):
        """Return the Point3d instances that make up this geometry."""
        raise NotImplementedError("Geometry subclasses must implement _points().")

    @property
    def _center(self):
        """Return the average of the shape's points.

        Returns:
            Point3d: The center, calculated on each access.
        """
        # Calculate on access so editing a child point cannot leave stale data.
        points = self._points()
        count = len(points)
        return Point3d(*(sum(p.get_xyz()[axis] for p in points) / count
                         for axis in range(3)))

    def get_center(self):
        """Return the current midpoint or geometric center."""
        return self._center

    def _transform(self, method, *args):
        """Call one Point3d method on each distinct point of the shape.

        Args:
            method (str): Name of the Point3d method to call on each point.
            *args (object): Arguments passed to that method.

        Returns:
            _Geometry3d: This shape.
        """
        # Faces can share edges. Transform each actual point only once.
        points = {id(point): point for point in self._points()}
        for point in points.values():
            getattr(point, method)(*args)
        return self

    def move(self, dx, dy, dz):
        """Translate the shape in place.

        Args:
            dx (float): The distance to move along X.
            dy (float): The distance to move along Y.
            dz (float): The distance to move along Z.

        Returns:
            _Geometry3d: This shape.
        """
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

        """Find two unit vectors perpendicular to a vector.

        Args:
            v (Line3d): A vector whose end point gives the direction.

        Returns:
            tuple[numpy.ndarray, numpy.ndarray]: A unit vector perpendicular to ``v`` and the unit normal to both.
        """
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


class Prism3d(_Geometry3d):
    """Regular N-sided prism stored as three real Point3d objects so move/rot/scale work.

    _center_point (bottom base center), _edge (one bottom vertex) and _top
    (top base center = center + unit normal * height) are the only stored
    geometry; radius, side length, normal, vertices, area and volume are
    derived on every call so they can never go stale after a transform.
    """
    def __init__(self, center_point, edge_point, num_faces, height, bc="blue", fc="green", name="Prism3d", normal=None):
        """
        Defines a generic regular N-sided 3D Prism.

        :param center_point: Point3d representing the center of the bottom polygon base.
        :param edge_point: Point3d representing one vertex on the outer edge of the bottom base.
                           (Establishes both the radius and the starting rotation angle).
        :param num_faces: int, number of sides/faces (e.g., 6 for Hexagonal, 8 for Octagonal).
        :param height: float, the straight extrusion height along the base normal.
        :param normal: optional extrusion direction (3 numbers); None = as close to world +Z
                       as possible while staying perpendicular to the radius.
        """
        if int(num_faces) < 3:
            raise ValueError("Prism3d needs at least 3 faces.")
        self._num_faces = int(num_faces)
        self._center_point = center_point.copy()
        self._edge = edge_point.copy()
        radial = self._xyz(self._edge) - self._xyz(self._center_point)
        if np.linalg.norm(radial) == 0:
            raise ValueError("Edge point cannot be identical to center point.")
        u = radial / np.linalg.norm(radial)
        if normal is not None:
            norm = np.array(normal, dtype=float)
        else:
            # World up with the radial part removed; fall back to Y if the radius points up.
            up = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
            norm = up - np.dot(up, u) * u
        # Keep the normal square to the base even if the caller's isn't.
        norm = norm - np.dot(norm, u) * u
        if np.linalg.norm(norm) == 0:
            raise ValueError("Prism3d normal cannot be zero or parallel to the radius.")
        norm = norm / np.linalg.norm(norm)
        self._top = Point3d(*(self._xyz(self._center_point) + norm * float(height)))
        # Custom overrides for length and width (optional manual settings)
        self._custom_length = None
        self._custom_width = None
        self._border_col = bc
        self._fill_col = fc
        self._name = name
        self._Istlink = False
        self._list_name = None

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to test.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    # Names of the stored Point3d attributes; subclasses add to this tuple.
    _point_attrs = ("_center_point", "_edge", "_top")

    def _points(self):
        """Return the stored base center, edge and top points.

        Returns:
            list[Point3d]: The stored points.
        """
        return [getattr(self, a) for a in self._point_attrs]

    def _get_base_geometry(self):
        """
        Helper method to extract the base area and perimeter.
        """
        radius = self.get_radius()
        N = self._num_faces

        # 1. Area of a regular N-sided polygon using circumradius (r)
        base_area = 0.5 * N * (radius ** 2) * np.sin(2 * np.pi / N)

        # 2. Perimeter from the side length
        perimeter = N * self.get_length()

        return base_area, perimeter

    def get_volume(self):
        """
        Calculates the 3D volume of the prism.
        Works universally for 3-sided up to N-sided prisms.
        """
        base_area, _ = self._get_base_geometry()
        return float(base_area * self.get_height())

    def get_area(self):
        """
        Calculates the total surface area (Top Base + Bottom Base + Lateral Sides).
        """
        base_area, perimeter = self._get_base_geometry()

        # Lateral surface area is the perimeter wrapped along the extrusion height
        lateral_area = perimeter * self.get_height()

        # Total Surface Area = Both flat ends + the side walls
        return float((2 * base_area) + lateral_area)

    def get_base_area(self):
        """Return the area of the base polygon.

        Returns:
            float: The base area.
        """
        return float(self._get_base_geometry()[0])

    def get_perimeter(self):
        """Return the perimeter of the base polygon.

        Returns:
            float: The perimeter.
        """
        return float(self._get_base_geometry()[1])

    def len_sqr(self):
        """Squared radius (center to edge vertex)."""
        xx = self._edge.get_x() - self._center_point.get_x()
        yy = self._edge.get_y() - self._center_point.get_y()
        zz = self._edge.get_z() - self._center_point.get_z()
        return xx * xx + yy * yy + zz * zz

    def get_radius(self):
        """Circumradius: base center to a vertex."""
        return math.sqrt(self.len_sqr())

    def get_apothem(self):
        """Inradius: base center to the middle of a side."""
        return self.get_radius() * math.cos(math.pi / self._num_faces)

    def get_length(self):
        """Length of one side (edge) of the base polygon."""
        if self._custom_length is not None:
            return self._custom_length
        return 2 * self.get_radius() * math.sin(math.pi / self._num_faces)

    def set_length(self, new_len):
        """Resize the base so each side is new_len long (keeps center, direction and height)."""
        self.set_radius(new_len / (2 * math.sin(math.pi / self._num_faces)))

    def get_width(self):
        """Widest distance across the base: the longest corner-to-corner diagonal (= 2r for even N)."""
        if self._custom_width is not None:
            return self._custom_width
        N = self._num_faces
        return 2 * self.get_radius() * math.sin((N // 2) * math.pi / N)

    def get_width_flats(self):
        """Across the base from a side: side to opposite side (even N), corner to opposite side (odd N)."""
        if self._num_faces % 2 == 0:
            return 2 * self.get_apothem()
        return self.get_radius() + self.get_apothem()

    def set_radius(self, new_r):
        """Resize the base so the center-to-vertex distance is the given radius.

        Args:
            new_r (float): The new radius.
        """
        c = self._xyz(self._center_point)
        v1 = self._xyz(self._edge) - c
        self._edge.set_xyz(*(c + v1 / np.linalg.norm(v1) * new_r))

    def get_norm(self):
        """Unit extrusion normal (bottom center -> top center) as a numpy array."""
        n = self._xyz(self._top) - self._xyz(self._center_point)
        length = np.linalg.norm(n)
        if length == 0:
            raise ValueError("Prism3d has zero height, so no normal.")
        return n / length

    def pr_norm(self):
        """Return the unit extrusion normal as a Point3d.

        Returns:
            Point3d: The unit normal.
        """
        n = self.get_norm()
        return Point3d(n[0], n[1], n[2])

    def get_face_normals(self):
        """Outward unit normal of every face, in get_faces() order (bottom, top, side0 .. sideN-1)."""
        pts = [self._xyz(p) for p in self.get_points()]
        normals = []
        for face in self.get_faces():
            # Newell's method: works for any flat polygon wound counter-clockwise from outside.
            n = np.zeros(3)
            for i in range(len(face)):
                cur, nxt = pts[face[i]], pts[face[(i + 1) % len(face)]]
                n += np.cross(cur, nxt)
            normals.append(Point3d(*(n / np.linalg.norm(n))))
        return normals

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_center(self):
        """Center of the bottom base."""
        return self._center_point

    def set_center(self, new_c):
        """Move the whole prism so its bottom center lands on a point.

        Args:
            new_c (Point3d): The new center.
        """
        # Move the whole shape so its bottom center lands on new_c.
        d = self._xyz(new_c) - self._xyz(self._center_point)
        self.move(*d)

    def get_mid(self):
        """Middle of the solid (halfway between the two base centers)."""
        return Point3d(*((self._xyz(self._center_point) + self._xyz(self._top)) / 2))

    def get_top(self):
        """Center of the top base."""
        return self._top

    def get_edge(self):
        """Return the base vertex point that sets the radius and rotation.

        Returns:
            Point3d: The edge point.
        """
        return self._edge

    def set_edge(self, edge):
        """Move the starting vertex, keeping it on the base plane.

        Args:
            edge (Point3d): The edge point.

        Raises:
            ValueError: If the point lies on the prism axis.
        """
        # Edge is the starting vertex: keep it on the base plane and square to the normal.
        n = self.get_norm()
        c = self._xyz(self._center_point)
        v = self._xyz(edge) - c
        v = v - np.dot(v, n) * n
        if np.linalg.norm(v) == 0:
            raise ValueError("Edge point cannot be on the prism axis.")
        self._edge.set_xyz(*(c + v))

    def get_num_faces(self):
        """Return the number of side faces.

        Returns:
            int: The side count.
        """
        return self._num_faces

    def set_num_faces(self, num_faces):
        """Set the number of side faces.

        Args:
            num_faces (int): The new side count (at least 3).

        Raises:
            ValueError: If fewer than 3 faces are requested.
        """
        if int(num_faces) < 3:
            raise ValueError("Prism3d needs at least 3 faces.")
        self._num_faces = int(num_faces)

    def get_height(self):
        """Return the distance between the two base centers.

        Returns:
            float: The height.
        """
        return float(np.linalg.norm(self._xyz(self._top) - self._xyz(self._center_point)))

    def set_height(self, height):
        """Move the top base to the given height along the normal.

        Args:
            height (float): The height.
        """
        self._top.set_xyz(*(self._xyz(self._center_point) + self.get_norm() * float(height)))

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_points(self):
        """
        Vertex list built fresh from the stored points:
        bottom ring = indices 0..N-1, top ring = N..2N-1 (top i sits above bottom i).
        """
        c = self._xyz(self._center_point)
        radial = self._xyz(self._edge) - c
        n = self.get_norm()
        # Second in-plane axis, so the ring is square to the normal.
        v = np.cross(n, radial)
        extrude = self._xyz(self._top) - c
        N = self._num_faces
        bottom, top = [], []
        for i in range(N):
            angle = (2 * np.pi * i) / N
            p = c + radial * np.cos(angle) + v * np.sin(angle)
            bottom.append(Point3d(*p))
            top.append(Point3d(*(p + extrude)))
        return bottom + top

    def get_faces(self):
        """
        Face index lists into get_points(): [bottom cap, top cap, side0 .. sideN-1].
        Each face winds counter-clockwise when seen from outside.
        """
        N = self._num_faces
        faces = [tuple(range(N - 1, -1, -1)), tuple(range(N, 2 * N))]
        for i in range(N):
            next_i = (i + 1) % N
            # v1: bottom current, v2: bottom next, v3: top next, v4: top current
            faces.append((i, next_i, next_i + N, i + N))
        return faces

    def _clone(self, points):
        """Return a shallow clone that uses the given points.

        Args:
            points (list[Point3d]): The points to store, in the order of the point attributes.

        Returns:
            Prism3d: A clone of the same class.
        """
        # Same subclass, same settings; caller decides whether the points are shared or new.
        new = self.__class__.__new__(self.__class__)
        new.__dict__.update(self.__dict__)
        for attr, point in zip(self._point_attrs, points):
            setattr(new, attr, point)
        return new

    def truncate(self, top_scale=0.5, name=None):
        """New TruncatedPrism3d with this prism's base, height and sides; top = top_scale * base size."""
        return TruncatedPrism3d(self._center_point, self._edge, self._num_faces, self.get_height(),
                                top_scale, self._border_col, self._fill_col,
                                name or self._name, normal=self.get_norm())

    def deepcopy(self):
        """Independent prism: moving the copy never moves the original."""
        return self._clone([p.deepcopy() for p in self._points()])

    def copy(self):
        """Same as deepcopy, like Point3d.copy: a shared point would make the copy drag the original."""
        return self.deepcopy()

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    def set_bc(self, bc):
        """Set the border color.

        Args:
            bc (object): The new border color.
        """
        self._border_col = bc

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def set_fc(self, fc):
        """Set the fill color.

        Args:
            fc (object): The new fill color.
        """
        self._fill_col = fc

    def fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    def __str__(self):
        """Return the prism's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tedge={self.get_edge()}\tfaces={self.get_num_faces()}, length={self.get_length():.2f}, width={self.get_width():.2f}, height={self.get_height():.2f}, volume={self.get_volume():.2f}, area={self.get_area():.2f}\n\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}\n'

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()

class TrianglePrism3d(Prism3d):
    """Prism with 3 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="TrianglePrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 3 sides
        super().__init__(center_point, edge_point, num_faces=3, height=height, bc=bc, fc=fc, name=name, normal=normal)


class QuadrangularPrism3d(Prism3d):
    """Prism with 4 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="QuadrangularPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 4 sides
        super().__init__(center_point, edge_point, num_faces=4, height=height, bc=bc, fc=fc, name=name, normal=normal)

class PentagonalPrism3d(Prism3d):
    """Prism with 5 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="PentagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 5 sides
        super().__init__(center_point, edge_point, num_faces=5, height=height, bc=bc, fc=fc, name=name, normal=normal)

class HexagonalPrism3d(Prism3d):
    """Prism with 6 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="HexagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 6 sides
        super().__init__(center_point, edge_point, num_faces=6, height=height, bc=bc, fc=fc, name=name, normal=normal)

class OctagonalPrism3d(Prism3d):
    """Prism with 8 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="OctagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 8 sides
        super().__init__(center_point, edge_point, num_faces=8, height=height, bc=bc, fc=fc, name=name, normal=normal)

class NonagonalPrism3d(Prism3d):
    """Prism with 9 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="NonagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 9 sides
        super().__init__(center_point, edge_point, num_faces=9, height=height, bc=bc, fc=fc, name=name, normal=normal)

class DecagonalPrism3d(Prism3d):
    """Prism with 10 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="DecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 10 sides
        super().__init__(center_point, edge_point, num_faces=10, height=height, bc=bc, fc=fc, name=name, normal=normal)

class HendecagonalPrism3d(Prism3d):
    """Prism with 11 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="HendecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 11 sides
        super().__init__(center_point, edge_point, num_faces=11, height=height, bc=bc, fc=fc, name=name, normal=normal)

class DodecagonalPrism3d(Prism3d):
    """Prism with 12 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="DodecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 12 sides
        super().__init__(center_point, edge_point, num_faces=12, height=height, bc=bc, fc=fc, name=name, normal=normal)

class TridecagonalPrism3d(Prism3d):
    """Prism with 13 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="TridecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 13 sides
        super().__init__(center_point, edge_point, num_faces=13, height=height, bc=bc, fc=fc, name=name, normal=normal)

class TetraDecagonalPrism3d(Prism3d):
    """Prism with 14 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="TetraDecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 14 sides
        super().__init__(center_point, edge_point, num_faces=14, height=height, bc=bc, fc=fc, name=name, normal=normal)

class PentaDecagonalPrism3d(Prism3d):
    """Prism with 15 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="PentaDecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 15 sides
        super().__init__(center_point, edge_point, num_faces=15, height=height, bc=bc, fc=fc, name=name, normal=normal)

class HexadecagonalPrism3d(Prism3d):
    """Prism with 16 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="HexadecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 16 sides
        super().__init__(center_point, edge_point, num_faces=16, height=height, bc=bc, fc=fc, name=name, normal=normal)

class HeptadecagonalPrism3d(Prism3d):
    """Prism with 17 side faces."""
    def __init__(self, center_point, edge_point, height , bc="blue", fc="green", name="HeptadecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 17 sides
        super().__init__(center_point, edge_point, num_faces=17, height=height, bc=bc, fc=fc, name=name, normal=normal)

class OctadecagonalPrism3d(Prism3d):
    """Prism with 18 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="OctadecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 18 sides
        super().__init__(center_point, edge_point, num_faces=18, height=height, bc=bc, fc=fc, name=name, normal=normal)

class EnneadecagonalPrism3d(Prism3d):
    """Prism with 19 side faces."""
    def __init__(self, center_point, edge_point, height, bc="blue", fc="green", name="EnneadecagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 19 sides
        super().__init__(center_point, edge_point, num_faces=19, height=height, bc=bc, fc=fc, name=name, normal=normal)

class IcosagonalPrism3d(Prism3d):
    """Prism with 20 side faces."""
    def __init__(self, center_point, edge_point, height , bc="blue", fc="green", name="IcosagonalPrism3d", normal=None):   
        """Initialize the prism.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The extrusion height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        # Enforces exactly 20 sides
        super().__init__(center_point, edge_point, num_faces=20, height=height, bc=bc, fc=fc, name=name, normal=normal)


class TruncatedPrism3d(Prism3d):
    """Regular N-sided frustum: a pyramid with its point cut off flat.

    The top is the base polygon shrunk by top_scale (0.5 = half size), centered
    over the base and turned the same way. top_scale 0 gives a full pyramid,
    1 gives a plain prism, above 1 flares out. Any Prism3d can make one with
    prism.truncate(top_scale).
    Stored points: base center, base edge vertex, top center, top edge vertex.
    """
    _point_attrs = Prism3d._point_attrs + ("_top_edge",)

    def __init__(self, center_point, edge_point, num_faces, height, top_scale=0.5,
                 bc="blue", fc="green", name="TruncatedPrism3d", normal=None):
        """Initialize the frustum.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            num_faces (int): The number of side faces.
            height (float): The height.
            top_scale (float): The top size as a fraction of the base size. Must not be negative.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.

        Raises:
            ValueError: If ``top_scale`` is negative.
        """
        super().__init__(center_point, edge_point, num_faces, height, bc, fc, name, normal)
        if top_scale < 0:
            raise ValueError("top_scale cannot be negative.")
        radial = self._xyz(self._edge) - self._xyz(self._center_point)
        self._top_edge = Point3d(*(self._xyz(self._top) + radial * float(top_scale)))

    def is_pointed(self):
        """True when the top has shrunk to a single apex point."""
        return self.get_top_radius() < 1e-12

    def get_top_edge(self):
        """Return the vertex point on the top polygon.

        Returns:
            Point3d: The top edge point.
        """
        return self._top_edge

    def get_top_radius(self):
        """Return the top polygon's circumradius.

        Returns:
            float: The top radius.
        """
        return float(np.linalg.norm(self._xyz(self._top_edge) - self._xyz(self._top)))

    def set_top_radius(self, new_r):
        """Set the top polygon's circumradius.

        Args:
            new_r (float): The new top radius.
        """
        self.set_top_scale(new_r / self.get_radius())

    def get_top_scale(self):
        """Return the top size as a fraction of the base size.

        Returns:
            float: The top radius divided by the base radius.
        """
        return self.get_top_radius() / self.get_radius()

    def set_top_scale(self, top_scale):
        """Set the top size as a fraction of the base size.

        Args:
            top_scale (float): The top size as a fraction of the base size. Must not be negative.

        Raises:
            ValueError: If ``top_scale`` is negative.
        """
        if top_scale < 0:
            raise ValueError("top_scale cannot be negative.")
        radial = self._xyz(self._edge) - self._xyz(self._center_point)
        self._top_edge.set_xyz(*(self._xyz(self._top) + radial * float(top_scale)))

    def get_top_length(self):
        """Side length of the top polygon."""
        return 2 * self.get_top_radius() * math.sin(math.pi / self._num_faces)

    def get_top_area(self):
        """Return the area of the top polygon.

        Returns:
            float: The top area.
        """
        r2 = self.get_top_radius()
        return float(0.5 * self._num_faces * r2 * r2 * math.sin(2 * math.pi / self._num_faces))

    def get_slant_height(self):
        """Height of one side face, measured up its middle."""
        drop = self.get_apothem() - self.get_top_radius() * math.cos(math.pi / self._num_faces)
        return math.sqrt(self.get_height() ** 2 + drop ** 2)

    def get_volume(self):
        """Return the volume of the frustum.

        Returns:
            float: The volume.
        """
        a1, a2 = self.get_base_area(), self.get_top_area()
        return float(self.get_height() / 3 * (a1 + a2 + math.sqrt(a1 * a2)))

    def get_area(self):
        """Return the total surface area.

        Returns:
            float: The two ends plus the side faces.
        """
        # Both ends + N trapezoid sides (triangles when pointed).
        lateral = self._num_faces * 0.5 * (self.get_length() + self.get_top_length()) * self.get_slant_height()
        return float(self.get_base_area() + self.get_top_area() + lateral)

    def get_width(self):
        """Widest distance across the wider end."""
        if self._custom_width is not None:
            return self._custom_width
        N = self._num_faces
        return 2 * max(self.get_radius(), self.get_top_radius()) * math.sin((N // 2) * math.pi / N)

    def set_height(self, height):
        """Set the height, carrying the top edge point with the top.

        Args:
            height (float): The height.
        """
        offset = self._xyz(self._top_edge) - self._xyz(self._top)
        super().set_height(height)
        self._top_edge.set_xyz(*(self._xyz(self._top) + offset))

    def set_edge(self, edge):
        """Move the starting vertex, turning the top with the base.

        Args:
            edge (Point3d): The edge point.
        """
        # Turn the top with the base so the sides stay flat.
        scale = self.get_top_scale()
        super().set_edge(edge)
        self.set_top_scale(scale)

    def set_radius(self, new_r):
        """Resize the base while keeping the top the same actual size.

        Args:
            new_r (float): The new radius.
        """
        # Resizing the base keeps the top the same actual size.
        top_r = self.get_top_radius()
        super().set_radius(new_r)
        self.set_top_radius(top_r)

    def get_points(self):
        """
        Bottom ring = 0..N-1, top ring = N..2N-1 (top i sits above bottom i).
        When pointed, the top ring is replaced by a single apex at index N.
        """
        bottom = super().get_points()[:self._num_faces]
        if self.is_pointed():
            return bottom + [self._top.deepcopy()]
        c = self._xyz(self._top)
        radial = self._xyz(self._top_edge) - c
        v = np.cross(self.get_norm(), radial)
        N = self._num_faces
        top = [Point3d(*(c + radial * np.cos(2 * np.pi * i / N) + v * np.sin(2 * np.pi * i / N)))
               for i in range(N)]
        return bottom + top

    def get_faces(self):
        """[bottom cap, top cap, side0 .. sideN-1]; when pointed: [bottom cap, triangle0 .. triangleN-1]."""
        if not self.is_pointed():
            return super().get_faces()
        N = self._num_faces
        faces = [tuple(range(N - 1, -1, -1))]
        for i in range(N):
            faces.append((i, (i + 1) % N, N))
        return faces

    def __str__(self):
        """Return the frustum's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tedge={self.get_edge()}\tfaces={self.get_num_faces()}, length={self.get_length():.2f}, top_length={self.get_top_length():.2f}, width={self.get_width():.2f}, height={self.get_height():.2f}, volume={self.get_volume():.2f}, area={self.get_area():.2f}\n\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}\n'


class Pyramid3d(TruncatedPrism3d):
    """Pointed pyramid (square base by default; num_faces=3 gives a triangular one)."""
    def __init__(self, center_point, edge_point, height, num_faces=4, bc="blue", fc="green",
                 name="Pyramid3d", normal=None):
        """Initialize the pyramid.

        Args:
            center_point (Point3d): The center of the bottom base.
            edge_point (Point3d): A vertex on the outer edge of the bottom base.
            height (float): The height.
            num_faces (int): The number of base sides. Defaults to 4.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        super().__init__(center_point, edge_point, num_faces, height, 0.0, bc, fc, name, normal)

    def get_apex(self):
        """Return the apex point.

        Returns:
            Point3d: The apex.
        """
        return self._top



class ObjGroup3d( _Geometry3d, OpOverloaded):
    """Group objects so they can be moved, rotated and scaled together."""
    def __init__(self, nam=None):
        """Initialize an empty group.

        Args:
            nam (str | None): The name.
        """
        self._objects = col.deque(maxlen=10000)
        self._name = nam
        self._objlen = 0

    def addobj(self, obj):
        """Add an object to the group and link it to the group's name.

        Args:
            obj (object): The object.

        Returns:
            bool: Always True.
        """
        obj._Istlink = True
        obj._list_name = self._name
        self._objects.append(obj)
        self._objlen += 1
        return True

    def len(self):
        """Return the number of objects in the group.

        Returns:
            int: The object count.
        """
        return self._objlen

    def _points(self):
        """Return every point of every member.

        Returns:
            list[Point3d]: The combined points.
        """
        points = []
        for obj in self._objects:
            if isinstance(obj, Point3d):
                points.append(obj)
            elif isinstance(obj, _Geometry3d):
                points.extend(obj._points())
        return points

    def remobj(self, obj):
        """Remove an object, found by identity.

        Args:
            obj (object): The object.

        Returns:
            bool | str: True if removed, otherwise a message saying the object is not in the list.
        """
        # Find by identity: OpOverloaded makes every object == every other one.
        idx = self.get_idx(obj)
        if idx < 0:
            return f'ValueError:  {obj} not in list'
        del self._objects[idx]
        obj._Istlink = False
        obj._list_name = None
        self._objlen -= 1
        return True

    def get_idx(self, obj):
        """Find an object's position in the group, by identity.

        Args:
            obj (object): The object.

        Returns:
            int: The index, or -1 if absent.
        """
        for i, item in enumerate(self._objects):
            if item is obj:
                return i
        return -1

    def has(self, obj):
        """Check whether an object is in the group.

        Args:
            obj (object): The object.

        Returns:
            bool: True if present.
        """
        return self.get_idx(obj) >= 0

    def get_objects(self):
        """Return the group's members.

        Returns:
            list: A new list of the objects.
        """
        return list(self._objects)

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, nam):
        """Rename the group and update every member's list name.

        Args:
            nam (str | None): The name.
        """
        self._name = nam
        for obj in self._objects:
            obj._list_name = nam

    def clear(self):
        """Remove every object and unlink it."""
        for obj in self._objects:
            obj._Istlink = False
            obj._list_name = None
        self._objects.clear()
        self._objlen = 0

    def get_center(self):
        """Middle of the group's bounding box (the pivot for "center" rotations)."""
        pts = [p.get_xyz() for p in self._points()]
        if not pts:
            return Point3d(0, 0, 0)
        lo, hi = np.min(pts, axis=0), np.max(pts, axis=0)
        return Point3d(*((lo + hi) / 2))

    def __str__(self):
        """Return the group's name and member names.

        Returns:
            str: The description.
        """
        names = ", ".join(str(o.get_name()) if hasattr(o, "get_name") else type(o).__name__
                          for o in self._objects)
        return f'{self._name}: {self._objlen} objects [{names}]'

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()


class Line3d(_Geometry3d, OpOverloaded):
    """Store and manipulate a 3d line segment methods: get_start, get_end return start or end Point3d
    move(newx,newy,newz) translates start and end points
    """

    # Initialize and store start and end Point3d objects
    def __init__(self, start, end, color=None, name="Line3d"):
        """Initialize the line with copies of its end points.

        Args:
            start (Point3d | list | tuple): The start point.
            end (Point3d | list | tuple): The end point.
            color (object): The line color.
            name (str): The name.

        Raises:
            TypeError: If ``start`` is neither a Point3d nor a list or tuple.
        """
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
            raise TypeError("Error Line3d arguments mut be Pomt3d or x,y,z,")
        self._Istlink = False 
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def _points(self):
        """Return the start and end points.

        Returns:
            list[Point3d]: The two end points.
        """
        return [self._start_pt, self._end_pt]

    # Return start point
    def get_start(self):
        """Return the start point.

        Returns:
            Point3d: The start point.
        """
        return self._start_pt

    # Return end point
    def get_end(self):
        """Return the end point.

        Returns:
            Point3d: The end point.
        """
        return self._end_pt

    def length(self):
        """Return the line's length.

        Returns:
            float: The length.
        """
        return math.sqrt(self.len_sqr())
    
    def len_sqr(self):
        """Return the squared length of the line.

        Returns:
            float: The squared length.
        """
        xx = self._end_pt.get_x() - self._start_pt.get_x()
        yy = self._end_pt.get_y() - self._start_pt.get_y()
        zz = self._end_pt.get_z() - self._start_pt.get_z()
        return xx * xx + yy * yy + zz * zz

    def deepcopy(self):
        """Return a new line with copies of the end points.

        Returns:
            Line3d: The copy.
        """
        return Line3d(self.get_start(), self.get_end(), self.get_color())
    
    def copy(self):
        """Return a new line with copies of the end points.

        Returns:
            Line3d: The copy.
        """
        return Line3d(self.get_start(), self.get_end(), self.get_color())

 
    def get_color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    def set_color(self, color):
        """Set the color.

        Args:
            color (object): The color.
        """
        self._color = color

    @property
    def color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    @color.setter
    def color(self, val):
        """Set the color.

        Args:
            val (object): The new color.
        """
        self._color = val

    def __str__(self):
        """Return the line's name, end points and color.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def descr(self):
        """Return the line's name, end points and color.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:Line3D(start=Point3d(x={self._start_pt.get_x():.2f}, y={self._start_pt.get_y():.2f}, z={self._start_pt.get_z():.2f}), end=Point3d(x={self._end_pt.get_x():.2f}, y={self._end_pt.get_y():.2f}, z={self._end_pt.get_z():.2f}), color={self._color})\n"

    def __repr__(self):
        """Return the line's name, end points and color.

        Returns:
            str: The representation.
        """
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
        """Initialize the vector.

        Args:
            origin (Point3d): The start of the vector.
            direction (Point3d): The end of the vector.
            name (str): The name.
        """
        super().__init__(origin, direction)
        # Use the same points as Line3d so inherited transforms stay visible.
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def at(self, t):
        """Return the point at a given parameter along the vector.

        Args:
            t (float): The ray parameter, so the point is origin + t * direction.

        Returns:
            Point3d: origin + t * direction.
        """
        return self.origin + t * self.direction

    # Return the origin of the vector
    def get_origin(self):
        """Return the origin point.

        Returns:
            Point3d: The origin.
        """
        return self._start_pt

    @property
    def origin(self):
        """Return the origin point.

        Returns:
            Point3d: The origin.
        """
        return self._start_pt

    @property
    def direction(self):
        """Return the direction point (the end point).

        Returns:
            Point3d: The direction.
        """
        return self._end_pt

    @direction.setter
    def direction(self, val):
        """Replace the direction point.

        Args:
            val (Point3d): The new direction.
        """
        self._end_pt = val

    @origin.setter
    def origin(self, val):
        """Replace the origin point.

        Args:
            val (Point3d): The new origin.
        """
        self._start_pt = val

    def set_origin(self, origin):
        """Move the origin point to the coordinates of another point.

        Args:
            origin (Point3d): The point to copy the coordinates from.
        """
        self._start_pt.set_xyz(*origin.get_xyz())

    def get_direction(self):
        """Return the direction point (the end point).

        Returns:
            Point3d: The direction.
        """
        return self._end_pt

    def set_direction(self, direction):
        """Move the direction point to the coordinates of another point.

        Args:
            direction (Point3d): The point to copy the coordinates from.
        """
        self._end_pt.set_xyz(*direction.get_xyz())

    def __str__(self):
        """Return the vector's name, origin and direction.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:origin={self._start_pt}\tdirection={self._end_pt}"

    def descr(self):
        """Return the vector's name, origin and direction.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:origin={self._start_pt}\tdirection={self._end_pt}"

    def __repr__(self):
        """Return the vector's name, origin and direction.

        Returns:
            str: The representation.
        """
        return f"{self.get_name()}:origin={self._start_pt}\tdirection={self._end_pt}"


class Square3d(_Geometry3d, OpOverloaded):
    """Store and manipulate a 3d Square
    methods: get_area returns area of square
    move(newx,newy,newz) translates all four lines
    """ 
    # Store four boundary edges; centers and dimensions use their current points.
    def __init__(self, line1, line2, line3, line4, bc=None,fc=None, name="Square3d"):
        """Initialize the square with copies of its four edges.

        Args:
            line1 (Line3d): The first edge.
            line2 (Line3d): The second edge.
            line3 (Line3d): The third edge.
            line4 (Line3d): The fourth edge.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
        """
        self._line1 = line1.deepcopy()
        self._line2 = line2.deepcopy()
        self._line3 = line3.deepcopy()
        self._line4 = line4.deepcopy()
        self._border_col = bc
        self._fill_col = fc
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def _points(self):
        """Return the points of all four edges.

        Returns:
            list[Point3d]: The edge points.
        """
        return [point for line in (self._line1, self._line2, self._line3, self._line4)
                for point in line._points()]

    def deepcopy(self):
        """Return a new square built from copies of the edges.

        Returns:
            Square3d: The copy.
        """
        return Square3d(self._line1, self._line2, self._line3, self._line4,  self._border_col, self._fill_col)

    def copy(self):
        """Return a new square built from copies of the edges.

        Returns:
            Square3d: The copy.
        """
        return Square3d(self._line1, self._line2, self._line3, self._line4,  self._border_col, self._fill_col)

    @property
    def _length(self):
        """Return the length of the first edge.

        Returns:
            float: The length.
        """
        return self._line1.length()

    @property
    def _width(self):
        """Return the length of the second edge.

        Returns:
            float: The width.
        """
        return self._line2.length()

    @property
    def _area(self):
        """Return the area as length times width.

        Returns:
            float: The area.
        """
        # Assumes four boundary edges of a square/rectangle, in order.
        return self._length * self._width

    @_area.setter
    def _area(self, val):
          """Reject attempts to set the area.

          Args:
              val (float): Ignored.

          Raises:
              ValueError: Always, because the area is derived.
          """
          raise ValueError("_ar cannot be set mannually. Adjust length or width instead.")
    
    @_length.setter
    def _length(self, val):
          """Set the length.

          Args:
              val (float): The new length.
          """
          self._length = val

    @_width.setter
    def _width(self, val):
          """Set the width.

          Args:
              val (float): The new width.
          """
          self._with = val

    # Calculate and return the area of the square
    def get_area(self):
        """Return the area of the square.

        Returns:
            float: The area.
        """
        return self._area

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    def set_bc(self, bc):
        """Set the border color.

        Args:
            bc (object): The new border color.
        """
        self._border_col = bc

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def set_fc(self, fc):
        """Set the fill color.

        Args:
            fc (object): The new fill color.
        """
        self._fill_col = fc

    def fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    # Return state of Square object
    def __str__(self):
        """Return the square's area, colors and edges.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def descr(self):
        """Return the square's area, colors and edges.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:\n\tArea: {self.get_area()} border color: {self.bc()} fill color: {self.fc()}\n\tLine1: {self._line1}\tLine2: {self._line2}\tLine3: {self._line3}\tLine4: {self._line4}"

    def __repr__(self):
        """Return the square's area, colors and edges.

        Returns:
            str: The representation.
        """
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
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        """Return the center, edge and normal-tip points.

        Returns:
            list[Point3d]: The stored points.
        """
        return [self._cent, self._rad_edge, self._norm_tip]

    def get_norm(self):
        """Return the unit normal.

        Returns:
            numpy.ndarray: The unit normal vector.
        """
        n = self._xyz(self._norm_tip) - self._xyz(self._cent)
        return n / np.linalg.norm(n)

    def pr_norm(self):
        """Return the unit normal as a Point3d.

        Returns:
            Point3d: The unit normal.
        """
        n = self.get_norm()
        return Point3d(n[0], n[1], n[2])

    def get_vec1(self):
        """Return the vector from the center to the edge point.

        Returns:
            Vector3d: The radius vector.
        """
        return Vector3d(self._cent, self._rad_edge)

    def get_vec2(self):
        """Return the in-plane unit vector perpendicular to the radius.

        Returns:
            numpy.ndarray: The unit vector.
        """
        # In-plane unit vector perpendicular to vec1 (normal x vec1).
        v1 = self._xyz(self._rad_edge) - self._xyz(self._cent)
        v2 = np.cross(self.get_norm(), v1)
        return v2 / np.linalg.norm(v2)

    def get_center(self):
        """Return the center point.

        Returns:
            Point3d: The center.
        """
        return self._cent

    def set_center(self, new_c):
        """Move the whole shape so its center lands on a new point.

        Args:
            new_c (Point3d): The new center.
        """
        # Move the whole shape so its center lands on new_c.
        d = self._xyz(new_c) - self._xyz(self._cent)
        self.move(*d)

    def get_radius(self):
        """Return the radius.

        Returns:
            float: The radius.
        """
        return self.get_vec1().length()

    def set_radius(self, new_r):
        """Move the edge point so the radius is the given length.

        Args:
            new_r (float): The new radius.
        """
        v1 = self._xyz(self._rad_edge) - self._xyz(self._cent)
        self._rad_edge.set_xyz(*(self._xyz(self._cent) + v1 / np.linalg.norm(v1) * new_r))

    def get_border(self):
        """Return the circumference.

        Returns:
            float: The circumference.
        """
        return 2 * math.pi * self.get_radius()

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_color

    def set_bc(self, new_bc):
        """Set the border color.

        Args:
            new_bc (object): The new border color.
        """
        self._border_color = new_bc

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_color

    def set_fc(self, nwe_fc):
        """Set the fill color.

        Args:
            nwe_fc (object): The new fill color.
        """
        self._fill_color = nwe_fc

    def __str__(self):
        """Return the circle's center, radius, normal and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __repr__(self):
        """Return the circle's center, radius, normal and colors.

        Returns:
            str: The representation.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def descr(self):
        """Return the circle's center, radius, normal and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

class Cylinder3d(Circle3d):
    """Circle base plus a stored _top point (center + normal * height)."""
    def __init__(self, center, rad_edge, height, bc=None, fc=None, name="Cylinder3d", normal=None):
        """Initialize the cylinder.

        Args:
            center (Point3d): The center point.
            rad_edge (Point3d): A point on the circle's edge.
            height (float): The height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        super().__init__(center, rad_edge, bc, fc, name, normal)
        self._top = Point3d(*(self._xyz(self._cent) + self.get_norm() * height))
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink
    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def _points(self):
        """Return the circle points plus the top point.

        Returns:
            list[Point3d]: The stored points.
        """
        return super()._points() + [self._top]

    def get_top(self):
        """Return the center of the top circle.

        Returns:
            Point3d: The top point.
        """
        return self._top

    def get_area(self):
        """Return the total surface area including both ends.

        Returns:
            float: The surface area.
        """
        r = self.get_radius()
        return 2 * math.pi * r * self.get_height() + 2 * (math.pi * (r * r))

    def get_height(self):
        """Return the distance between the two circle centers.

        Returns:
            float: The height.
        """
        return float(np.linalg.norm(self._xyz(self._top) - self._xyz(self._cent)))

    def get_volume(self):
        """Return the volume.

        Returns:
            float: The volume.
        """
        r = self.get_radius()
        return math.pi * (r * r) * self.get_height()

    def set_height(self, new_h):
        """Move the top point to the given height along the normal.

        Args:
            new_h (float): The new height.
        """
        self._top.set_xyz(*(self._xyz(self._cent) + self.get_norm() * new_h))

    def pr_norm(self):
        """Return the unit normal as a Point3d.

        Returns:
            Point3d: The unit normal.
        """
        n = self.get_norm()
        return Point3d(n[0], n[1], n[2])

    def __str__(self):
        """Return the cylinder's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}, height={self.get_height()}, volume={self.get_volume()}, area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __repr__(self):
        """Return the cylinder's measurements and colors.

        Returns:
            str: The representation.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}, height={self.get_height()}, volume={self.get_volume()}, area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __descr__(self):
        """Return the cylinder's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}, height={self.get_height()}, volume={self.get_volume()}, area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}'


class Torus3d(_Geometry3d, OpOverloaded):
    """Store a torus approximated by a ring of cylinder segments."""
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
        self._Istlink = False
        self._list_name = None

        radial = self._xyz(self._rad_edge) - self._xyz(self._cent)
        self._xyz(self._tube_rad) - self._xyz(self._rad_edge)
        if np.linalg.norm(radial) == 0:
            raise ValueError("Circle3d center and edge point cannot be the same point.")
        # Direction-only vector (from origin) so get_perpendicular_vectors sees end - start.
        _, normal = self.get_perpendicular_vectors(Vector3d((0, 0, 0), tuple(radial)))
        self._norm_tip = Point3d(*(self._xyz(self._cent) + normal))
        self._cyl_list = self.get_segments()

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def _points(self):
        """Return the defining points plus every segment's points.

        Returns:
            list[Point3d]: The combined points.
        """
        # Torus's own defining points plus every segment's points, so inherited
        # move/rot/scale turn the whole ring about one shared pivot.
        pts = [self._cent, self._rad_edge, self._tube_rad, self._norm_tip]
        for cyl in self.get_cyllist():
            pts += cyl._points()
        return pts

    def get_center(self):
        """Return the center of the hole.

        Returns:
            Point3d: The center.
        """
        return self._cent

    def get_norm(self):
        """Return the unit normal of the ring plane.

        Returns:
            numpy.ndarray: The unit normal.
        """
        n = self._xyz(self._norm_tip) - self._xyz(self._cent)
        return n / np.linalg.norm(n)

    def get_major_radius(self):
        """Return the distance from the center to the tube's center line.

        Returns:
            float: The major radius.
        """
        return self.length(self._cent, self._rad_edge)

    def get_minor_radius(self):
        """Return the radius of the tube.

        Returns:
            float: The minor radius.
        """
        return self.length(self._rad_edge, self._tube_rad)

    def length(self, start, end):
        """Return the distance between two points.

        Args:
            start (Point3d): The first point.
            end (Point3d): The second point.

        Returns:
            float: The distance.
        """
        return math.sqrt(self.len_sqr(start, end))
    
    def len_sqr(self, start, end):
        """Return the squared distance between two points.

        Args:
            start (Point3d): The first point.
            end (Point3d): The second point.

        Returns:
            float: The squared distance.
        """
        xx = end.get_x() - start.get_x()
        yy = end.get_y() - start.get_y()
        zz = end.get_z() - start.get_z()
        return xx * xx + yy * yy + zz * zz

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def get_cyllist(self):
        """Return the cylinder segments that make up the ring.

        Returns:
            list[Cylinder3d]: The segments.
        """
        return self._cyl_list

    def set_cyllist(self):
        """Rebuild the cylinder segments from the current geometry."""
        self._cyl_list = self.get_segments()
    
    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_color
    
    def set_fc(self, color):
        """Set the fill color.

        Args:
            color (object): The color.
        """
        self._fill_color = color

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_color

    def set_bc(self, color):
        """Set the border color.

        Args:
            color (object): The color.
        """
        self._border_color = color

    def __str__(self):
        """Return the description of every segment.

        Returns:
            str: The description.
        """
        ret_str =  f'{self.get_name()}:\n'
        for cyl in self.get_cyllist():
            ret_str += f'\t{cyl}\n\n'
        return ret_str

    def __repr__(self):
        """Return the description of every segment.

        Returns:
            str: The representation.
        """
        ret_str =  f'{self.get_name()}:\n'
        for cyl in self.get_cyllist():
            ret_str += f'\t{cyl}\n\n'
        return ret_str
 
    def desc(self):
        """Return the description of every segment.

        Returns:
            str: The description.
        """
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
        """Initialize the curved tube.

        Args:
            bend_center (Point3d): The point the tube curves around.
            spine_start (Point3d): The start of the tube's center line.
            tube_radius (float): The radius of the tube.
            angle (float): How far the tube bends, in radians (0 to 2*pi).
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.

        Raises:
            ValueError: If the angle is outside (0, 2*pi], the center and start coincide, the tube radius is not smaller than the bend radius, or the normal is parallel to the radius.
        """
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
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        """Return the bend center, start, edge and normal-tip points.

        Returns:
            list[Point3d]: The stored points.
        """
        return [self._bend_cent, self._start, self._edge, self._norm_tip]

    # ---- frame: e1 = radial at the start, e2 = sweep direction at the start
    def _frame(self):
        """Return the bend center and its orthonormal frame.

        Returns:
            tuple: The bend center, the radial unit vector at the start, the sweep unit vector, and the normal.
        """
        c = self._xyz(self._bend_cent)
        e1 = self._xyz(self._start) - c
        e1 = e1 / np.linalg.norm(e1)
        n = self.get_norm()
        return c, e1, np.cross(n, e1), n

    def get_norm(self):
        """Return the unit normal of the bend plane.

        Returns:
            numpy.ndarray: The unit normal.
        """
        n = self._xyz(self._norm_tip) - self._xyz(self._bend_cent)
        return n / np.linalg.norm(n)

    def get_bend_center(self):
        """Return the point the tube curves around.

        Returns:
            Point3d: The bend center.
        """
        return self._bend_cent

    def get_bend_radius(self):
        """Return the distance from the bend center to the center line.

        Returns:
            float: The bend radius.
        """
        return float(np.linalg.norm(self._xyz(self._start) - self._xyz(self._bend_cent)))

    def get_tube_radius(self):
        """Return the radius of the tube.

        Returns:
            float: The tube radius.
        """
        return float(np.linalg.norm(self._xyz(self._edge) - self._xyz(self._start)))

    def get_angle(self):
        """Return how far the tube bends.

        Returns:
            float: The angle in radians.
        """
        return self._angle

    def set_angle(self, angle):
        """Set how far the tube bends.

        Args:
            angle (float): The new bend angle in radians.

        Raises:
            ValueError: If the angle is outside (0, 2*pi].
        """
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
        """Return the start of the tube's center line.

        Returns:
            Point3d: The start point.
        """
        return self._start

    def get_spine_end(self):
        """Return the end of the tube's center line.

        Returns:
            Point3d: The end point.
        """
        return self.spine_point(1.0)

    def get_center(self):
        """Return the middle of the tube's center line.

        Returns:
            Point3d: The center.
        """
        # Middle of the bend's center line, so pivot="center" spins the banana about its middle.
        return self.spine_point(0.5)

    def get_arc_length(self):
        """Return the length of the tube's center line.

        Returns:
            float: The arc length.
        """
        return self.get_bend_radius() * self._angle

    def get_volume(self):
        """Return the volume of the tube.

        Returns:
            float: The volume.
        """
        r = self.get_tube_radius()
        return math.pi * (r * r) * self.get_arc_length()

    def get_area(self):
        """Return the surface area, including end caps unless the bend closes.

        Returns:
            float: The surface area.
        """
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
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_color

    def set_bc(self, bc):
        """Set the border color.

        Args:
            bc (object): The new border color.
        """
        self._border_color = bc

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_color

    def set_fc(self, fc):
        """Set the fill color.

        Args:
            fc (object): The new fill color.
        """
        self._fill_color = fc

    def __str__(self):
        """Return the tube's measurements and colors.

        Returns:
            str: The description.
        """
        return (f'{self.get_name()}:\n\tbend center={self.get_bend_center()}\tbend radius={self.get_bend_radius()},'
                f'  tube radius={self.get_tube_radius()},  angle={math.degrees(self._angle)} deg\n'
                f'\tstart={self.get_spine_start()}\tend={self.get_spine_end()}\tnormal={self.get_norm()}\n'
                f'\tvolume={self.get_volume()},  area={self.get_area()},  fc={self.get_fc()}, bc={self.get_bc()}')

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()


class CurvedTorus3d(_Geometry3d, OpOverloaded):
    """Torus built from `segments` CurvedCylinder3d bends chained end to end (smooth joints)."""
    def __init__(self, center, ring_point, tube_radius, segments=4, bc=None, fc=None,
                 name="CurvedTorus3d", normal=None):
        """Initialize the torus from chained curved tubes.

        Args:
            center (Point3d): The center of the ring.
            ring_point (Point3d): A point on the ring's center line.
            tube_radius (float): The radius of the tube.
            segments (int): The number of bends (at least 1).
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.

        Raises:
            ValueError: If there are no segments, or the tube radius is not smaller than the ring radius.
        """
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
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def _points(self):
        """Return the points of every bend.

        Returns:
            list[Point3d]: The combined points.
        """
        return [p for bend in self._bends for p in bend._points()]

    def get_bends(self):
        """Return the curved tubes that make up the ring.

        Returns:
            list[CurvedCylinder3d]: The bends.
        """
        return self._bends

    def get_center(self):
        """Return the center of the ring.

        Returns:
            Point3d: The center.
        """
        return self._bends[0].get_bend_center()

    def get_norm(self):
        """Return the unit normal of the ring plane.

        Returns:
            numpy.ndarray: The unit normal.
        """
        return self._bends[0].get_norm()

    def get_major_radius(self):
        """Return the ring radius.

        Returns:
            float: The major radius.
        """
        return self._bends[0].get_bend_radius()

    def get_minor_radius(self):
        """Return the tube radius.

        Returns:
            float: The minor radius.
        """
        return self._bends[0].get_tube_radius()

    def get_volume(self):
        """Return the total volume of the bends.

        Returns:
            float: The volume.
        """
        return sum(b.get_volume() for b in self._bends)

    def get_area(self):
        """Return the surface area of the torus.

        Returns:
            float: The surface area.
        """
        r = self.get_minor_radius()
        return 2 * math.pi * r * 2 * math.pi * self.get_major_radius()

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_color

    def set_bc(self, bc):
        """Set the border color of the torus and every bend.

        Args:
            bc (object): The new border color.
        """
        self._border_color = bc
        for b in self._bends:
            b.set_bc(bc)

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_color

    def set_fc(self, fc):
        """Set the fill color of the torus and every bend.

        Args:
            fc (object): The new fill color.
        """
        self._fill_color = fc
        for b in self._bends:
            b.set_fc(fc)

    def __str__(self):
        """Return the torus measurements and colors.

        Returns:
            str: The description.
        """
        return (f'{self.get_name()}:\n\tcenter={self.get_center()}\tR={self.get_major_radius()},  '
                f'r={self.get_minor_radius()},  segments={len(self._bends)},  volume={self.get_volume()},  '
                f'area={self.get_area()}\n\tnormal={self.get_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}')

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()


class Cone3d(Circle3d):
    """Circle base plus a stored _top apex point (center + normal * height)."""
    def __init__(self, center, rad_edge, height, bc=None, fc=None, name="Cone3", normal=None):
        """Initialize the cone.

        Args:
            center (Point3d): The center point.
            rad_edge (Point3d): A point on the circle's edge.
            height (float): The height.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.
        """
        super().__init__(center, rad_edge, bc, fc, name, normal)
        self._top = Point3d(*(self._xyz(self._cent) + self.get_norm() * height))
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink


    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def _points(self):
        """Return the circle points plus the apex.

        Returns:
            list[Point3d]: The stored points.
        """
        return super()._points() + [self._top]

    def get_apex(self):
        """Return the apex point.

        Returns:
            Point3d: The apex.
        """
        return self._top

    def get_height(self):
        """Return the distance from the base center to the apex.

        Returns:
            float: The height.
        """
        return float(np.linalg.norm(self._xyz(self._top) - self._xyz(self._cent)))

    def set_height(self, new_h):
        """Move the apex to the given height along the normal.

        Args:
            new_h (float): The new height.
        """
        self._top.set_xyz(*(self._xyz(self._cent) + self.get_norm() * new_h))

    def get_slant_height(self):
        """Return the distance from the apex to the base edge.

        Returns:
            float: The slant height.
        """
        r, h = self.get_radius(), self.get_height()
        return math.sqrt((r * r) + (h * h))

    def get_area(self):
        """Return the total surface area including the base.

        Returns:
            float: The surface area.
        """
        r = self.get_radius()
        return math.pi * r * self.get_slant_height() + math.pi * (r * r)

    def get_volume(self):
        """Return the volume.

        Returns:
            float: The volume.
        """
        r = self.get_radius()
        return (1/3) * math.pi * (r * r) * self.get_height()

    def __str__(self):
        """Return the cone's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __repl__(self):
        """Return the cone's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __desc__(self):
        """Return the cone's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()},  height={self.get_height()},  volume={self.get_volume()},  sarea={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.get_norm()}\n\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'


class TruncatedCone3d(Cylinder3d):
    """Cone with its point cut off flat (a frustum).

    Cylinder base plus a stored _top_edge point on the top circle; the top
    radius is top_scale * base radius (0 = full cone, 1 = cylinder).
    """
    def __init__(self, center, rad_edge, height, top_scale=0.5, bc=None, fc=None,
                 name="TruncatedCone3d", normal=None):
        """Initialize the frustum.

        Args:
            center (Point3d): The center point.
            rad_edge (Point3d): A point on the circle's edge.
            height (float): The height.
            top_scale (float): The top size as a fraction of the base size. Must not be negative.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
            normal (tuple | None): The facing direction as three numbers, or None to choose one.

        Raises:
            ValueError: If ``top_scale`` is negative.
        """
        super().__init__(center, rad_edge, height, bc, fc, name, normal)
        if top_scale < 0:
            raise ValueError("top_scale cannot be negative.")
        radial = self._xyz(self._rad_edge) - self._xyz(self._cent)
        self._top_edge = Point3d(*(self._xyz(self._top) + radial * float(top_scale)))

    def _points(self):
        """Return the cylinder points plus the top edge point.

        Returns:
            list[Point3d]: The stored points.
        """
        return super()._points() + [self._top_edge]

    def get_top_edge(self):
        """Return the point on the top circle's edge.

        Returns:
            Point3d: The top edge point.
        """
        return self._top_edge

    def get_top_radius(self):
        """Return the radius of the top circle.

        Returns:
            float: The top radius.
        """
        return float(np.linalg.norm(self._xyz(self._top_edge) - self._xyz(self._top)))

    def set_top_radius(self, new_r):
        """Set the radius of the top circle.

        Args:
            new_r (float): The new top radius.
        """
        self.set_top_scale(new_r / self.get_radius())

    def get_top_scale(self):
        """Return the top radius as a fraction of the base radius.

        Returns:
            float: The ratio of top radius to base radius.
        """
        return self.get_top_radius() / self.get_radius()

    def set_top_scale(self, top_scale):
        """Set the top radius as a fraction of the base radius.

        Args:
            top_scale (float): The top size as a fraction of the base size. Must not be negative.

        Raises:
            ValueError: If ``top_scale`` is negative.
        """
        if top_scale < 0:
            raise ValueError("top_scale cannot be negative.")
        radial = self._xyz(self._rad_edge) - self._xyz(self._cent)
        self._top_edge.set_xyz(*(self._xyz(self._top) + radial * float(top_scale)))

    def set_height(self, new_h):
        """Set the height, carrying the top edge point with the top.

        Args:
            new_h (float): The new height.
        """
        offset = self._xyz(self._top_edge) - self._xyz(self._top)
        super().set_height(new_h)
        self._top_edge.set_xyz(*(self._xyz(self._top) + offset))

    def set_radius(self, new_r):
        """Resize the base while keeping the top the same actual size.

        Args:
            new_r (float): The new radius.
        """
        # Resizing the base keeps the top the same actual size.
        top_r = self.get_top_radius()
        super().set_radius(new_r)
        self.set_top_radius(top_r)

    def get_slant_height(self):
        """Return the length of the slanted side.

        Returns:
            float: The slant height.
        """
        return math.sqrt(self.get_height() ** 2 + (self.get_radius() - self.get_top_radius()) ** 2)

    def get_top_border(self):
        """Return the circumference of the top circle.

        Returns:
            float: The top circumference.
        """
        return 2 * math.pi * self.get_top_radius()

    def get_area(self):
        """Return the total surface area including both ends.

        Returns:
            float: The surface area.
        """
        r1, r2 = self.get_radius(), self.get_top_radius()
        return math.pi * (r1 + r2) * self.get_slant_height() + math.pi * (r1 * r1 + r2 * r2)

    def get_volume(self):
        """Return the volume.

        Returns:
            float: The volume.
        """
        r1, r2 = self.get_radius(), self.get_top_radius()
        return math.pi * self.get_height() / 3 * (r1 * r1 + r1 * r2 + r2 * r2)

    def get_side_normal(self, angle=0.0):
        """Outward unit normal of the slanted side, angle radians round from the edge point."""
        n = self.get_norm()
        u = self._xyz(self._rad_edge) - self._xyz(self._cent)
        u = u / np.linalg.norm(u)
        out = u * math.cos(angle) + np.cross(n, u) * math.sin(angle)
        # The side leans in by (r1 - r2) over the height, so tip the normal up by that much.
        side = out * self.get_height() + n * (self.get_radius() - self.get_top_radius())
        side = side / np.linalg.norm(side)
        return Point3d(*side)

    def deepcopy(self):
        """Return an independent copy.

        Returns:
            TruncatedCone3d: The copy.
        """
        return TruncatedCone3d(self._cent, self._rad_edge, self.get_height(), self.get_top_scale(),
                               self._border_color, self._fill_color, self._name, tuple(self.get_norm()))

    def copy(self):
        """Return an independent copy.

        Returns:
            TruncatedCone3d: The copy.
        """
        return self.deepcopy()

    def __str__(self):
        """Return the frustum's measurements and colors.

        Returns:
            str: The description.
        """
        return f'{self.get_name()}:\n\tcenter={self.get_center()}\tradius={self.get_radius()}, top_radius={self.get_top_radius()}, height={self.get_height()}, volume={self.get_volume()}, area={self.get_area()}\n\tvecto1={self.get_vec1()}\tnormal={self.pr_norm()}\tfc={self.get_fc()}, bc={self.get_bc()}, border={self.get_border()}\n'

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()

class Plane3d(_Geometry3d, OpOverloaded):

    """Store a plane as two vectors and a normal."""
    def __init__(self,vec1,color=None, texture=None, name="Plane3d"):
        """Initialize the plane from one in-plane vector.

        Args:
            vec1 (Vector3d): A vector in the plane.
            color (object): The plane color.
            texture (object): The plane texture.
            name (str): The name.
        """
        self._vector1 = Vector3d(vec1.get_start(), vec1.get_end())
        tmp_vec, tmp_norm = self.get_perpendicular_vectors(vec1)
        self._vector2 = Vector3d(self._vector1.get_origin(),Point3d(tmp_vec[0], tmp_vec[1], tmp_vec[2]))
        self._normal = Point3d(tmp_norm[0], tmp_norm[1], tmp_norm[2])
        self._col = color
        self._txt = texture
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_color(self):
        """Return the plane color.

        Returns:
            object: The color.
        """
        return self._col

    def set_color(self, color):
        """Set the plane color.

        Args:
            color (object): The color.
        """
        self._color = color

    def get_texture(self):
        """Return the plane texture.

        Returns:
            object: The texture.
        """
        return self._txt

    def set_teture(self, teture):
        """Set the plane texture.

        Args:
            teture (object): The texture.
        """
        self._txt = teture

    def get_norm(self):
        """Return the plane's normal.

        Returns:
            Point3d: The normal.
        """
        return self._normal
    
    def set_norm(self, norm):
        """Set the plane's normal.

        Args:
            norm (Point3d): The new normal.
        """
        self._normal = norm

    def get_vec1(self):
        """Return the first in-plane vector.

        Returns:
            Vector3d: The first vector.
        """
        return self._vector1

    def set_vec1(self, vector):
        """Set the first in-plane vector.

        Args:
            vector (Vector3d): The vector.
        """
        self._vector1 = vector

    def get_vec2(self):
        """Return the second in-plane vector.

        Returns:
            Vector3d: The second vector.
        """
        return self._vector2
    
    def set_vec2(self, vector):
        """Set the second in-plane vector.

        Args:
            vector (Vector3d): The vector.
        """
        self._vector2 = vector
        
    def __str__(self):
        """Return the plane's vectors, normal, color and texture.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:\nVect1:\t{self.get_vec1()}vector2:{self.get_vec2()}normal: {self.get_norm()}color: {self.get_color()}Texture: {self.get_texture()}\n"

    def descr(self):
        """Return the plane's vectors, normal, color and texture.

        Returns:
            str: The description.
        """
        return f"{self.get_name()}:\nVect1:\t{self.get_vec1()}vector2:{self.get_vec2()}normal: {self.get_norm()}color: {self.get_color()}Texture: {self.get_texture()}\n"

    def __repr__(self):
        """Return the plane's vectors, normal, color and texture.

        Returns:
            str: The representation.
        """
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
        if name != None:
            self._name = name
        else:
            self._name = "cube"
        sname = "square"
        remaining = (square3, square4, square5, square6)
        if square2 is not None and not isinstance(square2, Square3d):
            if height is not None or any(face is not None for face in remaining):
                raise TypeError("Provide one base and height, or all six faces.")
            height, square2 = square2, None
        if square2 is None:
            if any(face is not None for face in remaining):
                raise TypeError("Provide one base or all six faces.")
            square1, square2, square3, square4, square5, square6 = self._from_base(square1, height)
            square1.set_name(f'{sname}1')
            square2.set_name(f'{sname}2')
            square3.set_name(f'{sname}3')
            square4.set_name(f'{sname}4')
            square5.set_name(f'{sname}5')
            square6.set_name(f'{sname}6')
        elif height is not None or not all(isinstance(face, Square3d)
                                           for face in (square1, square2, *remaining)):
            raise TypeError("The six-face form requires six squares and no height.")
        faces = (square1, square2, square3, square4, square5, square6)
        valid_faces = []
        for face in faces:
            if not isinstance(face, Square3d):
                raise TypeError("Cube3d requires six squares.")
            valid_faces.append(face)
        self._square1 = valid_faces[0].deepcopy()
        self._square2 = valid_faces[1].deepcopy()
        self._square3 = valid_faces[2].deepcopy()
        self._square4 = valid_faces[3].deepcopy()
        self._square5 = valid_faces[4].deepcopy()
        self._square6 = valid_faces[5].deepcopy()
        for index, face in enumerate((self._square1, self._square2, self._square3,
                                      self._square4, self._square5, self._square6), 1):
            face.set_name(f'{sname}{index}')
        self._border_col = bc
        self._fill_col = fc
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
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
            """Build a line between two points that shares those point objects.

            Args:
                start (Point3d): The start point.
                end (Point3d): The end point.

            Returns:
                Line3d: The line.
            """
            line = Line3d(start, end)
            line._start_pt, line._end_pt = start, end
            return line

        def face(points):
            """Build a square face from four corner points.

            Args:
                points (list[Point3d]): The four corners, in order.

            Returns:
                Square3d: The face.
            """
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
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    def set_fc(self, color):
        """Set the fill color.

        Args:
            color (object): The new fill color.
        """
        self._fill_col= color

    def set_bc(self, color):
        """Set the border color.

        Args:
            color (object): The new border color.
        """
        self._border_col = color

    def _points(self):
        """Return the points of all six faces.

        Returns:
            list[Point3d]: The combined points.
        """
        return [point for square in (self._square1, self._square2, self._square3,
                                    self._square4, self._square5, self._square6)
                for point in square._points()]

    @property
    def _volume(self):
        """Return the volume as base area times height.

        Returns:
            float: The volume.
        """
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
        """Return the volume.

        Returns:
            float: The volume.
        """
        return self._volume

    def __str__(self):
        """Return the faces, center, volume and colors.

        Returns:
            str: The description.
        """
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4},\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}\tvolume: {self.get_volume()}, fill color: {self.get_fc()}, border color: {self.get_bc()}\n")

    def __repr__(self):
        """Return the faces, center, volume and colors.

        Returns:
            str: The representation.
        """
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4}\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}\tvolume: {self.get_volume()}, fill color: {self.get_fc()}, border color: {self.get_bc()}\n")


    def descr(self):
        """Return the faces, center, volume and colors.

        Returns:
            str: The description.
        """
        return (f"{self.get_name()}:\n\t{self._square1}\n\t{self._square2}\n\t{self._square3}\n\t"
                f"{self._square4}\n\t{self._square5}\n\t{self._square6}\n"
                f"\tcenter= {self.get_center()}, volume: {self.get_volume()}, fill color: {self.get_fc()}, border color: {self.get_bc()}\n")

#Rectangle3d = Cube3d

class Sphere3d(_Geometry3d, OpOverloaded, Hittable):
    """ Sphere3d represents a shpere in 3 dementions
        as arguments it takes a Point3d center ahd a radius. and optionally a name,
        a matrial and a color
    """
    def __init__(self, center, radius, mat=None, color=None,name="Sphere3d"):
        """Initialize the sphere with a copy of its center.

        Args:
            center (Point3d): The center point.
            radius (float): The radius.
            mat (object): The material.
            color (object): The color.
            name (str): The name.
        """
        # Stationary Sphere
        self._static_center= center.deepcopy()
        self._radius = max(0,radius)
        self._mat = mat
        self._color = color
        self._name = name  
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def hit(self, r, ray_tmin, ray_t_max, rec):
        """Test whether a ray hits the sphere.

        Args:
            r (Ray3d): The ray being tested.
            ray_tmin (float): The smallest accepted ray parameter.
            ray_t_max (float): The largest accepted ray parameter.
            rec (Hit_Record): Receives the hit details when the ray hits.

        Returns:
            bool: True if the ray hits within the accepted range. On a hit, ``rec`` is filled in.
        """
        oc = self._static_center - r.get_origin()
        a = r.get_direction().len_sqr()
        h = dot(r.direction, oc)
        c = oc.len_sqr() - self._radius*self._radius

        discriminant = h*h - a*c
        if (discriminant < 0):
            return False

        sqrtd = math.sqrt(discriminant)

        #Find the nearest root that lies in the acceptable range.
        root = (h - sqrtd) / a
        if (root <= ray_tmin  or ray_t_max <= root):
            root = (h + sqrtd) / a
            if (root <= ray_tmin or ray_t_max <= root):
                return False
    

        rec.t = root
        rec.p = r.at(rec.t)
        outward_normal = (rec.p - self._static_center) / self._radius
        rec.set_face_normal(r, outward_normal)

        return True

    @property
    def center(self):
        """Return the sphere's center.

        Returns:
            Point3d: The center.
        """
        return self._static_center

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self,name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name
        
    def get_static_radius_center(self):
        """Return the sphere's center.

        Returns:
            Point3d: The center.
        """
        return self._static_center

    def get_static_radius(self):
        """Return the sphere's radius.

        Returns:
            float: The radius.
        """
        return self._radius

    def set_static_center(self, center):
        """Set the sphere's center.

        Args:
            center (Point3d): The center point.
        """
        self._static_center = center

    def set_static_radius(self, radius):
        """Set the sphere's radius, which is never negative.

        Args:
            radius (float): The radius.
        """
        self._radius = max(0, radius)
    
    def get_color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color
    
    def set_color(self, color):
        """Set the color.

        Args:
            color (object): The color.
        """
        self._color = color
    
    def get_radius(self):
        """Return the sphere's radius.

        Returns:
            float: The radius.
        """
        return self.get_static_radius()
        
    def get_center(self):
        """Return the sphere's center.

        Returns:
            Point3d: The center.
        """
        return self.get_static_radius_center()

    def __str__(self):
        """Return the sphere's name, center, radius and color.

        Returns:
            str: The description.
        """
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")

    def __repr__(self):     
        """Return the sphere's name, center, radius and color.

        Returns:
            str: The representation.
        """
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")

    def descr(self):
        """Return the sphere's name, center, radius and color.

        Returns:
            str: The description.
        """
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius: {self.get_radius()}, color: {self.get_color()}\n")


class Ellipsoid3d(_Geometry3d, OpOverloaded, Hittable):
    """Sphere stretched to three radii (an oval ball).

    rx, ry, rz are the half-widths along the world X, Y, Z axes when built;
    rotate it afterwards to tilt it. Stored as real Point3d objects (center and
    the three axis tip points) so move/rot/scale work and it stays oval-shaped.
    rx == ry == rz is a plain sphere. Hittable like Sphere3d.
    """
    def __init__(self, center, rx, ry, rz, mat=None, color=None, name="Ellipsoid3d"):
        """Initialize the ellipsoid.

        Args:
            center (Point3d): The center point.
            rx (float): The radius along X.
            ry (float): The radius along Y.
            rz (float): The radius along Z.
            mat (object): The material.
            color (object): The color.
            name (str): The name.

        Raises:
            ValueError: If any radius is not positive.
        """
        if min(rx, ry, rz) <= 0:
            raise ValueError("Ellipsoid3d radii must be positive.")
        c = np.array(center.get_xyz(), dtype=float)
        self._cent = Point3d(*c)
        self._tip_x = Point3d(*(c + (rx, 0, 0)))
        self._tip_y = Point3d(*(c + (0, ry, 0)))
        self._tip_z = Point3d(*(c + (0, 0, rz)))
        self._mat = mat
        self._color = color
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        """Return the center and the three axis tip points.

        Returns:
            list[Point3d]: The stored points.
        """
        return [self._cent, self._tip_x, self._tip_y, self._tip_z]

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    def set_color(self, color):
        """Set the color.

        Args:
            color (object): The color.
        """
        self._color = color

    def get_center(self):
        """Return the center.

        Returns:
            Point3d: The center.
        """
        return self._cent

    @property
    def center(self):
        """Return the center.

        Returns:
            Point3d: The center.
        """
        return self._cent

    def set_center(self, new_c):
        """Move the whole shape so its center lands on a new point.

        Args:
            new_c (Point3d): The new center.
        """
        self.move(*(self._xyz(new_c) - self._xyz(self._cent)))

    def get_radii(self):
        """(rx, ry, rz): distance from the center to each axis tip."""
        c = self._xyz(self._cent)
        return tuple(float(np.linalg.norm(self._xyz(t) - c)) for t in (self._tip_x, self._tip_y, self._tip_z))

    def set_radii(self, rx, ry, rz):
        """Set the three radii, keeping the current axis directions.

        Args:
            rx (float): The half-width along X.
            ry (float): The half-width along Y.
            rz (float): The half-width along Z.

        Raises:
            ValueError: If any radius is not positive.
        """
        if min(rx, ry, rz) <= 0:
            raise ValueError("Ellipsoid3d radii must be positive.")
        c = self._xyz(self._cent)
        for tip, axis, r in zip((self._tip_x, self._tip_y, self._tip_z), self.get_axes(), (rx, ry, rz)):
            tip.set_xyz(*(c + axis * r))

    def get_axes(self):
        """Unit direction of each of the three axes (they follow rotations)."""
        c = self._xyz(self._cent)
        return [(self._xyz(t) - c) / np.linalg.norm(self._xyz(t) - c)
                for t in (self._tip_x, self._tip_y, self._tip_z)]

    def get_width(self):
        """Return the full width along the first axis.

        Returns:
            float: Twice the first radius.
        """
        return 2 * self.get_radii()[0]

    def get_length(self):
        """Return the full length along the second axis.

        Returns:
            float: Twice the second radius.
        """
        return 2 * self.get_radii()[1]

    def get_height(self):
        """Return the full height along the third axis.

        Returns:
            float: Twice the third radius.
        """
        return 2 * self.get_radii()[2]

    def is_sphere(self):
        """Check whether all three radii are equal.

        Returns:
            bool: True if the ellipsoid is a sphere.
        """
        rx, ry, rz = self.get_radii()
        return math.isclose(rx, ry) and math.isclose(ry, rz)

    def get_volume(self):
        """Return the volume.

        Returns:
            float: The volume.
        """
        rx, ry, rz = self.get_radii()
        return 4 / 3 * math.pi * rx * ry * rz

    def get_area(self):
        """Surface area. Exact for a sphere; otherwise Knud Thomsen's formula (within about 1%)."""
        rx, ry, rz = self.get_radii()
        if self.is_sphere():
            return 4 * math.pi * rx * rx
        p = 1.6075
        return 4 * math.pi * (((rx * ry) ** p + (rx * rz) ** p + (ry * rz) ** p) / 3) ** (1 / p)

    def _local(self, point):
        """Point in the ellipsoid's own frame, divided by the radii (unit-sphere space)."""
        d = self._xyz(point) - self._xyz(self._cent)
        return np.array([np.dot(d, a) / r for a, r in zip(self.get_axes(), self.get_radii())])

    def contains(self, point):
        """True if point is inside or on the surface."""
        return float(np.dot(self._local(point), self._local(point))) <= 1 + 1e-9

    def get_normal(self, point):
        """Outward unit surface normal at (or nearest the direction of) point, as a Point3d."""
        local = self._local(point)
        n = sum(axis * (q / r) for axis, q, r in zip(self.get_axes(), local, self.get_radii()))
        return Point3d(*(n / np.linalg.norm(n)))

    def get_points(self, rings=12, segments=24):
        """Surface points for drawing: south pole, `rings`-1 rings of `segments` points, north pole (along the z axis)."""
        c = self._xyz(self._cent)
        ax, ay, az = self.get_axes()
        rx, ry, rz = self.get_radii()
        pts = [Point3d(*(c - az * rz))]
        for i in range(1, rings):
            lat = -math.pi / 2 + math.pi * i / rings
            for j in range(segments):
                lon = 2 * math.pi * j / segments
                p = (c + ax * rx * math.cos(lat) * math.cos(lon) + ay * ry * math.cos(lat) * math.sin(lon)
                     + az * rz * math.sin(lat))
                pts.append(Point3d(*p))
        pts.append(Point3d(*(c + az * rz)))
        return pts

    def hit(self, r, ray_tmin, ray_tmax, rec):
        """Test whether a ray hits the ellipsoid.

        Args:
            r (Ray3d): The ray being tested.
            ray_tmin (float): The smallest accepted ray parameter.
            ray_tmax (float): The largest accepted ray parameter.
            rec (Hit_Record): Receives the hit details when the ray hits.

        Returns:
            bool: True if the ray hits within the accepted range. On a hit, ``rec`` is filled in.
        """
        # Squash the ray into unit-sphere space, solve there; t is the same in both spaces.
        o = self._local(r.get_origin())
        d = np.array([np.dot(self._xyz(r.direction), a) / rad for a, rad in zip(self.get_axes(), self.get_radii())])
        a = float(np.dot(d, d))
        h = float(-np.dot(d, o))
        c = float(np.dot(o, o)) - 1
        discriminant = h * h - a * c
        if discriminant < 0:
            return False
        sqrtd = math.sqrt(discriminant)

        # Find the nearest root that lies in the acceptable range.
        root = (h - sqrtd) / a
        if root <= ray_tmin or ray_tmax <= root:
            root = (h + sqrtd) / a
            if root <= ray_tmin or ray_tmax <= root:
                return False

        rec.t = root
        rec.p = r.at(rec.t)
        rec.set_face_normal(r, self.get_normal(rec.p))
        return True

    def deepcopy(self):
        """Return an independent copy.

        Returns:
            Ellipsoid3d: The copy.
        """
        new = Ellipsoid3d(self._cent, 1, 1, 1, self._mat, self._color, self._name)
        new._tip_x, new._tip_y, new._tip_z = (t.deepcopy() for t in (self._tip_x, self._tip_y, self._tip_z))
        return new

    def copy(self):
        """Return an independent copy.

        Returns:
            Ellipsoid3d: The copy.
        """
        return self.deepcopy()

    def __str__(self):
        """Return the radii, volume, area and color.

        Returns:
            str: The description.
        """
        rx, ry, rz = self.get_radii()
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradii: ({rx:.2f}, {ry:.2f}, {rz:.2f}), "
                f"volume={self.get_volume():.2f}, area={self.get_area():.2f}, color: {self.get_color()}\n")

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()


PHI = (1 + math.sqrt(5)) / 2     # golden ratio, used by the dodecahedron and icosahedron


class Polyhedron3d(_Geometry3d):
    """Shared base for solids with flat faces (octahedron, dodecahedron, ...).

    Every vertex is a real Point3d, so move/rot/scale just move the corners.
    Subclasses only give their corner coordinates (_canonical) and their
    area/volume factors (area = _area_k * a^2, volume = _volume_k * a^3, a = edge).
    The faces are worked out once from the corners and reused.
    """
    _area_k = None
    _volume_k = None
    _face_cache = {}

    @classmethod
    def _canonical(cls):
        """Return the corner coordinates of the solid for the base edge length.

        Returns:
            list[tuple]: The corner coordinates.

        Raises:
            NotImplementedError: Always, in the base class.
        """
        raise NotImplementedError("Polyhedron subclasses must give their corner coordinates.")

    def __init__(self, center, edge_length, bc="blue", fc="green", name="Polyhedron3d"):
        """Initialize the solid and find its faces.

        Args:
            center (Point3d): The center point.
            edge_length (float): The edge length.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.

        Raises:
            ValueError: If the edge length is not positive.
        """
        if edge_length <= 0:
            raise ValueError("Edge length must be positive.")
        canon = np.array(self._canonical(), dtype=float)
        faces = self._find_faces(canon)
        canon_edge = np.linalg.norm(canon[faces[0][0]] - canon[faces[0][1]])
        c = np.array(center.get_xyz(), dtype=float)
        self._cent = Point3d(*c)
        self._verts = [Point3d(*(c + v * (edge_length / canon_edge))) for v in canon]
        self._faces = faces
        self._border_col = bc
        self._fill_col = fc
        self._name = name
        self._Istlink = False
        self._list_name = None

    @classmethod
    def _find_faces(cls, verts):
        """Find every face plane of the convex solid; corners listed counter-clockwise from outside."""
        if cls in Polyhedron3d._face_cache:
            return Polyhedron3d._face_cache[cls]
        eps = 1e-9 * max(np.linalg.norm(verts, axis=1))
        found, faces = set(), []
        n_v = len(verts)
        for i in range(n_v):
            for j in range(i + 1, n_v):
                for k in range(j + 1, n_v):
                    n = np.cross(verts[j] - verts[i], verts[k] - verts[i])
                    if np.linalg.norm(n) < eps:
                        continue
                    side = verts @ n - np.dot(n, verts[i])
                    if np.all(side <= eps):
                        pass
                    elif np.all(side >= -eps):
                        n, side = -n, -side
                    else:
                        continue            # corners on both sides: not a face
                    on = tuple(sorted(np.nonzero(np.abs(side) <= eps)[0]))
                    if on in found:
                        continue
                    found.add(on)
                    # Sort the face corners round its middle, counter-clockwise seen along +n.
                    mid = verts[list(on)].mean(axis=0)
                    u = verts[on[0]] - mid
                    w = np.cross(n, u)
                    on = sorted(on, key=lambda m: math.atan2(np.dot(verts[m] - mid, w), np.dot(verts[m] - mid, u)))
                    faces.append(tuple(int(m) for m in on))
        Polyhedron3d._face_cache[cls] = faces
        return faces

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        """Return the center and every corner point.

        Returns:
            list[Point3d]: The stored points.
        """
        return [self._cent] + self._verts

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_center(self):
        """Return the center point.

        Returns:
            Point3d: The center.
        """
        return self._cent

    def set_center(self, new_c):
        """Move the whole solid so its center lands on a point.

        Args:
            new_c (Point3d): The new center.
        """
        self.move(*(self._xyz(new_c) - self._xyz(self._cent)))

    def get_points(self):
        """Copies of the corner points (get_faces() indexes into this list)."""
        return [v.deepcopy() for v in self._verts]

    def get_faces(self):
        """Each face as a tuple of corner indexes, counter-clockwise seen from outside."""
        return list(self._faces)

    def get_edges(self):
        """Each edge once, as a (corner index, corner index) pair."""
        edges = set()
        for face in self._faces:
            for i in range(len(face)):
                edges.add(tuple(sorted((face[i], face[(i + 1) % len(face)]))))
        return sorted(edges)

    def get_num_faces(self):
        """Return the number of faces.

        Returns:
            int: The face count.
        """
        return len(self._faces)

    def get_num_vertices(self):
        """Return the number of corners.

        Returns:
            int: The corner count.
        """
        return len(self._verts)

    def get_num_edges(self):
        """Return the number of edges.

        Returns:
            int: The edge count.
        """
        return len(self.get_edges())

    def get_length(self):
        """Edge length."""
        f = self._faces[0]
        return float(np.linalg.norm(self._xyz(self._verts[f[0]]) - self._xyz(self._verts[f[1]])))

    get_edge_length = get_length

    def set_length(self, new_len):
        """Resize about the center so every edge is new_len long."""
        k = new_len / self.get_length()
        c = self._xyz(self._cent)
        for v in self._verts:
            v.set_xyz(*(c + (self._xyz(v) - c) * k))

    set_edge_length = set_length

    def get_radius(self):
        """Circumradius: center to a corner."""
        return float(np.linalg.norm(self._xyz(self._verts[0]) - self._xyz(self._cent)))

    def get_inradius(self):
        """Center to the middle of the nearest face."""
        c = self._xyz(self._cent)
        return min(float(np.dot(self._xyz(fc) - c, self._xyz(n)))
                   for fc, n in zip(self.get_face_centers(), self.get_face_normals()))

    def get_width(self):
        """Widest distance across: corner to opposite corner."""
        pts = [self._xyz(v) for v in self._verts]
        return max(float(np.linalg.norm(p - q)) for p in pts for q in pts)

    def get_area(self):
        """Return the surface area.

        Returns:
            float: The surface area.
        """
        return self._area_k * self.get_length() ** 2

    def get_volume(self):
        """Return the volume.

        Returns:
            float: The volume.
        """
        return self._volume_k * self.get_length() ** 3

    def get_face_centers(self):
        """Return the center of every face.

        Returns:
            list[Point3d]: The face centers, in get_faces() order.
        """
        return [Point3d(*np.mean([self._xyz(self._verts[m]) for m in face], axis=0)) for face in self._faces]

    def get_face_normals(self):
        """Outward unit normal of every face, in get_faces() order."""
        normals = []
        for face in self._faces:
            # Newell's method: works for any flat polygon wound counter-clockwise from outside.
            n = np.zeros(3)
            for i in range(len(face)):
                n += np.cross(self._xyz(self._verts[face[i]]), self._xyz(self._verts[face[(i + 1) % len(face)]]))
            normals.append(Point3d(*(n / np.linalg.norm(n))))
        return normals

    def get_norm(self):
        """Normal of the first face (use get_face_normals() for all of them)."""
        return self.get_face_normals()[0]

    def deepcopy(self):
        """Return an independent copy.

        Returns:
            Polyhedron3d: The copy.
        """
        new = self.__class__.__new__(self.__class__)
        new.__dict__.update(self.__dict__)
        new._cent = self._cent.deepcopy()
        new._verts = [v.deepcopy() for v in self._verts]
        return new

    def copy(self):
        """Return an independent copy.

        Returns:
            Polyhedron3d: The copy.
        """
        return self.deepcopy()

    def get_bc(self):
        """Return the border color.

        Returns:
            object: The border color.
        """
        return self._border_col

    def set_bc(self, bc):
        """Set the border color.

        Args:
            bc (object): The new border color.
        """
        self._border_col = bc

    def get_fc(self):
        """Return the fill color.

        Returns:
            object: The fill color.
        """
        return self._fill_col

    def set_fc(self, fc):
        """Set the fill color.

        Args:
            fc (object): The new fill color.
        """
        self._fill_col = fc

    def __str__(self):
        """Return the solid's measurements and colors.

        Returns:
            str: The description.
        """
        return (f'{self.get_name()}:\n\tcenter={self.get_center()}\tfaces={self.get_num_faces()}, '
                f'vertices={self.get_num_vertices()}, edges={self.get_num_edges()}, edge_length={self.get_length():.2f}, '
                f'width={self.get_width():.2f}, volume={self.get_volume():.2f}, area={self.get_area():.2f}'
                f'\n\tfc={self.get_fc()}, bc={self.get_bc()}\n')

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()


class Octahedron3d(Polyhedron3d):
    """8 equal triangle faces; corners point along the world axes when built."""
    _area_k = 2 * math.sqrt(3)
    _volume_k = math.sqrt(2) / 3

    def __init__(self, center, edge_length, bc="blue", fc="green", name="Octahedron3d"):
        """Initialize the solid.

        Args:
            center (Point3d): The center point.
            edge_length (float): The edge length.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
        """
        super().__init__(center, edge_length, bc, fc, name)

    @classmethod
    def _canonical(cls):
        """Return the corner coordinates of the solid for the base edge length.

        Returns:
            list[tuple]: The corner coordinates.
        """
        return [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


class Dodecahedron3d(Polyhedron3d):
    """12 equal pentagon faces."""
    _area_k = 3 * math.sqrt(25 + 10 * math.sqrt(5))
    _volume_k = (15 + 7 * math.sqrt(5)) / 4

    def __init__(self, center, edge_length, bc="blue", fc="green", name="Dodecahedron3d"):
        """Initialize the solid.

        Args:
            center (Point3d): The center point.
            edge_length (float): The edge length.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
        """
        super().__init__(center, edge_length, bc, fc, name)

    @classmethod
    def _canonical(cls):
        """Return the corner coordinates of the solid for the base edge length.

        Returns:
            list[tuple]: The corner coordinates.
        """
        s = (-1, 1)
        cube = [(x, y, z) for x in s for y in s for z in s]
        rest = []
        for a in s:
            for b in s:
                rest += [(0, a / PHI, b * PHI), (a / PHI, b * PHI, 0), (a * PHI, 0, b / PHI)]
        return cube + rest


class Icosahedron3d(Polyhedron3d):
    """20 equal triangle faces."""
    _area_k = 5 * math.sqrt(3)
    _volume_k = 5 * (3 + math.sqrt(5)) / 12

    def __init__(self, center, edge_length, bc="blue", fc="green", name="Icosahedron3d"):
        """Initialize the solid.

        Args:
            center (Point3d): The center point.
            edge_length (float): The edge length.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
        """
        super().__init__(center, edge_length, bc, fc, name)

    @classmethod
    def _canonical(cls):
        """Return the corner coordinates of the solid for the base edge length.

        Returns:
            list[tuple]: The corner coordinates.
        """
        verts = []
        for a in (-1, 1):
            for b in (-1, 1):
                verts += [(0, a, b * PHI), (a, b * PHI, 0), (a * PHI, 0, b)]
        return verts


class RhombicDodecahedron3d(Polyhedron3d):
    """12 equal rhombus (diamond) faces; 6 pointy corners along the world axes when built."""
    _area_k = 8 * math.sqrt(2)
    _volume_k = 16 * math.sqrt(3) / 9

    def __init__(self, center, edge_length, bc="blue", fc="green", name="RhombicDodecahedron3d"):
        """Initialize the solid.

        Args:
            center (Point3d): The center point.
            edge_length (float): The edge length.
            bc (object): The border color.
            fc (object): The fill color.
            name (str): The name.
        """
        super().__init__(center, edge_length, bc, fc, name)

    @classmethod
    def _canonical(cls):
        """Return the corner coordinates of the solid for the base edge length.

        Returns:
            list[tuple]: The corner coordinates.
        """
        s = (-1, 1)
        cube = [(x, y, z) for x in s for y in s for z in s]
        tips = [(2, 0, 0), (-2, 0, 0), (0, 2, 0), (0, -2, 0), (0, 0, 2), (0, 0, -2)]
        return cube + tips


class SphericalCap3d(_Geometry3d, OpOverloaded, Hittable):
    """Part of a sphere cut off by a flat plane (a dome), flat side included.

    center/radius are the whole sphere's; cap_height is how far the dome rises
    from the cut to its pole (radius = hemisphere, 2*radius = whole sphere).
    normal points from the flat cut toward the pole (default world +Z).
    Stored points: sphere center and pole, so move/rot/scale work.
    """
    def __init__(self, center, radius, cap_height, normal=(0, 0, 1), mat=None, color=None, name="SphericalCap3d"):
        """Initialize the cap.

        Args:
            center (Point3d): The center point.
            radius (float): The radius of the whole sphere.
            cap_height (float): The height of the cap from the flat cut to the pole.
            normal (tuple): The direction from the flat cut toward the pole.
            mat (object): The material.
            color (object): The color.
            name (str): The name.

        Raises:
            ValueError: If the radius is not positive, the cap height is outside (0, 2*radius], or the normal is zero.
        """
        if radius <= 0:
            raise ValueError("Radius must be positive.")
        if not 0 < cap_height <= 2 * radius:
            raise ValueError("cap_height must be above 0 and at most 2 * radius.")
        n = np.array(normal, dtype=float)
        if np.linalg.norm(n) == 0:
            raise ValueError("Normal cannot be a zero vector.")
        n = n / np.linalg.norm(n)
        c = np.array(center.get_xyz(), dtype=float)
        self._cent = Point3d(*c)
        self._pole = Point3d(*(c + n * radius))
        # Kept as a fraction of the radius so scale() keeps the same shape.
        self._cap_frac = cap_height / radius
        self._mat = mat
        self._color = color
        self._name = name
        self._Istlink = False
        self._list_name = None

    def set_listname(self, name):
        """Link the object to a named list.

        Args:
            name (str): The name of the list.
        """
        self._list_name = name
        self._Istlink = True

    def get_listname(self):
        """Return the name of the list the object belongs to.

        Returns:
            str | None: The list name, or None if the object is not linked.
        """
        if self._Istlink:
            return self._list_name
        else:
            return None

    def listlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    def rem_listlink(self):
        """Unlink the object from its list and clear the list name."""
        self._Istlink = False
        self._list_name = None

    def set_listlink(self, state):
        """Set whether the object is linked to a list.

        Args:
            state (bool): Whether the object is linked to a list.
        """
        self._Istlink = state

    def get_istlink(self):
        """Return whether the object is linked to a list.

        Returns:
            bool: True if linked.
        """
        return self._Istlink

    @staticmethod
    def _xyz(point):
        """Return a point's coordinates as an array.

        Args:
            point (Point3d): The point to convert.

        Returns:
            numpy.ndarray: The X, Y and Z values.
        """
        return np.array(point.get_xyz(), dtype=float)

    def _points(self):
        """Return the sphere center and the pole.

        Returns:
            list[Point3d]: The stored points.
        """
        return [self._cent, self._pole]

    def get_name(self):
        """Return the object's name.

        Returns:
            str: The name.
        """
        return self._name

    def set_name(self, name):
        """Set the object's name.

        Args:
            name (str): The name.
        """
        self._name = name

    def get_color(self):
        """Return the color.

        Returns:
            object: The color.
        """
        return self._color

    def set_color(self, color):
        """Set the color.

        Args:
            color (object): The color.
        """
        self._color = color

    def get_center(self):
        """Center of the whole sphere the cap is cut from."""
        return self._cent

    @property
    def center(self):
        """Return the center of the whole sphere.

        Returns:
            Point3d: The center.
        """
        return self._cent

    def set_center(self, new_c):
        """Move the whole cap so its sphere center lands on a point.

        Args:
            new_c (Point3d): The new center.
        """
        self.move(*(self._xyz(new_c) - self._xyz(self._cent)))

    def get_pole(self):
        """Top of the dome."""
        return self._pole

    def get_radius(self):
        """Return the radius of the whole sphere.

        Returns:
            float: The radius.
        """
        return float(np.linalg.norm(self._xyz(self._pole) - self._xyz(self._cent)))

    def set_radius(self, new_r):
        """Set the sphere radius, keeping the cap shape.

        Args:
            new_r (float): The new radius.
        """
        c = self._xyz(self._cent)
        self._pole.set_xyz(*(c + self.get_norm() * new_r))

    def get_norm(self):
        """Unit direction from the flat cut toward the pole."""
        n = self._xyz(self._pole) - self._xyz(self._cent)
        return n / np.linalg.norm(n)

    def pr_norm(self):
        """Return the unit direction toward the pole as a Point3d.

        Returns:
            Point3d: The unit direction.
        """
        n = self.get_norm()
        return Point3d(n[0], n[1], n[2])

    def get_height(self):
        """Cap height: flat cut to pole."""
        return self._cap_frac * self.get_radius()

    def set_height(self, cap_height):
        """Set the cap height.

        Args:
            cap_height (float): The new cap height.

        Raises:
            ValueError: If the height is outside (0, 2*radius].
        """
        if not 0 < cap_height <= 2 * self.get_radius():
            raise ValueError("cap_height must be above 0 and at most 2 * radius.")
        self._cap_frac = cap_height / self.get_radius()

    def get_base_center(self):
        """Middle of the flat cut."""
        return Point3d(*(self._xyz(self._pole) - self.get_norm() * self.get_height()))

    def get_base_radius(self):
        """Radius of the flat cut circle."""
        r, h = self.get_radius(), self.get_height()
        return math.sqrt(max(0.0, h * (2 * r - h)))

    def get_width(self):
        """Widest distance across (the whole sphere's width once the cap is past halfway)."""
        r, h = self.get_radius(), self.get_height()
        return 2 * r if h >= r else 2 * self.get_base_radius()

    def get_curved_area(self):
        """Return the area of the curved dome.

        Returns:
            float: The dome area.
        """
        return 2 * math.pi * self.get_radius() * self.get_height()

    def get_base_area(self):
        """Return the area of the flat cut.

        Returns:
            float: The base area.
        """
        a = self.get_base_radius()
        return math.pi * a * a

    def get_area(self):
        """Curved dome plus the flat cut."""
        return self.get_curved_area() + self.get_base_area()

    def get_volume(self):
        """Return the volume of the cap.

        Returns:
            float: The volume.
        """
        r, h = self.get_radius(), self.get_height()
        return math.pi * h * h * (3 * r - h) / 3

    def _on_cap_side(self, p):
        """Check whether a point is on the dome side of the flat cut.

        Args:
            p (Point3d): The point to test.

        Returns:
            bool: True if so.
        """
        # Distance along the normal from the sphere center to the cut plane is r - h.
        d = float(np.dot(self._xyz(p) - self._xyz(self._cent), self.get_norm()))
        return d >= self.get_radius() - self.get_height() - 1e-9

    def contains(self, point):
        """Check whether a point is inside or on the cap.

        Args:
            point (Point3d): The point to test.

        Returns:
            bool: True if the point is in the cap.
        """
        inside = np.linalg.norm(self._xyz(point) - self._xyz(self._cent)) <= self.get_radius() + 1e-9
        return bool(inside and self._on_cap_side(point))

    def get_normal(self, point):
        """Outward unit normal: straight out of the dome, or straight down on the flat cut."""
        p = self._xyz(point)
        d = float(np.dot(p - self._xyz(self._cent), self.get_norm()))
        cut = self.get_radius() - self.get_height()
        if abs(d - cut) < 1e-7 * max(1.0, self.get_radius()):
            return Point3d(*(-self.get_norm()))
        n = p - self._xyz(self._cent)
        return Point3d(*(n / np.linalg.norm(n)))

    def get_points(self, rings=8, segments=24):
        """Points for drawing: base center, then rings from the cut up to the pole, then the pole."""
        c, n, r = self._xyz(self._cent), self.get_norm(), self.get_radius()
        _, u = self._perp(n)
        w = np.cross(n, u)
        # Angle from the pole down to the cut edge.
        top = math.acos(max(-1.0, min(1.0, (r - self.get_height()) / r)))
        pts = [self.get_base_center()]
        for i in range(rings):
            ang = top * (1 - i / rings)
            for j in range(segments):
                lon = 2 * math.pi * j / segments
                pts.append(Point3d(*(c + n * r * math.cos(ang)
                                     + (u * math.cos(lon) + w * math.sin(lon)) * r * math.sin(ang))))
        pts.append(self._pole.deepcopy())
        return pts

    @staticmethod
    def _perp(n):
        """Return a unit vector perpendicular to a unit vector.

        Args:
            n (numpy.ndarray): A unit vector.

        Returns:
            tuple: The input and the perpendicular unit vector.
        """
        helper = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = np.cross(n, helper)
        return n, u / np.linalg.norm(u)

    def hit(self, r, ray_tmin, ray_tmax, rec):
        """Test whether a ray hits the dome or the flat cut.

        Args:
            r (Ray3d): The ray being tested.
            ray_tmin (float): The smallest accepted ray parameter.
            ray_tmax (float): The largest accepted ray parameter.
            rec (Hit_Record): Receives the hit details when the ray hits.

        Returns:
            bool: True if the ray hits within the accepted range. On a hit, ``rec`` is filled in.
        """
        o, d = self._xyz(r.get_origin()), self._xyz(r.direction)
        c, n, rad = self._xyz(self._cent), self.get_norm(), self.get_radius()
        best = None
        # Dome: sphere hits that land on the cap side of the cut.
        oc = c - o
        a = float(np.dot(d, d))
        h = float(np.dot(d, oc))
        disc = h * h - a * (float(np.dot(oc, oc)) - rad * rad)
        if disc >= 0:
            sq = math.sqrt(disc)
            for t in ((h - sq) / a, (h + sq) / a):
                if ray_tmin < t < ray_tmax and self._on_cap_side(Point3d(*(o + d * t))):
                    best = t
                    break
        # Flat cut: plane hit inside the cut circle.
        denom = float(np.dot(d, n))
        if denom != 0:
            base = self._xyz(self.get_base_center())
            t = float(np.dot(base - o, n)) / denom
            if ray_tmin < t < ray_tmax and (best is None or t < best):
                if np.linalg.norm(o + d * t - base) <= self.get_base_radius():
                    best = t
        if best is None:
            return False
        rec.t = best
        rec.p = r.at(rec.t)
        rec.set_face_normal(r, self.get_normal(rec.p))
        return True

    def deepcopy(self):
        """Return an independent copy.

        Returns:
            SphericalCap3d: The copy.
        """
        new = self.__class__.__new__(self.__class__)
        new.__dict__.update(self.__dict__)
        new._cent = self._cent.deepcopy()
        new._pole = self._pole.deepcopy()
        return new

    def copy(self):
        """Return an independent copy.

        Returns:
            SphericalCap3d: The copy.
        """
        return self.deepcopy()

    def __str__(self):
        """Return the cap's measurements and color.

        Returns:
            str: The description.
        """
        return (f"{self.get_name()}:\n\tcenter= {self.get_center()}\tradius={self.get_radius():.2f}, "
                f"cap_height={self.get_height():.2f}, base_radius={self.get_base_radius():.2f}, "
                f"volume={self.get_volume():.2f}, area={self.get_area():.2f}\n\tnormal={self.pr_norm()}\tcolor: {self.get_color()}\n")

    def __repr__(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The representation.
        """
        return self.__str__()

    def descr(self):
        """Return the same text as ``__str__``.

        Returns:
            str: The description.
        """
        return self.__str__()


class Hemisphere3d(SphericalCap3d):
    """Half a sphere: flat side through the center, dome toward normal (default world +Z)."""
    def __init__(self, center, radius, normal=(0, 0, 1), mat=None, color=None, name="Hemisphere3d"):
        """Initialize the hemisphere.

        Args:
            center (Point3d): The center point.
            radius (float): The radius of the hemisphere.
            normal (tuple): The direction the dome faces.
            mat (object): The material.
            color (object): The color.
            name (str): The name.
        """
        super().__init__(center, radius, radius, normal, mat, color, name)

def main():
    """Run the module's entry point. Currently does nothing."""
    pass

if __name__ == "__main__":
    main()