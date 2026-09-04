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

from hittable import Hittable
from vec3 import dot


class Sphere(Hittable):
    def __init__(self, center, radius, mat):
        self.center = center
        self.radius = max(0, radius)
        self.mat = mat

    def hit(self, r, ray_t, rec):
        oc = self.center - r.origin()
        a = r.direction().length_squared()
        h = dot(r.direction(), oc)
        c = oc.length_squared() - self.radius * self.radius

        discriminant = h * h - a * c
        if discriminant < 0:
            return False

        sqrtd = math.sqrt(discriminant)

        # Find the nearest root that lies in the acceptable range.
        root = (h - sqrtd) / a
        if not ray_t.surrounds(root):
            root = (h + sqrtd) / a
            if not ray_t.surrounds(root):
                return False

        rec.t = root
        rec.p = r.at(rec.t)
        outward_normal = (rec.p - self.center) / self.radius
        rec.set_face_normal(r, outward_normal)
        rec.mat = self.mat

        return True
