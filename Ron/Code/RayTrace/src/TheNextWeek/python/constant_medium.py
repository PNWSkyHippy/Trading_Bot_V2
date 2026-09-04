# Python port of constant_medium.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from hittable import HitRecord, Hittable
from interval import Interval
from material import Isotropic
from rtweekend import infinity, random_double
from vec3 import Vec3


class ConstantMedium(Hittable):
    def __init__(self, boundary, density, tex_or_albedo):
        self.boundary = boundary
        self.neg_inv_density = -1 / density
        self.phase_function = Isotropic(tex_or_albedo)

    def hit(self, r, ray_t, rec):
        rec1 = HitRecord()
        rec2 = HitRecord()

        if not self.boundary.hit(r, Interval.universe, rec1):
            return False

        if not self.boundary.hit(r, Interval(rec1.t + 0.0001, infinity), rec2):
            return False

        if rec1.t < ray_t.min:
            rec1.t = ray_t.min
        if rec2.t > ray_t.max:
            rec2.t = ray_t.max

        if rec1.t >= rec2.t:
            return False

        if rec1.t < 0:
            rec1.t = 0

        ray_length = r.direction().length()
        distance_inside_boundary = (rec2.t - rec1.t) * ray_length
        hit_distance = self.neg_inv_density * math.log(random_double())

        if hit_distance > distance_inside_boundary:
            return False

        rec.t = rec1.t + hit_distance / ray_length
        rec.p = r.at(rec.t)

        rec.normal = Vec3(1, 0, 0)  # arbitrary
        rec.front_face = True  # also arbitrary
        rec.mat = self.phase_function
        return True

    def bounding_box(self):
        return self.boundary.bounding_box()
