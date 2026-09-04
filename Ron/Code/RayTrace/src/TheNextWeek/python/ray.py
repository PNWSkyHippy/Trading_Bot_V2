# Python port of ray.h
# Originally written in 2016 by Peter Shirley <ptrshrl@gmail.com>
#
# To the extent possible under law, the author(s) have dedicated all copyright and related and
# neighboring rights to this software to the public domain worldwide. This software is
# distributed without any warranty.
#
# You should have received a copy (see file COPYING.txt) of the CC0 Public Domain Dedication
# along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from vec3 import Point3, Vec3


class Ray:
    def __init__(self, origin=None, direction=None, time=0.0):
        self.orig = Point3() if origin is None else origin
        self.dir = Vec3() if direction is None else direction
        self.tm = time

    def origin(self):
        return self.orig

    def direction(self):
        return self.dir

    def time(self):
        return self.tm

    def at(self, t):
        return self.orig + t * self.dir
