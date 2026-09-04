# Python port of sphere.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from aabb import Aabb
from hittable import HitRecord, Hittable
from interval import Interval
from onb import Onb
from ray import Ray
from rtweekend import infinity, pi, random_double
from vec3 import Vec3, dot


class Sphere(Hittable):
    def __init__(self, *args):
        if len(args) == 3:
            # Stationary Sphere
            static_center, radius, mat = args
            self.center = Ray(static_center, Vec3(0, 0, 0))
            self.radius = max(0, radius)
            self.mat = mat
            rvec = Vec3(self.radius, self.radius, self.radius)
            self.bbox = Aabb(static_center - rvec, static_center + rvec)
        elif len(args) == 4:
            # Moving Sphere
            center1, center2, radius, mat = args
            self.center = Ray(center1, center2 - center1)
            self.radius = max(0, radius)
            self.mat = mat
            rvec = Vec3(self.radius, self.radius, self.radius)
            box1 = Aabb(self.center.at(0) - rvec, self.center.at(0) + rvec)
            box2 = Aabb(self.center.at(1) - rvec, self.center.at(1) + rvec)
            self.bbox = Aabb(box1, box2)
        else:
            raise TypeError("Sphere(center, radius, mat) or Sphere(center1, center2, radius, mat)")

    def hit(self, r, ray_t, rec):
        current_center = self.center.at(r.time())
        oc = current_center - r.origin()
        a = r.direction().length_squared()
        h = dot(r.direction(), oc)
        c = oc.length_squared() - self.radius * self.radius

        discriminant = h * h - a * c
        if discriminant < 0:
            return False

        sqrtd = math.sqrt(discriminant)

        root = (h - sqrtd) / a
        if not ray_t.surrounds(root):
            root = (h + sqrtd) / a
            if not ray_t.surrounds(root):
                return False

        rec.t = root
        rec.p = r.at(rec.t)
        outward_normal = (rec.p - current_center) / self.radius
        rec.set_face_normal(r, outward_normal)
        rec.u, rec.v = self.get_sphere_uv(outward_normal)
        rec.mat = self.mat
        return True

    def bounding_box(self):
        return self.bbox

    def pdf_value(self, origin, direction):
        # This method only works for stationary spheres.
        rec = HitRecord()
        if not self.hit(Ray(origin, direction), Interval(0.001, infinity), rec):
            return 0

        dist_squared = (self.center.at(0) - origin).length_squared()
        cos_theta_max = math.sqrt(1 - self.radius * self.radius / dist_squared)
        solid_angle = 2 * pi * (1 - cos_theta_max)
        return 1 / solid_angle

    def random(self, origin):
        direction = self.center.at(0) - origin
        distance_squared = direction.length_squared()
        uvw = Onb(direction)
        return uvw.transform(self.random_to_sphere(self.radius, distance_squared))

    @staticmethod
    def get_sphere_uv(p):
        # p: a given point on the sphere of radius one, centered at the origin.
        theta = math.acos(-p.y())
        phi = math.atan2(-p.z(), p.x()) + pi
        u = phi / (2 * pi)
        v = theta / pi
        return u, v

    @staticmethod
    def random_to_sphere(radius, distance_squared):
        r1 = random_double()
        r2 = random_double()
        z = 1 + r2 * (math.sqrt(1 - radius * radius / distance_squared) - 1)

        phi = 2 * pi * r1
        x = math.cos(phi) * math.sqrt(1 - z * z)
        y = math.sin(phi) * math.sqrt(1 - z * z)
        return Vec3(x, y, z)
