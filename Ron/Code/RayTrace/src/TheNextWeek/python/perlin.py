# Python port of perlin.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import math

from rtweekend import random_int
from vec3 import Vec3, dot, unit_vector


class Perlin:
    point_count = 256

    def __init__(self):
        self.randvec = [
            unit_vector(Vec3.random(-1, 1)) for _ in range(self.point_count)
        ]
        self.perm_x = self.perlin_generate_perm()
        self.perm_y = self.perlin_generate_perm()
        self.perm_z = self.perlin_generate_perm()

    def noise(self, p):
        u = p.x() - math.floor(p.x())
        v = p.y() - math.floor(p.y())
        w = p.z() - math.floor(p.z())

        i = int(math.floor(p.x()))
        j = int(math.floor(p.y()))
        k = int(math.floor(p.z()))
        c = [[[None, None], [None, None]], [[None, None], [None, None]]]

        for di in range(2):
            for dj in range(2):
                for dk in range(2):
                    c[di][dj][dk] = self.randvec[
                        self.perm_x[(i + di) & 255]
                        ^ self.perm_y[(j + dj) & 255]
                        ^ self.perm_z[(k + dk) & 255]
                    ]

        return self.perlin_interp(c, u, v, w)

    def turb(self, p, depth):
        accum = 0.0
        temp_p = Vec3(p.x(), p.y(), p.z())
        weight = 1.0

        for _i in range(depth):
            accum += weight * self.noise(temp_p)
            weight *= 0.5
            temp_p *= 2

        return abs(accum)

    @classmethod
    def perlin_generate_perm(cls):
        p = list(range(cls.point_count))
        cls.permute(p, cls.point_count)
        return p

    @staticmethod
    def permute(p, n):
        for i in range(n - 1, 0, -1):
            target = random_int(0, i)
            p[i], p[target] = p[target], p[i]

    @staticmethod
    def perlin_interp(c, u, v, w):
        uu = u * u * (3 - 2 * u)
        vv = v * v * (3 - 2 * v)
        ww = w * w * (3 - 2 * w)
        accum = 0.0

        for i in range(2):
            for j in range(2):
                for k in range(2):
                    weight_v = Vec3(u - i, v - j, w - k)
                    accum += (
                        (i * uu + (1 - i) * (1 - uu))
                        * (j * vv + (1 - j) * (1 - vv))
                        * (k * ww + (1 - k) * (1 - ww))
                        * dot(c[i][j][k], weight_v)
                    )

        return accum
