import math
from opoverloaded import OpOverloaded
import local_functions
import numpy as np

def rotate_x_3d(point, angle_rad):
    """
    Rotates a 3D point or vector [x, y, z] around the X-axis by angle_rad.
    Accepts both a single 1D array/list or a batch array of shape (N, 3).
    """
    v = np.array([point.get_x(), point.get_y(), point.get_z()], dtype=float)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    # If a single 3D coordinate/vector is passed
    if v.ndim == 1:
        x, y, z = point.get_xyz()
        x_rot = x
        y_rot = y * cos_a - z * sin_a
        z_rot = y * sin_a + z * cos_a
        return Point3d(x_rot, y_rot, z_rot)

def rotate_y_3d(point, angle_rad):
    """Rotates a 3D point/vector around the Y-axis."""
    v = np.array([point.get_x(), point.get_y(), point.get_z()], dtype=float)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    # If a single 3D coordinate/vector is passed
    if v.ndim == 1:
        x, y, z = point.get_xyz()
        y_rot = y
        x_rot = x * cos_a + z * sin_a
        z_rot = -x * sin_a + z * cos_a
        return Point3d(x_rot, y_rot, z_rot)
    
   
def rotate_z_3d(point, angle_rad):
    """Rotates a 3D point/vector around the Z-axis."""
    v = np.array([point.get_x(), point.get_y(), point.get_z()], dtype=float)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    if v.ndim == 1:
        x, y, z = point.get_xyz()
        z_rot = z
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        return Point3d(x_rot, y_rot, z_rot)
 
def rotate_around_vector(point, axis_vector, angle_rad):
    """
    Rotates a 3D point/vector around an arbitrary 3D axis vector 
    using Rodrigues' rotation formula.
    """
    v = np.array([point.get_x(), point.get_y(), point.get_z()], dtype=float)
    # Ensure the axis vector is a unit vector (length of 1)
    axis = np.array((axis_vector.get_x(), axis_vector.get_y(), axis_vector.get_z()), dtype=float)

    axis_norm = np.linalg.norm(axis)
    if axis_norm == 0:
        raise ValueError("Rotation axis cannot be a zero vector.")
    k = axis / axis_norm  # Normalized axis
    
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    if v.ndim == 1:
        # Rodrigues' formula for a single vector
        v_rot = v * cos_a + np.cross(k, v) * sin_a + k * np.dot(k, v) * (1 - cos_a)
        return Point3d(v_rot[0], v_rot[1], v_rot[2])



def rotate_line_x_3d(line, angle_rad):
    """
    Rotates a 3D line around the X-axis by angle_rad.
    Accepts both a single 1D array/list or a batch array of shape (N, 3).
    """
    start = line.get_start()
    end = line.get_end()
    start_rot = rotate_x_3d(start, angle_rad)
    end_rot = rotate_x_3d(end, angle_rad)
    return Line3d(start_rot, end_rot)


class Point3d(OpOverloaded):
    """Store and manipulate a 3d X,Y,Z coordinate
    methods: get_x, get_y, get_z return x,y,or z
    move(newx,newy,newz) translates x+newx,y+newy,z+newz

    """

    # intitialie and store x,y, z
    def __init__(self, x, y, z):
        self._x = x
        self._y = y
        self._z = z

    def set_x(self, val):
        self._x  - val

    # Report current color
    def get_x(self):
        return self._x

    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, val):
        self._x = val 
        
    def set_y(self, val):
        self._y - val

    # Report current color
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

    # translate x,y,z to new x,y,z
    def move(self, dx, dy, dz):
        self._x = self._x + dx
        self._y = self._y + dy
        self._z = self._z + dz

    # Return state of Line3d object
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

    def set_x(self, val):
        super().set_x(val)

    # Report current color
    def get_x(self):
        return super().get_x()

    @property
    def x(self):
        return super().get_x()
    
    @x.setter
    def x(self, val):
        super().set_x(val) 
        
    def set_y(self, val):
        super().set_y(val)

    # Report current color
    def get_y(self):
        return super().get_y()

    @property
    def y(self):
        return super().get_y()
    
    @y.setter
    def y(self, val):
        super().set_y(val)

    # Change color ofpixel
    def set_z(self, val):
        super().set_z(val)

    def get_z(self):
        return super().get_z()

    @property
    def z(self):
        return super().get_z()
    
    @z.setter
    def z(self, val):
        super().set_z(val)

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

    def length(self):
        return math.sqrt(self.length_squared())

    def length_squared(self):
        xx = self._end_point.get_x() - self._start_point.get_x()
        yy = self._end_point.get_y() - self._start_point.get_y()
        zz = self._end_point.get_z() - self._start_point.get_z()
        return xx * xx + yy * yy + zz * zz
 
    # Move the line by dx, dy, dz
    def move(self, dx, dy, dz):
        self._start_point.move(dx, dy, dz)
        self._end_point.move(dx, dy, dz)
        
    # Rotate the line around the x-axis
    def rotate_x(self, angle):
        # Implementation for rotating around the x-axis
        self._start_point.rotate_x(angle)
        self._end_point.rotate_x(angle)

    # Return end point
    def get_end(self):
        return self._end_point

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
point5 = Point3d(6, 6, 5)
point6 = Point3d(6, 1, 5)
point7 = Point3d(6, 1, 5)
point8 = Point3d(1, 1, 5)
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

# --- Example Usage ---
angle = 0.180  # Angle in radians

# 1. Representing a 3D Line: Line = Point + t * Vector
line_point = line2
line_vector =  line4

line_point_rot = rotate_line_x_3d(line_point, angle)
line_vector_rot = rotate_line_x_3d(line_vector, angle)


# --- Example Usage ---
angle = 0.45
arbitrary_axis = point1 # Diagonal axis
sample_point = point7

print("Original Point      :", point2)
print("Rotated around Y    :", rotate_y_3d(point2, angle))
print("Rotated around Z    :", rotate_z_3d(point3, angle))
print("Rotated around Vector:", rotate_around_vector(point4, arbitrary_axis, angle))

# 2. Representing a 3D Plane: Defined by a point and two spanning vectors
#plane_point = np.array([0.0, 0.0, 5.0])
#plane_v1 = np.array([1.0, 0.0, 0.0])
#plane_v2 = np.array([0.0, 2.0, -1.0])

#plane_point_rot = rotate_x_3d(plane_point, angle)
#plane_v1_rot = rotate_x_3d(plane_v1, angle)
#plane_v2_rot = rotate_x_3d(plane_v2, angle)

# --- Output Verification ---
print("--- ROTATED LINE ---")
print(f"Original Point : {line_point}  -> Rotated: {line_point_rot}")
print(f"Original Vector: {line_vector}  -> Rotated: {line_vector_rot}\n")

#print("--- ROTATED PLANE ---")
#print(f"Original Point : {plane_point}  -> Rotated: {plane_point_rot}")
#print(f"Original Vector 1: {plane_v1}  -> Rotated: {plane_v1_rot}")
#p#rint(f"Original Vector 2: {plane_v2}  -> Rotated: {plane_v2_rot}")