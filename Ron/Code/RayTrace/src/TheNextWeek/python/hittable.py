# Python port of hittable.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from abc import ABC, abstractmethod
import math

from aabb import Aabb
from ray import Ray
from rtweekend import degrees_to_radians, infinity
from vec3 import Point3, Vec3, dot


class HitRecord:
    def __init__(self):
        self.p = Point3()
        self.normal = Vec3()
        self.mat = None
        self.t = 0.0
        self.u = 0.0
        self.v = 0.0
        self.front_face = False

    def set_face_normal(self, r, outward_normal):
        # Sets the hit record normal vector.
        # NOTE: the parameter `outward_normal` is assumed to have unit length.
        self.front_face = dot(r.direction(), outward_normal) < 0
        self.normal = outward_normal if self.front_face else -outward_normal

    def copy_from(self, other):
        self.p = other.p
        self.normal = other.normal
        self.mat = other.mat
        self.t = other.t
        self.u = other.u
        self.v = other.v
        self.front_face = other.front_face


class Hittable(ABC):
    @abstractmethod
    def hit(self, r, ray_t, rec):
        raise NotImplementedError

    @abstractmethod
    def bounding_box(self):
        raise NotImplementedError


class Translate(Hittable):
    def __init__(self, obj, offset):
        self.object = obj
        self.offset = offset
        self.bbox = obj.bounding_box() + offset

    def hit(self, r, ray_t, rec):
        # Move the ray backwards by the offset
        offset_r = Ray(r.origin() - self.offset, r.direction(), r.time())

        # Determine whether an intersection exists along the offset ray (and if so, where)
        if not self.object.hit(offset_r, ray_t, rec):
            return False

        # Move the intersection point forwards by the offset
        rec.p += self.offset
        return True

    def bounding_box(self):
        return self.bbox


class RotateY(Hittable):
    def __init__(self, obj, angle):
        self.object = obj
        radians = degrees_to_radians(angle)
        self.sin_theta = math.sin(radians)
        self.cos_theta = math.cos(radians)
        self.bbox = obj.bounding_box()

        min_p = Point3(infinity, infinity, infinity)
        max_p = Point3(-infinity, -infinity, -infinity)

        for i in range(2):
            for j in range(2):
                for k in range(2):
                    x = i * self.bbox.x.max + (1 - i) * self.bbox.x.min
                    y = j * self.bbox.y.max + (1 - j) * self.bbox.y.min
                    z = k * self.bbox.z.max + (1 - k) * self.bbox.z.min

                    newx = self.cos_theta * x + self.sin_theta * z
                    newz = -self.sin_theta * x + self.cos_theta * z

                    tester = Vec3(newx, y, newz)

                    for c in range(3):
                        min_p[c] = min(min_p[c], tester[c])
                        max_p[c] = max(max_p[c], tester[c])

        self.bbox = Aabb(min_p, max_p)

    def hit(self, r, ray_t, rec):
        # Transform the ray from world space to object space.
        origin = Point3(
            (self.cos_theta * r.origin().x()) - (self.sin_theta * r.origin().z()),
            r.origin().y(),
            (self.sin_theta * r.origin().x()) + (self.cos_theta * r.origin().z()),
        )

        direction = Vec3(
            (self.cos_theta * r.direction().x()) - (self.sin_theta * r.direction().z()),
            r.direction().y(),
            (self.sin_theta * r.direction().x()) + (self.cos_theta * r.direction().z()),
        )

        rotated_r = Ray(origin, direction, r.time())

        if not self.object.hit(rotated_r, ray_t, rec):
            return False

        rec.p = Point3(
            (self.cos_theta * rec.p.x()) + (self.sin_theta * rec.p.z()),
            rec.p.y(),
            (-self.sin_theta * rec.p.x()) + (self.cos_theta * rec.p.z()),
        )

        rec.normal = Vec3(
            (self.cos_theta * rec.normal.x()) + (self.sin_theta * rec.normal.z()),
            rec.normal.y(),
            (-self.sin_theta * rec.normal.x()) + (self.cos_theta * rec.normal.z()),
        )

        return True

    def bounding_box(self):
        return self.bbox
