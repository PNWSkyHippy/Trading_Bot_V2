# Python port of quad.h
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from aabb import Aabb
from hittable import Hittable
from hittable_list import HittableList
from interval import Interval
from vec3 import Point3, Vec3, cross, dot, unit_vector


class Quad(Hittable):
    def __init__(self, Q, u, v, mat):
        self.Q = Q
        self.u = u
        self.v = v
        self.mat = mat

        n = cross(u, v)
        self.normal = unit_vector(n)
        self.D = dot(self.normal, Q)
        self.w = n / dot(n, n)

        self.set_bounding_box()

    def set_bounding_box(self):
        bbox_diagonal1 = Aabb(self.Q, self.Q + self.u + self.v)
        bbox_diagonal2 = Aabb(self.Q + self.u, self.Q + self.v)
        self.bbox = Aabb(bbox_diagonal1, bbox_diagonal2)

    def bounding_box(self):
        return self.bbox

    def hit(self, r, ray_t, rec):
        denom = dot(self.normal, r.direction())

        # No hit if the ray is parallel to the plane.
        if abs(denom) < 1e-8:
            return False

        t = (self.D - dot(self.normal, r.origin())) / denom
        if not ray_t.contains(t):
            return False

        intersection = r.at(t)
        planar_hitpt_vector = intersection - self.Q
        alpha = dot(self.w, cross(planar_hitpt_vector, self.v))
        beta = dot(self.w, cross(self.u, planar_hitpt_vector))

        if not self.is_interior(alpha, beta, rec):
            return False

        rec.t = t
        rec.p = intersection
        rec.mat = self.mat
        rec.set_face_normal(r, self.normal)
        return True

    def is_interior(self, a, b, rec):
        unit_interval = Interval(0, 1)
        if not unit_interval.contains(a) or not unit_interval.contains(b):
            return False
        rec.u = a
        rec.v = b
        return True


def box(a, b, mat):
    # Returns the 3D box (six sides) that contains the two opposite vertices a & b.
    sides = HittableList()

    min_p = Point3(min(a.x(), b.x()), min(a.y(), b.y()), min(a.z(), b.z()))
    max_p = Point3(max(a.x(), b.x()), max(a.y(), b.y()), max(a.z(), b.z()))

    dx = Vec3(max_p.x() - min_p.x(), 0, 0)
    dy = Vec3(0, max_p.y() - min_p.y(), 0)
    dz = Vec3(0, 0, max_p.z() - min_p.z())

    sides.add(Quad(Point3(min_p.x(), min_p.y(), max_p.z()), dx, dy, mat))  # front
    sides.add(Quad(Point3(max_p.x(), min_p.y(), max_p.z()), -dz, dy, mat))  # right
    sides.add(Quad(Point3(max_p.x(), min_p.y(), min_p.z()), -dx, dy, mat))  # back
    sides.add(Quad(Point3(min_p.x(), min_p.y(), min_p.z()), dz, dy, mat))  # left
    sides.add(Quad(Point3(min_p.x(), max_p.y(), max_p.z()), dx, -dz, mat))  # top
    sides.add(Quad(Point3(min_p.x(), min_p.y(), min_p.z()), dx, dz, mat))  # bottom

    return sides
