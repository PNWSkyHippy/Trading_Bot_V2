from vectors import Vec3, unit_vector
from colors import Color, write_color
from spheres import hit_sphere
#If you have an alias like in C++:
Point3 = Vec3  # (or Point = Vector)

class Ray:
    def __init__(self, origin=None, direction=None, color=None):
        # In C++, default constructor creates default Vector/Point instances
        self._orig = origin if origin is not None else Vec3()
        self._dir = direction if direction is not None else Vec3()
        self.color = color if color is not None else Color() 

    def origin(self):
        """const point3& origin() const"""
        return self._orig

    def direction(self):
        """const vec3& direction() const"""
        return self._dir
    
    def color(self):
        return self.color

    def at(self, t: float):
        """point3 at(double t) const"""
        return self._orig + self._dir * t


def ray_color(r):
    t = HitSphere(Point3(0,0,-1), 0.5, r)
    if (t > 0.0):
        N = unit_vector(r.at(t) - Vec3(0,0,-1))
        return 0.5 * Color(N.x() + 1, N.y() + 1, N.z() + 1)

    unit_direction = unit_vector(r.direction())
    a = 0.5 * (unit_direction.y() + 1.0)
    return (1.0 - a) * Color(1.0, 1.0, 1.0) + a * Color(0.5, 0.7, 1.0)


def main():
    return
    
if __name__ == "__main__":
    main()