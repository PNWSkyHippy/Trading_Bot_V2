# Python port of aabb.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from interval import Interval
from vec3 import Point3


class Aabb:
    def __init__(self, a=None, b=None, c=None):
        if a is None:
            # The default AABB is empty, since intervals are empty by default.
            self.x = Interval()
            self.y = Interval()
            self.z = Interval()
        elif c is not None:
            self.x = a
            self.y = b
            self.z = c
            self.pad_to_minimums()
        elif isinstance(a, Aabb):
            self.x = Interval(a.x, b.x)
            self.y = Interval(a.y, b.y)
            self.z = Interval(a.z, b.z)
        else:
            # Treat the two points a and b as extrema for the bounding box.
            self.x = Interval(a[0], b[0]) if a[0] <= b[0] else Interval(b[0], a[0])
            self.y = Interval(a[1], b[1]) if a[1] <= b[1] else Interval(b[1], a[1])
            self.z = Interval(a[2], b[2]) if a[2] <= b[2] else Interval(b[2], a[2])
            self.pad_to_minimums()

    def axis_interval(self, n):
        if n == 1:
            return self.y
        if n == 2:
            return self.z
        return self.x

    def hit(self, r, ray_t):
        # C++ passes interval by value; copy so we can shrink the range locally.
        ray_t = Interval(ray_t.min, ray_t.max)
        ray_orig = r.origin()
        ray_dir = r.direction()

        for axis in range(3):
            ax = self.axis_interval(axis)
            adinv = 1.0 / ray_dir[axis]

            t0 = (ax.min - ray_orig[axis]) * adinv
            t1 = (ax.max - ray_orig[axis]) * adinv

            if t0 < t1:
                if t0 > ray_t.min:
                    ray_t.min = t0
                if t1 < ray_t.max:
                    ray_t.max = t1
            else:
                if t1 > ray_t.min:
                    ray_t.min = t1
                if t0 < ray_t.max:
                    ray_t.max = t0

            if ray_t.max <= ray_t.min:
                return False
        return True

    def longest_axis(self):
        # Returns the index of the longest axis of the bounding box.
        if self.x.size() > self.y.size():
            return 0 if self.x.size() > self.z.size() else 2
        return 1 if self.y.size() > self.z.size() else 2

    def pad_to_minimums(self):
        # Adjust the AABB so that no side is narrower than some delta, padding if necessary.
        delta = 0.0001
        if self.x.size() < delta:
            self.x = self.x.expand(delta)
        if self.y.size() < delta:
            self.y = self.y.expand(delta)
        if self.z.size() < delta:
            self.z = self.z.expand(delta)

    def __add__(self, offset):
        return Aabb(self.x + offset.x(), self.y + offset.y(), self.z + offset.z())

    def __radd__(self, offset):
        return self + offset


Aabb.empty = Aabb(Interval.empty, Interval.empty, Interval.empty)
Aabb.universe = Aabb(Interval.universe, Interval.universe, Interval.universe)
