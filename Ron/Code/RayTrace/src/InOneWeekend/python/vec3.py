# Python port of vec3.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from __future__ import annotations

import math

from rtweekend import random_double


class Vec3:
    def __init__(self, e0=0.0, e1=0.0, e2=0.0):
        self.e = [float(e0), float(e1), float(e2)]

    def x(self):
        return self.e[0]

    def y(self):
        return self.e[1]

    def z(self):
        return self.e[2]

    def __neg__(self):
        return Vec3(-self.e[0], -self.e[1], -self.e[2])

    def __getitem__(self, i):
        return self.e[i]

    def __setitem__(self, i, value):
        self.e[i] = float(value)

    def __iadd__(self, v):
        self.e[0] += v.e[0]
        self.e[1] += v.e[1]
        self.e[2] += v.e[2]
        return self

    def __imul__(self, t):
        self.e[0] *= t
        self.e[1] *= t
        self.e[2] *= t
        return self

    def __itruediv__(self, t):
        return self.__imul__(1 / t)

    def length(self):
        return math.sqrt(self.length_squared())

    def length_squared(self):
        return self.e[0] * self.e[0] + self.e[1] * self.e[1] + self.e[2] * self.e[2]

    def near_zero(self):
        # Return true if the vector is close to zero in all dimensions.
        s = 1e-8
        return (abs(self.e[0]) < s) and (abs(self.e[1]) < s) and (abs(self.e[2]) < s)

    def copy_from(self, other):
        self.e[0], self.e[1], self.e[2] = other.e[0], other.e[1], other.e[2]
        return self

    @staticmethod
    def random(min_val=None, max_val=None):
        if min_val is None:
            return Vec3(random_double(), random_double(), random_double())
        return Vec3(
            random_double(min_val, max_val),
            random_double(min_val, max_val),
            random_double(min_val, max_val),
        )

    def __add__(self, v):
        return Vec3(self.e[0] + v.e[0], self.e[1] + v.e[1], self.e[2] + v.e[2])

    def __sub__(self, v):
        return Vec3(self.e[0] - v.e[0], self.e[1] - v.e[1], self.e[2] - v.e[2])

    def __mul__(self, t):
        if isinstance(t, Vec3):
            return Vec3(self.e[0] * t.e[0], self.e[1] * t.e[1], self.e[2] * t.e[2])
        return Vec3(self.e[0] * t, self.e[1] * t, self.e[2] * t)

    def __rmul__(self, t):
        return self * t

    def __truediv__(self, t):
        return self * (1 / t)

    def __repr__(self):
        return f"Vec3({self.e[0]}, {self.e[1]}, {self.e[2]})"


# Point3 is just an alias for Vec3, but useful for geometric clarity in the code.
Point3 = Vec3


# Vector Utility Functions

def dot(u, v):
    return u.e[0] * v.e[0] + u.e[1] * v.e[1] + u.e[2] * v.e[2]


def cross(u, v):
    return Vec3(
        u.e[1] * v.e[2] - u.e[2] * v.e[1],
        u.e[2] * v.e[0] - u.e[0] * v.e[2],
        u.e[0] * v.e[1] - u.e[1] * v.e[0],
    )


def unit_vector(v):
    return v / v.length()


def random_in_unit_disk():
    while True:
        p = Vec3(random_double(-1, 1), random_double(-1, 1), 0)
        if p.length_squared() < 1:
            return p


def random_unit_vector():
    while True:
        p = Vec3.random(-1, 1)
        lensq = p.length_squared()
        if 1e-160 < lensq <= 1.0:
            return p / math.sqrt(lensq)


def random_on_hemisphere(normal):
    on_unit_sphere = random_unit_vector()
    if dot(on_unit_sphere, normal) > 0.0:
        return on_unit_sphere
    return -on_unit_sphere


def reflect(v, n):
    return v - 2 * dot(v, n) * n


def refract(uv, n, etai_over_etat):
    cos_theta = min(dot(-uv, n), 1.0)
    r_out_perp = etai_over_etat * (uv + cos_theta * n)
    r_out_parallel = -math.sqrt(abs(1.0 - r_out_perp.length_squared())) * n
    return r_out_perp + r_out_parallel
